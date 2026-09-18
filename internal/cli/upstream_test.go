package cli

import (
	"errors"
	"reflect"
	"strings"
	"testing"

	"codeberg.org/traidare/ck3_mods/internal/generate"
	"codeberg.org/traidare/ck3_mods/internal/sourcelock"
	"codeberg.org/traidare/ck3_mods/internal/workspace"
)

func TestRootRegistersUpstream(t *testing.T) {
	if Root().child("upstream") == nil {
		t.Fatal("root does not register upstream")
	}
}

func TestItemOfGroupsByWorkshopItemAndNamespace(t *testing.T) {
	for key, want := range map[string]string{
		"workshop/2962333032/common/traits.txt": "2962333032",
		"game/common/traits/00_traits.txt":      "game",
		"repo/mods/x/descriptor.mod":            "repo",
	} {
		if got := itemOf(key); got != want {
			t.Errorf("itemOf(%q) = %q, want %q", key, got, want)
		}
	}
}

func TestKeysForItemSelectsOnlyThatItem(t *testing.T) {
	keys := []string{
		"workshop/111/a.txt",
		"workshop/222/b.txt",
		"workshop/111/c.txt",
		"game/d.txt",
	}
	got := keysForItem(keys, "111")
	want := []string{"workshop/111/a.txt", "workshop/111/c.txt"}
	if !reflect.DeepEqual(got, want) {
		t.Errorf("keysForItem = %v, want %v", got, want)
	}
	if got := keysForItem(keys, "333"); got != nil {
		t.Errorf("keysForItem for an unconsumed item = %v, want nil", got)
	}
}

// Drift under one item must not make a module look affected by another, which
// is the whole point of asking about specific updated Workshop IDs.
func TestChangedForIsScopedToOneItem(t *testing.T) {
	entry := &consumer{
		mod:    &workspace.Mod{Slug: "example"},
		pinned: map[string]int{"111": 2, "222": 1},
		changes: sourcelock.Changes{
			Changed: []string{"workshop/111/a.txt"},
			Removed: []string{"workshop/111/b.txt"},
		},
	}
	if got := entry.changedFor("111"); got != 2 {
		t.Errorf("changedFor(111) = %d, want 2", got)
	}
	if got := entry.changedFor("222"); got != 0 {
		t.Errorf("changedFor(222) = %d, want 0", got)
	}
}

// An item nothing consumes still has to appear, because "we read none of that"
// is the answer to half of these questions.
func TestItemsInScopeKeepsRequestedItemsWithoutConsumers(t *testing.T) {
	consumers := []*consumer{{pinned: map[string]int{"111": 1}}}
	got := itemsInScope(consumers, map[string]bool{"111": true, "999": true})
	want := []string{"111", "999"}
	if !reflect.DeepEqual(got, want) {
		t.Errorf("itemsInScope = %v, want %v", got, want)
	}
}

// A generator whose assertions caught an upstream change is exactly when this
// report is wanted, so a module that fails must not take the others with it.
func TestUpstreamReportsAFailedGeneratorWithoutLosingTheRest(t *testing.T) {
	consumers := []*consumer{
		{
			mod:     &workspace.Mod{Slug: "broken"},
			pinned:  map[string]int{"111": 1},
			changes: sourcelock.Changes{Changed: []string{"workshop/111/a.txt"}},
		},
		{
			mod:     &workspace.Mod{Slug: "healthy"},
			pinned:  map[string]int{"111": 1},
			changes: sourcelock.Changes{Changed: []string{"workshop/111/b.txt"}},
		},
	}
	outcomes := map[string]generate.Result{"healthy": {ChangedFiles: []string{"common/a.txt"}}}
	failures := map[string]error{"broken": errors.New("expected 1 occurrence, found 0")}

	var out strings.Builder
	printUpstream(&Env{Stdout: &out}, []string{"111"}, consumers, outcomes, failures)
	text := out.String()
	for _, want := range []string{
		"broken: generator failed: expected 1 occurrence, found 0",
		"healthy: would update 1 file(s)",
		"common/a.txt",
	} {
		if !strings.Contains(text, want) {
			t.Errorf("report is missing %q:\n%s", want, text)
		}
	}

	report := upstreamReport([]string{"111"}, consumers, outcomes, failures)
	modules, _ := report[0].(map[string]any)["consumers"].([]any)
	if len(modules) != 2 {
		t.Fatalf("modules = %v, want both consumers reported", modules)
	}
	broken, _ := modules[0].(map[string]any)
	if broken["error"] != "expected 1 occurrence, found 0" {
		t.Errorf("broken module = %v, want the failure recorded against it", broken)
	}
	if _, reported := modules[1].(map[string]any)["error"]; reported {
		t.Errorf("healthy module = %v, want no error", modules[1])
	}
}

func TestItemsInScopeWithoutArgumentsCoversEveryPinnedItem(t *testing.T) {
	consumers := []*consumer{
		{pinned: map[string]int{"222": 1}},
		{pinned: map[string]int{"111": 1, "game": 3}},
	}
	got := itemsInScope(consumers, nil)
	want := []string{"111", "222", "game"}
	if !reflect.DeepEqual(got, want) {
		t.Errorf("itemsInScope = %v, want %v", got, want)
	}
}
