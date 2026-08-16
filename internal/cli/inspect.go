package cli

import (
	"fmt"
	"strings"

	"codeberg.org/traidare/ck3_mods/internal/config"
	"codeberg.org/traidare/ck3_mods/internal/gamedata"
	"codeberg.org/traidare/ck3_mods/internal/report"
)

// Shared rendering for the game-data inspection commands, so cultures,
// traditions, and faiths all print provenance the same way.

// requireGameDirs checks the settings every inspection command needs.
func requireGameDirs(env *Env) error {
	return env.Config.Require(config.GameDir, config.WorkshopDir, config.ParadoxDir)
}

// reportWarnings sends load-order warnings to stderr so stdout stays
// machine-readable.
func reportWarnings(env *Env, warnings []report.Warning) {
	for _, warning := range warnings {
		fmt.Fprintf(env.Stderr, "warning: %s: %s\n", warning.Code, warning.Message)
	}
}

// layerLabel names the layer a definition came from, without host paths.
func layerLabel(layer gamedata.Layer) string {
	label := layer.Kind + "/" + layer.Name
	if layer.Position != nil {
		label += fmt.Sprintf(" #%d", *layer.Position)
	}
	return label
}

// row is one label/value line in a summary block. A row with an empty label
// continues the previous one; a row with an empty value is skipped.
type row struct {
	Label string
	Value string
}

// sourceRows render the provenance every summary ends with.
func sourceRows(definition gamedata.Definition) []row {
	return []row{
		{"source", layerLabel(definition.Layer)},
		{"", fmt.Sprintf("%s:%d", definition.RelativePath, definition.Line)},
	}
}

// writeRows prints aligned label/value lines.
func writeRows(env *Env, indent string, rows []row) {
	width := 0
	for _, entry := range rows {
		if entry.Value != "" && len(entry.Label) > width {
			width = len(entry.Label)
		}
	}
	for _, entry := range rows {
		if entry.Value == "" {
			continue
		}
		env.Printf("%s%-*s  %s\n", indent, width, entry.Label, entry.Value)
	}
}

// writeRaw prints a definition's source block, ensuring a trailing newline.
func writeRaw(env *Env, text string) {
	env.Printf("%s", text)
	if !strings.HasSuffix(text, "\n") {
		env.Printf("\n")
	}
}

// stringsOrEmpty makes a nil slice serialize as [] rather than null.
func stringsOrEmpty(values []string) []string {
	if values == nil {
		return []string{}
	}
	return values
}
