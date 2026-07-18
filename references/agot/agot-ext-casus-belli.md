# AGOT Extension: Casus Belli

> This guide extends
> [references/patterns/casus-belli.md](../patterns/casus-belli.md) with
> AGOT-specific changes.

## What AGOT Changes

AGOT massively extends the CB system to reflect the political dynamics of
Westeros and Essos. The major differences from vanilla are:

1. **Mega Wars (MW) system** -- AGOT's most complex addition. Large-scale wars
   (e.g., Robert's Rebellion, War of the Five Kings) use a story-cycle-driven
   system where vassals choose stances (loyalist, neutral, rebel, independence)
   instead of joining as simple allies. Defined via `story_agot_mw_crown` and
   `story_agot_mw_rebel` story types.

2. **Custom CB groups** -- AGOT adds `dragon_conquest`, `slavery`,
   `shattered_world`, `ambush`, `free_captives`, and `personal` CB groups
   alongside vanilla groups. A separate `01_agot_rv_casus_belli_groups.txt` adds
   the `personal` group for RV (Rhaenyra's Victory) scenarios.

3. **Dragon-gated CBs** -- An entire tier of conquest CBs (county, duchy, ducal,
   kingdom, subjugation) that require `is_current_dragonrider = yes`. These use
   the `dragon_conquest` group and give dragonriders unique warpath options.

4. **Night's Watch and Beyond-the-Wall CBs** -- Ranging CBs
   (`nw_single_county_ranging_cb`, `nw_multi_county_ranging_cb`,
   `great_ranging_cb`) that use the `struggle` group tied to the `btw_struggle`
   and require `government_has_flag = government_is_nw`.

5. **AGOT-specific civil war CBs** -- `agot_rebellion_war`, `agot_revolt_war`,
   `agot_independence_war`, `agot_claimant_faction_war`,
   `agot_bastard_claimant_war`, `agot_succession_war`,
   `agot_liberty_faction_war` replace or supplement vanilla civil war CBs. Many
   are event-only (`valid_to_start = { always = no }` or `is_ai = no`).

6. **Invasion and scenario CBs** -- Targaryen exile invasions
   (`agot_targaryen_exile_invasion_war_cb`, `faegon_invasion_war_cb`), Blackfyre
   rebellions (`agot_blackfyre_claim`), and numerous scenario-specific war files
   for bookmarks like Defiance of Duskendale, Ninepenny Kings, etc.

7. **Slavery CBs** -- `slave_raid_cb` and related CBs in the `slavery` group,
   gated behind `has_realm_law = slavery_allowed_law` or
   `government_has_flag = government_is_pirate`.

8. **Government-based war blocking** -- AGOT injects
   `agot_generic_war_blocks_trigger` into almost every vanilla CB group. This
   blocks wars for `government_is_uninteractable` governments, faiths with
   `cannot_declare_war`, and respects the Braavos-Pentos treaty.

9. **Mega War validity checks** -- Many CBs include
   `agot_mw_war_valid_during_megawar = yes` in `allowed_against_character` to
   prevent declaring wars against participants already in a mega war.

10. **Geographic restrictions** -- CBs commonly exclude
    `world_westeros_beyond_the_wall` via `geographical_region` checks, and use
    `agot_invalid_war_target` to block wars against magisterial or pirate
    titles.

## AGOT CB Types

### CB Files Overview

| File                                | Contents                                                                                                                                                                                             |
| ----------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `00_agot_dragon_wars.txt`           | `dragon_county_conquest_cb`, `dragon_duchy_conquest_cb`, `dragon_ducal_conquest_cb`, `dragon_kingdom_conquest_cb`, `dragon_subjugation_cb`                                                           |
| `00_agot_casus_belli_mega_wars.txt` | `agot_independence_war`, `agot_reconquest_war`, `agot_rebellion_war`, `agot_revolt_war`, `agot_liberty_faction_war`, `agot_claimant_faction_war`, `agot_bastard_claimant_war`, `agot_succession_war` |
| `00_agot_invasion_wars.txt`         | `agot_targaryen_exile_invasion_war_cb`, `faegon_invasion_war_cb`                                                                                                                                     |
| `00_agot_blackfyre_wars.txt`        | `agot_blackfyre_claim`                                                                                                                                                                               |
| `00_agot_nights_watch_wars.txt`     | `wildling_raid_cb`, `nw_single_county_ranging_cb`, `nw_multi_county_ranging_cb`, `great_ranging_cb`                                                                                                  |
| `00_agot_slavery_wars.txt`          | `slave_raid_cb` and related                                                                                                                                                                          |
| `00_agot_pirate_wars.txt`           | Pirate-specific CBs                                                                                                                                                                                  |
| `00_agot_wildling_wars.txt`         | Wildling-specific CBs                                                                                                                                                                                |
| `00_agot_adventurer_wars.txt`       | Adventurer CBs                                                                                                                                                                                       |
| `00_agot_shattered_world_wars.txt`  | Shattered world game rule CBs                                                                                                                                                                        |
| `00_agot_unstable_regions_wars.txt` | Unstable region CBs                                                                                                                                                                                  |
| `00_agot_rv_rescue_wars.txt`        | Rhaenyra's Victory rescue CBs                                                                                                                                                                        |
| `00_agot_rv_revenge_wars.txt`       | Rhaenyra's Victory revenge CBs                                                                                                                                                                       |
| `00_agot_scenario_*_wars.txt`       | Bookmark-specific scenario CBs                                                                                                                                                                       |

### CB Groups

AGOT adds these groups in `01_agot_casus_belli_groups.txt`:

```
dragon_conquest = {
    allowed_for_character = {
        NOT = { agot_generic_war_blocks_trigger = yes }
        herders_and_tributary_constraints = yes
    }
}

slavery = {
    allowed_for_character = {
        NOT = { agot_generic_war_blocks_trigger = yes }
        herders_and_tributary_constraints = yes
    }
}

shattered_world = {
    allowed_for_character = {
        NOT = { agot_generic_war_blocks_trigger = yes }
        herders_and_tributary_constraints = yes
    }
}
```

And modifies every vanilla group in `00_casus_belli_groups.txt` to inject the
`agot_generic_war_blocks_trigger` check. For example, the vanilla `religious`
group adds:

```
#AGOT Added
NOT = { agot_generic_war_blocks_trigger = yes }
```

### Key AGOT Scripted Triggers for CBs

Found in `common/scripted_triggers/00_agot_war_triggers.txt`:

- **`agot_invalid_war_target`** -- Returns true for titles with
  `magisterial_attached_titles_law` or pirate domicile titles. Used in
  `valid_to_start` blocks.
- **`agot_generic_war_blocks_trigger`** -- Blocks wars for uninteractable
  governments, faiths with `cannot_declare_war`, same-faith war bans, and the
  Braavos-Pentos treaty.
- **`agot_pentos_braavos_treaty_prohibited_war_declaration_trigger`** -- Checks
  the global `braavos_treaty` variable.

Found in `common/scripted_triggers/00_agot_mega_wars_triggers.txt`:

- **`agot_mw_war_valid_during_megawar`** -- Prevents declaring wars against
  characters already in a mega war (checks `pre_war_liege` variable).
- **`agot_mw_start_regular_mw_trigger`** -- Determines if a war should escalate
  into a full mega war. Checks empire-tier participants, realm sizes.
- **`agot_mw_start_lite_mw_trigger`** -- Lower-tier version for smaller realms
  (30+ realm size for admin, 35+ for others).
- **`agot_mw_crown_trigger`** / **`agot_mw_rebel_leader_trigger`** -- Check if a
  character owns the crown/rebel story cycles.

## AGOT-Specific Template

Here is an annotated template for an AGOT-compatible CB, incorporating the
patterns found across AGOT source files:

```
my_agot_custom_cb = {
    icon = my_agot_custom_cb                          # Icon in gfx/interface/icons/casus_belli/
    group = conquest                                   # Or dragon_conquest, slavery, civil_war, etc.

    combine_into_one = yes
    should_show_war_goal_subview = yes
    mutually_exclusive_titles = { always = yes }

    allowed_for_character = {
        # AGOT: Check government flags instead of just is_ruler
        NOT = { government_has_flag = government_is_nw }

        # AGOT-specific character checks (e.g., dragonrider, government type)
        # is_current_dragonrider = yes                # For dragon CBs
        # has_government = lp_feudal_government       # For lord paramount CBs
    }

    allowed_against_character = {
        scope:attacker = {
            ALL_FALSE = {
                top_liege = scope:defender.top_liege
                liege = scope:defender
            }
        }

        # AGOT: Block wars during active mega wars
        agot_mw_war_valid_during_megawar = yes

        # AGOT: Block feudal vs Night's Watch wars
        NOT = {
            AND = {
                scope:attacker = { government_has_flag = government_is_feudal }
                scope:defender = { government_has_flag = government_is_nw }
            }
        }
    }

    target_titles = neighbor_land                      # Or: all, none, claim
    target_title_tier = duchy                          # Or: county, kingdom, all
    ignore_effect = change_title_holder

    valid_to_start = {
        # AGOT: Check for invalid targets (magisterial, pirate)
        NOT = {
            scope:target = { agot_invalid_war_target = yes }
        }
        # AGOT: Exclude Beyond the Wall
        scope:target = {
            NOT = {
                title_province = { geographical_region = world_westeros_beyond_the_wall }
            }
        }
    }

    should_invalidate = {
        # AGOT: Invalidate if character condition lost (e.g., dragon dies)
        NOT = {
            any_in_list = {
                list = target_titles
                any_in_de_jure_hierarchy = {
                    tier = tier_county
                    holder = {
                        OR = {
                            this = scope:defender
                            target_is_liege_or_above = scope:defender
                        }
                    }
                }
            }
        }
    }

    cost = {
        prestige = {
            value = 0
            add = {
                value = medium_prestige_value
                desc = CB_BASE_COST
            }
            multiply = common_cb_prestige_cost_multiplier
        }
    }

    on_declaration = {
        on_declared_war = yes                          # Standard AGOT pattern
    }

    on_victory = {
        scope:attacker = { show_pow_release_message_effect = yes }

        add_legitimacy_attacker_victory_effect = yes
        scope:attacker = { accolade_attacker_war_end_glory_gain_med_effect = yes }

        create_title_and_vassal_change = {
            type = conquest
            save_scope_as = change
            add_claim_on_loss = yes
        }
        every_in_list = {
            list = target_titles
            change_title_holder = {
                holder = scope:attacker
                change = scope:change
            }
        }
        resolve_title_and_vassal_change = scope:change

        add_truce_attacker_victory_effect = yes

        # AGOT: Always call this at end of on_victory
        agot_war_victory_effects = yes
    }

    on_white_peace = {
        scope:attacker = { show_pow_release_message_effect = yes }
        scope:attacker = {
            add_prestige = {
                value = minor_prestige_value
                multiply = -1.0
            }
        }
        add_truce_white_peace_effect = yes
    }

    on_defeat = {
        scope:attacker = { show_pow_release_message_effect = yes }
        add_legitimacy_attacker_defeat_effect = yes
        scope:attacker = {
            pay_short_term_gold_reparations_effect = {
                GOLD_VALUE = 3
            }
        }
        add_truce_attacker_defeat_effect = yes

        scope:attacker = {
            save_temporary_scope_as = loser
        }
        on_lost_aggression_war_discontent_loss = yes
    }

    transfer_behavior = transfer
    on_primary_attacker_death = inherit
    on_primary_defender_death = inherit
    attacker_allies_inherit = yes
    defender_allies_inherit = yes

    war_name = "MY_AGOT_WAR_NAME"
    war_name_base = "MY_AGOT_WAR_NAME_BASE"
    cb_name = "MY_AGOT_CB_NAME"

    interface_priority = 100

    use_de_jure_wargoal_only = yes
    attacker_wargoal_percentage = 0.8

    max_defender_score_from_occupation = 150            # AGOT uses 150 widely
    max_attacker_score_from_occupation = 150

    ai_score = {
        base = 100
    }
}
```

## Annotated AGOT Example

This is `dragon_county_conquest_cb` from `00_agot_dragon_wars.txt`, annotated
with key AGOT patterns:

```
dragon_county_conquest_cb = {
    icon = dragon_county_conquest_cb
    group = dragon_conquest                            # AGOT-specific group (defined in 01_agot_casus_belli_groups.txt)

    combine_into_one = yes
    should_show_war_goal_subview = yes
    mutually_exclusive_titles = { always = yes }

    allowed_for_character = {
        is_current_dragonrider = yes                   # AGOT: Requires active dragon mount

        NOT = { government_has_flag = government_is_nw }  # Night's Watch cannot declare

        trigger_if = {                                 # AGOT: Targaryen exiles cannot attack Iron Throne realm
            limit = {
                has_targaryen_exile_story = yes
            }
            NOR = {
                scope:defender.primary_title ?= title:h_the_iron_throne
                scope:defender.top_liege ?= title:h_the_iron_throne.holder
            }
        }
    }

    allowed_against_character = {
        scope:attacker = {
            ALL_FALSE = {                              # Cannot attack within same realm
                top_liege = scope:defender.top_liege
                liege = scope:defender
            }
        }
        agot_mw_war_valid_during_megawar = yes         # AGOT: Block during mega wars
        NOT = {                                        # AGOT: Feudal cannot attack Night's Watch
            AND = {
                scope:attacker = { government_has_flag = government_is_feudal }
                scope:defender = { government_has_flag = government_is_nw }
            }
        }
    }

    target_titles = all
    target_title_tier = county
    ignore_effect = change_title_holder

    valid_to_start = {
        scope:target = {
            neighboring_county_or_viking_conquest_trigger = { CHARACTER = root }
        }
        NOT = {
            scope:target = { agot_invalid_war_target = yes }   # AGOT: No magisterial/pirate targets
        }
        scope:target = {
            tier = tier_county
            NOT = {
                title_province = {
                    geographical_region = world_westeros_beyond_the_wall  # AGOT: No Beyond the Wall
                }
            }
        }
    }

    should_invalidate = {
        OR = {
            scope:attacker = {
                is_current_dragonrider = no             # AGOT: Invalidate if dragon lost
            }
            NOT = {
                any_in_list = {
                    list = target_titles
                    any_in_de_jure_hierarchy = {
                        tier = tier_county
                        holder = {
                            OR = {
                                this = scope:defender
                                target_is_liege_or_above = scope:defender
                            }
                        }
                    }
                }
            }
        }
    }

    # ... cost, on_declaration blocks ...

    on_victory = {
        scope:attacker = { show_pow_release_message_effect = yes }
        add_legitimacy_attacker_victory_effect = yes
        scope:attacker = { accolade_attacker_war_end_glory_gain_low_effect = yes }

        create_title_and_vassal_change = {
            type = conquest
            save_scope_as = change
            add_claim_on_loss = yes
        }
        every_in_list = {
            list = target_titles
            change_title_holder = {
                holder = scope:attacker
                change = scope:change
            }
        }
        resolve_title_and_vassal_change = scope:change

        # ... prestige, allies, truce ...

        agot_war_victory_effects = yes                 # AGOT: Always call at end of on_victory
    }

    # ... on_white_peace, on_defeat ...

    war_name = "DRAGON_CONQUEST_WAR_NAME"
    war_name_base = "DRAGON_CONQUEST_WAR_NAME_BASE"
    cb_name = "DRAGON_CONQUEST_COUNTY_CB_NAME"

    interface_priority = 995
    use_de_jure_wargoal_only = yes
    attacker_wargoal_percentage = 0.8
    max_defender_score_from_occupation = 150
    max_attacker_score_from_occupation = 150
}
```

## Key Differences from Vanilla

| Aspect                     | Vanilla                                             | AGOT                                                                                                                                                     |
| -------------------------- | --------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **CB groups**              | `conquest`, `religious`, `claim`, `civil_war`, etc. | Adds `dragon_conquest`, `slavery`, `shattered_world`, `ambush`, `free_captives`, `personal`                                                              |
| **Group-level blocking**   | Minimal checks                                      | Every group injects `agot_generic_war_blocks_trigger` to check government flags, faith doctrines, Braavos treaty                                         |
| **War blocking trigger**   | None                                                | `agot_generic_war_blocks_trigger` -- blocks `government_is_uninteractable`, `cannot_declare_war`, same-faith bans, Braavos-Pentos treaty                 |
| **Mega war integration**   | N/A                                                 | CBs check `agot_mw_war_valid_during_megawar` in `allowed_against_character`; wars can escalate into mega wars via `agot_mw_start_regular_mw_trigger`     |
| **Target validation**      | Basic tier/neighbor checks                          | `agot_invalid_war_target` blocks magisterial and pirate titles; geographic region exclusions for Beyond the Wall                                         |
| **Government checks**      | `is_ruler`, basic tier                              | `government_has_flag = government_is_nw`, `government_has_flag = government_is_feudal`, `has_government = lp_feudal_government`, etc.                    |
| **War resolution effects** | Prestige/title changes                              | Always calls `agot_war_victory_effects` at end of `on_victory`; `show_pow_release_message_effect` in all outcome blocks                                  |
| **Occupation scores**      | Usually 100 max                                     | AGOT uses `max_defender_score_from_occupation = 150` and `max_attacker_score_from_occupation = 150` widely                                               |
| **Event-only CBs**         | Few                                                 | Many AGOT CBs use `valid_to_start = { always = no }` or `valid_to_start = { is_ai = no }` -- they are started from events/interactions only              |
| **Iron Throne awareness**  | N/A                                                 | CBs reference `title:h_the_iron_throne`, `title:e_dorne`, `title:e_the_iron_islands`, etc. with special logic for subjugation and de jure reassignment   |
| **Dragonrider CBs**        | N/A                                                 | Full tier of CBs (county through kingdom + subjugation) gated behind `is_current_dragonrider = yes` with `should_invalidate` if dragon lost              |
| **War score tuning**       | Standard values                                     | Battle-heavy CBs like `agot_succession_war` use `max_attacker_score_from_battles = 200`, `max_defender_score_from_battles = 300`                         |
| **Independence**           | `agot_is_independent_ruler`                         | AGOT uses its own `agot_is_independent_ruler` trigger (not vanilla `is_independent_ruler`) to account for mega war displaced rulers with `pre_war_liege` |

## AGOT Pitfalls

1. **Forgetting `agot_war_victory_effects`** -- Nearly every AGOT CB calls
   `agot_war_victory_effects = yes` at the end of `on_victory` (and sometimes
   `on_defeat` for defender-perspective effects). Omitting this breaks post-war
   cleanup including mega war resolution.

2. **Using `is_independent_ruler` instead of `agot_is_independent_ruler`** --
   AGOT distinguishes between "truly independent" and "temporarily independent
   due to mega war" (characters with `pre_war_liege` variable). The AGOT trigger
   accounts for this. The mega war source even warns:
   `# Don't change this to agot_is_independent_ruler !` in specific contexts
   where vanilla behavior is needed.

3. **Not checking `agot_mw_war_valid_during_megawar`** -- If your CB does not
   include this in `allowed_against_character`, players can declare wars against
   characters already participating in a mega war, causing broken state.

4. **Ignoring `agot_invalid_war_target`** -- Forgetting
   `NOT = { scope:target = { agot_invalid_war_target = yes } }` in
   `valid_to_start` allows wars against magisterial attached titles and pirate
   domiciles.

5. **Missing Night's Watch blocks** -- AGOT consistently blocks feudal-vs-NW
   wars:

   ```
   NOT = {
       AND = {
           scope:attacker = { government_has_flag = government_is_feudal }
           scope:defender = { government_has_flag = government_is_nw }
       }
   }
   ```

   Forgetting this allows declaring war on the Night's Watch.

6. **Beyond the Wall geographic filter** -- If your CB targets titles in
   Westeros, always exclude Beyond the Wall:

   ```
   NOT = {
       title_province = { geographical_region = world_westeros_beyond_the_wall }
   }
   ```

7. **Missing `show_pow_release_message_effect`** -- AGOT calls
   `scope:attacker = { show_pow_release_message_effect = yes }` at the start of
   every `on_victory`, `on_white_peace`, and `on_defeat` block. Omitting it
   breaks prisoner-of-war message display.

8. **Not setting `on_declaration = { on_declared_war = yes }`** -- AGOT CBs
   consistently use this pattern. Omitting it can break mega war detection (the
   `on_war_started` on-action checks).

9. **Wrong group for event-only wars** -- AGOT event-only CBs (rebellion,
   revolt) use `group = civil_war` which has `can_only_start_via_script = yes`.
   If you want a player-declarable CB, do not use this group.

10. **Occupation score mismatch** -- AGOT uses 150 for max occupation scores in
    most CBs. Using the vanilla default of 100 will create inconsistent war
    score behavior relative to other AGOT wars.

11. **Dragon CB invalidation** -- If writing a dragonrider CB, always add
    `should_invalidate` checking `is_current_dragonrider = no`. AGOT invalidates
    wars if the attacker's dragon dies mid-war.

12. **Iron Throne title type** -- The Iron Throne is `title:h_the_iron_throne`
    (hegemony tier `h_`, not empire `e_`). The Seven Kingdoms are empire-tier
    titles (`e_dorne`, `e_the_north`, etc.) that are de jure under the hegemony.
    Getting the tier hierarchy wrong breaks subjugation and reconquest logic.
