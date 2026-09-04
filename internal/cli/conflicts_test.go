package cli

import (
	"flag"
	"io"
	"os"
	"path/filepath"
	"testing"

	"codeberg.org/traidare/ck3_mods/internal/layers"
)

func TestConflictsRejectsRemovedModsOnlyFlag(t *testing.T) {
	code, err := runConflicts(&Env{Args: []string{"--mods-only"}, Stderr: io.Discard})
	if code != 2 || err == nil {
		t.Fatalf("code = %d, error = %v", code, err)
	}
}

func TestConflictsRejectsFilesWithSummaryOnly(t *testing.T) {
	code, err := runConflicts(&Env{Args: []string{"--files", "--summary-only"}, Stderr: io.Discard})
	if code != 2 || err == nil {
		t.Fatalf("code = %d, error = %v", code, err)
	}
}

func TestConflictsRejectsAllFilesWithSummaryOnly(t *testing.T) {
	code, err := runConflicts(&Env{Args: []string{"--all-files", "--summary-only"}, Stderr: io.Discard})
	if code != 2 || err == nil {
		t.Fatalf("code = %d, error = %v", code, err)
	}
}

func TestInvolvingFlagIsRepeatable(t *testing.T) {
	set := flag.NewFlagSet("conflicts", flag.ContinueOnError)
	var involving stringList
	set.Var(&involving, "involving", "")
	positionals, err := parse(set, []string{"AGOT", "--involving", "first", "--involving", "second"})
	if err != nil {
		t.Fatal(err)
	}
	if len(positionals) != 1 || positionals[0] != "AGOT" || len(involving) != 2 ||
		involving[0] != "first" || involving[1] != "second" {
		t.Fatalf("positionals = %v, involving = %v", positionals, involving)
	}
}

func installCandidate(t *testing.T, paradoxDir, registry, name string) {
	t.Helper()
	payload := filepath.Join(paradoxDir, "mod", registry)
	if err := os.MkdirAll(payload, 0o755); err != nil {
		t.Fatal(err)
	}
	descriptor := "name=\"" + name + "\"\npath=\"mod/" + registry + "\"\n"
	if err := os.WriteFile(filepath.Join(paradoxDir, "mod", registry+".mod"), []byte(descriptor), 0o644); err != nil {
		t.Fatal(err)
	}
}

func TestWithExternalModsAppendsInSelectorOrderAndDeduplicatesAliases(t *testing.T) {
	paradoxDir := t.TempDir()
	installCandidate(t, paradoxDir, "first", "First")
	installCandidate(t, paradoxDir, "second", "Second")

	providers, _, err := withExternalMods(layers.Discovery{},
		[]string{"first", "mod/first.mod", "second"}, t.TempDir(), paradoxDir)
	if err != nil {
		t.Fatal(err)
	}
	if len(providers) != 2 {
		t.Fatalf("got %d providers, want 2", len(providers))
	}
	if providers[0].Name != "First" || providers[0].Position != 0 ||
		providers[1].Name != "Second" || providers[1].Position != 1 {
		t.Fatalf("unexpected provider order: %#v", providers)
	}
}
