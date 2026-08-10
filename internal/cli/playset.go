package cli

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"codeberg.org/traidare/ck3_mods/internal/config"
	"codeberg.org/traidare/ck3_mods/internal/jsonout"
	"codeberg.org/traidare/ck3_mods/internal/playset"
	"codeberg.org/traidare/ck3_mods/internal/preserve"
)

func playsetCommand() *Command {
	return &Command{
		Name:    "playset",
		Summary: "Read and compare Launcher playsets",
		Children: []*Command{
			{
				Name:    "summary",
				Summary: "Show the selected playset's composition",
				Usage:   "ck3mm playset summary [name]",
				Run:     runPlaysetSummary,
			},
			{
				Name:    "export",
				Summary: "Write the selected playset as portable JSON",
				Usage:   "ck3mm playset export [name] [--output FILE]",
				Run:     runPlaysetExport,
			},
			{
				Name:    "import",
				Summary: "Preview or write an exported playset into the Launcher",
				Usage:   "ck3mm playset import FILE [--allow-missing] [--apply]",
				Run:     runPlaysetImport,
			},
			{
				Name:    "preserve",
				Summary: "Preview or write an update-proof copy of a playset",
				Usage:   "ck3mm playset preserve [name] [--snapshot-name NAME] [--apply]",
				Run:     runPlaysetPreserve,
			},
			{
				Name:    "diff",
				Summary: "Compare two exported playsets",
				Usage:   "ck3mm playset diff BEFORE AFTER",
				Run:     runPlaysetDiff,
			},
		},
	}
}

// livePlayset loads the playset the global selection order picks out.
func livePlayset(env *Env, name string) (playset.Playset, error) {
	if err := env.Config.Require(config.ParadoxDir); err != nil {
		return playset.Playset{}, err
	}
	return playset.LoadLive(env.Config.LauncherDB(), name, env.Config.PlaysetName)
}

func positionalName(env *Env) (string, error) {
	switch len(env.Args) {
	case 0:
		return "", nil
	case 1:
		return env.Args[0], nil
	default:
		return "", fmt.Errorf("expected at most one playset name, got %d", len(env.Args))
	}
}

func runPlaysetSummary(env *Env) (int, error) {
	name, err := positionalName(env)
	if err != nil {
		return 2, err
	}
	source, err := livePlayset(env, name)
	if err != nil {
		return 1, err
	}
	summary := playset.Summary(source)

	if env.JSON() {
		if err := jsonout.Write(env.Stdout, summary); err != nil {
			return 1, err
		}
		return 0, nil
	}
	env.Printf("Playset: %v\n", summary["name"])
	env.Printf("Selection: %v\n", summary["selectionSource"])
	env.Printf("Mods: %v enabled / %v total\n", summary["enabled"], summary["total"])
	env.Printf("Local: %v\n", summary["local"])
	env.Printf("Workshop: %v\n", summary["workshop"])
	return 0, nil
}

func runPlaysetExport(env *Env) (int, error) {
	set := flagSet("playset export", env)
	output := set.String("output", "", "write the export to this file instead of stdout")
	positional, err := parse(set, env.Args)
	if err != nil {
		return 2, err
	}
	env.Args = positional

	name, err := positionalName(env)
	if err != nil {
		return 2, err
	}
	source, err := livePlayset(env, name)
	if err != nil {
		return 1, err
	}
	content, err := playset.Dump(source)
	if err != nil {
		return 1, err
	}

	if *output == "" {
		env.Printf("%s", content)
		return 0, nil
	}
	if err := os.WriteFile(*output, []byte(content), 0o644); err != nil {
		return 1, err
	}
	env.Printf("exported playset to %s\n", *output)
	return 0, nil
}

func runPlaysetDiff(env *Env) (int, error) {
	if len(env.Args) != 2 {
		return 2, fmt.Errorf("expected two playset files, got %d", len(env.Args))
	}
	before, err := playset.LoadFile(env.Args[0])
	if err != nil {
		return 1, err
	}
	after, err := playset.LoadFile(env.Args[1])
	if err != nil {
		return 1, err
	}
	diff, err := playset.Compare(before, after)
	if err != nil {
		return 1, err
	}

	if env.JSON() {
		if err := jsonout.Write(env.Stdout, diff.ToMap()); err != nil {
			return 1, err
		}
	} else {
		env.Printf("Playsets: %s -> %s\n", diff.BeforeName, diff.AfterName)
		for _, section := range []struct {
			label string
			mods  []playset.Mod
		}{{"Added", diff.Added}, {"Removed", diff.Removed}} {
			env.Printf("%s: %d\n", section.label, len(section.mods))
			for _, mod := range section.mods {
				env.Printf("  %s (%s)\n", mod.StableID(), mod.DisplayName)
			}
		}
		env.Printf("Changed: %d\n", len(diff.Changed))
		for _, change := range diff.Changed {
			env.Printf("  %s (%s)\n", change.StableID, change.After.DisplayName)
		}
	}
	if diff.Current() {
		return 0, nil
	}
	return 1, nil
}

func runPlaysetPreserve(env *Env) (int, error) {
	set := flagSet("playset preserve", env)
	snapshotName := set.String("snapshot-name", "", "name the snapshot instead of deriving one")
	positional, err := parse(set, env.Args)
	if err != nil {
		return 2, nil
	}
	env.Args = positional
	name, err := positionalName(env)
	if err != nil {
		return 2, err
	}
	if set.Lookup("snapshot-name").Value.String() != "" && strings.TrimSpace(*snapshotName) == "" {
		return 2, fmt.Errorf("snapshot name cannot be empty")
	}
	if err := env.Config.Require(config.ParadoxDir, config.WorkshopDir); err != nil {
		return 2, err
	}

	plan, err := preserve.Build(preserve.Options{
		DatabasePath:      env.Config.LauncherDB(),
		ModDirectory:      filepath.Join(env.Config.ParadoxDir, "mod"),
		WorkshopDirectory: env.Config.WorkshopDir,
		PlaysetName:       name,
		ConfiguredName:    env.Config.PlaysetName,
		SnapshotName:      *snapshotName,
	})
	if err != nil {
		return 1, err
	}

	var result preserve.Result
	if env.Apply {
		if result, err = plan.Apply(); err != nil {
			return 1, err
		}
	}

	if env.JSON() {
		document := plan.ToMap()
		if env.Apply {
			document["playsetId"] = result.PlaysetID
			document["backupPath"] = result.BackupPath
		}
		if err := jsonout.Write(env.Stdout, document); err != nil {
			return 1, err
		}
		return 0, nil
	}

	state := "preview"
	if env.Apply {
		state = "applied"
	}
	env.Printf("Preserve %s: %q -> %q\n", state, plan.SourcePlaysetName, plan.SnapshotName)
	env.Printf("  Selection: %s\n", plan.SelectionSource)
	env.Printf("  Directory: %s\n", plan.FinalRoot)
	env.Printf("  Enabled mods: %d\n", len(plan.Mods))
	env.Printf("  Content: %d bytes\n", plan.ContentBytes())
	env.Printf("  Space: %d bytes required, %d free\n", plan.RequiredBytes, plan.FreeBytes)
	if env.Apply {
		env.Printf("  Playset: %s\n", result.PlaysetID)
		env.Printf("  Backup: %s\n", result.BackupPath)
	}
	return 0, nil
}

func runPlaysetImport(env *Env) (int, error) {
	set := flagSet("playset import", env)
	allowMissing := set.Bool("allow-missing", false, "import without the mods that could not be matched")
	positional, err := parse(set, env.Args)
	if err != nil {
		return 2, nil
	}
	if len(positional) != 1 {
		return 2, fmt.Errorf("expected one exported playset file, got %d", len(positional))
	}
	if err := env.Config.Require(config.ParadoxDir); err != nil {
		return 2, err
	}

	source, err := playset.LoadFile(positional[0])
	if err != nil {
		return 1, err
	}

	var plan playset.ImportPlan
	if env.Apply {
		plan, err = playset.ApplyImport(env.Config.LauncherDB(), source, *allowMissing)
	} else {
		plan, err = playset.PlanImport(env.Config.LauncherDB(), source)
	}
	if err != nil {
		return 1, err
	}

	if env.JSON() {
		if err := jsonout.Write(env.Stdout, plan.ToMap()); err != nil {
			return 1, err
		}
		return 0, nil
	}
	state := "preview"
	if env.Apply {
		state = "applied"
	}
	env.Printf("Import %s: %s %q\n", state, plan.Action, plan.Name)
	env.Printf("  Resolved: %d\n", len(plan.Resolved))
	env.Printf("  Unresolved: %d\n", len(plan.Unresolved))
	for _, mod := range plan.Unresolved {
		env.Printf("    %s: %s\n", mod.DisplayName, mod.Reason)
	}
	if plan.BackupPath != "" {
		env.Printf("  Backup: %s\n", plan.BackupPath)
	}
	return 0, nil
}
