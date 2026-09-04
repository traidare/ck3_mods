package report

import (
	"strings"
	"testing"
)

func TestRenderTextLabelsProvidersByNameAndSelector(t *testing.T) {
	source := Report{
		Mods: []ModRecord{
			{StableID: "local:mod/ugc_3766038754.mod", SteamID: "3766038754", Name: "Seasons of Valyria", Position: 134},
			{StableID: "local:mod/lore_governments.mod", Name: "Lore Governments", Position: 8},
		},
		Files: []FileEntry{{
			Path:          "events/lov_season_events.txt",
			ConflictKinds: []string{"same_path"},
			Providers: []FileProvider{
				{ModID: "local:mod/lore_governments.mod", Position: 8},
				{ModID: "local:mod/ugc_3766038754.mod", Position: 134},
			},
			EffectiveState: "present",
		}},
	}

	rendered := RenderText(source)
	for _, want := range []string{
		// The Workshop ID identifies a subscribed mod; a local-only mod falls
		// back to its registry name. Positions are right-aligned.
		"    [  8] Lore Governments (lore_governments)",
		"    [134] Seasons of Valyria (3766038754)",
	} {
		if !strings.Contains(rendered, want) {
			t.Errorf("missing line %q in:\n%s", want, rendered)
		}
	}
}

// shadowedReport pairs two providers on one divergent file and has a third mod
// bury a second file by replace_path.
func shadowedReport() Report {
	return Report{
		Mods: []ModRecord{
			{StableID: "local:mod/agot.mod", SteamID: "2962333032", Name: "AGOT", Position: 3},
			{StableID: "local:mod/essos.mod", SteamID: "2887408083", Name: "Essos Expanded", Position: 1},
			{StableID: "local:mod/compatch.mod", Name: "Compatch", Position: 9},
		},
		Files: []FileEntry{{
			Path:          "common/traits/00_traits.txt",
			ConflictKinds: []string{"same_path"},
			Providers: []FileProvider{
				{ModID: "local:mod/essos.mod", Position: 1},
				{ModID: "local:mod/agot.mod", Position: 3},
			},
			ContentStatus:   "divergent",
			EffectiveWinner: EffectiveWinner{ModID: "local:mod/agot.mod"},
		}, {
			Path:          "history/provinces/01_north.txt",
			ConflictKinds: []string{"replace_path_shadow"},
			Providers: []FileProvider{
				{ModID: "local:mod/essos.mod", Position: 1},
			},
			ReplacePathOwners: []ReplacePathOwner{
				{ModID: "local:mod/compatch.mod", Position: 9, ReplacePaths: []string{"history/provinces"}},
			},
			EffectiveWinner: EffectiveWinner{ModID: "local:mod/compatch.mod"},
		}, {
			Path:            "events/quiet.txt",
			Providers:       []FileProvider{{ModID: "local:mod/agot.mod", Position: 3}},
			EffectiveWinner: EffectiveWinner{ModID: "local:mod/agot.mod"},
		}},
	}
}

func TestPairConflictsCountsProvidersAndReplacePathOwners(t *testing.T) {
	pairs := PairConflicts(shadowedReport().Files)
	if len(pairs) != 2 {
		t.Fatalf("got %d pairs, want one per conflicting file: %+v", len(pairs), pairs)
	}
	// The divergent same-path overlap sorts first; AGOT loads later and wins.
	first := pairs[0]
	if first.AID != "local:mod/agot.mod" || first.BID != "local:mod/essos.mod" {
		t.Fatalf("unexpected pair sides: %+v", first)
	}
	if first.Files != 1 || first.Divergent != 1 {
		t.Fatalf("unexpected tally: %+v", first)
	}
	// A replace_path owner overlaps the provider it buries even though it does
	// not physically contain the path.
	second := pairs[1]
	if second.AID != "local:mod/compatch.mod" || second.BID != "local:mod/essos.mod" {
		t.Fatalf("unexpected shadow pair sides: %+v", second)
	}
	if second.Files != 1 || second.Divergent != 0 {
		t.Fatalf("unexpected shadow tally: %+v", second)
	}
}

func TestPairConflictsIgnoresNonConflictingFiles(t *testing.T) {
	files := []FileEntry{{
		Path:      "events/quiet.txt",
		Providers: []FileProvider{{ModID: "local:mod/agot.mod"}},
	}}
	if pairs := PairConflicts(files); len(pairs) != 0 {
		t.Fatalf("expected no pairs from a single-provider file, got %+v", pairs)
	}
}

func TestModPairMapContainsOnlyPairTallies(t *testing.T) {
	payload := (ModPair{AID: "a", BID: "b", Files: 3, Divergent: 2}).ToMap()
	if len(payload) != 4 || payload["a"] != "a" || payload["b"] != "b" ||
		payload["files"] != 3 || payload["divergent"] != 2 {
		t.Fatalf("unexpected pair payload: %#v", payload)
	}
}

func TestPairsInvolvingDropsPairsWithoutTheAnchor(t *testing.T) {
	source := shadowedReport()
	pairs := PairConflicts(source.Files)
	anchored := PairsInvolving(pairs, map[string]bool{"local:mod/compatch.mod": true})
	if len(anchored) != 1 || anchored[0].AID != "local:mod/compatch.mod" {
		t.Fatalf("expected only the anchored pair, got %+v", anchored)
	}
	if got := PairsInvolving(pairs, nil); len(got) != len(pairs) {
		t.Fatalf("an empty anchor set must keep every pair, got %d", len(got))
	}
}

func TestRenderPairsGroupsByLaterLoadingMod(t *testing.T) {
	source := shadowedReport()
	rendered := RenderPairs(source, PairConflicts(source.Files))
	for _, want := range []string{
		"Mod conflicts: 2 pairs",
		"  [3] AGOT (2962333032)",
		"        files  divergent  conflicts with",
		"            1          1  [1] Essos Expanded (2887408083)",
		"  [9] Compatch (compatch)",
		"            1          0  [1] Essos Expanded (2887408083)",
	} {
		if !strings.Contains(rendered, want) {
			t.Errorf("missing line %q in:\n%s", want, rendered)
		}
	}
}

func TestRenderPairsBreaksPositionTiesByStableID(t *testing.T) {
	source := Report{Mods: []ModRecord{
		{StableID: "local:mod/a.mod", Name: "Alpha"},
		{StableID: "local:mod/b.mod", Name: "Beta"},
	}}
	pairs := []ModPair{{AID: "local:mod/a.mod", BID: "local:mod/b.mod", Files: 2}}
	rendered := RenderPairs(source, pairs)
	if !strings.Contains(rendered, "  [0] Beta (b)") ||
		!strings.Contains(rendered, "[0] Alpha (a)") {
		t.Errorf("expected Beta to be the deterministic later group:\n%s", rendered)
	}
}

func TestRenderPairsReportsAnEmptyTable(t *testing.T) {
	if !strings.Contains(RenderPairs(Report{}, nil), "Mod conflicts: 0 pairs\n  none") {
		t.Errorf("expected an explicit empty table:\n%s", RenderPairs(Report{}, nil))
	}
}

func TestRenderTextClosesWithTheSummary(t *testing.T) {
	source := shadowedReport()
	source.Warnings = []Warning{{Code: "mod_missing", Message: "gone"}}
	source.Summary = Summarize(source.Files, len(source.Mods), len(source.Files), source.Warnings)
	rendered := RenderText(source)

	warnings := strings.Index(rendered, "Warnings")
	files := strings.Index(rendered, "\nFiles")
	summary := strings.Index(rendered, "Summary")
	if warnings < 0 || files < 0 || summary < 0 {
		t.Fatalf("expected all three sections:\n%s", rendered)
	}
	if !(warnings < files && files < summary) {
		t.Errorf("expected warnings, then files, then the summary:\n%s", rendered)
	}
	if !strings.HasSuffix(rendered, "Scan scope: 3 mods, 3 provider files\n") {
		t.Errorf("expected the summary to close the report:\n%s", rendered)
	}
}

func TestSummaryLinesKeepTheNormalReportCompact(t *testing.T) {
	source := Report{Summary: Summary{
		ModsAnalyzed: 145, FilesScanned: 45776, FilesReported: 2989,
		Conflicts: 2989, SamePath: 2989, Divergent: 2799, Identical: 190,
	}}
	want := "Summary\n" +
		"  Conflicts: 2989\n" +
		"  Same path: 2989 (2799 divergent, 190 identical)\n" +
		"  Scan scope: 145 mods, 45776 provider files"
	if got := strings.Join(summaryLines(source), "\n"); got != want {
		t.Errorf("unexpected summary:\n%s", got)
	}
}

func TestSummaryLinesShowExceptionalCounts(t *testing.T) {
	source := Report{Summary: Summary{
		ModsAnalyzed: 3, ModsMissing: 1, FilesScanned: 12, FilesReported: 4,
		Conflicts: 3, SamePath: 2, ReplacePathShadow: 1,
		Divergent: 1, Unreadable: 1, EffectiveRemoved: 1,
	}}
	want := "Summary\n" +
		"  Conflicts: 3\n" +
		"  Same path: 2 (1 divergent, 1 unreadable)\n" +
		"  Replace path shadows: 1\n" +
		"  Effectively removed: 1\n" +
		"  Files reported: 4\n" +
		"  Mods missing: 1\n" +
		"  Scan scope: 3 mods, 12 provider files"
	if got := strings.Join(summaryLines(source), "\n"); got != want {
		t.Errorf("unexpected summary:\n%s", got)
	}
}

func TestRenderPairsOmitsTheSummaryAndKeepsWarnings(t *testing.T) {
	source := shadowedReport()
	source.Warnings = []Warning{{Code: "mod_missing", Message: "gone"}}
	rendered := RenderPairs(source, PairConflicts(source.Files))

	if strings.Contains(rendered, "Summary") || strings.Contains(rendered, "Files scanned") {
		t.Errorf("the pair view must not print the summary:\n%s", rendered)
	}
	// A mod that failed to resolve understates every pair below it.
	if !strings.Contains(rendered, "[mod_missing] gone") {
		t.Errorf("expected warnings to survive the compact view:\n%s", rendered)
	}
}

func TestRenderTextFallsBackToModID(t *testing.T) {
	source := Report{
		Files: []FileEntry{{
			Path:           "events/orphan.txt",
			Providers:      []FileProvider{{ModID: "local:mod/unlisted.mod", Position: 3}},
			EffectiveState: "present",
		}},
	}
	if !strings.Contains(RenderText(source), "[3] local:mod/unlisted.mod") {
		t.Errorf("expected the raw ID for a provider with no mod record:\n%s", RenderText(source))
	}
}
