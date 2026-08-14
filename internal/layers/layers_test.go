package layers

import (
	"errors"
	"os"
	"path/filepath"
	"testing"

	"codeberg.org/traidare/ck3_mods/internal/conflicts"
)

func TestExternalModNormalizesEverySelectorForm(t *testing.T) {
	cases := []struct {
		selector string
		registry string
		steamID  string
	}{
		{"3582007365", "mod/ugc_3582007365.mod", "3582007365"},
		{"steam:3582007365", "mod/ugc_3582007365.mod", "3582007365"},
		{"ugc_3582007365", "mod/ugc_3582007365.mod", "3582007365"},
		{"mod/ugc_3582007365.mod", "mod/ugc_3582007365.mod", "3582007365"},
		{"local:mod/ugc_3582007365.mod", "mod/ugc_3582007365.mod", "3582007365"},
		{"my_local_mod", "mod/my_local_mod.mod", "my_local_mod"},
	}
	for _, testCase := range cases {
		mod := externalMod(testCase.selector, 7)
		if mod.GameRegistryID != testCase.registry {
			t.Errorf("%q: registry = %q, want %q", testCase.selector, mod.GameRegistryID, testCase.registry)
		}
		// ResolveExternal drops a non-numeric Steam ID; externalMod only
		// strips the ugc_ prefix.
		if mod.SteamID != testCase.steamID {
			t.Errorf("%q: steamID = %q, want %q", testCase.selector, mod.SteamID, testCase.steamID)
		}
		if mod.Position != 7 {
			t.Errorf("%q: position = %d, want 7", testCase.selector, mod.Position)
		}
	}
}

func TestNextPositionFollowsTheLastProvider(t *testing.T) {
	if got := NextPosition(nil); got != 0 {
		t.Errorf("empty load order = %d, want 0", got)
	}
	providers := []conflicts.Provider{{Position: 3}, {Position: 138}, {Position: 12}}
	if got := NextPosition(providers); got != 139 {
		t.Errorf("NextPosition = %d, want 139", got)
	}
}

// installMod writes a Launcher registry descriptor and its payload, the way a
// subscribed but unenabled mod appears on disk.
func installMod(t *testing.T, paradoxDir, registryName, name string) {
	t.Helper()
	payload := filepath.Join(paradoxDir, "mod", registryName)
	if err := os.MkdirAll(filepath.Join(payload, "events"), 0o755); err != nil {
		t.Fatal(err)
	}
	descriptor := "name=\"" + name + "\"\npath=\"mod/" + registryName + "\"\nreplace_path=\"events\"\n"
	if err := os.WriteFile(filepath.Join(paradoxDir, "mod", registryName+".mod"), []byte(descriptor), 0o644); err != nil {
		t.Fatal(err)
	}
}

func TestResolveExternalAppendsAnInstalledMod(t *testing.T) {
	paradoxDir := t.TempDir()
	installMod(t, paradoxDir, "ugc_3582007365", "Regency Rework")

	for _, selector := range []string{"3582007365", "ugc_3582007365", "mod/ugc_3582007365.mod"} {
		provider, err := ResolveExternal(selector, t.TempDir(), paradoxDir, 139)
		if err != nil {
			t.Fatalf("%q: unexpected error: %v", selector, err)
		}
		if provider.Name != "Regency Rework" || provider.SteamID != "3582007365" {
			t.Errorf("%q: got %q/%q, want Regency Rework/3582007365", selector, provider.Name, provider.SteamID)
		}
		if provider.Position != 139 {
			t.Errorf("%q: position = %d, want 139 (last in load order)", selector, provider.Position)
		}
		if len(provider.ReplacePaths) != 1 || provider.ReplacePaths[0] != "events" {
			t.Errorf("%q: replace paths = %v, want [events]", selector, provider.ReplacePaths)
		}
	}
}

func TestResolveExternalReportsUninstalledSelectors(t *testing.T) {
	_, err := ResolveExternal("9999999999", t.TempDir(), t.TempDir(), 1)
	if !errors.Is(err, ErrNotInstalled) {
		t.Fatalf("got %v, want ErrNotInstalled", err)
	}
}
