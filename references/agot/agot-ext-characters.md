# AGOT Extension: Character Interactions

> This guide extends
> [references/patterns/characters.md](../patterns/characters.md) with
> AGOT-specific changes.

## What AGOT Changes

AGOT adds **30+ new interaction files** in `common/character_interactions/`,
covering lore-specific systems that have no vanilla equivalent. It also
**overrides several vanilla files** (e.g. `00_character_interactions.txt`,
`00_prison_interactions.txt`) to alter existing behavior.

Key changes:

- **New interaction categories**: dragons, Kingsguard, trials by combat,
  Valyrian steel, banking, coronations, Night's Watch, colonization, silent
  sisters, spy networks, and more
- **Custom government checks**: many interactions gate on
  `government_has_flag = government_is_nw` (Night's Watch), feudal, tribal, or
  clan — not just vanilla government types
- **Dragon characters as recipients**: AGOT models dragons as actual characters
  with `has_trait = dragon`. Interactions like `slay_dragon_interaction` and
  `rename_dragon_interaction` target dragon-characters directly
- **Artifact-targeting interactions**: `target_type = artifact` and
  `target_filter = actor_artifacts` are used heavily for dragon eggs and
  Valyrian steel swords (e.g. `cradle_egg`, `give_egg`,
  `offer_dawn_interaction`)
- **Custom triggers and effects**: AGOT defines many scripted triggers (e.g.
  `agot_has_dragonblood_heritage`, `ruler_primary_title_has_kingsguard_trigger`,
  `worthy_sword_of_the_morning_trigger`) and scripted effects (e.g.
  `agot_assign_lord_commander_effect`, `agot_offer_squire_interaction_effect`)
  that interactions call
- **redirect blocks**: used to reroute interactions to a different recipient
  (e.g. `legitimize_bastard_liege_interaction` redirects to
  `scope:actor.top_liege`, `invite_to_small_council` redirects to the vassal's
  liege)
- **Variable-based state tracking**: interactions read and write variables on
  titles and characters (e.g. `var:kingsguard_1` through `var:kingsguard_6` on
  the primary title, `var:current_dragon` on dragonriders)

## AGOT Interaction Categories

Based on the files in `common/character_interactions/`:

| File                                        | Theme                                                    | Example interactions                                                                            |
| ------------------------------------------- | -------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| `00_agot_dragon_interactions.txt`           | Dragon eggs, terror campaigns, dragon slaying, renaming  | `cradle_egg`, `give_egg`, `slay_dragon_interaction`, `agot_instruct_to_conduct_terror_campaign` |
| `00_agot_kingsguard_interactions.txt`       | Kingsguard recruitment, lord commander appointment       | `invite_to_kingsguard_interaction`, `appoint_lord_commander_interaction`                        |
| `00_agot_trial_by_combat_interactions.txt`  | Trials by combat and Trial of Seven                      | `demand_trial_by_combat_interaction`, `demand_trial_of_seven_interaction`                       |
| `00_agot_valyrian_steel_interactions.txt`   | Valyrian steel swords, Dawn                              | `offer_dawn_interaction`, `take_claimed_vs_sword_interaction`                                   |
| `00_agot_bastard_interactions.txt`          | Bastard legitimization via liege                         | `legitimize_bastard_liege_interaction`                                                          |
| `00_agot_coronation_interactions.txt`       | Coronation activity invites                              | `coronation_invite_to_activity_interaction`                                                     |
| `00_agot_small_council_interactions.txt`    | Small council vassal recruitment                         | `invite_to_small_council`                                                                       |
| `00_agot_captive_interactions.txt`          | AGOT-specific prisoner actions                           | —                                                                                               |
| `00_agot_colonization_interactions.txt`     | Beyond-the-Wall / Essos colonization                     | —                                                                                               |
| `00_agot_dragon_bond_interactions.txt`      | Bonding with dragons                                     | —                                                                                               |
| `00_agot_dragonkeeper_interactions.txt`     | Dragonkeeper order management                            | —                                                                                               |
| `00_agot_first_ranger_interactions.txt`     | Night's Watch first ranger                               | —                                                                                               |
| `00_agot_free_city_interactions.txt`        | Free Cities diplomacy                                    | —                                                                                               |
| `00_agot_hostile_interactions.txt`          | AGOT-specific hostile actions                            | —                                                                                               |
| `00_agot_knight_interactions.txt`           | Knighting, squiring                                      | —                                                                                               |
| `00_agot_lmf_interactions.txt`              | Lord/Master Feasts                                       | —                                                                                               |
| `00_agot_lover_interactions.txt`            | AGOT lover interactions                                  | —                                                                                               |
| `00_agot_religious_interactions.txt`        | Septon, faith-specific                                   | —                                                                                               |
| `00_agot_scheme_interactions.txt`           | AGOT scheme interactions                                 | —                                                                                               |
| `00_agot_self_interactions.txt`             | Self-targeted actions                                    | —                                                                                               |
| `00_agot_septon_character_interactions.txt` | Septon character actions                                 | —                                                                                               |
| `00_agot_silent_sisters_interactions.txt`   | Silent Sisters vows                                      | —                                                                                               |
| `00_agot_spy_network_interactions.txt`      | Spy network management                                   | —                                                                                               |
| `00_agot_banking_interactions.txt`          | Iron Bank / banking                                      | —                                                                                               |
| `00_agot_btw_interactions.txt`              | Beyond the Wall alliances                                | —                                                                                               |
| `00_agot_debug_interactions.txt`            | Debug/test interactions                                  | —                                                                                               |
| `00_agot_diarch_interactions.txt`           | Regent/diarch interactions                               | —                                                                                               |
| `00_agot_dynast_interactions.txt`           | Dynasty head actions                                     | —                                                                                               |
| `00_agot_house_customizer_interactions.txt` | House customization                                      | —                                                                                               |
| `00_agot_prison_interactions.txt`           | AGOT prison overrides                                    | —                                                                                               |
| `zz_agot_rv_war_interactions.txt`           | War interaction overrides (loaded last via `zz_` prefix) | —                                                                                               |

## AGOT-Specific Template

### Artifact-targeting interaction (dragon eggs, Valyrian steel)

```
my_agot_artifact_interaction = {
    category = interaction_category_friendly
    common_interaction = yes
    icon = icon_scheme_dragon

    # Target an artifact instead of (or in addition to) a character
    target_type = artifact
    target_filter = actor_artifacts

    # Filter which artifacts can be picked
    can_be_picked_artifact = {
        scope:target = {
            has_variable = dragon_egg       # AGOT artifact variable
            NOT = { has_variable = dud_egg }
        }
    }

    is_shown = {
        scope:actor = {
            this = scope:recipient           # Self-interaction
            any_character_artifact = {
                has_variable = dragon_egg
            }
        }
    }

    on_accept = {
        scope:target = {
            set_variable = my_custom_var
        }
    }

    auto_accept = yes

    ai_targets = {
        ai_recipients = self
    }
    ai_frequency = 84
    ai_will_do = {
        base = 0
        modifier = {
            add = 100
            agot_has_dragonblood_heritage = yes  # AGOT scripted trigger
        }
    }
}
```

### Interaction requiring acceptance with AGOT patterns

```
my_agot_request_interaction = {
    category = interaction_category_diplomacy
    icon = icon_kingsguard
    use_diplomatic_range = no           # Common in AGOT for realm-wide interactions

    ai_maybe = yes
    ai_min_reply_days = 8
    ai_max_reply_days = 16
    can_send_despite_rejection = yes
    popup_on_receive = yes
    pause_on_receive = yes

    desc = my_agot_request_interaction_desc

    greeting = negative
    notification_text = MY_NOTIFICATION_TEXT

    # Redirect to a different recipient (e.g. prisoner -> imprisoner)
    redirect = {
        if = {
            limit = {
                scope:actor = scope:recipient
                exists = scope:actor.imprisoner
            }
            scope:actor.imprisoner = { save_scope_as = recipient }
        }
    }

    is_shown = {
        scope:actor = { is_imprisoned_by = scope:recipient }
        scope:recipient = {
            OR = {
                government_has_flag = government_is_feudal
                government_has_flag = government_is_tribal
                government_has_flag = government_is_nw    # Night's Watch government
            }
        }
    }

    cooldown = { years = 3 }

    on_accept = {
        scope:recipient = { trigger_event = my_namespace.1000 }
    }

    on_decline = {
        scope:recipient = {
            add_prestige = major_prestige_loss
            add_character_modifier = {
                modifier = my_declined_modifier
                years = 15
            }
        }
    }

    auto_accept = no

    ai_accept = {
        base = 100
        modifier = {
            add = -100
            scope:recipient = { has_relation_nemesis = scope:actor }
            desc = "ACTOR_NEMESIS_TO_ME_REASON"
        }
    }
}
```

## Annotated AGOT Example

From `00_agot_kingsguard_interactions.txt` -- the
`invite_to_kingsguard_interaction`:

```
invite_to_kingsguard_interaction = {
    category = interaction_category_diplomacy
    icon = icon_kingsguard

    use_diplomatic_range = no               # 1. No diplomatic range limit -- realm-wide

    ai_maybe = yes                          # 2. AI can respond "maybe" (delays response)
    ai_min_reply_days = 8
    ai_max_reply_days = 16
    can_send_despite_rejection = yes        # 3. Can re-send even if previously rejected
    popup_on_receive = yes                  # 4. Forces a popup for the player recipient
    pause_on_receive = yes                  # 5. Pauses the game when received

    desc = invite_to_kingsguard_interaction_desc

    on_decline_summary = kingsguard_decline_summary  # 6. Custom decline summary loc key

    greeting = negative
    notification_text = REQUEST_VOWS_NOTIFICATION_TEXT

    is_shown = {
        scope:actor = {
            ruler_primary_title_has_kingsguard_trigger = yes  # 7. AGOT scripted trigger
            NAND = {                                           # 8. Check variable slots on title
                primary_title = { exists = var:kingsguard_1 }
                primary_title = { exists = var:kingsguard_2 }
                primary_title = { exists = var:kingsguard_3 }
                primary_title = { exists = var:kingsguard_4 }
                primary_title = { exists = var:kingsguard_5 }
                primary_title = { exists = var:kingsguard_6 }
            }
            NOT = { has_character_flag = choosing_kingsguard }
        }
        scope:recipient = {
            is_human = yes
            NOR = {
                has_trait = kingsguard
                has_trait = maester                            # 9. AGOT custom traits
                scope:recipient = scope:actor
            }
            top_liege = scope:actor
            valid_kingsguard_gender_trigger = yes              # 10. AGOT scripted trigger
        }
    }

    is_valid_showing_failures_only = {                         # 11. Shown but greyed-out reasons
        scope:recipient = {
            is_landed = no
            is_married = no
            is_capable_adult = yes
            can_be_knight_trigger = { ARMY_OWNER = scope:actor }
            agot_has_clergy_trait = no                          # 12. AGOT scripted trigger
            NOR = {
                has_trait = order_member
                has_trait = nightswatch                         # 13. AGOT-specific trait
            }
        }
    }

    auto_accept = {                                            # 14. Conditional auto-accept
        custom_description = {
            text = "ORDER_VOWS_AMBITION"
            scope:recipient = {
                has_character_modifier = training_for_kingsguard
            }
        }
    }

    ai_accept = {                                              # 15. Detailed AI acceptance
        base = 50
        # ... many modifiers using ai_honor, ai_greed, ai_zeal, ai_boldness
        # ... personality traits (lustful, craven) and situation checks (heir, betrothed)
        opinion_modifier = {
            who = scope:recipient
            opinion_target = scope:actor
            multiplier = 0.25
            desc = AI_SIMPLE_OPINION_REASON
        }
    }

    on_accept = {
        scope:recipient = { save_scope_as = kingsguard_candidate }
        scope:actor = {
            save_scope_as = king
            trigger_event = { id = agot_kingsguard.1005 }     # 16. Delegates to event chain
        }
    }

    on_decline = {
        scope:recipient = {
            save_scope_as = kingsguard_candidate
            add_character_flag = kingsguard_position_rejected   # 17. Flags to prevent re-asking
        }
        scope:actor = {
            save_scope_as = king
            trigger_event = { id = agot_kingsguard.1007 }
        }
    }
}
```

Key annotations:

1. **`use_diplomatic_range = no`** -- Most AGOT realm-wide interactions disable
   diplomatic range
2. **`popup_on_receive = yes` + `pause_on_receive = yes`** -- Forces player
   attention for important decisions
3. **Variable-based slot tracking** (lines 8) -- Kingsguard slots are tracked as
   `var:kingsguard_1` through `var:kingsguard_6` on the primary title
4. **AGOT scripted triggers** (lines 7, 10, 12) -- Always check
   `common/scripted_triggers/` for AGOT-specific triggers before writing your
   own
5. **Conditional `auto_accept`** (line 14) -- Takes a trigger block instead of
   just `yes`/`no`; characters training for Kingsguard auto-accept
6. **Event delegation** (line 16) -- The `on_accept` saves scopes and fires an
   event rather than doing effects inline

## Key Differences from Vanilla

| Aspect                         | Vanilla                                      | AGOT                                                                                                                                |
| ------------------------------ | -------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| **Recipient types**            | Always human characters                      | Can target dragon-characters (`has_trait = dragon`)                                                                                 |
| **Artifact targeting**         | Rare (EP2+ only)                             | Heavy use: dragon eggs, Valyrian steel, Dawn                                                                                        |
| **Government checks**          | `government_has_flag = government_is_feudal` | Adds `government_is_nw` (Night's Watch) and others                                                                                  |
| **Diplomatic range**           | Usually default (yes)                        | Often `use_diplomatic_range = no` for realm-wide interactions                                                                       |
| **State tracking**             | Mostly character flags                       | Variables on titles (`var:kingsguard_1`), characters (`var:current_dragon`), and artifacts (`var:dragon_egg`, `var:valyrian_steel`) |
| **Scripted triggers**          | Use vanilla triggers directly                | Wrap checks in AGOT scripted triggers (`agot_has_dragonblood_heritage`, `ruler_primary_title_has_kingsguard_trigger`, etc.)         |
| **`redirect` blocks**          | Occasionally used                            | Frequently used -- e.g. bastard legitimization redirects to top liege, small council redirects to vassal's liege                    |
| **`on_decline` consequences**  | Typically mild (opinion penalty)             | Can be severe: prestige loss, piety loss, long-duration character modifiers, family opinion cascades                                |
| **AI complexity**              | Simple base + a few modifiers                | Extensive modifier chains using `ai_honor`, `ai_greed`, `ai_zeal`, `ai_boldness`, `opinion_modifier`, and personality trait checks  |
| **`on_send` block**            | Rarely used                                  | Used for hostile-action cooldown flags (`flag_hostile_actions_disabled_delay`) and pre-acceptance opinion hits                      |
| **`common_interaction = yes`** | Standard for most                            | Used on AGOT interactions that should appear in the default right-click menu                                                        |

## AGOT Pitfalls

- **Missing AGOT scripted triggers**: Do not inline complex checks that AGOT
  already provides as scripted triggers. Search `common/scripted_triggers/` for
  `agot_` prefixed triggers before writing your own. For example, use
  `agot_has_dragonblood_heritage` instead of manually checking heritage flags.

- **Dragon characters are characters, not artifacts**: Dragons in AGOT are
  actual character objects with `has_trait = dragon`. They can be
  `scope:recipient` in interactions. Dragon eggs, however, are artifacts. Do not
  confuse the two.

- **Variable slot system for Kingsguard**: The Kingsguard uses
  `var:kingsguard_1` through `var:kingsguard_6` on the ruler's primary title,
  plus `cp:kingsguard_lord_commander` for the council position. Do not create a
  parallel tracking system; use the existing variables.

- **`has_none_of_variables` / `has_all_variables`**: AGOT uses these
  multi-variable check triggers extensively (e.g. checking egg state). These are
  vanilla syntax but rarely seen outside AGOT. They take a list of `name = ...`
  entries.

- **Night's Watch government**: Many interactions explicitly include or exclude
  `government_has_flag = government_is_nw`. If your interaction should work at
  the Wall, add this check. If it should not, explicitly exclude it.

- **`zz_` prefix for load order**: AGOT uses `zz_agot_rv_war_interactions.txt`
  to ensure it loads after all other interaction files, overriding vanilla war
  interactions. If you need to override AGOT interactions, your file must load
  after `zz_` (e.g. use `zzz_` prefix).

- **`redirect` scope changes**: When using `redirect`, the original
  `scope:recipient` becomes `scope:secondary_recipient` (or similar). Make sure
  your `is_shown`, `on_accept`, and `ai_accept` blocks reference the correct
  scope. See `legitimize_bastard_liege_interaction` for a clear example.

- **Cooldown and flag stacking**: AGOT interactions often set temporary
  character flags with day/year expiry (e.g.
  `flag_hostile_actions_disabled_delay` with `days = 10`). If you add a new
  interaction in the same domain (e.g. combat, trials), check for these existing
  flags in `can_send` blocks.

- **`is_human = yes` guards**: Many AGOT interactions restrict visibility to
  human players (`scope:actor = { is_human = yes }` or `is_ai = no`). This is
  intentional -- some interactions are designed as player-only UI actions (e.g.
  `rename_dragon_interaction`). Do not remove these guards without understanding
  why they exist.

- **Event namespace collisions**: AGOT interaction events use namespaces like
  `agot_char_interaction`, `agot_kingsguard`, `agot_trial_by_combat`,
  `agot_dragon`, `agot_btw_interaction_events`, `agot_faceless_interaction`. Use
  a unique namespace for your sub-mod events to avoid collisions.
