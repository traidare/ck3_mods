package validate

import (
	"encoding/json"
	"fmt"
	"os"
	"regexp"
	"sort"
	"strconv"
	"strings"

	"codeberg.org/traidare/ck3_mods/internal/fsutil"
)

// BaselineFileName is the per-module record of the ck3-tiger findings already
// accepted, tracked in git so a new one lands as a reviewable diff.
const BaselineFileName = "tiger.baseline.json"

// BaselineSchemaVersion is the baseline format this package reads and writes.
const BaselineSchemaVersion = 1

// Severities are ck3-tiger's levels, worst first. Reports are ordered by this
// rank so the line worth reading is never below the line that is not.
var Severities = []string{"fatal", "error", "warning", "untidy", "tips"}

// InferenceCodes are the ck3-tiger checks whose output is not reproducible.
//
// Both deduce the type of a scope or variable from how it is used, and tiger
// visits files in parallel, so which usage wins the deduction varies between
// identical runs. Measured over three consecutive runs of two modules: the
// deduced type in the message swaps (`produces landed title` against `produces
// dynasty house`), occurrence counts drift by one or two, and roughly one
// finding per module appears in some runs and not others. Nothing outside these
// two codes moved.
//
// They are therefore held to a high-water mark rather than an exact count: a
// larger result is reported but does not fail, a smaller one is ignored, and
// --apply only ever raises the recorded count. A gate on a value that changes
// when nothing changed is not a gate.
var InferenceCodes = map[string]bool{"scopes": true, "strict-scopes": true}

var (
	// A finding header: a severity, an optional parenthesised code, a message.
	tigerHeader = regexp.MustCompile(
		`^(fatal|error|warning|untidy|tips)(?:\(([^)]*)\))?: (.*)$`)
	// The location line, tagged with the mod or game the file belongs to: the
	// same relative path exists in several of them, so the tag is part of the
	// identity of the file, not decoration.
	tigerLocation = regexp.MustCompile(`^\s*--> \[([^\]]*)\] (.+)$`)
	// What --consolidate prints instead of repeating a finding verbatim.
	tigerConsolidated = regexp.MustCompile(`^\s*--> and (\d+) other locations?$`)
	// The closing tally, which is also the only line that would otherwise parse
	// as a codeless `fatal:` finding.
	tigerSummary = regexp.MustCompile(
		`^fatal: (\d+), error: (\d+), warning: (\d+), untidy: (\d+), tips: (\d+)$`)
)

// Finding is one ck3-tiger diagnostic, identified by everything except where in
// the file it sits.
//
// Line numbers are deliberately not part of it: they shift on every unrelated
// edit above them, so a baseline that remembered them would report churn on
// every commit and hide the one finding that is genuinely new.
type Finding struct {
	Severity string `json:"severity"`
	Code     string `json:"code,omitempty"`
	Message  string `json:"message"`
	// Source is tiger's location tag: MOD for the module under validation, and
	// the display name of a parent or CK3 otherwise.
	Source string `json:"source"`
	File   string `json:"file"`
	// Count is how many places report it, including the ones --consolidate
	// folded into a single entry.
	Count int `json:"count"`
}

// key identifies a finding across runs, ignoring how often it occurred.
func (f Finding) key() Finding {
	f.Count = 0
	return f
}

// Inferred reports whether this finding comes from a check whose result is not
// reproducible between runs. See InferenceCodes.
func (f Finding) Inferred() bool {
	return InferenceCodes[f.Code]
}

// Label renders one finding for a report line.
func (f Finding) Label() string {
	severity := f.Severity
	if f.Code != "" {
		severity += "(" + f.Code + ")"
	}
	location := f.File
	if f.Source != "" {
		location = "[" + f.Source + "] " + f.File
	}
	if location == "" {
		return fmt.Sprintf("%s: %s", severity, f.Message)
	}
	return fmt.Sprintf("%s %s: %s", severity, location, f.Message)
}

func severityRank(severity string) int {
	for rank, known := range Severities {
		if known == severity {
			return rank
		}
	}
	return len(Severities)
}

// lessFinding orders findings worst-first and then deterministically, so a
// baseline diff shows what moved rather than how a map happened to iterate.
func lessFinding(a, b Finding) bool {
	if rankA, rankB := severityRank(a.Severity), severityRank(b.Severity); rankA != rankB {
		return rankA < rankB
	}
	for _, pair := range [][2]string{
		{a.Source, b.Source},
		{a.File, b.File},
		{a.Code, b.Code},
		{a.Message, b.Message},
	} {
		if pair[0] != pair[1] {
			return pair[0] < pair[1]
		}
	}
	return false
}

func sortFindings(findings []Finding) {
	sort.Slice(findings, func(left, right int) bool {
		return lessFinding(findings[left], findings[right])
	})
}

// Totals counts findings by severity.
type Totals map[string]int

// String renders the tally in ck3-tiger's own order and wording.
func (t Totals) String() string {
	parts := make([]string, len(Severities))
	for index, severity := range Severities {
		parts[index] = fmt.Sprintf("%s %d", severity, t[severity])
	}
	return strings.Join(parts, ", ")
}

func tally(findings []Finding) Totals {
	totals := Totals{}
	for _, severity := range Severities {
		totals[severity] = 0
	}
	for _, finding := range findings {
		totals[finding.Severity] += finding.Count
	}
	return totals
}

// ParseTiger turns `ck3-tiger --consolidate` output into findings.
//
// The result is cross-checked against tiger's own closing tally. That check is
// the point: if an upstream tiger release changes the report format, this fails
// loudly instead of quietly recording an empty baseline that then accepts
// everything.
func ParseTiger(output string) ([]Finding, error) {
	merged := map[Finding]int{}
	var order []Finding
	var current *Finding
	var reported Totals

	flush := func() {
		if current == nil {
			return
		}
		key := current.key()
		if _, seen := merged[key]; !seen {
			order = append(order, key)
		}
		merged[key] += current.Count
		current = nil
	}

	for _, line := range strings.Split(output, "\n") {
		line = strings.TrimRight(line, "\r")
		if match := tigerSummary.FindStringSubmatch(line); match != nil {
			flush()
			reported = Totals{}
			for index, severity := range Severities {
				count, err := strconv.Atoi(match[index+1])
				if err != nil {
					return nil, fmt.Errorf("unreadable ck3-tiger summary: %s", line)
				}
				reported[severity] = count
			}
			continue
		}
		if match := tigerHeader.FindStringSubmatch(line); match != nil {
			flush()
			current = &Finding{
				Severity: match[1],
				Code:     match[2],
				Message:  match[3],
				Count:    1,
			}
			continue
		}
		if current == nil {
			continue
		}
		if match := tigerConsolidated.FindStringSubmatch(line); match != nil {
			others, err := strconv.Atoi(match[1])
			if err != nil {
				return nil, fmt.Errorf("unreadable ck3-tiger location count: %s", line)
			}
			current.Count += others
			continue
		}
		// Only the first location names the finding; the rest are the context
		// tiger prints to explain how execution reached it.
		if match := tigerLocation.FindStringSubmatch(line); match != nil && current.File == "" {
			current.Source = match[1]
			current.File = strings.TrimSpace(match[2])
		}
	}
	flush()

	findings := make([]Finding, 0, len(order))
	for _, key := range order {
		key.Count = merged[key]
		findings = append(findings, key)
	}
	sortFindings(findings)

	if reported == nil {
		if len(findings) > 0 {
			return nil, fmt.Errorf("ck3-tiger printed %d finding(s) but no summary line", len(findings))
		}
		return findings, nil
	}
	if counted := tally(findings); !sameTotals(counted, reported) {
		return nil, fmt.Errorf(
			"parsed ck3-tiger findings (%s) disagree with its summary (%s); "+
				"the report format changed and the parser needs updating",
			counted, reported)
	}
	return findings, nil
}

func sameTotals(left, right Totals) bool {
	for _, severity := range Severities {
		if left[severity] != right[severity] {
			return false
		}
	}
	return true
}

// Baseline is the set of ck3-tiger findings one module has already accepted.
type Baseline struct {
	SchemaVersion int       `json:"schemaVersion"`
	Findings      []Finding `json:"findings"`
}

// Change is one finding whose number of occurrences moved.
type Change struct {
	Finding Finding
	// Recorded is what the baseline held, and is zero for a finding that is
	// wholly new.
	Recorded int
}

// Delta is how a run compares to the baseline.
type Delta struct {
	// New are findings from reproducible checks that appeared or grew. These
	// fail validation: an upstream update that adds one is what the baseline
	// exists to surface.
	New []Change
	// Unstable are the same, from the checks in InferenceCodes. They are
	// reported and not failed on, because they also appear when nothing
	// changed.
	Unstable []Change
	// Resolved are findings that went away. They never fail; they only mean the
	// baseline is due a refresh. Shrinking inference findings are left out
	// entirely, since they shrink on their own.
	Resolved []Change
}

// Empty reports whether the run matches the baseline exactly.
func (d Delta) Empty() bool {
	return len(d.New) == 0 && len(d.Unstable) == 0 && len(d.Resolved) == 0
}

// Regressed reports whether anything appeared that validation should fail on.
func (d Delta) Regressed() bool {
	return len(d.New) > 0
}

// CompareBaseline reports which findings appeared and which went away.
//
// A finding that merely grew is reported by the amount it grew, and one that
// shrank as resolved: how often a finding occurs is part of what was accepted.
func CompareBaseline(recorded Baseline, current []Finding) Delta {
	previous := map[Finding]int{}
	for _, finding := range recorded.Findings {
		previous[finding.key()] += finding.Count
	}

	var delta Delta
	for _, finding := range current {
		key := finding.key()
		was := previous[key]
		delete(previous, key)
		switch {
		case finding.Count > was:
			appeared := finding
			appeared.Count -= was
			change := Change{Finding: appeared, Recorded: was}
			if finding.Inferred() {
				delta.Unstable = append(delta.Unstable, change)
			} else {
				delta.New = append(delta.New, change)
			}
		case finding.Count < was && !finding.Inferred():
			gone := finding
			gone.Count = was - finding.Count
			delta.Resolved = append(delta.Resolved, Change{Finding: gone, Recorded: was})
		}
	}
	for key, was := range previous {
		if key.Inferred() {
			continue
		}
		gone := key
		gone.Count = was
		delta.Resolved = append(delta.Resolved, Change{Finding: gone, Recorded: was})
	}

	sortChanges(delta.New)
	sortChanges(delta.Unstable)
	sortChanges(delta.Resolved)
	return delta
}

// MergeBaseline is what --apply records: the run as it stands, except that an
// inference finding is never lowered or dropped.
//
// Holding those at their high-water mark is what makes the report settle. A run
// that happens to deduce fewer of them would otherwise lower the baseline, and
// the next ordinary run would report the difference back as growth, forever.
func MergeBaseline(recorded Baseline, current []Finding) []Finding {
	merged := map[Finding]int{}
	var order []Finding
	add := func(finding Finding, count int) {
		key := finding.key()
		if _, seen := merged[key]; !seen {
			order = append(order, key)
		}
		if count > merged[key] {
			merged[key] = count
		}
	}
	for _, finding := range current {
		add(finding, finding.Count)
	}
	for _, finding := range recorded.Findings {
		if finding.Inferred() {
			add(finding, finding.Count)
		}
	}

	findings := make([]Finding, 0, len(order))
	for _, key := range order {
		key.Count = merged[key]
		findings = append(findings, key)
	}
	sortFindings(findings)
	return findings
}

func sortChanges(changes []Change) {
	sort.Slice(changes, func(left, right int) bool {
		return lessFinding(changes[left].Finding, changes[right].Finding)
	})
}

// LoadBaseline reads one module's accepted findings. A missing baseline is an
// empty one, so a module that has never been recorded reports everything as new
// rather than silently accepting it.
func LoadBaseline(path string) (Baseline, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		if os.IsNotExist(err) {
			return Baseline{SchemaVersion: BaselineSchemaVersion}, nil
		}
		return Baseline{}, err
	}
	var baseline Baseline
	if err := json.Unmarshal(data, &baseline); err != nil {
		return Baseline{}, fmt.Errorf("%s: %w", path, err)
	}
	if baseline.SchemaVersion != BaselineSchemaVersion {
		return Baseline{}, fmt.Errorf("%s: unsupported baseline schema version %d",
			path, baseline.SchemaVersion)
	}
	return baseline, nil
}

// SaveBaseline writes one module's accepted findings, or removes the file when
// the module is clean.
func SaveBaseline(path string, findings []Finding) error {
	if len(findings) == 0 {
		if err := os.Remove(path); err != nil && !os.IsNotExist(err) {
			return err
		}
		return nil
	}
	sorted := append([]Finding(nil), findings...)
	sortFindings(sorted)
	data, err := json.MarshalIndent(
		Baseline{SchemaVersion: BaselineSchemaVersion, Findings: sorted}, "", "  ")
	if err != nil {
		return err
	}
	return fsutil.WriteFileAtomic(path, append(data, '\n'), 0o644)
}
