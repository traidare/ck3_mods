package sourcelock

import (
	"os"
	"path/filepath"
	"testing"
)

// roots builds a workspace-shaped set of temporary roots.
func roots(t *testing.T) (Roots, string, string) {
	t.Helper()
	base := t.TempDir()
	workshop := filepath.Join(base, "workshop")
	repository := filepath.Join(base, "repo")
	for _, dir := range []string{workshop, repository} {
		if err := os.MkdirAll(dir, 0o755); err != nil {
			t.Fatal(err)
		}
	}
	return Roots{Workshop: workshop, Repository: repository}, workshop, repository
}

func write(t *testing.T, path, content string) string {
	t.Helper()
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, []byte(content), 0o644); err != nil {
		t.Fatal(err)
	}
	return path
}

func TestCanonicalNamespacesEachRoot(t *testing.T) {
	set, workshop, repository := roots(t)
	cases := map[string]string{
		write(t, filepath.Join(workshop, "2962333032", "common", "traits.txt"), "a"): "workshop/2962333032/common/traits.txt",
		write(t, filepath.Join(repository, "mods", "x", "descriptor.mod"), "b"):      "repo/mods/x/descriptor.mod",
	}
	for path, want := range cases {
		key, err := Canonical(path, set)
		if err != nil {
			t.Fatalf("%s: %v", path, err)
		}
		if key != want {
			t.Errorf("Canonical(%s) = %q, want %q", path, key, want)
		}
		back, err := Resolve(key, set)
		if err != nil {
			t.Fatalf("%s: %v", key, err)
		}
		if back != path {
			t.Errorf("Resolve(%q) = %q, want %q", key, back, path)
		}
	}
}

// A read outside every declared root must be refused rather than silently
// pinned under a wrong namespace.
func TestCanonicalRejectsPathsOutsideEveryRoot(t *testing.T) {
	set, _, _ := roots(t)
	stray := write(t, filepath.Join(t.TempDir(), "stray.txt"), "x")
	if _, err := Canonical(stray, set); err == nil {
		t.Fatal("expected an error for a path outside every root")
	}
}

// The repository root can contain the others, so the longest match has to win.
func TestCanonicalPrefersTheDeepestRoot(t *testing.T) {
	base := t.TempDir()
	nested := filepath.Join(base, "workshop")
	set := Roots{Repository: base, Workshop: nested}
	path := write(t, filepath.Join(nested, "123", "file.txt"), "a")
	key, err := Canonical(path, set)
	if err != nil {
		t.Fatal(err)
	}
	if key != "workshop/123/file.txt" {
		t.Errorf("key = %q, want workshop/123/file.txt", key)
	}
}

func TestWorkshopID(t *testing.T) {
	for key, want := range map[string]string{
		"workshop/2962333032/common/traits.txt": "2962333032",
		"repo/mods/x/file.txt":                  "",
		"game/common/traits.txt":                "",
		"workshop/":                             "",
	} {
		id, found := WorkshopID(key)
		if found != (want != "") || id != want {
			t.Errorf("WorkshopID(%q) = %q,%v; want %q", key, id, found, want)
		}
	}
}

func TestBuildAndVerifyDetectChangeAndRemoval(t *testing.T) {
	set, workshop, _ := roots(t)
	stable := write(t, filepath.Join(workshop, "1", "stable.txt"), "unchanged")
	edited := write(t, filepath.Join(workshop, "1", "edited.txt"), "before")
	vanished := write(t, filepath.Join(workshop, "1", "vanished.txt"), "here")

	lock, err := Build([]string{stable, edited, vanished}, set)
	if err != nil {
		t.Fatal(err)
	}
	if len(lock.Files) != 3 {
		t.Fatalf("locked %d files, want 3", len(lock.Files))
	}

	changes, err := Verify(lock, set)
	if err != nil {
		t.Fatal(err)
	}
	if !changes.Empty() {
		t.Fatalf("a pristine tree reported %+v", changes)
	}

	write(t, edited, "after")
	if err := os.Remove(vanished); err != nil {
		t.Fatal(err)
	}
	changes, err = Verify(lock, set)
	if err != nil {
		t.Fatal(err)
	}
	if len(changes.Changed) != 1 || changes.Changed[0] != "workshop/1/edited.txt" {
		t.Errorf("changed = %v, want [workshop/1/edited.txt]", changes.Changed)
	}
	if len(changes.Removed) != 1 || changes.Removed[0] != "workshop/1/vanished.txt" {
		t.Errorf("removed = %v, want [workshop/1/vanished.txt]", changes.Removed)
	}
	if changes.Total() != 2 {
		t.Errorf("total = %d, want 2", changes.Total())
	}
}

func TestLoadTreatsAMissingLockAsEmpty(t *testing.T) {
	lock, err := Load(filepath.Join(t.TempDir(), FileName))
	if err != nil {
		t.Fatal(err)
	}
	if len(lock.Files) != 0 || lock.SchemaVersion != SchemaVersion {
		t.Errorf("missing lock = %+v", lock)
	}
}

func TestLoadRejectsAnUnknownSchemaVersion(t *testing.T) {
	path := write(t, filepath.Join(t.TempDir(), FileName), `{"schemaVersion":99,"files":{}}`)
	if _, err := Load(path); err == nil {
		t.Fatal("expected an error for an unsupported schema version")
	}
}

// A run that reads nothing must clear a stale lock instead of leaving pins that
// no longer describe the generator.
func TestSaveRemovesAnEmptyLock(t *testing.T) {
	path := write(t, filepath.Join(t.TempDir(), FileName), `{"schemaVersion":1,"files":{}}`)
	if err := Save(path, Lock{SchemaVersion: SchemaVersion}); err != nil {
		t.Fatal(err)
	}
	if _, err := os.Stat(path); !os.IsNotExist(err) {
		t.Fatalf("lock still present: %v", err)
	}
}

func TestSaveThenLoadRoundTrips(t *testing.T) {
	set, workshop, _ := roots(t)
	file := write(t, filepath.Join(workshop, "7", "a.txt"), "content")
	built, err := Build([]string{file}, set)
	if err != nil {
		t.Fatal(err)
	}
	path := filepath.Join(t.TempDir(), FileName)
	if err := Save(path, built); err != nil {
		t.Fatal(err)
	}
	loaded, err := Load(path)
	if err != nil {
		t.Fatal(err)
	}
	if !Compare(loaded, built).Empty() {
		t.Errorf("round trip lost pins: %+v vs %+v", loaded, built)
	}
}

func TestCompareReportsAdditions(t *testing.T) {
	recorded := Lock{SchemaVersion: SchemaVersion, Files: map[string]Entry{
		"workshop/1/a.txt": {Sha256: "aa"},
	}}
	current := Lock{SchemaVersion: SchemaVersion, Files: map[string]Entry{
		"workshop/1/a.txt": {Sha256: "aa"},
		"workshop/1/b.txt": {Sha256: "bb"},
	}}
	changes := Compare(recorded, current)
	if len(changes.Added) != 1 || changes.Added[0] != "workshop/1/b.txt" {
		t.Errorf("added = %v", changes.Added)
	}
	if len(changes.Changed) != 0 || len(changes.Removed) != 0 {
		t.Errorf("unexpected drift: %+v", changes)
	}
}
