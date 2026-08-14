package conflicts

import (
	"strings"
	"testing"

	"codeberg.org/traidare/ck3_mods/internal/report"
)

// subscribedPlayset mirrors the live shape: a Workshop mod the Launcher
// registered locally, so its stable ID is local but it still has a Steam ID.
func subscribedPlayset() report.Report {
	mods := []report.ModRecord{
		{StableID: "local:mod/ugc_3766038754.mod", SteamID: "3766038754", Name: "Seasons of Valyria", Position: 0},
		{StableID: "local:mod/other.mod", Name: "Other", Position: 1},
	}
	files := []report.FileEntry{{
		Path: "common/traits/00_traits.txt",
		Providers: []report.FileProvider{
			{ModID: "local:mod/ugc_3766038754.mod"},
			{ModID: "local:mod/other.mod"},
		},
		EffectiveWinner: report.EffectiveWinner{ModID: "local:mod/other.mod"},
	}, {
		Path:            "common/traits/01_other.txt",
		Providers:       []report.FileProvider{{ModID: "local:mod/other.mod"}},
		EffectiveWinner: report.EffectiveWinner{ModID: "local:mod/other.mod"},
	}}
	return report.Report{Mods: mods, Files: files}
}

func TestApplyInvolvingAcceptsEveryAlias(t *testing.T) {
	source := subscribedPlayset()
	aliases := []string{
		"local:mod/ugc_3766038754.mod",
		"mod/ugc_3766038754.mod",
		"ugc_3766038754.mod",
		"ugc_3766038754",
		"Seasons of Valyria",
		"3766038754",
		"steam:3766038754",
	}
	for _, alias := range aliases {
		filtered, err := Apply(source, Filter{Involving: alias})
		if err != nil {
			t.Fatalf("alias %q: unexpected error: %v", alias, err)
		}
		if len(filtered.Files) != 1 || filtered.Files[0].Path != "common/traits/00_traits.txt" {
			t.Fatalf("alias %q: got %d files, want the one shared file", alias, len(filtered.Files))
		}
	}
}

func TestApplyInvolvingRejectsUnknownSelector(t *testing.T) {
	_, err := Apply(subscribedPlayset(), Filter{Involving: "9999999999"})
	if err == nil {
		t.Fatal("expected an unknown selector to be an error, not an empty report")
	}
	if !strings.Contains(err.Error(), "unknown mod selector") {
		t.Fatalf("unexpected error: %v", err)
	}
}

func TestApplyInvolvingSuggestsNearMatches(t *testing.T) {
	_, err := Apply(subscribedPlayset(), Filter{Involving: "Seasons"})
	if err == nil {
		t.Fatal("expected a partial name to be rejected")
	}
	if !strings.Contains(err.Error(), `did you mean "Seasons of Valyria"?`) {
		t.Fatalf("expected a suggestion, got: %v", err)
	}
}
