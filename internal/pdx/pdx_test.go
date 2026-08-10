package pdx

import (
	"reflect"
	"strings"
	"testing"
)

func TestTokenizeSkipsCommentsAndTracksLines(t *testing.T) {
	tokens, err := Tokenize("# leading\nname=\"A\"\n# trailing\nversion=1.0\n")
	if err != nil {
		t.Fatalf("Tokenize: %v", err)
	}
	want := []Token{
		{TokenValue, "name", 2, 10, 14},
		{TokenEquals, "=", 2, 14, 15},
		{TokenValue, "A", 2, 15, 18},
		{TokenValue, "version", 4, 30, 37},
		{TokenEquals, "=", 4, 37, 38},
		{TokenValue, "1.0", 4, 38, 41},
	}
	if !reflect.DeepEqual(tokens, want) {
		t.Errorf("tokens = %#v, want %#v", tokens, want)
	}
}

func TestTokenizeStringEscapes(t *testing.T) {
	tokens, err := Tokenize(`name="a\"b\tc\\d"`)
	if err != nil {
		t.Fatalf("Tokenize: %v", err)
	}
	if got := tokens[2].Value; got != "a\"b\tc\\d" {
		t.Errorf("value = %q", got)
	}
}

func TestTokenizeUnterminatedString(t *testing.T) {
	if _, err := Tokenize("name=\"unclosed\n"); err == nil {
		t.Fatal("expected an error")
	}
}

func TestTokenizeHashInsideQuotesIsNotAComment(t *testing.T) {
	tokens, err := Tokenize(`name="a # b"`)
	if err != nil {
		t.Fatalf("Tokenize: %v", err)
	}
	if got := tokens[2].Value; got != "a # b" {
		t.Errorf("value = %q, want %q", got, "a # b")
	}
}

func TestParseBlocksAndRepeatedFields(t *testing.T) {
	descriptor, err := Parse(`
name="Test Mod"
version="1.0"
tags={
	"Culture"
	"Total Conversion"
}
replace_path="common/traits"
replace_path="common/cultures"
`)
	if err != nil {
		t.Fatalf("Parse: %v", err)
	}
	if name, err := descriptor.Name(); err != nil || name != "Test Mod" {
		t.Errorf("Name() = %q, %v", name, err)
	}
	if tags := descriptor.Values("tags"); !reflect.DeepEqual(tags, []string{"Culture", "Total Conversion"}) {
		t.Errorf("tags = %#v", tags)
	}
	want := []string{"common/traits", "common/cultures"}
	if got := descriptor.ReplacePaths(); !reflect.DeepEqual(got, want) {
		t.Errorf("replace_path = %#v, want %#v", got, want)
	}
	if _, err := descriptor.Value("replace_path", ""); err == nil {
		t.Error("expected Value to reject a repeated field")
	}
}

func TestParseRejectsMalformedInput(t *testing.T) {
	for name, text := range map[string]string{
		"missing equals":     "name \"A\"",
		"missing value":      "name=",
		"unterminated block": "tags={ \"a\"",
		"nested assignment":  "tags={ inner=1 }",
		"leading brace":      "{ name=\"A\" }",
	} {
		t.Run(name, func(t *testing.T) {
			if _, err := Parse(text); err == nil {
				t.Fatal("expected an error")
			}
		})
	}
}

func TestValidateNativeRejectsLauncherPath(t *testing.T) {
	descriptor, err := Parse("name=\"A\"\npath=\"mod/a\"\n")
	if err != nil {
		t.Fatal(err)
	}
	if err := ValidateNative(descriptor); err == nil {
		t.Fatal("expected the Launcher-only path field to be rejected")
	}
}

func TestLauncherDescriptorTextPreservesFormatting(t *testing.T) {
	native := "name=\"A\"\ntags={\n\t\"Culture\"\n}\n"
	derived, err := LauncherDescriptorText(native, "a_mod", "")
	if err != nil {
		t.Fatalf("LauncherDescriptorText: %v", err)
	}
	if !strings.HasPrefix(derived, native) {
		t.Errorf("derived descriptor did not preserve the native text: %q", derived)
	}
	if !strings.HasSuffix(derived, "path=\"mod/a_mod\"\n") {
		t.Errorf("derived descriptor has no trailing path field: %q", derived)
	}
}

func TestLauncherDescriptorTextRejectsEscapingPaths(t *testing.T) {
	for name, modPath := range map[string]string{
		"parent":   "../elsewhere",
		"absolute": "/etc/ck3",
	} {
		t.Run(name, func(t *testing.T) {
			if _, err := LauncherDescriptorText("name=\"A\"\n", "a_mod", modPath); err == nil {
				t.Fatal("expected an error")
			}
		})
	}
	if _, err := LauncherDescriptorText("name=\"A\"\n", "../escape", ""); err == nil {
		t.Fatal("expected an invalid slug to be rejected")
	}
}

func TestRenderRoundTrips(t *testing.T) {
	source := "name=\"A\"\ntags={\n\t\"Culture\"\n\t\"Fixes\"\n}\n"
	descriptor, err := Parse(source)
	if err != nil {
		t.Fatal(err)
	}
	if got := Render(descriptor); got != source {
		t.Errorf("Render() = %q, want %q", got, source)
	}
}
