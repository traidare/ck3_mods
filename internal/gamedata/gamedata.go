// Package gamedata reads the effective contents of a live playset's game-data
// directories.
//
// It resolves the load order with internal/layers, so it sees exactly the files
// CK3 would load, including replace_path shadowing. It knows nothing about any
// particular database: callers name a directory, get the winning definitions
// back, and read their fields through the schema-free accessors below.
package gamedata

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

// Layer is one provider of game data, vanilla included.
type Layer struct {
	Kind         string
	Name         string
	Identifier   string
	Position     *int
	Root         string
	ReplacePaths []string
}

// Definition is one block as the playset effectively defines it, together with
// where the winning definition came from.
type Definition struct {
	Identifier   string
	Text         string
	Layer        Layer
	RelativePath string
	Line         int
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

// Source is one resolved playset: the game root and the ordered mod layers on
// top of it.
type Source struct {
	PlaysetName string
	Root        string
	Layers      []Layer
	Warnings    []report.Warning
}

// virtualFile is the file that wins for one relative path.
type virtualFile struct {
	RelativePath string
	AbsolutePath string
	Layer        Layer
}

// gameRoot returns the directory holding the game's own data, which is either
// the install directory or its game/ subdirectory. requiredDirs are the data
// directories that must exist below it for the candidate to be the real root.
func gameRoot(gameDir string, requiredDirs []string) (string, error) {
	for _, candidate := range []string{gameDir, filepath.Join(gameDir, "game")} {
		found := true
		for _, relativeDir := range requiredDirs {
			if !fsutil.IsDir(filepath.Join(candidate, filepath.FromSlash(relativeDir))) {
				found = false
				break
			}
		}
		if found {
			return fsutil.MustAbs(candidate), nil
		}
	}
	return "", fmt.Errorf("CK3 data directories were not found below %s; expected %s, optionally below game/",
		gameDir, strings.Join(requiredDirs, ", "))
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
		return nil, fmt.Errorf("could not list %s: %w", directory, err)
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
func (s Source) virtualFiles(relativeDir string) ([]virtualFile, error) {
	files := map[string]virtualFile{}

	vanillaReplaced := false
	for _, layer := range s.Layers {
		for _, replacePath := range layer.ReplacePaths {
			if replacePath == relativeDir {
				vanillaReplaced = true
			}
		}
	}
	vanilla := Layer{Kind: "game", Name: "Crusader Kings III", Identifier: "vanilla", Root: s.Root}

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
	for _, layer := range s.Layers {
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

// readSource reads a data file with newline translation applied, so quoted
// definitions do not carry a mod's CRLF endings.
func readSource(path string) (string, error) {
	text, err := fsutil.ReadTextBOM(path)
	if err != nil {
		return "", fmt.Errorf("could not read %s: %w", path, err)
	}
	text = strings.ReplaceAll(text, "\r\n", "\n")
	return strings.ReplaceAll(text, "\r", "\n"), nil
}

// ParseDirectory applies the load order to one data directory and returns the
// winning top-level definition per identifier. Files are read in load order, so
// a later definition of the same identifier replaces an earlier one.
func (s Source) ParseDirectory(relativeDir string) (map[string]Definition, error) {
	files, err := s.virtualFiles(relativeDir)
	if err != nil {
		return nil, err
	}

	definitions := map[string]Definition{}
	for _, file := range files {
		text, err := readSource(file.AbsolutePath)
		if err != nil {
			return nil, err
		}
		tokens, err := pdx.Tokenize(text)
		if err != nil {
			return nil, fmt.Errorf("%s: %w", file.AbsolutePath, err)
		}
		matches, err := pdx.MatchBraces(tokens, file.AbsolutePath)
		if err != nil {
			return nil, err
		}
		runes := []rune(text)
		for _, block := range pdx.TopLevelBlocks(tokens, matches) {
			definitions[block.Key.Value] = Definition{
				Identifier:   block.Key.Value,
				Text:         string(runes[block.Key.Start:tokens[block.CloseIndex].End]),
				Layer:        file.Layer,
				RelativePath: file.RelativePath,
				Line:         block.Key.Line,
			}
		}
	}
	return definitions, nil
}

// layerFromProvider maps a resolved load-order provider onto a data layer.
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

// Open resolves the playset and locates the game root. requiredDirs are the
// relative data directories that must exist below it, which is how the game
// root is told apart from its parent install directory.
func Open(gameDir, workshopDir, paradoxDir, databasePath, playsetName, configuredName string,
	requiredDirs []string,
) (Source, error) {
	source, err := playset.LoadLive(databasePath, playsetName, configuredName)
	if err != nil {
		return Source{}, err
	}
	if strings.TrimSpace(source.Name) == "" {
		return Source{}, fmt.Errorf("the selected playset has no name")
	}

	discovery := layers.Discover(source, workshopDir, paradoxDir)
	ordered := make([]Layer, 0, len(discovery.Providers))
	for _, provider := range discovery.Providers {
		ordered = append(ordered, layerFromProvider(provider))
	}

	root, err := gameRoot(gameDir, requiredDirs)
	if err != nil {
		return Source{}, err
	}
	return Source{
		PlaysetName: source.Name,
		Root:        root,
		Layers:      ordered,
		Warnings:    discovery.Warnings,
	}, nil
}
