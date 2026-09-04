// Package sourcelock records, by content, which upstream files a generator
// consumed.
//
// Declaring those files per module is not workable: most declared sources
// resolve to a whole Workshop root, and the largest is 13G. The sidecar reports
// what a run actually read instead, and this package turns those host paths
// into host-independent keys, hashes them, and compares them against the lock
// checked in beside the generator.
//
// The point is the case a staleness check cannot see: upstream changes a file
// the generator reads, but the generated output does not move. Without a lock
// that reads as "current" and the change is invisible.
package sourcelock

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"codeberg.org/traidare/ck3_mods/internal/fsutil"
)

// SchemaVersion is the lock format this package reads and writes.
const SchemaVersion = 1

// FileName is the per-module lock, tracked in git so an upstream change lands
// as a reviewable diff rather than a hidden state-directory mutation.
const FileName = "sources.lock.json"

// The namespaces a canonical key can start with. They are explicit so a key is
// self-describing and can never be ambiguous between two roots.
const (
	WorkshopNamespace   = "workshop"
	GameNamespace       = "game"
	RepositoryNamespace = "repo"
)

// Entry pins one upstream file.
type Entry struct {
	Sha256 string `json:"sha256"`
	Size   int64  `json:"size"`
}

// Lock is one module's recorded inputs, keyed by canonical path.
//
// Files is a map so encoding/json sorts it on the way out, which keeps the
// checked-in file stable across runs.
type Lock struct {
	SchemaVersion int              `json:"schemaVersion"`
	Files         map[string]Entry `json:"files"`
}

// Roots names the host directories canonical keys are taken relative to.
type Roots struct {
	Workshop   string
	Game       string
	Repository string
}

// Changes is the difference between two locks, or between a lock and disk.
type Changes struct {
	Added   []string
	Removed []string
	Changed []string
}

// Empty reports whether nothing moved.
func (c Changes) Empty() bool {
	return len(c.Added) == 0 && len(c.Removed) == 0 && len(c.Changed) == 0
}

// Total counts every difference, for a one-line summary.
func (c Changes) Total() int {
	return len(c.Added) + len(c.Removed) + len(c.Changed)
}

// WorkshopID returns the Workshop item a canonical key belongs to, if any.
func WorkshopID(key string) (string, bool) {
	rest, found := strings.CutPrefix(key, WorkshopNamespace+"/")
	if !found {
		return "", false
	}
	id, _, _ := strings.Cut(rest, "/")
	if id == "" {
		return "", false
	}
	return id, true
}

// realPath follows symlinks where it can. Source roots and the paths read below
// them have to be compared in one namespace, and only some of them are
// canonical to begin with; a root that cannot be resolved is used as given.
func realPath(path string) string {
	if path == "" {
		return ""
	}
	absolute := fsutil.MustAbs(path)
	resolved, err := filepath.EvalSymlinks(absolute)
	if err != nil {
		return absolute
	}
	return resolved
}

type namespacedRoot struct {
	namespace string
	path      string
}

func (r Roots) ordered() []namespacedRoot {
	var roots []namespacedRoot
	for _, candidate := range []namespacedRoot{
		{WorkshopNamespace, r.Workshop},
		{GameNamespace, r.Game},
		{RepositoryNamespace, r.Repository},
	} {
		if candidate.path == "" {
			continue
		}
		candidate.path = realPath(candidate.path)
		roots = append(roots, candidate)
	}
	// Longest first, so a root nested inside another still wins.
	sort.SliceStable(roots, func(left, right int) bool {
		return len(roots[left].path) > len(roots[right].path)
	})
	return roots
}

// Canonical turns one absolute host path into a host-independent key.
func Canonical(absolute string, roots Roots) (string, error) {
	target := realPath(absolute)
	for _, root := range roots.ordered() {
		relative, inside := fsutil.RelativeWithin(root.path, target)
		if !inside || relative == "." {
			continue
		}
		return root.namespace + "/" + relative, nil
	}
	return "", fmt.Errorf("read path is outside every known root: %s", absolute)
}

// Resolve turns a canonical key back into a host path.
func Resolve(key string, roots Roots) (string, error) {
	namespace, relative, found := strings.Cut(key, "/")
	if !found || relative == "" {
		return "", fmt.Errorf("malformed source key: %s", key)
	}
	var root string
	switch namespace {
	case WorkshopNamespace:
		root = roots.Workshop
	case GameNamespace:
		root = roots.Game
	case RepositoryNamespace:
		root = roots.Repository
	default:
		return "", fmt.Errorf("unknown source namespace %q in key: %s", namespace, key)
	}
	if root == "" {
		return "", fmt.Errorf("no %s root configured for key: %s", namespace, key)
	}
	return filepath.Join(root, filepath.FromSlash(relative)), nil
}

// Build hashes the paths one run read and returns the lock they imply.
func Build(paths []string, roots Roots) (Lock, error) {
	lock := Lock{SchemaVersion: SchemaVersion, Files: map[string]Entry{}}
	if len(paths) == 0 {
		return lock, nil
	}
	keys := make([]string, len(paths))
	for index, absolute := range paths {
		key, err := Canonical(absolute, roots)
		if err != nil {
			return Lock{}, err
		}
		keys[index] = key
	}
	for index, result := range fsutil.HashFiles(paths) {
		if result.Err != nil {
			return Lock{}, result.Err
		}
		info, err := os.Stat(paths[index])
		if err != nil {
			return Lock{}, err
		}
		lock.Files[keys[index]] = Entry{Sha256: result.Sha256, Size: info.Size()}
	}
	return lock, nil
}

// Compare reports how a freshly built lock differs from the recorded one.
func Compare(recorded, current Lock) Changes {
	var changes Changes
	for key, entry := range current.Files {
		previous, known := recorded.Files[key]
		switch {
		case !known:
			changes.Added = append(changes.Added, key)
		case previous.Sha256 != entry.Sha256:
			changes.Changed = append(changes.Changed, key)
		}
	}
	for key := range recorded.Files {
		if _, known := current.Files[key]; !known {
			changes.Removed = append(changes.Removed, key)
		}
	}
	sort.Strings(changes.Added)
	sort.Strings(changes.Removed)
	sort.Strings(changes.Changed)
	return changes
}

// Verify rehashes the files a lock names and reports what moved on disk.
//
// This is what answers "did these Workshop items change anything we consume"
// without running a single generator: it touches only the locked files.
func Verify(recorded Lock, roots Roots) (Changes, error) {
	keys := make([]string, 0, len(recorded.Files))
	for key := range recorded.Files {
		keys = append(keys, key)
	}
	sort.Strings(keys)

	paths := make([]string, len(keys))
	for index, key := range keys {
		path, err := Resolve(key, roots)
		if err != nil {
			return Changes{}, err
		}
		paths[index] = path
	}

	current := Lock{SchemaVersion: SchemaVersion, Files: map[string]Entry{}}
	for index, result := range fsutil.HashFiles(paths) {
		if result.Err != nil {
			// A vanished input is a removal, not a failure to report it.
			if os.IsNotExist(result.Err) {
				continue
			}
			return Changes{}, result.Err
		}
		current.Files[keys[index]] = Entry{Sha256: result.Sha256}
	}
	// Sizes are not compared here: the digest already decides, and stat'ing
	// every file again would only slow the sweep down.
	comparable := Lock{SchemaVersion: recorded.SchemaVersion, Files: map[string]Entry{}}
	for key, entry := range recorded.Files {
		comparable.Files[key] = Entry{Sha256: entry.Sha256}
	}
	return Compare(comparable, current), nil
}

// Load reads one module's lock. A missing lock is an empty one, so a module
// that has never been pinned reports every input as newly added.
func Load(path string) (Lock, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		if os.IsNotExist(err) {
			return Lock{SchemaVersion: SchemaVersion, Files: map[string]Entry{}}, nil
		}
		return Lock{}, err
	}
	var lock Lock
	if err := json.Unmarshal(data, &lock); err != nil {
		return Lock{}, fmt.Errorf("%s: %w", path, err)
	}
	if lock.SchemaVersion != SchemaVersion {
		return Lock{}, fmt.Errorf("%s: unsupported lock schema version %d", path, lock.SchemaVersion)
	}
	if lock.Files == nil {
		lock.Files = map[string]Entry{}
	}
	return lock, nil
}

// Save writes one module's lock, or removes it when the run read nothing.
func Save(path string, lock Lock) error {
	if len(lock.Files) == 0 {
		if err := os.Remove(path); err != nil && !os.IsNotExist(err) {
			return err
		}
		return nil
	}
	lock.SchemaVersion = SchemaVersion
	data, err := json.MarshalIndent(lock, "", "  ")
	if err != nil {
		return err
	}
	return fsutil.WriteFileAtomic(path, append(data, '\n'), 0o644)
}
