package cli

import "testing"

// subcommandNames returns a command's children in declaration order.
func subcommandNames(command *Command) []string {
	names := make([]string, 0, len(command.Children))
	for _, child := range command.Children {
		names = append(names, child.Name)
	}
	return names
}

func assertSubcommands(t *testing.T, command *Command, want []string) {
	t.Helper()
	got := subcommandNames(command)
	if len(got) != len(want) {
		t.Fatalf("%s has %v, want %v", command.Name, got, want)
	}
	for index, name := range want {
		if got[index] != name {
			t.Errorf("%s subcommand %d = %q, want %q", command.Name, index, got[index], name)
		}
	}
}

func TestInspectionCommandsExposeOnlySupportedSubcommands(t *testing.T) {
	assertSubcommands(t, culturesCommand(), []string{"list", "show"})
	assertSubcommands(t, traditionsCommand(), []string{"list", "show"})
	assertSubcommands(t, faithsCommand(), []string{"list", "show", "holy-sites"})
}

func TestRootRegistersTheInspectionCommands(t *testing.T) {
	root := Root()
	for _, name := range []string{"cultures", "traditions", "faiths"} {
		if root.child(name) == nil {
			t.Errorf("root does not register %q", name)
		}
	}
	// Traditions moved to their own group, so cultures must no longer claim them.
	if culturesCommand().child("traditions") != nil {
		t.Error("cultures still exposes a traditions subcommand")
	}
}
