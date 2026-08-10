package cli

import (
	"codeberg.org/traidare/ck3_mods/internal/config"
	"codeberg.org/traidare/ck3_mods/internal/jsonout"
)

func configCommand() *Command {
	return &Command{
		Name:    "config",
		Summary: "Inspect the local CK3 configuration",
		Children: []*Command{{
			Name:    "check",
			Summary: "Validate the required CK3 paths",
			Usage:   "ck3mm config check",
			Run:     runConfigCheck,
		}},
	}
}

func runConfigCheck(env *Env) (int, error) {
	if err := env.Config.Require(); err != nil {
		return 1, err
	}
	values := env.Config.Environment()

	if env.JSON() {
		payload := map[string]any{}
		for name, value := range values {
			payload[name] = value
		}
		if err := jsonout.Write(env.Stdout, payload); err != nil {
			return 1, err
		}
		return 0, nil
	}

	for _, variable := range config.KnownVariables {
		value, ok := values[variable]
		if !ok {
			value = "<unset>"
		}
		env.Printf("%s=%s\n", variable, value)
	}
	return 0, nil
}
