package cli

import (
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
		Usage:   "ck3mm conflicts [playset] [--involving ID] [--summary-only]",
		Run:     runConflicts,
	}
}

func runConflicts(env *Env) (int, error) {
	set := flagSet("conflicts", env)
	playsetFile := set.String("playset-file", "", "analyze an exported playset instead of the live one")
	involving := set.String("involving", "", "only report files touching this mod")
	summaryOnly := set.Bool("summary-only", false, "omit the per-file section")
	allFiles := set.Bool("all-files", false, "report every scanned file, not only conflicts")
	debugPaths := set.Bool("debug-paths", false, "append the resolved provider roots")
	failOn := set.String("fail-on", "", "exit non-zero on divergent, any, or missing")
	var includePrefix, excludePrefix stringList
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
	analysis, err := conflicts.Analyze(discovery.Providers, &discovery.Playset, discovery.Warnings, *allFiles)
	if err != nil {
		return 1, err
	}
	analysis, err = conflicts.Apply(analysis, conflicts.Filter{
		Involving:       *involving,
		IncludePrefixes: includePrefix,
		ExcludePrefixes: excludePrefix,
		ConflictsOnly:   !*allFiles,
		SummaryOnly:     *summaryOnly,
	})
	if err != nil {
		return 1, err
	}

	resolvedRoots := map[string]string{}
	for _, provider := range discovery.Providers {
		resolvedRoots[provider.StableID] = provider.Root
	}

	if env.JSON() {
		payload := analysis.ToMap()
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
		env.Printf("%s", report.RenderText(analysis))
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
