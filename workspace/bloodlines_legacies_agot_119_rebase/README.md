# bloodlines_legacies_agot_119_rebase — module state

Compatibility rebase for **Bloodlines: Legacies of AGOT** (`3522779004`) against
current **A Game of Thrones 0.5.1** (`2962333032`) on CK3 1.19. Load position:
immediately after Bloodlines.

## Ownership

Generated same-path overrides of the Bloodlines files that still carry a defect,
plus ten re-encoded textures. Files Bloodlines has corrected itself are left to
load unmodified, so this module's scope shrinks as upstream catches up. It owns
nothing AGOT provides.

## Repairs and evidence

- Rebases Bloodlines' stale `execute_prisoner_interaction` override onto current
  AGOT while retaining both AGOT's and Bloodlines' Bolton flaying perks.
- Guards each of the 57 active game-start special-building additions so it skips
  a barony that already carries a special building from the expanded map stack
  and a barony that has no holding at all. Under the module's default game rules
  this is the only Bloodlines work that runs at game start, and the expanded map
  leaves some targets holdingless, so the unguarded effect reached a holding
  that does not exist. The upstream file keeps a further sixteen assignments
  commented out; the count assertion covers only the active ones.
- Repairs the malformed child-birth and Riverlands script blocks, whose brace
  and indentation errors stop later events in the same file from loading while
  the yearly pulse continues to call them.
- Migrates removed traits, title ids, event backgrounds, portrait scopes, and
  animation names.
- Removes explicit durations from CK3 1.19's self-decaying opinion modifiers.
- Restores missing Bloodlines opinion-modifier definitions and values.
- Repairs invalid county/character modifier scope usage.
- Makes the scripted great-project sound reference self-contained.
- Re-encodes ten invalid block-compressed DDS files without resizing their
  artwork.

Two Bloodlines defects are carried rather than repaired, since fixing either
means authoring content instead of rebasing it: three `*_by_trident_lord_bla`
opinion modifiers are declared in `common/modifiers/` but used where CK3 expects
`common/opinion_modifiers/`, and `agot_riverlands_events_bla.txt` calls the
unknown effect `add_knight`. ck3-tiger reports both against this module because
it is the last writer of those paths.

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
