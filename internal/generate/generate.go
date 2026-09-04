// Package generate stages one mod's generated outputs, checks them against the
// ownership its manifest declares, and promotes them only when asked.
//
// The generator body itself is Python: this package resolves the mod's sources,
// hands them to the sidecar in tools/gen over a JSON request, and owns
// everything that touches the repository.
package generate

import (
	"encoding/json"
	"fmt"
	"io/fs"
	"os"
	"os/exec"
	"path"
	"path/filepath"
	"sort"
	"strings"

	"codeberg.org/traidare/ck3_mods/internal/config"
	"codeberg.org/traidare/ck3_mods/internal/fsutil"
	"codeberg.org/traidare/ck3_mods/internal/sourcelock"
	"codeberg.org/traidare/ck3_mods/internal/workspace"
)

// RequestSchemaVersion is the generator protocol version the sidecar accepts.
const RequestSchemaVersion = 1

// PythonEnv names the environment variable that pins the sidecar interpreter.
// The Nix wrapper sets it; a plain checkout falls back to python3 on PATH.
const PythonEnv = "CK3MM_PYTHON"

// Result is one generator run, compared against what is checked in.
type Result struct {
	Slug         string
	StagedFiles  []string
	ChangedFiles []string
	StaleFiles   []string
	Promoted     bool
	Stdout       string
	Stderr       string

	// SourceChanges is how the files this run read differ from the checked-in
	// lock. It is reported separately from the output comparison because the
	// interesting case is precisely when the two disagree: an upstream file
	// moved and the generated output did not.
	SourceChanges sourcelock.Changes
}

// Current reports whether the checked-in tree already matches the run.
func (r Result) Current() bool {
	return len(r.ChangedFiles) == 0 && len(r.StaleFiles) == 0
}

// Pinned reports whether the run read exactly what the lock recorded.
func (r Result) Pinned() bool {
	return r.SourceChanges.Empty()
}

// Settled reports whether nothing at all needs review.
func (r Result) Settled() bool {
	return r.Current() && r.Pinned()
}

// Options selects what one run does.
type Options struct {
	// Apply promotes the staged tree instead of only reporting the difference.
	Apply bool
	// Generator options, forwarded to the sidecar verbatim.
	Values map[string]any
}

type request struct {
	SchemaVersion  int               `json:"schemaVersion"`
	ModSlug        string            `json:"modSlug"`
	Entrypoint     string            `json:"entrypoint"`
	WorkspaceRoot  string            `json:"workspaceRoot"`
	ModRoot        string            `json:"modRoot"`
	ToolingRoot    string            `json:"toolingRoot"`
	StageDir       string            `json:"stageDir"`
	Sources        map[string]string `json:"sources"`
	OwnedOutputs   []string          `json:"ownedOutputs"`
	OwnedArtifacts []string          `json:"ownedArtifacts"`
	Options        map[string]any    `json:"options"`
}

type response struct {
	SchemaVersion int      `json:"schemaVersion"`
	Status        string   `json:"status"`
	Error         string   `json:"error"`
	Traceback     string   `json:"traceback"`
	Stdout        string   `json:"stdout"`
	Stderr        string   `json:"stderr"`
	Reads         []string `json:"reads"`
}

type outputGroup struct {
	root     string
	files    map[string]string
	patterns []string
	artifact bool
}

func (g outputGroup) label(relative string) string {
	if g.artifact {
		return workspace.ArtifactPrefix + "/" + relative
	}
	return relative
}

// Run stages one mod's generator and compares the result with the tree.
func Run(space *workspace.Workspace, mod *workspace.Mod, settings config.Config, options Options) (Result, error) {
	if !mod.HasGenerator() {
		return Result{}, fmt.Errorf("mod %s has no configured generator", mod.Slug)
	}
	manifest := mod.Manifest
	generator := manifest.Generator

	sources, err := space.ResolveSources(manifest, settings, true)
	if err != nil {
		return Result{}, err
	}
	stateDir := space.StateDir()
	if err := os.MkdirAll(stateDir, 0o755); err != nil {
		return Result{}, err
	}
	stageDir, err := os.MkdirTemp(stateDir, "generate-"+mod.Slug+"-")
	if err != nil {
		return Result{}, err
	}
	defer os.RemoveAll(stageDir)

	answer, err := invoke(space, mod, stageDir, sources, options)
	if err != nil {
		return Result{}, err
	}
	result := Result{Slug: mod.Slug, Stdout: answer.Stdout, Stderr: answer.Stderr, Promoted: options.Apply}
	if answer.Status != "ok" {
		message := answer.Error
		if message == "" {
			message = "generator reported no reason"
		}
		return result, fmt.Errorf("generator for %s failed: %s", mod.Slug, message)
	}

	staged, err := regularFiles(stageDir)
	if err != nil {
		return result, err
	}
	if unexpected := undeclaredOutputs(staged, generator); len(unexpected) > 0 {
		return result, fmt.Errorf("generator for %s wrote undeclared outputs: %s",
			mod.Slug, strings.Join(unexpected, ", "))
	}
	result.StagedFiles = sortedKeys(staged)

	for _, group := range outputGroups(mod, generator, staged) {
		if err := updateGroup(&result, group, options.Apply); err != nil {
			return result, err
		}
	}

	if err := updateSourceLock(&result, space, mod, settings, answer.Reads, options.Apply); err != nil {
		return result, err
	}

	sort.Strings(result.ChangedFiles)
	sort.Strings(result.StaleFiles)
	return result, nil
}

// LockPath is where one mod's input pins are checked in.
func LockPath(mod *workspace.Mod) string {
	return filepath.Join(mod.ToolingRoot, sourcelock.FileName)
}

// LockRoots names the host directories input keys are taken relative to.
func LockRoots(space *workspace.Workspace, settings config.Config) sourcelock.Roots {
	return sourcelock.Roots{
		Workshop:   settings.WorkshopDir,
		Game:       settings.GameDir,
		Repository: space.Root,
	}
}

// updateSourceLock compares what the run read against the checked-in lock.
func updateSourceLock(result *Result, space *workspace.Workspace, mod *workspace.Mod, settings config.Config, reads []string, apply bool) error {
	path := LockPath(mod)
	recorded, err := sourcelock.Load(path)
	if err != nil {
		return err
	}
	current, err := sourcelock.Build(reads, LockRoots(space, settings))
	if err != nil {
		return err
	}
	result.SourceChanges = sourcelock.Compare(recorded, current)
	if !apply || result.Pinned() {
		return nil
	}
	return sourcelock.Save(path, current)
}

func undeclaredOutputs(staged map[string]string, generator *workspace.GeneratorSpec) []string {
	var unexpected []string
	for relative := range staged {
		if !stagedIsOwned(relative, generator) {
			unexpected = append(unexpected, relative)
		}
	}
	sort.Strings(unexpected)
	return unexpected
}

// outputGroups separates installable payload from non-shipping artifacts.
func outputGroups(mod *workspace.Mod, generator *workspace.GeneratorSpec, staged map[string]string) []outputGroup {
	payload := map[string]string{}
	artifacts := map[string]string{}
	for relative, stagedPath := range staged {
		if IsArtifact(relative) {
			artifacts[artifactRelative(relative)] = stagedPath
			continue
		}
		payload[relative] = stagedPath
	}
	return []outputGroup{
		{root: mod.Root, files: payload, patterns: generator.OwnedOutputs},
		{
			root: mod.ArtifactsRoot, files: artifacts,
			patterns: generator.OwnedArtifacts, artifact: true,
		},
	}
}

func updateGroup(result *Result, group outputGroup, apply bool) error {
	present, err := regularFiles(group.root)
	if err != nil {
		return err
	}
	var changed, stale []string
	for relative, stagedPath := range group.files {
		destination := filepath.Join(group.root, filepath.FromSlash(relative))
		same, err := sameFile(stagedPath, destination)
		if err != nil {
			return err
		}
		if !same {
			changed = append(changed, relative)
		}
	}
	for relative := range present {
		if _, staged := group.files[relative]; !staged && matchesDeclaration(relative, group.patterns) {
			stale = append(stale, relative)
		}
	}
	sort.Strings(changed)
	sort.Strings(stale)
	for _, relative := range changed {
		result.ChangedFiles = append(result.ChangedFiles, group.label(relative))
	}
	for _, relative := range stale {
		result.StaleFiles = append(result.StaleFiles, group.label(relative))
	}
	if !apply {
		return nil
	}
	for _, relative := range changed {
		destination := filepath.Join(group.root, filepath.FromSlash(relative))
		if err := promote(group.files[relative], destination); err != nil {
			return err
		}
	}
	for _, relative := range stale {
		destination := filepath.Join(group.root, filepath.FromSlash(relative))
		if err := os.Remove(destination); err != nil {
			return err
		}
		removeEmptyParents(destination, group.root)
	}
	return nil
}

// invoke runs the Python sidecar for one staged generator.
func invoke(space *workspace.Workspace, mod *workspace.Mod, stageDir string, sources map[string]string, options Options) (response, error) {
	values := options.Values
	if values == nil {
		values = map[string]any{}
	}
	payload, err := json.Marshal(request{
		SchemaVersion:  RequestSchemaVersion,
		ModSlug:        mod.Slug,
		Entrypoint:     mod.Manifest.Generator.Entrypoint,
		WorkspaceRoot:  space.Root,
		ModRoot:        mod.Root,
		ToolingRoot:    mod.ToolingRoot,
		StageDir:       stageDir,
		Sources:        sources,
		OwnedOutputs:   mod.Manifest.Generator.OwnedOutputs,
		OwnedArtifacts: mod.Manifest.Generator.OwnedArtifacts,
		Options:        values,
	})
	if err != nil {
		return response{}, err
	}

	interpreter := os.Getenv(PythonEnv)
	if interpreter == "" {
		interpreter = "python3"
	}
	command := exec.Command(interpreter, "-m", "gen")
	command.Dir = space.Root
	command.Stdin = strings.NewReader(string(payload))
	command.Env = append(os.Environ(), "PYTHONPATH="+pythonPath(space.Root))

	var stdout, stderr strings.Builder
	command.Stdout = &stdout
	command.Stderr = &stderr
	runError := command.Run()

	// The sidecar's own report is the last stdout line. Anything before it came
	// from a subprocess the generator started, whose output Python cannot
	// capture, so it is passed through as that generator's output.
	passthrough, report := splitReport(stdout.String())
	var answer response
	if report != "" {
		if err := json.Unmarshal([]byte(report), &answer); err != nil {
			return response{}, fmt.Errorf("generator sidecar for %s produced no usable result: %w\n%s",
				mod.Slug, err, stderr.String())
		}
	}
	if runError != nil && answer.Status == "" {
		return response{}, fmt.Errorf("generator sidecar for %s did not run: %w\n%s",
			mod.Slug, runError, stderr.String())
	}
	if answer.SchemaVersion != RequestSchemaVersion {
		return response{}, fmt.Errorf("generator sidecar for %s answered with schema version %d",
			mod.Slug, answer.SchemaVersion)
	}
	answer.Stdout = passthrough + answer.Stdout
	if answer.Traceback != "" {
		answer.Stderr += answer.Traceback
	}
	// Anything the interpreter itself wrote belongs with the generator's own
	// diagnostics rather than being swallowed.
	answer.Stderr += stderr.String()
	return answer, nil
}

// pythonPath puts the sidecar package first while keeping any inherited entries.
func pythonPath(root string) string {
	tools := filepath.Join(root, "tools")
	if inherited := os.Getenv("PYTHONPATH"); inherited != "" {
		return tools + string(os.PathListSeparator) + inherited
	}
	return tools
}

// splitReport separates passed-through generator output from the final report.
func splitReport(text string) (passthrough, report string) {
	trimmed := strings.TrimRight(text, "\n")
	if trimmed == "" {
		return "", ""
	}
	if index := strings.LastIndex(trimmed, "\n"); index >= 0 {
		return trimmed[:index+1], trimmed[index+1:]
	}
	return "", trimmed
}

// IsArtifact reports whether a staged path belongs to the tooling tree.
func IsArtifact(relative string) bool {
	return firstSegment(relative) == workspace.ArtifactPrefix
}

func artifactRelative(relative string) string {
	_, rest, _ := strings.Cut(relative, "/")
	return rest
}

func firstSegment(relative string) string {
	segment, _, _ := strings.Cut(relative, "/")
	return segment
}

func stagedIsOwned(relative string, generator *workspace.GeneratorSpec) bool {
	if IsArtifact(relative) {
		rest := artifactRelative(relative)
		return rest != "" && matchesDeclaration(rest, generator.OwnedArtifacts)
	}
	return matchesDeclaration(relative, generator.OwnedOutputs)
}

// matchesDeclaration matches exact files, directory prefixes, and globs.
func matchesDeclaration(relative string, patterns []string) bool {
	for _, pattern := range patterns {
		if strings.ContainsAny(pattern, "*?[") {
			if matched, err := path.Match(pattern, relative); err == nil && matched {
				return true
			}
			continue
		}
		if relative == pattern || strings.HasPrefix(relative, strings.TrimSuffix(pattern, "/")+"/") {
			return true
		}
	}
	return false
}

// regularFiles maps every regular file below root to its absolute path.
//
// A generated tree that contains symlinks cannot be promoted faithfully, so
// finding one is an error rather than something to resolve.
func regularFiles(root string) (map[string]string, error) {
	files := map[string]string{}
	if !fsutil.IsDir(root) {
		return files, nil
	}
	err := filepath.WalkDir(root, func(current string, entry fs.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if entry.Type()&fs.ModeSymlink != 0 {
			return fmt.Errorf("generated outputs must not be symlinks: %s", current)
		}
		if !entry.Type().IsRegular() {
			return nil
		}
		relative, err := filepath.Rel(root, current)
		if err != nil {
			return err
		}
		files[filepath.ToSlash(relative)] = current
		return nil
	})
	if err != nil {
		return nil, err
	}
	return files, nil
}

func sortedKeys(files map[string]string) []string {
	keys := make([]string, 0, len(files))
	for key := range files {
		keys = append(keys, key)
	}
	sort.Strings(keys)
	return keys
}

func sameFile(staged, destination string) (bool, error) {
	stagedInfo, err := os.Stat(staged)
	if err != nil {
		return false, err
	}
	destinationInfo, err := os.Stat(destination)
	if err != nil || !destinationInfo.Mode().IsRegular() {
		return false, nil
	}
	if stagedInfo.Size() != destinationInfo.Size() {
		return false, nil
	}
	left, err := fsutil.Sha256File(staged)
	if err != nil {
		return false, err
	}
	right, err := fsutil.Sha256File(destination)
	if err != nil {
		return false, err
	}
	return left == right, nil
}

// promote copies one staged file over its checked-in destination atomically,
// keeping the mode the generator gave it.
func promote(staged, destination string) error {
	info, err := os.Stat(staged)
	if err != nil {
		return err
	}
	content, err := os.ReadFile(staged)
	if err != nil {
		return err
	}
	return fsutil.WriteFileAtomic(destination, content, info.Mode().Perm())
}

func removeEmptyParents(path, stop string) {
	parent := filepath.Dir(path)
	for parent != stop && strings.HasPrefix(parent, stop+string(filepath.Separator)) {
		if err := os.Remove(parent); err != nil {
			return
		}
		parent = filepath.Dir(parent)
	}
}
