package cli

import (
	"fmt"

	"codeberg.org/traidare/ck3_mods/internal/jsonout"
)

func traditionsCommand() *Command {
	return &Command{
		Name:    "traditions",
		Summary: "Inspect the playset's effective culture traditions",
		Children: []*Command{
			{
				Name:    "list",
				Summary: "List effective tradition definitions",
				Usage:   "ck3mm traditions list [--culture ID]",
				Run:     runTraditionsList,
			},
			{
				Name:    "show",
				Summary: "Print one tradition's effective definition",
				Usage:   "ck3mm traditions show TRADITION [--raw]",
				Run:     runTraditionsShow,
			},
		},
	}
}

func runTraditionsList(env *Env) (int, error) {
	set := flagSet("traditions list", env)
	culture := set.String("culture", "", "only include the traditions this culture holds")
	positional, err := parse(set, env.Args)
	if err != nil {
		return 2, nil
	}
	if len(positional) > 0 {
		return 2, fmt.Errorf("unexpected argument %q", positional[0])
	}

	database, err := cultureDatabase(env)
	if err != nil {
		return 1, err
	}
	selected, err := database.SelectTraditions(*culture)
	if err != nil {
		return 1, err
	}

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
			"filter":     map[string]any{"culture": *culture},
			"traditions": items,
		})
	}
	for _, definition := range selected {
		env.Printf("%s\n", definition.Identifier)
	}
	return 0, nil
}

func runTraditionsShow(env *Env) (int, error) {
	set := flagSet("traditions show", env)
	raw := set.Bool("raw", false, "print the winning definition verbatim instead of a summary")
	positional, err := parse(set, env.Args)
	if err != nil {
		return 2, nil
	}
	if len(positional) != 1 {
		return 2, fmt.Errorf("expected one tradition ID, got %d", len(positional))
	}

	database, err := cultureDatabase(env)
	if err != nil {
		return 1, err
	}
	definition, err := database.Tradition(positional[0])
	if err != nil {
		return 1, err
	}

	if env.JSON() {
		tradition := map[string]any{
			"id":     definition.Identifier,
			"source": definition.SourceMap(),
		}
		// A tradition is a rules block rather than a record of fields, so the
		// summary and the raw form carry the same payload.
		tradition["definition"] = definition.Text
		return 0, jsonout.Write(env.Stdout, map[string]any{
			"playset":   database.PlaysetName,
			"command":   "show-tradition",
			"tradition": tradition,
		})
	}
	if !*raw {
		env.Printf("%s\n", definition.Identifier)
		writeRows(env, "  ", sourceRows(definition))
		env.Printf("\n")
	}
	writeRaw(env, definition.Text)
	return 0, nil
}
