# agot_canon_enforcement — module state

Protects the characters a canon storyline depends on from unchosen deaths.
Parents: A Game of Thrones (`2962333032`) and AGOT: Canon Children EZ Mode
(`3664962140`). Load position: after both parents and before
`agot_playset_runtime_fixes`, so the repair and final-compatch layers stay the
last writers. That slot is a layering convention rather than a requirement:
every payload file is either a new key or a `zzzz_` keyed redefinition, and none
shares a path with an enabled mod, so no output here is decided by load order.

## Why the module exists at all

`death` is unconditional and takes no immunity parameter, and the game has no
revive effect. The one interception hook, `on_natural_death_second_chance`,
covers health-system deaths only, which is exactly the range EZ Mode's
`canon_children_easy_mode_health_boost_modifier` already handles. Every other
death is a scripted `death = { … }`, so protection means keeping a character out
of the set an event selects from, or gating the branch that kills them.

## Population and window

`agot_ce_is_protected_trigger` reads
`has_character_modifier = canon_children_easy_mode_health_boost_modifier` or the
module's own `agot_ce_protected` flag. Keying on EZ Mode's modifier rather than
its `canon_parent` trait ties the window to that mod's own protection window —
last canon child's birth year + 5 — instead of to the character's lifetime.

Two derived triggers gate the rest, one per rule:
`agot_ce_battle_protected_trigger` for the combat redefinition,
`agot_ce_event_death_protected_trigger` for every guarded death site, here and
in the three modules listed below.

## Ownership

Additive except for three keyed redefinitions. `common/` resolves per key by
ASCIIbetical filename, so a `zzzz_` file wins the key without shadowing the
definitions its source file also carries.

| output                                                               | defines or redefines                        |
| -------------------------------------------------------------------- | ------------------------------------------- |
| `common/scripted_triggers/agot_ce_triggers.txt`                      | the three population triggers               |
| `common/game_rules/agot_ce_game_rules.txt`                           | six rules in the `agot_ce` category         |
| `common/modifiers/agot_ce_modifiers.txt`                             | `agot_ce_protection_modifier`               |
| `common/scripted_effects/agot_ce_effects.txt`                        | apply and clear effects                     |
| `common/on_action/agot_ce_on_actions.txt`                            | game-start sweep and yearly maintenance     |
| `common/character_interactions/agot_ce_interactions.txt`             | manual marking, other characters            |
| `common/decisions/agot_ce_decisions.txt`                             | manual marking, self                        |
| `common/combat_phase_events/zzzz_agot_ce_commander_phase_events.txt` | `commander_killed`                          |
| `common/scripted_effects/zzzz_agot_ce_natural_disaster_effects.txt`  | `natural_disaster_death_damage_roll_effect` |
| `common/scripted_effects/zzzz_agot_ce_tournament_effects.txt`        | `tournament_accidental_death_effect`        |

The three redefinitions are generated: the generator extracts the current parent
definition, injects the guard at a pinned anchor, and emits the result, so an
unrelated upstream edit to those definitions flows through.

## How each protection works

**Travel** is one modifier, not a set of event edits.
`chance_of_no_event = 100 − danger + travel_safety`, capped at
`100 − TRAVEL_DANGER_MINIMUM`, so `character_travel_safety = 500` pins the
danger roll at that cap and no lethal travel danger event is drawn. This holds
for travel plans the protected character owns; as a passenger in someone else's
entourage they are still selectable.

**Battle** is knight-pool exclusion. `set_knight_status = forbid` removes the
character from `knight_killed`, from the losing-side loop in
`combat_event.1001`, and from the Long Night knight phase events, so those three
need no redefinition. `agot_ce_knight_forbidden` records that this module set
the state, because a forbidden character is no longer a potential knight and the
flag is what makes the state reversible. Dragonriders are skipped: AGOT
force-knights them at every war start so the AI will use them, and dragonrider
warfare has its own casualty events. `commander_killed` is the one combat
definition that needs a guard, since the commander is not drawn from the knight
pool.

**Duels** use `mfb_duel_cooldown`. Every definer of `mfb_commander_duel_event` —
Battle Events, its AGOT patch, and Duels & Blademasters — gates `is_valid` on
that flag's absence, so holding it means the battlefield duel is never offered.
The `plot_armor` rule variant swaps in AGOT's `multi_duelist_plot_armor`, which
also makes the holder win.

**Accidents** are per-site guards, listed below.

Protection is applied by a one-day-delayed sweep on `on_game_start_after_lobby`
and refreshed on `random_yearly_everyone_pulse`, which is the pulse that reaches
unlanded courtiers. Both effects are idempotent. The knight status is read at
army raise, so a change takes effect from the next raise.

## Guarded death sites in other modules

These deaths live in event files and in one activity definition, which resolve
whole-file by exact path, so the guard belongs to whichever module owns that
path. All of them call `agot_ce_event_death_protected_trigger`.

| module                       | sites                                                                                                                                          |
| ---------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| `agot_playset_runtime_fixes` | `travel_events.4003/4007/4032`, `kraken.0100/1105`, `health.3107/3200/4105/6200/6203/6204/6207/6208`, `host_dinner_events.1002/3060/3061/3080` |
| `agot_mfa_039_rebase`        | `tournament_events.1110/1141/1151/1230/1280`                                                                                                   |
| `agot_full_playset_compatch` | the host death in both dragon hatching activities                                                                                              |

In the runtime fixes module the guards are inserted by `guard_event_deaths` in
`runtime_fixes/common.py`, which wraps every `death` in the named event and
asserts their number, so an upstream release that adds a lethal outcome fails
generation rather than leaving it unguarded. Tournament deaths inside
`show_as_tooltip` are display copies of the real ones and are not guarded.

## Not covered

- `travel_danger_events.6020`, which kills a travel plan's whole entourage.
  Nothing in it checks the victim, and it sits in a LoV event file no module
  here owns.
- Dragon hatching guests. Their death is in AGOT's hatching events file; only
  the host dies in the activity definition this repository owns.
- AGOT sailing, Night's Watch maintenance, and the AGOT- and LoV-owned travel
  events `travel_events.1003/1005/2110` and `travel_danger_events.6030`. The
  travel-safety modifier already keeps the travel family from being drawn for
  plan owners.
- Murder, execution, poisoning, sacrifice, witch-burning and war deaths, by
  design.

## Source assertions

Generation fails when a marker this module reads disappears:
`canon_children_easy_mode_health_boost_modifier` in EZ Mode's modifier file, and
the `mfb_duel_cooldown` gate in all three definers of
`mfb_commander_duel_event`.

## Generation and validation

```sh
ck3mm mod generate agot_canon_enforcement
ck3mm mod generate agot_canon_enforcement --apply
ck3mm mod validate agot_canon_enforcement
```

ck3-tiger reports three warnings inside the generated `commander_killed`: a
value overwrite in the prowess factor, a `crown_theft_battle_effect` scope
expectation, and an `else_if` without `limit`. All three are AGOT's own code,
carried through verbatim, and are not repaired here.

## Re-audit

Recompare after every update to `2962333032` and `3664962140`, and whenever
another playset mod begins defining `commander_killed`,
`natural_disaster_death_damage_roll_effect`,
`tournament_accidental_death_effect`, or a file in `common/combat_phase_events`
or `common/scripted_effects` that sorts after `zzzz_`.
