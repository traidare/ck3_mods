package gamedata

import (
	"os"
	"path/filepath"
	"testing"
)

const dataDir = "common/culture/cultures"

// writeData creates one data file below a layer root.
func writeData(t *testing.T, root, name, content string) {
	t.Helper()
	directory := filepath.Join(root, filepath.FromSlash(dataDir))
	if err := os.MkdirAll(directory, 0o755); err != nil {
		t.Fatalf("could not create %s: %v", directory, err)
	}
	if err := os.WriteFile(filepath.Join(directory, name), []byte(content), 0o644); err != nil {
		t.Fatalf("could not write %s: %v", name, err)
	}
}

// testSource builds a game root with one mod layer on top of it.
func testSource(t *testing.T, replacePaths []string) (Source, string, string) {
	t.Helper()
	root := t.TempDir()
	modRoot := t.TempDir()
	position := 0
	return Source{
		Root: root,
		Layers: []Layer{{
			Kind:         "local",
			Name:         "Test Mod",
			Identifier:   "test",
			Position:     &position,
			Root:         modRoot,
			ReplacePaths: replacePaths,
		}},
	}, root, modRoot
}

func TestParseDirectoryLetsTheLastLayerWinTheSamePath(t *testing.T) {
	source, root, modRoot := testSource(t, nil)
	writeData(t, root, "00_base.txt", "english = {\n\tethos = ethos_vanilla\n}\n")
	writeData(t, modRoot, "00_base.txt", "english = {\n\tethos = ethos_modded\n}\n")

	definitions, err := source.ParseDirectory(dataDir)
	if err != nil {
		t.Fatalf("ParseDirectory: %v", err)
	}
	english, found := definitions["english"]
	if !found {
		t.Fatal("english is missing")
	}
	if english.Layer.Identifier != "test" {
		t.Errorf("winner = %q, want the mod layer", english.Layer.Identifier)
	}
	fields, err := english.Fields()
	if err != nil {
		t.Fatalf("Fields: %v", err)
	}
	if got := fields.Scalar("ethos"); got != "ethos_modded" {
		t.Errorf("ethos = %q, want ethos_modded", got)
	}
}

func TestParseDirectoryKeepsVanillaFilesTheModDoesNotShadow(t *testing.T) {
	source, root, modRoot := testSource(t, nil)
	writeData(t, root, "00_base.txt", "english = {\n\tethos = ethos_vanilla\n}\n")
	writeData(t, modRoot, "01_extra.txt", "andal = {\n\tethos = ethos_bellicose\n}\n")

	definitions, err := source.ParseDirectory(dataDir)
	if err != nil {
		t.Fatalf("ParseDirectory: %v", err)
	}
	if len(definitions) != 2 {
		t.Fatalf("got %d definitions, want 2", len(definitions))
	}
	if definitions["english"].Layer.Kind != "game" {
		t.Errorf("english came from %q, want the game layer", definitions["english"].Layer.Kind)
	}
}

func TestParseDirectoryDropsVanillaBehindReplacePath(t *testing.T) {
	source, root, modRoot := testSource(t, []string{dataDir})
	writeData(t, root, "00_base.txt", "english = {\n\tethos = ethos_vanilla\n}\n")
	writeData(t, modRoot, "01_extra.txt", "andal = {\n\tethos = ethos_bellicose\n}\n")

	definitions, err := source.ParseDirectory(dataDir)
	if err != nil {
		t.Fatalf("ParseDirectory: %v", err)
	}
	if _, found := definitions["english"]; found {
		t.Error("english survived a replace_path that removes the vanilla directory")
	}
	if _, found := definitions["andal"]; !found {
		t.Error("andal is missing")
	}
}

func TestChildrenReportsLinesRelativeToTheFile(t *testing.T) {
	source, root, _ := testSource(t, nil)
	writeData(t, root, "00_base.txt", "# a comment\n\nchristianity_religion = {\n"+
		"\tfamily = rf_abrahamic\n"+
		"\tfaiths = {\n"+
		"\t\tcatholic = {\n"+
		"\t\t\treligious_head = k_papal_state\n"+
		"\t\t}\n"+
		"\t\torthodox = {\n"+
		"\t\t\treligious_head = k_orthodox\n"+
		"\t\t}\n"+
		"\t}\n"+
		"}\n")

	definitions, err := source.ParseDirectory(dataDir)
	if err != nil {
		t.Fatalf("ParseDirectory: %v", err)
	}
	religion := definitions["christianity_religion"]
	if religion.Line != 3 {
		t.Fatalf("religion line = %d, want 3", religion.Line)
	}

	children, err := religion.Children("faiths")
	if err != nil {
		t.Fatalf("Children: %v", err)
	}
	if len(children) != 2 {
		t.Fatalf("got %d faiths, want 2", len(children))
	}
	want := map[string]int{"catholic": 6, "orthodox": 9}
	for _, child := range children {
		if child.Line != want[child.Identifier] {
			t.Errorf("%s line = %d, want %d", child.Identifier, child.Line, want[child.Identifier])
		}
		if child.RelativePath != religion.RelativePath {
			t.Errorf("%s path = %q, want the religion's", child.Identifier, child.RelativePath)
		}
		fields, err := child.Fields()
		if err != nil {
			t.Fatalf("Fields for %s: %v", child.Identifier, err)
		}
		if fields.Scalar("religious_head") == "" {
			t.Errorf("%s lost its religious_head", child.Identifier)
		}
	}
}

func TestFieldsReadsRepeatedKeysAndLists(t *testing.T) {
	definition := Definition{
		Identifier: "catholic",
		Line:       1,
		Text: "catholic = {\n" +
			"\tholy_site = jerusalem\n" +
			"\tholy_site = rome\n" +
			"\tdoctrine = tenet_communion\n" +
			"\ttraditions = { tradition_a tradition_b }\n" +
			"\tcharacter_modifier = { monthly_piety_gain_mult = 0.2 }\n" +
			"}",
	}
	fields, err := definition.Fields()
	if err != nil {
		t.Fatalf("Fields: %v", err)
	}

	sites := fields.Scalars("holy_site")
	if len(sites) != 2 || sites[0] != "jerusalem" || sites[1] != "rome" {
		t.Errorf("holy_site = %v, want [jerusalem rome]", sites)
	}
	traditions := fields.List("traditions")
	if len(traditions) != 2 || traditions[0] != "tradition_a" {
		t.Errorf("traditions = %v, want two entries", traditions)
	}
	blocks := fields.Blocks("character_modifier")
	if len(blocks) != 1 {
		t.Fatalf("got %d character_modifier blocks, want 1", len(blocks))
	}
	pairs := blocks[0].Pairs()
	if len(pairs) != 1 || pairs[0].Key != "monthly_piety_gain_mult" || pairs[0].Value != "0.2" {
		t.Errorf("modifier pairs = %v, want one piety entry", pairs)
	}
}
