// Package pdx parses Paradox Script. It provides the one tokenizer the whole
// tool uses, plus descriptor reading and Launcher descriptor derivation.
package pdx

import (
	"fmt"
	"path"
	"strings"

	"codeberg.org/traidare/ck3_mods/internal/fsutil"
)

// TokenKind distinguishes the four things Paradox Script is made of.
type TokenKind int

const (
	// TokenValue is a bare word or quoted string.
	TokenValue TokenKind = iota
	// TokenEquals is the '=' assignment operator.
	TokenEquals
	// TokenOpen is '{'.
	TokenOpen
	// TokenClose is '}'.
	TokenClose
)

// Token is one lexed unit together with the line it started on and its span
// in the source, as rune indices. The span lets callers quote a definition
// back exactly as it was written.
type Token struct {
	Kind  TokenKind
	Value string
	Line  int
	Start int
	End   int
}

const specials = " \t\r\n#={}"

// Tokenize lexes Paradox Script into a flat token stream.
func Tokenize(text string) ([]Token, error) {
	runes := []rune(text)
	var tokens []Token
	index := 0
	line := 1

	for index < len(runes) {
		character := runes[index]
		switch {
		case character == ' ' || character == '\t' || character == '\r':
			index++
		case character == '\n':
			line++
			index++
		case character == '#':
			for index < len(runes) && runes[index] != '\n' {
				index++
			}
		case character == '=':
			tokens = append(tokens, Token{TokenEquals, "=", line, index, index + 1})
			index++
		case character == '{':
			tokens = append(tokens, Token{TokenOpen, "{", line, index, index + 1})
			index++
		case character == '}':
			tokens = append(tokens, Token{TokenClose, "}", line, index, index + 1})
			index++
		case character == '"':
			startLine := line
			start := index
			index++
			var value strings.Builder
			terminated := false
			for index < len(runes) {
				character = runes[index]
				if character == '"' {
					index++
					terminated = true
					break
				}
				if character == '\\' {
					index++
					if index >= len(runes) {
						return nil, fmt.Errorf("unterminated escape on line %d", startLine)
					}
					switch runes[index] {
					case 'n':
						value.WriteRune('\n')
					case 'r':
						value.WriteRune('\r')
					case 't':
						value.WriteRune('\t')
					default:
						value.WriteRune(runes[index])
					}
				} else {
					value.WriteRune(character)
					if character == '\n' {
						line++
					}
				}
				index++
			}
			if !terminated {
				return nil, fmt.Errorf("unterminated string on line %d", startLine)
			}
			tokens = append(tokens, Token{TokenValue, value.String(), startLine, start, index})
		default:
			start := index
			for index < len(runes) && !strings.ContainsRune(specials, runes[index]) {
				index++
			}
			tokens = append(tokens, Token{TokenValue, string(runes[start:index]), line, start, index})
		}
	}
	return tokens, nil
}

// Field is one root-level assignment. Block records whether the source used
// braces, so rendering round-trips.
type Field struct {
	Key    string
	Values []string
	Block  bool
}

// Descriptor is the ordered set of root assignments in a .mod file.
type Descriptor struct {
	Fields []Field
}

// Values returns every value assigned to key, across repeated fields.
func (d Descriptor) Values(key string) []string {
	var result []string
	for _, field := range d.Fields {
		if field.Key == key {
			result = append(result, field.Values...)
		}
	}
	return result
}

// Value returns the single value for key, or fallback when it is absent. A key
// assigned more than once is an error rather than a silent last-writer choice.
func (d Descriptor) Value(key, fallback string) (string, error) {
	values := d.Values(key)
	if len(values) == 0 {
		return fallback, nil
	}
	if len(values) > 1 {
		return "", fmt.Errorf("descriptor field %q occurs more than once", key)
	}
	return values[0], nil
}

// Name returns the mod's declared name.
func (d Descriptor) Name() (string, error) {
	name, err := d.Value("name", "")
	if err != nil {
		return "", err
	}
	if name == "" {
		return "", fmt.Errorf("descriptor is missing a non-empty name")
	}
	return name, nil
}

// Has reports whether the descriptor assigns key at all.
func (d Descriptor) Has(key string) bool { return len(d.Values(key)) > 0 }

// ReplacePaths returns the mod's replace_path declarations, unnormalized.
func (d Descriptor) ReplacePaths() []string { return d.Values("replace_path") }

// Parse reads the root assignments used by native and Launcher descriptors.
func Parse(text string) (Descriptor, error) {
	tokens, err := Tokenize(text)
	if err != nil {
		return Descriptor{}, err
	}

	var fields []Field
	index := 0
	for index < len(tokens) {
		key := tokens[index]
		if key.Kind != TokenValue {
			return Descriptor{}, fmt.Errorf("expected a descriptor field on line %d, got %q", key.Line, key.Value)
		}
		index++
		if index >= len(tokens) || tokens[index].Kind != TokenEquals {
			return Descriptor{}, fmt.Errorf("expected '=' after %q on line %d", key.Value, key.Line)
		}
		index++
		if index >= len(tokens) {
			return Descriptor{}, fmt.Errorf("missing value for %q on line %d", key.Value, key.Line)
		}

		if tokens[index].Kind != TokenOpen {
			value := tokens[index]
			if value.Kind != TokenValue {
				return Descriptor{}, fmt.Errorf("invalid value for %q on line %d", key.Value, value.Line)
			}
			fields = append(fields, Field{Key: key.Value, Values: []string{value.Value}})
			index++
			continue
		}

		index++
		var values []string
		depth := 1
		for index < len(tokens) && depth > 0 {
			token := tokens[index]
			index++
			switch {
			case token.Kind == TokenOpen:
				depth++
			case token.Kind == TokenClose:
				depth--
			case token.Kind == TokenValue && depth == 1:
				values = append(values, token.Value)
			case token.Kind == TokenEquals && depth == 1:
				return Descriptor{}, fmt.Errorf("nested assignments are not supported in %q", key.Value)
			}
		}
		if depth > 0 {
			return Descriptor{}, fmt.Errorf("unterminated block for %q on line %d", key.Value, key.Line)
		}
		fields = append(fields, Field{Key: key.Value, Values: values, Block: true})
	}
	return Descriptor{Fields: fields}, nil
}

// Load reads and parses a descriptor file.
func Load(path string) (Descriptor, error) {
	text, err := fsutil.ReadTextBOM(path)
	if err != nil {
		return Descriptor{}, &ReadError{Path: path, Err: err}
	}
	return Parse(text)
}

// ReadError distinguishes an unreadable descriptor from an invalid one, so
// warnings can say which without leaking host paths.
type ReadError struct {
	Path string
	Err  error
}

func (e *ReadError) Error() string {
	return fmt.Sprintf("cannot read descriptor %s: %v", e.Path, e.Err)
}

func (e *ReadError) Unwrap() error { return e.Err }

// ValidateNative requires CK3-owned metadata and rejects the Launcher-only
// path field, which must never appear in a tracked descriptor.mod.
func ValidateNative(descriptor Descriptor) error {
	if _, err := descriptor.Name(); err != nil {
		return err
	}
	if descriptor.Has("path") {
		return fmt.Errorf("native descriptor.mod must not contain a Launcher-only path field")
	}
	return nil
}

func quoted(value string) string {
	escaped := strings.ReplaceAll(value, `\`, `\\`)
	escaped = strings.ReplaceAll(escaped, `"`, `\"`)
	return `"` + escaped + `"`
}

// Render writes a deterministic descriptor, primarily for synthetic metadata.
func Render(descriptor Descriptor) string {
	var lines []string
	for _, field := range descriptor.Fields {
		if field.Block {
			lines = append(lines, field.Key+"={")
			for _, value := range field.Values {
				lines = append(lines, "\t"+quoted(value))
			}
			lines = append(lines, "}")
			continue
		}
		for _, value := range field.Values {
			lines = append(lines, field.Key+"="+quoted(value))
		}
	}
	return strings.Join(lines, "\n") + "\n"
}

// LauncherDescriptorText derives a Launcher descriptor from native text,
// preserving the original formatting and appending only the path field.
func LauncherDescriptorText(nativeText, modSlug, launcherModPath string) (string, error) {
	descriptor, err := Parse(nativeText)
	if err != nil {
		return "", err
	}
	if err := ValidateNative(descriptor); err != nil {
		return "", err
	}
	if modSlug == "" || modSlug == "." || modSlug == ".." ||
		strings.ContainsAny(modSlug, `/\`) {
		return "", fmt.Errorf("invalid mod slug: %q", modSlug)
	}

	modPath := launcherModPath
	if modPath == "" {
		modPath = "mod/" + modSlug
	}
	cleaned := path.Clean(strings.ReplaceAll(modPath, `\`, "/"))
	if strings.HasPrefix(cleaned, "/") || cleaned == "." || cleaned == ".." ||
		strings.HasPrefix(cleaned, "../") {
		return "", fmt.Errorf("invalid Launcher mod path: %q", launcherModPath)
	}
	return strings.TrimRight(nativeText, "\n") + "\npath=" + quoted(cleaned) + "\n", nil
}

// DeriveLauncherDescriptor reads a native descriptor and returns its Launcher
// form without writing anything.
func DeriveLauncherDescriptor(nativePath, modSlug, launcherModPath string) (string, error) {
	nativeText, err := fsutil.ReadTextBOM(nativePath)
	if err != nil {
		return "", &ReadError{Path: nativePath, Err: err}
	}
	return LauncherDescriptorText(nativeText, modSlug, launcherModPath)
}
