# Bloodlines: Legacies of AGOT - CK3 1.19 Runtime Rebase

Compatibility rebase for **Bloodlines: Legacies of AGOT** on current **A Game of
Thrones** and CK3 1.19.

## Requirements and load order

1. A Game of Thrones
2. Bloodlines: Legacies of AGOT
3. This rebase

Load immediately after Bloodlines.

## What it repairs

- Rebases Bloodlines' stale execute-prisoner interaction onto current AGOT,
  keeping both AGOT's and Bloodlines' Bolton flaying perks.
- Guards each of the 57 game-start special-building additions, so it skips a
  barony that already carries a special building from an expanded map and a
  barony that has no holding at all. On the expanded map some Bloodlines targets
  have no holding, and the unguarded effect reached a holding that does not
  exist.
- Repairs the malformed Riverlands and child-birth script blocks, where brace
  and indentation errors stopped later events in the same file from loading
  while the yearly pulse kept calling them.
- Migrates removed traits, title ids, event backgrounds, portrait scopes, and
  animation names to their current equivalents.
- Removes explicit durations from opinion modifiers that decay on their own in
  CK3 1.19.
- Restores missing Bloodlines opinion-modifier definitions and values.
- Repairs invalid county and character modifier scope usage.
- Makes the scripted great-project sound reference self-contained.
- Re-encodes ten invalid compressed textures without resizing their artwork.
