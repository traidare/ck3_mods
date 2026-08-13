package cli

import "testing"

func TestModCommandExposesOnlySupportedSubcommands(t *testing.T) {
	command := modCommand()
	want := []string{"list", "generate", "validate", "install"}
	if len(command.Children) != len(want) {
		t.Fatalf("got %d subcommands, want %d", len(command.Children), len(want))
	}
	for index, child := range command.Children {
		if child.Name != want[index] {
			t.Errorf("subcommand %d = %q, want %q", index, child.Name, want[index])
		}
	}
}
