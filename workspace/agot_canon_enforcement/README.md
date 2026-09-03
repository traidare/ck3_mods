# agot_canon_enforcement — module state

Protects the characters a canon storyline depends on from unchosen deaths, and
replays the canon rider-dragon bonds AGOT's own dispatch cannot reach. Parents:
A Game of Thrones (`2962333032`) and AGOT: Canon Children EZ Mode
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

| output                                                               | defines or redefines                               |
| -------------------------------------------------------------------- | -------------------------------------------------- |
| `common/scripted_triggers/agot_ce_triggers.txt`                      | the three population triggers, and the taming gate |
| `common/game_rules/agot_ce_game_rules.txt`                           | seven rules in the `agot_ce` category              |
| `common/modifiers/agot_ce_modifiers.txt`                             | `agot_ce_protection_modifier`                      |
| `common/scripted_effects/agot_ce_effects.txt`                        | apply and clear effects                            |
| `common/scripted_effects/agot_ce_canon_dragon_effects.txt`           | `agot_ce_canon_dragon_bond_effect`                 |
| `common/on_action/agot_ce_on_actions.txt`                            | game-start sweeps and yearly maintenance           |
| `common/character_interactions/agot_ce_interactions.txt`             | manual marking, other characters                   |
| `common/decisions/agot_ce_decisions.txt`                             | manual marking, self                               |
| `common/scripted_triggers/agot_ce_canon_dragon_triggers.txt`         | `agot_ce_canon_taming_due_trigger`                 |
| `events/agot_ce_canon_dragon_taming_events.txt`                      | `agot_ce_canon_dragon.0001`                        |
| `common/combat_phase_events/zzzz_agot_ce_commander_phase_events.txt` | `commander_killed`                                 |
| `common/scripted_effects/zzzz_agot_ce_natural_disaster_effects.txt`  | `natural_disaster_death_damage_roll_effect`        |
| `common/scripted_effects/zzzz_agot_ce_tournament_effects.txt`        | `tournament_accidental_death_effect`               |

The three redefinitions are generated: the generator extracts the current parent
definition, injects the guard at a pinned anchor, and emits the result, so an
unrelated upstream edit to those definitions flows through. The last two
generated outputs, the taming trigger and the taming event, are derived from
AGOT's dragon history instead and carry keys of this module's own.

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

## Canon dragon tamings

AGOT's only static record of who rode which dragon is the set of dated
`agot_tame_dragon` entries in `history/characters/00_agot_char_dragons.txt`. A
record dated before the bookmark is replayed at game start. A record dated after
it is never replayed, so the bond depends entirely on AGOT's runtime dispatch:
`on_10th_birthday_tame_canon_dragon`, and a game-start branch gated on
`age >= 10`. Both schedule `dragon_taming_events.9000`, and neither retries, so
a rider that passes through neither gate never bonds at all.

The generator reads every record and emits two additive outputs: an OR over each
record's runtime identity and its recorded day, and a hidden dispatcher whose
branches call `agot_ce_canon_dragon_bond_effect` with the recorded dragon. Rider
identity is `has_character_flag = is_<ID>` where some AGOT effect adds that
flag, and a direct `character:<ID>` reference where none does. Dragon identity
is AGOT's own `is_character_dragon_<token>` trigger, resolved by finding the
trigger whose body references `character:<dragon>`, so a canon dragon recreated
under a different character is still matched.

`agot_ce_canon_taming_pending_trigger` gates the whole path. It requires the
rule and AGOT's own Canon Dragons rule, restricts the fallback to AI characters,
and skips a rider who already has a dragon, is `dragonwidowed`, holds
`attempting_canon_bond`, or is running a `bond_with_dragon_scheme`. The last two
mean AGOT keeps first refusal: this module never ends a scheme and never takes a
dragon from an existing rider. The bond effect reuses AGOT's own availability
guards from event 9000 — the living dragon list, the no-rider requirement, and
the dragonpit ban.

Enforcement runs on the same one-day game-start sweep and the same yearly pulse
as protection, so a record takes effect within a year of its recorded date. That
is the granularity AGOT's own 365-730 day dispatch delay already has.

`artifacts/canon_dragon_tamings/taming_audit.csv` reports every record with the
identities the script uses and why AGOT's dispatch does or does not reach it:
`no_canon_flag`, `created_after_game_start`, `unpaired`,
`before_tenth_birthday`, or `birthday_dispatch`.

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

The canon dragon outputs pin the AGOT behaviour they are defined against.
Generation fails when `agot_tame_dragon` or
`agot_can_tame_or_bond_or_etc_with_pitted_dragons` loses a parameter the emitted
script passes, when `dragon_taming_events.9000` stops naming the tame effect,
the living dragon list or the rider-dragon pair trigger, when
`on_10th_birthday_tame_canon_dragon` stops dispatching event 9000, when the game
start dispatch stops gating on `age >= 10`, or when
`agot_dragons_on_start_effect` stops filling the living dragon list.

It also fails on the record set itself: a rider that gains a second record, a
recorded dragon with no `is_character_dragon_*` trigger, an `agot_tame_dragon`
call outside a dated block, and any change to the two pinned rider sets —
`EXPECTED_FLAGLESS_RIDERS`, whose canon flag no effect adds, and
`EXPECTED_DYNAMIC_RIDERS`, whom AGOT creates after game start above age ten.
Both sets are the fallback's reason for existing, so a change to either is a
re-audit, not a silent regeneration.

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

For the canon dragon outputs, re-read the audit whenever either pinned rider set
changes, and whenever another playset mod begins defining
`dragon_taming_events.9000`, `on_10th_birthday_tame_canon_dragon`, or AGOT's
`on_10th_birthday` dispatch — `agot_full_playset_compatch` already restores that
dispatch beside New Personality Events, and this module assumes it is in place.
