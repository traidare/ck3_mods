package fsutil

import (
	"regexp"
	"strings"
	"sync"
)

var (
	patternCacheMutex sync.Mutex
	patternCache      = map[string]*regexp.Regexp{}
)

// MatchGlob reports whether a slash-separated relative path matches a shell
// pattern. The semantics are Python's fnmatch, not filepath.Match: `*` and `?`
// cross directory separators, and a trailing `/**` also matches the directory
// itself. The manifests were written against fnmatch, so this must stay
// compatible with them.
func MatchGlob(pattern, value string) bool {
	normalized := strings.TrimRight(strings.ReplaceAll(pattern, `\`, "/"), "/")
	if compileGlob(normalized).MatchString(value) {
		return true
	}
	if suffix := strings.TrimSuffix(normalized, "/**"); suffix != normalized {
		prefix := strings.TrimRight(suffix, "/")
		return value == prefix || strings.HasPrefix(value, prefix+"/")
	}
	return false
}

// MatchAnyGlob reports whether any pattern matches.
func MatchAnyGlob(patterns []string, value string) bool {
	for _, pattern := range patterns {
		if MatchGlob(pattern, value) {
			return true
		}
	}
	return false
}

func compileGlob(pattern string) *regexp.Regexp {
	patternCacheMutex.Lock()
	defer patternCacheMutex.Unlock()
	if compiled, ok := patternCache[pattern]; ok {
		return compiled
	}
	compiled := regexp.MustCompile(translateGlob(pattern))
	patternCache[pattern] = compiled
	return compiled
}

// translateGlob converts one fnmatch pattern into an anchored regular
// expression, mirroring fnmatch.translate.
func translateGlob(pattern string) string {
	var builder strings.Builder
	builder.WriteString(`\A`)
	runes := []rune(pattern)
	for index := 0; index < len(runes); index++ {
		character := runes[index]
		switch character {
		case '*':
			builder.WriteString(`.*`)
		case '?':
			builder.WriteString(`.`)
		case '[':
			closing := index + 1
			if closing < len(runes) && (runes[closing] == '!' || runes[closing] == '^') {
				closing++
			}
			if closing < len(runes) && runes[closing] == ']' {
				closing++
			}
			for closing < len(runes) && runes[closing] != ']' {
				closing++
			}
			if closing >= len(runes) {
				builder.WriteString(regexp.QuoteMeta("["))
				continue
			}
			body := string(runes[index+1 : closing])
			index = closing
			if strings.HasPrefix(body, "!") {
				body = "^" + body[1:]
			}
			builder.WriteString("[" + strings.ReplaceAll(body, `\`, `\\`) + "]")
		default:
			builder.WriteString(regexp.QuoteMeta(string(character)))
		}
	}
	builder.WriteString(`\z`)
	return builder.String()
}
