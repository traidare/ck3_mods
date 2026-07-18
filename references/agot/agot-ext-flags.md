# AGOT Extension: Flags

> This guide extends [references/patterns/flags.md](../patterns/flags.md) with
> AGOT-specific changes.

## What AGOT Changes

AGOT makes massive use of the flag system:

- **266+ unique `agot_` character flags** across events — used for cooldowns,
  state tracking, scenario logic, and system gating
- **52 government flags** — AGOT adds ~30 custom government flags beyond vanilla
  for its unique government types (Night's Watch, piracy, ruins, Free Cities,
  etc.)
- **Heavy use of `government_has_flag` over `has_government`** — AGOT follows
  Paradox's own recommendation; sub-mods should do the same
- **Character flags as the primary inter-system communication** — dragons,
  knighthood, kingsguard, coronation, and other systems all use character flags
  to track state

## AGOT Government Flags

AGOT defines ~20 unique government types, each with multiple flags. The most
important for sub-modders:

### AGOT-Unique Government Flags

| Flag                                 | Governments                                     | Meaning                                                                                |
| ------------------------------------ | ----------------------------------------------- | -------------------------------------------------------------------------------------- |
| `government_is_nw`                   | `nights_watch_government`                       | Night's Watch — blocks marriage, inheritance, most interactions                        |
| `government_is_kg`                   | `kingsguard_government`                         | Kingsguard — similar blocks to NW                                                      |
| `government_is_pirate`               | `pirate_government`, `pirate_no_dlc_government` | Pirate government — enables pirate mechanics                                           |
| `government_is_pirate_trigger_check` | both pirate governments                         | Used in building/decision checks — always check this, not `government_is_pirate` alone |
| `government_is_free_city`            | `free_city_government`                          | Free Cities (Braavos, Pentos, etc.)                                                    |
| `government_is_ruins`                | `ruins_government`                              | Ruined holdings — dummy government                                                     |
| `government_is_wilderness`           | `wilderness_government`                         | Wilderness holdings                                                                    |
| `government_is_unknown`              | `unknown_government`                            | Placeholder                                                                            |
| `government_is_uninteractable`       | various                                         | Blocks most character interactions                                                     |
| `government_is_silent_sisters`       | `silent_sisters_government`                     | Silent Sisters order                                                                   |
| `government_is_the_citadel`          | `citadel_government`                            | The Citadel (maesters)                                                                 |
| `government_is_first_ranger`         | `first_ranger_government`                       | First Ranger (NW variant)                                                              |
| `government_is_lp_feudal`            | `lp_feudal_government`                          | Lord Paramount feudal (paramountcy system)                                             |
| `government_is_default`              | most playable governments                       | Shared flag — gates lifestyle perks and standard gameplay                              |

### Vanilla Flags AGOT Reuses

| Flag                           | Meaning                                                |
| ------------------------------ | ------------------------------------------------------ |
| `government_is_feudal`         | Standard feudal — many AGOT governments also have this |
| `government_is_clan`           | Clan government (used for Dothraki, etc.)              |
| `government_is_tribal`         | Tribal (wildlings, some Essos groups)                  |
| `government_is_republic`       | Republic government                                    |
| `government_is_theocracy`      | Theocratic government                                  |
| `government_is_administrative` | Administrative government                              |
| `government_is_nomadic`        | Nomadic government                                     |
| `government_is_mercenary`      | Mercenary company                                      |
| `government_is_holy_order`     | Holy order                                             |
| `government_is_settled`        | Settled (has holdings)                                 |

### The `government_is_default` Pattern

AGOT uses `government_is_default` as a universal flag for "this is a normal
playable government." Most AGOT governments that players can play have this
flag. It gates access to vanilla lifestyle perks and standard interactions.

**Sub-mod rule:** If you create a new government type that should have standard
gameplay features, include `government_is_default` in its flags.

```pdx
my_custom_government = {
    # ...
    flags = {
        government_is_default       # Access to lifestyle perks
        government_is_feudal        # Treated as feudal for most checks
        government_is_settled       # Has holdings
    }
}
```

## AGOT Character Flag Conventions

AGOT uses the `agot_` prefix for all character flags. They fall into these
categories:

### Cooldown Flags

Prevent events from firing repeatedly. Standard pattern with timed duration:

```pdx
# Typical AGOT event cooldown
immediate = {
    add_character_flag = {
        flag = agot_ruins_event_charcoal
        years = 25
    }
}
trigger = {
    NOT = { has_character_flag = agot_ruins_event_charcoal }
}
```

Common durations: 5 years (minor events), 10 years (medium), 25 years (major),
50 years (rare).

### State Tracking Flags

Track ongoing processes — set permanently, removed when complete:

```pdx
# Rebuilding state
add_character_flag = rebuilding_moat_cailin
add_character_flag = started_rebuilding_moat_cailin

# Coronation state
add_character_flag = agot_is_being_coronated

# Dragon bonding
add_character_flag = agot_had_dragon_bond
```

### System Gating Flags

Used by AGOT systems to gate interactions and events:

| Flag pattern                 | System     | Purpose                              |
| ---------------------------- | ---------- | ------------------------------------ |
| `agot_had_dragon_bond`       | Dragons    | Tracks past bond                     |
| `agot_is_being_coronated`    | Coronation | Prevents duplicate ceremonies        |
| `agot_closed_pits`           | Dragonpit  | Tracks dragonpit state               |
| `agot_claimant_king`         | Mega wars  | Marks rebel leader                   |
| `agot_currently_being_fired` | Kingsguard | Prevents interaction race conditions |
| `blocked_from_leaving`       | NW/KG      | Prevents departure during events     |

### Scenario Flags

Used for bookmark-specific logic:

```pdx
has_character_flag = agot_admiral_won_second_war
has_character_flag = agot_corlys_had_first_win_event
has_character_flag = agot_choose_three_daughters_capital
```

### Dragon-Related Flags

Heavily used for dragon animations and state:

| Flag                                 | Purpose                              |
| ------------------------------------ | ------------------------------------ |
| `dragon_idle`                        | Dragon portrait animation            |
| `dragon_flying`                      | Dragon flying animation              |
| `dragon_roar`                        | Dragon roar animation                |
| `dragon_hover`                       | Dragon hover animation               |
| `agot_chose_adult_dragon_custom`     | Character designer dragon age choice |
| `agot_chose_hatchling_dragon_custom` | Character designer dragon age choice |
| `agot_child_asked_to_ride_dragon`    | Event gating                         |
| `agot_burned_in_dragon_hatching`     | Hatching outcome                     |
| `agot_dead_in_dragon_hatching`       | Hatching outcome                     |

## AGOT Building Flags

AGOT buildings use definition flags for categorization:

| Flag                                      | Purpose                           | Example buildings          |
| ----------------------------------------- | --------------------------------- | -------------------------- |
| `castle`                                  | Castle-type building              | Castle tiers               |
| `travel_point_of_interest_martial`        | Travel system integration         | Red Keep, Winterfell, etc. |
| `travel_point_of_interest_religious`      | Travel system integration         | Great Sept, Starry Sept    |
| `holy_building`                           | Holy site building                | Sept, godswood buildings   |
| `special_building_enabled_in_ruin_county` | Works in ruin counties            | Some special buildings     |
| `obstacle`                                | Blocks colonization feudalization | Ruin blocker buildings     |

## Sub-Mod Recipes

### Recipe 1: Check Government Type the AGOT Way

```pdx
# WRONG — only matches one specific government
trigger = {
    has_government = nights_watch_government
}

# RIGHT — matches any government with the NW flag
trigger = {
    government_has_flag = government_is_nw
}
```

### Recipe 2: Add a Character Flag Cooldown

```pdx
# Standard AGOT pattern: 25-year cooldown
immediate = {
    add_character_flag = {
        flag = mymod_had_special_event
        years = 25
    }
}

trigger = {
    NOT = { has_character_flag = mymod_had_special_event }
}
```

### Recipe 3: Create a Government with Proper Flags

```pdx
my_agot_government = {
    # ...
    flags = {
        government_is_default           # Standard gameplay access
        government_is_feudal            # Feudal category
        government_is_settled           # Has holdings
        # Add your custom flags:
        government_is_my_custom_type    # Your own flag for gating
    }
}
```

### Recipe 4: Track State Across Systems with Flags

```pdx
# Set state in one system
agot_start_my_process_effect = {
    add_character_flag = mymod_process_active
}

# Check from another system
trigger = {
    has_character_flag = mymod_process_active
    NOT = { government_has_flag = government_is_nw }  # Exclude NW
}

# Clean up
agot_end_my_process_effect = {
    remove_character_flag = mymod_process_active
}
```

## AGOT Pitfalls

1. **Always use `government_has_flag`, not `has_government`.** AGOT has 20+
   governments. Checking by flag covers multiple governments (e.g., both pirate
   variants). AGOT code consistently uses flags.

2. **Check `government_is_pirate_trigger_check`, not `government_is_pirate`.**
   The DLC and non-DLC pirate governments have different names but both share
   `government_is_pirate_trigger_check`. Buildings and decisions should use this
   flag.

3. **Don't forget NW/KG exclusions.** Many AGOT events exclude Night's Watch and
   Kingsguard: `NOT = { government_has_flag = government_is_nw }`. Your sub-mod
   events should do the same when appropriate.

4. **Use the `agot_` prefix for your flags.** Actually no — use YOUR OWN prefix
   (`mymod_`). The `agot_` prefix is reserved for the AGOT team. Using it risks
   collisions when AGOT updates.

5. **AGOT cooldown durations vary.** Don't assume all cooldowns are 25 years.
   Check the original event's cooldown before writing a sub-mod event that hooks
   into the same on-action.

6. **Dragon animation flags are not `agot_` prefixed.** The 4 dragon animation
   flags (`dragon_idle`, `dragon_flying`, `dragon_roar`, `dragon_hover`) don't
   have the `agot_` prefix — they're set by the animation system directly.

7. **The `government_is_default` flag is critical.** Without it, characters in
   your custom government won't have access to lifestyle perks. AGOT uses this
   flag on all playable governments.

8. **Scenario flags are bookmark-specific.** Flags like
   `agot_admiral_won_second_war` only make sense in specific bookmarks. Don't
   check them in generic events.

9. **`government_is_uninteractable` blocks everything.** If you set this flag on
   your government, characters with it cannot be targeted by most interactions.
   Used for ruins, wilderness, and placeholder governments.

10. **Flag names are case-sensitive.** `agot_My_Flag` and `agot_my_flag` are
    different flags. AGOT consistently uses lowercase with underscores.
