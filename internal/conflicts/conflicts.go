// Package conflicts analyzes provider trees according to their effective CK3
// load order.
//
// A mod's replace_path operation is applied immediately before that same mod's
// files. A mod may therefore remove an earlier file and restore its own version
// in a single load step, which is why the walk below is strictly sequential
// over providers even though the filesystem work is parallel.
package conflicts

import (
	"fmt"
	"os"
	"path"
	"path/filepath"
	"runtime"
	"sort"
	"strings"
	"sync"

	"codeberg.org/traidare/ck3_mods/internal/fsutil"
	"codeberg.org/traidare/ck3_mods/internal/report"
)

// conflictKindOrder fixes the order conflict kinds appear in, so reports are
// diffable.
var conflictKindOrder = []string{"same_path", "replace_path_shadow"}

// Error reports a provider tree that cannot be analyzed safely.
type Error struct{ Message string }

func (e *Error) Error() string { return e.Message }

func errorf(format string, arguments ...any) error {
	return &Error{Message: fmt.Sprintf(format, arguments...)}
}

// Provider is a resolved mod root at one position in effective load order.
type Provider struct {
	StableID     string
	Name         string
	Root         string
	Position     int
	Source       string
	ReplacePaths []string
}

// NewProvider validates and normalizes a provider's declared replace paths.
func NewProvider(stableID, name, root string, position int, source string, replacePaths []string) (Provider, error) {
	if strings.TrimSpace(stableID) == "" {
		return Provider{}, errorf("stable_id must not be empty")
	}
	if strings.TrimSpace(name) == "" {
		return Provider{}, errorf("provider name must not be empty")
	}
	if position < 0 {
		return Provider{}, errorf("provider position must not be negative")
	}

	unique := map[string]bool{}
	for _, replacePath := range replacePaths {
		normalized, err := NormalizeRelativePath(replacePath)
		if err != nil {
			return Provider{}, err
		}
		if normalized == "" {
			return Provider{}, errorf("replace_path must not refer to the mod root")
		}
		unique[normalized] = true
	}
	normalized := make([]string, 0, len(unique))
	for value := range unique {
		normalized = append(normalized, value)
	}
	sort.Strings(normalized)

	return Provider{
		StableID:     stableID,
		Name:         name,
		Root:         root,
		Position:     position,
		Source:       source,
		ReplacePaths: normalized,
	}, nil
}

// ToRecord renders the provider's public, path-free metadata.
func (p Provider) ToRecord() report.ModRecord {
	return report.ModRecord{
		StableID:     p.StableID,
		Name:         p.Name,
		Position:     p.Position,
		Source:       p.Source,
		ReplacePaths: p.ReplacePaths,
	}
}

// MakeStableModID builds the portable identity hierarchy playset records use.
func MakeStableModID(gameRegistryID, steamID, pdxID, name string) (string, error) {
	if gameRegistryID != "" {
		registryID, err := NormalizeRelativePath(gameRegistryID)
		if err == nil && registryID != "" {
			return "local:" + registryID, nil
		}
	}
	if trimmed := strings.TrimSpace(steamID); trimmed != "" {
		return "steam:" + trimmed, nil
	}
	if trimmed := strings.TrimSpace(pdxID); trimmed != "" {
		return "pdx:" + trimmed, nil
	}
	if trimmed := strings.Join(strings.Fields(name), " "); trimmed != "" {
		return "name:" + trimmed, nil
	}
	return "", errorf("at least one mod identifier is required")
}

// NormalizeRelativePath validates a repository-independent relative path.
func NormalizeRelativePath(value string) (string, error) {
	candidate := strings.ReplaceAll(strings.TrimSpace(value), `\`, "/")
	if candidate == "" {
		return "", nil
	}
	normalized := strings.TrimSuffix(strings.TrimPrefix(path.Clean(candidate), "./"), "/")
	if strings.HasPrefix(normalized, "/") ||
		(len(normalized) >= 3 && normalized[1:3] == ":/") ||
		normalized == ".." || strings.HasPrefix(normalized, "../") {
		return "", errorf("expected a repository-independent relative path: %q", value)
	}
	if normalized == "." {
		return "", nil
	}
	return normalized, nil
}

// scanResult carries one provider's file list back from the worker pool.
type scanResult struct {
	index int
	files []string
	err   error
}

// scanProviders walks every provider tree in parallel and indexes the CK3
// payload files by their load-relative path.
//
// Only files at least one directory deep participate: root files are
// descriptors or repository metadata, and CK3 does not load them.
func scanProviders(providers []Provider) (map[string]map[string]string, int, error) {
	results := make([][]string, len(providers))
	jobs := make(chan int)
	failures := make(chan scanResult, len(providers))

	workers := runtime.GOMAXPROCS(0)
	if workers > len(providers) {
		workers = len(providers)
	}
	var group sync.WaitGroup
	for range workers {
		group.Add(1)
		go func() {
			defer group.Done()
			for index := range jobs {
				files, err := fsutil.WalkFiles(providers[index].Root)
				if err != nil {
					failures <- scanResult{index: index, err: err}
					continue
				}
				results[index] = files
			}
		}()
	}
	for index := range providers {
		jobs <- index
	}
	close(jobs)
	group.Wait()
	close(failures)

	for failure := range failures {
		return nil, 0, errorf("could not enumerate provider %s: %v",
			providers[failure.index].StableID, failure.err)
	}

	byPath := map[string]map[string]string{}
	filesScanned := 0
	for index, provider := range providers {
		for _, relative := range results[index] {
			if fsutil.HiddenSkipped(relative) {
				continue
			}
			if !strings.Contains(relative, "/") {
				continue
			}
			normalized, err := NormalizeRelativePath(relative)
			if err != nil {
				return nil, 0, err
			}
			filesScanned++
			if byPath[normalized] == nil {
				byPath[normalized] = map[string]string{}
			}
			byPath[normalized][provider.StableID] = filepath.Join(provider.Root, filepath.FromSlash(relative))
		}
	}
	return byPath, filesScanned, nil
}

// Analyze produces the full conflict report for an ordered provider set.
func Analyze(providers []Provider, playset *report.PlaysetRecord, warnings []report.Warning, includeAll bool) (report.Report, error) {
	ordered := make([]Provider, len(providers))
	copy(ordered, providers)
	sort.SliceStable(ordered, func(left, right int) bool {
		if ordered[left].Position != ordered[right].Position {
			return ordered[left].Position < ordered[right].Position
		}
		return ordered[left].StableID < ordered[right].StableID
	})
	if err := validateProviders(ordered); err != nil {
		return report.Report{}, err
	}

	providerFiles, filesScanned, err := scanProviders(ordered)
	if err != nil {
		return report.Report{}, err
	}

	paths := make([]string, 0, len(providerFiles))
	for relativePath := range providerFiles {
		paths = append(paths, relativePath)
	}
	sort.Strings(paths)

	entries := analyzePaths(paths, ordered, providerFiles)
	if !includeAll {
		filtered := entries[:0]
		for _, entry := range entries {
			if entry.IsConflict() {
				filtered = append(filtered, entry)
			}
		}
		entries = filtered
	}

	reportWarnings := make([]report.Warning, len(warnings))
	copy(reportWarnings, warnings)
	SortWarnings(reportWarnings)

	mods := make([]report.ModRecord, len(ordered))
	for index, provider := range ordered {
		mods[index] = provider.ToRecord()
	}
	return report.Report{
		Playset:  playset,
		Summary:  report.Summarize(entries, len(mods), filesScanned, reportWarnings),
		Warnings: reportWarnings,
		Mods:     mods,
		Files:    entries,
	}, nil
}

// analyzePaths evaluates every scanned path, hashing same-path candidates in
// parallel. Entries stay in the sorted path order they were given.
func analyzePaths(paths []string, providers []Provider, providerFiles map[string]map[string]string) []report.FileEntry {
	entries := make([]report.FileEntry, len(paths))
	digests := hashConflictCandidates(paths, providerFiles)

	jobs := make(chan int)
	workers := runtime.GOMAXPROCS(0)
	if workers > len(paths) {
		workers = len(paths)
	}
	if workers < 1 {
		return nil
	}
	var group sync.WaitGroup
	for range workers {
		group.Add(1)
		go func() {
			defer group.Done()
			for index := range jobs {
				entries[index] = analyzePath(paths[index], providers, providerFiles[paths[index]], digests)
			}
		}()
	}
	for index := range paths {
		jobs <- index
	}
	close(jobs)
	group.Wait()
	return entries
}

// digestResult is one file's content hash, or the failure to read it.
type digestResult struct {
	sha256   string
	readable bool
}

// hashConflictCandidates digests only the files that more than one mod
// provides. Everything else has no content status to report.
func hashConflictCandidates(paths []string, providerFiles map[string]map[string]string) map[string]digestResult {
	var targets []string
	for _, relativePath := range paths {
		files := providerFiles[relativePath]
		if len(files) < 2 {
			continue
		}
		for _, physical := range files {
			targets = append(targets, physical)
		}
	}
	sort.Strings(targets)

	results := fsutil.HashFiles(targets)
	digests := make(map[string]digestResult, len(results))
	for _, result := range results {
		digests[result.Path] = digestResult{sha256: result.Sha256, readable: result.Err == nil}
	}
	return digests
}

func analyzePath(relativePath string, providers []Provider, physicalFiles map[string]string, digests map[string]digestResult) report.FileEntry {
	var fileMods []Provider
	for _, provider := range providers {
		if _, present := physicalFiles[provider.StableID]; present {
			fileMods = append(fileMods, provider)
		}
	}
	samePath := len(fileMods) > 1

	var owners []report.ReplacePathOwner
	var currentProvider *Provider
	var replacementMod *Provider
	replacementPath := ""
	replacePathShadow := false

	for index := range providers {
		provider := &providers[index]
		var matching []string
		for _, replacePath := range provider.ReplacePaths {
			if replacePathMatches(relativePath, replacePath) {
				matching = append(matching, replacePath)
			}
		}
		if len(matching) > 0 {
			owners = append(owners, report.ReplacePathOwner{
				ModID:        provider.StableID,
				Position:     provider.Position,
				ReplacePaths: matching,
			})
			if currentProvider != nil {
				replacePathShadow = true
			}
			currentProvider = nil
			replacementMod = provider
			replacementPath = mostSpecific(matching)
		}
		if _, present := physicalFiles[provider.StableID]; present {
			currentProvider = provider
		}
	}

	var kinds []string
	for index, applies := range []bool{samePath, replacePathShadow} {
		if applies {
			kinds = append(kinds, conflictKindOrder[index])
		}
	}

	contentStatus, fileProviders := contentAnalysis(fileMods, physicalFiles, samePath, digests)

	var effectiveState string
	var winner report.EffectiveWinner
	if currentProvider != nil {
		effectiveState = "present"
		winner = report.EffectiveWinner{
			Kind:     "provider",
			ModID:    currentProvider.StableID,
			Position: currentProvider.Position,
			Description: currentProvider.Name +
				" is the last provider after load-order replace_path processing.",
		}
	} else {
		effectiveState = "removed"
		winner = report.EffectiveWinner{
			Kind:        "replace_path",
			ModID:       replacementMod.StableID,
			Position:    replacementMod.Position,
			ReplacePath: replacementPath,
			HasReplace:  true,
			Description: replacementMod.Name +
				" is the last applicable replace_path owner; no later provider restores the file.",
		}
	}

	category := relativePath
	if index := strings.Index(relativePath, "/"); index >= 0 {
		category = relativePath[:index]
	}
	return report.FileEntry{
		Path:              relativePath,
		Category:          category,
		ConflictKinds:     kinds,
		Providers:         fileProviders,
		ReplacePathOwners: owners,
		EffectiveState:    effectiveState,
		EffectiveWinner:   winner,
		ContentStatus:     contentStatus,
	}
}

// mostSpecific picks the longest matching replace_path, breaking ties
// alphabetically, so the reported owner is the narrowest declaration.
func mostSpecific(paths []string) string {
	best := paths[0]
	for _, candidate := range paths[1:] {
		if len(candidate) > len(best) || (len(candidate) == len(best) && candidate < best) {
			best = candidate
		}
	}
	return best
}

func contentAnalysis(providers []Provider, physicalFiles map[string]string, samePath bool, digests map[string]digestResult) (string, []report.FileProvider) {
	records := make([]report.FileProvider, 0, len(providers))
	if !samePath {
		for _, provider := range providers {
			records = append(records, report.FileProvider{
				ModID:    provider.StableID,
				Position: provider.Position,
			})
		}
		return "not_applicable", records
	}

	unique := map[string]bool{}
	unreadable := false
	for _, provider := range providers {
		digest := digests[physicalFiles[provider.StableID]]
		if !digest.readable {
			unreadable = true
			readable := false
			records = append(records, report.FileProvider{
				ModID:    provider.StableID,
				Position: provider.Position,
				Readable: &readable,
			})
			continue
		}
		unique[digest.sha256] = true
		readable := true
		records = append(records, report.FileProvider{
			ModID:    provider.StableID,
			Position: provider.Position,
			Sha256:   digest.sha256,
			Readable: &readable,
		})
	}

	switch {
	case unreadable:
		return "unreadable", records
	case len(unique) == 1:
		return "identical", records
	default:
		return "divergent", records
	}
}

func validateProviders(providers []Provider) error {
	seen := map[string]bool{}
	for _, provider := range providers {
		if seen[provider.StableID] {
			return errorf("duplicate stable mod identity: %s", provider.StableID)
		}
		seen[provider.StableID] = true
		if info, err := os.Stat(provider.Root); err != nil || !info.IsDir() {
			return errorf("provider root is not a readable directory: %s", provider.StableID)
		}
	}
	return nil
}

func replacePathMatches(candidate, replacePath string) bool {
	return candidate == replacePath || strings.HasPrefix(candidate, replacePath+"/")
}

// SortWarnings orders warnings by load position, then by code, mod, message.
func SortWarnings(warnings []report.Warning) {
	sort.SliceStable(warnings, func(left, right int) bool {
		leftPosition, rightPosition := warningPosition(warnings[left]), warningPosition(warnings[right])
		if leftPosition != rightPosition {
			return leftPosition < rightPosition
		}
		if warnings[left].Code != warnings[right].Code {
			return warnings[left].Code < warnings[right].Code
		}
		if warnings[left].ModID != warnings[right].ModID {
			return warnings[left].ModID < warnings[right].ModID
		}
		return warnings[left].Message < warnings[right].Message
	})
}

func warningPosition(warning report.Warning) int {
	if warning.Position == nil {
		// Python sorts unpositioned warnings last with 2**63 - 1.
		return int(^uint(0) >> 1)
	}
	return *warning.Position
}
