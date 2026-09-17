# agot_inner_circle_revoke_cost — module state

Delivers the free-dismissal half of the `fp2_coterie_legacy_1` ("Inner Circle")
dynasty perk, which neither the base game nor **A Game of Thrones**
(`2962333032`) implements for most court positions. Parent: AGOT. Load position:
after AGOT and after any other mod that redefines the three shared court
position prestige revoke costs. No enabled mod in the AGOT playset does, so this
module is the last writer for those keys.

## Why the perk is broken upstream

`LEGACY_DYNASTY_NO_SALARY_FREE_FIRING_COURT_POSITION_FROM_DYNASTY` promises that
house members "can be fired without losing prestige". The salary half of that
promise is one shared trigger, `court_position_inner_circle_salary_trigger`, and
works. The dismissal half is not a mechanic: `revoke_cost` is evaluated with
`root` set to the liege and no employee scope
(`common/court_positions/types/_court_positions.info`, and vanilla's own
`# root is the liege, no other scopes are passed here!`), so each position has
to hand-roll `employs_court_position` plus
`any_court_position_holder = { type = <self> … }` inside its own `revoke_cost`.

Vanilla writes that check only into `00_camp_officers.txt`. AGOT writes it into
its own `00_agot_court_positions.txt` and
`00_agot_court_positions_crownlands.txt`, but its copies of the vanilla type
files inherit vanilla's omission. Resolved through the playset's load order, 51
employable entries charge prestige with no Inner Circle check, across
`00_court_positions.txt`, `00_mpo_court_positions.txt`,
`00_celestial_court_positions.txt`, `00_mandala_court_positions.txt`,
`00_admin_court_position.txt`, AGOT's own files and Immersive Mercs & Raiders'
`zz_gptmerc_court_positions.txt`.

## Ownership

`common/script_values/zz_agot_inner_circle_revoke_cost.txt` redefines `minor_`,
`medium_` and `major_court_position_prestige_revoke_cost` by key. Every one of
those 51 entries reaches its cost through one of those three values, so three
keys stand in for 51 whole-entry copies that would otherwise freeze AGOT's
aptitudes, modifiers and validity rules at a pinned version. The keys are
referenced only from `revoke_cost` blocks under `common/court_positions/types/`,
so the override reaches nothing else. `medium_` is carried although nothing
references it today, so a position that later adopts it is covered.

## Behavior and its approximation

Each value gains one clause: when the scoped character's dynasty has
`fp2_coterie_legacy_1` and `any_court_position_holder` finds a holder whose
house is the scoped character's own, the cost multiplies to zero, described
through AGOT's existing `inner_circle_salary_mod` key so the breakdown names the
perk.

A shared script value cannot see which holder is being dismissed, so the gate is
"a house member holds a court position", not "the holder being dismissed is a
house member". While a house member serves, dismissing a holder outside the
house is also free. That approximation is the module's rule, stated as such in
the mod's player-facing description, and it is the reason the module is three
keys instead of 17,700 lines of entry copies.

The generator pins each value to its exact AGOT body — `value = 25 / 75 / 200`
plus the `temporary_court_position_cost_removal` clause — and fails by key name
if AGOT changes any of them, so a rebalanced cost cannot be silently overwritten
with the old one.

## Re-audit trigger

```sh
rg -c 'fp2_coterie_legacy_1' "$CK3_WORKSHOP_DIR/2962333032/common/court_positions/types/"*.txt
```

Only `00_agot_court_positions.txt` and `00_agot_court_positions_crownlands.txt`
report hits. A hit in `00_court_positions.txt`, `00_mpo_court_positions.txt`,
`00_celestial_court_positions.txt`, `00_mandala_court_positions.txt` or
`00_admin_court_position.txt` means AGOT has implemented the check per entry,
and this module needs re-evaluating: both layers would then zero the same cost,
and AGOT's is the precise one.

## Out of reach

Twenty entries write a literal prestige cost instead of the shared values, so no
script value override reaches them: the 19 Night's Watch keeper seats and
`nw_septon` in `01_agot_nights_watch_positions.txt` (flat `200`), and
`bloodrider_court_position` in `00_agot_court_positions.txt` (`15000`, a cost
that size reads as a deliberate lock). Covering any of them means a whole-entry
override.

Separately, AGOT's `septa_court_position` carries the Inner Circle check but
reads `septon_court_position` in all three of its own uses — `revoke_cost`,
salary gold and salary prestige. This module's override covers that entry's
revoke cost anyway, since it uses `major_court_position_prestige_revoke_cost`;
the salary half stays broken, so a house-member Septa keeps drawing a salary
unless a house-member Septon is employed as well. Fixing it means a whole-entry
override of `septa_court_position`, and it belongs upstream.
