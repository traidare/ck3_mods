package cli

import (
	"path/filepath"
	"strings"
	"time"

	"codeberg.org/traidare/ck3_mods/internal/config"
	"codeberg.org/traidare/ck3_mods/internal/jsonout"
	"codeberg.org/traidare/ck3_mods/internal/refs"
)

func refsCommand() *Command {
	return &Command{
		Name:    "refs",
		Summary: "Synchronize the local reference cache",
		Children: []*Command{{
			Name:    "sync",
			Summary: "Report or refresh references/generated",
			Usage:   "ck3mm refs sync [--apply]",
			Run:     runRefsSync,
		}},
	}
}

func runRefsSync(env *Env) (int, error) {
	if err := env.Config.Require(config.GameDir, config.ParadoxDir); err != nil {
		return 2, err
	}
	cacheRoot := filepath.Join(env.Workspace.Root, "references", "generated")

	built, err := refs.Build(env.Config.GameDir, env.Config.ParadoxDir, cacheRoot)
	if err != nil {
		return 1, err
	}
	var check refs.Check
	if env.Apply {
		check, err = built.Apply(time.Now())
	} else {
		check, err = built.Check()
	}
	if err != nil {
		return 1, err
	}

	if env.JSON() {
		if err := jsonout.Write(env.Stdout, check.JSON()); err != nil {
			return 1, err
		}
	} else {
		var builder strings.Builder
		check.Render(&builder)
		env.Printf("%s", builder.String())
	}
	if check.Current() {
		return 0, nil
	}
	return 1, nil
}
