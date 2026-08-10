// Package playset holds the portable playset model and the Launcher
// import/export operations built on it.
package playset

import (
	"encoding/json"
	"fmt"
	"os"
	"path"
	"path/filepath"
	"sort"
	"strings"

	"codeberg.org/traidare/ck3_mods/internal/fsutil"
	"codeberg.org/traidare/ck3_mods/internal/jsonout"
	"codeberg.org/traidare/ck3_mods/internal/launcher"
)

func errorf(format string, arguments ...any) error {
	return &launcher.Error{Message: fmt.Sprintf(format, arguments...)}
}

// Mod is one playset entry, identified portably rather than by database key.
type Mod struct {
	DisplayName    string
	Enabled        bool
	Position       int
	Source         string
	SteamID        string
	PdxID          string
	GameRegistryID string
}

// NormalizeRegistryID renders a local registry ID with forward slashes.
func NormalizeRegistryID(identifier string) string {
	return path.Clean(strings.ReplaceAll(identifier, `\`, "/"))
}

// StableID is the portable identity used across exports, diffs, and reports.
func (m Mod) StableID() string {
	if m.GameRegistryID != "" {
		return "local:" + NormalizeRegistryID(m.GameRegistryID)
	}
	if m.SteamID != "" {
		return "steam:" + m.SteamID
	}
	if m.PdxID != "" {
		return "pdx:" + m.PdxID
	}
	return "name:" + m.DisplayName
}

// ToMap renders the entry for reports, whose keys serialize alphabetically.
func (m Mod) ToMap() map[string]any {
	result := map[string]any{}
	for _, pair := range m.ToOrdered() {
		result[pair.Key] = pair.Value
	}
	return result
}

// ToOrdered renders the entry for the playset export, which keeps the field
// order a reader expects rather than sorting it.
func (m Mod) ToOrdered() jsonout.Ordered {
	ordered := jsonout.Ordered{
		{Key: "displayName", Value: m.DisplayName},
		{Key: "enabled", Value: m.Enabled},
		{Key: "position", Value: m.Position},
	}
	if m.Source != "" {
		ordered = append(ordered, jsonout.Pair{Key: "source", Value: m.Source})
	}
	if m.GameRegistryID != "" {
		ordered = append(ordered, jsonout.Pair{
			Key:   "gameRegistryId",
			Value: NormalizeRegistryID(m.GameRegistryID),
		})
	}
	if m.SteamID != "" {
		ordered = append(ordered, jsonout.Pair{Key: "steamId", Value: m.SteamID})
	}
	if m.PdxID != "" {
		ordered = append(ordered, jsonout.Pair{Key: "pdxId", Value: m.PdxID})
	}
	return ordered
}

// Playset is a named, ordered set of mods.
type Playset struct {
	Name            string
	Game            string
	SelectionSource string
	Mods            []Mod
}

// EnabledMods returns the entries CK3 would actually load.
func (p Playset) EnabledMods() []Mod {
	var enabled []Mod
	for _, mod := range p.Mods {
		if mod.Enabled {
			enabled = append(enabled, mod)
		}
	}
	return enabled
}

// ToOrdered renders the playset as the portable export document.
func (p Playset) ToOrdered() jsonout.Ordered {
	mods := make([]any, len(p.Mods))
	for index, mod := range p.Mods {
		mods[index] = mod.ToOrdered()
	}
	game := p.Game
	if game == "" {
		game = "ck3"
	}
	return jsonout.Ordered{
		{Key: "game", Value: game},
		{Key: "name", Value: p.Name},
		{Key: "mods", Value: mods},
	}
}

// Dump renders the export document as text.
func Dump(playset Playset) (string, error) {
	return jsonout.String(playset.ToOrdered())
}

// RequestedName resolves the playset selection order: command argument, then
// CK3_PLAYSET_NAME, then the active Launcher playset. The second return value
// names the layer that decided, for reporting.
func RequestedName(argument, configured string) (string, string) {
	if trimmed := strings.TrimSpace(argument); trimmed != "" {
		return trimmed, "command argument"
	}
	if trimmed := strings.TrimSpace(configured); trimmed != "" {
		return trimmed, "CK3_PLAYSET_NAME"
	}
	return "", "active Launcher playset"
}

func modFromRow(row launcher.Row, fallbackPosition int) Mod {
	displayName := row.String("displayName", "name")
	if displayName == "" {
		displayName = "<unnamed mod>"
	}
	return Mod{
		DisplayName:    displayName,
		Enabled:        launcher.ParseEnabled(row["enabled"]),
		Position:       launcher.ParsePosition(row["position"], fallbackPosition),
		Source:         strings.ToLower(row.String("source")),
		SteamID:        row.String("steamId", "remoteSteamId"),
		PdxID:          row.String("pdxId", "remotePdxId"),
		GameRegistryID: row.String("gameRegistryId"),
	}
}

// LoadLive reads a playset from the Launcher database.
func LoadLive(databasePath, name, configuredName string) (Playset, error) {
	requestedName, selectionSource := RequestedName(name, configuredName)
	database, err := launcher.Open(databasePath, true)
	if err != nil {
		return Playset{}, err
	}
	defer database.Close()

	row, err := database.SelectPlayset(requestedName)
	if err != nil {
		return Playset{}, err
	}
	modRows, err := database.PlaysetModRows(launcher.AsString(row["id"]))
	if err != nil {
		return Playset{}, err
	}
	mods := make([]Mod, len(modRows))
	for index, modRow := range modRows {
		mods[index] = modFromRow(modRow, index)
	}
	return Playset{
		Name:            launcher.AsString(row["name"]),
		Game:            "ck3",
		SelectionSource: selectionSource,
		Mods:            mods,
	}, nil
}

type playsetFile struct {
	Name string           `json:"name"`
	Game string           `json:"game"`
	Mods []map[string]any `json:"mods"`
}

func firstValue(raw map[string]any, names ...string) any {
	for _, name := range names {
		value, ok := raw[name]
		if !ok || value == nil {
			continue
		}
		if text, isText := value.(string); isText && text == "" {
			continue
		}
		return value
	}
	return nil
}

func stringValue(raw map[string]any, names ...string) string {
	return launcher.AsString(firstValue(raw, names...))
}

// LoadFile reads an exported playset JSON snapshot.
func LoadFile(filePath string) (Playset, error) {
	text, err := fsutil.ReadTextBOM(filePath)
	if err != nil {
		return Playset{}, errorf("could not read playset JSON: %v", err)
	}
	var file playsetFile
	if err := json.Unmarshal([]byte(text), &file); err != nil {
		return Playset{}, errorf("could not read playset JSON: %v", err)
	}
	if file.Mods == nil {
		return Playset{}, errorf(`expected a JSON object containing a "mods" array`)
	}

	name := strings.TrimSpace(file.Name)
	if name == "" {
		base := filepath.Base(filePath)
		name = strings.TrimSuffix(base, filepath.Ext(base))
	}
	if name == "" {
		return Playset{}, errorf("playset name is empty")
	}
	game := strings.ToLower(strings.TrimSpace(file.Game))
	if game == "" {
		game = "ck3"
	}

	mods := make([]Mod, 0, len(file.Mods))
	for index, raw := range file.Mods {
		displayName := stringValue(raw, "displayName", "name")
		if displayName == "" {
			displayName = fmt.Sprintf("entry %d", index)
		}
		enabled := true
		if value, ok := raw["enabled"]; ok {
			enabled = launcher.ParseEnabled(value)
		}
		mods = append(mods, Mod{
			DisplayName:    displayName,
			Enabled:        enabled,
			Position:       launcher.ParsePosition(raw["position"], index),
			Source:         strings.ToLower(stringValue(raw, "source")),
			SteamID:        stringValue(raw, "steamId", "steamID", "remoteSteamId"),
			PdxID:          stringValue(raw, "pdxId", "pdxID", "remotePdxId"),
			GameRegistryID: stringValue(raw, "gameRegistryId"),
		})
	}
	sort.SliceStable(mods, func(left, right int) bool {
		if mods[left].Position != mods[right].Position {
			return mods[left].Position < mods[right].Position
		}
		return mods[left].DisplayName < mods[right].DisplayName
	})
	return Playset{Name: name, Game: game, SelectionSource: "file", Mods: mods}, nil
}

// Summary is the path-free overview of a playset's composition.
func Summary(playset Playset) map[string]any {
	enabled := playset.EnabledMods()
	var local, workshop, disabledLocal []Mod
	for _, mod := range enabled {
		if mod.Source == "local" {
			local = append(local, mod)
		}
		if mod.SteamID != "" {
			workshop = append(workshop, mod)
		}
	}
	for _, mod := range playset.Mods {
		if !mod.Enabled && mod.Source == "local" {
			disabledLocal = append(disabledLocal, mod)
		}
	}
	return map[string]any{
		"name":              playset.Name,
		"selectionSource":   playset.SelectionSource,
		"total":             len(playset.Mods),
		"enabled":           len(enabled),
		"local":             len(local),
		"workshop":          len(workshop),
		"enabledLocalMods":  mapsOf(local),
		"disabledLocalMods": mapsOf(disabledLocal),
	}
}

func mapsOf(mods []Mod) []any {
	result := make([]any, len(mods))
	for index, mod := range mods {
		result[index] = mod.ToMap()
	}
	return result
}

// ChangedMod records one entry that exists in both playsets but differs.
type ChangedMod struct {
	StableID string
	Before   Mod
	After    Mod
}

// ToMap renders the change in the portable JSON shape.
func (c ChangedMod) ToMap() map[string]any {
	return map[string]any{
		"id":     c.StableID,
		"before": c.Before.ToMap(),
		"after":  c.After.ToMap(),
	}
}

// Diff is a portable comparison of two playsets.
type Diff struct {
	BeforeName string
	AfterName  string
	Added      []Mod
	Removed    []Mod
	Changed    []ChangedMod
}

// Current reports whether the two playsets agree.
func (d Diff) Current() bool {
	return len(d.Added) == 0 && len(d.Removed) == 0 && len(d.Changed) == 0
}

// ToMap renders the diff in the portable JSON shape.
func (d Diff) ToMap() map[string]any {
	changed := make([]any, len(d.Changed))
	for index, change := range d.Changed {
		changed[index] = change.ToMap()
	}
	return map[string]any{
		"before":  d.BeforeName,
		"after":   d.AfterName,
		"added":   mapsOf(d.Added),
		"removed": mapsOf(d.Removed),
		"changed": changed,
	}
}

func indexed(playset Playset) (map[string]Mod, error) {
	result := map[string]Mod{}
	for _, mod := range playset.Mods {
		stableID := mod.StableID()
		if _, duplicate := result[stableID]; duplicate {
			return nil, errorf("playset %q has duplicate mod ID %q", playset.Name, stableID)
		}
		result[stableID] = mod
	}
	return result, nil
}

// comparable drops the load position, so a pure reorder is not a change.
func comparable(mod Mod) string {
	value := mod.ToMap()
	delete(value, "position")
	encoded, _ := json.Marshal(value)
	return string(encoded)
}

// Compare reports membership and setting changes, ignoring load positions.
func Compare(before, after Playset) (Diff, error) {
	left, err := indexed(before)
	if err != nil {
		return Diff{}, err
	}
	right, err := indexed(after)
	if err != nil {
		return Diff{}, err
	}

	diff := Diff{BeforeName: before.Name, AfterName: after.Name}
	for _, stableID := range sortedKeys(right) {
		if _, exists := left[stableID]; !exists {
			diff.Added = append(diff.Added, right[stableID])
		}
	}
	for _, stableID := range sortedKeys(left) {
		if _, exists := right[stableID]; !exists {
			diff.Removed = append(diff.Removed, left[stableID])
			continue
		}
		if comparable(left[stableID]) != comparable(right[stableID]) {
			diff.Changed = append(diff.Changed, ChangedMod{
				StableID: stableID,
				Before:   left[stableID],
				After:    right[stableID],
			})
		}
	}
	return diff, nil
}

func sortedKeys(values map[string]Mod) []string {
	keys := make([]string, 0, len(values))
	for key := range values {
		keys = append(keys, key)
	}
	sort.Strings(keys)
	return keys
}

// WriteFile writes an exported playset snapshot.
func WriteFile(filePath string, text string) error {
	return os.WriteFile(filePath, []byte(text), 0o644)
}
