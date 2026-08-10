// Package cultures answers questions about the effective culture and
// tradition definitions of a live playset.
//
// It resolves the load order with internal/layers, so it sees exactly the
// files CK3 would load, including replace_path shadowing.
package cultures

import (
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"codeberg.org/traidare/ck3_mods/internal/conflicts"
	"codeberg.org/traidare/ck3_mods/internal/fsutil"
	"codeberg.org/traidare/ck3_mods/internal/layers"
	"codeberg.org/traidare/ck3_mods/internal/pdx"
	"codeberg.org/traidare/ck3_mods/internal/playset"
	"codeberg.org/traidare/ck3_mods/internal/report"
)

// The two data directories this tool reads.
const (
	CulturesPath   = "common/culture/cultures"
	TraditionsPath = "common/culture/traditions"
)

// Error reports a query that cannot be answered.
type Error struct{ Message string }

func (e *Error) Error() string { return e.Message }

func errorf(format string, arguments ...any) error {
	return &Error{Message: fmt.Sprintf(format, arguments...)}
}

// Layer is one provider of culture data, vanilla included.
type Layer struct {
	Kind         string
	Name         string
	Identifier   string
	Position     *int
	Root         string
	ReplacePaths []string
}

// Definition is one culture or tradition as the playset effectively defines
// it, together with where the winning definition came from.
type Definition struct {
	Identifier   string
	Text         string
	Layer        Layer
	RelativePath string
	Line         int
	Traditions   []string
}

// SourceMap renders the provenance block shared by every output shape.
func (d Definition) SourceMap() map[string]any {
	source := map[string]any{
		"layer":      d.Layer.Kind,
		"name":       d.Layer.Name,
		"identifier": d.Layer.Identifier,
		"file":       d.RelativePath,
		"line":       d.Line,
	}
	if d.Layer.Position != nil {
		source["position"] = *d.Layer.Position
	}
	return source
}

// Database is the effective culture and tradition data of one playset.
type Database struct {
	PlaysetName string
	Cultures    map[string]Definition
	Traditions  map[string]Definition
	Warnings    []report.Warning
}

// virtualFile is the file that wins for one relative path.
type virtualFile struct {
	RelativePath string
	AbsolutePath string
	Layer        Layer
}

// gameRoot returns the directory holding the game's own data, which is either
// the install directory or its game/ subdirectory.
func gameRoot(gameDir string) (string, error) {
	for _, candidate := range []string{gameDir, filepath.Join(gameDir, "game")} {
		if fsutil.IsDir(filepath.Join(candidate, CulturesPath)) &&
			fsutil.IsDir(filepath.Join(candidate, TraditionsPath)) {
			return fsutil.MustAbs(candidate), nil
		}
	}
	return "", errorf("CK3 data directories were not found below %s; expected %s and %s, optionally below game/",
		gameDir, CulturesPath, TraditionsPath)
}

// immediateTextFiles lists the .txt files directly inside one data directory.
// CK3 does not recurse into these, so neither does this.
func immediateTextFiles(root, relativeDir string) ([]string, error) {
	directory := filepath.Join(root, filepath.FromSlash(relativeDir))
	entries, err := os.ReadDir(directory)
	if err != nil {
		if os.IsNotExist(err) {
			return nil, nil
		}
		return nil, errorf("could not list %s: %v", directory, err)
	}
	var names []string
	for _, entry := range entries {
		if entry.IsDir() || filepath.Ext(entry.Name()) != ".txt" {
			continue
		}
		path := filepath.Join(directory, entry.Name())
		if !fsutil.IsFile(path) {
			continue
		}
		names = append(names, entry.Name())
	}
	sort.Strings(names)
	return names, nil
}

// virtualFiles applies the load order to one data directory: later layers win,
// and a layer that replaces the directory removes everything below it.
func virtualFiles(root string, ordered []Layer, relativeDir string) ([]virtualFile, error) {
	files := map[string]virtualFile{}

	vanillaReplaced := false
	for _, layer := range ordered {
		for _, replacePath := range layer.ReplacePaths {
			if replacePath == relativeDir {
				vanillaReplaced = true
			}
		}
	}
	vanilla := Layer{Kind: "game", Name: "Crusader Kings III", Identifier: "vanilla", Root: root}

	add := func(layer Layer) error {
		names, err := immediateTextFiles(layer.Root, relativeDir)
		if err != nil {
			return err
		}
		for _, name := range names {
			relativePath := relativeDir + "/" + name
			files[relativePath] = virtualFile{
				RelativePath: relativePath,
				AbsolutePath: filepath.Join(layer.Root, filepath.FromSlash(relativePath)),
				Layer:        layer,
			}
		}
		return nil
	}

	if !vanillaReplaced {
		if err := add(vanilla); err != nil {
			return nil, err
		}
	}
	for _, layer := range ordered {
		if err := add(layer); err != nil {
			return nil, err
		}
	}

	keys := make([]string, 0, len(files))
	for key := range files {
		keys = append(keys, key)
	}
	sort.Strings(keys)
	result := make([]virtualFile, 0, len(keys))
	for _, key := range keys {
		result = append(result, files[key])
	}
	return result, nil
}

// readSource reads a data file with the newline translation Python's text mode
// applied, so quoted definitions do not carry a mod's CRLF endings.
func readSource(path string) (string, error) {
	text, err := fsutil.ReadTextBOM(path)
	if err != nil {
		return "", errorf("could not read %s: %v", path, err)
	}
	text = strings.ReplaceAll(text, "\r\n", "\n")
	return strings.ReplaceAll(text, "\r", "\n"), nil
}

// cultureTraditions collects the traditions one culture block assigns,
// including the DLC-gated ones.
func cultureTraditions(tokens []pdx.Token, matches map[int]int, block pdx.Block) []string {
	unique := map[string]bool{}
	for _, assignment := range pdx.DirectAssignments(tokens, matches, block.OpenIndex, block.CloseIndex) {
		if assignment.Value.Kind != pdx.TokenOpen {
			continue
		}
		switch assignment.Key.Value {
		case "traditions":
			for _, value := range pdx.BlockValues(tokens, assignment.ValueOpen, assignment.ValueClose) {
				unique[value] = true
			}
		case "dlc_tradition":
			for _, child := range pdx.DirectAssignments(tokens, matches, assignment.ValueOpen, assignment.ValueClose) {
				if child.Key.Value == "trait" && child.ValueClose < 0 && child.Value.Kind == pdx.TokenValue {
					unique[child.Value.Value] = true
				}
			}
		}
	}
	values := make([]string, 0, len(unique))
	for value := range unique {
		values = append(values, value)
	}
	sort.Strings(values)
	return values
}

// parseFiles reads the winning files in load order, so a later definition of
// the same identifier replaces an earlier one.
func parseFiles(files []virtualFile, withTraditions bool) (map[string]Definition, error) {
	definitions := map[string]Definition{}
	for _, file := range files {
		text, err := readSource(file.AbsolutePath)
		if err != nil {
			return nil, err
		}
		tokens, err := pdx.Tokenize(text)
		if err != nil {
			return nil, errorf("%s: %v", file.AbsolutePath, err)
		}
		matches, err := pdx.MatchBraces(tokens, file.AbsolutePath)
		if err != nil {
			return nil, err
		}
		runes := []rune(text)
		for _, block := range pdx.TopLevelBlocks(tokens, matches) {
			var traditions []string
			if withTraditions {
				traditions = cultureTraditions(tokens, matches, block)
			}
			definitions[block.Key.Value] = Definition{
				Identifier:   block.Key.Value,
				Text:         string(runes[block.Key.Start:tokens[block.CloseIndex].End]),
				Layer:        file.Layer,
				RelativePath: file.RelativePath,
				Line:         block.Key.Line,
				Traditions:   traditions,
			}
		}
	}
	return definitions, nil
}

// layerFromProvider maps a resolved load-order provider onto a culture layer.
func layerFromProvider(provider conflicts.Provider) Layer {
	position := provider.Position
	return Layer{
		Kind:         provider.Source,
		Name:         provider.Name,
		Identifier:   provider.StableID,
		Position:     &position,
		Root:         provider.Root,
		ReplacePaths: provider.ReplacePaths,
	}
}

// Load resolves the playset and parses its effective culture data.
func Load(gameDir, workshopDir, paradoxDir, databasePath, playsetName, configuredName string) (Database, error) {
	source, err := playset.LoadLive(databasePath, playsetName, configuredName)
	if err != nil {
		return Database{}, err
	}
	if strings.TrimSpace(source.Name) == "" {
		return Database{}, errorf("the selected playset has no name")
	}

	discovery := layers.Discover(source, workshopDir, paradoxDir)
	ordered := make([]Layer, 0, len(discovery.Providers))
	for _, provider := range discovery.Providers {
		ordered = append(ordered, layerFromProvider(provider))
	}

	root, err := gameRoot(gameDir)
	if err != nil {
		return Database{}, err
	}

	cultureFiles, err := virtualFiles(root, ordered, CulturesPath)
	if err != nil {
		return Database{}, err
	}
	traditionFiles, err := virtualFiles(root, ordered, TraditionsPath)
	if err != nil {
		return Database{}, err
	}
	cultureDefinitions, err := parseFiles(cultureFiles, true)
	if err != nil {
		return Database{}, err
	}
	traditionDefinitions, err := parseFiles(traditionFiles, false)
	if err != nil {
		return Database{}, err
	}

	return Database{
		PlaysetName: source.Name,
		Cultures:    cultureDefinitions,
		Traditions:  traditionDefinitions,
		Warnings:    discovery.Warnings,
	}, nil
}

// SelectCultures returns the cultures matching a tradition filter, sorted by
// identifier. An empty filter selects everything.
func (d Database) SelectCultures(requested []string, matchAll bool) ([]Definition, error) {
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
		return nil, errorf("unknown tradition(s): %s", strings.Join(unknown, ", "))
	}

	identifiers := make([]string, 0, len(d.Cultures))
	for identifier := range d.Cultures {
		identifiers = append(identifiers, identifier)
	}
	sort.Strings(identifiers)

	var selected []Definition
	for _, identifier := range identifiers {
		definition := d.Cultures[identifier]
		if len(unique) > 0 && !definition.matches(unique, matchAll) {
			continue
		}
		selected = append(selected, definition)
	}
	return selected, nil
}

func (d Definition) matches(requested []string, matchAll bool) bool {
	assigned := map[string]bool{}
	for _, tradition := range d.Traditions {
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

// SelectTraditions returns every tradition, sorted by identifier.
func (d Database) SelectTraditions() []Definition {
	identifiers := make([]string, 0, len(d.Traditions))
	for identifier := range d.Traditions {
		identifiers = append(identifiers, identifier)
	}
	sort.Strings(identifiers)
	selected := make([]Definition, 0, len(identifiers))
	for _, identifier := range identifiers {
		selected = append(selected, d.Traditions[identifier])
	}
	return selected
}

// Tradition returns one tradition definition.
func (d Database) Tradition(identifier string) (Definition, error) {
	definition, found := d.Traditions[identifier]
	if !found {
		return Definition{}, errorf("unknown tradition: %s", identifier)
	}
	return definition, nil
}
