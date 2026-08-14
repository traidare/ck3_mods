// Package report holds the deterministic, portable conflict report model.

package report

import (
	"path"
	"strconv"
	"strings"
)

// SchemaVersion is the report format this package emits.
const SchemaVersion = 2

// PlaysetRecord is path-free metadata identifying the analyzed playset.
type PlaysetRecord struct {
	Name            string
	Game            string
	SelectionSource string
	ModsTotal       int
	ModsEnabled     int
}

// ToMap renders the record.
func (p PlaysetRecord) ToMap() map[string]any {
	game := p.Game
	if game == "" {
		game = "ck3"
	}
	selection := p.SelectionSource
	if selection == "" {
		selection = "unknown"
	}
	return map[string]any{
		"game":            game,
		"name":            p.Name,
		"selectionSource": selection,
		"modsTotal":       p.ModsTotal,
		"modsEnabled":     p.ModsEnabled,
	}
}

// ModRecord is public mod metadata; it deliberately excludes the mod's root.
type ModRecord struct {
	StableID     string
	SteamID      string
	Name         string
	Position     int
	Source       string
	ReplacePaths []string
}

// ToMap renders the record.
func (m ModRecord) ToMap() map[string]any {
	result := map[string]any{
		"id":       m.StableID,
		"name":     m.Name,
		"position": m.Position,
	}
	if m.SteamID != "" {
		result["steamId"] = m.SteamID
	}
	if m.Source != "" {
		result["source"] = m.Source
	}
	if len(m.ReplacePaths) > 0 {
		result["replacePaths"] = toAny(m.ReplacePaths)
	}
	return result
}

// Warning explains why part of a playset could not be analyzed.
type Warning struct {
	Code     string
	Message  string
	ModID    string
	Position *int
}

// ToMap renders the warning.
func (w Warning) ToMap() map[string]any {
	result := map[string]any{"code": w.Code, "message": w.Message}
	if w.ModID != "" {
		result["modId"] = w.ModID
	}
	if w.Position != nil {
		result["position"] = *w.Position
	}
	return result
}

// FileProvider is one mod that physically contains a CK3-relative file.
type FileProvider struct {
	ModID    string
	Position int
	Sha256   string
	Readable *bool
}

// ToMap renders the provider.
func (f FileProvider) ToMap() map[string]any {
	result := map[string]any{"modId": f.ModID, "position": f.Position}
	if f.Readable != nil {
		result["readable"] = *f.Readable
	}
	if f.Sha256 != "" {
		result["sha256"] = f.Sha256
	}
	return result
}

// ReplacePathOwner is a mod whose replace_path declarations cover a file.
type ReplacePathOwner struct {
	ModID        string
	Position     int
	ReplacePaths []string
}

// ToMap renders the owner.
func (r ReplacePathOwner) ToMap() map[string]any {
	return map[string]any{
		"modId":        r.ModID,
		"position":     r.Position,
		"replacePaths": toAny(r.ReplacePaths),
	}
}

// EffectiveWinner describes observed load behaviour without judging whether it
// is correct. Investigating that is the reader's job.
type EffectiveWinner struct {
	Kind        string
	ModID       string
	Position    int
	Description string
	ReplacePath string
	HasReplace  bool
}

// ToMap renders the winner.
func (e EffectiveWinner) ToMap() map[string]any {
	result := map[string]any{
		"kind":        e.Kind,
		"modId":       e.ModID,
		"position":    e.Position,
		"description": e.Description,
	}
	if e.HasReplace {
		result["replacePath"] = e.ReplacePath
	}
	return result
}

// FileEntry is the full analysis of one CK3-relative path.
type FileEntry struct {
	Path              string
	Category          string
	ConflictKinds     []string
	Providers         []FileProvider
	ReplacePathOwners []ReplacePathOwner
	EffectiveState    string
	EffectiveWinner   EffectiveWinner
	ContentStatus     string
}

// IsConflict reports whether the entry records any kind of conflict.
func (f FileEntry) IsConflict() bool { return len(f.ConflictKinds) > 0 }

// ToMap renders the entry.
func (f FileEntry) ToMap() map[string]any {
	providers := make([]any, len(f.Providers))
	for index, provider := range f.Providers {
		providers[index] = provider.ToMap()
	}
	owners := make([]any, len(f.ReplacePathOwners))
	for index, owner := range f.ReplacePathOwners {
		owners[index] = owner.ToMap()
	}
	return map[string]any{
		"path":              f.Path,
		"category":          f.Category,
		"conflictKinds":     toAny(f.ConflictKinds),
		"providers":         providers,
		"replacePathOwners": owners,
		"effectiveState":    f.EffectiveState,
		"effectiveWinner":   f.EffectiveWinner.ToMap(),
		"contentStatus":     f.ContentStatus,
	}
}

// Summary counts one report's findings.
type Summary struct {
	ModsAnalyzed      int
	ModsMissing       int
	FilesScanned      int
	FilesReported     int
	Conflicts         int
	SamePath          int
	ReplacePathShadow int
	Identical         int
	Divergent         int
	Unreadable        int
	EffectivePresent  int
	EffectiveRemoved  int
}

// ToMap renders the summary.
func (s Summary) ToMap() map[string]any {
	return map[string]any{
		"modsAnalyzed":      s.ModsAnalyzed,
		"modsMissing":       s.ModsMissing,
		"filesScanned":      s.FilesScanned,
		"filesReported":     s.FilesReported,
		"conflicts":         s.Conflicts,
		"samePath":          s.SamePath,
		"replacePathShadow": s.ReplacePathShadow,
		"identical":         s.Identical,
		"divergent":         s.Divergent,
		"unreadable":        s.Unreadable,
		"effectivePresent":  s.EffectivePresent,
		"effectiveRemoved":  s.EffectiveRemoved,
	}
}

// Report is one complete conflict analysis.
type Report struct {
	Playset  *PlaysetRecord
	Summary  Summary
	Warnings []Warning
	Mods     []ModRecord
	Files    []FileEntry
}

// ToMap renders the report.
func (r Report) ToMap() map[string]any {
	warnings := make([]any, len(r.Warnings))
	for index, warning := range r.Warnings {
		warnings[index] = warning.ToMap()
	}
	mods := make([]any, len(r.Mods))
	for index, mod := range r.Mods {
		mods[index] = mod.ToMap()
	}
	files := make([]any, len(r.Files))
	for index, file := range r.Files {
		files[index] = file.ToMap()
	}

	var playset any
	if r.Playset != nil {
		playset = r.Playset.ToMap()
	}
	return map[string]any{
		"schemaVersion": SchemaVersion,
		"playset":       playset,
		"summary":       r.Summary.ToMap(),
		"warnings":      warnings,
		"mods":          mods,
		"files":         files,
	}
}

// missingWarningCodes are the warnings that mean a mod could not be analyzed
// at all, as opposed to a lesser problem.
var missingWarningCodes = map[string]bool{
	"enabled_mod_missing":              true,
	"enabled_local_mod_missing":        true,
	"local_mod_directory_unconfigured": true,
	"mod_missing":                      true,
}

// Summarize counts a set of entries. Scan-wide totals are passed in because
// filtering changes what is reported without changing what was scanned.
func Summarize(files []FileEntry, modsAnalyzed, filesScanned int, warnings []Warning) Summary {
	summary := Summary{
		ModsAnalyzed:  modsAnalyzed,
		FilesScanned:  filesScanned,
		FilesReported: len(files),
	}
	for _, warning := range warnings {
		if missingWarningCodes[warning.Code] {
			summary.ModsMissing++
		}
	}
	for _, entry := range files {
		if entry.IsConflict() {
			summary.Conflicts++
		}
		for _, kind := range entry.ConflictKinds {
			switch kind {
			case "same_path":
				summary.SamePath++
			case "replace_path_shadow":
				summary.ReplacePathShadow++
			}
		}
		switch entry.ContentStatus {
		case "identical":
			summary.Identical++
		case "divergent":
			summary.Divergent++
		case "unreadable":
			summary.Unreadable++
		}
		switch entry.EffectiveState {
		case "present":
			summary.EffectivePresent++
		case "removed":
			summary.EffectiveRemoved++
		}
	}
	return summary
}

// WithFiles replaces a report's entries and rebuilds every derived count,
// keeping the scan-wide and missing-mod totals from the original.
func WithFiles(source Report, files []FileEntry, summaryOnly bool) Report {
	result := source
	result.Summary = Summarize(files, len(source.Mods), source.Summary.FilesScanned, source.Warnings)
	if summaryOnly {
		result.Files = nil
	} else {
		result.Files = files
	}
	return result
}

// RenderText renders the same model as a compact, deterministic text report.
func RenderText(source Report) string {
	summary := source.Summary
	lines := []string{
		"Summary",
		"  Mods analyzed: " + itoa(summary.ModsAnalyzed),
		"  Mods missing: " + itoa(summary.ModsMissing),
		"  Files scanned: " + itoa(summary.FilesScanned),
		"  Files reported: " + itoa(summary.FilesReported),
		"  Conflicts: " + itoa(summary.Conflicts),
		"  Same path: " + itoa(summary.SamePath),
		"  Replace path shadow: " + itoa(summary.ReplacePathShadow),
		"  Divergent: " + itoa(summary.Divergent),
	}
	if len(source.Warnings) > 0 {
		lines = append(lines, "", "Warnings")
		for _, warning := range source.Warnings {
			lines = append(lines, "  ["+warning.Code+"] "+warning.Message)
		}
	}
	if len(source.Files) > 0 {
		labels := modLabels(source.Mods)
		width := positionWidth(source.Mods)
		lines = append(lines, "", "Files")
		for _, entry := range source.Files {
			kinds := strings.Join(entry.ConflictKinds, ", ")
			if kinds == "" {
				kinds = "none"
			}
			lines = append(lines, "  "+entry.Path+" ["+kinds+"] -> "+entry.EffectiveState)
			for _, provider := range entry.Providers {
				label := labels[provider.ModID]
				if label == "" {
					label = provider.ModID
				}
				lines = append(lines, "    ["+pad(provider.Position, width)+"] "+label)
			}
		}
	}
	return strings.Join(lines, "\n") + "\n"
}

// modLabels renders each mod as "name (selector)". The selector is the shortest
// string --involving accepts for that mod: its Workshop ID, or for local-only
// mods its registry name.
func modLabels(mods []ModRecord) map[string]string {
	labels := make(map[string]string, len(mods))
	for _, mod := range mods {
		selector := mod.SteamID
		if selector == "" {
			_, identity, _ := strings.Cut(mod.StableID, ":")
			selector = strings.TrimSuffix(path.Base(identity), ".mod")
		}
		switch {
		case mod.Name == "":
			labels[mod.StableID] = selector
		case selector == "":
			labels[mod.StableID] = mod.Name
		default:
			labels[mod.StableID] = mod.Name + " (" + selector + ")"
		}
	}
	return labels
}

// positionWidth measures the widest load position so the column stays aligned.
func positionWidth(mods []ModRecord) int {
	width := 1
	for _, mod := range mods {
		if digits := len(itoa(mod.Position)); digits > width {
			width = digits
		}
	}
	return width
}

// pad right-aligns a load position within the measured column.
func pad(value, width int) string {
	text := itoa(value)
	if len(text) >= width {
		return text
	}
	return strings.Repeat(" ", width-len(text)) + text
}

func toAny(values []string) []any {
	result := make([]any, len(values))
	for index, value := range values {
		result[index] = value
	}
	return result
}

func itoa(value int) string { return strconv.Itoa(value) }
