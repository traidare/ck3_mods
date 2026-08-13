// Package refs mirrors the game's syntax-reference sources into the local,
// git-ignored cache under references/generated.
//
// Planning and checking never write; only Apply does.
package refs

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"

	"codeberg.org/traidare/ck3_mods/internal/fsutil"
	"codeberg.org/traidare/ck3_mods/internal/jsonout"
	"codeberg.org/traidare/ck3_mods/internal/plan"
)

// ScriptDocLogs are the script-documentation dumps CK3 writes on request.
var ScriptDocLogs = []string{
	"effects.log",
	"event_scopes.log",
	"event_targets.log",
	"modifiers.log",
	"triggers.log",
}

// Copy is one cached file and the source it mirrors.
type Copy struct {
	Source       string
	Destination  string
	RelativePath string
}

// Plan is the derived mirror of the reference sources.
type Plan struct {
	GameDir       string
	ParadoxDir    string
	CacheRoot     string
	Copies        []Copy
	Removals      []string
	InfoFiles     int
	ScriptDocLogs int
}

// Check is the difference between the sources, the cache, and its manifest.
type Check struct {
	InfoFiles      int
	ScriptDocLogs  int
	Missing        []string
	Stale          []string
	Unexpected     []string
	ManifestErrors []string
}

// Current reports whether the cache needs no refresh.
func (c Check) Current() bool {
	return len(c.Missing) == 0 && len(c.Stale) == 0 &&
		len(c.Unexpected) == 0 && len(c.ManifestErrors) == 0
}

// infoRelative strips the game directory and its optional "game/" wrapper.
func infoRelative(path, gameDir string) (string, error) {
	relative, inside := fsutil.RelativeWithin(gameDir, path)
	if !inside || relative == "." {
		return "", fmt.Errorf("invalid .info source path: %s", path)
	}
	if relative == "game" {
		return "", fmt.Errorf("invalid .info source path: %s", path)
	}
	return strings.TrimPrefix(relative, "game/"), nil
}

// expectedFiles maps each cache-relative path to the source providing it.
func expectedFiles(gameDir, paradoxDir string) (map[string]string, int, int, error) {
	if !fsutil.IsDir(gameDir) {
		return nil, 0, 0, fmt.Errorf("CK3 game directory is missing: %s", gameDir)
	}
	if !fsutil.IsDir(paradoxDir) {
		return nil, 0, 0, fmt.Errorf("CK3 user-data directory is missing: %s", paradoxDir)
	}

	files, err := fsutil.WalkFiles(gameDir)
	if err != nil {
		return nil, 0, 0, fmt.Errorf("cannot scan %s: %w", gameDir, err)
	}
	expected := map[string]string{}
	infoCount := 0
	for _, relative := range files {
		if !strings.HasSuffix(relative, ".info") {
			continue
		}
		source := filepath.Join(gameDir, filepath.FromSlash(relative))
		trimmed, err := infoRelative(source, gameDir)
		if err != nil {
			return nil, 0, 0, err
		}
		key := "info/" + trimmed
		if _, clash := expected[key]; clash {
			return nil, 0, 0, fmt.Errorf("multiple .info sources map to %s", key)
		}
		expected[key] = source
		infoCount++
	}
	if infoCount == 0 {
		return nil, 0, 0, fmt.Errorf("no .info files found below game directory: %s", gameDir)
	}

	docs := 0
	for _, name := range ScriptDocLogs {
		source := filepath.Join(paradoxDir, "logs", name)
		if fsutil.IsFile(source) {
			expected["script_docs/"+name] = source
			docs++
		}
	}
	return expected, infoCount, docs, nil
}

// Build derives the mirror plan without touching the cache.
func Build(gameDir, paradoxDir, cacheRoot string) (*Plan, error) {
	game := fsutil.MustAbs(gameDir)
	paradox := fsutil.MustAbs(paradoxDir)
	cache := fsutil.MustAbs(cacheRoot)
	if _, inside := fsutil.RelativeWithin(game, cache); inside {
		return nil, fmt.Errorf("reference cache must not be inside the game directory")
	}
	if _, inside := fsutil.RelativeWithin(paradox, cache); inside {
		return nil, fmt.Errorf("reference cache must not be inside CK3 user data")
	}

	expected, infoCount, docsCount, err := expectedFiles(game, paradox)
	if err != nil {
		return nil, err
	}

	keys := make([]string, 0, len(expected))
	for key := range expected {
		keys = append(keys, key)
	}
	sort.Strings(keys)
	copies := make([]Copy, 0, len(keys))
	for _, key := range keys {
		copies = append(copies, Copy{
			Source:       expected[key],
			Destination:  filepath.Join(cache, filepath.FromSlash(key)),
			RelativePath: key,
		})
	}

	var removals []string
	for _, name := range []string{"info", "script_docs"} {
		root := filepath.Join(cache, name)
		if !fsutil.IsDir(root) {
			continue
		}
		present, err := fsutil.WalkFiles(root)
		if err != nil {
			return nil, fmt.Errorf("cannot scan %s: %w", root, err)
		}
		for _, relative := range present {
			key := name + "/" + relative
			if _, wanted := expected[key]; !wanted {
				removals = append(removals, filepath.Join(cache, filepath.FromSlash(key)))
			}
		}
	}
	sort.Strings(removals)

	return &Plan{
		GameDir:       game,
		ParadoxDir:    paradox,
		CacheRoot:     cache,
		Copies:        copies,
		Removals:      removals,
		InfoFiles:     infoCount,
		ScriptDocLogs: docsCount,
	}, nil
}

// Inspect compares sources, cached files, and the manifest without writing.
func Inspect(gameDir, paradoxDir, cacheRoot string) (Check, error) {
	built, err := Build(gameDir, paradoxDir, cacheRoot)
	if err != nil {
		return Check{}, err
	}
	return built.Check()
}

// Check reports what the plan would change.
func (p *Plan) Check() (Check, error) {
	result := Check{InfoFiles: p.InfoFiles, ScriptDocLogs: p.ScriptDocLogs}
	for _, item := range p.Copies {
		info, err := os.Lstat(item.Destination)
		if err != nil || !info.Mode().IsRegular() {
			result.Missing = append(result.Missing, item.RelativePath)
			continue
		}
		same, err := fsutil.SameContent(item.Source, item.Destination)
		if err != nil {
			return Check{}, fmt.Errorf("cannot compare %s: %w", item.RelativePath, err)
		}
		if !same {
			result.Stale = append(result.Stale, item.RelativePath)
		}
	}
	for _, path := range p.Removals {
		relative, _ := fsutil.RelativeWithin(p.CacheRoot, path)
		result.Unexpected = append(result.Unexpected, relative)
	}
	result.ManifestErrors = p.manifestErrors()
	return result, nil
}

func (p *Plan) manifestErrors() []string {
	path := filepath.Join(p.CacheRoot, "manifest.json")
	data, err := os.ReadFile(path)
	if err != nil {
		if os.IsNotExist(err) {
			return []string{"manifest.json is missing"}
		}
		return []string{fmt.Sprintf("manifest.json is invalid: %v", err)}
	}
	var manifest struct {
		InfoFiles     *int `json:"info_files"`
		ScriptDocLogs *int `json:"script_doc_logs"`
	}
	if err := json.Unmarshal(data, &manifest); err != nil {
		return []string{fmt.Sprintf("manifest.json is invalid: %v", err)}
	}
	var problems []string
	if manifest.InfoFiles == nil || *manifest.InfoFiles != p.InfoFiles {
		problems = append(problems, "manifest info_files count is stale")
	}
	if manifest.ScriptDocLogs == nil || *manifest.ScriptDocLogs != p.ScriptDocLogs {
		problems = append(problems, "manifest script_doc_logs count is stale")
	}
	return problems
}

// Apply mirrors the sources into the cache and returns the resulting check.
func (p *Plan) Apply(generatedAt time.Time) (Check, error) {
	operations := &plan.Plan{}
	for _, item := range p.Copies {
		operations.Add(plan.Op{Kind: plan.Copy, Source: item.Source, Path: item.Destination})
	}
	for _, path := range p.Removals {
		operations.Add(plan.Op{Kind: plan.Remove, Path: path})
	}
	for _, name := range []string{"info", "script_docs"} {
		operations.Add(plan.Op{Kind: plan.PruneDirs, Path: filepath.Join(p.CacheRoot, name)})
	}
	if err := operations.Apply(); err != nil {
		return Check{}, err
	}

	manifest, err := jsonout.Marshal(map[string]any{
		"generated_at":    isoUTC(generatedAt),
		"info_files":      p.InfoFiles,
		"script_doc_logs": p.ScriptDocLogs,
	})
	if err != nil {
		return Check{}, err
	}
	path := filepath.Join(p.CacheRoot, "manifest.json")
	if err := fsutil.WriteFileAtomic(path, manifest, 0o644); err != nil {
		return Check{}, fmt.Errorf("cannot write %s: %w", path, err)
	}
	// Re-derive the plan: the removals this one carries have just been done,
	// and reusing them would report them as still outstanding.
	return Inspect(p.GameDir, p.ParadoxDir, p.CacheRoot)
}

// isoUTC renders a timestamp the way datetime.isoformat does for UTC, so the
// manifest keeps the shape the Python tooling wrote.
func isoUTC(moment time.Time) string {
	return moment.UTC().Format("2006-01-02T15:04:05.000000") + "+00:00"
}

// Render writes the same report the Python command printed.
func (c Check) Render(builder *strings.Builder) {
	fmt.Fprintf(builder, "Info files: %d\n", c.InfoFiles)
	fmt.Fprintf(builder, "Script-doc logs: %d\n", c.ScriptDocLogs)
	sections := []struct {
		label  string
		values []string
	}{
		{"Missing", c.Missing},
		{"Stale", c.Stale},
		{"Unexpected", c.Unexpected},
		{"Manifest errors", c.ManifestErrors},
	}
	for _, section := range sections {
		if len(section.values) == 0 {
			continue
		}
		fmt.Fprintf(builder, "%s:\n", section.label)
		for _, value := range section.values {
			fmt.Fprintf(builder, "  %s\n", value)
		}
	}
	if c.Current() {
		builder.WriteString("References are current\n")
	} else {
		builder.WriteString("References need refresh\n")
	}
}

// JSON returns the machine-readable form of a check.
func (c Check) JSON() map[string]any {
	list := func(values []string) []string {
		if values == nil {
			return []string{}
		}
		return values
	}
	return map[string]any{
		"infoFiles":      c.InfoFiles,
		"scriptDocLogs":  c.ScriptDocLogs,
		"missing":        list(c.Missing),
		"stale":          list(c.Stale),
		"unexpected":     list(c.Unexpected),
		"manifestErrors": list(c.ManifestErrors),
		"current":        c.Current(),
	}
}
