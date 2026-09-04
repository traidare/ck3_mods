package validate

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// sample is one finding of each shape ck3-tiger --consolidate emits: a plain
// one, one whose extra locations were folded away, and one followed by the
// context arrows that explain how execution reached it.
const sample = `error(missing-item): title d_turnbridge not defined in common/landed_titles/
   --> [MOD] map_data/geographical_regions/north_sans_neck.txt
886 |         d_turnbridge
    |         ^^^^^^^^^^^^

error(missing-item): special guest priest not defined in common/activities/activity_types/
    --> [MOD] events/activities/coronation_activity/coronation_events.txt
1817 |                 exists = scope:activity.special_guest:priest
     |                                                       ^^^^^^
    --> and 1 other locations

warning(scopes): scope:province might not be available here
    --> [AGOT] common/scripted_effects/agot_effects.txt
5170 |             scope:province = {
     |             ^^^^^^^^^^^^^^
    --> [MOD] common/activities/activity_types/coronation.txt
2276 |                 id = coronation_events.0310
     |                      ^^^^^^^^^^^^^^^^^^^^^^ <-- triggered from here

fatal: 0, error: 3, warning: 1, untidy: 0, tips: 0
`

func parseOrFail(t *testing.T, output string) []Finding {
	t.Helper()
	findings, err := ParseTiger(output)
	if err != nil {
		t.Fatalf("ParseTiger: %v", err)
	}
	return findings
}

func TestParseTigerReadsEveryFieldOfAFinding(t *testing.T) {
	findings := parseOrFail(t, sample)
	if len(findings) != 3 {
		t.Fatalf("findings = %d, want 3", len(findings))
	}
	want := Finding{
		Severity: "error",
		Code:     "missing-item",
		Message:  "special guest priest not defined in common/activities/activity_types/",
		Source:   "MOD",
		File:     "events/activities/coronation_activity/coronation_events.txt",
		Count:    2,
	}
	if findings[0] != want {
		t.Errorf("findings[0] = %+v, want %+v", findings[0], want)
	}
}

func TestParseTigerCountsConsolidatedLocations(t *testing.T) {
	findings := parseOrFail(t, sample)
	totals := tally(findings)
	// The summary line agrees, so the two folded-away locations were counted.
	if totals["error"] != 3 || totals["warning"] != 1 {
		t.Fatalf("totals = %s, want error 3 and warning 1", totals)
	}
}

func TestParseTigerTakesOnlyTheFirstLocation(t *testing.T) {
	findings := parseOrFail(t, sample)
	var warning Finding
	for _, finding := range findings {
		if finding.Severity == "warning" {
			warning = finding
		}
	}
	// The [MOD] arrow below it is the "triggered from here" context, not where
	// the finding lives.
	if warning.Source != "AGOT" {
		t.Errorf("source = %q, want AGOT", warning.Source)
	}
	if warning.File != "common/scripted_effects/agot_effects.txt" {
		t.Errorf("file = %q", warning.File)
	}
}

func TestParseTigerIgnoresLineNumbers(t *testing.T) {
	// The whole reason the baseline exists: an edit above a finding moves its
	// line number without changing the finding.
	shifted := strings.NewReplacer(
		"886 |", "912 |", "1817 |", "1900 |", "5170 |", "5233 |",
	).Replace(sample)
	if shifted == sample {
		t.Fatal("the fixture no longer contains the line numbers this test shifts")
	}
	before := parseOrFail(t, sample)
	after := parseOrFail(t, shifted)
	if CompareBaseline(Baseline{Findings: before}, after).Empty() != true {
		t.Error("shifting line numbers changed the findings")
	}
}

func TestParseTigerMergesRepeatedFindings(t *testing.T) {
	body := strings.ReplaceAll(sample,
		"fatal: 0, error: 3, warning: 1, untidy: 0, tips: 0\n", "")
	repeated := body + body + "fatal: 0, error: 6, warning: 2, untidy: 0, tips: 0\n"
	findings, err := ParseTiger(repeated)
	if err != nil {
		t.Fatalf("ParseTiger: %v", err)
	}
	if len(findings) != 3 {
		t.Fatalf("findings = %d, want the same 3 keys merged", len(findings))
	}
	if totals := tally(findings); totals["error"] != 6 || totals["warning"] != 2 {
		t.Errorf("totals = %s, want doubled counts", totals)
	}
}

func TestParseTigerRejectsOutputItsSummaryDisagreesWith(t *testing.T) {
	// A parser that silently under-counts would record an empty baseline and
	// then accept everything, so a disagreement has to be an error.
	broken := strings.Replace(sample,
		"fatal: 0, error: 3, warning: 1, untidy: 0, tips: 0",
		"fatal: 0, error: 4, warning: 1, untidy: 0, tips: 0", 1)
	_, err := ParseTiger(broken)
	if err == nil {
		t.Fatal("expected an error when the summary disagrees")
	}
	if !strings.Contains(err.Error(), "summary") {
		t.Errorf("error = %v", err)
	}
}

func TestParseTigerRejectsFindingsWithoutASummary(t *testing.T) {
	truncated := strings.Replace(sample,
		"fatal: 0, error: 3, warning: 1, untidy: 0, tips: 0\n", "", 1)
	if _, err := ParseTiger(truncated); err == nil {
		t.Fatal("expected an error when the summary is missing")
	}
}

func TestParseTigerAcceptsEmptyOutput(t *testing.T) {
	findings, err := ParseTiger("")
	if err != nil {
		t.Fatalf("ParseTiger: %v", err)
	}
	if len(findings) != 0 {
		t.Fatalf("findings = %d, want none", len(findings))
	}
}

func TestParseTigerDoesNotTakeTheSummaryForAFatal(t *testing.T) {
	// `fatal: 0, error: ...` matches the codeless finding header too, and a
	// baseline that recorded it would carry a permanent phantom fatal.
	findings := parseOrFail(t, sample)
	for _, finding := range findings {
		if finding.Severity == "fatal" {
			t.Fatalf("summary line parsed as a finding: %+v", finding)
		}
	}
}

func TestParseTigerSortsWorstFirst(t *testing.T) {
	findings := parseOrFail(t, sample)
	ranks := make([]int, len(findings))
	for index, finding := range findings {
		ranks[index] = severityRank(finding.Severity)
	}
	for index := 1; index < len(ranks); index++ {
		if ranks[index-1] > ranks[index] {
			t.Fatalf("severity ranks out of order: %v", ranks)
		}
	}
}

func TestCompareBaselineReportsNewAndResolved(t *testing.T) {
	kept := Finding{Severity: "error", Message: "kept", File: "a.txt", Count: 1}
	gone := Finding{Severity: "warning", Message: "gone", File: "b.txt", Count: 1}
	fresh := Finding{Severity: "error", Message: "fresh", File: "c.txt", Count: 1}

	delta := CompareBaseline(
		Baseline{Findings: []Finding{kept, gone}},
		[]Finding{kept, fresh},
	)
	if len(delta.New) != 1 || delta.New[0].Finding.Message != "fresh" {
		t.Errorf("new = %+v", delta.New)
	}
	if len(delta.Resolved) != 1 || delta.Resolved[0].Finding.Message != "gone" {
		t.Errorf("resolved = %+v", delta.Resolved)
	}
}

func TestCompareBaselineReportsOnlyTheAmountACountMoved(t *testing.T) {
	recorded := Finding{Severity: "error", Message: "same", File: "a.txt", Count: 3}
	grown := recorded
	grown.Count = 5

	delta := CompareBaseline(Baseline{Findings: []Finding{recorded}}, []Finding{grown})
	if len(delta.New) != 1 || len(delta.Resolved) != 0 {
		t.Fatalf("delta = %+v", delta)
	}
	if delta.New[0].Finding.Count != 2 || delta.New[0].Recorded != 3 {
		t.Errorf("change = %+v, want 2 more over a baseline of 3", delta.New[0])
	}

	shrunk := recorded
	shrunk.Count = 1
	delta = CompareBaseline(Baseline{Findings: []Finding{recorded}}, []Finding{shrunk})
	if len(delta.Resolved) != 1 || delta.Resolved[0].Finding.Count != 2 {
		t.Errorf("delta = %+v, want 2 resolved", delta)
	}
}

func TestCompareBaselineIsEmptyWhenNothingMoved(t *testing.T) {
	findings := parseOrFail(t, sample)
	if !CompareBaseline(Baseline{Findings: findings}, findings).Empty() {
		t.Error("a run compared against itself reported a delta")
	}
}

func TestBaselineRoundTrips(t *testing.T) {
	path := filepath.Join(t.TempDir(), BaselineFileName)
	findings := parseOrFail(t, sample)
	if err := SaveBaseline(path, findings); err != nil {
		t.Fatalf("SaveBaseline: %v", err)
	}
	loaded, err := LoadBaseline(path)
	if err != nil {
		t.Fatalf("LoadBaseline: %v", err)
	}
	if !CompareBaseline(loaded, findings).Empty() {
		t.Error("the baseline did not survive a round trip")
	}
}

func TestLoadBaselineTreatsAMissingFileAsEmpty(t *testing.T) {
	baseline, err := LoadBaseline(filepath.Join(t.TempDir(), BaselineFileName))
	if err != nil {
		t.Fatalf("LoadBaseline: %v", err)
	}
	if len(baseline.Findings) != 0 {
		t.Fatalf("findings = %d, want none", len(baseline.Findings))
	}
	// Nothing recorded means everything is reported, never anything accepted.
	findings := parseOrFail(t, sample)
	delta := CompareBaseline(baseline, findings)
	if reported := len(delta.New) + len(delta.Unstable); reported != len(findings) {
		t.Errorf("reported = %d, want all %d", reported, len(findings))
	}
}

func TestLoadBaselineRejectsAnUnknownSchemaVersion(t *testing.T) {
	path := filepath.Join(t.TempDir(), BaselineFileName)
	if err := os.WriteFile(path, []byte(`{"schemaVersion":99,"findings":[]}`), 0o644); err != nil {
		t.Fatal(err)
	}
	if _, err := LoadBaseline(path); err == nil {
		t.Fatal("expected an error for an unknown schema version")
	}
}

func TestSaveBaselineRemovesTheFileForACleanModule(t *testing.T) {
	path := filepath.Join(t.TempDir(), BaselineFileName)
	if err := SaveBaseline(path, parseOrFail(t, sample)); err != nil {
		t.Fatal(err)
	}
	if err := SaveBaseline(path, nil); err != nil {
		t.Fatalf("SaveBaseline: %v", err)
	}
	if _, err := os.Stat(path); !os.IsNotExist(err) {
		t.Errorf("stat = %v, want the baseline removed", err)
	}
}

// scopeFinding is one of the checks ck3-tiger does not report reproducibly.
func scopeFinding(count int) Finding {
	return Finding{Severity: "warning", Code: "scopes", Message: "deduced something",
		Source: "AGOT", File: "common/scripted_triggers/00_artifact_triggers.txt",
		Count: count}
}

func TestCompareBaselineDoesNotFailOnUnreproducibleChecks(t *testing.T) {
	recorded := Baseline{Findings: []Finding{scopeFinding(2)}}
	delta := CompareBaseline(recorded, []Finding{scopeFinding(4)})
	if len(delta.New) != 0 {
		t.Errorf("new = %+v, want an inference finding kept out of the failing set", delta.New)
	}
	if len(delta.Unstable) != 1 || delta.Unstable[0].Finding.Count != 2 {
		t.Errorf("unstable = %+v, want the growth of 2", delta.Unstable)
	}
	if delta.Regressed() {
		t.Error("growth in an unreproducible check failed validation")
	}
}

func TestCompareBaselineIgnoresUnreproducibleChecksThatShrank(t *testing.T) {
	recorded := Baseline{Findings: []Finding{scopeFinding(4)}}
	for name, current := range map[string][]Finding{
		"fewer occurrences": {scopeFinding(1)},
		"gone entirely":     nil,
	} {
		if delta := CompareBaseline(recorded, current); !delta.Empty() {
			t.Errorf("%s: delta = %+v, want silence", name, delta)
		}
	}
}

func TestCompareBaselineStillFailsOnReproducibleChecks(t *testing.T) {
	finding := Finding{Severity: "error", Code: "missing-item", Message: "m",
		Source: "MOD", File: "a.txt", Count: 1}
	delta := CompareBaseline(Baseline{}, []Finding{finding})
	if !delta.Regressed() || len(delta.New) != 1 {
		t.Errorf("delta = %+v, want a failing regression", delta)
	}
}

func TestMergeBaselineHoldsUnreproducibleChecksAtTheirHighWaterMark(t *testing.T) {
	stable := Finding{Severity: "error", Code: "missing-item", Message: "m",
		Source: "MOD", File: "a.txt", Count: 3}
	recorded := Baseline{Findings: []Finding{scopeFinding(4), stable}}

	lower := stable
	lower.Count = 1
	merged := MergeBaseline(recorded, []Finding{scopeFinding(2), lower})

	byKey := map[Finding]int{}
	for _, finding := range merged {
		byKey[finding.key()] = finding.Count
	}
	if got := byKey[scopeFinding(0).key()]; got != 4 {
		t.Errorf("inference count = %d, want the recorded high-water mark 4", got)
	}
	// A reproducible check that genuinely shrank is recorded as it is, so the
	// baseline does not accumulate findings that are actually gone.
	if got := byKey[stable.key()]; got != 1 {
		t.Errorf("stable count = %d, want the current 1", got)
	}
}

func TestMergeBaselineSettlesAfterOneRefresh(t *testing.T) {
	// The property that makes the report go quiet: refreshing on a run that saw
	// more, then validating on a run that saw fewer, reports nothing.
	recorded := Baseline{Findings: MergeBaseline(Baseline{}, []Finding{scopeFinding(2)})}
	recorded.Findings = MergeBaseline(recorded, []Finding{scopeFinding(5)})
	for _, count := range []int{5, 4, 2} {
		if delta := CompareBaseline(recorded, []Finding{scopeFinding(count)}); !delta.Empty() {
			t.Errorf("count %d: delta = %+v, want silence", count, delta)
		}
	}
}

func TestChangeDetailDistinguishesGrowthFromArrival(t *testing.T) {
	finding := Finding{Severity: "error", Code: "scopes", Message: "m",
		Source: "MOD", File: "a.txt", Count: 2}
	arrived := changeDetail("+", Change{Finding: finding})
	if !strings.Contains(arrived, "2 occurrences") {
		t.Errorf("arrived = %q", arrived)
	}
	grew := changeDetail("+", Change{Finding: finding, Recorded: 3})
	if !strings.Contains(grew, "+2, baseline 3") {
		t.Errorf("grew = %q", grew)
	}
	if !strings.Contains(arrived, "error(scopes) [MOD] a.txt: m") {
		t.Errorf("label = %q", arrived)
	}
}
