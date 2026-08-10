package conflicts

import (
	"path"
	"sort"
	"strings"

	"codeberg.org/traidare/ck3_mods/internal/report"
)

// FailOn names the opt-in CI policies that turn findings into a non-zero exit.
type FailOn string

// The supported policies.
const (
	// FailOnDivergent fails when any conflicting file has differing content.
	FailOnDivergent FailOn = "divergent"
	// FailOnAny fails on any conflict at all, identical content included.
	FailOnAny FailOn = "any"
	// FailOnMissing fails when an enabled mod could not be resolved.
	FailOnMissing FailOn = "missing"
)

// FailOnChoices lists the policies in help order.
var FailOnChoices = []FailOn{FailOnDivergent, FailOnAny, FailOnMissing}

// Filter narrows a report by path prefix and mod involvement.
type Filter struct {
	Involving       string
	IncludePrefixes []string
	ExcludePrefixes []string
	ConflictsOnly   bool
	SummaryOnly     bool
}

// Apply filters entries and rebuilds every report-level count.
func Apply(source report.Report, filter Filter) (report.Report, error) {
	included, err := normalizePrefixes(filter.IncludePrefixes)
	if err != nil {
		return report.Report{}, err
	}
	excluded, err := normalizePrefixes(filter.ExcludePrefixes)
	if err != nil {
		return report.Report{}, err
	}
	involvingIDs := resolveInvolvingIDs(source, filter.Involving)

	var entries []report.FileEntry
	for _, entry := range source.Files {
		if filter.ConflictsOnly && !entry.IsConflict() {
			continue
		}
		if !matchesPrefixes(entry.Path, included, excluded) {
			continue
		}
		if !entryInvolves(entry, involvingIDs) {
			continue
		}
		entries = append(entries, entry)
	}
	return report.WithFiles(source, entries, filter.SummaryOnly), nil
}

// ShouldFail reports whether a report violates the requested policy.
func ShouldFail(source report.Report, policy string) (bool, error) {
	if policy == "" {
		return false, nil
	}
	switch FailOn(policy) {
	case FailOnDivergent:
		return source.Summary.Divergent > 0, nil
	case FailOnAny:
		return source.Summary.Conflicts > 0, nil
	case FailOnMissing:
		return source.Summary.ModsMissing > 0, nil
	}
	choices := make([]string, len(FailOnChoices))
	for index, choice := range FailOnChoices {
		choices[index] = string(choice)
	}
	return false, errorf("unknown fail-on policy %q; choose %s", policy, strings.Join(choices, ", "))
}

func normalizePrefixes(prefixes []string) ([]string, error) {
	unique := map[string]bool{}
	for _, prefix := range prefixes {
		normalized, err := NormalizeRelativePath(prefix)
		if err != nil {
			return nil, err
		}
		if normalized != "" {
			unique[normalized] = true
		}
	}
	result := make([]string, 0, len(unique))
	for value := range unique {
		result = append(result, value)
	}
	sort.Strings(result)
	return result, nil
}

func matchesPrefixes(candidate string, included, excluded []string) bool {
	for _, prefix := range excluded {
		if strings.HasPrefix(candidate, prefix) {
			return false
		}
	}
	if len(included) == 0 {
		return true
	}
	for _, prefix := range included {
		if strings.HasPrefix(candidate, prefix) {
			return true
		}
	}
	return false
}

// resolveInvolvingIDs accepts any of a mod's public aliases: its stable ID, its
// display name, the bare identity value, and for local mods the registry file
// name with or without its .mod suffix.
func resolveInvolvingIDs(source report.Report, involving string) map[string]bool {
	if involving == "" {
		return nil
	}
	matches := map[string]bool{}
	for _, mod := range source.Mods {
		identityType, identityValue, hasSeparator := strings.Cut(mod.StableID, ":")
		aliases := map[string]bool{mod.StableID: true, mod.Name: true}
		if hasSeparator {
			aliases[identityValue] = true
		}
		if identityType == "local" {
			registryName := path.Base(identityValue)
			aliases[registryName] = true
			aliases[strings.TrimSuffix(registryName, ".mod")] = true
		}
		if aliases[involving] {
			matches[mod.StableID] = true
		}
	}
	if len(matches) == 0 {
		// An unknown selector filters everything out rather than silently
		// reporting the whole playset.
		return map[string]bool{involving: true}
	}
	return matches
}

func entryInvolves(entry report.FileEntry, involvingIDs map[string]bool) bool {
	if len(involvingIDs) == 0 {
		return true
	}
	for _, provider := range entry.Providers {
		if involvingIDs[provider.ModID] {
			return true
		}
	}
	for _, owner := range entry.ReplacePathOwners {
		if involvingIDs[owner.ModID] {
			return true
		}
	}
	return involvingIDs[entry.EffectiveWinner.ModID]
}
