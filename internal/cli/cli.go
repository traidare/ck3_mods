// Package cli is the command tree. Commands share one set of global flags and
// one output-format choice, so every subcommand behaves the same way.
package cli

import (
	"flag"
	"fmt"
	"io"
	"sort"
	"strings"

	"codeberg.org/traidare/ck3_mods/internal/config"
	"codeberg.org/traidare/ck3_mods/internal/workspace"
)

// Version is the tool's reported version.
const Version = "0.2.0"

// Env carries everything a command needs to run and everywhere it may write.
// Tests and the real main share this, so nothing reaches for globals.
type Env struct {
	Stdout    io.Writer
	Stderr    io.Writer
	Args      []string
	Workspace *workspace.Workspace
	Config    config.Config

	// Format is "text" or "json".
	Format string
	// Apply turns a preview into a write. Every mutating command honours it.
	Apply bool
}

// JSON reports whether the caller asked for machine-readable output.
func (e *Env) JSON() bool { return e.Format == "json" }

// Printf writes to the command's stdout.
func (e *Env) Printf(format string, arguments ...any) {
	fmt.Fprintf(e.Stdout, format, arguments...)
}

// Command is one node in the command tree. A node either runs (Run) or
// dispatches to children (Children), never both.
type Command struct {
	Name     string
	Summary  string
	Usage    string
	Run      func(env *Env) (int, error)
	Children []*Command
}

func (c *Command) child(name string) *Command {
	for _, child := range c.Children {
		if child.Name == name {
			return child
		}
	}
	return nil
}

// globalFlags are accepted before, between, and after subcommand names, so
// `ck3mm --format json conflicts` and `ck3mm conflicts --format json` agree.
type globalFlags struct {
	root        string
	gameDir     string
	paradoxDir  string
	workshopDir string
	playset     string
	format      string
	apply       bool
	version     bool
	set         map[string]bool
}

func newGlobalFlags() *globalFlags {
	return &globalFlags{format: "text", set: map[string]bool{}}
}

// extract pulls the global flags out of an argument list, leaving the
// command-specific ones behind.
func (g *globalFlags) extract(arguments []string) ([]string, error) {
	stringTargets := map[string]*string{
		"--root":         &g.root,
		"--game-dir":     &g.gameDir,
		"--paradox-dir":  &g.paradoxDir,
		"--workshop-dir": &g.workshopDir,
		"--playset":      &g.playset,
		"--format":       &g.format,
	}

	var remaining []string
	for index := 0; index < len(arguments); index++ {
		argument := arguments[index]
		if argument == "--" {
			remaining = append(remaining, arguments[index:]...)
			break
		}
		name, inlineValue, hasInline := strings.Cut(argument, "=")
		target, isGlobal := stringTargets[name]
		switch {
		case isGlobal:
			if hasInline {
				*target = inlineValue
			} else {
				index++
				if index >= len(arguments) {
					return nil, fmt.Errorf("%s requires a value", name)
				}
				*target = arguments[index]
			}
			g.set[name] = true
		case name == "--apply":
			g.apply = true
		case name == "--version":
			g.version = true
		default:
			remaining = append(remaining, argument)
		}
	}

	if g.format != "text" && g.format != "json" {
		return nil, fmt.Errorf("unknown --format %q; choose text or json", g.format)
	}
	return remaining, nil
}

func (g *globalFlags) overrides() map[string]string {
	overrides := map[string]string{}
	pairs := map[string]string{
		"--game-dir":     config.GameDir,
		"--paradox-dir":  config.ParadoxDir,
		"--workshop-dir": config.WorkshopDir,
		"--playset":      config.PlaysetName,
	}
	for flagName, variable := range pairs {
		if g.set[flagName] {
			switch variable {
			case config.GameDir:
				overrides[variable] = g.gameDir
			case config.ParadoxDir:
				overrides[variable] = g.paradoxDir
			case config.WorkshopDir:
				overrides[variable] = g.workshopDir
			case config.PlaysetName:
				overrides[variable] = g.playset
			}
		}
	}
	return overrides
}

// Root builds the command tree.
func Root() *Command {
	return &Command{
		Name:    "ck3mm",
		Summary: "Manage this CK3 modding workspace",
		Children: []*Command{
			configCommand(),
			modCommand(),
			playsetCommand(),
			conflictsCommand(),
			refsCommand(),
			culturesCommand(),
			traditionsCommand(),
			faithsCommand(),
		},
	}
}

// Main runs the CLI and returns the process exit code.
func Main(arguments []string, stdout, stderr io.Writer) int {
	globals := newGlobalFlags()
	remaining, err := globals.extract(arguments)
	if err != nil {
		fmt.Fprintf(stderr, "error: %v\n", err)
		return 2
	}
	if globals.version {
		fmt.Fprintf(stdout, "ck3mm %s\n", Version)
		return 0
	}

	root := Root()
	command := root
	for len(remaining) > 0 && len(command.Children) > 0 {
		child := command.child(remaining[0])
		if child == nil {
			break
		}
		command = child
		remaining = remaining[1:]
	}

	if command.Run == nil {
		if len(remaining) > 0 {
			fmt.Fprintf(stderr, "error: unknown command %q\n\n", remaining[0])
			writeHelp(stderr, command)
			return 2
		}
		writeHelp(stdout, command)
		return 2
	}

	start := globals.root
	if start == "" {
		start = "."
	}
	space, err := workspace.Open(start)
	if err != nil {
		fmt.Fprintf(stderr, "error: %v\n", err)
		return 2
	}
	settings, err := config.Load(space.Root, config.Options{Overrides: globals.overrides()})
	if err != nil {
		fmt.Fprintf(stderr, "error: %v\n", err)
		return 2
	}

	env := &Env{
		Stdout:    stdout,
		Stderr:    stderr,
		Args:      remaining,
		Workspace: space,
		Config:    settings,
		Format:    globals.format,
		Apply:     globals.apply,
	}
	code, err := command.Run(env)
	if err != nil {
		fmt.Fprintf(stderr, "error: %v\n", err)
		if code == 0 {
			return 1
		}
	}
	return code
}

func writeHelp(writer io.Writer, command *Command) {
	fmt.Fprintf(writer, "%s - %s\n\n", command.Name, command.Summary)
	if command.Usage != "" {
		fmt.Fprintf(writer, "Usage: %s\n\n", command.Usage)
	}
	if len(command.Children) > 0 {
		fmt.Fprintln(writer, "Commands:")
		names := make([]string, 0, len(command.Children))
		width := 0
		for _, child := range command.Children {
			names = append(names, child.Name)
			if len(child.Name) > width {
				width = len(child.Name)
			}
		}
		sort.Strings(names)
		for _, name := range names {
			child := command.child(name)
			fmt.Fprintf(writer, "  %-*s  %s\n", width, child.Name, child.Summary)
		}
		fmt.Fprintln(writer)
	}
	fmt.Fprint(writer, `Global flags:
  --root DIR          workspace root (default: search upward for ck3mm.toml)
  --game-dir DIR      override CK3_GAME_DIR
  --paradox-dir DIR   override CK3_PARADOX_DIR
  --workshop-dir DIR  override CK3_WORKSHOP_DIR
  --playset NAME      override CK3_PLAYSET_NAME
  --format text|json  output format (default: text)
  --apply             perform the previewed changes
  --version           print the version and exit
`)
}

// flagSet builds a command-local flag set that reports errors instead of
// exiting, so Main stays in control of the exit code.
func flagSet(name string, env *Env) *flag.FlagSet {
	set := flag.NewFlagSet(name, flag.ContinueOnError)
	set.SetOutput(env.Stderr)
	return set
}

// parse accepts flags and positional arguments in any order and returns the
// positionals. Go's flag package stops at the first non-flag argument, which
// would make `conflicts AGOT --involving X` silently drop the filter.
func parse(set *flag.FlagSet, arguments []string) ([]string, error) {
	var flags, positionals []string
	for index := 0; index < len(arguments); index++ {
		argument := arguments[index]
		if argument == "--" {
			positionals = append(positionals, arguments[index+1:]...)
			break
		}
		if !strings.HasPrefix(argument, "-") || argument == "-" {
			positionals = append(positionals, argument)
			continue
		}

		flags = append(flags, argument)
		name := strings.TrimLeft(argument, "-")
		if strings.Contains(name, "=") {
			continue
		}
		entry := set.Lookup(name)
		if entry == nil {
			// Let the flag package produce the unknown-flag error.
			continue
		}
		if boolFlag, ok := entry.Value.(interface{ IsBoolFlag() bool }); ok && boolFlag.IsBoolFlag() {
			continue
		}
		if index+1 < len(arguments) {
			index++
			flags = append(flags, arguments[index])
		}
	}
	if err := set.Parse(flags); err != nil {
		return nil, err
	}
	return append(positionals, set.Args()...), nil
}

// stringList collects a repeatable string flag.
type stringList []string

func (s *stringList) String() string { return strings.Join(*s, ",") }

func (s *stringList) Set(value string) error {
	*s = append(*s, value)
	return nil
}
