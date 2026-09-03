package playset

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestDumpUsesLauncherVisiblePositions(t *testing.T) {
	content, err := Dump(Playset{
		Name: "Test",
		Mods: []Mod{{DisplayName: "First", Enabled: true, Position: 0}},
	})
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(content, `"position": 1`) {
		t.Errorf("export does not contain a one-based position:\n%s", content)
	}
	if strings.Contains(content, "positionBase") {
		t.Errorf("export contains redundant position-base metadata:\n%s", content)
	}
}

func TestSummaryUsesLauncherVisiblePositions(t *testing.T) {
	summary := Summary(Playset{
		Mods: []Mod{{DisplayName: "First", Enabled: true, Position: 0, Source: "local"}},
	})
	mods := summary["enabledLocalMods"].([]any)
	position := mods[0].(map[string]any)["position"]
	if position != 1 {
		t.Fatalf("summary position = %v, want 1", position)
	}
}

func TestLoadFileAcceptsOneBasedPositions(t *testing.T) {
	content := `{
  "name": "Test",
  "mods": [
    {"displayName": "First", "position": 1},
    {"displayName": "Second", "position": 2}
  ]
}`
	filePath := filepath.Join(t.TempDir(), "playset.json")
	if err := os.WriteFile(filePath, []byte(content), 0o600); err != nil {
		t.Fatal(err)
	}
	loaded, err := LoadFile(filePath)
	if err != nil {
		t.Fatal(err)
	}
	if len(loaded.Mods) != 2 {
		t.Fatalf("loaded %d mods, want 2", len(loaded.Mods))
	}
	for index, mod := range loaded.Mods {
		if mod.Position != index {
			t.Errorf("mod %d position = %d, want %d", index, mod.Position, index)
		}
	}
}

func TestLoadFileRejectsZeroBasedPositions(t *testing.T) {
	filePath := filepath.Join(t.TempDir(), "playset.json")
	content := `{"name":"Test","mods":[{"displayName":"First","position":0}]}`
	if err := os.WriteFile(filePath, []byte(content), 0o600); err != nil {
		t.Fatal(err)
	}
	if _, err := LoadFile(filePath); err == nil || !strings.Contains(err.Error(), "position must be at least 1") {
		t.Fatalf("LoadFile error = %v, want invalid position", err)
	}
}

func TestImportPlanUsesLauncherVisibleSourcePosition(t *testing.T) {
	result := (ResolvedMod{SourcePosition: 0}).ToMap()
	if result["source_position"] != 1 {
		t.Fatalf("source_position = %v, want 1", result["source_position"])
	}
}
