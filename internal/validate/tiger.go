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

// BaselineSchemaVersion is the baseline format this package writes.
//
// Version 2 added the ck3-tiger build a baseline was recorded with and the
// per-finding reason. Version 1 is still read, as a version 2 carrying neither,
// so a module is upgraded by the next --apply rather than by a migration.
const BaselineSchemaVersion = 2

// MinBaselineSchemaVersion is the oldest format still readable.
const MinBaselineSchemaVersion = 1

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
// finding per module appears in some runs and not others.
//
// The drift is not strictly confined to these two codes. Three identical runs
// over one module also moved a single `validation` finding and a single
// `missing-localization` one, out of four and 2298 findings under those codes
// respectively; both sit downstream of a deduced scope. Listing those codes
// here would stop gating 2300 findings in order to absorb two, so they stay
// gated, and a lone spurious one is settled by running validation again.
//
// The codes listed are held to a high-water mark rather than an exact count: a
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
	// Reason records why this finding is accepted instead of fixed. It is
	// required for the findings ReasonRequired selects and optional elsewhere,
	// and it is written by hand: --apply preserves the reasons already recorded
	// but never invents one.
	Reason string `json:"reason,omitempty"`
}

// key identifies a finding across runs, ignoring how often it occurred and why
// it was accepted. Both are things recorded about a finding rather than part of
// what makes it that finding, so a reason survives a change in count.
func (f Finding) key() Finding {
	f.Count = 0
	f.Reason = ""
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
	SchemaVersion int `json:"schemaVersion"`
	// TigerVersion is the ck3-tiger build that produced these findings.
	//
	// Without it, a finding that appears or resolves because a tiger release
	// reclassified a check is indistinguishable from one an upstream update
	// introduced, and the diff offers nothing to tell them apart. Empty for a
	// version 1 baseline that predates the field.
	TigerVersion string    `json:"tigerVersion,omitempty"`
	Findings     []Finding `json:"findings"`
}

// ReasonRequired reports whether accepting this finding has to be justified in
// writing, given whether the module's generator owns the file it sits in.
//
// The set is deliberately narrow: an error or fatal, reported against the
// module itself, in a path the generator writes. Those are the findings the
// module is the last writer for and could have fixed, so accepting one is a
// decision. A finding the same file carries verbatim from a parent still needs
// a reason, but naming the parent as its origin is a complete one — the
// baseline is not a place to re-audit a parent mod.
//
// Everything else is left optional. Warnings run to four figures per module,
// and findings tagged with a parent or CK3 are not ours to answer for.
func (f Finding) ReasonRequired(ownsFile bool) bool {
	if f.Source != "MOD" || !ownsFile {
		return false
	}
	return f.Severity == "error" || f.Severity == "fatal"
}

// MissingReasons returns the accepted findings that owe a reason and lack one.
// ownsFile reports whether the module's generator writes a given payload path.
func MissingReasons(baseline Baseline, ownsFile func(string) bool) []Finding {
	var missing []Finding
	for _, finding := range baseline.Findings {
		if finding.Reason != "" || !finding.ReasonRequired(ownsFile(finding.File)) {
			continue
		}
		missing = append(missing, finding)
	}
	sortFindings(missing)
	return missing
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
//
// Reasons already recorded are carried onto the findings they belong to. A
// finding whose count moved keeps its reason; one that resolved takes its
// reason with it, so a reason never outlives what it justifies.
func MergeBaseline(recorded Baseline, current []Finding) []Finding {
	reasons := map[Finding]string{}
	for _, finding := range recorded.Findings {
		if finding.Reason != "" {
			reasons[finding.key()] = finding.Reason
		}
	}

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
		finding := key
		finding.Count = merged[key]
		finding.Reason = reasons[key]
		findings = append(findings, finding)
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
	if baseline.SchemaVersion < MinBaselineSchemaVersion ||
		baseline.SchemaVersion > BaselineSchemaVersion {
		return Baseline{}, fmt.Errorf(
			"%s: unsupported baseline schema version %d, expected %d to %d",
			path, baseline.SchemaVersion, MinBaselineSchemaVersion, BaselineSchemaVersion)
	}
	return baseline, nil
}

// SaveBaseline writes one module's accepted findings, or removes the file when
// the module is clean. It always writes the current schema version, so a
// version 1 baseline is upgraded in place by the --apply that next touches it.
func SaveBaseline(path, tigerVersion string, findings []Finding) error {
	if len(findings) == 0 {
		if err := os.Remove(path); err != nil && !os.IsNotExist(err) {
			return err
		}
		return nil
	}
	sorted := append([]Finding(nil), findings...)
	sortFindings(sorted)
	data, err := json.MarshalIndent(Baseline{
		SchemaVersion: BaselineSchemaVersion,
		TigerVersion:  tigerVersion,
		Findings:      sorted,
	}, "", "  ")
	if err != nil {
		return err
	}
	return fsutil.WriteFileAtomic(path, append(data, '\n'), 0o644)
}
