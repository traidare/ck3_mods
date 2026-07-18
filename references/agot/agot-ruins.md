# AGOT: Ruins & Rebuilding

## Overview

AGOT has a dedicated ruin system separate from colonization. Ruins are destroyed
baronies with `ruin_holding` type, held by characters with `ruins_government`.
They generate flavor events for any character who holds ruin baronies, and have
two major location-specific event chains (Moat Cailin and Harrenhal) with unique
rebuilding narratives.

**Source files:**

| Type                  | File                                                                                     |
| --------------------- | ---------------------------------------------------------------------------------------- |
| Ruinize effects       | `common/scripted_effects/00_agot_ruins_effects.txt` (184 lines)                          |
| Rebuilding events     | `events/agot_events/agot_rebuilding_ruins_events.txt` (5178 lines, 41 events)            |
| Ruin buildings        | `common/buildings/00_agot_ruin_buildings.txt`                                            |
| Availability triggers | `common/scripted_triggers/00_agot_available_for_events_triggers.txt`                     |
| On-actions            | `common/on_action/agot_on_actions/agot_filler_events_on_actions.txt`                     |
| Game start setup      | `common/on_action/agot_on_actions/agot_game_start.txt` (initializes ruins at game start) |

## Key Concepts

### Ruin Holding Type

A ruin is a barony province with `holding_type = ruin_holding`. Ruin baronies
get:

- A `medium_ruin_01` building (or `small_ruin_01` / `large_ruin_01` depending on
  the location)
- `ruins_coa` coat of arms
- A generated character with `ruins_government` as holder
- Optional blocker buildings: `ruin_desolate_01`, `ruin_flooded_01`,
  `ruin_infamous_01`, `ruin_renowned_01`

### Ruins Government

Ruin holders use `ruins_government`. This is a pseudo-government — the generated
character exists only to hold the barony. When ruins are colonized or rebuilt,
the title transfers to a real character and government changes.

### Ruinization vs. Colonization

| Aspect       | Ruins                                             | Colonization                                |
| ------------ | ------------------------------------------------- | ------------------------------------------- |
| Holding type | `ruin_holding`                                    | `settlement_holding` / `wilderness_holding` |
| Government   | `ruins_government`                                | Normal                                      |
| Events       | 41 dedicated events                               | Separate colonization events                |
| Who holds it | Generated dummy character                         | Player/AI                                   |
| Rebuild path | Location-specific chains (Moat Cailin, Harrenhal) | Settlement → feudalize pipeline             |
| Source       | `00_agot_ruins_effects.txt`                       | `00_agot_colonization_effects.txt`          |

### The `title:c_ruins` Holder

All ruined counties are transferred to `title:c_ruins.holder` (saved as
`scope:ruins_empress`). This is AGOT's global "ruins container" — the same
`title:c_ruins.holder` pattern used by the dragon tree system as a variable bus.

## Scripted API

### Ruinize Effects (`00_agot_ruins_effects.txt`)

| Effect                      | Scope  | Description                                                                                                                                                                                 |
| --------------------------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `agot_ruin_province_effect` | barony | Converts a single barony to ruin: sets `ruin_holding`, adds `medium_ruin_01`, creates dummy holder with `ruins_government`, transfers Citadel if affected, destroys dragonpit if present    |
| `agot_ruin_county_effect`   | county | Ruins ALL non-capital baronies, then ruins the county capital, transfers county to `title:c_ruins.holder`, sets faith to `fg_unknown`, culture to `unknown_culture`, drops development to 0 |
| `agot_ruinize_title_effect` | any    | Takes `$TITLE$` parameter. Routes to `agot_ruin_county_effect` (county) or `agot_ruin_province_effect` (barony). If ruining a capital barony with other castles, reassigns capital first    |

### Availability Triggers (`00_agot_available_for_events_triggers.txt`)

| Trigger                                   | Description                                                                 |
| ----------------------------------------- | --------------------------------------------------------------------------- |
| `is_available_for_reconstruction_generic` | `age >= 14` AND `is_available = yes`                                        |
| `is_available_for_reconstruction_mc`      | Generic + `rebuilding_moat_cailin` or `started_rebuilding_moat_cailin` flag |
| `is_available_for_reconstruction_hh`      | Generic + `rebuilding_harrenhal` or `started_rebuilding_harrenhal` flag     |

## Events

### Generic Ruin Events (0001–0018)

Fired via `yearly_playable_pulse` on-action for characters holding
`ruin_holding` baronies. Each has a 25-year cooldown flag and equal weight
(100). Night's Watch government is excluded from most.

| Event   | Theme                | Cooldown | Description                                                                                                        |
| ------- | -------------------- | -------- | ------------------------------------------------------------------------------------------------------------------ |
| `.0001` | Charcoal Sellers     | 25y      | Diplomacy duel with peasant; kill, negotiate, or pay 50 gold                                                       |
| `.0002` | Bandits Hideout      | 25y      | Combat encounter; imprison, execute for loot, or recruit                                                           |
| `.0003` | Buried Treasure      | 5y       | Random gold find (5–100 gold)                                                                                      |
| `.0004` | Bandit Attack        | 25y      | Large bandit raid with prowess duel; trait gain chances                                                            |
| `.0005` | Ghost Stories        | 25y      | Knight reports ghosts → chains to .0006/.0007/.0008 (brave/craven/ring outcomes)                                   |
| `.0006` | Brave Night          | —        | Follow-up: good outcome, gain brave trait                                                                          |
| `.0007` | Craven Night         | —        | Follow-up: bad outcome, gain craven trait                                                                          |
| `.0008` | Ring Night           | —        | Follow-up: stressful discovery                                                                                     |
| `.0009` | Blacksmith Cache     | 10y      | Find old forge; sell for 50 gold or pay 50 to craft artifact (sword/mace/spear/dagger/axe)                         |
| `.0010` | A Quick Decision     | 25y      | Stewardship choice; gain hook on vassal or gold                                                                    |
| `.0011` | Options Set in Stone | 25y      | Pay 50 gold for `agot_rebuilding_new_stone` modifier (10y)                                                         |
| `.0012` | In the Details       | 25y      | Gain diligent trait chance or stress relief                                                                        |
| `.0013` | Bronze Slate         | 50y      | Skane-only (c_skane); discover bronze tablet, sell or decipher → .0014/.0015 (faith conversion to `fg_pan_bronze`) |
| `.0016` | Leader by Example    | 25y      | Hardwork; gain prestige modifier, possible content/diligent trait                                                  |
| `.0017` | Curious Visitor      | 25y      | Mysterious visitor chain; can recruit talented courtier or reject                                                  |
| `.0018` | Flower in the Ruins  | 25y      | Discover garden; naming choice, can recruit court poet                                                             |

### Moat Cailin Events (1000–1002)

Triggered by `.1000` handler (hidden event checking
`is_available_for_reconstruction_mc`).

| Event   | Theme           | Description                                                                     |
| ------- | --------------- | ------------------------------------------------------------------------------- |
| `.1000` | Handler         | Hidden dispatcher — 20% nothing, 40% lizard lion, 40% maester reading           |
| `.1001` | Lizard Lions    | Choice: ignore (prestige loss + building delay) or pay 250 gold (prestige gain) |
| `.1002` | Maester Reading | Complex multi-option event about ancient texts                                  |

### Harrenhal Events (2000–2804, 9999)

The largest event chain. Triggered by `.9999` handler which cycles through 7
unique events (each fires once, dedup via flags). Requires
`is_available_for_reconstruction_hh` and
`rebuilding_harrenhal`/`started_rebuilding_harrenhal` flags.

| Event           | Theme                  | Description                                                                                                |
| --------------- | ---------------------- | ---------------------------------------------------------------------------------------------------------- |
| `.2000`         | Curse Decision         | Core event: lift curse (33% chance), accept it, or pay workers 100g. Chains to `.2001`–`.2003`             |
| `.2001`         | Curse Follow-up        | Extended decision with multiple skill checks                                                               |
| `.2002`         | Success                | Curse lifted (sets `restore_harrenhal_curse` global)                                                       |
| `.2003`         | Failure                | Curse persists, construction delayed                                                                       |
| `.2100`         | Physician Consultation | Hidden handler for curse events (requires court physician/maester)                                         |
| `.2200`         | Pyre Revival           | Post-revival event (fire_obsessed trait variant); zealous vs. normal paths, includes burning the structure |
| `.2300`         | Plague Bearer          | Disease outbreak during reconstruction; pay 100g to contain                                                |
| `.2400`         | Heart of Harrenhal     | Atmospheric exploration event with multiple paths; paranoid/brave branching                                |
| `.2401`–`.2402` | Heart Follow-ups       | Deep ruin exploration consequences                                                                         |
| `.2500`         | Foreman                | Construction management decisions                                                                          |
| `.2501`         | Foreman Follow-up      | Worker unrest or progress                                                                                  |
| `.2600`         | The Bard               | Musical visitor at reconstruction site; recruit or dismiss                                                 |
| `.2700`         | The Green Man          | Mysterious green figure; religious/nature encounter                                                        |
| `.2701`         | Green Man Follow-up    | Consequences of meeting                                                                                    |
| `.2800`         | The Vision             | Weirwood vision; faith-dependent descriptions (craven/shy variants)                                        |
| `.2801`–`.2804` | Vision Follow-ups      | Vision consequences and choices                                                                            |
| `.9999`         | Event Handler          | Hidden master dispatcher — cycles through all 7 Harrenhal events, suppresses repeats with flags            |

### Handler Pattern (`.9999`)

```pdx
agot_rebuilding_ruins.9999 = {
    hidden = yes
    trigger = { title:c_harrenhal.holder = { is_available_for_reconstruction_hh = yes } }
    immediate = {
        title:c_harrenhal.holder = {
            if = {
                limit = { NOT = { has_character_flag = pyre_revived } }
                random_list = {
                    1 = {
                        modifier = {
                            trigger = { has_character_flag = had_harren_curse }
                            add = -1  # Won't repeat
                        }
                        trigger_event = agot_rebuilding_ruins.2100
                        add_character_flag = had_harren_curse
                    }
                    1 = {
                        modifier = {
                            trigger = { has_character_flag = had_plague_bearer }
                            add = -1
                        }
                        trigger_event = agot_rebuilding_ruins.2300
                        add_character_flag = had_plague_bearer
                    }
                    # ... 5 more entries, same pattern
                }
            }
        }
    }
}
```

Each event is weighted equally (1) with a `-1` modifier if the flag exists,
preventing repeats. Once all 7 have fired for a character, the handler produces
no new events.

## On-Actions

Generic ruin events are fired from `agot_filler_events_on_actions.txt` under
`yearly_playable_pulse`:

```pdx
# In agot_filler_events_on_actions.txt
agot_filler_ruins_events = {
    random_events = {
        100 = agot_rebuilding_ruins.0001  # Charcoal Sellers
        100 = agot_rebuilding_ruins.0002  # Bandits Hideout
        100 = agot_rebuilding_ruins.0003  # Buried Treasure
        100 = agot_rebuilding_ruins.0004  # Bandit Attack
        100 = agot_rebuilding_ruins.0005  # Ghost Stories
        100 = agot_rebuilding_ruins.0009  # Blacksmith Cache
        100 = agot_rebuilding_ruins.0010  # Quick Decision
        100 = agot_rebuilding_ruins.0011  # Set in Stone
        100 = agot_rebuilding_ruins.0012  # In the Details
        100 = agot_rebuilding_ruins.0013  # Bronze God
        100 = agot_rebuilding_ruins.0016  # Leader by Example
        100 = agot_rebuilding_ruins.0017  # Curious Visitor
        100 = agot_rebuilding_ruins.0018  # Flower in the Ruins
    }
}
```

## Ruin Buildings

Defined in `common/buildings/00_agot_ruin_buildings.txt`. Ruins have size tiers:

| Building         | Meaning                                                |
| ---------------- | ------------------------------------------------------ |
| `small_ruin_01`  | Small ruin (e.g., Hardhome, Skane)                     |
| `medium_ruin_01` | Medium ruin (default from `agot_ruin_province_effect`) |
| `large_ruin_01`  | Large ruin (e.g., Oldstones, Summerhall)               |

Plus blocker/flavor buildings: | Building | Meaning | |----------|---------| |
`ruin_desolate_01` | Desolate — extra hard to rebuild | | `ruin_flooded_01` |
Flooded (e.g., Castamere) | | `ruin_infamous_01` | Infamous reputation (e.g.,
Tarbeck Hall) | | `ruin_renowned_01` | Renowned — historically significant
(e.g., Oldstones, Summerhall) |

## Historical Ruins at Game Start

AGOT sets up ruins at game start in `agot_game_start.txt`. Known ruins include:

| Barony                 | Ruin Size | Special Buildings  |
| ---------------------- | --------- | ------------------ |
| Skane                  | small     | `ruin_desolate_01` |
| Hardhome (×4 baronies) | small     | `ruin_desolate_01` |
| Woodfoot Watch         | small     | —                  |
| Hellgate Hall          | medium    | `ruin_desolate_01` |
| Morne                  | medium    | —                  |
| Castamere              | medium    | `ruin_flooded_01`  |
| Tarbeck Hall           | medium    | `ruin_infamous_01` |
| Oldstones              | large     | `ruin_renowned_01` |
| Summerhall             | large     | `ruin_renowned_01` |
| Hugor's Hill           | large     | `ruin_renowned_01` |
| Shandystone            | small     | `ruin_desolate_01` |
| Hoare Castle           | large     | `ruin_renowned_01` |
| Vulture's Roost        | small     | `ruin_desolate_01` |
| Castle Hollard         | medium    | —                  |

## Sub-Mod Recipes

### Recipe 1: Ruinize a Province via Script

```pdx
# Ruin a single barony
title:b_my_barony = {
    agot_ruin_province_effect = yes
}

# Ruin an entire county (all baronies + county itself)
title:c_my_county = {
    agot_ruin_county_effect = yes
}

# Ruin any title (auto-detects tier)
agot_ruinize_title_effect = { TITLE = title:b_my_barony }
```

### Recipe 2: Add a Location-Specific Rebuilding Chain

Follow the Moat Cailin/Harrenhal pattern:

1. Create an availability trigger:

```pdx
# common/scripted_triggers/99_my_ruin_triggers.txt
is_available_for_reconstruction_my_ruin = {
    is_available_for_reconstruction_generic = yes
    OR = {
        has_character_flag = rebuilding_my_ruin
        has_character_flag = started_rebuilding_my_ruin
    }
}
```

2. Create a handler event:

```pdx
# events/my_ruin_events.txt
namespace = my_ruin_rebuild

my_ruin_rebuild.9999 = {
    hidden = yes
    trigger = { title:c_my_ruin.holder = { is_available_for_reconstruction_my_ruin = yes } }
    immediate = {
        title:c_my_ruin.holder = {
            random_list = {
                1 = {
                    modifier = { trigger = { has_character_flag = had_event_a } add = -1 }
                    trigger_event = my_ruin_rebuild.0001
                    add_character_flag = had_event_a
                }
                # More events...
            }
        }
    }
}
```

3. Hook the handler into an on-action (e.g., `yearly_playable_pulse`).

### Recipe 3: Add a Custom Generic Ruin Event

Hook into the existing filler on-action:

```pdx
# common/on_action/my_on_actions.txt
agot_filler_ruins_events = {
    random_events = {
        100 = my_namespace.0001
    }
}
```

Your event must check for `ruin_holding`:

```pdx
my_namespace.0001 = {
    type = character_event
    trigger = {
        any_held_title = {
            tier = tier_barony
            title_province = { has_holding_type = ruin_holding }
        }
        NOT = { has_character_flag = my_ruin_event_flag }
    }
    immediate = {
        add_character_flag = { flag = my_ruin_event_flag years = 25 }
    }
    # options...
}
```

### Recipe 4: Create a New Ruin at Game Start

Add to an on-action that fires at game start:

```pdx
# common/on_action/my_game_start.txt
on_game_start_after_lobby = {
    effect = {
        title:b_my_location.title_province = {
            set_holding_type = ruin_holding
            add_building = medium_ruin_01
            add_building = ruin_infamous_01  # Optional flavor
        }
        # Transfer to ruins holder
        title:b_my_location = {
            agot_ruin_province_effect = yes
        }
    }
}
```

## Pitfalls

1. **Ruins ≠ colonization.** The ruin system (`ruin_holding`,
   `ruins_government`, ruin events) is completely separate from the colonization
   system (`settlement_holding`, `wilderness_holding`). Don't confuse
   `agot_ruin_province_effect` with `ai_colonization_effect`.

2. **Always use `agot_ruin_province_effect` to create ruins.** Don't just
   `set_holding_type = ruin_holding` — the effect also creates a dummy holder,
   sets CoA, handles Citadel/dragonpit cleanup, and applies `ruins_government`.

3. **`agot_ruin_county_effect` drops development to 0.** It calls
   `change_development_level = -100` and sets faith/culture to unknowns. This is
   intentional for total destruction but may be too aggressive for your sub-mod.

4. **Ruin events exclude Night's Watch.** Most generic ruin events check
   `NOT = { government_has_flag = government_is_nw }`. If your sub-mod changes
   NW government flags, these events may break.

5. **Cooldown flags vary.** Most events use 25-year flags, but `.0003` (Buried
   Treasure) uses 5 years, `.0009` (Blacksmith Cache) uses 10 years, and `.0013`
   (Bronze Slate) uses 50 years. Don't assume uniform cooldowns.

6. **Location-specific events require character flags.** Moat Cailin events
   check `rebuilding_moat_cailin`/`started_rebuilding_moat_cailin` flags.
   Harrenhal checks similar flags. These must be set by the rebuild decision —
   the events won't fire without them.

7. **The Harrenhal handler deduplicates.** `.9999` uses `-1` modifiers to
   suppress repeated events. Once all 7 have fired for a character, no more
   Harrenhal events appear. A new holder gets a fresh set.

8. **`title:c_ruins.holder` is shared.** The ruins container is the same global
   "bus" used by dragon trees. Don't modify this character without understanding
   the ripple effects.

9. **Ruin buildings are not obstacle buildings.** The colonization system's
   `obstacle` flag is separate from ruin buildings. Ruin buildings
   (`small_ruin_01`, etc.) are structural markers, not colonization blockers.

10. **Some events are location-locked.** `.0013` (Bronze Slate) only fires for
    `c_skane` holders. Don't assume all generic events fire everywhere — check
    their triggers.
