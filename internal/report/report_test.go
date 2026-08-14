package report

import (
	"strings"
	"testing"
)

func TestRenderTextLabelsProvidersByNameAndSelector(t *testing.T) {
	source := Report{
		Mods: []ModRecord{
			{StableID: "local:mod/ugc_3766038754.mod", SteamID: "3766038754", Name: "Seasons of Valyria", Position: 134},
			{StableID: "local:mod/lore_governments.mod", Name: "Lore Governments", Position: 8},
		},
		Files: []FileEntry{{
			Path:          "events/lov_season_events.txt",
			ConflictKinds: []string{"same_path"},
			Providers: []FileProvider{
				{ModID: "local:mod/lore_governments.mod", Position: 8},
				{ModID: "local:mod/ugc_3766038754.mod", Position: 134},
			},
			EffectiveState: "present",
		}},
	}

	rendered := RenderText(source)
	for _, want := range []string{
		// The Workshop ID identifies a subscribed mod; a local-only mod falls
		// back to its registry name. Positions are right-aligned.
		"    [  8] Lore Governments (lore_governments)",
		"    [134] Seasons of Valyria (3766038754)",
	} {
		if !strings.Contains(rendered, want) {
			t.Errorf("missing line %q in:\n%s", want, rendered)
		}
	}
}

func TestRenderTextFallsBackToModID(t *testing.T) {
	source := Report{
		Files: []FileEntry{{
			Path:           "events/orphan.txt",
			Providers:      []FileProvider{{ModID: "local:mod/unlisted.mod", Position: 3}},
			EffectiveState: "present",
		}},
	}
	if !strings.Contains(RenderText(source), "[3] local:mod/unlisted.mod") {
		t.Errorf("expected the raw ID for a provider with no mod record:\n%s", RenderText(source))
	}
}
