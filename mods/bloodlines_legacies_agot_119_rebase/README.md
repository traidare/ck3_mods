# Bloodlines: Legacies of AGOT - CK3 1.19 Runtime Rebase

Compatibility rebase for **Bloodlines: Legacies of AGOT** (`3522779004`) and
current **A Game of Thrones 0.4.40** (`2962333032`) on CK3 1.19.

Load immediately after Bloodlines.

## What it repairs

- rebases Bloodlines' stale `execute_prisoner_interaction` override onto current
  AGOT while retaining both AGOT's and Bloodlines' Bolton flaying perks;
- prevents 73 game-start special-building additions from trying to overwrite
  special buildings already supplied by the expanded map stack;
- repairs the malformed Riverlands and child-birth script blocks;
- migrates removed titles, traits, hook types, character templates, decision
  fields, effects, backgrounds, and geographical-region ids;
- removes explicit durations from CK3 1.19's self-decaying opinion modifiers;
- restores missing Bloodlines opinion-modifier definitions and values;
- repairs invalid county/character modifier scope usage; and
- makes the scripted great-project sound reference self-contained; and
- re-encodes ten invalid block-compressed DDS files without resizing their
  artwork.

The current full-playset log directly reproduced the malformed Riverlands event:
events `.0009` through `.0015` did not load, while the yearly pulse continued to
call them. It also reproduced the stale title, hook, trait, template, modifier,
decision-field, and opinion-duration failures addressed here.

## Regeneration

Generated files come from the current Workshop sources:

```bash
ck3mm mod check bloodlines_legacies_agot_119_rebase
ck3mm mod generate bloodlines_legacies_agot_119_rebase
```

The `.ck3mm/mod.toml` manifest declares the parents, staged entrypoint, and
owned outputs. The generator asserts expected replacement counts. Re-run it and
re-audit this module whenever Bloodlines or AGOT updates.
