# faster_travel — module state

A standalone quality-of-life tweak, independent of the AGOT playset, tuned
relative to base CK3.

**It must not be combined with a parent that sets these four members.** Because
`common/defines` resolves per define by ASCIIbetical filename, this module wins
over an earlier-sorting parent rather than layering on it, so it replaces that
parent's values with base CK3's. A Game of Thrones sets
`BASE_TRAVEL_SPEED_LAND = 15` and `BASE_TRAVEL_SPEED_WATER = 30`; with this
module enabled they become 5 and 12, which is three times slower on land and two
and a half times slower at sea than AGOT intends. This is an exclusion, not a
load-order hint: no position fixes it.

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
hand-authored. It is also the only module without a `ck3-tiger.conf`, which is
deliberate: it is validated against bare vanilla, because bare vanilla is what
its values are relative to.

## Re-audit

**Manual**, on two triggers.

1. A CK3 patch that changes the `NTravel` defaults or renames these members.
   Recheck `$CK3_GAME_DIR/game/common/defines/00_defines.txt` after each game
   version bump and confirm the four names still exist and the recorded defaults
   still match.
2. A playset gaining a mod that sets any of the four members, which makes this
   module the wrong thing to enable rather than merely stale. Because
   `common/defines` resolves per define rather than per file, a mod can override
   these four from its own filename without ever conflicting on a path, so the
   default conflict view will not show it. Enumerate the providers with
   `ck3mm conflicts <playset> --all-files --include-prefix common/defines` and
   search those files for the four names.
