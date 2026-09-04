// Package validate checks one mod without changing anything: its canonical
// descriptor, whether its generated outputs are current, and what ck3-tiger
// says about the payload.
package validate

import (
	"errors"
	"fmt"
	"os/exec"
	"path/filepath"
	"strings"

	"codeberg.org/traidare/ck3_mods/internal/config"
	"codeberg.org/traidare/ck3_mods/internal/fsutil"
	"codeberg.org/traidare/ck3_mods/internal/generate"
	"codeberg.org/traidare/ck3_mods/internal/pdx"
	"codeberg.org/traidare/ck3_mods/internal/workspace"
)

// Step names one stage of validation.
type Step string

// Status is one stage's outcome. Skipped stages do not fail a mod.
type Status string

const (
	StepDescriptor Step = "descriptor"
	StepGenerator  Step = "generator"
	StepTiger      Step = "tiger"

	StatusPassed  Status = "passed"
	StatusFailed  Status = "failed"
	StatusSkipped Status = "skipped"
	StatusError   Status = "error"
)

// TigerExecutable is the linter the payload is checked with.
const TigerExecutable = "ck3-tiger"

// TigerConfigName is the per-mod dependency load order ck3-tiger reads.
const TigerConfigName = "ck3-tiger.conf"

// Check is one validation stage's result.
type Check struct {
	Step    Step
	Status  Status
	Message string
	Command []string
	Stdout  string
	Stderr  string
	Details []string
	// Totals is the tiger stage's finding tally, carried structurally so a JSON
	// consumer can trend it instead of parsing the message.
	Totals Totals
}

// OK reports whether this stage lets the mod pass.
func (c Check) OK() bool {
	return c.Status == StatusPassed || c.Status == StatusSkipped
}

// ToMap renders one check for JSON output, omitting what did not happen.
func (c Check) ToMap() map[string]any {
	result := map[string]any{
		"step":    string(c.Step),
		"status":  string(c.Status),
		"message": c.Message,
	}
	if len(c.Command) > 0 {
		result["command"] = c.Command
	}
	if c.Stdout != "" {
		result["stdout"] = c.Stdout
	}
	if c.Stderr != "" {
		result["stderr"] = c.Stderr
	}
	if len(c.Details) > 0 {
		result["details"] = c.Details
	}
	if c.Totals != nil {
		result["totals"] = c.Totals
	}
	return result
}

// Result is every stage run against one mod.
type Result struct {
	Slug   string
	Checks []Check
}

// Status is the worst outcome any stage reported.
func (r Result) Status() Status {
	statuses := map[Status]bool{}
	for _, check := range r.Checks {
		statuses[check.Status] = true
	}
	switch {
	case statuses[StatusError]:
		return StatusError
	case statuses[StatusFailed]:
		return StatusFailed
	case statuses[StatusPassed]:
		return StatusPassed
	default:
		return StatusSkipped
	}
}

// OK reports whether every stage let the mod pass.
func (r Result) OK() bool {
	for _, check := range r.Checks {
		if !check.OK() {
			return false
		}
	}
	return true
}

// ToMap renders one mod's result for JSON output.
func (r Result) ToMap() map[string]any {
	checks := make([]any, len(r.Checks))
	for index, check := range r.Checks {
		checks[index] = check.ToMap()
	}
	return map[string]any{
		"mod":    r.Slug,
		"status": string(r.Status()),
		"checks": checks,
	}
}

// Options controls what a validation run is allowed to write. Nothing is
// written unless Apply is set, and even then only the tiger baseline.
type Options struct {
	Apply bool
}

// Mod validates one mod, promoting no outputs and writing nothing unless
// options.Apply refreshes the tiger baseline.
func Mod(space *workspace.Workspace, mod *workspace.Mod, settings config.Config, options Options) Result {
	return Result{
		Slug: mod.Slug,
		Checks: []Check{
			validateDescriptor(mod),
			validateGenerator(space, mod, settings),
			validateTiger(space, mod, settings, options),
		},
	}
}

func validateDescriptor(mod *workspace.Mod) Check {
	descriptor, err := pdx.Load(mod.DescriptorPath)
	if err == nil {
		err = pdx.ValidateNative(descriptor)
	}
	if err != nil {
		return Check{Step: StepDescriptor, Status: StatusFailed, Message: err.Error()}
	}
	name, err := descriptor.Name()
	if err != nil {
		return Check{Step: StepDescriptor, Status: StatusFailed, Message: err.Error()}
	}
	return Check{
		Step:    StepDescriptor,
		Status:  StatusPassed,
		Message: "canonical descriptor is valid: " + name,
	}
}

func validateGenerator(space *workspace.Workspace, mod *workspace.Mod, settings config.Config) Check {
	if !mod.HasGenerator() {
		return Check{
			Step:    StepGenerator,
			Status:  StatusSkipped,
			Message: "no generator is configured",
		}
	}
	result, err := generate.Run(space, mod, settings, generate.Options{})
	if err != nil {
		return Check{
			Step:    StepGenerator,
			Status:  StatusError,
			Message: "generator freshness check failed: " + err.Error(),
		}
	}
	if result.Current() {
		return Check{
			Step:    StepGenerator,
			Status:  StatusPassed,
			Message: "generated outputs are current",
		}
	}
	details := make([]string, 0, len(result.ChangedFiles)+len(result.StaleFiles))
	for _, path := range result.ChangedFiles {
		details = append(details, "changed: "+path)
	}
	for _, path := range result.StaleFiles {
		details = append(details, "stale: "+path)
	}
	return Check{
		Step:    StepGenerator,
		Status:  StatusFailed,
		Message: "generated outputs are stale; run `ck3mm mod generate --apply`",
		Details: details,
	}
}

func validateTiger(space *workspace.Workspace, mod *workspace.Mod, settings config.Config, options Options) Check {
	if err := settings.Require(config.GameDir, config.ParadoxDir); err != nil {
		return Check{
			Step:    StepTiger,
			Status:  StatusError,
			Message: "ck3-tiger cannot run: " + err.Error(),
		}
	}

	command := []string{
		TigerExecutable,
		"--no-color",
		"--consolidate",
		"--game", settings.GameDir,
		"--paradox", settings.ParadoxDir,
	}
	// The dependency load order lives with the mod's tooling, never in the
	// descriptor CK3 itself reads.
	tigerConfig := mod.ToolingRoot + "/" + TigerConfigName
	if fsutil.IsFile(tigerConfig) {
		command = append(command, "--config", tigerConfig)
	}
	command = append(command, mod.DescriptorPath)

	execution := exec.Command(command[0], command[1:]...)
	execution.Dir = space.Root
	var stdout, stderr strings.Builder
	execution.Stdout = &stdout
	execution.Stderr = &stderr

	err := execution.Run()
	check := Check{Step: StepTiger, Command: command}
	var exitError *exec.ExitError
	switch {
	case err == nil, errors.As(err, &exitError):
		// A nonzero exit means fatal findings, which the report below covers in
		// detail. Anything else means ck3-tiger never ran at all.
	case errors.Is(err, exec.ErrNotFound):
		check.Status = StatusError
		check.Message = TigerExecutable + " was not found on PATH; run validation inside " +
			"`nix develop` or install ck3-tiger, then retry"
		return check
	default:
		check.Status = StatusError
		check.Message = "could not start " + TigerExecutable + ": " + err.Error()
		return check
	}

	// The raw output is deliberately dropped from here on: the sweep emits six
	// figures of lines, all of it identical from one run to the next. What the
	// baseline comparison keeps is the part that changed. The command above
	// reproduces the full report when a finding needs its line number.
	findings, parseErr := ParseTiger(stdout.String())
	if parseErr != nil {
		return Check{
			Step:    StepTiger,
			Status:  StatusError,
			Command: command,
			Message: parseErr.Error(),
			Stdout:  stdout.String(),
			Stderr:  stderr.String(),
		}
	}
	totals := tally(findings)
	check.Totals = totals

	baselinePath := filepath.Join(mod.ToolingRoot, BaselineFileName)
	recorded, err := LoadBaseline(baselinePath)
	if err != nil {
		return Check{
			Step:    StepTiger,
			Status:  StatusError,
			Command: command,
			Message: err.Error(),
		}
	}
	delta := CompareBaseline(recorded, findings)
	for _, group := range []struct {
		marker  string
		changes []Change
	}{
		{"+", delta.New},
		// Marked apart so a finding tiger only sometimes reports is never read
		// as one an upstream update introduced.
		{"?", delta.Unstable},
		{"-", delta.Resolved},
	} {
		for _, change := range group.changes {
			check.Details = append(check.Details, changeDetail(group.marker, change))
		}
	}

	// A fatal is never an accepted finding: it fails whatever the baseline says,
	// and --apply refuses to record it.
	if exitError != nil {
		check.Status = StatusFailed
		check.Message = fmt.Sprintf("ck3-tiger exited with status %d: %s",
			exitError.ExitCode(), totals)
		return check
	}

	if options.Apply && !delta.Empty() {
		if err := SaveBaseline(baselinePath, MergeBaseline(recorded, findings)); err != nil {
			return Check{
				Step:    StepTiger,
				Status:  StatusError,
				Command: command,
				Message: err.Error(),
			}
		}
		check.Status = StatusPassed
		check.Message = fmt.Sprintf(
			"recorded %d new, %d unreproducible and %d resolved ck3-tiger finding(s): %s",
			len(delta.New), len(delta.Unstable), len(delta.Resolved), totals)
		return check
	}

	switch {
	case delta.Regressed():
		check.Status = StatusFailed
		check.Message = fmt.Sprintf(
			"%d new ck3-tiger finding(s) since the baseline; review them, then "+
				"run `ck3mm mod validate %s --apply` to accept: %s",
			len(delta.New), mod.Slug, totals)
	case !delta.Empty():
		check.Status = StatusPassed
		check.Message = fmt.Sprintf(
			"%d unreproducible and %d resolved ck3-tiger finding(s); run "+
				"`ck3mm mod validate %s --apply` to refresh the baseline: %s",
			len(delta.Unstable), len(delta.Resolved), mod.Slug, totals)
	default:
		check.Status = StatusPassed
		check.Message = "ck3-tiger matches the baseline: " + totals.String()
	}
	return check
}

// changeDetail renders one baseline difference, keeping the recorded count in
// view so a finding that merely grew is never read as one that is wholly new.
func changeDetail(marker string, change Change) string {
	detail := marker + " " + change.Finding.Label()
	switch {
	case change.Recorded > 0:
		return fmt.Sprintf("%s (%s%d, baseline %d)",
			detail, marker, change.Finding.Count, change.Recorded)
	case change.Finding.Count > 1:
		return fmt.Sprintf("%s (%d occurrences)", detail, change.Finding.Count)
	}
	return detail
}
