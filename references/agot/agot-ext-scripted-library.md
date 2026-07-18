# AGOT Extension: Scripted Effects & Triggers Library

## Overview

AGOT provides **231 scripted_effects files** and **158 scripted_triggers files**
— a massive library of reusable logic that sub-mods should use rather than
reinvent.

This guide catalogs the key public API effects and triggers by system. It covers
naming conventions, file organization, and the most important calls a sub-modder
needs to know.

## How to Find AGOT Scripted API

### File Naming Convention

AGOT effects files follow the pattern:

```
00_agot_{system}_effects.txt
```

AGOT trigger files follow the pattern:

```
00_agot_{system}_triggers.txt
```

Some systems span multiple files (e.g., dragon has ~12 effect files). A few use
alternative prefixes like `agot_` without the `00_` prefix (e.g.,
`agot_pirate_triggers.txt`).

### Search Strategy

1. **By filename**: Search `common/scripted_effects/` and
   `common/scripted_triggers/` for files containing your system keyword (e.g.,
   `dragon`, `knight`, `banking`)
2. **By effect name**: Grep for the effect name pattern — most AGOT effects
   start with `agot_` prefix
3. **By variable/flag names**: If you see a variable like `IB_FreeCapital` in
   events, search scripted_effects to find the initialization and management
   effects

### File Categories at a Glance

**Core AGOT systems** (~130 AGOT-prefixed effect files):

- Dragon (12 files): core, eggs, combat, spawning, slay, warfare, animation,
  appearance, congenital, canon, tree, dragonpit
- Banking (1 file): Iron Bank loans, shares, credit
- Knighthood (2 files): squire system, knight tree
- Night's Watch (2 files): NW membership, BTW (Beyond the Wall)
- Kingsguard (2 files): membership, white book
- Coronation (5 files): coronation, accolades, crown selection, officiant,
  reward
- Colonization (1 file): wilderness, settlements
- Bastard (1 file): surnames, legitimization
- Citadel/Maester (1 file): chain links, archmaesters, grandmaester
- Pirate (1 file): domicile creation, AI behavior
- Appearance (1 file): scripted hair, beard, dye, heterochromia, disfigurement
- Birth (1 file): birth effects pipeline
- Slavery (1 file): slave camps, population, freeing
- Magic (1 file): dragon birth/death magic
- Strong Seed (1 file): genetic trait inheritance
- Mega Wars (1 file): multi-realm civil war system
- Secret Identity (1 file): hidden characters, identity reveal
- Free Cities (1 file): magisterial elections, triarchy
- Small Council (1 file): appointment, repatriation
- Invasion (1 file): scripted invasions
- Scenarios (~18 files): per-bookmark setup effects
- Artifacts (~10 files): VS swords, crowns, armor, court items, maester items

**Vanilla overrides** (~100 files): CK3 base files that AGOT modifies

---

## Effects by System

### Dragon Effects

The dragon system spans 12 effect files with hundreds of individual effects.

**Core dragon lifecycle** (`00_agot_dragon_effects.txt`): | Effect | Description
| |--------|-------------| | `agot_apply_dragon_aging_effect` | Annual dragon
growth — adds prowess and size based on age and dragonpit status. Params:
`$DRAGON$` | | `agot_back_apply_dragon_aging_effect` | One-time application for
dragon creation catch-up growth | | `agot_become_the_dragon` | Transforms a
character into a dragon entity | | `agot_tame_dragon` | Full taming sequence —
sets rider, adds dragonrider trait. Params: `$OWNER$`, `$DRAGON$` | |
`agot_untame_dragon` | Removes taming — frees dragon from rider. Params:
`$OWNER$`, `$DRAGON$` | | `agot_unbond_dragon` | Removes bond relationship only.
Params: `$OWNER$`, `$DRAGON$` | | `agot_bond_dragon_relation_effect` |
Establishes the agot_dragon relation | | `agot_set_as_owned_dragon` | Sets
ownership variables and flags | | `agot_free_dragon` | Called directly on dragon
— releases to wild | | `agot_dragon_flees_province` | Dragon leaves its current
location | | `agot_set_as_rider` | Assigns a rider to a dragon | |
`agot_try_tame_dragon_effect` | Attempt to tame with success/failure outcomes |
| `agot_add_dragon_training_xp` | Adds training XP to a dragon | |
`change_dragon_size` | Modifies dragon size variable. Called on dragon. Params:
`$VALUE$` | | `change_draconic_dread` | Modifies draconic dread value | |
`change_temperament` | Modifies dragon temperament value | |
`change_taming_chance` | Modifies taming chance value | |
`agot_reveal_dragon_gender_effect` | Reveals a dragon's gender | |
`agot_generate_dragon_nick` | Generates a nickname for a dragon | |
`agot_generate_dragon_baby_name` | Names a hatchling | |
`agot_set_dragon_baby_name` | Applies a selected name | |
`agot_give_random_physical_traits` | Random physical trait assignment for
dragons | | `agot_give_random_dragon_personality_trait` | Random personality
trait for dragons | | `agot_dragon_personality_forced_effect` | Force-set a
personality trait on dragon | | `agot_clear_dragon_genetic_traits_effect` |
Removes all genetic traits from a dragon |

**Dragon spawning** (`00_agot_dragon_spawning_effects.txt`): | Effect |
Description | |--------|-------------| |
`agot_spawn_owned_hatchling_from_egg_effect` | Hatches an egg into an owned
hatchling | | `agot_spawn_bonded_hatchling_from_egg_effect` | Hatches an egg
with bond to a character | | `agot_spawn_wild_hatchling_from_egg_effect` |
Hatches an egg as a wild dragon | | `agot_spawn_wild_dragon_effect` | Creates a
wild dragon in the world | | `agot_spawn_wild_child_dragon_effect` | Creates a
wild juvenile dragon | | `agot_spawn_young_dragon_effect` | Creates a young
dragon | | `agot_spawn_adult_dragon_effect` | Creates an adult dragon | |
`agot_spawn_old_dragon_effect` | Creates an old dragon | |
`agot_spawn_monster_dragon_effect` | Creates a massive elder dragon | |
`agot_populate_dragons` | Debug: spawns multiple dragons |

**Dragon eggs** (`00_agot_dragon_eggs_effects.txt`): | Effect | Description |
|--------|-------------| | `agot_create_random_dragon_egg_artifact` | Creates a
random-colored egg artifact | | `agot_create_weighted_dragon_egg_artifact` |
Creates an egg with weighted color selection | |
`agot_create_dragon_egg_from_selection` | Creates an egg of a specific color | |
`agot_spawn_laid_egg` | Dragon lays an egg | |
`create_artifact_dragon_egg_{color}_effect` | Creates a specific color egg
(rainbow, yellow, blue, purple, red, tan, brown, orange, white, pink, black,
gold, whitegold, purplegold, flame, blackred) | |
`agot_create_random_{color}_dragon_egg_artifact` | Creates a random egg within a
color family (white, black, red, orange, yellow, green, blue, purple, pink) |

**Dragon combat** (`00_agot_dragon_combat_effects.txt`): | Effect | Description
| |--------|-------------| | `configure_start_dragon_combat_effect` |
Initializes a dragon vs dragon fight | |
`select_special_dragon_tier_move_effect` | Selects combat moves based on tier |
| `select_dragon_combat_options_from_pool_effect` | Populates combat option pool
| | `finalise_dragon_combat_results_effect` | Resolves dragon combat outcome | |
`wound_dragon` | Inflicts wounds on a dragon | |
`remove_dragon_combat_info_effect` | Cleans up combat data |

**Dragon slay** (`00_agot_dragon_slay_effects.txt`): | Effect | Description |
|--------|-------------| | `agot_burn_effect` | Fire damage to a character | |
`agot_ds_burn_effect` | Dragon siege burn effect | |
`agot_dragon_combat_inflict_wounds_effect` | Combat wound application | |
`agot_increase_wounds_effect` | Escalates wound severity | |
`agot_resolve_wounds_events_effect` | Fires wound resolution events | |
`agot_ds_get_dragon_skill_effect` | Calculates dragon's combat skill | |
`agot_ds_get_human_skill_effect` | Calculates human's combat skill vs dragon | |
`agot_ds_compare_skills_effect` | Compares skills to determine outcome | |
`agot_ds_clean_up_effect` | Cleans up slay combat data |

**Dragon warfare** (`00_agot_dragon_warfare_effects.txt`): | Effect |
Description | |--------|-------------| | `base_dragon_army_modifier_effect` |
Applies dragon army modifiers to battle | | `dragon_combat_modifier_effect` |
Dragon-specific combat modifiers | | `remove_base_dragon_army_modifiers` |
Removes dragon modifiers after battle | | `agot_give_dragon_battle_prowess` |
Gives prowess bonus from dragon in battle | | `dragon_army_modifier_calculation`
| Calculates total army modifier | | `base_dragon_army_scorpions_counter_effect`
| Scorpion counter-dragon effect | | `agot_dragon_damage_county_effect` | Dragon
damages a county (devastation) | |
`agot_dragon_siege_fort_damage_{severity}_effect` | Fort damage (minor, medium,
major, massive) | | `agot_hire_scorpions_effect` | Hires scorpion MaA regiment |

**Dragon tree** (`00_agot_dragon_tree_effects.txt`): | Effect | Description |
|--------|-------------| | `agot_dragon_tree_creation_effect` | Creates the
dragon lineage tree | | `agot_add_to_dragon_tree` | Adds a dragon to the lineage
tree |

**Magic** (`00_agot_magic_effects.txt`): | Effect | Description |
|--------|-------------| | `agot_dragon_birth_magic_effect` | Magical effects
when a dragon is born | | `agot_dragon_death_magic_effect` | Magical effects
when a dragon dies |

---

### Banking Effects

**File:** `00_agot_banking_effects.txt`

The Iron Bank system uses global variables (`IB_FreeCapital`, `IB_NofLoans`,
`IB_NofDefaults`, `IB_LoanedCapital`, `IB_BankValue`, `IB_NofShares`,
`IB_InvestmentFund`) and per-character variables (`IB_Shares`).

| Effect                          | Description                                                               |
| ------------------------------- | ------------------------------------------------------------------------- |
| `agot_init_banking_system`      | Initializes all Iron Bank global variables (free capital starts at 15000) |
| `agot_init_historical_loans`    | Sets up loans for historical characters on game start                     |
| `loan_inheritance`              | Transfers loan obligations to heir on death                               |
| `share_inheritance`             | Transfers bank shares to heir on death                                    |
| `bank_director_election`        | Runs the Iron Bank director election                                      |
| `vassal_loan_inheritance`       | Handles loan inheritance through vassalage                                |
| `agot_credit_score_effect`      | Calculates a character's credit score                                     |
| `historical_loan_on_game_start` | Applies loans during scenario setup                                       |
| `dissolve_conquered_bank`       | Removes a bank when its holding is conquered                              |
| `dissolve_bankrupt_bank`        | Removes a bankrupt bank                                                   |

---

### Knighthood Effects

**Files:** `00_agot_knighthood_effects.txt`, `00_agot_knight_tree_effects.txt`

| Effect                                                | Description                                                                                                                   |
| ----------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| `agot_become_a_knight_effect`                         | Full knighting ceremony — adds trait XP, removes squire relation, notifies family. Params: `$KNIGHT_TO_BE$`, `$KNIGHT_MAKER$` |
| `agot_add_become_a_knight_prestige_effect`            | Prestige and memory for knighting                                                                                             |
| `agot_offer_squire_interaction_effect`                | Initiates squire offer                                                                                                        |
| `agot_offer_knight_tutelage_interaction_effect`       | Initiates knight tutelage offer                                                                                               |
| `agot_set_squire_effect`                              | Establishes the squire relationship                                                                                           |
| `agot_strip_knighthood_as_punishment_effect`          | Removes knight status as punishment                                                                                           |
| `agot_move_knight_for_education_or_squiring_purposes` | Relocates knight for squiring                                                                                                 |
| `agot_init_squire_story_cycle_effect`                 | Starts the squire story cycle                                                                                                 |
| `agot_tournament_reward_knighthood_prize`             | Awards knighthood as tournament prize                                                                                         |
| `agot_add_squire_trait_xp_effect`                     | Adds training XP for squires                                                                                                  |
| `agot_knight_tree_on_start`                           | Initializes the knight lineage tree                                                                                           |
| `agot_add_to_knight_tree`                             | Adds a knight to the lineage tree                                                                                             |
| `agot_add_to_historical_knight_tree`                  | Adds a historical knight entry                                                                                                |

---

### Night's Watch Effects

**Files:** `00_agot_nightswatch_effects.txt`, `00_agot_nw_btw_effects.txt`

| Effect                                      | Description                                                                                                                                                                                                                                   |
| ------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `agot_add_to_nightswatch_effect`            | Full NW induction — untames dragons, removes kingsguard, releases from prison, transfers bank shares to heir                                                                                                                                  |
| `agot_send_to_nightswatch_effect`           | Sends a character to the Night's Watch                                                                                                                                                                                                        |
| `agot_random_nightswatch_death_effect`      | Random death for NW members                                                                                                                                                                                                                   |
| `agot_nightswatch_ruler_on_start_effect`    | Setup for NW rulers at game start                                                                                                                                                                                                             |
| `agot_nightswatch_courtier_on_start_effect` | Setup for NW courtiers at game start                                                                                                                                                                                                          |
| `agot_remove_nightswatch_traits_effect`     | Removes all NW-related traits                                                                                                                                                                                                                 |
| `agot_on_{castle}_court_position_revoked`   | Castle-specific court position revocation (eastwatch, shadowtower, nightfort, icemark, deep_lake, queengate, oakenshield, woodwatch, westwatch, sentinel, greyguard, stonedoor, hoarfrost, stable, rimegate, longbarrow, torches, greenguard) |

---

### Kingsguard Effects

**Files:** `00_agot_kingsguard_effects.txt`,
`00_agot_kingsguard_white_book_effects.txt`

| Effect                                  | Description                                                                                                                                                                 |
| --------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `agot_join_kingsguard_effect`           | Full KG induction — adds trait, blocks leaving, assigns to council slot (kingsguard_1 through kingsguard_6, or kingsguard_lord_commander). Params: `$KINGSGUARD$`, `$KING$` |
| `agot_assign_lord_commander_effect`     | Promotes a KG member to Lord Commander                                                                                                                                      |
| `agot_remove_kingsguard_effect`         | Removes from KG. Params: `$KINGSGUARD$`                                                                                                                                     |
| `agot_on_get_kingsguard`                | Fires when a character joins the KG                                                                                                                                         |
| `agot_on_get_kingsguard_lord_commander` | Fires when appointed LC                                                                                                                                                     |
| `agot_kingsguard_fled_effect`           | Handles a KG member fleeing                                                                                                                                                 |
| `agot_kingsguard_destroy_artifacts`     | Destroys KG-specific artifacts                                                                                                                                              |
| `agot_on_fired_from_kingsguard`         | Fires when dismissed                                                                                                                                                        |
| `agot_on_start_kingsguard_bodyguard`    | Starts bodyguard task                                                                                                                                                       |
| `agot_start_bodyguarding`               | Activates bodyguard behavior                                                                                                                                                |
| `agot_end_kingsguard_effect`            | Ends all KG duties and cleanup                                                                                                                                              |
| `white_book_transfer`                   | Transfers white book to new king                                                                                                                                            |

**White Book** (`00_agot_kingsguard_white_book_effects.txt`): | Effect |
Description | |--------|-------------| |
`agot_kingsguard_create_historical_white_book_page` | Creates a page for a
historical KG member | | `agot_kingsguard_create_dynamic_white_book_page_join` |
Creates a page when a KG member joins | |
`agot_kingsguard_update_white_book_page_lc` | Updates page for LC promotion | |
`agot_kingsguard_update_white_book_page_died_update` | Updates page on KG member
death | | `agot_kingsguard_update_white_book_page_removed_update` | Updates page
on KG member removal | | `agot_kingsguard_init_white_book` | Initializes the
white book system |

---

### Coronation Effects

**Files:** `00_agot_coronation_effects.txt`,
`00_agot_coronation_accolades_scripted_effects.txt`,
`00_agot_coronation_ai_select_crown_effects.txt`,
`00_agot_coronation_reward_effects.txt`,
`00_agot_coronation_select_officiant_effects.txt`,
`00_agot_restore_crown_coronation_effect.txt`

| Effect                               | Description                                                           |
| ------------------------------------ | --------------------------------------------------------------------- |
| `agot_remove_any_uncoronated_effect` | Removes all uncoronated traits, flags, and modifiers from a character |

The coronation system primarily works through the activity system and events.
The effect files handle crown selection AI logic, officiant selection, and
reward distribution. The `00_agot_coronation_effects.txt` file contains only the
cleanup effect above — the bulk of coronation logic lives in the activity and
event files.

---

### Colonization Effects

**File:** `00_agot_colonization_effects.txt`

| Effect                                           | Description                                                                                |
| ------------------------------------------------ | ------------------------------------------------------------------------------------------ |
| `add_random_wilderness_blocker_building`         | Adds random blocker building (bandits, wolf_den, bear_den, dense_growth, flooded_lands)    |
| `make_settlement_county_wilderness`              | Returns a colonized county to wilderness — revokes, resets faith/culture, removes holdings |
| `ai_colonization_effect`                         | AI colonization decision logic                                                             |
| `colonize_pirate_den_effect`                     | Converts a pirate den to a settlement                                                      |
| `pirate_takeover_effect`                         | Pirates take over a county                                                                 |
| `halve_development`                              | Halves county development                                                                  |
| `add_settlement_upkeep_in_history`               | Adds historical settlement upkeep modifier                                                 |
| `release_excess_colony`                          | Releases excess colonies above limit                                                       |
| `agot_upgrade_settlement_to_full_holding_effect` | Upgrades a settlement to a full holding                                                    |
| `agot_increase_settler_maa`                      | Increases settler men-at-arms                                                              |
| `agot_conqueror_settle_wilderness_effect`        | AI conqueror settles wilderness                                                            |

---

### Bastard Effects

**File:** `00_agot_bastard_effects.txt`

| Effect                                             | Description                                                                                                                                         |
| -------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| `agot_add_birthplace_bastard_nickname_effect`      | Assigns regional bastard surname (Snow, Sand, Rivers, Stone, Hill, Flowers, Storm, Waters, Pyke) based on geographic region. Params: `$BIRTHPLACE$` |
| `agot_add_custom_bastard_nickname_effect`          | Assigns a custom bastard surname                                                                                                                    |
| `agot_remove_bastard_nickname_effect`              | Removes bastard surname trait                                                                                                                       |
| `agot_create_bastard_cadet_effect`                 | Creates a cadet branch for a bastard                                                                                                                |
| `agot_legitimize_bastard_effect`                   | Full legitimization — removes bastard trait, updates house                                                                                          |
| `agot_crown_bastard_nickname_effect`               | Handles bastard surname when crowned                                                                                                                |
| `agot_children_of_bastard_surname_effect`          | Applies bastard surnames to children of bastards                                                                                                    |
| `agot_update_noble_bastard_house_and_descendants`  | Updates house for noble bastards and descendants                                                                                                    |
| `agot_update_common_bastard_house_and_descendants` | Updates house for common bastards and descendants                                                                                                   |
| `agot_update_bastard_descendant_effect`            | Propagates house changes to descendants                                                                                                             |

---

### Citadel/Maester Effects

**File:** `00_agot_citadel_effects.txt`

| Effect                                    | Description                                                                                                                                         |
| ----------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| `agot_send_to_citadel_effect`             | Full citadel induction — divorces, breaks betrothals, removes guardians/wards, drops concubines, sets learning focus. Params: `$MAESTER_CANDIDATE$` |
| `send_traveling_maester_to_citadel`       | Sends a traveling maester back to the Citadel                                                                                                       |
| `agot_add_chain_link_effect`              | Adds a single chain link to a maester                                                                                                               |
| `agot_add_chain_link_histories_effect`    | Adds historical chain links                                                                                                                         |
| `agot_complete_chain_effect`              | Completes a maester's chain                                                                                                                         |
| `agot_add_partial_chain_effect`           | Adds a partial chain                                                                                                                                |
| `agot_progress_to_maester_effect`         | Advances an acolyte to full maester                                                                                                                 |
| `agot_progress_to_archmaester_effect`     | Advances a maester to archmaester                                                                                                                   |
| `agot_progress_to_grandmaester_effect`    | Advances to grandmaester                                                                                                                            |
| `agot_seed_archmaesters_effect`           | Seeds archmaester positions                                                                                                                         |
| `agot_grab_new_maester_effect`            | Assigns a new maester to a court                                                                                                                    |
| `agot_seed_maesters_effect`               | Seeds maester positions across the realm                                                                                                            |
| `agot_find_new_grandmaester_effect`       | Selects a new grandmaester                                                                                                                          |
| `agot_seneschal_election_effect`          | Runs Citadel seneschal election                                                                                                                     |
| `agot_expel_maester_effect`               | Expels a maester from service                                                                                                                       |
| `agot_expel_archmaester_effect`           | Expels an archmaester                                                                                                                               |
| `agot_expel_grandmaester_effect`          | Expels the grandmaester                                                                                                                             |
| `agot_remove_maesterhood_effect`          | Fully removes maester status                                                                                                                        |
| `agot_remove_maester_chain_effect`        | Removes chain artifacts                                                                                                                             |
| `agot_random_maester_death_effect`        | Random maester death                                                                                                                                |
| `agot_seed_acolytes_effect`               | Seeds acolyte pool                                                                                                                                  |
| `agot_make_former_acolyte_effect`         | Creates a former acolyte character                                                                                                                  |
| `agot_citadel_transfer_effect`            | Transfers citadel authority                                                                                                                         |
| `agot_citadel_maintenance_effect`         | Periodic citadel maintenance                                                                                                                        |
| `agot_equip_archmaester_artifacts_effect` | Equips archmaester with appropriate artifacts                                                                                                       |

---

### Pirate Effects

**File:** `00_agot_pirate_effects.txt`

| Effect                                                                | Description                                                                                    |
| --------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| `agot_create_pirate_domicile_effect`                                  | Creates a pirate ship domicile with random name, sets up pirate government. Params: `$PIRATE$` |
| `agot_pirate_ai_find_next_county_effect`                              | AI pirate pathfinding for next raid target                                                     |
| `agot_pirate_becoming_a_laamp_domicile_destruction_workaround_effect` | Handles landless adventurer transition                                                         |
| `agot_split_pirates_old_realm_effect`                                 | Splits a pirate's old realm                                                                    |
| `agot_get_potential_pirate_effect`                                    | Finds a suitable pirate candidate                                                              |
| `pirate_adventurer_start_war_effect`                                  | Starts a pirate adventurer war                                                                 |
| `clean_pirate_adventurer_effect`                                      | Cleans up pirate adventurer data                                                               |
| `add_realm_size_appropriate_pirate_adventurer_reprieve_effect`        | Adds raid cooldown based on realm size                                                         |
| `agot_pirate_convert_whole_realm_to_feudalism_effect`                 | Converts pirate realm to feudal                                                                |

---

### Appearance Effects

**File:** `00_agot_appearance_effects.txt` (13,000+ lines)

| Effect                                          | Description                                                          |
| ----------------------------------------------- | -------------------------------------------------------------------- |
| `agot_schedule_scripted_hair_update_effect`     | Schedules a hair change at a specific age. Params: `$HAIR$`, `$AGE$` |
| `agot_update_scripted_hair_effect`              | Applies a scripted hair style                                        |
| `agot_remove_scripted_hair_effect`              | Removes scripted hair flags                                          |
| `agot_scripted_hair_death_effect`               | Cleans up hair flags on death                                        |
| `agot_schedule_scripted_beard_update_effect`    | Schedules a beard change                                             |
| `agot_update_scripted_beard_effect`             | Applies a scripted beard                                             |
| `agot_remove_scripted_beard_effect`             | Removes beard flags                                                  |
| `agot_schedule_scripted_hair_dye_update_effect` | Schedules hair dye change                                            |
| `agot_update_scripted_hair_dye_effect`          | Applies hair dye                                                     |
| `agot_remove_scripted_hair_dye_effect`          | Removes hair dye                                                     |
| `agot_culture_appropiate_hair_dye_effect`       | Sets culturally appropriate hair dye                                 |
| `agot_random_hair_dye_effect`                   | Random hair dye application                                          |
| `agot_remove_heterochromia_eyes_effect`         | Removes heterochromia                                                |
| `agot_inactive_heterochromia_eyes_effect`       | Applies inactive heterochromia                                       |
| `agot_random_one_eyed_fashion_effect`           | Random eye patch or gem for one-eyed characters                      |
| `agot_random_visible_disfigurement_effect`      | Random visible disfigurement                                         |
| `agot_remove_visible_disfigurement_effect`      | Removes disfigurement flags                                          |

---

### Birth Effects

**File:** `00_agot_birth_effects.txt`

| Effect                            | Description                                                                      |
| --------------------------------- | -------------------------------------------------------------------------------- |
| `agot_birth_effects`              | Master birth pipeline — calls all sub-effects in `hidden_effect`                 |
| `agot_birth_dynasty_effect`       | Dynasty-specific birth traits (Umber physique, Valyrian beauty, Borrell mark)    |
| `agot_birth_magic_traits_effect`  | Random magic trait assignment (greensight, dragon dreams — weighted by ancestry) |
| `agot_birth_random_traits_effect` | Random trait assignment at birth                                                 |
| `agot_heir_designation_effect`    | Heir designation logic                                                           |
| `agot_dragon_parent_effect`       | Dragon inheritance from parents                                                  |
| `agot_bittercringe_effect`        | Bitterbridge/cringe special effects                                              |

---

### Slavery Effects

**File:** `00_agot_slavery_base_effects.txt`

| Effect                                  | Description                              |
| --------------------------------------- | ---------------------------------------- |
| `destroy_realm_slave_camps_effect`      | Destroys all slave camps in a realm      |
| `remove_slave_population_effect`        | Removes slave population from a county   |
| `remove_realm_slave_population_effect`  | Removes all slave population realm-wide  |
| `end_realm_slavery_effect`              | Ends slavery in a realm (peacefully)     |
| `forcibly_end_realm_slavery_effect`     | Forces slavery abolition                 |
| `upgrade_slave_population_effect`       | Upgrades slave camp level                |
| `set_random_faith_culture_slave_effect` | Sets random faith/culture for a slave    |
| `sell_into_slavery_opinion_effect`      | Opinion effect when selling into slavery |
| `create_skilled_freed_slave_effect`     | Creates a freed slave with skills        |
| `free_slave_history_effect`             | Records slave freedom in history         |
| `agot_setup_slave_leader_effect`        | Sets up a slave revolt leader            |
| `slave_faction_demands_enforced`        | Enforces slave faction demands           |

---

### General Utility Effects

**File:** `00_agot_effects.txt`

| Effect                                       | Description                                                                         |
| -------------------------------------------- | ----------------------------------------------------------------------------------- |
| `increase_variable`                          | Safe variable increment — initializes to 0 if not set. Params: `$NAME$`, `$AMOUNT$` |
| `decrease_variable`                          | Safe variable decrement. Params: `$NAME$`, `$AMOUNT$`                               |
| `agot_has_historical_claim_effect`           | Grants claim based on dynasty's historical claim to a title. Params: `$TITLE$`      |
| `agot_create_crannogman_ambush`              | Creates crannogman ambush event                                                     |
| `agot_spawn_crannogman_army`                 | Spawns crannogman army. Params: `$TARGET$`                                          |
| `agot_prowess_rank_up_effect`                | Prowess rank-up notification                                                        |
| `agot_become_paramour_effect`                | Establishes paramour relationship                                                   |
| `agot_free_captive_effect`                   | Frees a captive                                                                     |
| `agot_drowned_effect`                        | Ironborn drowning ceremony                                                          |
| `agot_end_wildfire`                          | Ends wildfire event chain                                                           |
| `agot_depose_effect`                         | Deposes a ruler                                                                     |
| `agot_cancel_tourneys_effect`                | Cancels active tournaments                                                          |
| `agot_add_to_silent_sisters_effect`          | Sends a character to the Silent Sisters                                             |
| `agot_send_to_silent_sisters_effect`         | Full silent sister induction                                                        |
| `agot_remove_from_combat`                    | Removes character from combat                                                       |
| `agot_assign_high_septon_effect`             | Assigns a new High Septon                                                           |
| `agot_assign_high_septon_nickname_effect`    | Gives the High Septon a nickname                                                    |
| `agot_duel_effect`                           | Initiates an AGOT-style duel                                                        |
| `agot_add_building_if_possible`              | Safely adds a building if requirements are met                                      |
| `agot_sent_to_essos_effect`                  | Banishes and sends to Essos                                                         |
| `agot_banish_effect`                         | AGOT-specific banishment                                                            |
| `agot_init_legit_level_effect`               | Initializes legitimacy level                                                        |
| `agot_add_random_trait_effect`               | Adds a random personality trait                                                     |
| `agot_add_random_education_effect`           | Adds a random education trait                                                       |
| `agot_house_customizer_spawn_dummies_effect` | Spawns dummy characters for house customization                                     |

---

### Mega Wars Effects

**File:** `00_agot_mega_wars_effects.txt`

| Effect                              | Description                                       |
| ----------------------------------- | ------------------------------------------------- |
| `agot_mw_scenario_rebel_setup`      | Sets up the rebel side of a mega war              |
| `agot_mw_scenario_crown_setup`      | Sets up the crown/loyalist side                   |
| `agot_mw_add_character_to_mw_list`  | Adds a character to the mega war participant list |
| `agot_mw_join_loyalists_effect`     | Character joins the loyalist side                 |
| `agot_mw_stay_neutral_effect`       | Character stays neutral                           |
| `agot_mw_join_rebels_effect`        | Character joins the rebel side                    |
| `agot_mw_start_mid_war_effect`      | Starts a mega war mid-game                        |
| `agot_assign_temp_vassalage_effect` | Assigns temporary vassalage during war            |
| `agot_mw_change_vassalage`          | Changes vassalage during mega war resolution      |
| `agot_mw_become_independent`        | Character becomes independent post-war            |

---

### Secret Identity Effects

**File:** `00_agot_secret_identity_effects.txt`

| Effect                                        | Description                                     |
| --------------------------------------------- | ----------------------------------------------- |
| `agot_end_secret_identity_effect`             | Reveals a hidden identity                       |
| `agot_swap_secret_child_bodies`               | Swaps two children's identities                 |
| `agot_move_secret_child`                      | Moves a secret child to a new court             |
| `secret_flee_effect`                          | Character flees in secret                       |
| `agot_get_secret_claims_generic_effect`       | Grants claims based on secret identity          |
| `agot_get_secret_claims_on_title_gain_effect` | Claims granted on title gain                    |
| `agot_secret_child_start_war_effect`          | Secret child starts a war for their claim       |
| `agot_events_after_identity_reveal`           | Fires events after identity is revealed         |
| `agot_create_secret_character_army_effect`    | Creates an army for a revealed secret character |
| `agot_secret_identity_adventure_effect`       | Starts an adventure for a secret character      |

---

### Strong Seed Effects

**File:** `00_agot_strong_seed_effects.txt`

| Effect                                         | Description                             |
| ---------------------------------------------- | --------------------------------------- |
| `agot_assign_strong_seed_effect`               | Master strong seed application at birth |
| `agot_assign_strong_seed_traits_effect`        | Assigns all strong seed traits          |
| `agot_assign_strong_seed_eyes_traits_effect`   | Eye color inheritance                   |
| `agot_assign_strong_seed_hair_traits_effect`   | Hair color inheritance                  |
| `agot_assign_strong_seed_height_traits_effect` | Height inheritance                      |
| `agot_assign_strong_seed_ears_traits_effect`   | Ear shape inheritance                   |
| `agot_assign_strong_seed_eyes_effect`          | Actual eye color application            |
| `agot_assign_strong_seed_hair_effect`          | Actual hair color application           |

---

### Other Notable Effect Files

| File                                    | Key Effects                                                                                                              |
| --------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| `00_agot_free_city_effects.txt`         | `check_for_free_city_election`, `magisterial_succession`, `create_triarchy`, `agot_free_city_setup_effect`               |
| `00_agot_small_council_effects.txt`     | `fire_small_councillor`, `small_councillor_appointment_effect`, `small_councillor_vassal_repatriation_effect`            |
| `00_agot_invasion_scripted_effects.txt` | `agot_invasions_move_to_new_court`, `agot_invasions_remove_story_modifiers`, `agot_invaders_dragonstone_transfer_effect` |
| `00_agot_death_effects.txt`             | `agot_apply_inactive_traits_on_death`                                                                                    |
| `00_agot_education_effects.txt`         | `agot_add_coming_of_age_martial_prowess_flag_effect`, `agot_coming_of_age_education_flags_to_traits`                     |
| `00_agot_reaving_effects.txt`           | `agot_viking_points_gain_effect`, `agot_viking_rank_up_check_effect`                                                     |
| `00_agot_wildling_effects.txt`          | `agot_setup_beyond_the_wall`, `agot_update_wildling_resistance`, `agot_generate_duchy_tribe`                             |
| `00_agot_esr_effects.txt`               | Extended succession/realm effects                                                                                        |
| `00_agot_culture_effects.txt`           | Culture assignment and conversion                                                                                        |
| `00_agot_religion_effects.txt`          | Religion-specific effects                                                                                                |
| `00_agot_dynasty_effects.txt`           | Dynasty management                                                                                                       |
| `00_agot_cadet_effects.txt`             | Cadet branch creation                                                                                                    |
| `00_agot_legitimate_house_effects.txt`  | House legitimization                                                                                                     |
| `00_agot_personal_coas_effects.txt`     | Personal coat of arms                                                                                                    |
| `00_agot_execution_effects.txt`         | AGOT execution methods                                                                                                   |
| `00_agot_multi_duel_effects.txt`        | Multi-combatant duels                                                                                                    |

---

## Triggers by System

### Dragon Triggers

**Files:** `00_agot_dragon_triggers.txt`, `00_agot_dragon_size_triggers.txt`,
`00_agot_dragon_trait_inheritance_triggers.txt`,
`00_agot_canon_dragons_triggers.txt`, `00_agot_canon_dragons_trait_triggers.txt`

| Trigger                                              | Scope              | Description                                                                                                 |
| ---------------------------------------------------- | ------------------ | ----------------------------------------------------------------------------------------------------------- |
| `is_current_dragonrider`                             | character          | TRUE if alive, not incapable, not imprisoned, has dragonrider trait, has living dragon not homed separately |
| `is_current_dragonrider_warfare`                     | character          | Above + age >= 14 and not flagged as not using dragon                                                       |
| `dragon_homed_separate_from_rider`                   | character          | TRUE if dragon is in a dragonpit away from rider's capital. Params: `$DRAGON$`                              |
| `can_be_warrior_trigger_no_dragon`                   | character          | Can fight as knight excluding dragon-based eligibility. Params: `$ARMY_OWNER$`                              |
| `can_start_dragon_combat_trigger`                    | character          | Full eligibility check for dragon combat                                                                    |
| `can_start_dragon_combat_eligibility_checks_trigger` | character          | Basic eligibility (adult, dragonrider, etc.)                                                                |
| `can_start_dragon_combat_banned_checks_trigger`      | character          | Checks for combat bans                                                                                      |
| `agot_can_use_dragonpit_amenities`                   | character          | Can use dragonpit facilities                                                                                |
| `agot_has_an_active_dragonpit`                       | character          | Has at least one active dragonpit                                                                           |
| `agot_has_multiple_active_dragonpits`                | character          | Has more than one active dragonpit                                                                          |
| `agot_title_is_an_active_dragonpit`                  | title              | Title is a functioning dragonpit                                                                            |
| `has_dragonmont_dragonpit`                           | character          | Has the Dragonstone dragonpit                                                                               |
| `has_any_dragonpits`                                 | character          | Has any dragonpit buildings                                                                                 |
| `allow_naming_of_dragon_trigger`                     | character          | Can name their dragon                                                                                       |
| `can_dragon_chomp`                                   | character          | Dragon can eat someone                                                                                      |
| `is_historical_dragon`                               | character          | Is a canon dragon from lore                                                                                 |
| `has_stationed_scorpions`                            | title              | Province has anti-dragon scorpions                                                                          |
| `agot_has_dragonblood_culture`                       | culture            | Culture has dragon blood                                                                                    |
| `agot_is_dragonblood_character`                      | character          | Character has dragon blood                                                                                  |
| `agot_has_dragonblood_heritage`                      | culture            | Culture heritage includes dragon blood                                                                      |
| `agot_has_relationship_dragon`                       | character          | Has an agot_dragon relation                                                                                 |
| `can_use_bond_with_dragon_scheme`                    | character          | Can start dragon bonding scheme                                                                             |
| `can_use_deepen_bond_with_dragon_scheme`             | character          | Can deepen existing dragon bond                                                                             |
| `dragon_can_do_terror_campaign`                      | character (dragon) | Dragon can terrorize a province                                                                             |
| `agot_dragon_population_low`                         | —                  | Global dragon population is low                                                                             |
| `agot_dragon_population_extinct`                     | —                  | No dragons alive                                                                                            |
| `agot_dragon_population_alive`                       | —                  | At least one dragon alive                                                                                   |
| `agot_cannot_use_dragon_egg`                         | character          | Cannot use/hatch a dragon egg                                                                               |
| `agot_has_dragonpit_requirements_trigger`            | —                  | Meets dragonpit construction requirements                                                                   |
| `level_{N}_dragon_size_trigger`                      | character (dragon) | Dragon is at size level N (1-10)                                                                            |

---

### Banking Triggers

Banking logic primarily uses scripted*values and variable checks rather than
dedicated trigger files. Check `00_agot_banking_effects.txt` for inline
conditions using `IB*` global variables.

---

### Knighthood Triggers

**File:** `00_agot_knighting_triggers.txt`

| Trigger                                         | Scope     | Description                                                                                                                                                |
| ----------------------------------------------- | --------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `agot_has_traits_preventing_knighthood_trigger` | character | Has any disqualifying trait (blind, dwarf, clubfooted, one_legged, one_handed, incapable, infirm, physique_bad, crippled, already knight, septon, maester) |
| `is_eligible_for_agot_squirehood_trigger`       | character | Age 9-22, male (or female tomboy with high prowess), no disqualifying traits, not already squire                                                           |
| `has_past_experience_with_squirehood`           | character | Was previously a squire                                                                                                                                    |
| `is_agot_knight_trigger`                        | character | Has knight trait OR squire track at 100 with no ongoing story                                                                                              |
| `is_squire_with_trait_xp`                       | character | Currently a squire with active training                                                                                                                    |

---

### Night's Watch Triggers

**File:** `00_agot_nights_watch_triggers.txt`

| Trigger                               | Scope     | Description                                                                                                                 |
| ------------------------------------- | --------- | --------------------------------------------------------------------------------------------------------------------------- |
| `agot_valid_potential_nw_member`      | character | Male (basic gender check)                                                                                                   |
| `agot_reasonable_potential_nw_member` | character | Male, adult, physically fit, unmarried, unbetrothed, human                                                                  |
| `agot_is_member_of_nights_watch`      | character | Has nightswatch, nightswatch_temp, or nightswatch_historical trait                                                          |
| `agot_nw_can_banish`                  | —         | Banisher is Westerosi non-wildling with capital in Seven Kingdoms; banishee is eligible. Params: `$BANISHER$`, `$BANISHEE$` |
| `agot_nw_physically_unfit`            | character | Has any disqualifying physical trait                                                                                        |
| `agot_nw_is_pruneable_trigger`        | character | NW member can be safely pruned from the game (no important connections)                                                     |

---

### Kingsguard Triggers

**File:** `00_agot_kingsguard_triggers.txt`

| Trigger                                      | Scope     | Description                                                                                                                            |
| -------------------------------------------- | --------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| `title_has_kingsguard_trigger`               | title     | Empire+ tier title with kingsguard variable                                                                                            |
| `ruler_has_kingsguard_trigger`               | character | Holds a title with KG                                                                                                                  |
| `ruler_primary_title_has_kingsguard_trigger` | character | Primary title has KG                                                                                                                   |
| `can_be_kingsguard_trigger`                  | character | Full eligibility — capable adult, not ruler (unless already KG), unmarried, no blocking traits, can be knight. Params: `$COURT_OWNER$` |
| `valid_kingsguard_gender_trigger`            | character | Male only                                                                                                                              |
| `highborn_kingsguard_candidate`              | character | Highborn, martial education, not heir, not betrothed                                                                                   |
| `can_have_kingsguard`                        | character | Primary title supports KG                                                                                                              |

---

### Coronation Triggers

**File:** `00_agot_coronation_triggers.txt`

| Trigger                                     | Scope     | Description                                                         |
| ------------------------------------------- | --------- | ------------------------------------------------------------------- |
| `agot_ruler_requires_coronation`            | character | Kingdom+ tier, independent, landed, feudal                          |
| `agot_is_coronated_trigger`                 | character | Has been coronated (checks trait/flag/law based on DLC)             |
| `agot_is_uncoronated_trigger`               | character | Has NOT been coronated                                              |
| `agot_has_any_uncoronated_trigger`          | character | Has any uncoronated indicator (trait, flag, or modifier)            |
| `agot_uses_agot_coronations_trigger`        | character | Uses AGOT coronation system (no coronation DLC)                     |
| `is_valid_coronation_special_guest_trigger` | character | Alive, human, not at war, not imprisoned                            |
| `needs_crown_for_coronation_trigger`        | character | Has a helmet-slot artifact (crown)                                  |
| `iron_throne_valid_trigger`                 | character | Holds the Iron Throne holy title                                    |
| `activity_agot_coronation_is_valid_guest`   | character | Age 3+, not at war, not in army, not imprisoned, no active activity |

---

### Colonization Triggers

**File:** `00_agot_colonization_triggers.txt`

| Trigger                                 | Scope     | Description                                                            |
| --------------------------------------- | --------- | ---------------------------------------------------------------------- |
| `above_settlement_limit`                | character | Holds more settlements than allowed by tier                            |
| `agot_at_settlement_limit`              | character | At exactly the settlement limit                                        |
| `not_settlement_or_wilderness`          | title     | Province is neither settlement nor wilderness                          |
| `region_is_colonized_and_controlled_by` | —         | Region is fully colonized and controlled. Params: `$TITLE$`, `$RULER$` |
| `region_is_colonized`                   | —         | Region is fully colonized. Params: `$TITLE$`                           |

---

### Maester Triggers

**File:** `00_agot_maester_triggers.txt`

| Trigger                                | Scope     | Description                              |
| -------------------------------------- | --------- | ---------------------------------------- |
| `agot_maester_culture_trigger`         | character | Has a culture that trains maesters       |
| `agot_is_maester_candidate`            | character | Eligible to become a maester             |
| `agot_is_maester`                      | character | Is a maester                             |
| `agot_any_maester_in_citadel`          | —         | Any maester present in the Citadel       |
| `agot_is_archmaester_candidate`        | character | Eligible for archmaester promotion       |
| `agot_is_field_qualified`              | character | Qualified in a specific field of study   |
| `agot_is_field_qualified_lesser`       | character | Lesser qualification in a field          |
| `maester_available_trigger`            | character | Available for maester assignment         |
| `can_be_maester_of`                    | character | Can serve as maester of a specific court |
| `can_punish_maester`                   | character | Can punish their maester                 |
| `maester_can_fail_on_purpose_trigger`  | character | Maester can intentionally fail           |
| `agot_can_be_expelled_maester_trigger` | character | Can be expelled from maesterhood         |

---

### Pirate Triggers

**File:** `agot_pirate_triggers.txt`

| Trigger                                                 | Scope     | Description                        |
| ------------------------------------------------------- | --------- | ---------------------------------- |
| `agot_located_in_traditional_pirate_region_trigger`     | character | In a traditional pirate region     |
| `agot_is_pirate_domicile_title_trigger`                 | title     | Title is a pirate ship domicile    |
| `agot_pirate_landless_succession_jank_courtier_checker` | character | Workaround for landless succession |
| `agot_landless_pirate_absolute_control_perk_trigger`    | character | Pirate has absolute control perk   |
| `agot_ai_pirate_wants_to_move`                          | character | AI pirate wants to relocate        |
| `agot_potential_pirate`                                 | character | Character could become a pirate    |

---

### Bastard Triggers

**File:** `00_agot_bastard_triggers.txt`

| Trigger                                | Scope     | Description                          |
| -------------------------------------- | --------- | ------------------------------------ |
| `real_paternal_held_iron_throne_claim` | character | Real father held Iron Throne claim   |
| `knows_self_royal_bastard_secret`      | character | Knows own royal bastard secret       |
| `knows_other_royal_bastard_secret`     | character | Knows another's royal bastard secret |
| `agot_royal_bastard_should_give_up`    | character | Royal bastard should abandon claim   |
| `agot_bastard_surname_trigger`         | character | Has a bastard surname trait          |

---

### General Triggers

**File:** `00_agot_triggers.txt`

| Trigger                                        | Scope     | Description                              |
| ---------------------------------------------- | --------- | ---------------------------------------- |
| `agot_is_independent_ruler`                    | character | Is truly independent (not vanilla check) |
| `agot_wall_is_normal`                          | —         | The Wall is intact                       |
| `agot_wall_has_fallen_left`                    | —         | Left section of Wall has fallen          |
| `agot_wall_has_fallen_middle`                  | —         | Middle section has fallen                |
| `agot_wall_has_fallen_right`                   | —         | Right section has fallen                 |
| `agot_has_historical_events_trigger`           | —         | Historical events are enabled            |
| `agot_has_any_shattered_rule_trigger`          | —         | Any shattered realm rule is active       |
| `agot_has_throne_room`                         | character | Has a throne room                        |
| `agot_death_can_start_feud_trigger`            | character | Death can trigger a feud                 |
| `agot_can_form_lord_paramountcy`               | character | Can form a lord paramountcy              |
| `agot_flavour_is_in_westeros_trigger`          | character | Is in Westeros                           |
| `agot_flavour_capital_is_in_westerosi_trigger` | character | Capital is in Westeros                   |
| `agot_flavour_iron_throne_exists_trigger`      | —         | Iron Throne title exists                 |
| `agot_flavour_is_lord_in_westeros_trigger`     | character | Is a lord in Westeros                    |
| `agot_flavour_is_prince_dragonstone_trigger`   | character | Is Prince of Dragonstone                 |

---

### Other Notable Trigger Files

| File                                | Key Triggers                                                                                                                                                                                                  |
| ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `00_agot_blood_triggers.txt`        | `has_paramountblood`, `has_dukesblood`, `has_countsblood`                                                                                                                                                     |
| `00_agot_character_triggers.txt`    | `agot_is_dummy_character`, `agot_is_available_for_anything`, `agot_boring_character_trigger`, `agot_exceptionalism_incest_allowed`, `worthy_sword_of_the_morning_trigger`                                     |
| `00_agot_government_triggers.txt`   | `agot_is_valid_paramountcy_realm`, `agot_is_valid_pirate_government_target`, `agot_is_valid_free_city_government_target`, `agot_is_a_republic`                                                                |
| `00_agot_title_triggers.txt`        | `agot_is_historical_free_city`, `agot_is_a_republic_title`, `agot_is_de_jure_nights_watch_title`, `agot_kingdom_tier_is_real_kingdom_trigger`, `agot_can_create_duchy_title`, `agot_can_create_kingdom_title` |
| `00_agot_magic_triggers.txt`        | `agot_dragon_dream_scheme_discovery_trigger`, `agot_greensight_scheme_discovery_trigger`, `agot_prevent_harm_event_with_foresight_trigger`                                                                    |
| `00_agot_slavery_base_triggers.txt` | `agot_can_upgrade_slave_camps_trigger`, `agot_can_upgrade_slave_population_trigger`, `agot_has_slave_population_trigger`                                                                                      |
| `00_agot_war_triggers.txt`          | `agot_pentos_braavos_treaty_prohibited_war_declaration_trigger`, `agot_generic_war_blocks_trigger`                                                                                                            |
| `00_agot_strong_seed_triggers.txt`  | Strong seed genetic inheritance checks                                                                                                                                                                        |
| `00_agot_appearance_triggers.txt`   | Appearance-related checks                                                                                                                                                                                     |
| `00_agot_building_triggers.txt`     | Building requirement overrides                                                                                                                                                                                |
| `00_agot_cultural_triggers.txt`     | Culture checks (e.g., `agot_is_wildling_culture`)                                                                                                                                                             |
| `00_agot_religious_triggers.txt`    | Religion-specific checks                                                                                                                                                                                      |
| `00_agot_sea_triggers.txt`          | Sea/coastal terrain checks                                                                                                                                                                                    |
| `00_agot_terrain_type_triggers.txt` | AGOT terrain type checks (e.g., `agot_is_glacier_terrain`, `agot_is_frozen_flats_terrain`, `agot_is_forest_terrain`)                                                                                          |
| `00_agot_faceless_triggers.txt`     | Faceless Men checks                                                                                                                                                                                           |
| `00_agot_spy_network_triggers.txt`  | Spy network checks                                                                                                                                                                                            |

---

## Sub-Mod Best Practices

### Always Search Before Writing Custom Logic

Before writing any scripted effect or trigger, search AGOT's library:

1. Check filenames in `common/scripted_effects/` and `common/scripted_triggers/`
   for your system keyword
2. Grep for the action you want (e.g., "knighthood", "dragon", "bastard")
3. Read the top-level effect names in the relevant file

### Use AGOT Effects Instead of Reimplementing

**Bad** — reinventing bastard surname logic:

```pdx
# DON'T DO THIS
if = {
    limit = { location = { geographical_region = world_westeros_the_north } }
    make_trait_inactive = surname_snow
}
```

**Good** — use the existing effect:

```pdx
agot_add_birthplace_bastard_nickname_effect = { BIRTHPLACE = root.location }
```

**Bad** — manually adding to NW:

```pdx
# DON'T DO THIS
add_trait = nightswatch
add_character_flag = blocked_from_leaving
```

**Good** — use the full effect that handles dragons, KG, shares, etc.:

```pdx
agot_add_to_nightswatch_effect = yes
```

### File Naming Conventions for Sub-Mods

- Prefix your files with your mod identifier: `99_mymod_dragon_effects.txt`
- Use high load order numbers (90+) to load after AGOT
- Never overwrite AGOT files — add new files instead
- If you must patch an AGOT effect, copy the entire effect to your file with a
  higher load order number (the last-loaded definition wins for same-named
  effects)

### Leverage Compound Effects

Many AGOT effects are pipelines that call multiple sub-effects. For example,
`agot_add_to_nightswatch_effect` handles:

- Dragon untaming
- Kingsguard removal
- Prison release
- Faith piety bonus
- Loan/share inheritance
- Title management
- Trait assignment

Calling the compound effect ensures all edge cases are handled.

---

## Pitfalls

### 1. Scope Mismatches

Many AGOT effects expect specific scopes or parameters. `agot_tame_dragon`
expects `$OWNER$` and `$DRAGON$` as character scopes. Passing a title or wrong
character will fail silently.

### 2. Effects with Side Effects

`agot_add_to_nightswatch_effect` untames dragons, removes kingsguard, and
transfers bank shares. If you only want to add the NW trait, you might not want
all those side effects — but skipping them creates inconsistent state. Prefer
the full effect.

### 3. Variable Initialization

The banking system requires `agot_init_banking_system` to have run. If you
access `IB_FreeCapital` before initialization, it won't exist. Check with
`exists = global_var:IB_FreeCapital`.

### 4. Load Order for Effect Overrides

If two files define the same effect name, the last-loaded file wins. AGOT uses
`00_` prefix. Using `99_` ensures your override loads last. But be cautious:
AGOT updates may change the original effect, making your override stale.

### 5. Inline vs API Effects

Some AGOT logic is inline in events rather than exposed as scripted effects. If
you can't find an effect for something AGOT does, check the event files
directly. Key event namespaces: `agot_dragon`, `agot_knighthood`,
`agot_coronation`, `agot_banking`.

### 6. Dragon Scope Confusion

Dragons are characters in AGOT. Effects like `change_dragon_size` must be called
ON the dragon character, not on the rider. The rider's dragon is accessed via
`var:current_dragon` or `any_relation = { type = agot_dragon }`.

### 7. Kingsguard Council Slots

The KG uses council positions `kingsguard_lord_commander`, `kingsguard_1`
through `kingsguard_6`. These are checked via `exists = cp:kingsguard_1`. The
`agot_join_kingsguard_effect` automatically finds the first empty slot.

### 8. Coronation DLC Compatibility

AGOT has two coronation code paths — one for when the coronation DLC is present,
and one without it. The trigger `agot_uses_agot_coronations_trigger` returns yes
when the DLC is NOT present. Always use `agot_is_coronated_trigger` and
`agot_is_uncoronated_trigger` rather than checking traits/laws directly.
