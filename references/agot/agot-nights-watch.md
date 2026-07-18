# AGOT: Night's Watch

## Overview

The Night's Watch is one of the most complex custom systems in AGOT. It is
implemented as a unique government type (`nights_watch_government`) with its own
succession law, trait-driven lifecycle, maintenance events, court positions for
castle keepers, a custom Lord Commander election scripted effect, and a full
petition/ranging event chain.

The Lord Commander holds `title:k_the_wall`. All NW members carry the
`nightswatch` trait (or the staging variants `nightswatch_temp` /
`nightswatch_historical`). Upon taking their vows, brothers are assigned one of
three lifestyle traits: `lifestyle_nw_ranger`, `lifestyle_nw_builder`, or
`lifestyle_nw_steward`.

Key source files (all paths relative to the AGOT mod root):

| Area                | File                                                                               |
| ------------------- | ---------------------------------------------------------------------------------- |
| Scripted effects    | `common/scripted_effects/00_agot_nightswatch_effects.txt`                          |
| Scripted triggers   | `common/scripted_triggers/00_agot_nights_watch_triggers.txt`                       |
| Election effect     | `common/scripted_effects/00_agot_nw_btw_effects.txt` (contains `agot_nw_elect_lc`) |
| Election definition | `common/succession_election/00_agot_nights_watch_elective.txt`                     |
| Government          | `common/governments/00_agot_government_types.txt`                                  |
| Succession law      | `common/laws/00_succession_laws.txt` (`nights_watch_realm_succession_law`)         |
| On-actions          | `common/on_action/agot_on_actions/agot_wall_on_actions.txt`                        |
| Decisions           | `common/decisions/agot_decisions/00_agot_nw_decisions.txt`                         |
| Main events         | `events/agot_events/agot_nights_watch_events.txt`                                  |
| Maintenance         | `events/agot_government_events/agot_nightswatch_maintenance_events.txt`            |
| Ranger events       | `events/agot_events/agot_nw_ranger_events.txt`                                     |
| Petition events     | `events/agot_events/agot_nw_petition_events.txt`                                   |
| Filler events       | `events/agot_filler/00_agot_nights_watch_filler_events.txt`                        |

---

## Key Concepts

### Joining the Night's Watch

A character joins the NW through the central effect
`agot_add_to_nightswatch_effect`. This effect handles every aspect of severing a
character's ties to the outside world:

1. **Dragon unbonding** -- untames or unbonds any dragon, cancels
   `bond_with_dragon_scheme`.
2. **Kingsguard removal** -- calls `agot_remove_kingsguard_effect` if trait
   `kingsguard` is present.
3. **Order / devotion cleanup** -- removes traits `order_member`, `devoted`.
4. **Release from prison** -- `release_from_prison = yes`.
5. **Faith bonus** -- Old Gods followers (`faith:old_gods_wnw`) gain +1 piety
   level.
6. **Inheritance transfer** -- `loan_inheritance = yes`, plus bank shares
   transferred to `primary_heir`.
7. **House head transfer** -- if the character is house head, it is handed off
   (to primary heir, or highest-tier ruler in house, or random member).
8. **Title stripping** -- `depose = yes` if the character is a ruler outside the
   NW hierarchy.
9. **Marriage / betrothal / concubine cleanup** -- divorces all spouses, breaks
   betrothals, removes concubines.
10. **Guardian / ward removal** -- severs all guardian/ward relations.
11. **Trait addition** -- `add_trait = nightswatch` (only for human characters).
12. **Memory** -- `create_character_memory = { type = agot_joined_nightswatch }`
    with the LC as participant.
13. **Claims stripped** -- every claim is removed.

The wrapper effect `agot_send_to_nightswatch_effect` takes parameters
`$NIGHTSWATCH_CANDIDATE$` and `$ACTOR$`, calls the above, notifies rivals
(`agot_nights_watch.0027`), moves the character to the LC's court, and gives the
LC a +30 `grateful_opinion` toward the actor.

```pdx
# Usage example -- sending a prisoner to the Wall
agot_send_to_nightswatch_effect = {
    NIGHTSWATCH_CANDIDATE = scope:my_prisoner
    ACTOR = root
}
```

### Oath-Taking and Lifestyle Assignment

After joining, brothers are recruits (trait XP < 100). The maintenance event
`agot_nightswatch_maintenance.0101` fires once the character is 15+ and promotes
them by setting XP to 100 and assigning a lifestyle trait via `random_list`:

- **`lifestyle_nw_ranger`** -- weighted by `prowess` and `martial`; blocked if
  `agot_nw_physically_unfit`.
- **`lifestyle_nw_steward`** -- weighted by `stewardship`, `learning`,
  `intrigue`, `diplomacy`.
- **`lifestyle_nw_builder`** -- same weights as steward; also blocked if
  physically unfit.

A memory `agot_swore_nightswatch_oath` is created at this point.

### Lifecycle Trait Progression

Event `agot_nightswatch_maintenance.0102` gradually improves lifestyle trait XP
for sworn brothers based on their relevant skill scores. Rangers advance faster
with high prowess (15+, 20+, 25+); stewards and builders advance with high
stewardship (10+, 15+, 20+).

### Lord Commander Election

When the LC dies, the on-action `on_nw_lord_commander_death` fires and calls
`agot_nw_elect_lc` (defined in `00_agot_nw_btw_effects.txt`). The election
algorithm:

1. **Gather candidates** -- all courtiers, vassals, and their courtiers with
   `nightswatch` trait. The First Ranger (`title:d_nw_landless_first_ranger`
   holder) is included if not currently beyond the Wall.
2. **Filter eligible** -- must have `nightswatch` trait XP >= 100, be a
   physically able adult, and not be a maester or septon.
3. **Score** -- each candidate gets `agot_nw_lc_succession_score_value`,
   influenced by the outgoing LC's opinion.
4. **Shortlist** -- top 5 by score.
5. **Weighted random** -- one is chosen, weighted by score. Historical overrides
   exist (e.g. `character:Mormont_2` is heavily favored in historical/weighted
   game rules).
6. **Fallback** -- if no eligible candidate exists, a new character is spawned
   from `agot_black_brother_character` template at Castle Black.

The new LC receives `title:k_the_wall` and event `agot_nights_watch.0026` fires,
letting the player choose whether to keep or reset all castle command positions.

There is also a formal elective definition in
`00_agot_nights_watch_elective.txt` (`nights_watch_elective`) which defines
candidate pools and elector logic using vanilla feudal elective patterns, plus
custom AGOT modifiers `agot_nights_watch_elective_negative_modifier` and
`agot_nights_watch_elective_positive_modifier`.

### Castle Keepers (Court Positions)

Each Wall castle has a dedicated court position (e.g.
`b_eastwatch_by_the_sea_keeper`, `b_the_shadow_tower_keeper`,
`b_the_nightfort_keeper`, etc.). When a castle keeper's court position is
revoked, a cleanup event reclaims the holding for the LC. These are mapped via
effects like `agot_on_eastwatch_court_position_revoked` through
`agot_on_greenguard_court_position_revoked` (events `agot_nights_watch.0006`
through `.0023`).

The on-action `on_castle_keeper_start` initializes these at game start and adds
the `nw_castle` province modifier to all Wall baronies.

### Random Deaths and Pruning

Event `agot_nightswatch_maintenance.0100` handles population control. Non-ruler
brothers may die randomly with higher chances for:

- **Pruneable characters** (no family connections, no high skills, no claims)
  when the court is overcrowded (>60 courtiers for kingdom, >20 otherwise): 75%
  chance.
- **Low-prowess recruits, builders, or rangers**: 25% base chance.
- Maesters and septons get a 0.5x multiplier.
- Councillors, court position holders, knights, army members, and characters
  under 16 are immune.

The death causes come from `agot_random_nightswatch_death_effect`:

| Weight | Condition            | Death Reason                   |
| ------ | -------------------- | ------------------------------ |
| 40     | Recruit (XP < 100)   | `death_training_accident`      |
| 20     | Builder              | `death_crushed_by_boulder`     |
| 20     | Builder              | `death_equipment`              |
| 20     | Ranger               | `death_wild_animal`            |
| 20     | Ranger               | `death_disappeared_on_ranging` |
| 20     | Ranger               | `death_lost_in_the_forest`     |
| 20     | Drunkard / depressed | `death_jumped_off_the_wall`    |
| 40     | Any                  | `death_froze_to_death`         |
| 40     | Any                  | `death_lost_in_snowstorm`      |
| 5      | Any                  | `death_fell_off_the_wall`      |
| 40     | Any                  | `death_vanished`               |
| 1      | Lunatic              | `death_grabbed_by_grumkins`    |

### Desertion

Desertion is handled implicitly through the maintenance system. Characters who
are female or otherwise fail `agot_valid_potential_nw_member` are expelled
(deposed if ruler, traits stripped, moved to Winterfell's pool). The trigger
`agot_valid_potential_nw_member` is simply `is_male = yes`, making gender the
sole hard gate.

---

## AGOT Scripted API

### Triggers (`common/scripted_triggers/00_agot_nights_watch_triggers.txt`)

| Trigger                               | Description                                                                                                                |
| ------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| `agot_valid_potential_nw_member`      | `is_male = yes` -- hard gate for NW eligibility                                                                            |
| `agot_reasonable_potential_nw_member` | Valid + adult + not physically unfit + unmarried + not betrothed + human                                                   |
| `agot_is_member_of_nights_watch`      | Has any of: `nightswatch`, `nightswatch_temp`, `nightswatch_historical`                                                    |
| `agot_nw_can_banish`                  | Parameterized (`$BANISHER$`, `$BANISHEE$`); checks cultures, geography, NW existence                                       |
| `agot_nw_physically_unfit`            | Checks for `blind`, `dwarf`, `clubfooted`, `one_legged`, `one_handed`, `incapable`, `infirm`, `physique_bad_1/2/3`, `weak` |
| `agot_nw_is_pruneable_trigger`        | No family ties to rulers, no claims, no spouse, no minor children, no extreme skills                                       |

### Effects (`common/scripted_effects/00_agot_nightswatch_effects.txt`)

| Effect                                      | Scope     | Description                                           |
| ------------------------------------------- | --------- | ----------------------------------------------------- |
| `agot_add_to_nightswatch_effect`            | character | Full NW induction -- see "Joining" section above      |
| `agot_send_to_nightswatch_effect`           | any       | Wrapper; params: `$NIGHTSWATCH_CANDIDATE$`, `$ACTOR$` |
| `agot_random_nightswatch_death_effect`      | character | Weighted random death for NW brothers                 |
| `agot_nightswatch_ruler_on_start_effect`    | character | Game-start init for NW rulers                         |
| `agot_nightswatch_courtier_on_start_effect` | character | Game-start init for NW courtiers                      |
| `agot_remove_nightswatch_traits_effect`     | character | Strips all NW-related traits                          |
| `agot_on_*_court_position_revoked`          | (various) | Castle keeper cleanup (one per castle)                |

### Election Effect (`common/scripted_effects/00_agot_nw_btw_effects.txt`)

| Effect             | Scope                  | Description                                               |
| ------------------ | ---------------------- | --------------------------------------------------------- |
| `agot_nw_elect_lc` | character (current LC) | Full election algorithm -- gather, score, shortlist, pick |

### Government (`common/governments/00_agot_government_types.txt`)

```pdx
nights_watch_government = {
    government_rules = {
        create_cadet_branches = no
        rulers_should_have_dynasty = no
        dynasty_named_realms = no
        court_generate_spouses = no
    }
    court_generate_commanders = no
    primary_holding = castle_holding
    required_county_holdings = { castle_holding }
    valid_holdings = { ruin_holding }
    can_get_government = {
        OR = {
            has_title = title:k_the_wall
            any_liege_or_above = { has_title = title:k_the_wall }
        }
        OR = {
            has_trait = nightswatch
            has_trait = nightswatch_temp
            has_trait = nightswatch_historical
        }
    }
    character_modifier = {
        monthly_dread = 0.5
        army_maintenance_mult = -0.6
        men_at_arms_maintenance = -0.7
        martial_per_prestige_level = 2
        prowess_per_prestige_level = 2
        holy_order_hire_cost_mult = 1000
        ai_war_chance = 2
        ai_war_cooldown = -0.5
    }
    vassal_contract_group = nights_watch_vassal
    flags = {
        government_is_nw
        government_is_settled
        government_is_default
    }
}
```

The flag `government_is_nw` is the standard way to check if a character belongs
to the Night's Watch government in triggers throughout the mod.

### Succession Law

`nights_watch_realm_succession_law` in `common/laws/00_succession_laws.txt`:

```pdx
nights_watch_realm_succession_law = {
    can_keep = { government_has_flag = government_is_nw }
    can_have = { government_has_flag = government_is_nw }
    should_start_with = { government_has_flag = government_is_nw }
    potential = { government_has_flag = government_is_nw }
    succession = {
        order_of_succession = generate
    }
}
```

Note the `order_of_succession = generate` -- the actual successor is determined
by the `agot_nw_elect_lc` scripted effect, not by the elective law alone.

---

## Decisions

All decisions are in `common/decisions/agot_decisions/00_agot_nw_decisions.txt`.

### `restore_the_nights_watch`

A major decision for the holder of `title:h_the_iron_throne` or
`title:e_the_north`.

- **is_shown**: Ruler + landed + either no LC exists, or player holds/vassalizes
  `k_the_wall`.
- **is_valid**: Prestige level >= 3, independent, completely controls
  `world_westeros_the_wall_only`.
- **Cost**: 500 gold, 250 prestige.
- **Effect**: Fires `agot_nights_watch.0024`, which creates a new LC from
  template `agot_black_brother_character`, grants them `k_the_wall`,
  `d_the_wall`, `d_nw_landless_first_ranger`, sets NW government, and optionally
  grants Brandon's Gift or the full New Gift depending on what the player
  controls.

### `dissolve_the_nights_watch`

A major decision for wildling culture rulers.

- **is_shown**: Ruler + landed + LC exists + wildling culture + no `nightswatch`
  trait.
- **is_valid**: Prestige level >= 3, independent, completely controls
  `world_westeros_the_wall_only`, holds or vassalizes `k_the_wall`.
- **Cost**: 400 gold, 250 prestige.
- **Effect**: Fires `agot_nights_watch.0025`, which destroys `k_the_wall` and
  `d_the_wall`, grants dynasty prestige (1500), adds
  `walled_off_no_more_modifier` for 50 years, grants prestige (1500) and gold
  (200), and re-assigns Wall duchies to `k_last_lands`.

### `reclaim_wall_for_nw` (AI-only)

An AI decision to start or join a `agot_wall_reclamation_cb` war against
wildlings holding NW de jure lands. Never shown to human players (placeholder
texts).

- Weighted by `ai_boldness`, `ai_honor`, proximity to the North, military
  strength vs NW.
- Will not fire if the AI is in debt or weaker than the NW.

### `rebuild_nights_watch_fort` (Commented Out)

Currently disabled/mothballed. Would have allowed the LC to rebuild abandoned
Wall castles. The events `agot_nights_watch.1000` through `.1004` are also
commented out.

---

## Events & Story Cycles

### Main Events (`agot_nights_watch` namespace)

| Event ID        | Summary                                                                      |
| --------------- | ---------------------------------------------------------------------------- |
| `.0001`         | On-join: new recruits arriving at a NW court become brothers or get expelled |
| `.0003`         | Debug: forces NW government and succession law on NW title holders           |
| `.0004`         | Wildling breach notification to LC (shows `scope:wildling_breacher`)         |
| `.0005`         | Wildling breach: starts `wildling_raid_cb` war, spawns 1000-levy army        |
| `.0006`-`.0023` | Castle keeper cleanup events (one per Wall castle)                           |
| `.0024`         | Restore NW -- creates new LC, grants titles, optional Gift expansion         |
| `.0025`         | Dissolve NW -- destroys Wall titles, grants prestige to wildlings            |
| `.0026`         | New LC setup: handle First Ranger, reset command positions, restore traits   |
| `.0027`         | Rival takes the Black -- notification to rivals with stress impact           |
| `.0028`         | Hidden: converts `nightswatch_temp` to `nightswatch` with full XP            |
| `.0030`         | Hidden: transfers all holdings from a deposed NW holder to the LC            |
| `.0100`         | Notify LC of new recruit arrival                                             |

### Flavour Events (2000 series)

| Event ID        | Summary                                                  |
| --------------- | -------------------------------------------------------- |
| `.2001`         | Child wishes to join the NW -- player can send or refuse |
| `.2002`         | Kinsman wants to join the NW                             |
| `.2003`-`.2007` | Additional NW flavour events                             |

### Gift Reclamation Events (3000 series)

| Event ID | Summary                                                                     |
| -------- | --------------------------------------------------------------------------- |
| `.3000`  | LC petitions Winterfell holder for New Gift/Brandon's Gift land reclamation |
| `.3001`+ | Follow-up events for the gift exchange process                              |

### Maintenance Events (`agot_nightswatch_maintenance` namespace)

| Event ID | Summary                                                                |
| -------- | ---------------------------------------------------------------------- |
| `.0001`  | Game-start initialization: applies NW effects to all Wall characters   |
| `.0002`  | Periodic maintenance: trait assignment, government correction, pruning |
| `.0100`  | Random death chance for non-ruler brothers                             |
| `.0101`  | Oath-taking: recruits gain full XP + lifestyle trait                   |
| `.0102`  | Trait progression: improves lifestyle trait XP based on skills         |

### Ranger Events (`agot_nw_ranger_events` namespace)

| Event ID | Summary                                                                                                                                            |
| -------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| `.0001`  | First Ranger died/deserted/became LC -- player picks new First Ranger from courtier list using custom GUI `agot_character_selection_three_options` |

The First Ranger is tracked via `title:d_nw_landless_first_ranger` and assigned
as `councillor_marshal`.

### Petition Events (`agot_nw_petition_events` namespace)

A large event chain (~50 events) where the LC sends an envoy to petition lords
for men, supplies, or both.

- `.01` / `.02` -- chain start (Royal Court DLC vs non-RC versions)
- `.0100`-`.0120` -- journey random events (treasure, volunteers, bandits,
  duels, animal attacks)
- `.0200`-`.0213` -- post-petition events (secret female recruit, deserters,
  blacksmith supplies, theft)
- `.1000`-`.1011` -- non-RC petition chain (envoy travel, lord decision,
  persuasion, return)

### Filler Events (`agot_filler_nights_watch` namespace)

- `.0001`-`.0006` -- Mule shortage at Eastwatch (smuggling sub-plot, adds
  `mule_shortage_modifier`)

### On-Actions (`agot_wall_on_actions.txt`)

| On-Action                     | Trigger                                                                                  |
| ----------------------------- | ---------------------------------------------------------------------------------------- |
| `on_nw_start`                 | Game start: populates `nw_wall_provinces` global variable list with all 19 Wall baronies |
| `on_castle_keeper_start`      | Game start: assigns court positions, adds `nw_castle` modifier                           |
| `on_castle_keeper_title_gain` | Title gain: reassigns court positions or revokes titles                                  |
| `on_wall_succession`          | Stub (TODO)                                                                              |
| `on_wall_election`            | Stub (TODO)                                                                              |
| `on_nw_lord_commander_death`  | LC death: triggers `agot_nw_elect_lc`                                                    |
| `on_nw_holder_death`          | NW vassal death: transfers holdings to liege, courtiers to LC                            |
| `on_wall_breach_chance`       | Delayed 15 years from game start: wildling breach events                                 |

---

## Sub-Mod Recipes

### Recipe 1: Allow Women in the Night's Watch

Override the single trigger that gates membership:

```pdx
# In your mod's common/scripted_triggers/
agot_valid_potential_nw_member = {
    # Remove is_male = yes to allow women
    always = yes
}
```

You will also need to update `agot_nw_can_banish` (the `$BANISHEE$` block) and
the elective candidate/elector limits in `00_agot_nights_watch_elective.txt`
which filter on `is_male = yes`.

### Recipe 2: Add a Custom NW Death Cause

Extend the random death list by overriding
`agot_random_nightswatch_death_effect`:

```pdx
agot_random_nightswatch_death_effect = {
    random_list = {
        # ... keep all existing entries ...

        15 = {
            trigger = {
                has_trait = lifestyle_nw_steward
            }
            death = { death_reason = death_poisoned_food }
        }
    }
}
```

Remember to define `death_poisoned_food` in `common/death_reasons/` and add
localization.

### Recipe 3: Add a New NW Event Chain (Deserter Hunt)

```pdx
namespace = my_nw_deserter

# Trigger from maintenance or on_action
my_nw_deserter.0001 = {
    type = character_event
    title = my_nw_deserter.0001.t
    desc = my_nw_deserter.0001.desc
    theme = nightswatch
    override_background = { reference = agot_the_wall }

    trigger = {
        has_title = title:k_the_wall
        government_has_flag = government_is_nw
        any_courtier = {
            has_trait = nightswatch
            has_trait = lifestyle_nw_ranger
            prowess >= 12
        }
    }

    immediate = {
        random_courtier = {
            limit = {
                has_trait = nightswatch
                has_trait = lifestyle_nw_ranger
                prowess >= 12
            }
            save_scope_as = hunter
        }
    }

    option = {
        name = my_nw_deserter.0001.a
        # Send the ranger to hunt the deserter
        scope:hunter = {
            add_trait_xp = {
                trait = lifestyle_nw_ranger
                value = 5
            }
        }
    }
}
```

### Recipe 4: Custom NW Court Position

Add a new position (e.g., Wall Maester) following the pattern of existing
keepers:

```pdx
# common/court_positions/my_nw_positions.txt
wall_maester_court_position = {
    # ... standard court position definition ...
    is_shown = {
        employer = {
            government_has_flag = government_is_nw
        }
    }
    valid_position = {
        has_trait = maester
        employer = {
            government_has_flag = government_is_nw
        }
    }
}
```

### Recipe 5: Petition the Night's Watch for Help

If you want to add an interaction where a Westerosi lord asks the NW for ranger
scouts, check against `government_is_nw` and use `title:k_the_wall.holder`:

```pdx
# In a character_interaction or decision
is_valid = {
    exists = title:k_the_wall.holder
    title:k_the_wall.holder = {
        government_has_flag = government_is_nw
        opinion = {
            target = root
            value >= 0
        }
    }
}
```

---

## Pitfalls

1. **Trait vs government check** -- Do not assume `has_trait = nightswatch`
   implies `government_has_flag = government_is_nw`. Courtiers have the trait
   but not the government. Use the trait to check membership, the flag to check
   NW realm mechanics.

2. **Three nightswatch traits** -- There are three: `nightswatch` (active
   brother), `nightswatch_temp` (transitional, used during election), and
   `nightswatch_historical` (bookmark characters awaiting initialization).
   Always use `agot_is_member_of_nights_watch` to catch all three.

3. **Election is a scripted effect, not just an elective law** -- The actual LC
   selection runs through `agot_nw_elect_lc`, not through the
   `nights_watch_elective` succession definition alone. If you want to influence
   elections, you likely need to modify the scripted effect or the
   `agot_nw_lc_succession_score_value` script value.

4. **Title hierarchy matters** -- The NW uses `title:k_the_wall` (kingdom),
   `title:d_the_wall` (duchy), and `title:d_nw_landless_first_ranger` (landless
   duchy for the First Ranger). Do not confuse duchy and kingdom scope when
   checking holders.

5. **Castle keeper revocation cascade** -- Every Wall castle has its own
   revocation effect and event. If you add a new castle to the Wall, you must
   also add a corresponding `agot_on_<castle>_court_position_revoked` effect and
   cleanup event.

6. **Gender gate is a single trigger** -- `agot_valid_potential_nw_member` only
   checks `is_male = yes`. The maintenance system will actively expel anyone who
   fails this check by stripping traits and moving them to Winterfell's pool. If
   you override this trigger, make sure the maintenance events will not fight
   your changes.

7. **`agot_send_to_nightswatch_effect` requires both parameters** -- Always pass
   both `$NIGHTSWATCH_CANDIDATE$` and `$ACTOR$`. The actor receives the LC's
   gratitude opinion and determines tooltip context.

8. **Physically unfit characters** -- `agot_nw_physically_unfit` blocks ranger
   and builder lifestyle assignment but does NOT prevent joining the NW. The
   character can still become a steward. Do not add physically unfit checks to
   your own NW eligibility triggers unless you specifically want to block
   induction entirely.

9. **Wall province list is hardcoded at game start** -- The global variable list
   `nw_wall_provinces` is populated in `on_nw_start` with 19 specific baronies.
   If your sub-mod adds new Wall castles, you must also add them to this list.

10. **Commented-out rebuild system** -- The castle rebuilding decision and
    events (`rebuild_nights_watch_fort`, `.1000`-`.1004`) are fully commented
    out. Do not try to call them; they will not work. If you want rebuild
    mechanics, you need to implement your own.
