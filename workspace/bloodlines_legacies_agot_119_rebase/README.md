# bloodlines_legacies_agot_119_rebase — module state

Compatibility rebase for **Bloodlines: Legacies of AGOT** (`3522779004`) against
current **A Game of Thrones 0.5.0** (`2962333032`) on CK3 1.19. Load position:
immediately after Bloodlines.

## Ownership

Generated same-path overrides of the Bloodlines files it repairs, plus ten
re-encoded textures. It owns nothing AGOT provides.

## Repairs and evidence

- Rebases Bloodlines' stale `execute_prisoner_interaction` override onto current
  AGOT while retaining both AGOT's and Bloodlines' Bolton flaying perks.
- Guards all 73 game-start special-building additions so each one skips a barony
  that already carries a special building from the expanded map stack and a
  barony that has no holding at all. Under the module's default game rules this
  is the only Bloodlines work that runs at game start, and two targets (`1935`
  Harrenton and `7265` Misty Isle) currently resolve to holdingless baronies, so
  the unguarded effect reached a holding that does not exist.
- Repairs the malformed Riverlands and child-birth script blocks. In the
  malformed Riverlands event, events `.0009` through `.0015` do not load while
  the yearly pulse continues to call them.
- Migrates removed titles, traits, hook types, character templates, decision
  fields, effects, backgrounds, and geographical-region ids.
- Removes explicit durations from CK3 1.19's self-decaying opinion modifiers.
- Restores missing Bloodlines opinion-modifier definitions and values.
- Repairs invalid county/character modifier scope usage.
- Makes the scripted great-project sound reference self-contained.
- Re-encodes ten invalid block-compressed DDS files without resizing their
  artwork.

## Generation

Generated files come from the current Workshop sources:

```bash
ck3mm mod generate bloodlines_legacies_agot_119_rebase
ck3mm mod generate bloodlines_legacies_agot_119_rebase --apply
```

The `mod.toml` manifest declares the parents, staged entrypoint, and owned
outputs.

## Re-audit

The generator asserts expected replacement counts. Re-run it and re-audit this
module whenever Bloodlines or AGOT updates.
