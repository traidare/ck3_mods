package religions

import (
	"testing"

	"codeberg.org/traidare/ck3_mods/internal/gamedata"
)

// testDatabase builds a database with the doctrine groups the merge tests need,
// skipping the playset resolution Load performs.
func testDatabase() *Database {
	database := &Database{
		Religions:     map[string]Religion{},
		Faiths:        map[string]Faith{},
		HolySites:     map[string]HolySite{},
		Groups:        map[string]Group{},
		doctrineGroup: map[string]string{},
		doctrines:     map[string]bool{},
	}
	groups := map[string][]string{
		"doctrine_marriage_type": {"doctrine_monogamy", "doctrine_polygamy"},
		"doctrine_core_tenets":   {"tenet_communion", "tenet_monasticism", "tenet_asceticism"},
		"hostility_group":        {"abrahamic_hostility_doctrine"},
	}
	picks := map[string]int{"doctrine_core_tenets": 3}
	for group, members := range groups {
		count := picks[group]
		if count == 0 {
			count = 1
		}
		database.Groups[group] = Group{ID: group, Picks: count}
		for _, doctrine := range members {
			database.doctrineGroup[doctrine] = group
			database.doctrines[doctrine] = true
		}
	}
	database.doctrines["special_doctrine_ungrouped"] = true
	return database
}

const religionText = `christianity_religion = {
	family = rf_abrahamic
	doctrine = abrahamic_hostility_doctrine
	doctrine = doctrine_monogamy
	doctrine = special_doctrine_ungrouped
	doctrine_selection_pair = {
		requires_dlc_flag = royal_court
		doctrine = tenet_asceticism
		fallback_doctrine = tenet_monasticism
	}
	faiths = {
		catholic = {
			religious_head = k_papal_state
			holy_site = rome
			doctrine = tenet_communion
			doctrine = tenet_monasticism
		}
		cathar = {
			doctrine = doctrine_polygamy
		}
	}
}`

func parseFixture(t *testing.T) *Database {
	t.Helper()
	database := testDatabase()
	definition := gamedata.Definition{
		Identifier:   "christianity_religion",
		Text:         religionText,
		RelativePath: ReligionsPath + "/00_test.txt",
		Line:         1,
	}
	err := database.parseReligions(map[string]gamedata.Definition{"christianity_religion": definition})
	if err != nil {
		t.Fatalf("parseReligions: %v", err)
	}
	return database
}

// doctrineMap indexes a faith's effective doctrines by identifier.
func doctrineMap(faith Faith) map[string]Doctrine {
	result := map[string]Doctrine{}
	for _, doctrine := range faith.Doctrines {
		result[doctrine.ID] = doctrine
	}
	return result
}

func TestFaithInheritsReligionDoctrinesItDoesNotOverride(t *testing.T) {
	database := parseFixture(t)
	faith, err := database.Faith("catholic")
	if err != nil {
		t.Fatalf("Faith: %v", err)
	}
	doctrines := doctrineMap(faith)

	inherited, found := doctrines["abrahamic_hostility_doctrine"]
	if !found {
		t.Fatal("catholic did not inherit the religion's hostility doctrine")
	}
	if inherited.Origin != FromReligion {
		t.Errorf("origin = %q, want %q", inherited.Origin, FromReligion)
	}
	if _, found := doctrines["doctrine_monogamy"]; !found {
		t.Error("catholic did not inherit doctrine_monogamy")
	}
	if ungrouped, found := doctrines["special_doctrine_ungrouped"]; !found {
		t.Error("an ungrouped religion doctrine was dropped")
	} else if ungrouped.Group != "" {
		t.Errorf("group = %q, want empty", ungrouped.Group)
	}
}

func TestFaithOverridesReligionDoctrineInTheSameGroup(t *testing.T) {
	database := parseFixture(t)
	faith, err := database.Faith("cathar")
	if err != nil {
		t.Fatalf("Faith: %v", err)
	}
	doctrines := doctrineMap(faith)

	if _, found := doctrines["doctrine_monogamy"]; found {
		t.Error("the religion's doctrine_monogamy survived the faith's doctrine_polygamy")
	}
	polygamy, found := doctrines["doctrine_polygamy"]
	if !found {
		t.Fatal("cathar lost its own doctrine_polygamy")
	}
	if polygamy.Origin != FromFaith {
		t.Errorf("origin = %q, want %q", polygamy.Origin, FromFaith)
	}
	// Overriding one group must not disturb another.
	if _, found := doctrines["abrahamic_hostility_doctrine"]; !found {
		t.Error("overriding marriage also dropped the hostility doctrine")
	}
}

func TestFaithTenetsReplaceTheReligionsSelectionPair(t *testing.T) {
	database := parseFixture(t)

	catholic, err := database.Faith("catholic")
	if err != nil {
		t.Fatalf("Faith: %v", err)
	}
	doctrines := doctrineMap(catholic)
	// catholic declares tenets of its own, so the religion's DLC pair, which
	// belongs to the same multi-pick group, does not reach it.
	if _, found := doctrines["tenet_asceticism"]; found {
		t.Error("the religion's gated tenet reached a faith that picks its own")
	}
	if len(doctrines) != 5 {
		t.Errorf("catholic has %d doctrines, want 5", len(doctrines))
	}

	// cathar picks no tenets, so both branches of the pair come through, marked
	// with the feature that selects between them.
	cathar, err := database.Faith("cathar")
	if err != nil {
		t.Fatalf("Faith: %v", err)
	}
	gated := doctrineMap(cathar)
	asceticism, found := gated["tenet_asceticism"]
	if !found {
		t.Fatal("cathar did not inherit the gated tenet")
	}
	if asceticism.RequiresDLC != "royal_court" || asceticism.Fallback {
		t.Errorf("asceticism = %+v, want the royal_court branch", asceticism)
	}
	monasticism, found := gated["tenet_monasticism"]
	if !found {
		t.Fatal("cathar did not inherit the fallback tenet")
	}
	if !monasticism.Fallback {
		t.Errorf("monasticism = %+v, want the fallback branch", monasticism)
	}
}

func TestFaithCarriesReligionFamilyAndUndefinedHolySiteWarns(t *testing.T) {
	database := parseFixture(t)
	faith, err := database.Faith("catholic")
	if err != nil {
		t.Fatalf("Faith: %v", err)
	}
	if faith.Family != "rf_abrahamic" {
		t.Errorf("family = %q, want the religion's rf_abrahamic", faith.Family)
	}
	if faith.Religion != "christianity_religion" {
		t.Errorf("religion = %q, want christianity_religion", faith.Religion)
	}

	// No holy site was defined, so the reference must be reported.
	found := false
	for _, warning := range database.Warnings {
		if warning.Code == "undefined_holy_site" {
			found = true
		}
	}
	if !found {
		t.Error("an undefined holy site produced no warning")
	}

	sites, err := database.SelectHolySites("catholic")
	if err != nil {
		t.Fatalf("SelectHolySites: %v", err)
	}
	if len(sites) != 1 || sites[0].Identifier != "rome" {
		t.Errorf("holy sites = %v, want the undefined rome placeholder", sites)
	}
}

func TestSelectFaithsRejectsUnknownFilters(t *testing.T) {
	database := parseFixture(t)
	if _, err := database.SelectFaiths("no_such_religion", nil, true); err == nil {
		t.Error("an unknown religion was accepted")
	}
	if _, err := database.SelectFaiths("", []string{"no_such_doctrine"}, true); err == nil {
		t.Error("an unknown doctrine was accepted")
	}

	selected, err := database.SelectFaiths("christianity_religion", []string{"tenet_communion"}, true)
	if err != nil {
		t.Fatalf("SelectFaiths: %v", err)
	}
	if len(selected) != 1 || selected[0].Identifier != "catholic" {
		t.Errorf("selected = %v, want only catholic", selected)
	}
}
