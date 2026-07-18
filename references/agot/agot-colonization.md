# AGOT: Colonization & Ruin Rebuilding

## Overview

AGOT replaces vanilla CK3's barren/wasteland system with a full **colonization
pipeline**. Unowned land is held by a special `title:c_wilderness` holder with
`government_is_wilderness` flag. Players and AI can colonize adjacent wilderness
counties, turning them into `settlement_holding` provinces that must be upgraded
through three tiers (`settlement_01` -> `settlement_02` -> `settlement_03`)
before being converted into a proper holding (castle, city, temple, tribal, or
pirate den).

A parallel system handles **ruin rebuilding**: baronies with `ruin_holding` type
trigger flavor events when held by a character.

Landless adventurers (EP3) use a separate decision-based path with
`laamp_settler_maa` troops as a currency.

### Lifecycle of a Colony

1. Wilderness county (`wilderness_holding`, held by `title:c_wilderness.holder`)
2. Player/AI colonizes -> `settlement_holding` with `settlement_01` building
3. Random "blocker" buildings (`bandits`, `wolf_den`, `bear_den`,
   `dense_growth`, `flooded_lands`) are placed, must be cleared
4. Player upgrades through `settlement_02` and `settlement_03`
5. Once `settlement_03` is built, all blockers cleared, and dev >= 3, the
   settlement can be feudalized into `castle_holding`, `city_holding`,
   `church_holding`, or `tribal_holding`

---

## Key Concepts

### Holding Types

| Holding Type         | Role                                                 |
| -------------------- | ---------------------------------------------------- |
| `wilderness_holding` | Uncolonized land, held by wilderness dummy character |
| `settlement_holding` | Active colony in progress (3 upgrade tiers)          |
| `ruin_holding`       | Destroyed barony, triggers rebuilding events         |
| `pirate_den_holding` | Pirate-government colony variant                     |

### Settlement Limit

Each ruler has a maximum number of `settlement_holding` counties they can
maintain, based on their highest title tier. Exceeding this limit does not block
colonization but triggers the AI to abandon excess colonies.

The trigger `above_settlement_limit` (in `00_agot_colonization_triggers.txt`)
checks:

| Highest Title Tier | Max Settlements |
| ------------------ | --------------- |
| County             | 1               |
| Duchy              | 2               |
| Kingdom            | 3               |
| Empire             | 4               |

The companion trigger `agot_at_settlement_limit` checks for exactly reaching the
limit.

### Colonization Cost

Defined in `common/script_values/00_agot_colonization_values.txt` via
`colonize_cost_val`:

```pdx
# Base constants
@base_colonize_cost = 50
@count_colonize_cost = 25
@duke_colonize_cost = 50
@king_colonize_cost = 75
@emporer_colonize_cost = 100

colonize_cost_val = {
    value = 0
    add = { value = base_colonize_cost }
    if = {
        limit = { highest_held_title_tier = tier_county }
        add = { value = count_colonize_cost }     # Total: 75
    }
    else_if = {
        limit = { highest_held_title_tier = tier_duchy }
        add = { value = duke_colonize_cost }       # Total: 100
    }
    # ... king = 125, emperor = 150
}
```

### Upkeep Modifiers

Holding settlements imposes scaling tax penalties via character modifiers. The
variable `num_settled_wilderness` tracks how many settlements a character holds.
Event `agot_colonization_events.0007` dispatches to tier-specific events
(`.0008` for counts, `.0009` for dukes, `.0010` for kings, `.0011` for emperors,
`.0012` for hegemons) that apply the appropriate modifier.

Defined in `common/modifiers/00_agot_colonization_modifiers.txt`:

| Modifier                             | `domain_tax_mult` | `vassal_tax_mult` |
| ------------------------------------ | ----------------- | ----------------- |
| `holding_one_settlements`            | -5%               | --                |
| `holding_two_settlements`            | -10%              | --                |
| `holding_three_settlements`          | -25%              | --                |
| `holding_four_settlements`           | -50%              | --                |
| `holding_five_settlements`           | -75%              | -25%              |
| `holding_more_than_five_settlements` | -95%              | -50%              |

Higher-tier rulers get more "free" settlements before the penalty escalates. For
example, a duke's first two settlements only trigger `holding_one_settlements`
(-5%), while a count's first settlement immediately gets -5%.

### Colonization Cooldown

After colonizing, a `colonization_cooldown` variable is set:

- **Pirates**: 4 years
- **Everyone else**: 2 years

### Blocker Buildings

When a county is colonized, `add_random_wilderness_blocker_building` places
random obstacles on the province. These have the `obstacle` flag and must be
cleared (turned into `_cleared` variants) before the settlement can be
feudalized:

- `bandits` / `bandits_cleared`
- `wolf_den` / `wolf_den_cleared`
- `bear_den` / `bear_den_cleared`
- `dense_growth` / `dense_growth_cleared`
- `flooded_lands` / `flooded_lands_cleared`
- `pirate_remnants` / `pirate_remnants_cleared`

Event `agot_colonization_events.9000` cleans up `_cleared` buildings by removing
them entirely via `cleanup_cleared_blockers_effect`.

### block_settlement_ability Modifier

A county modifier that prevents colonization entirely. Used to lock specific
counties from being settled (e.g., story-driven regions). Checked in both AI
logic and the player scripted GUI.

---

## AGOT Scripted API

### Scripted Effects (`common/scripted_effects/00_agot_colonization_effects.txt`)

#### `ai_colonization_effect`

The core colonization effect. Transfers the wilderness county to the new holder,
sets faith/culture, swaps holding type, deducts gold, increments
`num_settled_wilderness`, sets cooldown, and fires struggle catalysts.

**Parameters:**

- `$WILDERNESS$` -- the county to colonize (scope: title)
- `$ROOT_SCOPE$` -- the colonizing character

```pdx
ai_colonization_effect = { WILDERNESS = scope:target_county ROOT_SCOPE = root }
```

Key behaviors:

- Transfers title via `create_title_and_vassal_change` with `type = returned`
- Sets county faith to holder's faith
- Handles High Valyrian culture splitting (game rule
  `agot_hv_conversion_offshoots` -> `westerosi_valyrian` or `essosi_valyrian`)
- Sets holding to `pirate_den_holding` for pirate governments,
  `settlement_holding` otherwise
- Deducts `colonize_cost_val` gold (unless the character owns a
  `story_conqueror` story)
- Fires `agot_colonization_events.0007` for upkeep recalculation
- Activates `catalyst_new_colony_btw` for the Beyond the Wall struggle

#### `make_settlement_county_wilderness`

Reverts a colony back to wilderness. Transfers county to
`title:c_wilderness.holder`, resets faith to `faith:fg_unknown`, culture to
`culture:unknown_culture`, removes all non-capital holdings, zeroes development,
and sets the capital holding back to `wilderness_holding`.

**Parameters:**

- `$COUNTY$` -- the county to revert

```pdx
make_settlement_county_wilderness = { COUNTY = scope:target }
```

#### `colonize_pirate_den_effect`

Converts a pirate den province into a settlement. Swaps `pirate_den_holding` to
`settlement_holding`, adds `pirate_remnants` blocker building.

**Parameters:**

- `$COLONIZER$` -- the character
- `$PIRATE_DEN$` -- the province

#### `pirate_takeover_effect`

Allows a pirate character to conquer and convert a county to pirate den
holdings.

**Parameters:**

- `$PIRATE$` -- the pirate character
- `$COUNTY$` -- the target county

#### `agot_upgrade_settlement_to_full_holding_effect`

Converts a `settlement_holding` to a proper holding type based on government:

- `tribal_government` -> `tribal_holding`
- `government_is_pirate_trigger_check` -> `pirate_den_holding`
- Default -> `castle_holding`

**Parameters:**

- `$COUNTY$` -- the county to upgrade

#### `correct_wilderness_tracker`

Recounts all `settlement_holding` counties held by a character and fixes the
`num_settled_wilderness` variable if it drifted. Removes stale upkeep modifiers
and reapplies the correct one.

#### `remove_upkeep_modifier`

Strips all six upkeep character modifiers. Called before reapplying the correct
tier.

#### `add_random_wilderness_blocker_building`

Randomly adds one blocker building to a province (weighted by terrain).
Forest/taiga terrain heavily favors `dense_growth`.

#### `agot_conqueror_settle_wilderness_effect`

Used by the conqueror story cycle. Auto-upgrades existing settlements through
tiers, then colonizes the best adjacent wilderness county (scored by de jure
alignment: duchy +16, kingdom +8, empire +4, neighbor +2).

#### `agot_increase_settler_maa`

Adds soldiers to the `laamp_settler_maa` regiment (adventurer settler troops).
Creates the regiment if it does not exist.

**Parameters:**

- `$CHARACTER$` -- the adventurer
- `$SIZE$` -- number of soldiers to add

### Scripted Triggers (`common/scripted_triggers/00_agot_colonization_triggers.txt`)

| Trigger                                 | Scope     | Description                                                                                |
| --------------------------------------- | --------- | ------------------------------------------------------------------------------------------ |
| `above_settlement_limit`                | character | True if holding more settlements than tier allows                                          |
| `agot_at_settlement_limit`              | character | True if at exactly the settlement cap                                                      |
| `not_settlement_or_wilderness`          | title     | True if county capital is neither settlement nor wilderness                                |
| `region_is_colonized_and_controlled_by` | any       | Checks a de jure region has no settlements/wilderness and is fully controlled by `$RULER$` |
| `region_is_colonized`                   | any       | Same but infers ruler from title holder                                                    |

### Script Values (`common/script_values/00_agot_colonization_values.txt`)

| Value                                               | Description                                                                                       |
| --------------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| `colonize_cost_val`                                 | Gold cost to colonize, scales by tier (75-150)                                                    |
| `feudalize_tribal_holding_interaction_cost`         | Gold cost to upgrade settlement to full holding (base 500, reduced by tier, +2000 for permafrost) |
| `settle_settlement_holding_interaction_cost`        | Fixed 150 gold                                                                                    |
| `settlement_title_tier_limit`                       | Returns max settlements for current tier (1-5)                                                    |
| `number_of_held_colonies`                           | Counts current settlement_holding counties                                                        |
| `agot_settle_wilderness_as_adventurer_county_limit` | Adventurer settler MAA count / 100                                                                |
| `agot_current_settler_maa_count`                    | Raw settler MAA troop count                                                                       |

### Scripted GUI (`common/scripted_guis/00_agot_colonization_scripted_gui.txt`)

| GUI                                | Scope     | Purpose                                                                                                                                                                   |
| ---------------------------------- | --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `agot_county_holder_is_wilderness` | province  | Shows UI indicator when county is wilderness                                                                                                                              |
| `agot_can_colonize`                | character | Player colonization button: checks gold >= `colonize_cost_val`, not Night's Watch, not uninteractable, adjacent to wilderness, no cooldown, no `block_settlement_ability` |

The `agot_can_colonize` GUI is the **player-facing colonization interface**. AI
uses `agot_colonization_events.0006` instead.

---

## Interactions & Decisions

### Character Interactions (`common/character_interactions/00_agot_colonization_interactions.txt`)

All interactions are `hidden = yes` (triggered by UI buttons, not the
interaction menu) unless noted.

#### `return_settlement_county_to_wilderness`

Abandons a settlement colony, reverting it to wilderness. Cannot abandon your
last county.

#### `feudalize_into_castle_holding_interaction`

Upgrades a fully developed settlement (has `settlement_03`, dev >= 3, zero
`obstacle` buildings) into a `castle_holding`. Costs
`feudalize_tribal_holding_interaction_cost` gold for human players (free for
AI). Decrements `num_settled_wilderness`.

#### `feudalize_into_city_holding_interaction`

Same requirements as castle, but produces `city_holding`.

#### `feudalize_into_temple_holding_interaction`

Same requirements, produces `church_holding`. Cannot be the county capital
barony.

#### `tribalize_settlement_holding_interaction`

For `government_is_tribal` characters. Converts settlement to `tribal_holding`.
Requires `settlement_03` and zero blockers. Costs half gold + double prestige of
`settle_settlement_holding_interaction_cost`.

#### `colonize_pirate_den_interaction`

For non-pirate rulers who hold a `pirate_den_holding` province. Converts it to
`settlement_holding` and adds `pirate_remnants` blocker.

#### `support_colonize_pirate_den_interaction`

**Visible interaction** (not hidden). A liege can pay
`feudalize_holding_interaction_cost` gold to convert a vassal's pirate den
directly to `castle_holding`. Grants +15 `grateful_opinion` and influence for
administrative governments. AI checks: not at war, not warlike, gold >=
cost \* 4.

#### `pirate_takeover_of_holding_interaction`

For pirate-government characters. Converts a castle or city holding to
`pirate_den_holding`. Requires dev <=
`dev_level_to_convert_into_pirate_holding`, coastal county. Costs 200 gold + 500
prestige.

### Decisions (`common/decisions/agot_decisions/00_agot_colonization_decisions.txt`)

#### `settle_wilderness_county_or_duchy_decision`

**Adventurer/pirate landing decision.** Requires EP3 DLC. Available when a
landless adventurer or landless pirate is located in a wilderness county.

Requirements:

- Location is wilderness, not occupied/raided/sieged
- No `block_settlement_ability` on the county
- Adventurers need domicile building `settlement_supplies_01`
- Pirates must be in `historical_pirate_region`

Two options via widget:

- **`settle_one_county`**: Needs >= 100 `laamp_settler_maa` troops
- **`settle_duchy`**: Needs >= 300 `laamp_settler_maa` troops, settles all
  wilderness counties in the duchy

On execution:

- Calls `ai_colonization_effect` for each county
- Assigns government based on culture head (feudal/clan/tribal, or pirate if in
  pirate region with pirate domicile)
- Grants random dev +2/3/4 per county
- Converts holding type based on government
- Destroys all `laamp_settler_maa` regiments
- If settling a duchy and controlling >= 50%, auto-creates the duchy title

---

## Events

### Core Events (`events/agot_events/agot_colonization_events.txt`)

| Event ID                                | Type            | Description                                                                                                                                                                                                                           |
| --------------------------------------- | --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `agot_colonization_events.0006`         | hidden, AI-only | Yearly pulse: AI evaluates adjacent wilderness and colonizes the best candidate. Scores by de jure alignment (duchy +16, kingdom +8, empire +4, adjacent +2). Checks income thresholds (50-150 gold, 1.5-2.0 monthly income by tier). |
| `agot_colonization_events.0007`         | hidden          | Dispatcher: removes old upkeep modifier, routes to tier-specific events `.0008`-`.0012`                                                                                                                                               |
| `agot_colonization_events.0008`-`.0012` | hidden          | Apply the correct `holding_X_settlements` modifier based on `num_settled_wilderness` and ruler tier                                                                                                                                   |
| `agot_colonization_events.0020`         | hidden, AI-only | Yearly: AI with negative income or above settlement limit abandons lowest-tier settlements                                                                                                                                            |
| `agot_colonization_events.0022`         | hidden, AI-only | Vassal directive: AI with `vassal_directive_settle_wilderness` flag upgrades existing settlements                                                                                                                                     |
| `agot_colonization_events.9000`         | hidden          | Removes `_cleared` blocker buildings after obstacles are resolved                                                                                                                                                                     |

### Filler Events (`events/agot_filler/00_agot_colonization_filler_events.txt`)

Flavor events fired yearly for characters who own `settlement_holding`
provinces. 17% chance per year, weighted random selection.

**Terrain-specific:**

- `agot_filler_colonization.0001` -- [Forest] The Squirrel (prowess duel)
- `agot_filler_colonization.0002` -- [Forest] The White Hart
- `agot_filler_colonization.0003` -- [Highlands] Hard Scrabble

**Generic colony events:**

- `agot_filler_colonization.1001` -- Recruitment Drive
- `agot_filler_colonization.1002` -- A New Life
- `agot_filler_colonization.1003` -- The Blaze
- `agot_filler_colonization.1004` -- A Den of Sin
- `agot_filler_colonization.1005` -- Thick as Thieves
- `agot_filler_colonization.1006` -- Colonial Feud
- `agot_filler_colonization.1007` -- Boycott
- `agot_filler_colonization.1008` -- Plague (rare, weight 10)
- `agot_filler_colonization.1009` -- Prospecting
- `agot_filler_colonization.1010` -- Lupine Threat
- `agot_filler_colonization.1011` -- Bandit Country
- `agot_filler_colonization.1012` -- A Plea from the Settlers
- `agot_filler_colonization.1013` -- Astonishing Progress
- `agot_filler_colonization.1014` -- Heresy Outbreak

### Rebuilding Ruins Events

> **Note:** The ruin system is a separate, dedicated system from colonization.
> It has its own effects, 41 events (5178 lines), and location-specific chains
> (Moat Cailin, Harrenhal). See the full guide: [agot-ruins.md](agot-ruins.md)

### On-Actions (`common/on_action/agot_on_actions/agot_colonization_on_actions.txt`)

| On-Action                                                                         | Fires                                                                                                                     |
| --------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| `yearly_global_pulse` -> `agot_pirate_colonization`                               | 10% chance per wilderness county in `historical_pirate_region` to spawn pirates                                           |
| `random_yearly_playable_pulse` -> `random_yearly_playable_pulse_colonization`     | 50% no-event chance; equal weight between `.0006` (AI colonize) and `.0022` (AI upgrade)                                  |
| `yearly_playable_pulse` -> `agot_filler_colonization_events`                      | Filler events for settlement holders                                                                                      |
| `yearly_playable_pulse`                                                           | Fires `agot_colonization_events.0020` (AI abandon excess)                                                                 |
| `on_domicile_building_completed` -> `on_domicile_building_completed_colonization` | Grants 2 `laamp_settler_maa` soldiers per `settlement_supplies` tier built                                                |
| `on_travel_plan_arrival` / `on_travel_plan_movement`                              | Adventurers with settler MAA gain +50 troops when passing through non-wilderness holdings (6-month cooldown per province) |
| `on_title_gain` -> `on_title_gain_colonization`                                   | Destroys settler MAA when gaining a title (landing ends adventurer phase)                                                 |

---

## Sub-Mod Recipes

### Recipe 1: Make a Region Uncolonizable

Apply the `block_settlement_ability` county modifier to prevent colonization.
The system already checks for this everywhere.

```pdx
# In an on_action or event:
title:c_my_locked_county = {
    add_county_modifier = {
        modifier = block_settlement_ability
        years = -1  # Permanent
    }
}
```

### Recipe 2: Instant Colony (Skip Settlement Phase)

Use `ai_colonization_effect` then immediately upgrade to a full holding:

```pdx
my_instant_colony_effect = {
    ai_colonization_effect = { WILDERNESS = scope:target_county ROOT_SCOPE = root }
    scope:target_county = {
        agot_upgrade_settlement_to_full_holding_effect = { COUNTY = this }
    }
    root = { correct_wilderness_tracker = yes }
}
```

### Recipe 3: Add a Custom Blocker Building

Define a building with the `obstacle` flag in your settlement buildings file.
The feudalization interactions check
`has_building_with_flag = { flag = obstacle count = 0 }`, so any building with
this flag will block upgrading.

```pdx
# common/buildings/my_blocker_buildings.txt
haunted_forest = {
    can_construct = { always = no }
    can_construct_potential = { always = no }
    flag = obstacle

    province_modifier = {
        monthly_county_control_decline_add = -0.5
    }
}

haunted_forest_cleared = {
    can_construct_potential = { always = no }
    # No obstacle flag -- clearing this removes the block
    on_complete = {
        county.holder = {
            cleanup_cleared_blockers_effect = yes
        }
    }
}
```

### Recipe 4: Custom Colonization Filler Event

Add your own events to the yearly pulse by hooking into the on-action:

```pdx
# common/on_action/my_on_actions.txt
agot_filler_colonization_events = {
    random_events = {
        100 = my_namespace.0001
    }
}
```

Your event must trigger on characters who own `settlement_holding` provinces:

```pdx
# events/my_events.txt
namespace = my_namespace

my_namespace.0001 = {
    type = character_event
    title = my_namespace.0001.t
    desc = my_namespace.0001.desc
    theme = realm

    trigger = {
        any_directly_owned_province = {
            has_holding_type = settlement_holding
        }
        NOT = { has_character_flag = had_my_event }
    }

    immediate = {
        add_character_flag = {
            flag = had_my_event
            years = 25
        }
        random_directly_owned_province = {
            limit = { has_holding_type = settlement_holding }
            save_scope_as = colony_province
            county = { save_scope_as = colony_county }
        }
    }

    option = {
        name = my_namespace.0001.a
        scope:colony_county = {
            change_development_level = 1
        }
    }
}
```

### Recipe 5: Grant a Free Colony to a Character

```pdx
# Colonize without gold cost by temporarily giving gold
scope:target_character = {
    add_gold = colonize_cost_val
    ai_colonization_effect = { WILDERNESS = scope:target_county ROOT_SCOPE = scope:target_character }
    correct_wilderness_tracker = yes
}
```

### Recipe 6: Custom Settlement Limit

Override `above_settlement_limit` in your own scripted triggers file. Your file
must load after AGOT's (use a filename that sorts after
`00_agot_colonization_triggers.txt`).

```pdx
# common/scripted_triggers/99_my_colonization_triggers.txt
above_settlement_limit = {
    trigger_if = {
        limit = { highest_held_title_tier = tier_county }
        any_held_title = {
            tier = tier_county
            title_province ?= { has_holding_type = settlement_holding }
            count > 2  # Was 1, now 2 for counts
        }
    }
    # ... repeat for other tiers
}
```

---

## Pitfalls

1. **Always call `correct_wilderness_tracker` after manual colonization.** If
   you use `ai_colonization_effect` or `make_settlement_county_wilderness`
   outside the normal flow, the `num_settled_wilderness` variable and upkeep
   modifier can desync. The effect recounts all settlements and reapplies the
   correct modifier.

2. **Do not set holdings directly without the colonization effect.** Simply
   calling `set_holding_type = settlement_holding` on a wilderness province will
   not transfer the title from the wilderness holder, set faith/culture, deduct
   gold, or track the settlement count. Always use `ai_colonization_effect`.

3. **Feudalization requires ALL three conditions.** The feudalization
   interactions check: `settlement_03` built, zero `obstacle`-flagged buildings,
   AND `development_level >= 3`. Missing any one silently disables the button.

4. **The `block_settlement_ability` modifier blocks the GUI button AND AI
   logic.** But it does NOT prevent script-level calls to
   `ai_colonization_effect`. If your mod adds counties with this modifier, make
   sure your own effects also check for it.

5. **Pirate governments have separate paths.** Pirates get `pirate_den_holding`
   instead of `settlement_holding`, a 4-year cooldown instead of 2, and use
   `colonize_pirate_den_effect` when non-pirates take over pirate dens. Do not
   assume all colonies are `settlement_holding`.

6. **High Valyrian culture splitting is conditional.** The game rule
   `agot_hv_conversion_offshoots` controls whether High Valyrian colonizers get
   `westerosi_valyrian` or `essosi_valyrian` culture applied to the county. If
   this rule is off, the county gets `high_valyrian` directly.

7. **Adventurer settler MAA is destroyed on title gain.** The
   `on_title_gain_colonization` on-action destroys all `laamp_settler_maa`
   regiments whenever any title is gained. This is intentional -- once landed,
   the adventurer phase ends.

8. **Upkeep events are tier-specific.** Events `.0008` through `.0012` have
   different thresholds for when each modifier tier kicks in. A duke holding 2
   settlements gets `holding_one_settlements` (-5%), while a count holding 2
   gets `holding_two_settlements` (-10%). Do not assume the modifier name maps
   1:1 to settlement count.

9. **The `colonization_cooldown` variable auto-expires.** It is set with
   `years = 2` (or 4 for pirates), so it naturally disappears. Do not manually
   remove it unless you intend to bypass the cooldown.

10. **Conqueror stories have their own colonization logic.** Characters with
    `story_conqueror` skip gold costs and use
    `agot_conqueror_settle_wilderness_effect` which auto-upgrades existing
    settlements and colonizes adjacent wilderness with sophisticated de jure
    scoring. Do not interfere with this flow unless you also modify the
    conqueror story.
