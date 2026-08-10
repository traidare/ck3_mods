// Command ck3mm manages this CK3 modding workspace.
package main

import (
	"os"

	"codeberg.org/traidare/ck3_mods/internal/cli"
)

func main() {
	os.Exit(cli.Main(os.Args[1:], os.Stdout, os.Stderr))
}
