package cli

import (
	"strings"

	"codeberg.org/traidare/ck3_mods/internal/fsutil"
	"codeberg.org/traidare/ck3_mods/internal/jsonout"
)

func modCommand() *Command {
	return &Command{
		Name:    "mod",
		Summary: "Work with the mods in this workspace",
		Children: []*Command{{
			Name:    "list",
			Summary: "List local mods and their tooling",
			Usage:   "ck3mm mod list",
			Run:     runModList,
		}},
	}
}

func runModList(env *Env) (int, error) {
	mods, err := env.Workspace.Mods()
	if err != nil {
		return 1, err
	}

	if env.JSON() {
		payload := make([]any, len(mods))
		for index, mod := range mods {
			payload[index] = map[string]any{
				"slug":       mod.Slug,
				"descriptor": fsutil.IsFile(mod.DescriptorPath),
				"manifest":   mod.Manifest != nil,
				"generator":  mod.HasGenerator(),
			}
		}
		if err := jsonout.Write(env.Stdout, payload); err != nil {
			return 1, err
		}
		return 0, nil
	}

	for _, mod := range mods {
		var features []string
		if mod.Manifest != nil {
			features = append(features, "manifest")
		}
		if mod.HasGenerator() {
			features = append(features, "generator")
		}
		suffix := ""
		if len(features) > 0 {
			suffix = " (" + strings.Join(features, ", ") + ")"
		}
		env.Printf("%s%s\n", mod.Slug, suffix)
	}
	return 0, nil
}
