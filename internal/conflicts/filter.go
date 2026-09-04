package conflicts

import (
	"fmt"
	"path"
	"sort"
	"strconv"
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
	Involving       []string
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
	involvingIDs, err := resolveInvolvingIDs(source, filter.Involving)
	if err != nil {
		return report.Report{}, err
	}

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
	return false, fmt.Errorf("unknown fail-on policy %q; choose %s", policy, strings.Join(choices, ", "))
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

// modAliases lists the public selectors a mod answers to: its stable ID, its
// display name, the bare identity value, its Workshop ID, and for local mods
// the registry file name with or without its .mod suffix.
func modAliases(mod report.ModRecord) map[string]bool {
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
	if mod.SteamID != "" {
		// Subscribed mods are identified by their local registry entry, so the
		// Workshop ID is not derivable from the stable ID.
		aliases[mod.SteamID] = true
		aliases["steam:"+mod.SteamID] = true
	}
	return aliases
}

// Selects reports whether a mod answers to a public --involving selector.
func Selects(mod report.ModRecord, selector string) bool {
	return selector != "" && modAliases(mod)[selector]
}

// resolveInvolvingIDs maps selectors onto the stable IDs they name. An
// unresolvable selector is an error: reporting zero conflicts would be
// indistinguishable from a genuinely clean playset.
func resolveInvolvingIDs(source report.Report, involving []string) (map[string]bool, error) {
	if len(involving) == 0 {
		return nil, nil
	}
	matches := map[string]bool{}
	for _, selector := range involving {
		if selector == "" {
			continue
		}
		found := false
		for _, mod := range source.Mods {
			if modAliases(mod)[selector] {
				matches[mod.StableID] = true
				found = true
			}
		}
		if !found {
			return nil, unknownSelectorError(source, selector)
		}
	}
	return matches, nil
}

// suggestionLimit caps how many near matches an unknown selector reports.
const suggestionLimit = 5

func unknownSelectorError(source report.Report, involving string) error {
	message := fmt.Sprintf("unknown mod selector %q; expected a stable ID, Workshop ID, or display name from the playset", involving)
	suggestions := nearMatches(source, involving)
	if len(suggestions) == 0 {
		return fmt.Errorf("%s", message)
	}
	return fmt.Errorf("%s; did you mean %s?", message, strings.Join(suggestions, ", "))
}

// nearMatches collects the aliases that contain the selector, so a typo or a
// partial name points at the mods it was probably meant to name.
func nearMatches(source report.Report, involving string) []string {
	needle := strings.ToLower(involving)
	unique := map[string]bool{}
	for _, mod := range source.Mods {
		for alias := range modAliases(mod) {
			if alias != "" && strings.Contains(strings.ToLower(alias), needle) {
				unique[alias] = true
			}
		}
	}
	suggestions := make([]string, 0, len(unique))
	for alias := range unique {
		suggestions = append(suggestions, strconv.Quote(alias))
	}
	sort.Strings(suggestions)
	if len(suggestions) > suggestionLimit {
		suggestions = suggestions[:suggestionLimit]
	}
	return suggestions
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
