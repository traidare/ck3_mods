package cli

import (
	"path/filepath"

	"codeberg.org/traidare/ck3_mods/internal/config"
	"codeberg.org/traidare/ck3_mods/internal/install"
	"codeberg.org/traidare/ck3_mods/internal/jsonout"
)

func runModInstall(env *Env) (int, error) {
	set := flagSet("mod install", env)
	mods, err := parse(set, env.Args)
	if err != nil {
		return 2, nil
	}
	if err := env.Config.Require(config.ParadoxDir); err != nil {
		return 2, err
	}

	plan, err := install.Build(env.Workspace, filepath.Join(env.Config.ParadoxDir, "mod"), mods)
	if err != nil {
		return 1, err
	}
	if env.Apply {
		if err := plan.Apply(); err != nil {
			return 1, err
		}
	}

	if env.JSON() {
		if err := jsonout.Write(env.Stdout, plan.JSON(env.Apply)); err != nil {
			return 1, err
		}
		return 0, nil
	}
	env.Printf("%s", plan.Summary(env.Apply))
	return 0, nil
}
