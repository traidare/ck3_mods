package cli

import (
	"fmt"
	"strings"

	"codeberg.org/traidare/ck3_mods/internal/cultures"
	"codeberg.org/traidare/ck3_mods/internal/jsonout"
)

func culturesCommand() *Command {
	return &Command{
		Name:    "cultures",
		Summary: "Inspect the playset's effective culture data",
		Children: []*Command{
			{
				Name:    "list",
				Summary: "List effective cultures",
				Usage:   "ck3mm cultures list [--tradition ID]... [--match all|any] [--heritage ID] [--with-traditions]",
				Run:     runCulturesList,
			},
			{
				Name:    "show",
				Summary: "Print one culture's effective definition",
				Usage:   "ck3mm cultures show CULTURE [--raw]",
				Run:     runCulturesShow,
			},
		},
	}
}

// cultureDatabase resolves the playset and parses its culture data.
func cultureDatabase(env *Env) (cultures.Database, error) {
	if err := requireGameDirs(env); err != nil {
		return cultures.Database{}, err
	}
	database, err := cultures.Load(
		env.Config.GameDir,
		env.Config.WorkshopDir,
		env.Config.ParadoxDir,
		env.Config.LauncherDB(),
		"",
		env.Config.PlaysetName,
	)
	if err != nil {
		return cultures.Database{}, err
	}
	reportWarnings(env, database.Warnings)
	return database, nil
}

func runCulturesList(env *Env) (int, error) {
	set := flagSet("cultures list", env)
	var requested stringList
	set.Var(&requested, "tradition", "only include cultures with this tradition; repeatable")
	match := set.String("match", "all", "how repeated --tradition filters combine: all or any")
	heritage := set.String("heritage", "", "only include cultures with this heritage pillar")
	withTraditions := set.Bool("with-traditions", false, "include each culture's assigned traditions")
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

	database, err := cultureDatabase(env)
	if err != nil {
		return 1, err
	}
	selected, err := database.SelectCultures(requested, *match == "all", *heritage)
	if err != nil {
		return 1, err
	}

	if env.JSON() {
		items := make([]any, 0, len(selected))
		for _, culture := range selected {
			item := map[string]any{
				"id":       culture.Identifier,
				"heritage": culture.Pillar("heritage"),
				"source":   culture.SourceMap(),
			}
			if *withTraditions {
				item["traditions"] = stringsOrEmpty(culture.Traditions)
			}
			items = append(items, item)
		}
		return 0, jsonout.Write(env.Stdout, map[string]any{
			"playset": database.PlaysetName,
			"command": "list-cultures",
			"filter": map[string]any{
				"match":      *match,
				"traditions": stringsOrEmpty(requested),
				"heritage":   *heritage,
			},
			"cultures": items,
		})
	}

	for _, culture := range selected {
		if *withTraditions {
			env.Printf("%s: %s\n", culture.Identifier, strings.Join(culture.Traditions, ", "))
			continue
		}
		env.Printf("%s\n", culture.Identifier)
	}
	return 0, nil
}

func runCulturesShow(env *Env) (int, error) {
	set := flagSet("cultures show", env)
	raw := set.Bool("raw", false, "print the winning definition verbatim instead of a summary")
	positional, err := parse(set, env.Args)
	if err != nil {
		return 2, nil
	}
	if len(positional) != 1 {
		return 2, fmt.Errorf("expected one culture ID, got %d", len(positional))
	}

	database, err := cultureDatabase(env)
	if err != nil {
		return 1, err
	}
	culture, err := database.Culture(positional[0])
	if err != nil {
		return 1, err
	}

	if env.JSON() {
		return 0, jsonout.Write(env.Stdout, map[string]any{
			"playset": database.PlaysetName,
			"command": "show-culture",
			"culture": cultureJSON(culture, *raw),
		})
	}
	if *raw {
		writeRaw(env, culture.Text)
		return 0, nil
	}

	env.Printf("%s\n", culture.Identifier)
	rows := make([]row, 0, len(culture.Pillars)+6)
	for _, pillar := range culture.Pillars {
		rows = append(rows, row{pillar.Type, pillar.ID})
	}
	for _, pillar := range culture.FallbackPillars {
		value := pillar.ID + " (without " + pillar.RequiresDLC + ")"
		rows = append(rows, row{pillar.Type + " fallback", value})
	}
	rows = append(rows,
		row{"created", culture.Created},
		row{"parents", strings.Join(culture.Parents, ", ")},
		row{"name_list", strings.Join(culture.NameLists, ", ")},
	)
	rows = append(rows, sourceRows(culture.Definition)...)
	writeRows(env, "  ", rows)

	if len(culture.Traditions) > 0 {
		dlc := map[string]cultures.DLCTradition{}
		for _, entry := range culture.DLCTraditions {
			dlc[entry.Tradition] = entry
		}
		env.Printf("\n  Traditions (%d)\n", len(culture.Traditions))
		for _, tradition := range culture.Traditions {
			entry, gated := dlc[tradition]
			if !gated {
				env.Printf("    %s\n", tradition)
				continue
			}
			suffix := "requires " + entry.RequiresDLC
			if entry.Fallback != "" {
				suffix += ", else " + entry.Fallback
			}
			env.Printf("    %s (%s)\n", tradition, suffix)
		}
	}
	return 0, nil
}

func cultureJSON(culture cultures.Culture, raw bool) map[string]any {
	pillars := map[string]any{}
	for _, pillar := range culture.Pillars {
		pillars[pillar.Type] = pillar.ID
	}
	fallbacks := make([]any, 0, len(culture.FallbackPillars))
	for _, pillar := range culture.FallbackPillars {
		fallbacks = append(fallbacks, map[string]any{
			"type":        pillar.Type,
			"id":          pillar.ID,
			"requiresDlc": pillar.RequiresDLC,
		})
	}
	dlcTraditions := make([]any, 0, len(culture.DLCTraditions))
	for _, entry := range culture.DLCTraditions {
		dlcTraditions = append(dlcTraditions, map[string]any{
			"tradition":   entry.Tradition,
			"requiresDlc": entry.RequiresDLC,
			"fallback":    entry.Fallback,
		})
	}

	result := map[string]any{
		"id":              culture.Identifier,
		"pillars":         pillars,
		"fallbackPillars": fallbacks,
		"created":         culture.Created,
		"parents":         stringsOrEmpty(culture.Parents),
		"nameLists":       stringsOrEmpty(culture.NameLists),
		"traditions":      stringsOrEmpty(culture.Traditions),
		"dlcTraditions":   dlcTraditions,
		"source":          culture.SourceMap(),
	}
	if raw {
		result["definition"] = culture.Text
	}
	return result
}
