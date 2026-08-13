package workspace

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func writeManifest(t *testing.T, content string) string {
	t.Helper()
	path := filepath.Join(t.TempDir(), ManifestName)
	if err := os.WriteFile(path, []byte(content), 0o644); err != nil {
		t.Fatal(err)
	}
	return path
}

const ManifestName = "mod.toml"

func TestLoadManifestRejectsUnknownGeneratorFields(t *testing.T) {
	path := writeManifest(t, `
[generator]
entrypoint = "implementation.py:generate"
owned_outputs = ["common"]
assets = ["assets/source_manifest.json"]
`)

	_, err := LoadManifest(path, "example")
	if err == nil || !strings.Contains(err.Error(), "generator.assets") {
		t.Fatalf("expected generator.assets error, got %v", err)
	}
}

func TestLoadManifestAcceptsCurrentGeneratorSchema(t *testing.T) {
	path := writeManifest(t, `
[generator]
entrypoint = "implementation.py:generate"
owned_outputs = ["common"]
owned_artifacts = ["audit/*.csv"]

[[sources]]
name = "agot"
kind = "workshop"
item_id = "2962333032"
`)

	manifest, err := LoadManifest(path, "example")
	if err != nil {
		t.Fatal(err)
	}
	if manifest.Generator.Entrypoint != "implementation.py:generate" {
		t.Fatalf("unexpected entrypoint: %s", manifest.Generator.Entrypoint)
	}
}
