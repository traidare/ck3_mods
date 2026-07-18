# AGOT Extension: On Actions

## Overview

AGOT uses the CK3 on_action system extensively. On actions are hooks that fire
when specific game events occur (title gain, death, war start, birthday, etc.).
Because CK3 merges all `on_action` files additively, AGOT can extend vanilla
on_actions without replacing them -- it simply redeclares the same on_action
name in its own files and adds new `on_actions` or `events` entries.

AGOT places its on_action files in two locations:

- **`common/on_action/`** -- files like `title_on_actions.txt`, `death.txt`,
  `war_on_actions.txt` that redeclare vanilla on_action names and inject
  AGOT-specific sub-actions.
- **`common/on_action/agot_on_actions/`** -- a dedicated subdirectory containing
  ~55 AGOT-specific on_action files. These define custom on_actions as well as
  further vanilla extensions.

AGOT also sets a global variable `AGOT_is_loaded` at game start, which sub-mods
can check to confirm AGOT is active.

## What AGOT Changes

AGOT's on_action modifications fall into three categories:

1. **Vanilla on_action extensions** -- AGOT redeclares vanilla on_actions (e.g.,
   `on_title_gain`, `on_death`, `on_war_started`) and adds AGOT sub-actions into
   their `on_actions = { }` or `events = { }` blocks.
2. **AGOT-specific on_actions** -- Custom on*actions prefixed with
   `agot*`that form chains called from the vanilla extensions (e.g.,`agot_on_title_gain`, `agot_on_game_start`).
3. **AGOT custom lifecycle on_actions** -- Entirely new on_actions for
   AGOT-specific systems like dragons, the Night's Watch, the Citadel, Silent
   Sisters, mega wars, Free Cities, and the "Life More Feudal" (LMF) module.

## AGOT-Specific On Actions

### Title System (`agot_title_on_actions.txt`)

The title system is the most extensive. AGOT chains `on_title_gain` into
`agot_on_title_gain`, which then dispatches to ~20 specialized sub-actions:

| On Action                                      | Purpose                                                           |
| ---------------------------------------------- | ----------------------------------------------------------------- |
| `agot_on_title_gain`                           | Master dispatcher for all AGOT title-gain logic                   |
| `agot_on_title_gain_iron_throne`               | Handles Iron Throne succession (dragon eggs, small council, etc.) |
| `agot_on_title_gain_nightswatch`               | Night's Watch title processing                                    |
| `agot_on_title_gain_silent_sister`             | Silent Sisterhood title processing                                |
| `agot_on_title_gain_citadel`                   | Citadel (maester) title processing                                |
| `agot_on_title_gain_goldcloaks`                | Gold Cloaks commander assignment                                  |
| `agot_on_title_gain_high_septon`               | High Septon succession                                            |
| `agot_on_title_gain_kingsguard`                | Kingsguard member processing                                      |
| `agot_on_title_gain_high_valyrian`             | High Valyrian title logic                                         |
| `agot_on_title_gain_wildfire`                  | Wildfire-related title events                                     |
| `agot_on_title_gain_ruins`                     | Ruins management on title gain                                    |
| `agot_on_title_gain_unique_crown`              | Unique crown artifact assignment                                  |
| `agot_on_title_gain_inheritance`               | Inheritance-specific title logic                                  |
| `agot_on_title_gain_usurpation`                | Usurpation-specific title logic                                   |
| `agot_on_title_gain_moat_cailin`               | Moat Cailin special handling                                      |
| `agot_on_title_gain_free_city_attached_titles` | Free City attached title management                               |
| `agot_on_title_gain_crownlands_inheritance`    | Crownlands inheritance rules                                      |
| `agot_on_title_gain_mega_wars_action`          | Mega war title transfer logic                                     |
| `agot_on_title_lost_iron_throne`               | Iron Throne loss handling                                         |
| `agot_on_title_lost_nightswatch`               | Night's Watch title loss                                          |
| `agot_on_title_lost_dragonpit`                 | Dragonpit title loss                                              |
| `agot_on_title_throne_management`              | General throne management                                         |
| `agot_on_rank_up`                              | Rank-up logic                                                     |
| `agot_on_explicit_claim_gain`                  | Explicit claim gain handling                                      |

### Game Start (`agot_game_start.txt`)

```
on_game_start = {
    on_actions = {
        agot_remove_realms
        agot_on_game_start
        agot_house_dna
        agot_set_legacies
        agot_vassal_contracts
        agot_crown_authority
        agot_dummy_rulers
        agot_artifacts_sell
        agot_qohorik_weaponsmith_pulse
        agot_pirate_domiciles_setup
        agot_traditional_coronation_setup
    }
}
```

`agot_on_game_start` is the master initialization action. It sets
`AGOT_is_loaded`, initializes banking, Free Cities, tributaries, character
setup, and scenario-specific logic. A second action
`agot_on_game_start_after_lobby` runs after the lobby.

### War System (`agot_war_on_actions.txt`)

AGOT extends every major war on_action:

| Vanilla On Action          | AGOT Sub-Actions Added                                                                                                                                                                          |
| -------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `on_join_war_as_secondary` | `agot_on_join_war_as_secondary_action`                                                                                                                                                          |
| `on_war_started`           | `loyalist_faction_action`, `agot_mega_war_action`, `agot_dynamic_claimant_kings_start`, `tenet_ritual_wars_check`, `agot_pirate_domiciles_join_war`, `agot_dragonrider_forced_duel_story_start` |
| `on_war_won_attacker`      | `agot_kingsguard_employer_lost`, `agot_dynamic_claimant_kings_end`, `agot_spoils_demands`, `agot_war_won_attacker_on_action`, `agot_succession_war_house_head_change`                           |
| `on_war_won_defender`      | `agot_dynamic_claimant_kings_end`, `agot_war_won_defender_on_action`                                                                                                                            |
| `on_war_white_peace`       | `agot_dynamic_claimant_kings_end`, `agot_war_white_peace_on_action`                                                                                                                             |
| `on_war_invalidated`       | `agot_dynamic_claimant_kings_end`, `agot_war_invalidated_on_action`                                                                                                                             |

### Death System (`agot_death.txt`)

```
on_death = {
    events = {
        agot_small_council.0002
        agot_kingsguard.1000
        agot_widowed_events.999
        agot_valyrian_steel.0003
        agot_valyrian_steel.9000
        agot_dragonstone.0006
        agot_dragon.0001
        agot_dragon_death.0002
    }
    on_actions = {
        agot_dummy_char_death_on_action
        agot_after_death_on_action
        nw_ranger_death
        nw_ranger_history_on_lc_death
        agot_mw_death_on_action
        agot_landless_pirate_domicile_transfer
        agot_landless_pirate_succession_variable_manager
        agot_secret_hidden_artifact_on_action
    }
}
```

### Artifact System (`agot_artifact_on_actions.txt`)

Custom on_actions for AGOT's artifact market:

- `agot_on_artifact_bought` -- Fires when an artifact is purchased from the AGOT
  artifact keeper
- `agot_on_artifact_created_by_merchant` -- Fires when the merchant creates a
  new artifact
- `agot_on_artifact_destroyed_by_merchant` -- Fires when the merchant destroys
  an artifact
- `agot_on_merchant_added_gold` -- Fires when gold is added to the merchant

### Yearly Pulse (`agot_yearly_on_actions.txt`)

```
yearly_global_pulse = {
    on_actions = {
        agot_assign_slave_master
        agot_artifact_market_management
        agot_jon_snow_learns
        agot_citadel_yearly_pulse
        agot_king_is_dying
        agot_legitimate_house_maintenance
        agot_faegon_invasion
        agot_banking
        agot_dragonrider_forced_duel_list_yearly
        agot_grant_kingdom_titles
    }
}
```

### Other Major AGOT On Action Systems

- **Dragon system**: `agot_dragon_cradling_on_action.txt`,
  `agot_dragon_travel_on_actions.txt`, dragon relation on_actions
- **Night's Watch**: `agot_wall_on_actions.txt` (election, succession,
  maintenance, wall breach chance)
- **Citadel**: `agot_citadel_on_actions.txt`
- **Silent Sisters**: `agot_silent_sisters_on_actions.txt`
- **Free Cities**: `agot_free_city_on_actions.txt` (term limits, elections)
- **Colonization**: `agot_colonization_on_actions.txt`
- **Life More Feudal (LMF)**: `agot_lmf_on_actions.txt` and related files
  (childbirth, heir training, schemes, lover story cycles)
- **Relations**: `relations/` subfolder with on_actions for bodyguard, dragon,
  paramour, squire, and pirate ship heir relations
- **ESR (Extended Scripted Relations)**: `agot_esr_on_actions.txt` hooks into
  all vanilla relation set/remove/death on_actions

## Vanilla On Actions AGOT Extends

AGOT extends these vanilla on_actions by redeclaring them in its files:

### Core Lifecycle

- `on_game_start` -- AGOT initialization chain
- `on_game_start_after_lobby` -- Post-lobby setup
- `on_death` -- Dragon cleanup, Valyrian steel inheritance, Kingsguard, Night's
  Watch, dummy rulers
- `on_birthday` -- LMF checks, knight events
- `on_16th_birthday` -- Knight events, `agot_on_16th_birthday`

### Title & Realm

- `on_title_gain` -- Pentos treaty, shattered kingdoms, massive AGOT title gain
  chain
- `on_title_gain_inheritance` -- AGOT inheritance logic, unique banners
- `on_title_gain_usurpation` -- Usurpation-specific actions
- `on_title_lost` -- Pentos treaty, small council cleanup, mega wars
- `on_title_destroyed` -- Pentos treaty, mega wars
- `on_vassal_gained` -- Pentos treaty, ESR tooltips
- `on_vassal_change` -- Pentos treaty independence check
- `on_rank_up` / `on_rank_down` -- ESR updates, `agot_on_rank_up`
- `on_explicit_claim_gain` -- `agot_on_explicit_claim_gain`

### War

- `on_war_started`, `on_war_won_attacker`, `on_war_won_defender`,
  `on_war_white_peace`, `on_war_invalidated`, `on_war_transferred`
- `on_join_war_as_secondary`

### Relations

- `on_set_relation_*`, `on_remove_relation_*`, `on_death_relation_*` for friend,
  best_friend, rival, nemesis, lover, soulmate, and AGOT-custom relations
  (bodyguard, dragon, paramour, squire, pirate_ship_designated_heir,
  story_dragon)

### Marriage & Family

- `on_marriage` -- LMF, ESR, concubinage events
- `on_divorce` -- ESR, LMF
- `on_concubinage` -- AGOT marriage events
- `on_betrothal_broken` -- AGOT marriage events
- `on_pregnancy_mother`, `on_birth_mother`, `on_birth_child` -- LMF childbirth

### Military

- `on_siege_completion` -- AGOT siege events (Gulltown, Starpike, bank
  locations)
- `on_raid_action_completion` -- AGOT raid events
- `on_army_enter_province` -- Bottleneck terrain (The Neck)
- `on_army_monthly` -- LMF army events
- `on_combat_end_winner` -- Knight events

### Other

- `on_artifact_changed_owner` -- Blackfyre bastard dynasty formation
- `on_character_culture_change`, `on_character_faith_change` -- Culture/faith
  AGOT logic
- `on_culture_created` -- AGOT culture descriptions
- `on_county_culture_change` -- BTW (Beyond the Wall) maintenance
- `on_release_from_prison` -- ESR, RV (Royal Vassals) events
- `on_imprison` -- LMF events
- `on_prestige_level_gain` / `on_prestige_level_loss` -- AGOT prestige events
- `on_government_change` -- AGOT government change logic
- `on_domicile_building_started` / `on_domicile_building_completed` /
  `on_domicile_building_cancelled` -- Colonization
- `on_travel_plan_start` / `on_travel_plan_complete` / `on_travel_plan_arrival`
  / `on_travel_plan_movement` -- AGOT travel and colonization
- `yearly_playable_pulse` -- AGOT maintenance, AI character pulse
- `yearly_global_pulse` -- Artifact market, banking, Citadel, Jon Snow, Faegon
  invasion

## AGOT-Specific Template

To hook into AGOT on_actions from a sub-mod, you have two options:

### Option 1: Hook into an existing AGOT on_action

Redeclare the AGOT on_action and add your sub-action. CK3 merges additively.

```
# my_submod/common/on_action/my_submod_on_actions.txt

# Hook into AGOT's title gain chain
agot_on_title_gain_iron_throne = {
    on_actions = {
        my_submod_iron_throne_action
    }
}

my_submod_iron_throne_action = {
    trigger = {
        # Check AGOT is loaded
        has_global_variable = AGOT_is_loaded
    }
    effect = {
        # Your logic when someone gains the Iron Throne
    }
}
```

### Option 2: Hook into a vanilla on_action alongside AGOT

```
# my_submod/common/on_action/my_submod_on_actions.txt

# Hook into vanilla on_death -- your additions merge with AGOT's
on_death = {
    on_actions = {
        my_submod_death_cleanup
    }
}

my_submod_death_cleanup = {
    trigger = {
        has_global_variable = AGOT_is_loaded
        # Your conditions
    }
    effect = {
        # Your cleanup logic
    }
}
```

### Option 3: Hook into game start with AGOT detection

```
# my_submod/common/on_action/my_submod_game_start.txt

on_game_start = {
    on_actions = {
        my_submod_init
    }
}

my_submod_init = {
    effect = {
        if = {
            limit = { has_global_variable = AGOT_is_loaded }
            # AGOT-specific initialization
        }
    }
}
```

## Annotated AGOT Example

This example shows AGOT's chaining pattern -- how a vanilla on_action cascades
through AGOT-specific sub-actions. The war system demonstrates this clearly:

```
# File: agot_on_actions/agot_war_on_actions.txt

# Step 1: Extend the vanilla on_action by redeclaring it.
# CK3 merges this with the vanilla definition and any other mods.
on_war_started = {
    on_actions = {
        loyalist_faction_action          # AGOT loyalist faction logic
        agot_mega_war_action             # AGOT mega war system
        agot_dynamic_claimant_kings_start # Dynamic claimant kings
        tenet_ritual_wars_check          # Ritual wars check
        agot_pirate_domiciles_join_war   # Pirate domicile war joining
        agot_dragonrider_forced_duel_story_start # Dragon duel story
    }
}

# Step 2: Each sub-action uses a trigger to gate its logic.
# This is the standard AGOT pattern -- the sub-action only fires
# when its specific conditions are met.

# (Defined elsewhere in AGOT source)
# agot_mega_war_action = {
#     trigger = {
#         # Only fires for specific war types
#         agot_is_mega_war_trigger = yes
#     }
#     effect = {
#         # Mega war initialization
#     }
# }
```

The title system uses a deeper chain:

```
# File: title_on_actions.txt (AGOT's override of vanilla)

# Vanilla on_title_gain gets AGOT additions
on_title_gain = {
    # ... vanilla events still fire ...
    on_actions = {
        agot_on_title_gain                    # Master AGOT dispatcher
        agot_on_title_gain_iron_throne        # Iron Throne specific
        agot_on_title_gain_nightswatch        # Night's Watch specific
        agot_on_title_gain_silent_sister      # Silent Sisters specific
        agot_on_title_gain_citadel            # Citadel specific
        agot_on_title_gain_goldcloaks         # Gold Cloaks specific
        # ... ~15 more specialized sub-actions ...
    }
}

# Each specialized sub-action has its own trigger gate:
# agot_on_title_gain_nightswatch = {
#     trigger = {
#         scope:title = { agot_is_nights_watch_title = yes }
#     }
#     effect = { ... }
# }
```

## AGOT Pitfalls

1. **Do not replace AGOT on_action files.** AGOT's `common/on_action/` files
   (like `title_on_actions.txt`, `death.txt`) are full replacements of vanilla
   files. If your sub-mod also replaces these files, one will overwrite the
   other. Instead, create your own file with a unique name and redeclare the
   on_action -- CK3 merges additively across files.

2. **Load order matters for file-level replacements.** AGOT's top-level files
   like `title_on_actions.txt` and `death.txt` replace vanilla entirely. If your
   sub-mod needs to modify these, you must either load after AGOT and include
   all AGOT content, or (preferred) put your additions in a separate file.

3. **AGOT uses a dispatch pattern.** Many vanilla on*actions dispatch to a
   single
   `agot_on*\*`master action, which then calls specialized sub-actions. If you hook into the vanilla on_action directly, your code runs in parallel with the entire AGOT chain. If you hook into a specific AGOT sub-action (e.g.,`agot_on_title_gain_iron_throne`),
   you get finer control but depend on AGOT's internal structure.

4. **Check `has_global_variable = AGOT_is_loaded`** in your on_actions if your
   sub-mod should also work without AGOT. This variable is set in
   `agot_on_game_start`.

5. **Trigger gates are critical.** AGOT sub-actions use `trigger = { }` blocks
   to ensure they only fire in appropriate contexts. Always add triggers to your
   on_actions to avoid running logic in unintended situations (e.g., a Night's
   Watch-specific action firing for a normal title gain).

6. **The `agot_on_actions/` subdirectory is AGOT-only.** Files inside this
   folder define AGOT's custom on_actions. Your sub-mod should not place files
   here -- use your own folder or the top-level `common/on_action/` path.

7. **Multiple files can extend the same on_action.** AGOT itself extends
   `on_death` from at least 5 different files (`agot_death.txt`,
   `agot_nw_petition_on_action.txt`, `agot_rv_on_actions.txt`,
   `agot_wall_on_actions.txt`, `agot_silent_sisters_on_actions.txt`,
   `agot_lmf_on_actions.txt`, `agot_ub_on_actions.txt`,
   `agot_esr_on_actions.txt`). CK3 merges all of them. Your sub-mod can do the
   same.

8. **Events vs. on_actions in the block.** On_action definitions can contain
   both `events = { }` (direct event IDs) and `on_actions = { }` (references to
   other on_actions). AGOT uses both: direct events for simple reactions, and
   on_action references for complex chains with their own triggers.
