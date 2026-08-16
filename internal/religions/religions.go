// Package religions answers questions about the effective religion, faith,
// doctrine, and holy-site definitions of a live playset.
//
// Faiths are nested inside religions and inherit their religion's doctrines, so
// this package reports the merged result rather than what any one file writes.
// Load order and replace_path shadowing are handled by internal/gamedata.
package religions

import (
	"fmt"
	"sort"
	"strings"

	"codeberg.org/traidare/ck3_mods/internal/conflicts"
	"codeberg.org/traidare/ck3_mods/internal/gamedata"
	"codeberg.org/traidare/ck3_mods/internal/report"
)

// The four data directories this package reads.
const (
	ReligionsPath      = "common/religion/religion_types"
	HolySitesPath      = "common/religion/holy_site_types"
	DoctrineGroupsPath = "common/religion/doctrine_group_types"
	DoctrinesPath      = "common/religion/doctrine_types"
)

// Origin names the level a doctrine was declared at.
const (
	FromFaith    = "faith"
	FromReligion = "religion"
)

// Doctrine is one doctrine on a faith after the religion's have been merged in.
type Doctrine struct {
	ID    string
	Group string
	// Origin is FromFaith or FromReligion.
	Origin string
	// RequiresDLC is set for a doctrine_selection_pair branch. Fallback marks
	// the branch that applies when the feature is absent.
	RequiresDLC string
	Fallback    bool
}

// Group is one doctrine group. Picks defaults to 1; groups that allow more than
// one cannot be declared at religion level, so a faith's picks stand alone.
type Group struct {
	ID       string
	Category string
	Picks    int
}

// HolySite is one holy site with the bonuses it grants.
type HolySite struct {
	gamedata.Definition
	County     string
	Barony     string
	Modifiers  []gamedata.Pair
	Parameters []gamedata.Pair
}

// Religion is one religion and the doctrines it hands down to its faiths.
type Religion struct {
	gamedata.Definition
	Family    string
	Doctrines []Doctrine
	FaithIDs  []string
}

// Faith is one faith with its effective doctrines and holy sites.
type Faith struct {
	gamedata.Definition
	Religion      string
	Family        string
	ReligiousHead string
	Doctrines     []Doctrine
	HolySites     []string
}

// Database is the effective religion data of one playset.
type Database struct {
	PlaysetName string
	Religions   map[string]Religion
	Faiths      map[string]Faith
	HolySites   map[string]HolySite
	Groups      map[string]Group
	Warnings    []report.Warning

	// doctrineGroup maps a doctrine to the group that owns it. A doctrine in no
	// group never overrides another.
	doctrineGroup map[string]string
	// doctrines is every declared doctrine, for validating filters.
	doctrines map[string]bool
}

// Load resolves the playset and parses its effective religion data.
func Load(gameDir, workshopDir, paradoxDir, databasePath, playsetName, configuredName string) (Database, error) {
	source, err := gamedata.Open(gameDir, workshopDir, paradoxDir, databasePath, playsetName, configuredName,
		[]string{ReligionsPath, DoctrinesPath})
	if err != nil {
		return Database{}, err
	}

	database := Database{
		PlaysetName:   source.PlaysetName,
		Religions:     map[string]Religion{},
		Faiths:        map[string]Faith{},
		HolySites:     map[string]HolySite{},
		Groups:        map[string]Group{},
		Warnings:      source.Warnings,
		doctrineGroup: map[string]string{},
		doctrines:     map[string]bool{},
	}

	rawDoctrines, err := source.ParseDirectory(DoctrinesPath)
	if err != nil {
		return Database{}, err
	}
	for identifier := range rawDoctrines {
		database.doctrines[identifier] = true
	}

	rawGroups, err := source.ParseDirectory(DoctrineGroupsPath)
	if err != nil {
		return Database{}, err
	}
	if err := database.indexGroups(rawGroups); err != nil {
		return Database{}, err
	}

	rawHolySites, err := source.ParseDirectory(HolySitesPath)
	if err != nil {
		return Database{}, err
	}
	for identifier, definition := range rawHolySites {
		site, err := parseHolySite(definition)
		if err != nil {
			return Database{}, err
		}
		database.HolySites[identifier] = site
	}

	rawReligions, err := source.ParseDirectory(ReligionsPath)
	if err != nil {
		return Database{}, err
	}
	if err := database.parseReligions(rawReligions); err != nil {
		return Database{}, err
	}

	conflicts.SortWarnings(database.Warnings)
	return database, nil
}

// indexGroups records each group's picks and inverts it into doctrine -> group.
func (d *Database) indexGroups(definitions map[string]gamedata.Definition) error {
	for identifier, definition := range definitions {
		fields, err := definition.Fields()
		if err != nil {
			return err
		}
		picks := 1
		if declared := fields.Scalar("number_of_picks"); declared != "" {
			if parsed, err := parseInt(declared); err == nil {
				picks = parsed
			}
		}
		d.Groups[identifier] = Group{
			ID:       identifier,
			Category: strings.Trim(fields.Scalar("category"), `"`),
			Picks:    picks,
		}
		for _, doctrine := range fields.List("doctrine_types") {
			d.doctrineGroup[doctrine] = identifier
		}
	}
	return nil
}

func parseInt(value string) (int, error) {
	result := 0
	if value == "" {
		return 0, fmt.Errorf("empty integer")
	}
	for _, character := range value {
		if character < '0' || character > '9' {
			return 0, fmt.Errorf("not an integer: %q", value)
		}
		result = result*10 + int(character-'0')
	}
	return result, nil
}

func parseHolySite(definition gamedata.Definition) (HolySite, error) {
	fields, err := definition.Fields()
	if err != nil {
		return HolySite{}, err
	}
	site := HolySite{
		Definition: definition,
		County:     fields.Scalar("county"),
		Barony:     fields.Scalar("barony"),
	}
	for _, block := range fields.Blocks("character_modifier") {
		site.Modifiers = append(site.Modifiers, block.Pairs()...)
	}
	for _, block := range fields.Blocks("parameters") {
		site.Parameters = append(site.Parameters, block.Pairs()...)
	}
	return site, nil
}

// declaredDoctrines reads the doctrines one religion or faith block declares,
// including both branches of every DLC selection pair.
func (d *Database) declaredDoctrines(fields gamedata.Fields, origin string) []Doctrine {
	var doctrines []Doctrine
	for _, identifier := range fields.Scalars("doctrine") {
		doctrines = append(doctrines, Doctrine{
			ID:     identifier,
			Group:  d.doctrineGroup[identifier],
			Origin: origin,
		})
	}
	for _, block := range fields.Blocks("doctrine_selection_pair") {
		flag := block.Scalar("requires_dlc_flag")
		if identifier := block.Scalar("doctrine"); identifier != "" {
			doctrines = append(doctrines, Doctrine{
				ID:          identifier,
				Group:       d.doctrineGroup[identifier],
				Origin:      origin,
				RequiresDLC: flag,
			})
		}
		if identifier := block.Scalar("fallback_doctrine"); identifier != "" {
			doctrines = append(doctrines, Doctrine{
				ID:          identifier,
				Group:       d.doctrineGroup[identifier],
				Origin:      origin,
				RequiresDLC: flag,
				Fallback:    true,
			})
		}
	}
	return doctrines
}

func (d *Database) parseReligions(definitions map[string]gamedata.Definition) error {
	identifiers := make([]string, 0, len(definitions))
	for identifier := range definitions {
		identifiers = append(identifiers, identifier)
	}
	sort.Strings(identifiers)

	for _, identifier := range identifiers {
		definition := definitions[identifier]
		fields, err := definition.Fields()
		if err != nil {
			return err
		}
		religion := Religion{
			Definition: definition,
			Family:     fields.Scalar("family"),
			Doctrines:  d.declaredDoctrines(fields, FromReligion),
		}

		faiths, err := definition.Children("faiths")
		if err != nil {
			return err
		}
		for _, faithDefinition := range faiths {
			faith, err := d.parseFaith(faithDefinition, religion)
			if err != nil {
				return err
			}
			if previous, duplicate := d.Faiths[faith.Identifier]; duplicate {
				d.Warnings = append(d.Warnings, report.Warning{
					Code: "duplicate_faith",
					Message: fmt.Sprintf("%s is defined by both %s and %s; %s wins",
						faith.Identifier, previous.Religion, identifier, identifier),
				})
			}
			d.Faiths[faith.Identifier] = faith
			religion.FaithIDs = append(religion.FaithIDs, faith.Identifier)
		}
		sort.Strings(religion.FaithIDs)
		d.Religions[identifier] = religion
	}
	return nil
}

func (d *Database) parseFaith(definition gamedata.Definition, religion Religion) (Faith, error) {
	fields, err := definition.Fields()
	if err != nil {
		return Faith{}, err
	}

	family := fields.Scalar("family")
	if family == "" {
		family = religion.Family
	}
	faith := Faith{
		Definition:    definition,
		Religion:      religion.Identifier,
		Family:        family,
		ReligiousHead: fields.Scalar("religious_head"),
		HolySites:     fields.Scalars("holy_site"),
	}
	faith.Doctrines = d.mergeDoctrines(religion.Doctrines, d.declaredDoctrines(fields, FromFaith))

	for _, site := range faith.HolySites {
		if _, defined := d.HolySites[site]; !defined {
			d.Warnings = append(d.Warnings, report.Warning{
				Code:    "undefined_holy_site",
				Message: fmt.Sprintf("%s references holy site %s, which no layer defines", faith.Identifier, site),
			})
		}
	}
	return faith, nil
}

// mergeDoctrines applies the engine's inheritance rule: a religion's doctrines
// reach every faith in it, and a faith overrides by declaring a doctrine in the
// same group. Doctrines belonging to no known group never override.
func (d *Database) mergeDoctrines(religion, faith []Doctrine) []Doctrine {
	overridden := map[string]bool{}
	declared := map[string]bool{}
	for _, doctrine := range faith {
		declared[doctrine.ID] = true
		if doctrine.Group != "" {
			overridden[doctrine.Group] = true
		}
	}

	merged := make([]Doctrine, 0, len(religion)+len(faith))
	merged = append(merged, faith...)
	for _, doctrine := range religion {
		if declared[doctrine.ID] {
			continue
		}
		if doctrine.Group != "" && overridden[doctrine.Group] {
			continue
		}
		merged = append(merged, doctrine)
	}

	// Ungrouped doctrines sort last, so the grouped ones read as the table the
	// faith screen shows.
	sort.SliceStable(merged, func(left, right int) bool {
		leftGroup, rightGroup := merged[left].Group, merged[right].Group
		if (leftGroup == "") != (rightGroup == "") {
			return rightGroup == ""
		}
		if leftGroup != rightGroup {
			return leftGroup < rightGroup
		}
		return merged[left].ID < merged[right].ID
	})
	return merged
}

// SelectFaiths returns the faiths matching the religion and doctrine filters,
// sorted by identifier. Empty filters select everything.
func (d Database) SelectFaiths(religion string, requested []string, matchAll bool) ([]Faith, error) {
	if religion != "" {
		if _, known := d.Religions[religion]; !known {
			return nil, fmt.Errorf("unknown religion: %s", religion)
		}
	}

	unique := make([]string, 0, len(requested))
	seen := map[string]bool{}
	var unknown []string
	for _, value := range requested {
		if seen[value] {
			continue
		}
		seen[value] = true
		unique = append(unique, value)
		if !d.doctrines[value] {
			unknown = append(unknown, value)
		}
	}
	if len(unknown) > 0 {
		sort.Strings(unknown)
		return nil, fmt.Errorf("unknown doctrine(s): %s", strings.Join(unknown, ", "))
	}

	identifiers := make([]string, 0, len(d.Faiths))
	for identifier := range d.Faiths {
		identifiers = append(identifiers, identifier)
	}
	sort.Strings(identifiers)

	var selected []Faith
	for _, identifier := range identifiers {
		faith := d.Faiths[identifier]
		if religion != "" && faith.Religion != religion {
			continue
		}
		if len(unique) > 0 && !faith.matches(unique, matchAll) {
			continue
		}
		selected = append(selected, faith)
	}
	return selected, nil
}

func (f Faith) matches(requested []string, matchAll bool) bool {
	assigned := map[string]bool{}
	for _, doctrine := range f.Doctrines {
		assigned[doctrine.ID] = true
	}
	for _, doctrine := range requested {
		if assigned[doctrine] {
			if !matchAll {
				return true
			}
			continue
		}
		if matchAll {
			return false
		}
	}
	return matchAll
}

// Faith returns one faith definition.
func (d Database) Faith(identifier string) (Faith, error) {
	faith, found := d.Faiths[identifier]
	if !found {
		return Faith{}, fmt.Errorf("unknown faith: %s", identifier)
	}
	return faith, nil
}

// SelectHolySites returns every holy site sorted by identifier, or only the
// ones a faith holds, in the order the faith declares them.
func (d Database) SelectHolySites(faith string) ([]HolySite, error) {
	if faith == "" {
		identifiers := make([]string, 0, len(d.HolySites))
		for identifier := range d.HolySites {
			identifiers = append(identifiers, identifier)
		}
		sort.Strings(identifiers)
		selected := make([]HolySite, 0, len(identifiers))
		for _, identifier := range identifiers {
			selected = append(selected, d.HolySites[identifier])
		}
		return selected, nil
	}

	definition, err := d.Faith(faith)
	if err != nil {
		return nil, err
	}
	selected := make([]HolySite, 0, len(definition.HolySites))
	for _, identifier := range definition.HolySites {
		site, defined := d.HolySites[identifier]
		if !defined {
			// The warning was already recorded at load; report the reference so
			// the gap is visible rather than silently dropped.
			site = HolySite{Definition: gamedata.Definition{Identifier: identifier}}
		}
		selected = append(selected, site)
	}
	return selected, nil
}
