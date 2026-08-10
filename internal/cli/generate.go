package cli

import (
	"encoding/json"
	"fmt"
	"sort"
	"strings"

	"codeberg.org/traidare/ck3_mods/internal/fsutil"
	"codeberg.org/traidare/ck3_mods/internal/generate"
	"codeberg.org/traidare/ck3_mods/internal/jsonout"
	"codeberg.org/traidare/ck3_mods/internal/pdx"
	"codeberg.org/traidare/ck3_mods/internal/validate"
	"codeberg.org/traidare/ck3_mods/internal/workspace"
)

// generatorMods returns the named mods, or every mod that has a generator.
func generatorMods(env *Env, slugs []string) ([]*workspace.Mod, error) {
	if len(slugs) > 0 {
		selected := make([]*workspace.Mod, 0, len(slugs))
		for _, slug := range slugs {
			mod, err := env.Workspace.Mod(slug)
			if err != nil {
				return nil, err
			}
			selected = append(selected, mod)
		}
		return selected, nil
	}
	mods, err := env.Workspace.Mods()
	if err != nil {
		return nil, err
	}
	var withGenerator []*workspace.Mod
	for _, mod := range mods {
		if mod.HasGenerator() {
			withGenerator = append(withGenerator, mod)
		}
	}
	return withGenerator, nil
}

// generatorOptions parses repeatable --option NAME[=JSON] pairs.
func generatorOptions(values []string) (map[string]any, error) {
	options := map[string]any{}
	for _, raw := range values {
		key, value, hasValue := strings.Cut(raw, "=")
		if !isIdentifier(key) {
			return nil, fmt.Errorf("invalid generator option name: %q", key)
		}
		if !hasValue {
			options[key] = true
			continue
		}
		var decoded any
		if err := json.Unmarshal([]byte(value), &decoded); err != nil {
			options[key] = value
			continue
		}
		options[key] = decoded
	}
	return options, nil
}

func isIdentifier(value string) bool {
	if value == "" {
		return false
	}
	for index, character := range value {
		letter := character == '_' ||
			(character >= 'a' && character <= 'z') ||
			(character >= 'A' && character <= 'Z')
		digit := character >= '0' && character <= '9'
		if !letter && !(index > 0 && digit) {
			return false
		}
	}
	return true
}

func runModGenerate(env *Env) (int, error) {
	set := flagSet("mod generate", env)
	var options stringList
	set.Var(&options, "option", "generator option NAME[=JSON] (repeatable)")
	slugs, err := parse(set, env.Args)
	if err != nil {
		return 2, nil
	}
	values, err := generatorOptions(options)
	if err != nil {
		return 2, err
	}

	mods, err := generatorMods(env, slugs)
	if err != nil {
		return 1, err
	}

	failed := false
	stale := false
	reports := make([]any, 0, len(mods))
	for _, mod := range mods {
		result, err := generate.Run(env.Workspace, mod, env.Config,
			generate.Options{Apply: env.Apply, Values: values})
		if err != nil {
			failed = true
			if env.JSON() {
				reports = append(reports, map[string]any{
					"slug": mod.Slug, "status": "error", "error": err.Error(),
				})
				continue
			}
			fmt.Fprintf(env.Stderr, "%s: error: %v\n", mod.Slug, err)
			continue
		}

		paths := append(append([]string{}, result.ChangedFiles...), result.StaleFiles...)
		sort.Strings(paths)
		if env.JSON() {
			status := "current"
			if !result.Current() {
				status = "stale"
				if env.Apply {
					status = "updated"
				}
			}
			reports = append(reports, map[string]any{
				"slug":    mod.Slug,
				"status":  status,
				"changed": result.ChangedFiles,
				"stale":   result.StaleFiles,
				"stdout":  result.Stdout,
				"stderr":  result.Stderr,
			})
		}

		if result.Stdout != "" && !env.JSON() {
			fmt.Fprint(env.Stdout, result.Stdout)
		}
		if result.Stderr != "" {
			fmt.Fprint(env.Stderr, result.Stderr)
		}
		if result.Current() {
			if !env.JSON() {
				env.Printf("%s: current\n", mod.Slug)
			}
			continue
		}
		stale = true
		if env.JSON() {
			continue
		}
		action := "would update"
		if env.Apply {
			action = "updated"
		}
		env.Printf("%s: %s %d file(s)\n", mod.Slug, action, len(paths))
		for _, path := range paths {
			env.Printf("  %s\n", path)
		}
	}

	if env.JSON() {
		if err := jsonout.Write(env.Stdout, reports); err != nil {
			return 1, err
		}
	}
	if failed || (!env.Apply && stale) {
		return 1, nil
	}
	return 0, nil
}

func runModSources(env *Env) (int, error) {
	set := flagSet("mod sources", env)
	slugs, err := parse(set, env.Args)
	if err != nil {
		return 2, nil
	}
	mods, err := generatorMods(env, slugs)
	if err != nil {
		return 1, err
	}

	failed := false
	reports := make([]any, 0, len(mods))
	for _, mod := range mods {
		sources, err := env.Workspace.ResolveSources(mod.Manifest, env.Config, true)
		var content string
		if err == nil {
			if env.Apply {
				content, err = generate.WriteSourceLocks(mod, sources)
			} else {
				content, err = generate.RenderSourceLocks(sources)
			}
		}
		if err != nil {
			failed = true
			if env.JSON() {
				reports = append(reports, map[string]any{
					"slug": mod.Slug, "status": "error", "error": err.Error(),
				})
				continue
			}
			fmt.Fprintf(env.Stderr, "%s: error: %v\n", mod.Slug, err)
			continue
		}

		if env.JSON() {
			var lock any
			if err := json.Unmarshal([]byte(content), &lock); err != nil {
				return 1, err
			}
			status := "preview"
			if env.Apply {
				status = "updated"
			}
			reports = append(reports, map[string]any{
				"slug": mod.Slug, "status": status, "lock": lock,
			})
			continue
		}
		if env.Apply {
			env.Printf("%s: source locks updated\n", mod.Slug)
			continue
		}
		env.Printf("%s: source-lock preview\n", mod.Slug)
		fmt.Fprint(env.Stdout, content)
	}

	if env.JSON() {
		if err := jsonout.Write(env.Stdout, reports); err != nil {
			return 1, err
		}
	}
	if failed {
		return 1, nil
	}
	return 0, nil
}

func runModAudit(env *Env) (int, error) {
	set := flagSet("mod audit", env)
	slugs, err := parse(set, env.Args)
	if err != nil {
		return 2, nil
	}

	var mods []*workspace.Mod
	if len(slugs) > 0 {
		for _, slug := range slugs {
			mod, err := env.Workspace.Mod(slug)
			if err != nil {
				return 1, err
			}
			mods = append(mods, mod)
		}
	} else if mods, err = env.Workspace.Mods(); err != nil {
		return 1, err
	}

	invalid := false
	reports := make([]any, 0, len(mods))
	for _, mod := range mods {
		message := "descriptor valid"
		valid := true
		if !fsutil.IsFile(mod.DescriptorPath) {
			valid = false
			message = "missing " + env.Workspace.Settings.Descriptor
		} else if descriptor, err := pdx.Load(mod.DescriptorPath); err != nil {
			valid = false
			message = err.Error()
		} else if err := pdx.ValidateNative(descriptor); err != nil {
			valid = false
			message = err.Error()
		}
		if !valid {
			invalid = true
		}
		if env.JSON() {
			reports = append(reports, map[string]any{
				"slug": mod.Slug, "valid": valid, "message": message,
			})
			continue
		}
		env.Printf("%s: %s\n", mod.Slug, message)
	}

	if env.JSON() {
		if err := jsonout.Write(env.Stdout, reports); err != nil {
			return 1, err
		}
	}
	if invalid {
		return 1, nil
	}
	return 0, nil
}

func runModValidate(env *Env) (int, error) {
	set := flagSet("mod validate", env)
	slugs, err := parse(set, env.Args)
	if err != nil {
		return 2, nil
	}

	var mods []*workspace.Mod
	if len(slugs) > 0 {
		for _, slug := range slugs {
			mod, err := env.Workspace.Mod(slug)
			if err != nil {
				return 1, err
			}
			mods = append(mods, mod)
		}
	} else if mods, err = env.Workspace.Mods(); err != nil {
		return 1, err
	}

	failed := false
	reports := make([]any, 0, len(mods))
	for _, mod := range mods {
		result := validate.Mod(env.Workspace, mod, env.Config)
		if !result.OK() {
			failed = true
		}
		if env.JSON() {
			reports = append(reports, result.ToMap())
			continue
		}
		env.Printf("%s: %s\n", result.Slug, result.Status())
		for _, check := range result.Checks {
			env.Printf("  %s: %s - %s\n", check.Step, check.Status, check.Message)
			if len(check.Command) > 0 {
				env.Printf("    command: %s\n", strings.Join(check.Command, " "))
			}
			for _, detail := range check.Details {
				env.Printf("    %s\n", detail)
			}
			for _, stream := range []struct {
				label string
				text  string
			}{{"stdout", check.Stdout}, {"stderr", check.Stderr}} {
				if stream.text == "" {
					continue
				}
				env.Printf("    %s:\n", stream.label)
				for _, line := range strings.Split(strings.TrimRight(stream.text, "\n \t\r"), "\n") {
					env.Printf("      %s\n", line)
				}
			}
		}
	}

	if env.JSON() {
		if err := jsonout.Write(env.Stdout, reports); err != nil {
			return 1, err
		}
	}
	if failed {
		return 1, nil
	}
	return 0, nil
}
