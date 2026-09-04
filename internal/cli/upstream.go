package cli

import (
	"sort"
	"strings"

	"codeberg.org/traidare/ck3_mods/internal/generate"
	"codeberg.org/traidare/ck3_mods/internal/jsonout"
	"codeberg.org/traidare/ck3_mods/internal/sourcelock"
	"codeberg.org/traidare/ck3_mods/internal/workspace"
)

func upstreamCommand() *Command {
	return &Command{
		Name:    "upstream",
		Summary: "Check whether updated upstream items moved anything we consume",
		Usage:   "ck3mm upstream [WORKSHOP_ID...] [--locks-only] [--apply]",
		Run:     runUpstream,
	}
}

// itemOf names the upstream item a canonical key belongs to: a Workshop ID, or
// the bare namespace for the game and repository roots, which have no finer
// grain worth reporting on.
func itemOf(key string) string {
	if id, found := sourcelock.WorkshopID(key); found {
		return id
	}
	namespace, _, _ := strings.Cut(key, "/")
	return namespace
}

// keysForItem picks the keys belonging to one upstream item, in the order the
// lock comparison already sorted them into.
func keysForItem(keys []string, item string) []string {
	var selected []string
	for _, key := range keys {
		if itemOf(key) == item {
			selected = append(selected, key)
		}
	}
	return selected
}

// consumer is one module's stake in the items being checked: how many of its
// pinned inputs are in scope, and which of them moved on disk.
type consumer struct {
	mod     *workspace.Mod
	pinned  map[string]int
	changes sourcelock.Changes
}

// changedFor counts what moved under one item, so a module can be reported as
// untouched by the item being asked about even while another one moved.
func (c *consumer) changedFor(item string) int {
	return len(keysForItem(c.changes.Changed, item)) +
		len(keysForItem(c.changes.Removed, item))
}

// collectConsumers verifies every module's lock, restricted to the requested
// items. Only locked files are rehashed, so this stays a matter of tens of
// files rather than the whole Workshop tree.
func collectConsumers(env *Env, selected map[string]bool) ([]*consumer, error) {
	mods, err := env.Workspace.Mods()
	if err != nil {
		return nil, err
	}
	roots := generate.LockRoots(env.Workspace, env.Config)

	var consumers []*consumer
	for _, mod := range mods {
		lock, err := sourcelock.Load(generate.LockPath(mod))
		if err != nil {
			return nil, err
		}
		scoped := sourcelock.Lock{
			SchemaVersion: lock.SchemaVersion,
			Files:         map[string]sourcelock.Entry{},
		}
		pinned := map[string]int{}
		for key, entry := range lock.Files {
			if len(selected) > 0 && !selected[itemOf(key)] {
				continue
			}
			scoped.Files[key] = entry
			pinned[itemOf(key)]++
		}
		if len(scoped.Files) == 0 {
			continue
		}
		changes, err := sourcelock.Verify(scoped, roots)
		if err != nil {
			return nil, err
		}
		consumers = append(consumers, &consumer{mod: mod, pinned: pinned, changes: changes})
	}
	return consumers, nil
}

// itemsInScope lists every item to report on: the ones asked for, or every one
// anything is pinned against. Requested items with no consumer are kept, since
// "nothing we own reads that" is the answer to half of these questions.
func itemsInScope(consumers []*consumer, selected map[string]bool) []string {
	names := map[string]bool{}
	for item := range selected {
		names[item] = true
	}
	if len(selected) == 0 {
		for _, entry := range consumers {
			for item := range entry.pinned {
				names[item] = true
			}
		}
	}
	items := make([]string, 0, len(names))
	for item := range names {
		items = append(items, item)
	}
	sort.Strings(items)
	return items
}

func runUpstream(env *Env) (int, error) {
	set := flagSet("upstream", env)
	locksOnly := set.Bool("locks-only", false,
		"report pin drift only, without re-running the affected generators")
	ids, err := parse(set, env.Args)
	if err != nil {
		return 2, nil
	}

	selected := map[string]bool{}
	for _, id := range ids {
		selected[id] = true
	}
	consumers, err := collectConsumers(env, selected)
	if err != nil {
		return 1, err
	}

	items := itemsInScope(consumers, selected)
	drifted := make([]*consumer, 0, len(consumers))
	for _, entry := range consumers {
		if !entry.changes.Empty() {
			drifted = append(drifted, entry)
		}
	}

	// The generator re-run is what turns "an input moved" into "and here is what
	// it does to what we ship". Only drifted modules are run, so the cost tracks
	// the size of the answer rather than the size of the workspace.
	outcomes := map[string]generate.Result{}
	if !*locksOnly {
		for _, entry := range drifted {
			if !entry.mod.HasGenerator() {
				continue
			}
			result, err := generate.Run(env.Workspace, entry.mod, env.Config,
				generate.Options{Apply: env.Apply})
			if err != nil {
				return 1, err
			}
			outcomes[entry.mod.Slug] = result
		}
	}

	if env.JSON() {
		if err := jsonout.Write(env.Stdout,
			upstreamReport(items, consumers, outcomes)); err != nil {
			return 1, err
		}
	} else {
		printUpstream(env, items, consumers, outcomes)
	}

	if len(drifted) > 0 && (!env.Apply || *locksOnly) {
		return 1, nil
	}
	return 0, nil
}

func upstreamReport(items []string, consumers []*consumer, outcomes map[string]generate.Result) []any {
	report := make([]any, 0, len(items))
	for _, item := range items {
		modules := []any{}
		for _, entry := range consumers {
			if entry.pinned[item] == 0 {
				continue
			}
			module := map[string]any{
				"slug":    entry.mod.Slug,
				"pinned":  entry.pinned[item],
				"changed": keysForItem(entry.changes.Changed, item),
				"removed": keysForItem(entry.changes.Removed, item),
			}
			if result, ran := outcomes[entry.mod.Slug]; ran {
				module["outputs"] = map[string]any{
					"current": result.Current(),
					"changed": result.ChangedFiles,
					"stale":   result.StaleFiles,
				}
			}
			modules = append(modules, module)
		}
		report = append(report, map[string]any{"item": item, "consumers": modules})
	}
	return report
}

func printUpstream(env *Env, items []string, consumers []*consumer, outcomes map[string]generate.Result) {
	for _, item := range items {
		var stake []*consumer
		total := 0
		for _, entry := range consumers {
			if entry.pinned[item] == 0 {
				continue
			}
			stake = append(stake, entry)
			total += entry.pinned[item]
		}
		if len(stake) == 0 {
			env.Printf("%s: nothing we generate reads this item\n", item)
			continue
		}
		env.Printf("%s: %d pinned file(s) across %d module(s)\n", item, total, len(stake))
		for _, entry := range stake {
			moved := entry.changedFor(item)
			if moved == 0 {
				env.Printf("  %s: %d pinned, unchanged\n", entry.mod.Slug, entry.pinned[item])
				continue
			}
			env.Printf("  %s: %d of %d changed\n", entry.mod.Slug, moved, entry.pinned[item])
			printSourceChanges(env, sourcelock.Changes{
				Changed: keysForItem(entry.changes.Changed, item),
				Removed: keysForItem(entry.changes.Removed, item),
			}, "    ")
		}
	}

	if len(outcomes) == 0 {
		return
	}
	env.Printf("\n")
	slugs := make([]string, 0, len(outcomes))
	for slug := range outcomes {
		slugs = append(slugs, slug)
	}
	sort.Strings(slugs)
	for _, slug := range slugs {
		result := outcomes[slug]
		if result.Current() {
			env.Printf("%s: inputs moved, output unchanged\n", slug)
			continue
		}
		action := "would update"
		if env.Apply {
			action = "updated"
		}
		paths := append(append([]string{}, result.ChangedFiles...), result.StaleFiles...)
		sort.Strings(paths)
		env.Printf("%s: %s %d file(s)\n", slug, action, len(paths))
		for _, path := range paths {
			env.Printf("  %s\n", path)
		}
	}
}
