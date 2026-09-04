package validate

import (
	"os"
	"path/filepath"
	"strings"
	"testing"

	"codeberg.org/traidare/ck3_mods/internal/workspace"
)

// sourcesFixture writes one tooling root holding a manifest and a load order,
// and returns the mod that pairs them.
func sourcesFixture(t *testing.T, manifest, loadOrder string) *workspace.Mod {
	t.Helper()
	root := t.TempDir()
	manifestPath := filepath.Join(root, "mod.toml")
	if err := os.WriteFile(manifestPath, []byte(manifest), 0o644); err != nil {
		t.Fatal(err)
	}
	if loadOrder != "" {
		configPath := filepath.Join(root, TigerConfigName)
		if err := os.WriteFile(configPath, []byte(loadOrder), 0o644); err != nil {
			t.Fatal(err)
		}
	}
	parsed, err := workspace.LoadManifest(manifestPath, "example")
	if err != nil {
		t.Fatal(err)
	}
	return &workspace.Mod{
		Slug:         "example",
		ToolingRoot:  root,
		ManifestPath: manifestPath,
		Manifest:     parsed,
	}
}

const sourcesManifest = `
[generator]
entrypoint = "implementation.py:generate"
owned_outputs = ["common"]

[[sources]]
name = "agot"
kind = "workshop"
item_id = "2962333032"
`

const sourcesLoadOrder = `load_mod = {
	label = "AGOT"
	workshop_id = "2962333032"
}
`

func TestValidateSourcesAcceptsLoadedWorkshopSource(t *testing.T) {
	check := validateSources(sourcesFixture(t, sourcesManifest, sourcesLoadOrder))
	if check.Status != StatusPassed {
		t.Fatalf("expected passed, got %s: %s", check.Status, check.Message)
	}
}

func TestValidateSourcesRejectsUnloadedWorkshopSource(t *testing.T) {
	check := validateSources(sourcesFixture(t, sourcesManifest, "load_mod = {\n}\n"))
	if check.Status != StatusFailed {
		t.Fatalf("expected failed, got %s: %s", check.Status, check.Message)
	}
	if len(check.Details) != 1 || !strings.Contains(check.Details[0], "2962333032") {
		t.Fatalf("expected the unloaded ID in the details, got %v", check.Details)
	}
}

func TestValidateSourcesAcceptsExplainedOmission(t *testing.T) {
	explained := strings.Replace(
		sourcesManifest,
		"[[sources]]",
		"# Consumed for its model remaps only; loading it would shadow our own.\n[[sources]]",
		1,
	)
	check := validateSources(sourcesFixture(t, explained, "load_mod = {\n}\n"))
	if check.Status != StatusPassed {
		t.Fatalf("expected passed, got %s: %s", check.Status, check.Message)
	}
	if !strings.Contains(check.Message, "1 explained") {
		t.Fatalf("expected the explained count in the message, got %q", check.Message)
	}
}

func TestValidateSourcesSkipsWithoutLoadOrder(t *testing.T) {
	check := validateSources(sourcesFixture(t, sourcesManifest, ""))
	if check.Status != StatusSkipped {
		t.Fatalf("expected skipped, got %s: %s", check.Status, check.Message)
	}
}
