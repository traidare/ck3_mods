package cli

import (
	"path/filepath"

	"codeberg.org/traidare/ck3_mods/internal/config"
	"codeberg.org/traidare/ck3_mods/internal/install"
	"codeberg.org/traidare/ck3_mods/internal/jsonout"
	"codeberg.org/traidare/ck3_mods/internal/plan"
)

func runModInstall(env *Env) (int, error) {
	set := flagSet("mod install", env)
	var verbose bool
	set.BoolVar(&verbose, "verbose", false, "print each file as it is handled")
	set.BoolVar(&verbose, "v", false, "shorthand for --verbose")
	mods, err := parse(set, env.Args)
	if err != nil {
		return 2, nil
	}
	if err := env.Config.Require(config.ParadoxDir); err != nil {
		return 2, err
	}

	operations, err := install.Build(env.Workspace, filepath.Join(env.Config.ParadoxDir, "mod"), mods)
	if err != nil {
		return 1, err
	}

	// Verbose output is a text-mode affordance; the JSON plan already carries a
	// status per file.
	stream := verbose && !env.JSON()
	if stream && env.Apply {
		// Applying reports each operation as it completes, so the output tracks
		// the work rather than the plan.
		operations.Ops.Observer = func(op plan.Op) { writeInstallOp(env, operations.LauncherModDir, op) }
	}
	if env.Apply {
		if err := operations.Apply(); err != nil {
			return 1, err
		}
	} else if stream {
		for _, op := range operations.Ops.Ops {
			writeInstallOp(env, operations.LauncherModDir, op)
		}
	}

	if env.JSON() {
		if err := jsonout.Write(env.Stdout, operations.JSON(env.Apply)); err != nil {
			return 1, err
		}
		return 0, nil
	}
	env.Printf("%s", operations.Summary(env.Apply))
	return 0, nil
}

// writeInstallOp prints one rsync-style line. Unchanged files are skipped, as
// `rsync -v` skips the files it did not transfer.
func writeInstallOp(env *Env, launcherModDir string, op plan.Op) {
	if op.Status == plan.Unchanged {
		return
	}
	var marker string
	switch op.Kind {
	case plan.Copy:
		marker = "+"
		if op.Status == plan.Changed {
			marker = "~"
		}
	case plan.Write:
		marker = "*"
	case plan.Remove:
		marker = "-"
	default:
		return
	}
	env.Printf("%s %s\n", marker, installRelative(launcherModDir, op.Path))
}

// installRelative shortens a destination to its path inside the Launcher mod
// directory, keeping the host root out of the listing.
func installRelative(launcherModDir, path string) string {
	relative, err := filepath.Rel(launcherModDir, path)
	if err != nil {
		return path
	}
	return filepath.ToSlash(relative)
}
