# Bloodlines: Legacies of AGOT - CK3 1.19 Runtime Rebase

Compatibility rebase for **Bloodlines: Legacies of AGOT** on current **A Game of
Thrones** and CK3 1.19.

## Requirements and load order

1. A Game of Thrones
2. Bloodlines: Legacies of AGOT
3. This rebase

## What it repairs

- Rebases Bloodlines' stale execute-prisoner interaction onto current AGOT,
  keeping both AGOT's and Bloodlines' Bolton flaying perks.
- Guards each of the 57 game-start special-building additions, so it skips a
  barony that already has a special building or has no holding.
- Repairs malformed Riverlands and child-birth blocks that stopped later events
  in the same file from loading.
- Migrates removed traits, title ids, event backgrounds, portrait scopes, and
  animation names to their current equivalents.
- Removes explicit durations from self-decaying opinions and restores missing
  Bloodlines opinion-modifier definitions and values.
- Repairs invalid county and character modifier scope usage.
- Makes the scripted great-project sound reference self-contained.
- Re-encodes eleven invalid compressed textures without resizing their artwork.

## Crownlands repairs

- Restores 55 Crownlands modifier effects that CK3 1.19 discarded, so the road
  tolls, scheme, construction, tax, and marriage bonuses actually apply.
- Makes ten Crownlands event rewards grant the dynasty prestige they promise.
- Restores the intended suspicious pose on twelve Crownlands event portraits.
- Applies four Velaryon Driftmark and High Tide modifiers to the ruler instead
  of failing to apply at all.
- Opens the House Darklyn restoration events to Darke, Darkwood, and Dargood
  rulers, and restores the bought-claim option's cost and white-cloak prowess
  reward.
- Repairs the Celtigar artifact creation, which produced no artifact.
