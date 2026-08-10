package fsutil

import "testing"

// The manifests were written against Python's fnmatch, where `*` crosses
// directory separators. filepath.Match does not, so the difference is worth
// pinning down.
func TestMatchGlob(t *testing.T) {
	cases := []struct {
		pattern string
		value   string
		want    bool
	}{
		{"README.md", "README.md", true},
		{"README.md", "docs/README.md", false},
		{"*.md", "docs/README.md", true},
		{"docs/*", "docs/a/b.txt", true},
		{".ck3mm/**", ".ck3mm", true},
		{".ck3mm/**", ".ck3mm/gen/x.py", true},
		{".ck3mm/**", ".ck3mmm/x", false},
		{"common/?.txt", "common/a.txt", true},
		{"common/?.txt", "common/ab.txt", false},
		{"common/[ab].txt", "common/b.txt", true},
		{"common/[!ab].txt", "common/b.txt", false},
		{"common/[!ab].txt", "common/c.txt", true},
		{"a.b", "axb", false},
		{`content_source\**`, "content_source/raw/x", true},
	}
	for _, testCase := range cases {
		if got := MatchGlob(testCase.pattern, testCase.value); got != testCase.want {
			t.Errorf("MatchGlob(%q, %q) = %v, want %v",
				testCase.pattern, testCase.value, got, testCase.want)
		}
	}
}
