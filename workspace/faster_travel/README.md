# faster_travel — module state

A standalone quality-of-life tweak, independent of the AGOT playset. Load
position: anywhere after any mod that also edits `NTravel` defines.

## Ownership

One hand-authored file, `common/defines/sfts_defines.txt`, redefining four
members of the `NTravel` block:

| define                    | value | CK3 default                     |
| ------------------------- | ----- | ------------------------------- |
| `BASE_TRAVEL_SPEED_LAND`  | 5     | 5 (unchanged, kept for context) |
| `BASE_TRAVEL_SPEED_WATER` | 12    | 7                               |
| `TRAVEL_EMBARK_COST`      | 12    | 15                              |
| `TRAVEL_DISEMBARK_COST`   | 4     | 5                               |

`common/defines` resolves per define, LIOS by ASCIIbetical filename, so the
`sfts_` prefix wins over CK3's `00_defines.txt` regardless of playset position.
Any mod shipping a later-sorting defines file that also sets these members wins
instead.

## Generation

None. This module has no `mod.toml` and no generator; the payload is
hand-authored.

## Re-audit

**Manual.** The re-audit trigger is a CK3 patch that changes the `NTravel`
defaults or renames these members — not a Workshop update. Recheck
`$CK3_GAME_DIR/game/common/defines/00_defines.txt` after each game version bump
and confirm the four names still exist and the recorded defaults still match.
