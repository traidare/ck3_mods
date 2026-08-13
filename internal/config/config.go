// Package config resolves the local CK3 paths from flags, the process
// environment, and the repository dotenv, in that order of precedence.
//
// Nothing here mutates the process environment.
package config

import (
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"unicode"
)

// The variables this repository understands. The first three are required by
// every command that touches installed CK3 content.
const (
	GameDir     = "CK3_GAME_DIR"
	ParadoxDir  = "CK3_PARADOX_DIR"
	WorkshopDir = "CK3_WORKSHOP_DIR"
	SteamLogDir = "CK3_STEAM_LOG_DIR"
	PlaysetName = "CK3_PLAYSET_NAME"
)

// PathVariables lists every variable holding a filesystem path.
var PathVariables = []string{GameDir, ParadoxDir, WorkshopDir, SteamLogDir}

// RequiredPathVariables must be set and point at real directories.
var RequiredPathVariables = []string{GameDir, ParadoxDir, WorkshopDir}

// KnownVariables lists every recognized setting, in report order.
var KnownVariables = []string{GameDir, ParadoxDir, WorkshopDir, SteamLogDir, PlaysetName}

// LauncherDatabaseName is the Launcher's SQLite file inside CK3_PARADOX_DIR.
const LauncherDatabaseName = "launcher-v2.sqlite"

var dotenvKey = regexp.MustCompile(`^[A-Za-z_][A-Za-z0-9_]*$`)

// Config holds the resolved settings for one invocation.
type Config struct {
	RepoRoot    string
	GameDir     string
	ParadoxDir  string
	WorkshopDir string
	SteamLogDir string
	PlaysetName string
}

// LauncherDB returns the Launcher database implied by CK3_PARADOX_DIR, or the
// empty string when that directory is unset.
func (c Config) LauncherDB() string {
	if c.ParadoxDir == "" {
		return ""
	}
	return filepath.Join(c.ParadoxDir, LauncherDatabaseName)
}

// Value returns the resolved setting for one variable name.
func (c Config) Value(variable string) string {
	switch variable {
	case GameDir:
		return c.GameDir
	case ParadoxDir:
		return c.ParadoxDir
	case WorkshopDir:
		return c.WorkshopDir
	case SteamLogDir:
		return c.SteamLogDir
	case PlaysetName:
		return c.PlaysetName
	}
	return ""
}

// Environment returns the configured values under the names CK3 tooling wants.
func (c Config) Environment() map[string]string {
	result := map[string]string{}
	for _, variable := range KnownVariables {
		if value := c.Value(variable); value != "" {
			result[variable] = value
		}
	}
	return result
}

// Require validates the named variables, collecting every problem at once.
func (c Config) Require(variables ...string) error {
	if len(variables) == 0 {
		variables = RequiredPathVariables
	}
	var problems []string
	for _, variable := range variables {
		value := c.Value(variable)
		if value == "" {
			problems = append(problems, variable+" is not set")
			continue
		}
		if variable == PlaysetName {
			continue
		}
		info, err := os.Stat(value)
		if err != nil || !info.IsDir() {
			problems = append(problems, fmt.Sprintf("%s is not a directory: %s", variable, value))
		}
	}
	if len(problems) > 0 {
		return fmt.Errorf("invalid CK3 configuration:\n- %s", strings.Join(problems, "\n- "))
	}
	return nil
}

func stripInlineComment(value string) string {
	runes := []rune(value)
	for index, character := range runes {
		if character == '#' && (index == 0 || unicode.IsSpace(runes[index-1])) {
			return strings.TrimRight(string(runes[:index]), " \t")
		}
	}
	return strings.TrimSpace(value)
}

func parseDotenvValue(value string, lineNumber int, path string) (string, error) {
	value = strings.TrimSpace(value)
	if value == "" {
		return "", nil
	}
	quote := value[0]
	if quote != '\'' && quote != '"' {
		return stripInlineComment(value), nil
	}

	runes := []rune(value)
	escaped := false
	closing := -1
	for index := 1; index < len(runes); index++ {
		character := runes[index]
		if quote == '"' && character == '\\' && !escaped {
			escaped = true
			continue
		}
		if character == rune(quote) && !escaped {
			closing = index
			break
		}
		escaped = false
	}
	if closing < 0 {
		return "", fmt.Errorf("%s:%d: unterminated quoted value", path, lineNumber)
	}
	remainder := strings.TrimSpace(string(runes[closing+1:]))
	if remainder != "" && !strings.HasPrefix(remainder, "#") {
		return "", fmt.Errorf("%s:%d: unexpected text after quoted value", path, lineNumber)
	}

	parsed := string(runes[1:closing])
	if quote == '"' {
		replacer := strings.NewReplacer(
			`\n`, "\n",
			`\r`, "\r",
			`\t`, "\t",
			`\"`, `"`,
			`\\`, `\`,
		)
		parsed = replacer.Replace(parsed)
	}
	return parsed, nil
}

// ReadDotenv parses the small, deterministic dotenv subset this repository
// uses. A missing file is not an error.
func ReadDotenv(path string) (map[string]string, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		if os.IsNotExist(err) {
			return map[string]string{}, nil
		}
		return nil, fmt.Errorf("cannot read %s: %w", path, err)
	}

	values := map[string]string{}
	for index, rawLine := range strings.Split(strings.ReplaceAll(string(data), "\r\n", "\n"), "\n") {
		lineNumber := index + 1
		line := strings.TrimSpace(rawLine)
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		line = strings.TrimPrefix(line, "export ")
		line = strings.TrimLeft(line, " \t")
		key, rawValue, found := strings.Cut(line, "=")
		if !found {
			return nil, fmt.Errorf("%s:%d: expected KEY=VALUE", path, lineNumber)
		}
		key = strings.TrimSpace(key)
		if !dotenvKey.MatchString(key) {
			return nil, fmt.Errorf("%s:%d: invalid variable name %q", path, lineNumber, key)
		}
		value, err := parseDotenvValue(rawValue, lineNumber, path)
		if err != nil {
			return nil, err
		}
		values[key] = value
	}
	return values, nil
}

func configuredPath(variable, raw string) (string, error) {
	if strings.TrimSpace(raw) == "" {
		return "", nil
	}
	path, err := expandUser(raw)
	if err != nil {
		return "", err
	}
	if !filepath.IsAbs(path) {
		return "", fmt.Errorf("%s must be an absolute path: %s", variable, raw)
	}
	if resolved, err := filepath.EvalSymlinks(path); err == nil {
		return resolved, nil
	}
	return filepath.Clean(path), nil
}

func expandUser(path string) (string, error) {
	if !strings.HasPrefix(path, "~") {
		return path, nil
	}
	if path != "~" && !strings.HasPrefix(path, "~/") {
		// Only the current user's home is supported, as in pathlib.expanduser.
		return path, nil
	}
	home, err := os.UserHomeDir()
	if err != nil {
		return "", fmt.Errorf("cannot expand %q: %w", path, err)
	}
	return filepath.Join(home, strings.TrimPrefix(strings.TrimPrefix(path, "~"), "/")), nil
}

// Options carries the explicit overrides a command-line invocation supplies.
// An entry that is present but empty still wins, which is how an optional
// setting is cleared from the command line.
type Options struct {
	Overrides  map[string]string
	Environ    map[string]string
	DotenvPath string
}

// Load resolves configuration with flags > process environment > dotenv.
func Load(repoRoot string, options Options) (Config, error) {
	root, err := filepath.Abs(repoRoot)
	if err != nil {
		return Config{}, fmt.Errorf("cannot resolve repository root: %w", err)
	}

	dotenvPath := options.DotenvPath
	if dotenvPath == "" {
		dotenvPath = filepath.Join(root, ".env")
	}
	dotenv, err := ReadDotenv(dotenvPath)
	if err != nil {
		return Config{}, err
	}

	environ := options.Environ
	if environ == nil {
		environ = processEnvironment()
	}
	for name := range options.Overrides {
		if !known(name) {
			return Config{}, fmt.Errorf("unknown configuration override: %s", name)
		}
	}

	values := map[string]string{}
	for _, variable := range KnownVariables {
		if value, ok := options.Overrides[variable]; ok {
			values[variable] = value
		} else if value, ok := environ[variable]; ok {
			values[variable] = value
		} else {
			values[variable] = dotenv[variable]
		}
	}

	config := Config{RepoRoot: root, PlaysetName: strings.TrimSpace(values[PlaysetName])}
	for _, variable := range PathVariables {
		resolved, err := configuredPath(variable, values[variable])
		if err != nil {
			return Config{}, err
		}
		switch variable {
		case GameDir:
			config.GameDir = resolved
		case ParadoxDir:
			config.ParadoxDir = resolved
		case WorkshopDir:
			config.WorkshopDir = resolved
		case SteamLogDir:
			config.SteamLogDir = resolved
		}
	}
	return config, nil
}

func known(variable string) bool {
	for _, candidate := range KnownVariables {
		if candidate == variable {
			return true
		}
	}
	return false
}

func processEnvironment() map[string]string {
	environ := map[string]string{}
	for _, entry := range os.Environ() {
		if key, value, found := strings.Cut(entry, "="); found {
			environ[key] = value
		}
	}
	return environ
}
