# Legacy of Valyria RC71 - CK3 1.19 Runtime Rebase

Generated startup-script rebase for **Legacy of Valyria - AGOT Temporary
Compatch RC71** (`3719888822`) on the current AGOT source. Load it immediately
after that compatch and before Essos Expanded.

## Ownership

This module owns only `common/on_action/agot_on_actions/agot_game_start.txt`.
Pirate succession laws and title history remain owned by the LoV compatch and
later playset integration layers.

The generated file starts from AGOT's complete startup script and reapplies the
LoV dummy-ruler rehome hook, Mantaryan traits, estate innovation and slot
guards, and the 39 LoV estate dynasties. It retains AGOT's Narrow Sea gate,
Lorath setup, confederations, scenarios, sailing setup, and other unrelated
startup behavior.

The supersiren distributor selects each county capital, requires a valid culture
and faith, and kills the source ruler only after all counties transfer. The
generator pins the AGOT and RC71 startup inputs and the AGOT pirate-domicile
block with source hashes and counted replacements.

## Re-audit

Re-audit when Workshop `2962333032` or `3719888822` changes the pinned startup
file or when the intended LoV hooks change. Regenerate with:

```sh
ck3mm mod generate legacy_of_valyria_039_runtime_rebase
ck3mm mod generate legacy_of_valyria_039_runtime_rebase --apply
```
