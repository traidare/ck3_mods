package install

import (
	"os"
	"path/filepath"
	"testing"

	"codeberg.org/traidare/ck3_mods/internal/plan"
)

func write(t *testing.T, path, content string) string {
	t.Helper()
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatalf("could not create %s: %v", filepath.Dir(path), err)
	}
	if err := os.WriteFile(path, []byte(content), 0o644); err != nil {
		t.Fatalf("could not write %s: %v", path, err)
	}
	return path
}

func TestClassifySplitsFilesByWhatTheDestinationHolds(t *testing.T) {
	sourceRoot, destinationRoot := t.TempDir(), t.TempDir()
	sourceFiles := map[string]string{
		"new.txt":        write(t, filepath.Join(sourceRoot, "new.txt"), "fresh"),
		"same.txt":       write(t, filepath.Join(sourceRoot, "same.txt"), "identical"),
		"resized.txt":    write(t, filepath.Join(sourceRoot, "resized.txt"), "a longer body"),
		"same_size.txt":  write(t, filepath.Join(sourceRoot, "same_size.txt"), "aaaa"),
		"nested/one.txt": write(t, filepath.Join(sourceRoot, "nested/one.txt"), "nested"),
	}
	installedFiles := map[string]string{
		"same.txt":       write(t, filepath.Join(destinationRoot, "same.txt"), "identical"),
		"resized.txt":    write(t, filepath.Join(destinationRoot, "resized.txt"), "short"),
		"same_size.txt":  write(t, filepath.Join(destinationRoot, "same_size.txt"), "bbbb"),
		"nested/one.txt": write(t, filepath.Join(destinationRoot, "nested/one.txt"), "nested"),
	}

	relatives := sortedKeys(sourceFiles)
	statuses, err := classify(relatives, sourceFiles, installedFiles)
	if err != nil {
		t.Fatalf("classify: %v", err)
	}

	got := map[string]plan.Status{}
	for index, relative := range relatives {
		got[relative] = statuses[index]
	}
	want := map[string]plan.Status{
		"new.txt":        plan.Added,
		"same.txt":       plan.Unchanged,
		"resized.txt":    plan.Changed,
		"same_size.txt":  plan.Changed,
		"nested/one.txt": plan.Unchanged,
	}
	for relative, expected := range want {
		if got[relative] != expected {
			t.Errorf("%s = %q, want %q", relative, got[relative], expected)
		}
	}
}

func TestClassifyBytesComparesTheDerivedDescriptor(t *testing.T) {
	root := t.TempDir()
	existing := write(t, filepath.Join(root, "mod.mod"), "name=\"Test\"\n")

	if status := classifyBytes(existing, []byte("name=\"Test\"\n")); status != plan.Unchanged {
		t.Errorf("identical descriptor = %q, want unchanged", status)
	}
	if status := classifyBytes(existing, []byte("name=\"Other\"\n")); status != plan.Changed {
		t.Errorf("differing descriptor = %q, want changed", status)
	}
	if status := classifyBytes(filepath.Join(root, "absent.mod"), []byte("x")); status != plan.Added {
		t.Errorf("missing descriptor = %q, want added", status)
	}
}

func TestApplySkipsUnchangedOperations(t *testing.T) {
	root := t.TempDir()
	source := write(t, filepath.Join(root, "source.txt"), "payload")
	skipped := filepath.Join(root, "skipped.txt")
	copied := filepath.Join(root, "copied.txt")

	var observed []string
	operations := &plan.Plan{Observer: func(op plan.Op) { observed = append(observed, op.Path) }}
	operations.Add(plan.Op{Kind: plan.Copy, Source: source, Path: skipped, Status: plan.Unchanged})
	operations.Add(plan.Op{Kind: plan.Copy, Source: source, Path: copied, Status: plan.Changed})

	if err := operations.Apply(); err != nil {
		t.Fatalf("Apply: %v", err)
	}
	if _, err := os.Stat(skipped); !os.IsNotExist(err) {
		t.Error("an unchanged copy was written anyway")
	}
	if _, err := os.Stat(copied); err != nil {
		t.Errorf("a changed copy was not written: %v", err)
	}
	if len(observed) != 1 || observed[0] != copied {
		t.Errorf("observer saw %v, want only the changed copy", observed)
	}
}
