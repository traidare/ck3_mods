package config

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func writeDotenv(t *testing.T, body string) string {
	t.Helper()
	root := t.TempDir()
	path := filepath.Join(root, ".env")
	if err := os.WriteFile(path, []byte(body), 0o644); err != nil {
		t.Fatal(err)
	}
	return root
}

func TestReadDotenvValueForms(t *testing.T) {
	root := writeDotenv(t, `
# a comment
BARE=/tmp/bare
TRAILING=/tmp/plain   # inline comment
export EXPORTED=/tmp/exported
SINGLE='/tmp/with #hash'
DOUBLE="/tmp/a\tb"
EMPTY=
NOT_A_COMMENT=/tmp/a#b
`)

	values, err := ReadDotenv(filepath.Join(root, ".env"))
	if err != nil {
		t.Fatalf("ReadDotenv: %v", err)
	}
	expected := map[string]string{
		"BARE":          "/tmp/bare",
		"TRAILING":      "/tmp/plain",
		"EXPORTED":      "/tmp/exported",
		"SINGLE":        "/tmp/with #hash",
		"DOUBLE":        "/tmp/a\tb",
		"EMPTY":         "",
		"NOT_A_COMMENT": "/tmp/a#b",
	}
	for key, want := range expected {
		if got := values[key]; got != want {
			t.Errorf("%s = %q, want %q", key, got, want)
		}
	}
}

func TestReadDotenvRejectsMalformedLines(t *testing.T) {
	for name, body := range map[string]string{
		"missing separator": "JUST_A_KEY\n",
		"invalid name":      "9INVALID=1\n",
		"unterminated":      "KEY=\"unclosed\n",
		"text after quote":  "KEY=\"value\" trailing\n",
	} {
		t.Run(name, func(t *testing.T) {
			root := writeDotenv(t, body)
			if _, err := ReadDotenv(filepath.Join(root, ".env")); err == nil {
				t.Fatal("expected an error")
			}
		})
	}
}

func TestReadDotenvMissingFileIsEmpty(t *testing.T) {
	values, err := ReadDotenv(filepath.Join(t.TempDir(), "absent"))
	if err != nil {
		t.Fatalf("ReadDotenv: %v", err)
	}
	if len(values) != 0 {
		t.Fatalf("expected no values, got %v", values)
	}
}

func TestLoadPrecedence(t *testing.T) {
	root := t.TempDir()
	game := filepath.Join(root, "game")
	paradox := filepath.Join(root, "paradox")
	workshop := filepath.Join(root, "workshop")
	for _, directory := range []string{game, paradox, workshop} {
		if err := os.MkdirAll(directory, 0o755); err != nil {
			t.Fatal(err)
		}
	}
	dotenv := filepath.Join(root, ".env")
	body := "CK3_GAME_DIR=" + game + "\nCK3_PARADOX_DIR=" + paradox +
		"\nCK3_WORKSHOP_DIR=" + workshop + "\nCK3_PLAYSET_NAME=FromDotenv\n"
	if err := os.WriteFile(dotenv, []byte(body), 0o644); err != nil {
		t.Fatal(err)
	}

	t.Run("dotenv is the base layer", func(t *testing.T) {
		config, err := Load(root, Options{Environ: map[string]string{}})
		if err != nil {
			t.Fatal(err)
		}
		if config.PlaysetName != "FromDotenv" {
			t.Errorf("playset = %q, want FromDotenv", config.PlaysetName)
		}
	})

	t.Run("environment beats dotenv", func(t *testing.T) {
		config, err := Load(root, Options{
			Environ: map[string]string{PlaysetName: "FromEnviron"},
		})
		if err != nil {
			t.Fatal(err)
		}
		if config.PlaysetName != "FromEnviron" {
			t.Errorf("playset = %q, want FromEnviron", config.PlaysetName)
		}
	})

	t.Run("override beats environment", func(t *testing.T) {
		config, err := Load(root, Options{
			Overrides: map[string]string{PlaysetName: "FromFlag"},
			Environ:   map[string]string{PlaysetName: "FromEnviron"},
		})
		if err != nil {
			t.Fatal(err)
		}
		if config.PlaysetName != "FromFlag" {
			t.Errorf("playset = %q, want FromFlag", config.PlaysetName)
		}
	})

	t.Run("an empty override clears an optional setting", func(t *testing.T) {
		config, err := Load(root, Options{
			Overrides: map[string]string{PlaysetName: ""},
			Environ:   map[string]string{PlaysetName: "FromEnviron"},
		})
		if err != nil {
			t.Fatal(err)
		}
		if config.PlaysetName != "" {
			t.Errorf("playset = %q, want empty", config.PlaysetName)
		}
	})
}

func TestLoadRejectsRelativePaths(t *testing.T) {
	root := t.TempDir()
	_, err := Load(root, Options{
		Overrides: map[string]string{GameDir: "relative/path"},
		Environ:   map[string]string{},
	})
	if err == nil {
		t.Fatal("expected an error for a relative path")
	}
}

func TestRequireCollectsEveryProblem(t *testing.T) {
	root := t.TempDir()
	config := Config{RepoRoot: root, GameDir: filepath.Join(root, "absent")}
	err := config.Require(GameDir, ParadoxDir, WorkshopDir)
	if err == nil {
		t.Fatal("expected an error")
	}
	for _, fragment := range []string{
		"CK3_GAME_DIR is not a directory",
		"CK3_PARADOX_DIR is not set",
		"CK3_WORKSHOP_DIR is not set",
	} {
		if !strings.Contains(err.Error(), fragment) {
			t.Errorf("error %q is missing %q", err, fragment)
		}
	}
}
