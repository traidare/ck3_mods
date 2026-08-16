# agot_longnight_submodcore_dfp_compatch — module state

Animation-only final-integration layer between AGOT, AGOT Submod Core, Seasons
of Ice and Fire, Dynamic Family Portrait, its AGOT variant, and the local
standalone `agot_the_long_night`.

## Ownership

The module owns a single animation output and nothing else. Every other overlap
between these parents is left to its existing writer.

## Generation

```sh
ck3mm mod generate agot_longnight_submodcore_dfp_compatch
ck3mm mod generate agot_longnight_submodcore_dfp_compatch --apply
```

The `mod.toml` manifest declares the parents, the staged entrypoint, and the
owned animation output.

## Re-audit

Regenerate and review the diff after any update to the declared parents, or
after a change to the local `agot_the_long_night` payload.
