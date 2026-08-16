// Package cultures answers questions about the effective culture, tradition,
// and pillar definitions of a live playset.
//
// Load order and replace_path shadowing are handled by internal/gamedata, so
// what this package reports is what CK3 would load.
package cultures

import (
	"fmt"
	"sort"
	"strings"

	"codeberg.org/traidare/ck3_mods/internal/gamedata"
	"codeberg.org/traidare/ck3_mods/internal/report"
)

// The three data directories this package reads.
const (
	CulturesPath   = "common/culture/cultures"
	TraditionsPath = "common/culture/traditions"
	PillarsPath    = "common/culture/pillars"
)

// pillarKeys are the culture fields that hold a pillar. They only matter when a
// pillar is referenced but never defined, since resolution is normally driven
// by the pillar index. The shipped documentation still calls martial_custom
// "martial_tradition", so both spellings are accepted.
var pillarKeys = map[string]bool{
	"ethos":              true,
	"heritage":           true,
	"language":           true,
	"martial_custom":     true,
	"martial_tradition":  true,
	"head_determination": true,
}

// Pillar is one resolved pillar assignment. Type is the pillar's own declared
// type, which is what makes heritage the culture group.
type Pillar struct {
	Type string
	ID   string
	// RequiresDLC is set only for a dlc_fallback_pillar entry, which replaces
	// the culture's pillar of the same type when the feature is missing.
	RequiresDLC string
}

// DLCTradition is a tradition a culture only holds with a DLC feature, plus the
// tradition it falls back to without one.
type DLCTradition struct {
	Tradition   string
	RequiresDLC string
	Fallback    string
}

// Culture is one culture as the playset effectively defines it.
type Culture struct {
	gamedata.Definition
	Pillars         []Pillar
	FallbackPillars []Pillar
	// Traditions is the set a culture holds with every DLC present. It is what
	// the tradition filters match on.
	Traditions    []string
	DLCTraditions []DLCTradition
	Parents       []string
	Created       string
	NameLists     []string
}

// Pillar returns the culture's pillar of one type, or the empty string.
func (c Culture) Pillar(pillarType string) string {
	for _, pillar := range c.Pillars {
		if pillar.Type == pillarType {
			return pillar.ID
		}
	}
	return ""
}

// Database is the effective culture data of one playset.
type Database struct {
	PlaysetName string
	Cultures    map[string]Culture
	Traditions  map[string]gamedata.Definition
	Warnings    []report.Warning
}

// Load resolves the playset and parses its effective culture data.
func Load(gameDir, workshopDir, paradoxDir, databasePath, playsetName, configuredName string) (Database, error) {
	source, err := gamedata.Open(gameDir, workshopDir, paradoxDir, databasePath, playsetName, configuredName,
		[]string{CulturesPath, TraditionsPath})
	if err != nil {
		return Database{}, err
	}

	traditions, err := source.ParseDirectory(TraditionsPath)
	if err != nil {
		return Database{}, err
	}
	pillars, err := source.ParseDirectory(PillarsPath)
	if err != nil {
		return Database{}, err
	}
	pillarTypes, err := indexPillars(pillars)
	if err != nil {
		return Database{}, err
	}
	rawCultures, err := source.ParseDirectory(CulturesPath)
	if err != nil {
		return Database{}, err
	}

	cultures := make(map[string]Culture, len(rawCultures))
	for identifier, definition := range rawCultures {
		culture, err := parseCulture(definition, pillarTypes)
		if err != nil {
			return Database{}, err
		}
		cultures[identifier] = culture
	}

	return Database{
		PlaysetName: source.PlaysetName,
		Cultures:    cultures,
		Traditions:  traditions,
		Warnings:    source.Warnings,
	}, nil
}

// indexPillars maps every pillar identifier to its declared type.
func indexPillars(definitions map[string]gamedata.Definition) (map[string]string, error) {
	types := make(map[string]string, len(definitions))
	for identifier, definition := range definitions {
		fields, err := definition.Fields()
		if err != nil {
			return nil, err
		}
		if pillarType := fields.Scalar("type"); pillarType != "" {
			types[identifier] = pillarType
		}
	}
	return types, nil
}

// parseCulture reads the fields the reports need out of one culture block.
func parseCulture(definition gamedata.Definition, pillarTypes map[string]string) (Culture, error) {
	fields, err := definition.Fields()
	if err != nil {
		return Culture{}, err
	}

	culture := Culture{
		Definition: definition,
		Parents:    fields.List("parents"),
		Created:    fields.Scalar("created"),
		NameLists:  fields.Scalars("name_list"),
	}

	seen := map[Pillar]bool{}
	for _, pair := range fields.Pairs() {
		pillarType, indexed := pillarTypes[pair.Value]
		if !indexed {
			if !pillarKeys[pair.Key] {
				continue
			}
			// A pillar the playset references but never defines still belongs
			// in the report, typed by the field that held it.
			pillarType = pair.Key
		}
		pillar := Pillar{Type: pillarType, ID: pair.Value}
		if !seen[pillar] {
			seen[pillar] = true
			culture.Pillars = append(culture.Pillars, pillar)
		}
	}
	sort.Slice(culture.Pillars, func(left, right int) bool {
		if culture.Pillars[left].Type != culture.Pillars[right].Type {
			return culture.Pillars[left].Type < culture.Pillars[right].Type
		}
		return culture.Pillars[left].ID < culture.Pillars[right].ID
	})

	for _, block := range fields.Blocks("dlc_fallback_pillar") {
		fallback := block.Scalar("fallback")
		if fallback == "" {
			continue
		}
		pillarType, indexed := pillarTypes[fallback]
		if !indexed {
			pillarType = "unknown"
		}
		culture.FallbackPillars = append(culture.FallbackPillars, Pillar{
			Type:        pillarType,
			ID:          fallback,
			RequiresDLC: block.Scalar("requires_dlc_flag"),
		})
	}

	unique := map[string]bool{}
	for _, tradition := range fields.List("traditions") {
		unique[tradition] = true
	}
	for _, block := range fields.Blocks("dlc_tradition") {
		tradition := block.Scalar("trait")
		if tradition == "" {
			continue
		}
		unique[tradition] = true
		culture.DLCTraditions = append(culture.DLCTraditions, DLCTradition{
			Tradition:   tradition,
			RequiresDLC: block.Scalar("requires_dlc_flag"),
			Fallback:    block.Scalar("fallback"),
		})
	}
	culture.Traditions = sortedKeys(unique)
	return culture, nil
}

func sortedKeys(set map[string]bool) []string {
	keys := make([]string, 0, len(set))
	for key := range set {
		keys = append(keys, key)
	}
	sort.Strings(keys)
	return keys
}

// SelectCultures returns the cultures matching the tradition and heritage
// filters, sorted by identifier. Empty filters select everything.
func (d Database) SelectCultures(requested []string, matchAll bool, heritage string) ([]Culture, error) {
	unique := make([]string, 0, len(requested))
	seen := map[string]bool{}
	var unknown []string
	for _, value := range requested {
		if seen[value] {
			continue
		}
		seen[value] = true
		unique = append(unique, value)
		if _, known := d.Traditions[value]; !known {
			unknown = append(unknown, value)
		}
	}
	if len(unknown) > 0 {
		sort.Strings(unknown)
		return nil, fmt.Errorf("unknown tradition(s): %s", strings.Join(unknown, ", "))
	}

	var selected []Culture
	for _, identifier := range sortedCultureIDs(d.Cultures) {
		culture := d.Cultures[identifier]
		if len(unique) > 0 && !culture.matches(unique, matchAll) {
			continue
		}
		if heritage != "" && culture.Pillar("heritage") != heritage {
			continue
		}
		selected = append(selected, culture)
	}
	return selected, nil
}

func sortedCultureIDs(cultures map[string]Culture) []string {
	identifiers := make([]string, 0, len(cultures))
	for identifier := range cultures {
		identifiers = append(identifiers, identifier)
	}
	sort.Strings(identifiers)
	return identifiers
}

func (c Culture) matches(requested []string, matchAll bool) bool {
	assigned := map[string]bool{}
	for _, tradition := range c.Traditions {
		assigned[tradition] = true
	}
	for _, tradition := range requested {
		if assigned[tradition] {
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

// Culture returns one culture definition.
func (d Database) Culture(identifier string) (Culture, error) {
	culture, found := d.Cultures[identifier]
	if !found {
		return Culture{}, fmt.Errorf("unknown culture: %s", identifier)
	}
	return culture, nil
}

// SelectTraditions returns every tradition, sorted by identifier. A non-empty
// culture restricts the result to that culture's traditions.
func (d Database) SelectTraditions(culture string) ([]gamedata.Definition, error) {
	allowed := map[string]bool{}
	if culture != "" {
		definition, err := d.Culture(culture)
		if err != nil {
			return nil, err
		}
		for _, tradition := range definition.Traditions {
			allowed[tradition] = true
		}
	}

	identifiers := make([]string, 0, len(d.Traditions))
	for identifier := range d.Traditions {
		if culture != "" && !allowed[identifier] {
			continue
		}
		identifiers = append(identifiers, identifier)
	}
	sort.Strings(identifiers)

	selected := make([]gamedata.Definition, 0, len(identifiers))
	for _, identifier := range identifiers {
		selected = append(selected, d.Traditions[identifier])
	}
	return selected, nil
}

// Tradition returns one tradition definition.
func (d Database) Tradition(identifier string) (gamedata.Definition, error) {
	definition, found := d.Traditions[identifier]
	if !found {
		return gamedata.Definition{}, fmt.Errorf("unknown tradition: %s", identifier)
	}
	return definition, nil
}
