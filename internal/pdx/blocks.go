package pdx

// Structural helpers over a token stream. Descriptors only need root-level
// assignments, but game data is nested, so these expose blocks and their
// immediate contents without building a full tree.

// Block is one `key = { ... }` assignment. OpenIndex and CloseIndex are token
// indices, so callers can quote the exact source span.
type Block struct {
	Key        Token
	OpenIndex  int
	CloseIndex int
}

// MatchBraces pairs every opening brace with its closing one. Label names the
// source in error messages.
func MatchBraces(tokens []Token, label string) (map[int]int, error) {
	matches := map[int]int{}
	var stack []int
	for index, token := range tokens {
		switch token.Kind {
		case TokenOpen:
			stack = append(stack, index)
		case TokenClose:
			if len(stack) == 0 {
				return nil, errorf("%s:%d: unexpected closing brace", label, token.Line)
			}
			matches[stack[len(stack)-1]] = index
			stack = stack[:len(stack)-1]
		}
	}
	if len(stack) > 0 {
		return nil, errorf("%s:%d: unclosed block", label, tokens[stack[len(stack)-1]].Line)
	}
	return matches, nil
}

// TopLevelBlocks returns the `key = { ... }` assignments at depth zero.
func TopLevelBlocks(tokens []Token, matches map[int]int) []Block {
	var blocks []Block
	depth := 0
	index := 0
	for index < len(tokens) {
		token := tokens[index]
		if token.Kind == TokenOpen {
			depth++
			index++
			continue
		}
		if token.Kind == TokenClose {
			depth--
			index++
			continue
		}
		if depth == 0 && token.Kind == TokenValue && index+2 < len(tokens) &&
			tokens[index+1].Kind == TokenEquals && tokens[index+2].Kind == TokenOpen {
			openIndex := index + 2
			closeIndex := matches[openIndex]
			blocks = append(blocks, Block{Key: token, OpenIndex: openIndex, CloseIndex: closeIndex})
			index = closeIndex + 1
			continue
		}
		index++
	}
	return blocks
}

// Assignment is one immediate key/value pair inside a block. ValueClose is -1
// unless the value is itself a block.
type Assignment struct {
	Key        Token
	Value      Token
	ValueOpen  int
	ValueClose int
}

// DirectAssignments yields the immediate key/value pairs of one block,
// skipping anything nested deeper.
func DirectAssignments(tokens []Token, matches map[int]int, openIndex, closeIndex int) []Assignment {
	var assignments []Assignment
	index := openIndex + 1
	for index < closeIndex {
		token := tokens[index]
		if token.Kind == TokenValue && index+2 < closeIndex && tokens[index+1].Kind == TokenEquals {
			value := tokens[index+2]
			if value.Kind == TokenOpen {
				valueClose := matches[index+2]
				assignments = append(assignments, Assignment{token, value, index + 2, valueClose})
				index = valueClose + 1
				continue
			}
			assignments = append(assignments, Assignment{token, value, -1, -1})
			index += 3
			continue
		}
		if token.Kind == TokenOpen {
			index = matches[index] + 1
			continue
		}
		index++
	}
	return assignments
}

// BlockValues returns the bare list entries of a block, ignoring assignments
// and nested blocks.
func BlockValues(tokens []Token, openIndex, closeIndex int) []string {
	var values []string
	depth := 0
	for index := openIndex + 1; index < closeIndex; index++ {
		token := tokens[index]
		switch token.Kind {
		case TokenOpen:
			depth++
		case TokenClose:
			depth--
		case TokenValue:
			if depth != 0 {
				continue
			}
			if index+1 < closeIndex && tokens[index+1].Kind == TokenEquals {
				continue
			}
			values = append(values, token.Value)
		}
	}
	return values
}
