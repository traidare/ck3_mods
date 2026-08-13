package generate

import (
	"testing"

	"codeberg.org/traidare/ck3_mods/internal/workspace"
)

func TestStagedOwnershipSeparatesPayloadAndArtifacts(t *testing.T) {
	spec := &workspace.GeneratorSpec{
		OwnedOutputs:   []string{"common", "map_data/definition.csv"},
		OwnedArtifacts: []string{"audit/*.csv"},
	}
	tests := map[string]bool{
		"common/events/example.txt":      true,
		"map_data/definition.csv":        true,
		"artifacts/audit/example.csv":    true,
		"artifacts/audit/example.txt":    false,
		"artifacts/common/example.txt":   false,
		"map_data/default.map":           false,
		"artifacts":                      false,
		"commonality/events/example.txt": false,
	}
	for path, expected := range tests {
		if actual := stagedIsOwned(path, spec); actual != expected {
			t.Errorf("stagedIsOwned(%q) = %v, want %v", path, actual, expected)
		}
	}
}

func TestSplitReportKeepsSubprocessOutput(t *testing.T) {
	passthrough, report := splitReport("progress\n{\"status\":\"ok\"}\n")
	if passthrough != "progress\n" || report != `{"status":"ok"}` {
		t.Fatalf("unexpected split: passthrough=%q report=%q", passthrough, report)
	}
}
