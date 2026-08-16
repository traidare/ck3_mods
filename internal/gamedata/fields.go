package gamedata

import (
	"fmt"

	"codeberg.org/traidare/ck3_mods/internal/pdx"
)

// Fields reads the immediate assignments of one block. Callers name the keys
// they want, so this package stays free of any database's schema.
type Fields struct {
	tokens     []pdx.Token
	matches    map[int]int
	runes      []rune
	openIndex  int
	closeIndex int
	// lineOffset shifts reported lines back onto the original file, since a
	// definition's Text is re-tokenized on its own.
	lineOffset int
}

// Fields re-parses one definition's own block. Text is a self-contained
// `key = { ... }` snippet, so the tokenizer round-trips it.
func (d Definition) Fields() (Fields, error) {
	tokens, err := pdx.Tokenize(d.Text)
	if err != nil {
		return Fields{}, fmt.Errorf("%s: %w", d.Identifier, err)
	}
	matches, err := pdx.MatchBraces(tokens, d.Identifier)
	if err != nil {
		return Fields{}, err
	}
	blocks := pdx.TopLevelBlocks(tokens, matches)
	if len(blocks) != 1 {
		return Fields{}, fmt.Errorf("%s: expected one block, got %d", d.Identifier, len(blocks))
	}
	return Fields{
		tokens:     tokens,
		matches:    matches,
		runes:      []rune(d.Text),
		openIndex:  blocks[0].OpenIndex,
		closeIndex: blocks[0].CloseIndex,
		lineOffset: d.Line - 1,
	}, nil
}

func (f Fields) assignments() []pdx.Assignment {
	return pdx.DirectAssignments(f.tokens, f.matches, f.openIndex, f.closeIndex)
}

// Scalar returns the last `key = value` assignment, or the empty string when
// the key is absent. Later assignments win, matching the engine.
func (f Fields) Scalar(key string) string {
	value := ""
	for _, assignment := range f.assignments() {
		if assignment.Key.Value == key && assignment.ValueClose < 0 {
			value = assignment.Value.Value
		}
	}
	return value
}

// Scalars returns every `key = value` assignment in order, which is how
// repeated keys such as `doctrine` and `holy_site` are written.
func (f Fields) Scalars(key string) []string {
	var values []string
	for _, assignment := range f.assignments() {
		if assignment.Key.Value == key && assignment.ValueClose < 0 {
			values = append(values, assignment.Value.Value)
		}
	}
	return values
}

// List returns the bare entries of every `key = { a b c }` block, in order.
func (f Fields) List(key string) []string {
	var values []string
	for _, assignment := range f.assignments() {
		if assignment.Key.Value == key && assignment.ValueClose >= 0 {
			values = append(values, pdx.BlockValues(f.tokens, assignment.ValueOpen, assignment.ValueClose)...)
		}
	}
	return values
}

// Blocks returns every `key = { ... }` value as its own Fields.
func (f Fields) Blocks(key string) []Fields {
	var blocks []Fields
	for _, assignment := range f.assignments() {
		if assignment.Key.Value == key && assignment.ValueClose >= 0 {
			blocks = append(blocks, Fields{
				tokens:     f.tokens,
				matches:    f.matches,
				runes:      f.runes,
				openIndex:  assignment.ValueOpen,
				closeIndex: assignment.ValueClose,
				lineOffset: f.lineOffset,
			})
		}
	}
	return blocks
}

// Pair is one immediate `key = value` assignment, for blocks whose keys are
// data rather than schema, such as modifier and parameter blocks.
type Pair struct {
	Key   string
	Value string
}

// Pairs returns the immediate scalar assignments in source order.
func (f Fields) Pairs() []Pair {
	var pairs []Pair
	for _, assignment := range f.assignments() {
		if assignment.ValueClose < 0 {
			pairs = append(pairs, Pair{Key: assignment.Key.Value, Value: assignment.Value.Value})
		}
	}
	return pairs
}

// Children extracts the named sub-blocks of a container key as Definitions
// carrying the parent's provenance, which is how faiths come out of
// `faiths = { catholic = { ... } }`. Lines are mapped back onto the file.
func (d Definition) Children(containerKey string) ([]Definition, error) {
	fields, err := d.Fields()
	if err != nil {
		return nil, err
	}

	var children []Definition
	for _, container := range fields.Blocks(containerKey) {
		for _, assignment := range container.assignments() {
			if assignment.ValueClose < 0 {
				continue
			}
			children = append(children, Definition{
				Identifier:   assignment.Key.Value,
				Text:         string(container.runes[assignment.Key.Start:container.tokens[assignment.ValueClose].End]),
				Layer:        d.Layer,
				RelativePath: d.RelativePath,
				Line:         assignment.Key.Line + container.lineOffset,
			})
		}
	}
	return children, nil
}
