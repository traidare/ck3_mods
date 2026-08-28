# legacy_of_valyria_bridge_runtime_rebase — module state

Generated startup-script rebase for **Legacy of Valyria - AGOT 0.5.1**
(`3719888822`), the LoV AGOT bridge, onto the current AGOT source. Load
position: immediately after that bridge and before Essos Expanded.

## Ownership

This module owns only `common/on_action/agot_on_actions/agot_game_start.txt`.
Pirate succession laws and title history remain owned by the bridge and later
playset integration layers.

The bridge ships a whole-file copy of AGOT's game-start script, so it silently
reverts every AGOT startup change made since that copy was taken. The generated
file therefore starts from AGOT's complete current script and reapplies only the
bridge's intentional additions: the LoV dummy-ruler rehome hook, the Mantaryan
trait hook, and the estate innovation and slot guards. AGOT's Narrow Sea gate,
Lorath setup, confederations, scenarios, sailing setup, and every other startup
behaviour come back with it.

The supersiren distributor selects each county capital, requires a valid culture
and faith, and kills the source ruler only after all counties transfer.

The bridge's game-start estate-owner lists now match AGOT's exactly — it drives
noble family estates from its own `title_on_actions.txt` instead — so no owner
list is ported. The generator compares both lists per tier and fails if the
bridge starts widening them at game start again, which would otherwise be
dropped here without a trace.

## Generation

```sh
ck3mm mod generate legacy_of_valyria_bridge_runtime_rebase
ck3mm mod generate legacy_of_valyria_bridge_runtime_rebase --apply
```

The generator pins both game-start inputs by source hash and applies every
splice through counted replacements, so an upstream edit to either file fails
generation instead of producing a half-rebased script.

## Re-audit

Re-audit when Workshop `2962333032` or `3719888822` changes the pinned startup
file, or when the intended LoV hooks change.
