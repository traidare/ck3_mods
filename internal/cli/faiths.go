package cli

import (
	"fmt"
	"strings"

	"codeberg.org/traidare/ck3_mods/internal/gamedata"
	"codeberg.org/traidare/ck3_mods/internal/jsonout"
	"codeberg.org/traidare/ck3_mods/internal/religions"
)

func faithsCommand() *Command {
	return &Command{
		Name:    "faiths",
		Summary: "Inspect the playset's effective faith data",
		Children: []*Command{
			{
				Name:    "list",
				Summary: "List effective faiths",
				Usage:   "ck3mm faiths list [--religion ID] [--doctrine ID]... [--match all|any]",
				Run:     runFaithsList,
			},
			{
				Name:    "show",
				Summary: "Print one faith's effective definition",
				Usage:   "ck3mm faiths show FAITH [--raw]",
				Run:     runFaithsShow,
			},
			{
				Name:    "holy-sites",
				Summary: "List holy sites and the bonuses they grant",
				Usage:   "ck3mm faiths holy-sites [FAITH]",
				Run:     runFaithsHolySites,
			},
		},
	}
}

// religionDatabase resolves the playset and parses its religion data.
func religionDatabase(env *Env) (religions.Database, error) {
	if err := requireGameDirs(env); err != nil {
		return religions.Database{}, err
	}
	database, err := religions.Load(
		env.Config.GameDir,
		env.Config.WorkshopDir,
		env.Config.ParadoxDir,
		env.Config.LauncherDB(),
		"",
		env.Config.PlaysetName,
	)
	if err != nil {
		return religions.Database{}, err
	}
	reportWarnings(env, database.Warnings)
	return database, nil
}

func runFaithsList(env *Env) (int, error) {
	set := flagSet("faiths list", env)
	religion := set.String("religion", "", "only include faiths of this religion")
	var requested stringList
	set.Var(&requested, "doctrine", "only include faiths with this effective doctrine; repeatable")
	match := set.String("match", "all", "how repeated --doctrine filters combine: all or any")
	positional, err := parse(set, env.Args)
	if err != nil {
		return 2, nil
	}
	if len(positional) > 0 {
		return 2, fmt.Errorf("unexpected argument %q", positional[0])
	}
	if *match != "all" && *match != "any" {
		return 2, fmt.Errorf("unknown --match %q; choose all or any", *match)
	}

	database, err := religionDatabase(env)
	if err != nil {
		return 1, err
	}
	selected, err := database.SelectFaiths(*religion, requested, *match == "all")
	if err != nil {
		return 1, err
	}

	if env.JSON() {
		items := make([]any, 0, len(selected))
		for _, faith := range selected {
			items = append(items, map[string]any{
				"id":       faith.Identifier,
				"religion": faith.Religion,
				"family":   faith.Family,
				"source":   faith.SourceMap(),
			})
		}
		return 0, jsonout.Write(env.Stdout, map[string]any{
			"playset": database.PlaysetName,
			"command": "list-faiths",
			"filter": map[string]any{
				"match":     *match,
				"religion":  *religion,
				"doctrines": stringsOrEmpty(requested),
			},
			"faiths": items,
		})
	}
	for _, faith := range selected {
		env.Printf("%s\n", faith.Identifier)
	}
	return 0, nil
}

func runFaithsShow(env *Env) (int, error) {
	set := flagSet("faiths show", env)
	raw := set.Bool("raw", false, "print the winning definition verbatim instead of a summary")
	positional, err := parse(set, env.Args)
	if err != nil {
		return 2, nil
	}
	if len(positional) != 1 {
		return 2, fmt.Errorf("expected one faith ID, got %d", len(positional))
	}

	database, err := religionDatabase(env)
	if err != nil {
		return 1, err
	}
	faith, err := database.Faith(positional[0])
	if err != nil {
		return 1, err
	}
	sites, err := database.SelectHolySites(faith.Identifier)
	if err != nil {
		return 1, err
	}

	if env.JSON() {
		return 0, jsonout.Write(env.Stdout, map[string]any{
			"playset": database.PlaysetName,
			"command": "show-faith",
			"faith":   faithJSON(faith, sites, *raw),
		})
	}
	if *raw {
		writeRaw(env, faith.Text)
		return 0, nil
	}

	env.Printf("%s\n", faith.Identifier)
	rows := []row{
		{"religion", faith.Religion},
		{"family", faith.Family},
		{"head", faith.ReligiousHead},
	}
	rows = append(rows, sourceRows(faith.Definition)...)
	writeRows(env, "  ", rows)

	if len(faith.Doctrines) > 0 {
		env.Printf("\n  Doctrines (%d)\n", len(faith.Doctrines))
		groupWidth, idWidth := 0, 0
		for _, doctrine := range faith.Doctrines {
			if len(doctrine.Group) > groupWidth {
				groupWidth = len(doctrine.Group)
			}
			if len(doctrine.ID) > idWidth {
				idWidth = len(doctrine.ID)
			}
		}
		for _, doctrine := range faith.Doctrines {
			group := doctrine.Group
			if group == "" {
				group = "-"
			}
			env.Printf("    %-*s  %-*s  (%s)\n",
				groupWidth, group, idWidth, doctrine.ID, doctrineOrigin(doctrine))
		}
	}

	if len(sites) > 0 {
		env.Printf("\n  Holy sites (%d)\n", len(sites))
		writeHolySites(env, "    ", sites)
	}
	return 0, nil
}

// doctrineOrigin describes where a doctrine came from and whether a DLC gates it.
func doctrineOrigin(doctrine religions.Doctrine) string {
	origin := doctrine.Origin
	if doctrine.RequiresDLC == "" {
		return origin
	}
	if doctrine.Fallback {
		return origin + ", without " + doctrine.RequiresDLC
	}
	return origin + ", requires " + doctrine.RequiresDLC
}

func runFaithsHolySites(env *Env) (int, error) {
	if len(env.Args) > 1 {
		return 2, fmt.Errorf("expected at most one faith ID, got %d", len(env.Args))
	}
	faith := ""
	if len(env.Args) == 1 {
		faith = env.Args[0]
	}

	database, err := religionDatabase(env)
	if err != nil {
		return 1, err
	}
	sites, err := database.SelectHolySites(faith)
	if err != nil {
		return 1, err
	}

	if env.JSON() {
		items := make([]any, 0, len(sites))
		for _, site := range sites {
			items = append(items, holySiteJSON(site))
		}
		return 0, jsonout.Write(env.Stdout, map[string]any{
			"playset":   database.PlaysetName,
			"command":   "list-holy-sites",
			"filter":    map[string]any{"faith": faith},
			"holySites": items,
		})
	}
	writeHolySites(env, "", sites)
	return 0, nil
}

// writeHolySites prints one line per site, with its bonuses indented beneath.
func writeHolySites(env *Env, indent string, sites []religions.HolySite) {
	width := 0
	for _, site := range sites {
		if len(site.Identifier) > width {
			width = len(site.Identifier)
		}
	}
	for _, site := range sites {
		location := site.County
		if location == "" {
			location = site.Barony
		}
		if location == "" {
			location = "(undefined)"
		}
		env.Printf("%s%-*s  %s\n", indent, width, site.Identifier, location)
		for _, modifier := range site.Modifiers {
			env.Printf("%s%-*s  %s = %s\n", indent, width, "", modifier.Key, modifier.Value)
		}
		for _, parameter := range site.Parameters {
			env.Printf("%s%-*s  param %s\n", indent, width, "", parameter.Key)
		}
	}
}

func faithJSON(faith religions.Faith, sites []religions.HolySite, raw bool) map[string]any {
	doctrines := make([]any, 0, len(faith.Doctrines))
	for _, doctrine := range faith.Doctrines {
		entry := map[string]any{
			"id":     doctrine.ID,
			"group":  doctrine.Group,
			"origin": doctrine.Origin,
		}
		if doctrine.RequiresDLC != "" {
			entry["requiresDlc"] = doctrine.RequiresDLC
			entry["fallback"] = doctrine.Fallback
		}
		doctrines = append(doctrines, entry)
	}
	holySites := make([]any, 0, len(sites))
	for _, site := range sites {
		holySites = append(holySites, holySiteJSON(site))
	}

	result := map[string]any{
		"id":            faith.Identifier,
		"religion":      faith.Religion,
		"family":        faith.Family,
		"religiousHead": faith.ReligiousHead,
		"doctrines":     doctrines,
		"holySites":     holySites,
		"source":        faith.SourceMap(),
	}
	if raw {
		result["definition"] = faith.Text
	}
	return result
}

func holySiteJSON(site religions.HolySite) map[string]any {
	result := map[string]any{
		"id":         site.Identifier,
		"county":     site.County,
		"barony":     site.Barony,
		"modifiers":  pairsJSON(site.Modifiers),
		"parameters": pairsJSON(site.Parameters),
	}
	// An undefined site has no winning definition to attribute.
	if site.RelativePath != "" {
		result["source"] = site.SourceMap()
	} else {
		result["defined"] = false
	}
	return result
}

func pairsJSON(pairs []gamedata.Pair) map[string]any {
	result := map[string]any{}
	for _, pair := range pairs {
		result[pair.Key] = strings.Trim(pair.Value, `"`)
	}
	return result
}
