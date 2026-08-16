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
		Usage:   "ck3mm conflicts [playset] [--involving ID] [--mods-only] [--summary-only]",
		Run:     runConflicts,
	}
}

// withExternalMod appends the mod a selector names when the playset does not
// enable it, so `--involving` can preview a candidate addition. A selector that
// resolves to nothing is left to the filter, which reports it with suggestions;
// its resolution failure is returned for that message.
func withExternalMod(discovery layers.Discovery, involving, workshopDir, paradoxDir string) ([]conflicts.Provider, []report.Warning, error) {
	if involving == "" {
		return discovery.Providers, discovery.Warnings, nil
	}
	for _, provider := range discovery.Providers {
		if conflicts.Selects(provider.ToRecord(), involving) {
			return discovery.Providers, discovery.Warnings, nil
		}
	}

	external, err := layers.ResolveExternal(involving, workshopDir, paradoxDir,
		layers.NextPosition(discovery.Providers))
	if err != nil {
		return discovery.Providers, discovery.Warnings, err
	}
	return append(append([]conflicts.Provider{}, discovery.Providers...), external), discovery.Warnings, nil
}

func runConflicts(env *Env) (int, error) {
	set := flagSet("conflicts", env)
	playsetFile := set.String("playset-file", "", "analyze an exported playset instead of the live one")
	involving := set.String("involving", "", "only report files touching this mod")
	summaryOnly := set.Bool("summary-only", false, "report only the summary")
	modsOnly := set.Bool("mods-only", false, "report only the mod pairs that share conflicting files")
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
	// Each --*-only flag selects one section, so asking for two is contradictory.
	if *summaryOnly && *modsOnly {
		return 2, fmt.Errorf("choose either --summary-only or --mods-only, not both")
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
	providers, warnings, externalErr := withExternalMod(discovery, *involving,
		env.Config.WorkshopDir, env.Config.ParadoxDir)

	analysis, err := conflicts.Analyze(providers, &discovery.Playset, warnings, *allFiles)
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
		// Every filter error is bad input: an unknown selector or an
		// unusable prefix. A selector naming a mod that is installed but
		// unusable needs the reason; one that matches nothing does not.
		if externalErr != nil && !errors.Is(externalErr, layers.ErrNotInstalled) {
			return 2, fmt.Errorf("%w; its installed copy could not be read: %v", err, externalErr)
		}
		return 2, err
	}

	// The pair table is derived from the filtered entries, so --mods-only keeps
	// them through the filter and drops the file section after pairing. The
	// rebuilt summary stays available for --fail-on even when no view shows it.
	var pairs []report.ModPair
	if *modsOnly {
		anchors := map[string]bool{}
		for _, mod := range analysis.Mods {
			if conflicts.Selects(mod, *involving) {
				anchors[mod.StableID] = true
			}
		}
		pairs = report.PairsInvolving(report.PairConflicts(analysis.Files), anchors)
		analysis = report.WithFiles(analysis, analysis.Files, true)
	}

	resolvedRoots := map[string]string{}
	for _, provider := range providers {
		resolvedRoots[provider.StableID] = provider.Root
	}

	if env.JSON() {
		payload := analysis.ToMap()
		// A view selects the same sections in both formats: a key a view
		// leaves out is absent, not an empty list a consumer has to interpret.
		switch {
		case *modsOnly:
			delete(payload, "summary")
			delete(payload, "files")
			rendered := make([]any, len(pairs))
			for index, pair := range pairs {
				rendered[index] = pair.ToMap()
			}
			payload["modPairs"] = rendered
		case *summaryOnly:
			delete(payload, "files")
			delete(payload, "mods")
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
		if *modsOnly {
			env.Printf("%s", report.RenderPairs(analysis, pairs))
		} else {
			env.Printf("%s", report.RenderText(analysis))
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
