package cli

import (
	"fmt"
	"strings"

	"codeberg.org/traidare/ck3_mods/internal/config"
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
				Usage:   "ck3mm cultures list [--tradition ID]... [--match all|any] [--with-traditions]",
				Run:     runCulturesList,
			},
			{
				Name:    "traditions",
				Summary: "List effective tradition definitions",
				Usage:   "ck3mm cultures traditions",
				Run:     runCulturesTraditions,
			},
			{
				Name:    "show",
				Summary: "Print one tradition's effective definition",
				Usage:   "ck3mm cultures show TRADITION",
				Run:     runCulturesShow,
			},
		},
	}
}

// cultureDatabase resolves the playset and parses its culture data. Warnings
// from load-order resolution go to stderr so stdout stays machine-readable.
func cultureDatabase(env *Env, playsetName string) (cultures.Database, error) {
	if err := env.Config.Require(config.GameDir, config.WorkshopDir, config.ParadoxDir); err != nil {
		return cultures.Database{}, err
	}
	database, err := cultures.Load(
		env.Config.GameDir,
		env.Config.WorkshopDir,
		env.Config.ParadoxDir,
		env.Config.LauncherDB(),
		playsetName,
		env.Config.PlaysetName,
	)
	if err != nil {
		return cultures.Database{}, err
	}
	for _, warning := range database.Warnings {
		fmt.Fprintf(env.Stderr, "warning: %s: %s\n", warning.Code, warning.Message)
	}
	return database, nil
}

func runCulturesList(env *Env) (int, error) {
	set := flagSet("cultures list", env)
	var requested stringList
	set.Var(&requested, "tradition", "only include cultures with this tradition; repeatable")
	match := set.String("match", "all", "how repeated --tradition filters combine: all or any")
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

	database, err := cultureDatabase(env, "")
	if err != nil {
		return 1, err
	}
	selected, err := database.SelectCultures(requested, *match == "all")
	if err != nil {
		return 1, err
	}

	if env.JSON() {
		items := make([]any, 0, len(selected))
		for _, definition := range selected {
			item := map[string]any{
				"id":     definition.Identifier,
				"source": definition.SourceMap(),
			}
			if *withTraditions {
				traditions := definition.Traditions
				if traditions == nil {
					traditions = []string{}
				}
				item["traditions"] = traditions
			}
			items = append(items, item)
		}
		filter := map[string]any{"match": *match, "traditions": []string(requested)}
		if requested == nil {
			filter["traditions"] = []string{}
		}
		return 0, jsonout.Write(env.Stdout, map[string]any{
			"playset":  database.PlaysetName,
			"command":  "list-cultures",
			"filter":   filter,
			"cultures": items,
		})
	}

	for _, definition := range selected {
		if *withTraditions {
			env.Printf("%s: %s\n", definition.Identifier, strings.Join(definition.Traditions, ", "))
			continue
		}
		env.Printf("%s\n", definition.Identifier)
	}
	return 0, nil
}

func runCulturesTraditions(env *Env) (int, error) {
	if len(env.Args) > 0 {
		return 2, fmt.Errorf("unexpected argument %q", env.Args[0])
	}
	database, err := cultureDatabase(env, "")
	if err != nil {
		return 1, err
	}
	selected := database.SelectTraditions()

	if env.JSON() {
		items := make([]any, 0, len(selected))
		for _, definition := range selected {
			items = append(items, map[string]any{
				"id":     definition.Identifier,
				"source": definition.SourceMap(),
			})
		}
		return 0, jsonout.Write(env.Stdout, map[string]any{
			"playset":    database.PlaysetName,
			"command":    "list-traditions",
			"traditions": items,
		})
	}
	for _, definition := range selected {
		env.Printf("%s\n", definition.Identifier)
	}
	return 0, nil
}

func runCulturesShow(env *Env) (int, error) {
	if len(env.Args) != 1 {
		return 2, fmt.Errorf("expected one tradition ID, got %d", len(env.Args))
	}
	database, err := cultureDatabase(env, "")
	if err != nil {
		return 1, err
	}
	definition, err := database.Tradition(env.Args[0])
	if err != nil {
		return 1, err
	}

	if env.JSON() {
		return 0, jsonout.Write(env.Stdout, map[string]any{
			"playset": database.PlaysetName,
			"command": "show-tradition",
			"tradition": map[string]any{
				"id":         definition.Identifier,
				"definition": definition.Text,
				"source":     definition.SourceMap(),
			},
		})
	}
	env.Printf("%s", definition.Text)
	if !strings.HasSuffix(definition.Text, "\n") {
		env.Printf("\n")
	}
	return 0, nil
}
