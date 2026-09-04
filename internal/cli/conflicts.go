package cli

import (
	"errors"
	"fmt"
	"sort"

	"codeberg.org/traidare/ck3_mods/internal/config"
	"codeberg.org/traidare/ck3_mods/internal/conflicts"
	"codeberg.org/traidare/ck3_mods/internal/jsonout"
	"codeberg.org/traidare/ck3_mods/internal/layers"
	"codeberg.org/traidare/ck3_mods/internal/playset"
	"codeberg.org/traidare/ck3_mods/internal/report"
)

func conflictsCommand() *Command {
	return &Command{
		Name:    "conflicts",
		Summary: "Analyze load-order conflicts across a playset",
		Usage:   "ck3mm conflicts [playset] [--involving ID ...] [--files|--summary-only]",
		Run:     runConflicts,
	}
}

// withExternalMods appends installed selectors the playset does not enable.
// Multiple additions follow their flag order.
func withExternalMods(discovery layers.Discovery, involving []string, workshopDir, paradoxDir string) ([]conflicts.Provider, []report.Warning, error) {
	providers := append([]conflicts.Provider{}, discovery.Providers...)
	for _, selector := range involving {
		if selector == "" {
			continue
		}
		found := false
		for _, provider := range providers {
			if conflicts.Selects(provider.ToRecord(), selector) {
				found = true
				break
			}
		}
		if found {
			continue
		}

		external, err := layers.ResolveExternal(selector, workshopDir, paradoxDir,
			layers.NextPosition(providers))
		if errors.Is(err, layers.ErrNotInstalled) {
			continue
		}
		if err != nil {
			return providers, discovery.Warnings, fmt.Errorf("mod selector %q: installed copy could not be read: %w", selector, err)
		}
		providers = append(providers, external)
	}
	return providers, discovery.Warnings, nil
}

func runConflicts(env *Env) (int, error) {
	set := flagSet("conflicts", env)
	playsetFile := set.String("playset-file", "", "analyze an exported playset instead of the live one")
	files := set.Bool("files", false, "report individual files instead of mod pairs")
	summaryOnly := set.Bool("summary-only", false, "report only the summary")
	allFiles := set.Bool("all-files", false, "report all files, including non-conflicts")
	debugPaths := set.Bool("debug-paths", false, "append the resolved provider roots")
	failOn := set.String("fail-on", "", "exit non-zero on divergent, any, or missing")
	var involving, includePrefix, excludePrefix stringList
	set.Var(&involving, "involving", "only report conflicts involving this mod (repeatable)")
	set.Var(&includePrefix, "include-prefix", "only report paths under this prefix (repeatable)")
	set.Var(&excludePrefix, "exclude-prefix", "skip paths under this prefix (repeatable)")
	positional, err := parse(set, env.Args)
	if err != nil {
		return 2, err
	}
	if len(positional) > 1 {
		return 2, fmt.Errorf("expected at most one playset name, got %d", len(positional))
	}
	name := ""
	if len(positional) == 1 {
		name = positional[0]
	}
	if *playsetFile != "" && name != "" {
		return 2, fmt.Errorf("choose either a playset name or --playset-file, not both")
	}
	fileView := *files || *allFiles
	if *summaryOnly && fileView {
		return 2, fmt.Errorf("choose either a file view or --summary-only, not both")
	}

	if err := env.Config.Require(config.ParadoxDir, config.WorkshopDir); err != nil {
		return 1, err
	}

	var source playset.Playset
	if *playsetFile != "" {
		source, err = playset.LoadFile(*playsetFile)
	} else {
		source, err = playset.LoadLive(env.Config.LauncherDB(), name, env.Config.PlaysetName)
	}
	if err != nil {
		return 1, err
	}

	discovery := layers.Discover(source, env.Config.WorkshopDir, env.Config.ParadoxDir)
	providers, warnings, err := withExternalMods(discovery, involving,
		env.Config.WorkshopDir, env.Config.ParadoxDir)
	if err != nil {
		return 2, err
	}

	analysis, err := conflicts.Analyze(providers, &discovery.Playset, warnings, *allFiles)
	if err != nil {
		return 1, err
	}
	analysis, err = conflicts.Apply(analysis, conflicts.Filter{
		Involving:       involving,
		IncludePrefixes: includePrefix,
		ExcludePrefixes: excludePrefix,
		ConflictsOnly:   !*allFiles,
		SummaryOnly:     *summaryOnly,
	})
	if err != nil {
		return 2, err
	}

	// The default view pairs only the selected mods, not every participant on a
	// file that happens to involve one of them.
	var pairs []report.ModPair
	if !fileView && !*summaryOnly {
		anchors := map[string]bool{}
		for _, mod := range analysis.Mods {
			for _, selector := range involving {
				if conflicts.Selects(mod, selector) {
					anchors[mod.StableID] = true
					break
				}
			}
		}
		pairs = report.PairsInvolving(report.PairConflicts(analysis.Files), anchors)
		analysis.Files = nil
	}

	resolvedRoots := map[string]string{}
	for _, provider := range providers {
		resolvedRoots[provider.StableID] = provider.Root
	}

	if env.JSON() {
		payload := analysis.ToMap()
		// A view selects the same sections in both formats.
		switch {
		case *summaryOnly:
			delete(payload, "files")
			delete(payload, "mods")
		case fileView:
		default:
			delete(payload, "summary")
			delete(payload, "files")
			rendered := make([]any, len(pairs))
			for index, pair := range pairs {
				rendered[index] = pair.ToMap()
			}
			payload["modPairs"] = rendered
		}
		if *debugPaths {
			paths := map[string]any{}
			for stableID, root := range resolvedRoots {
				paths[stableID] = root
			}
			payload["debugPaths"] = paths
		}
		if err := jsonout.Write(env.Stdout, payload); err != nil {
			return 1, err
		}
	} else {
		if fileView || *summaryOnly {
			env.Printf("%s", report.RenderText(analysis))
		} else {
			env.Printf("%s", report.RenderPairs(analysis, pairs))
		}
		if *debugPaths {
			env.Printf("\nDebug paths\n")
			stableIDs := make([]string, 0, len(resolvedRoots))
			for stableID := range resolvedRoots {
				stableIDs = append(stableIDs, stableID)
			}
			sort.Strings(stableIDs)
			for _, stableID := range stableIDs {
				env.Printf("  %s: %s\n", stableID, resolvedRoots[stableID])
			}
		}
	}

	failed, err := conflicts.ShouldFail(analysis, *failOn)
	if err != nil {
		return 2, err
	}
	if failed {
		return 1, nil
	}
	return 0, nil
}
