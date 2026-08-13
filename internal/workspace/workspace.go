// Package workspace discovers the repository root and pairs each installable
// payload under mods/ with its non-shipping tooling under workspace/.
package workspace

import (
	"fmt"
	"os"
	"path"
	"path/filepath"
	"sort"
	"strings"

	"github.com/BurntSushi/toml"

	"codeberg.org/traidare/ck3_mods/internal/config"
	"codeberg.org/traidare/ck3_mods/internal/fsutil"
)

// RootMarker names the file whose presence marks the workspace root.
const RootMarker = "ck3mm.toml"

// ArtifactPrefix is the staging prefix reserved for generated development
// artifacts. Generators stage there; the runner promotes into workspace/.
const ArtifactPrefix = "artifacts"

// SourceKinds are the logical source roots a manifest may declare.
var SourceKinds = []string{"game", "mod", "repository", "workshop"}

// DiscoverRoot walks up from start to the nearest directory holding ck3mm.toml.
func DiscoverRoot(start string) (string, error) {
	candidate := start
	if candidate == "" {
		working, err := os.Getwd()
		if err != nil {
			return "", fmt.Errorf("cannot determine the working directory: %w", err)
		}
		candidate = working
	}
	if info, err := os.Stat(candidate); err == nil && !info.IsDir() {
		candidate = filepath.Dir(candidate)
	}
	candidate = fsutil.MustAbs(candidate)

	for {
		if fsutil.IsFile(filepath.Join(candidate, RootMarker)) {
			return candidate, nil
		}
		parent := filepath.Dir(candidate)
		if parent == candidate {
			return "", fmt.Errorf("no %s found from %s", RootMarker, fsutil.MustAbs(start))
		}
		candidate = parent
	}
}

// Settings is the repository layout declared by ck3mm.toml.
type Settings struct {
	ModsDir        string
	ToolingDir     string
	StateDir       string
	Descriptor     string
	Manifest       string
	ArtifactsDir   string
	InstallExclude []string
}

// DefaultSettings returns the layout assumed when ck3mm.toml omits a field.
func DefaultSettings() Settings {
	return Settings{
		ModsDir:        "mods",
		ToolingDir:     "workspace",
		StateDir:       ".ignored/ck3mm",
		Descriptor:     "descriptor.mod",
		Manifest:       "mod.toml",
		ArtifactsDir:   ArtifactPrefix,
		InstallExclude: []string{"README.md"},
	}
}

type settingsFile struct {
	Workspace struct {
		ModsDir        *string  `toml:"mods_dir"`
		ToolingDir     *string  `toml:"tooling_dir"`
		StateDir       *string  `toml:"state_dir"`
		Descriptor     *string  `toml:"descriptor"`
		Manifest       *string  `toml:"manifest"`
		ArtifactsDir   *string  `toml:"artifacts_dir"`
		InstallExclude []string `toml:"install_exclude"`
	} `toml:"workspace"`
}

// LoadSettings reads the [workspace] table from the root marker.
func LoadSettings(root string) (Settings, error) {
	markerPath := filepath.Join(root, RootMarker)
	var file settingsFile
	if _, err := toml.DecodeFile(markerPath, &file); err != nil {
		return Settings{}, fmt.Errorf("invalid TOML in %s: %w", markerPath, err)
	}

	settings := DefaultSettings()
	fields := []struct {
		name  string
		value *string
		into  *string
	}{
		{"mods_dir", file.Workspace.ModsDir, &settings.ModsDir},
		{"tooling_dir", file.Workspace.ToolingDir, &settings.ToolingDir},
		{"state_dir", file.Workspace.StateDir, &settings.StateDir},
		{"descriptor", file.Workspace.Descriptor, &settings.Descriptor},
		{"manifest", file.Workspace.Manifest, &settings.Manifest},
		{"artifacts_dir", file.Workspace.ArtifactsDir, &settings.ArtifactsDir},
	}
	for _, field := range fields {
		if field.value == nil {
			continue
		}
		trimmed := strings.TrimSpace(*field.value)
		if trimmed == "" {
			return Settings{}, fmt.Errorf("%s: workspace.%s must be a non-empty string", RootMarker, field.name)
		}
		*field.into = trimmed
	}
	if file.Workspace.InstallExclude != nil {
		settings.InstallExclude = file.Workspace.InstallExclude
	}
	return settings, nil
}

// SourceSpec is one logical, host-independent input a generator declares.
type SourceSpec struct {
	Name   string
	Kind   string
	Path   string
	ItemID string
	Mod    string
}

// GeneratorSpec declares a mod's generator and everything it owns.
//
// OwnedOutputs are payload paths promoted into mods/<slug>/; OwnedArtifacts are
// development paths promoted into workspace/<slug>/artifacts/ and never
// installed.
type GeneratorSpec struct {
	Entrypoint     string
	OwnedOutputs   []string
	OwnedArtifacts []string
}

// Manifest is one workspace/<slug>/mod.toml.
type Manifest struct {
	Path      string
	Slug      string
	Generator *GeneratorSpec
	Sources   []SourceSpec
}

// Mod pairs an installable payload root with its tooling root.
type Mod struct {
	Slug           string
	Root           string
	ToolingRoot    string
	DescriptorPath string
	ManifestPath   string
	ArtifactsRoot  string
	Manifest       *Manifest
}

// HasGenerator reports whether this mod's manifest declares a generator.
func (m Mod) HasGenerator() bool {
	return m.Manifest != nil && m.Manifest.Generator != nil
}

// relativePath validates a declared POSIX path that must stay inside its root.
func relativePath(value, fieldName string, allowGlob bool) (string, error) {
	trimmed := strings.TrimSpace(value)
	if trimmed == "" {
		return "", fmt.Errorf("%s must be a non-empty POSIX path", fieldName)
	}
	text := strings.ReplaceAll(trimmed, `\`, "/")
	if strings.HasPrefix(text, "/") {
		return "", fmt.Errorf("%s must stay within its declared root: %s", fieldName, value)
	}
	for _, part := range strings.Split(text, "/") {
		if part == ".." {
			return "", fmt.Errorf("%s must stay within its declared root: %s", fieldName, value)
		}
	}
	if !allowGlob && strings.ContainsAny(text, "*?[") {
		return "", fmt.Errorf("%s must not contain a glob: %s", fieldName, value)
	}
	normalized := path.Clean(text)
	if normalized == "" || normalized == "." {
		return "", fmt.Errorf("%s must not be empty", fieldName)
	}
	return normalized, nil
}

type manifestFile struct {
	Generator *struct {
		Entrypoint     string   `toml:"entrypoint"`
		OwnedOutputs   []string `toml:"owned_outputs"`
		OwnedArtifacts []string `toml:"owned_artifacts"`
	} `toml:"generator"`
	Sources []struct {
		Name   string `toml:"name"`
		Kind   string `toml:"kind"`
		Path   string `toml:"path"`
		ItemID any    `toml:"item_id"`
		Mod    string `toml:"mod"`
	} `toml:"sources"`
}

func parseGenerator(raw manifestFile, manifestPath string) (*GeneratorSpec, error) {
	if raw.Generator == nil {
		return nil, nil
	}
	entrypoint := strings.TrimSpace(raw.Generator.Entrypoint)
	if entrypoint == "" {
		return nil, fmt.Errorf("%s: generator.entrypoint is required", manifestPath)
	}
	modulePath, function, found := strings.Cut(entrypoint, ":")
	if !found || !isIdentifier(function) {
		return nil, fmt.Errorf("%s: generator.entrypoint must be FILE.py:function", manifestPath)
	}
	modulePath, err := relativePath(modulePath, "generator.entrypoint module", false)
	if err != nil {
		return nil, err
	}
	if !strings.HasSuffix(modulePath, ".py") {
		return nil, fmt.Errorf("%s: generator entrypoint must use a .py file", manifestPath)
	}

	outputs, err := normalizeList(raw.Generator.OwnedOutputs, "generator.owned_outputs")
	if err != nil {
		return nil, err
	}
	if len(outputs) == 0 {
		return nil, fmt.Errorf("%s: generator.owned_outputs must not be empty", manifestPath)
	}
	for _, output := range outputs {
		if strings.Split(output, "/")[0] == ArtifactPrefix {
			return nil, fmt.Errorf("%s: %s/ is reserved for generator.owned_artifacts: %s",
				manifestPath, ArtifactPrefix, output)
		}
	}
	artifacts, err := normalizeList(raw.Generator.OwnedArtifacts, "generator.owned_artifacts")
	if err != nil {
		return nil, err
	}
	return &GeneratorSpec{
		Entrypoint:     modulePath + ":" + function,
		OwnedOutputs:   outputs,
		OwnedArtifacts: artifacts,
	}, nil
}

func normalizeList(values []string, fieldName string) ([]string, error) {
	result := make([]string, 0, len(values))
	for _, value := range values {
		normalized, err := relativePath(value, fieldName, true)
		if err != nil {
			return nil, err
		}
		result = append(result, normalized)
	}
	return result, nil
}

func parseSources(raw manifestFile, manifestPath string) ([]SourceSpec, error) {
	var sources []SourceSpec
	seen := map[string]bool{}
	for _, entry := range raw.Sources {
		name := strings.TrimSpace(entry.Name)
		if name == "" {
			return nil, fmt.Errorf("%s: each source requires a non-empty name", manifestPath)
		}
		if !validKind(entry.Kind) {
			return nil, fmt.Errorf("%s: source %q has invalid kind %q; expected one of %s",
				manifestPath, name, entry.Kind, strings.Join(SourceKinds, ", "))
		}

		source := SourceSpec{Name: name, Kind: entry.Kind, Mod: strings.TrimSpace(entry.Mod)}
		if strings.TrimSpace(entry.Path) != "" {
			normalized, err := relativePath(entry.Path, "source "+name+".path", false)
			if err != nil {
				return nil, err
			}
			source.Path = normalized
		}
		switch value := entry.ItemID.(type) {
		case nil:
		case string:
			source.ItemID = value
		case int64:
			source.ItemID = fmt.Sprintf("%d", value)
		default:
			source.ItemID = fmt.Sprintf("%v", value)
		}

		switch entry.Kind {
		case "workshop":
			if source.ItemID == "" {
				return nil, fmt.Errorf("%s: workshop source %q requires item_id", manifestPath, name)
			}
		case "game", "repository":
			if source.Path == "" {
				return nil, fmt.Errorf("%s: %s source %q requires path", manifestPath, entry.Kind, name)
			}
		case "mod":
			if source.Mod == "" {
				return nil, fmt.Errorf("%s: mod source %q requires mod", manifestPath, name)
			}
		}

		if seen[name] {
			return nil, fmt.Errorf("%s: source names must be unique", manifestPath)
		}
		seen[name] = true
		sources = append(sources, source)
	}
	return sources, nil
}

func validKind(kind string) bool {
	for _, candidate := range SourceKinds {
		if candidate == kind {
			return true
		}
	}
	return false
}

func isIdentifier(value string) bool {
	if value == "" {
		return false
	}
	for index, character := range value {
		isLetter := character == '_' ||
			(character >= 'a' && character <= 'z') ||
			(character >= 'A' && character <= 'Z')
		isDigit := character >= '0' && character <= '9'
		if !isLetter && !(index > 0 && isDigit) {
			return false
		}
	}
	return true
}

// LoadManifest reads one workspace/<slug>/mod.toml.
func LoadManifest(manifestPath, defaultSlug string) (*Manifest, error) {
	var raw manifestFile
	metadata, err := toml.DecodeFile(manifestPath, &raw)
	if err != nil {
		if os.IsNotExist(err) {
			return nil, fmt.Errorf("workspace metadata not found: %s", manifestPath)
		}
		return nil, fmt.Errorf("invalid TOML in %s: %w", manifestPath, err)
	}
	if undecoded := metadata.Undecoded(); len(undecoded) > 0 {
		keys := make([]string, len(undecoded))
		for index, key := range undecoded {
			keys[index] = key.String()
		}
		sort.Strings(keys)
		return nil, fmt.Errorf("unknown field(s) in %s: %s", manifestPath, strings.Join(keys, ", "))
	}
	slug := strings.TrimSpace(defaultSlug)
	if slug == "." || slug == ".." || strings.ContainsAny(slug, `/\`) {
		return nil, fmt.Errorf("invalid mod directory name %q", slug)
	}

	generator, err := parseGenerator(raw, manifestPath)
	if err != nil {
		return nil, err
	}
	sources, err := parseSources(raw, manifestPath)
	if err != nil {
		return nil, err
	}
	return &Manifest{
		Path:      fsutil.MustAbs(manifestPath),
		Slug:      slug,
		Generator: generator,
		Sources:   sources,
	}, nil
}

// Workspace is one repository checkout and its declared layout.
type Workspace struct {
	Root     string
	Settings Settings
}

// Open discovers the workspace root from start and loads its settings.
func Open(start string) (*Workspace, error) {
	root, err := DiscoverRoot(start)
	if err != nil {
		return nil, err
	}
	settings, err := LoadSettings(root)
	if err != nil {
		return nil, err
	}
	return &Workspace{Root: root, Settings: settings}, nil
}

// ModsDir is the installable payload tree.
func (w *Workspace) ModsDir() string { return filepath.Join(w.Root, w.Settings.ModsDir) }

// ToolingDir is the never-installed per-mod tooling tree.
func (w *Workspace) ToolingDir() string { return filepath.Join(w.Root, w.Settings.ToolingDir) }

// StateDir holds local, git-ignored tool state.
func (w *Workspace) StateDir() string { return filepath.Join(w.Root, w.Settings.StateDir) }

func (w *Workspace) modAt(slug string) (*Mod, error) {
	modRoot := filepath.Join(w.ModsDir(), slug)
	toolingRoot := filepath.Join(w.ToolingDir(), slug)
	descriptorPath := filepath.Join(modRoot, w.Settings.Descriptor)
	manifestPath := filepath.Join(toolingRoot, w.Settings.Manifest)

	hasDescriptor := fsutil.IsFile(descriptorPath)
	hasManifest := fsutil.IsFile(manifestPath)
	if !hasDescriptor && !hasManifest {
		return nil, nil
	}

	var manifest *Manifest
	if hasManifest {
		loaded, err := LoadManifest(manifestPath, slug)
		if err != nil {
			return nil, err
		}
		manifest = loaded
	}
	return &Mod{
		Slug:           slug,
		Root:           modRoot,
		ToolingRoot:    toolingRoot,
		DescriptorPath: descriptorPath,
		ManifestPath:   manifestPath,
		ArtifactsRoot:  filepath.Join(toolingRoot, w.Settings.ArtifactsDir),
		Manifest:       manifest,
	}, nil
}

// Mods returns every mod in stable slug order, keyed by its payload directory.
func (w *Workspace) Mods() ([]*Mod, error) {
	entries, err := os.ReadDir(w.ModsDir())
	if err != nil {
		if os.IsNotExist(err) {
			return nil, nil
		}
		return nil, err
	}
	slugs := make([]string, 0, len(entries))
	for _, entry := range entries {
		if entry.IsDir() {
			slugs = append(slugs, entry.Name())
		}
	}
	sort.Strings(slugs)

	var mods []*Mod
	for _, slug := range slugs {
		mod, err := w.modAt(slug)
		if err != nil {
			return nil, err
		}
		if mod != nil {
			mods = append(mods, mod)
		}
	}
	return mods, nil
}

// Mod returns one mod by slug.
func (w *Workspace) Mod(slug string) (*Mod, error) {
	mods, err := w.Mods()
	if err != nil {
		return nil, err
	}
	for _, mod := range mods {
		if mod.Slug == slug {
			return mod, nil
		}
	}
	return nil, fmt.Errorf("unknown local mod: %s", slug)
}

// ResolveSource turns a portable logical source into a local read-only path.
func (w *Workspace) ResolveSource(source SourceSpec, settings config.Config, mustExist bool) (string, error) {
	var base string
	switch source.Kind {
	case "workshop":
		if settings.WorkshopDir == "" {
			return "", fmt.Errorf("CK3_WORKSHOP_DIR is required for Workshop sources")
		}
		base = filepath.Join(settings.WorkshopDir, source.ItemID)
	case "game":
		if settings.GameDir == "" {
			return "", fmt.Errorf("CK3_GAME_DIR is required for game sources")
		}
		base = settings.GameDir
	case "repository":
		base = w.Root
	case "mod":
		mod, err := w.Mod(source.Mod)
		if err != nil {
			return "", err
		}
		base = mod.Root
	default:
		return "", fmt.Errorf("unsupported source kind: %s", source.Kind)
	}

	resolvedBase := fsutil.MustAbs(base)
	relative := source.Path
	if relative == "" {
		relative = "."
	}
	resolved := fsutil.MustAbs(filepath.Join(resolvedBase, filepath.FromSlash(relative)))
	if _, inside := fsutil.RelativeWithin(resolvedBase, resolved); !inside {
		return "", fmt.Errorf("source escapes its declared root: %s", source.Name)
	}
	if mustExist {
		if _, err := os.Stat(resolved); err != nil {
			return "", fmt.Errorf("source %q does not exist: %s", source.Name, resolved)
		}
	}
	return resolved, nil
}

// ResolveSources resolves every source a manifest declares, by name.
func (w *Workspace) ResolveSources(manifest *Manifest, settings config.Config, mustExist bool) (map[string]string, error) {
	resolved := map[string]string{}
	for _, source := range manifest.Sources {
		path, err := w.ResolveSource(source, settings, mustExist)
		if err != nil {
			return nil, err
		}
		resolved[source.Name] = path
	}
	return resolved, nil
}
