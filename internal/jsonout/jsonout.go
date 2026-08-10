// Package jsonout writes the repository's canonical JSON: two-space indent,
// alphabetically ordered keys, literal UTF-8, and a trailing newline.
//
// Ordering comes from encoding/json's map handling, which sorts keys, so every
// serialized document is built from map[string]any rather than a struct.
package jsonout

import (
	"bytes"
	"encoding/json"
	"io"
)

// Pair is one key and value inside an Ordered document.
type Pair struct {
	Key   string
	Value any
}

// Ordered is a JSON object that serializes in declaration order rather than
// alphabetically. Only the playset export uses it: that file is a portable
// artifact whose field order (game, name, mods) is part of its readability.
type Ordered []Pair

// MarshalJSON writes the pairs in order.
func (o Ordered) MarshalJSON() ([]byte, error) {
	var buffer bytes.Buffer
	buffer.WriteByte('{')
	for index, pair := range o {
		if index > 0 {
			buffer.WriteByte(',')
		}
		key, err := compactValue(pair.Key)
		if err != nil {
			return nil, err
		}
		buffer.Write(key)
		buffer.WriteByte(':')

		value, err := compactValue(pair.Value)
		if err != nil {
			return nil, err
		}
		buffer.Write(value)
	}
	buffer.WriteByte('}')
	return buffer.Bytes(), nil
}

// compactValue encodes one value without HTML escaping. The standard
// json.Marshal would escape <, > and &, and the outer encoder cannot undo it.
func compactValue(value any) ([]byte, error) {
	var buffer bytes.Buffer
	encoder := json.NewEncoder(&buffer)
	encoder.SetEscapeHTML(false)
	if err := encoder.Encode(value); err != nil {
		return nil, err
	}
	return bytes.TrimRight(buffer.Bytes(), "\n"), nil
}

// Marshal renders value in the canonical form.
func Marshal(value any) ([]byte, error) {
	var buffer bytes.Buffer
	encoder := json.NewEncoder(&buffer)
	encoder.SetEscapeHTML(false)
	encoder.SetIndent("", "  ")
	if err := encoder.Encode(value); err != nil {
		return nil, err
	}
	return buffer.Bytes(), nil
}

// String renders value in the canonical form as text.
func String(value any) (string, error) {
	data, err := Marshal(value)
	if err != nil {
		return "", err
	}
	return string(data), nil
}

// Write renders value to writer.
func Write(writer io.Writer, value any) error {
	data, err := Marshal(value)
	if err != nil {
		return err
	}
	_, err = writer.Write(data)
	return err
}
