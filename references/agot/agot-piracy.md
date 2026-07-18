# AGOT: Piracy

## Overview

AGOT implements a complete piracy system built around the Stepstones and coastal
regions of Planetos. Pirates operate under a dedicated government type
(`pirate_government` or `pirate_no_dlc_government`) with their own holding type
(`pirate_den_holding`), domicile (`agot_pirate_ship`), port tax laws, casus
belli types, and a scheme for raiding rival pirate ships.

Pirates can exist in two forms:

- **Landed pirates** -- rulers who hold `pirate_den_holding` counties under
  pirate government.
- **Landless pirates** -- nomad-style characters with an `agot_pirate_ship`
  domicile (requires Roads to Power + Khans of the Steppe DLCs).

Key source files:

- `common/governments/00_agot_government_types.txt` -- `pirate_government`,
  `pirate_no_dlc_government`
- `common/scripted_effects/00_agot_pirate_effects.txt` -- all pirate scripted
  effects
- `common/scripted_triggers/agot_pirate_triggers.txt` -- pirate-specific
  triggers
- `common/scripted_triggers/00_agot_laamp_triggers.txt` -- landless pirate
  identity triggers
- `common/decisions/agot_decisions/00_agot_pirate_decisions.txt` -- pirate
  decisions
- `common/casus_belli_types/00_agot_pirate_wars.txt` -- pirate CBs
- `common/laws/00_agot_pirate_laws.txt` -- port tax rate laws
- `common/schemes/scheme_types/agot_raid_pirate_domicile_scheme.txt` -- raid
  pirate ship scheme
- `common/story_cycles/agot_landless_pirate_ai_story_cycles.txt` -- AI pirate
  behavior
- `events/agot_government_events/agot_pirate_events.txt` -- pirate event
  namespace

## Key Concepts

### Pirate Lifecycle

A character becomes a pirate through one of several paths:

1. **Wilderness colonization** (`agot_pirate_events.9100`) -- wilderness
   counties in the `historical_pirate_region` spawn new pirate rulers via
   `agot_get_potential_pirate_effect`.
2. **LAAMP-to-pirate decision** (`become_landless_pirate_decision`) -- a
   landless adventurer in the Stepstones with `camp_purpose_brigands` law can
   convert to a pirate ship domicile.
3. **Landed-to-landless decision** (`abandon_pirate_holdings_decision`) -- a
   landed pirate at county/duchy tier with 3 or fewer domain counties can
   abandon holdings and go landless.
4. **Landed-to-pirate decision** (`agot_become_landed_pirate_decision`) -- a
   landed non-pirate ruler whose capital is a `pirate_den_holding` can adopt
   pirate government (costs 1000 prestige, shatters realm).
5. **Pirate adventurer conquest** -- AI pirates spawned by
   `agot_get_potential_pirate_effect` wage wars using
   `pirate_adventurer_conquest` CB.

A pirate can exit the lifestyle via **feudalization**
(`agot_pirate_convert_whole_realm_to_feudalism_effect`), which converts all
`pirate_den_holding` provinces to `castle_holding` and changes government to
`feudal_government` or `lp_feudal_government`.

### Two Government Variants

```
pirate_government = {
    # Full version -- requires Roads to Power + Khans of the Steppe
    primary_holding = pirate_den_holding
    valid_holdings = { pirate_den_holding settlement_holding }
    domicile_type = agot_pirate_ship
    flags = {
        government_is_pirate
        government_is_pirate_trigger_check
        government_can_raid_rule
        agot_unlocks_conquest_cb
        ...
    }
}

pirate_no_dlc_government = {
    # Fallback without landless DLC
    primary_holding = pirate_den_holding
    valid_holdings = { pirate_den_holding }
    flags = {
        government_is_pirate_without_landless_dlc
        government_is_pirate_trigger_check
        government_can_raid_rule
        ...
    }
}
```

The flag `government_is_pirate_trigger_check` is shared by both variants, making
it the safe way to check "is this character a pirate of any kind" in triggers.

### Landless Pirates & the Pirate Ship Domicile

Landless pirates use `agot_pirate_ship` as their domicile type. The domicile
title is marked with `set_variable = is_pirate_domicile` and detected by
`agot_is_pirate_domicile_title_trigger`.

The ship is created via `create_nomad_title` with
`government = pirate_government`. Ships get randomized names:

- 90% chance: `agot_pirate_ship_name_dynamic` (derived from the pirate's
  identity)
- 10% chance: `agot_pirate_ship_name_static`

Ship buildings include the **forecastle** line (`agot_forecastle_01` through
`agot_forecastle_aftcastle_06`), which provides defense against the Raid Pirate
Ship scheme.

### Port Docking & Tax Laws

Landed pirate rulers control port tax rates through the `pirate_haven_port_laws`
law group (file: `common/laws/00_agot_pirate_laws.txt`). Four tiers exist:

| Law              | Key                  | Gameplay Effect                            |
| ---------------- | -------------------- | ------------------------------------------ |
| Rate 1 (default) | `pirate_tax_rate_01` | +10% raid speed, -10% MaA recruitment cost |
| Rate 2           | `pirate_tax_rate_02` | +30% travel speed, reduced sea danger      |
| Rate 3           | `pirate_tax_rate_03` | (intermediate tier)                        |
| Rate 4           | `pirate_tax_rate_04` | Highest fees -- drives away AI pirates     |

Changing tax rates has a 5-year cooldown (`pirate_port_law_cooldown`). AI
pirates evaluate whether to leave a port based on the tax rate and their gold
reserves (see `agot_ai_pirate_wants_to_move` trigger).

When a landless pirate arrives at a port (`agot_pirate_events.0003`), they pay a
one-time docking fee. A yearly recurring fee fires via
`agot_pirate_events.0004`. Pirates can refuse to pay (at the cost of opinion),
use a strong hook to skip payment, or be expelled by the port holder.

### Raiding

Pirates carry the `government_can_raid_rule` flag, enabling vanilla CK3 raiding.
However, the game engine does not allow landless characters to raid directly, so
the AI story cycle (`agot_story_landless_pirate_ai`) provides a gold subsidy of
75-325 gold every 12-14 months to compensate.

## AGOT Scripted API

### Scripted Triggers

Found in `common/scripted_triggers/agot_pirate_triggers.txt` and
`common/scripted_triggers/00_agot_laamp_triggers.txt`:

| Trigger                                                 | Scope     | Purpose                                                                                                                   |
| ------------------------------------------------------- | --------- | ------------------------------------------------------------------------------------------------------------------------- |
| `agot_dlc_check_for_landless_pirates`                   | --        | Returns yes if both `khans_of_the_steppe` and `landless_playable` DLC features are present                                |
| `agot_located_in_traditional_pirate_region_trigger`     | character | True if `location` is in `world_stepstones`                                                                               |
| `agot_is_pirate_domicile_title_trigger`                 | title     | True if title has `is_pirate_domicile` variable                                                                           |
| `agot_is_landless_pirate_character`                     | character | True if `government_is_pirate` flag + `is_landed = no` + `is_ruler = yes` + domicile is `agot_pirate_ship`                |
| `agot_character_is_valid_to_become_landless_pirate`     | character | Validates a character can become a landless pirate (human, adult, not content/craven/lazy, healthy, etc.)                 |
| `agot_potential_pirate`                                 | character | Selects AI characters eligible to become new pirates (prowess > 20, martial > 15, martial education 3+, bold, not clergy) |
| `agot_ai_pirate_wants_to_move`                          | character | Checks if an AI pirate should relocate based on opinion and port tax affordability                                        |
| `agot_pirate_landless_succession_jank_courtier_checker` | character | Validates human courtiers for pirate succession workaround                                                                |
| `agot_landless_pirate_absolute_control_perk_trigger`    | character | Landless pirate + has `absolute_control_perk`                                                                             |

### Scripted Effects

Found in `common/scripted_effects/00_agot_pirate_effects.txt`:

| Effect                                                                | Parameters           | Purpose                                                                                                                                                                                                 |
| --------------------------------------------------------------------- | -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `agot_create_pirate_domicile_effect`                                  | `PIRATE` (character) | Creates a pirate ship domicile via `create_nomad_title`, names the ship, adds opinion penalties to neighbors, creates the `agot_became_pirate` memory, starts `agot_story_landless_pirate_ai` for AI    |
| `agot_pirate_ai_find_next_county_effect`                              | --                   | Finds a neighboring coastal county with `pirate_den_01` building for AI pirate relocation, avoids recently visited dens                                                                                 |
| `agot_pirate_becoming_a_laamp_domicile_destruction_workaround_effect` | --                   | Destroys pirate domicile titles when transitioning to LAAMP                                                                                                                                             |
| `agot_split_pirates_old_realm_effect`                                 | --                   | Splits non-capital titles to newly created pirate characters when adopting pirate government                                                                                                            |
| `agot_get_potential_pirate_effect`                                    | --                   | Finds or creates a character to become a pirate (prefers existing landless pirates, then eligible NPCs weighted by prowess/martial/traits, falls back to generating at `b_the_stash` in the Stepstones) |
| `pirate_adventurer_start_war_effect`                                  | `PIRATE`, `TARGET`   | Initiates a `pirate_adventurer_conquest` war with event troops scaled to 1.5x defender strength (capped at 8000 levies, min 1000), plus `westerosi_sellswords`, `stepstone_sailors`, and `mangonel` MaA |
| `clean_pirate_adventurer_effect`                                      | --                   | Removes temporary titles and `pirate_adventurer_modifier` after war ends                                                                                                                                |
| `add_realm_size_appropriate_pirate_adventurer_reprieve_effect`        | --                   | Grants `proven_against_pirates_modifier` for 5-20 years based on sub_realm_size                                                                                                                         |
| `agot_pirate_convert_whole_realm_to_feudalism_effect`                 | --                   | Converts all `pirate_den_holding` to `castle_holding`, changes government, clears `pirate_succession_law`                                                                                               |

## Decisions & CBs

### Decisions

File: `common/decisions/agot_decisions/00_agot_pirate_decisions.txt`

**`become_landless_pirate_decision`**

- Shown to: landless adventurers with EP3 + MPO DLCs, not in Targaryen exile
  story
- Requires: location in `world_stepstones`, `camp_purpose_brigands` law
- Effect: creates pirate domicile, destroys LAAMP title, fires
  `agot_pirate_events.0100`
- AI score: base -25, modified by `agot_landless_pirate_chance_score_value`

**`abandon_pirate_holdings_decision`**

- Shown to: landed pirates with EP3 + MPO DLCs
- Requires: county-to-duchy tier, domain size <= 3, not at war
- Effect: transfers titles to heir/liege/new character, fires
  `agot_pirate_events.0101`

**`agot_pirate_higher_tier_title_decision`**

- Shown to: landed pirates below empire tier
- Requires: independent, not at war, prestige level thresholds (2/3/4 for
  county/duchy/kingdom)
- Effect: starts a `pirate_domination_cb` war against the de jure liege title
  holder, or creates the title if uncontested
- Cooldown: 10 years

**`agot_become_landed_pirate_decision`**

- Shown to: landed non-pirate rulers whose capital is a `pirate_den_holding`
- Requires: independent, not at war, both landless DLCs
- Cost: 1000 prestige
- Effect: shatters realm (non-capital titles go to new pirate characters via
  `agot_split_pirates_old_realm_effect`), former vassals become tributaries,
  converts holdings to pirate dens

### Casus Belli

File: `common/casus_belli_types/00_agot_pirate_wars.txt`

**`destroy_pirates_cb`**

- Group: `invasion`
- Who can use: non-pirate rulers with coastal counties in Free Cities /
  Stepstones / Dorne / Crownlands / Stormlands
- Target: pirate rulers at duchy+ tier
- On victory: shatters pirate realm (counties become wilderness), kills all
  defenders, grants `proven_against_pirates_offensive_modifier` +
  `agot_disrupted_piracy_modifier` on coastal counties
- On defeat: attacker gets `humiliated_by_pirates` modifier, defender gets
  gold + prestige + `agot_bested_anti_pirate_invaders` county modifier
- White peace: not possible (`white_peace_possible = no`)
- Note: auto-pulls the defender's pirate tributaries into the war

**`pirate_adventurer_conquest`**

- Group: `event` (AI-only, `valid_to_start = always = no`)
- Target: duchy-tier de jure regions
- On victory: conquers titles, converts attacker to pirate government if not
  already, cleans up adventurer
- On defeat: defender gets scaling reprieve via
  `add_realm_size_appropriate_pirate_adventurer_reprieve_effect`
- Attacker death: invalidates war

**`invade_pirate_haven_cb`**

- Who can use: landless pirate government characters
- Target: landed pirate counties with `pirate_den_01` building
- On victory: county conquest (pirate vs pirate)

**`establish_pirate_haven_cb`**

- Who can use: landed pirate government characters
- Target: coastal non-pirate counties with development <=
  `dev_level_to_convert_into_pirate_holding`
- On victory: strips non-capital holdings, converts capital to
  `pirate_den_holding`, reduces development by 4-6
- Cost: 700 prestige (halved for AI)

**`pirate_domination_cb`**

- Group: `event` (fired by `agot_pirate_higher_tier_title_decision`)
- On victory: conquers de jure title, losers become tributaries
- White peace: not possible
- Defender ticking warscore: 0.05

## Events & Story Cycles

### Event Namespace: `agot_pirate_events`

File: `events/agot_government_events/agot_pirate_events.txt`

| Event ID | Type      | Description                                                                                               |
| -------- | --------- | --------------------------------------------------------------------------------------------------------- |
| `0001`   | character | Feudalization notification for the converting ruler                                                       |
| `0002`   | letter    | Feudalization notification for vassals                                                                    |
| `0003`   | character | Arrival at a new port -- pay docking fee, tracks `ports_visited_variable`                                 |
| `0004`   | character | Yearly port fee -- pay, refuse (opinion hit), or use a strong hook; re-fires yearly                       |
| `0100`   | character | Confirmation after LAAMP-to-pirate conversion                                                             |
| `0101`   | character | Confirmation after landed-to-landless pirate conversion; transfers titles to inheritor                    |
| `0200`   | character | Expulsion from a port -- can relocate, refuse (opinion penalty), or renounce piracy and become LAAMP      |
| `0300`   | character | Port holder notified that a pirate refused to pay; option to let it slide or rightfully imprison          |
| `8031`   | hidden    | Raid Pirate Ship scheme resolution -- rolls success/discovery, calculates gold, selects victims/artifacts |
| `8032`   | character | Raid success -- steals gold/artifacts, kills up to 3 courtiers, destroys a ship building                  |
| `8033`   | character | Raid failure -- possible agent capture if discovered                                                      |
| `8034`   | character | Raid target notification (success or failure from target's perspective)                                   |
| `9000`   | character | Pirate succession event (on_death workaround) -- new captain inherits the ship                            |
| `9100`   | hidden    | Wilderness-to-pirate colonization -- spawns pirate in Stepstones wilderness counties                      |
| `9200`   | hidden    | Non-pirate ruler holding pirate land -- forces independence or wilderness reversion                       |
| `9201`   | character | Liege asked to fund vassal's pirate-land conversion (500 gold) or abandon the county                      |
| `9300`   | character | Pirate tributary pulled into a `destroy_pirates_cb` war                                                   |

### Raid Pirate Ship Scheme

File: `common/schemes/scheme_types/agot_raid_pirate_domicile_scheme.txt`

The `agot_raid_pirate_domicile` scheme allows one pirate to raid another
pirate's ship. Key details:

- **Skill:** intrigue
- **Cooldown:** 10 years
- **Category:** political
- **Requirements:** both owner and target must have pirate domicile titles;
  target cannot be the port holder of the owner's location
- **Success rewards:** gold scaled to
  `target.minor_gold_value * num_domicile_buildings`, plus random chance of
  stealing an artifact or bonus gold; up to 3 of the target's courtiers may die
- **Forecastle defense:** target's `agot_forecastle` building line provides -2.5
  to -15 penalty to success chance depending on tier

### AI Story Cycle

File: `common/story_cycles/agot_landless_pirate_ai_story_cycles.txt`

```
agot_story_landless_pirate_ai = {
    # Every 3-12 months: AI pirate checks if it wants to move
    effect_group = {
        months = { 3 12 }
        trigger = { story_owner ?= { is_ai = yes  agot_ai_pirate_wants_to_move = yes ... } }
        triggered_effect = {
            effect = { story_owner = { agot_pirate_ai_find_next_county_effect = yes } }
        }
    }
    # End story if owner becomes human
    effect_group = {
        months = 12
        trigger = { story_owner ?= { is_ai = no } }
        triggered_effect = { effect = { scope:story = { end_story = yes } } }
    }
    # Gold subsidy every 12-14 months (75-325 gold) since landless cannot raid
    effect_group = {
        months = { 12 14 }
        trigger = { story_owner ?= { is_alive = yes  is_ai = yes } }
        triggered_effect = { effect = { story_owner = { add_gold = { 75 325 } } } }
    }
}
```

The AI movement logic avoids recently visited counties (tracked via
`recent_pirate_dens` variable list with 1-year expiry) and only targets coastal
counties with `pirate_den_01` buildings.

## Sub-Mod Recipes

### Recipe 1: Add a New Pirate Region

To make pirates spawn in a new coastal region (e.g., the Summer Islands):

```
# common/scripted_triggers/my_mod_pirate_triggers.txt
# Override to expand where pirates can naturally appear
agot_located_in_traditional_pirate_region_trigger = {
    location = {
        OR = {
            geographical_region = world_stepstones
            geographical_region = world_summer_islands  # your custom region
        }
    }
}
```

You must also ensure your region's wilderness counties fire
`agot_pirate_events.9100` on the yearly pulse. Check
`common/on_action/agot_on_actions/agot_yearly_on_actions.txt` for the existing
trigger and extend its geographical filter.

### Recipe 2: Custom Pirate Adventurer War

To fire a pirate adventurer attack from script (e.g., a story event):

```
# In your event's immediate block:
# 1. Get or create the pirate character
agot_get_potential_pirate_effect = yes

# 2. Pick a target county
scope:potential_pirate = {
    save_scope_as = my_pirate
}
title:c_torturer_s_deep = {
    save_scope_as = my_target
}

# 3. Start the war with event troops
pirate_adventurer_start_war_effect = {
    PIRATE = scope:my_pirate
    TARGET = scope:my_target
}
```

The effect handles domicile creation, army spawning (levies scaled to 1.5x
defender strength, plus `westerosi_sellswords` and `stepstone_sailors` MaA), and
gold loans.

### Recipe 3: Custom Port Tax Interaction

To create a decision that forces a specific tax rate on pirate ports:

```
# common/decisions/my_mod_decisions.txt
force_low_port_taxes_decision = {
    is_shown = {
        government_has_flag = government_is_pirate_trigger_check
        is_landed = yes
        has_realm_law = pirate_tax_rate_04
    }
    is_valid = {
        is_at_war = no
    }
    effect = {
        # Use add_realm_law_skip_effects to change without firing on_pass
        add_realm_law_skip_effects = pirate_tax_rate_01
        # Notify docked pirates manually
        every_held_title = {
            limit = { tier = tier_county }
            every_county_province = {
                every_province_domicile = {
                    limit = { is_domicile_type = agot_pirate_ship }
                    owner = {
                        send_interface_message = {
                            type = msg_pirate_ship_changed_port_rates_taxes
                            title = my_mod_tax_change_title
                            desc = my_mod_tax_change_desc
                        }
                    }
                }
            }
        }
    }
}
```

### Recipe 4: Check if Character is Any Kind of Pirate

```
# Use the shared government flag -- covers both DLC and non-DLC variants:
trigger = {
    government_has_flag = government_is_pirate_trigger_check
}

# For specifically landless pirates only:
trigger = {
    agot_is_landless_pirate_character = yes
}

# For landed pirates only:
trigger = {
    government_has_flag = government_is_pirate_trigger_check
    is_landed = yes
}
```

## Pitfalls

### 1. Always use `government_is_pirate_trigger_check`, not `government_is_pirate`

There are two pirate governments. The flag `government_is_pirate` only exists on
the full DLC variant. If you check `government_has_flag = government_is_pirate`,
you will miss players using `pirate_no_dlc_government`. Always use
`government_is_pirate_trigger_check` to cover both.

### 2. Landless pirates cannot raid via the game engine

CK3 does not support raiding for landless characters at the engine level. AGOT
works around this with a gold subsidy in the AI story cycle. If your sub-mod
adds new raiding mechanics, you must account for this limitation -- landless
pirates need alternative income sources.

### 3. The `agot_is_pirate_domicile_title_trigger` checks a variable, not a title flag

The pirate domicile is identified by `has_variable = is_pirate_domicile` on the
title, not by any built-in CK3 title type. If you create pirate titles through
custom code, you must set this variable or AGOT triggers will not recognize
them.

### 4. Pirate succession uses a death-event workaround

Pirate ship succession does not use standard CK3 succession. Events
`agot_pirate_events.9000` and the `pirate_jank_succession_variable` /
`pirate_deletion` variable system handle it. If you interfere with pirate death
events, you may break ship inheritance.

### 5. Port docking events track visits with a counter variable

The `ports_visited_variable` on the pirate character and the
`ports_visited_scope_value` scope value are used to track docking history. The
`should_pay_pirate_rates` trigger checks this counter matches the expected scope
value. Modifying or resetting this variable can cause pirates to stop paying
fees or pay incorrect amounts.

### 6. The `destroy_pirates_cb` has no white peace

`white_peace_possible = no` means once declared, the war must end in total
victory or defeat. On victory, all defender counties become wilderness and all
defenders die. Plan accordingly if your sub-mod interacts with anti-piracy wars.

### 7. Feudalization destroys all pirate holdings in the realm

`agot_pirate_convert_whole_realm_to_feudalism_effect` converts every
`pirate_den_holding` in the ruler's realm and all vassals below to
`castle_holding`, generating buildings based on `combined_building_level`. It
also clears `pirate_succession_law` from all titles. This is a one-way
operation.

### 8. DLC gating with `agot_dlc_check_for_landless_pirates`

Many pirate features are gated behind both `khans_of_the_steppe` and
`landless_playable` DLC features. Always check
`agot_dlc_check_for_landless_pirates` before using domicile-related effects. The
fallback path creates a dynamic duchy title instead of a nomad domicile.
