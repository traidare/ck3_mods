# AGOT Extension: Decisions

> This guide extends
> [references/patterns/decisions.md](../patterns/decisions.md) with
> AGOT-specific changes.

## What AGOT Changes

AGOT overhauls the decision system in several ways:

1. **New decision group types** -- AGOT adds custom `decision_group_type` values
   beyond vanilla's `major`: `appearance`, `artifact`, `banking`, `religion`,
   `adventurer`, `adventurer_minor`. These control how decisions are categorized
   in the UI.
2. **Hegemony tier in `ai_check_interval_by_tier`** -- AGOT adds a `hegemony`
   tier (the Iron Throne). Every `ai_check_interval_by_tier` block must include
   all 6 tiers: `barony`, `county`, `duchy`, `kingdom`, `empire`, `hegemony`.
3. **Custom government checks** -- AGOT replaces vanilla `is_independent_ruler`
   with `agot_is_independent_ruler` (a scripted trigger) and uses
   `government_has_flag` extensively to gate decisions by government type
   (`government_is_nw`, `government_is_feudal`, `government_is_lp_feudal`,
   `government_is_tribal`, `government_is_free_city`, `government_is_pirate`,
   `government_is_wilderness`, `government_is_first_ranger`,
   `government_is_landless_adventurer`, `government_is_uninteractable`).
4. **AGOT geographical regions** -- Decisions use AGOT-specific regions like
   `world_westeros_seven_kingdoms`, `world_westeros_beyond_the_wall`,
   `world_westeros_dorne`, `world_westeros_the_north`, etc.
5. **Global variable lists for one-time decisions** -- AGOT uses
   `unavailable_unique_decisions` as a global variable list to track decisions
   that should only fire once across the entire game (e.g.,
   `recover_brightroar_decision`).
6. **AGOT-specific title references** -- Many decisions check for AGOT titles
   like `title:h_the_iron_throne`, `title:k_the_wall`, `title:e_the_crownlands`,
   etc.
7. **Game rule awareness** -- Some decisions check `has_game_rule` for
   AGOT-specific game rules (e.g.,
   `agot_story_historical_events_historical_outcomes`, `agot_silly_mode`,
   `matrilineal_marriages_never`).
8. **`ai_value_modifier` blocks** -- AGOT decisions use `ai_value_modifier`
   inside `ai_will_do` to weight AI behavior by personality traits like
   `ai_greed`, `ai_compassion`, `ai_boldness`, `ai_honor`, `ai_zeal`.
9. **Dragon system integration** -- Many decisions interact with the dragon
   system via `has_trait = dragonrider`,
   `any_relation = { type = agot_dragon }`, global lists like `living_dragons`,
   and custom scripted triggers like `is_current_dragonrider`.
10. **35+ AGOT decision files** in `common/decisions/agot_decisions/`, organized
    by theme.

## AGOT Decision Categories

AGOT decisions are organized into thematic files in
`common/decisions/agot_decisions/`:

| File                                       | Theme                    | Examples                                                                                                            |
| ------------------------------------------ | ------------------------ | ------------------------------------------------------------------------------------------------------------------- |
| `00_agot_iron_throne_decisions.txt`        | Iron Throne politics     | `agot_proclaim_iron_throne`, `set_capital_kingslanding_decision`, `build_dune_road_decision`                        |
| `00_agot_dragon_decisions.txt`             | Dragon management        | `become_dragonrider_house_decision`, `ride_dragon_decision`, `conduct_terror_campaign`, `bind_dragon_horn_decision` |
| `00_agot_valyrian_steel_decisions.txt`     | Valyrian steel artifacts | `reforge_valyrian_steel_decision`, `recover_brightroar_decision`                                                    |
| `00_agot_bastard_decisions.txt`            | Parentage and heritage   | `agot_expose_true_parentage_decision`                                                                               |
| `00_agot_nw_decisions.txt`                 | Night's Watch            | `restore_the_nights_watch`, `dissolve_the_nights_watch`                                                             |
| `00_agot_kingsguard_decisions.txt`         | Kingsguard               | `agot_view_white_book`                                                                                              |
| `00_agot_minor_decisions.txt`              | Small personal decisions | `start_contraceptives_decision`, `stop_contraceptives_decision`                                                     |
| `00_agot_major_decisions.txt`              | Government conversion    | `agot_pirate_convert_whole_realm_to_feudalism_decision`, `agot_adopt_kneeler_ways_decision`                         |
| `00_agot_banking_decisions.txt`            | Free Cities banking      | Bank-related decisions                                                                                              |
| `00_agot_appearance_decisions.txt`         | Character appearance     | Cosmetic changes with `decision_group_type = appearance`                                                            |
| `00_agot_religious_decisions.txt`          | AGOT faiths              | Faith-specific decisions with `decision_group_type = religion`                                                      |
| `00_agot_religion_creation_decisions.txt`  | New religions            | Religion creation with `decision_group_type = religion`                                                             |
| `00_agot_free_cities_decisions.txt`        | Free Cities politics     | Free city government decisions                                                                                      |
| `00_agot_house_revival_decisions.txt`      | House restoration        | Revive extinct houses                                                                                               |
| `00_agot_legitimate_house_decisions.txt`   | House legitimization     | Legitimize cadet branches                                                                                           |
| `00_agot_petty_kingdoms_decisions.txt`     | Petty kingdom formation  | Form regional kingdoms                                                                                              |
| `00_agot_colonization_decisions.txt`       | Colonization             | Settle wilderness counties                                                                                          |
| `00_agot_pirate_decisions.txt`             | Pirate gameplay          | Pirate-specific with `decision_group_type = adventurer`                                                             |
| `00_agot_epidemic_decisions.txt`           | Disease response         | Region-gated epidemic decisions                                                                                     |
| `00_agot_invasion_decisions.txt`           | Invasion mechanics       | Major invasion decisions                                                                                            |
| `00_agot_melee_decisions.txt`              | Combat/tournament        | Melee-related decisions                                                                                             |
| `00_agot_nickname_decisions.txt`           | Nicknames                | Earn character nicknames                                                                                            |
| `00_agot_silly_decisions.txt`              | Silly mode               | Gated behind `has_game_rule = agot_silly_mode`                                                                      |
| `00_agot_scenario_rr_decisions.txt`        | Robert's Rebellion       | Scenario-specific, uses `unavailable_unique_decisions`                                                              |
| `00_agot_dragonkeeper_decisions.txt`       | Dragonkeeper order       | Dragonkeeper management                                                                                             |
| `00_agot_reclaim_gift_decisions.txt`       | Artifact recovery        | Reclaim gifted artifacts                                                                                            |
| `00_agot_lmf_decisions.txt`                | Lady/matrilineal         | Marriage rules, checks `matrilineal_marriages_*` game rules                                                         |
| `00_agot_personal_coa_decisions.txt`       | Coat of arms             | Personal heraldry                                                                                                   |
| `00_agot_cultural_tradition_decisions.txt` | Culture traditions       | AGOT-specific traditions                                                                                            |
| `00_agot_tournament_decisions.txt`         | Tournaments              | AGOT tournament decisions                                                                                           |
| `00_agot_mega_wars_decisions.txt`          | Mega-wars                | Large-scale war decisions                                                                                           |
| `00_agot_activity_decisions.txt`           | Activities               | AGOT activity triggers                                                                                              |
| `00_agot_artifact_decisions.txt`           | General artifacts        | Non-VS artifact decisions                                                                                           |
| `00_agot_knighthood_decisions.txt`         | Knighthood               | Knighting decisions                                                                                                 |
| `00_agot_maester_decisions.txt`            | Maesters                 | Citadel-related decisions                                                                                           |

Event files are in `events/agot_decisions_events/`:

- `agot_decisions_events.txt` -- General decision events (e.g., title creation,
  dragon horn binding)
- `agot_major_decisions_events.txt` -- Major decision follow-up events
- `agot_minor_decisions_events.txt` -- Minor decision events (Dune Road
  notification, etc.)
- `agot_faceless_decisions_events.txt` -- Faceless Men events
- `agot_crown_commission_events.txt` -- Crown commission events
- `agot_dragon_tree_events.txt` -- Dragon tree events
- `agot_religion_creation_events.txt` -- Religion creation events
- `agot_appearance_decisions_events.txt` / `agot_appearance_events.txt` --
  Appearance change events
- `agot_global_news_settings_events.txt` -- News settings events

## AGOT-Specific Template

```
# common/decisions/agot_decisions/00_agot_my_custom_decisions.txt
my_agot_decision = {
	picture = {
		reference = "gfx/interface/illustrations/decisions/decision_realm.dds"
	}

	decision_group_type = major  # or: artifact, banking, religion, appearance, adventurer

	desc = my_agot_decision_desc
	selection_tooltip = my_agot_decision_tooltip

	# AGOT always uses ai_check_interval_by_tier, NOT ai_check_interval
	# Must include all 6 tiers including hegemony
	ai_check_interval_by_tier = {
		barony = 0
		county = 60
		duchy = 60
		kingdom = 60
		empire = 60
		hegemony = 60
	}

	is_shown = {
		is_ruler = yes
		is_landed = yes
		# Use AGOT government flags, not vanilla government checks
		NOT = { government_has_flag = government_is_nw }
		# Use AGOT geographical regions
		capital_county.title_province = {
			geographical_region = world_westeros_seven_kingdoms
		}
	}

	is_valid = {
		# Use AGOT scripted trigger instead of vanilla is_independent_ruler
		agot_is_independent_ruler = yes
		prestige_level >= 3
	}

	is_valid_showing_failures_only = {
		is_available_adult = yes
		is_at_war = no
	}

	cost = {
		gold = 500
		prestige = 250
	}

	effect = {
		# Trigger a follow-up event in events/agot_decisions_events/
		trigger_event = agot_my_custom_events.0001
		custom_tooltip = my_agot_decision_effect_tt
	}

	ai_potential = {
		always = yes
	}

	ai_will_do = {
		base = 50
		# AGOT uses ai_value_modifier for personality-driven AI weighting
		ai_value_modifier = {
			ai_honor = 0.25
			ai_greed = -0.25
		}
	}
}
```

## Annotated AGOT Example

This is `restore_the_nights_watch` from `00_agot_nw_decisions.txt`, a major
decision that lets the Iron Throne holder or King in the North restore the
Night's Watch:

```
restore_the_nights_watch = {
	picture = {
		reference = "gfx/interface/illustrations/decisions/decision_realm.dds"
	}

	desc = restore_the_nights_watch_desc
	selection_tooltip = restore_the_nights_watch_tooltip
	decision_group_type = major                        # Shown in the major decisions section

	ai_check_interval_by_tier = {                      # AGOT pattern: all 6 tiers required
		barony = 0                                     # Barons never check
		county = 0                                     # Counties never check
		duchy = 0                                      # Dukes never check
		kingdom = 120                                  # Kings check every ~10 years
		empire = 120                                   # Emperors check every ~10 years
		hegemony = 120                                 # Iron Throne holders check every ~10 years
	}

	is_shown = {
		is_ruler = yes
		is_landed = yes
		OR = {                                         # Wall must be vacant or under your control
			NOT = { exists = title:k_the_wall.holder }
			has_title = title:k_the_wall
			any_vassal = {
				has_title = title:k_the_wall
			}
		}
		OR = {                                         # Must hold Iron Throne or the North
			has_title = title:h_the_iron_throne         # AGOT hegemony-tier title
			has_title = title:e_the_north               # AGOT empire-tier title
		}
	}

	is_valid = {
		prestige_level >= 3
		agot_is_independent_ruler = yes                # AGOT scripted trigger (not vanilla)
		completely_controls_region = world_westeros_the_wall_only  # AGOT geographical region
	}

	is_valid_showing_failures_only = {
		is_at_war = no                                 # Soft requirement shown only on failure
	}

	cost = {
		gold = 500
		prestige = 250
	}

	effect = {
		trigger_event = agot_nights_watch.0024         # Fires event in separate event namespace
		custom_tooltip = restore_the_nights_watch.tooltip.1
		custom_tooltip = restore_the_nights_watch.tooltip.2
	}

	ai_will_do = {
		base = 100                                     # AI strongly favors this
	}
}
```

**Key AGOT patterns visible here:**

- `hegemony` tier in `ai_check_interval_by_tier`
- AGOT-specific title checks (`title:h_the_iron_throne`, `title:k_the_wall`,
  `title:e_the_north`)
- `agot_is_independent_ruler` instead of vanilla `is_independent_ruler`
- AGOT geographical region `world_westeros_the_wall_only`
- Event in a separate AGOT namespace (`agot_nights_watch`)

## Key Differences from Vanilla

| Aspect               | Vanilla                                | AGOT                                                                                             |
| -------------------- | -------------------------------------- | ------------------------------------------------------------------------------------------------ |
| AI check interval    | `ai_check_interval = N` (single value) | `ai_check_interval_by_tier` with 6 tiers including `hegemony`                                    |
| Independence check   | `is_independent_ruler = yes`           | `agot_is_independent_ruler = yes` (scripted trigger)                                             |
| Government gating    | `government_has_flag` rarely used      | `government_has_flag` is the primary way to gate by government type                              |
| Decision group types | `major` only                           | `major`, `artifact`, `banking`, `religion`, `appearance`, `adventurer`, `adventurer_minor`       |
| Geographical regions | `world_europe_west`, etc.              | `world_westeros_*`, `world_essos_*`, etc.                                                        |
| Title tier           | Up to `empire`                         | Includes `hegemony` (Iron Throne tier above empire)                                              |
| One-time decisions   | Per-character cooldowns                | Global variable list `unavailable_unique_decisions` to block globally                            |
| AI personality       | Basic `ai_will_do` modifiers           | `ai_value_modifier` block with `ai_greed`, `ai_compassion`, `ai_boldness`, `ai_honor`, `ai_zeal` |
| Game rules           | Rarely checked                         | `has_game_rule` for AGOT-specific settings (historical events, silly mode, etc.)                 |
| File location        | `common/decisions/` (flat)             | `common/decisions/agot_decisions/` (subdirectory)                                                |
| Character references | Generic character checks               | Named characters via `character:Lannister_1`, `character:Stark_3`, etc.                          |
| Dragon integration   | N/A                                    | `has_trait = dragonrider`, `any_relation = { type = agot_dragon }`, global `living_dragons` list |

## AGOT Pitfalls

1. **Missing `hegemony` tier** -- If you use `ai_check_interval_by_tier`, you
   must include all 6 tiers. Omitting `hegemony` will cause errors. AGOT never
   uses the vanilla single-value `ai_check_interval`.

2. **Using vanilla `is_independent_ruler`** -- In AGOT, Lord Paramounts under
   the Iron Throne are considered "independent" for most gameplay purposes. Use
   `agot_is_independent_ruler = yes` instead of vanilla
   `is_independent_ruler = yes` to get correct behavior.

3. **Wrong government check** -- AGOT has many custom government types. Do not
   assume `is_feudal = yes` works. Use
   `government_has_flag = government_is_feudal` or
   `government_has_flag = government_is_lp_feudal` to check government types.

4. **Forgetting Night's Watch exclusion** -- Many decisions should exclude
   Night's Watch characters. Add
   `NOT = { government_has_flag = government_is_nw }` to `is_shown` when the
   decision makes no sense for NW members.

5. **Wrong geographical regions** -- AGOT replaces all vanilla regions. Using
   `world_europe_west` will match nothing. Use AGOT regions like
   `world_westeros_seven_kingdoms`, `world_westeros_the_north`,
   `world_essos_free_cities`, etc.

6. **Not gating one-time decisions globally** -- For decisions that should only
   happen once in the entire game (not just per-character), use the
   `unavailable_unique_decisions` global variable list pattern:

   ```
   is_shown = {
       NOT = {
           is_target_in_global_variable_list = {
               name = unavailable_unique_decisions
               target = flag:my_unique_decision_flag
           }
       }
   }
   ```

   And in the effect, add:

   ```
   effect = {
       add_to_global_variable_list = {
           name = unavailable_unique_decisions
           target = flag:my_unique_decision_flag
       }
   }
   ```

7. **Ignoring game rules** -- If your decision relates to historical events or
   alternative history, check the relevant AGOT game rule (e.g.,
   `has_game_rule = agot_story_historical_events_historical_outcomes`) to ensure
   consistency.

8. **`custom_tooltip` vs `custom_description`** -- AGOT uses `custom_tooltip` in
   `effect` blocks for tooltip text and `custom_description` in `is_valid`
   blocks for requirement descriptions. The `custom_description` variant uses
   `text` and optionally `subject` parameters.

9. **Dragon decisions without safety checks** -- When writing dragon-related
   decisions, always check `agot_dragon_population_alive = yes` and verify
   dragon existence with `any_relation = { type = agot_dragon is_alive = yes }`.
   Check `has_character_flag = owned_dragon` to distinguish wild vs. claimed
   dragons.

10. **File placement** -- Place new AGOT sub-mod decisions in
    `common/decisions/agot_decisions/` (the subdirectory), not the parent
    `common/decisions/`. The parent folder contains vanilla overrides; the
    subdirectory is for AGOT-native decisions.
