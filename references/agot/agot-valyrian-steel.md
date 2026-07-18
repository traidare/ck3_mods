# AGOT: Valyrian Steel

## Overview

Valyrian steel swords are the most prestigious artifacts in AGOT. The mod
implements them as CK3 artifacts with a rich system of scripted effects, custom
inheritance logic, battle looting, house claims, and forging. Every historical
VS sword (Blackfyre, Dark Sister, Ice, Longclaw, Dawn, etc.) has its own
creation effect, artifact template, modifier, and visual. A parallel "forgeable"
system lets players select from named generic swords when forging new VS blades.

Key source files:

| File                                                                      | Purpose                                                                   |
| ------------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| `common/scripted_effects/00_agot_artifact_vs_sword_effects.txt`           | Creation effects for all historical VS swords                             |
| `common/scripted_effects/00_agot_artifact_vs_sword_forgeable_effects.txt` | Forgeable (generic) VS sword creation + selection system                  |
| `common/artifacts/templates/00_agot_historical_artifacts_equipment.txt`   | Artifact templates for all VS swords                                      |
| `common/modifiers/00_agot_artifact_modifiers.txt`                         | Stat modifiers for each VS sword                                          |
| `common/character_interactions/00_agot_valyrian_steel_interactions.txt`   | Dawn offering + taking claimed VS swords                                  |
| `events/agot_events/agot_valyrian_steel_events.txt`                       | Dawn bestowal, battle looting, inheritance, Lamentation quest, customizer |
| `common/on_action/agot_on_actions/agot_death.txt`                         | Triggers VS inheritance on death                                          |

## Key Concepts

### VS Swords as Artifacts

Every Valyrian steel sword is a CK3 artifact of `type = sword` with:

- **`decaying = no`** -- VS swords never decay
- **`rarity = illustrious`** -- set via `set_artifact_rarity_illustrious`
- **A `valyrian_steel` variable** -- the universal tag
  (`has_variable = valyrian_steel`) used to identify VS swords throughout the
  codebase
- **A `historical_unique_artifact` variable** -- marks it as historically unique
- **A `traditional_house_owner` variable** -- records the dynasty house that
  traditionally owns the sword
- **An artifact modifier** -- unique per sword (e.g. `vs_blackfyre_modifier`,
  `vs_ice_modifier`)
- **An artifact template** -- unique per sword (e.g. `vs_blackfyre_template`)
- **Custom visuals** -- unique per sword (e.g. `vs_blackfyre_visuals`)

### Two Categories of VS Swords

1. **Historical swords** (in `00_agot_artifact_vs_sword_effects.txt`): Named
   swords tied to specific houses with full artifact history. Examples:
   Blackfyre, Dark Sister, Ice, Longclaw, Heartsbane, Dawn, Brightroar. Created
   with `$OWNER$` parameter only.

2. **Forgeable swords** (in `00_agot_artifact_vs_sword_forgeable_effects.txt`):
   Named generic swords for the forging system. Created with both `$OWNER$` and
   `$CREATOR$` parameters. Examples: Black Death, Mother's Grief, Talon, Glory,
   Widow's Wail, Dragonbane, Unkindness. Also includes cultural variants: Andal,
   First Men, and Valyrian styles in arming sword / longsword / gold / silver /
   bronze combinations.

### Sword Forging System

The forging system uses a selection UI where the player picks from pre-defined
forgeable swords:

1. `agot_spawn_vs_forgeables_for_selection_effect` creates all forgeable swords
   on `title:c_ruins.holder` (a hidden holder)
2. `agot_build_vs_forgeables_list_for_selection_effect` iterates those
   artifacts, builds a `possible_artifacts` variable list for the UI
3. The player selects one via the `agot_artifact_selection` widget
4. `agot_create_selected_vs_forgeable` reads `var:selected_artifact` and calls
   the matching creation effect

### Inheritance and Claiming

On death (`agot_death.txt` on_action), two events fire:

- `agot_valyrian_steel.0003` -- returns Dawn to the Dayne dynast
- `agot_valyrian_steel.9000` -- runs `give_vs_sword_to_appropriate_heir` for all
  other VS swords

The inheritance logic in `give_vs_sword_to_appropriate_heir` follows this
priority:

1. Special case for Bittersteel (character:Targaryen_95)
2. If the dead owner is NOT the house head -> sword goes to house head
3. If the dead owner IS the house head and player_heir is in same house -> heir
4. If no house members remain -> dynast of the dynasty
5. Fallback: player_heir

### House Claims

When a VS sword changes hands outside normal inheritance, the original house
gets an artifact claim:

```
scope:artifact_house = {
    add_house_artifact_claim = scope:looted_vs_sword
}
```

The victim also gets a personal claim:

```
scope:recipient = {
    add_personal_artifact_claim = scope:demanded_artifact
}
```

## AGOT Scripted API

### VS Sword Creation Effects (Historical)

File: `common/scripted_effects/00_agot_artifact_vs_sword_effects.txt`

Every historical sword follows this pattern:

```
agot_create_artifact_vs_<sword_name>_effect = {
    $OWNER$ = {
        save_scope_as = owner
    }
    set_artifact_rarity_illustrious = yes
    create_artifact = {
        name = vs_<sword_name>_name
        visuals = vs_<sword_name>_visuals
        description = vs_<sword_name>_description
        type = sword
        wealth = scope:wealth
        quality = scope:quality
        template = vs_<sword_name>_template
        history = {
            type = created_before_history  # or created
            date = <date>
        }
        modifier = vs_<sword_name>_modifier
        save_scope_as = newly_created_artifact
        decaying = no
    }
    scope:newly_created_artifact ?= {
        equip_artifact_to_owner_replace = yes
        set_variable = { name = valyrian_steel value = yes }
        set_variable = { name = historical_unique_artifact value = yes }
        set_variable = {
            name = traditional_house_owner
            value = dynasty:dynn_<Dynasty>.dynasty_founder.house
        }
        # Artifact history entries follow...
        agot_add_artifact_history = {
            ARTIFACT = this
            TYPE = inherited    # or given, stolen, conquered, discovered
            DATE = <date>
            RECIPIENT = character:<id>
        }
    }
}
```

Known historical VS swords (partial list from templates file):

| Effect Name                                   | House     | Sword        |
| --------------------------------------------- | --------- | ------------ |
| `agot_create_artifact_vs_adders_fang_effect`  | Wyl       | Adder's Fang |
| `agot_create_artifact_vs_blackfyre_effect`    | Targaryen | Blackfyre    |
| `agot_create_artifact_vs_brightroar_effect`   | Lannister | Brightroar   |
| `agot_create_artifact_vs_cloudbreak_effect`   | Adarys    | Cloudbreak   |
| `agot_create_artifact_vs_dancer_effect`       | Massey    | Dancer       |
| `agot_create_artifact_vs_dark_sister_effect`  | Targaryen | Dark Sister  |
| `agot_create_artifact_vs_dawn_effect`         | Dayne     | Dawn         |
| `agot_create_artifact_vs_heartsbane_effect`   | Tarly     | Heartsbane   |
| `agot_create_artifact_vs_ice_effect`          | Stark     | Ice          |
| `agot_create_artifact_vs_lady_forlorn_effect` | Corbray   | Lady Forlorn |
| `agot_create_artifact_vs_longclaw_effect`     | Mormont   | Longclaw     |
| `agot_create_artifact_vs_nightfall_effect`    | Harlaw    | Nightfall    |
| `agot_create_artifact_vs_oathkeeper_effect`   | --        | Oathkeeper   |
| `agot_create_artifact_vs_orphan_maker_effect` | Roxton    | Orphan-Maker |
| `agot_create_artifact_vs_red_rain_effect`     | Drumm     | Red Rain     |
| `agot_create_artifact_vs_vigilance_effect`    | --        | Vigilance    |

### Artifact History Helper

File: `common/scripted_effects/00_agot_artifact_effects.txt`

```
agot_add_artifact_history = {
    if = {
        limit = {
            game_start_date >= $DATE$
        }
        $ARTIFACT$ = {
            add_artifact_history = {
                type = $TYPE$
                date = $DATE$
                recipient = $RECIPIENT$
            }
        }
    }
}
```

This only adds history entries if the game start is after the specified date, so
bookmarks before a transfer do not show it.

History types used: `inherited`, `given`, `stolen`, `conquest`, `discovered`,
`ransomed`, `created`, `created_before_history`.

### Forgeable Effects

File: `common/scripted_effects/00_agot_artifact_vs_sword_forgeable_effects.txt`

**Key effects:**

`agot_spawn_vs_forgeables_for_selection_effect` -- Creates all forgeable VS
swords on the hidden `title:c_ruins.holder`. This is the "catalog" of available
designs.

`agot_build_vs_forgeables_list_for_selection_effect` -- Takes `$VIEWER$`
parameter, iterates all VS artifacts on c_ruins holder, builds a
`possible_artifacts` variable list, and sets a default `selected_artifact`.

`agot_create_selected_vs_forgeable` -- Takes `$OWNER$` and `$CREATOR$`, reads
`var:selected_artifact`, dispatches to the correct creation effect via a long
if/else_if chain matching artifact modifiers.

**Forgeable swords with unique names:**

| Effect                                           | Modifier used for selection   |
| ------------------------------------------------ | ----------------------------- |
| `agot_create_artifact_vs_black_death_effect`     | `vs_black_death_modifier`     |
| `agot_create_artifact_vs_dark_moon_effect`       | `vs_dark_moon_modifier`       |
| `agot_create_artifact_vs_dragonbane_effect`      | `vs_dragonbane_modifier`      |
| `agot_create_artifact_vs_glory_effect`           | `vs_glory_modifier`           |
| `agot_create_artifact_vs_iron_price_effect`      | `vs_iron_price_modifier`      |
| `agot_create_artifact_vs_mothers_grief_effect`   | `vs_mothers_grief_modifier`   |
| `agot_create_artifact_vs_skinpeeler_effect`      | `vs_skinpeeler_modifier`      |
| `agot_create_artifact_vs_sting_effect`           | `vs_sting_modifier`           |
| `agot_create_artifact_vs_stormy_nights_effect`   | `vs_stormy_nights_modifier`   |
| `agot_create_artifact_vs_strangers_touch_effect` | `vs_strangers_touch_modifier` |
| `agot_create_artifact_vs_talon_effect`           | `vs_talon_modifier`           |
| `agot_create_artifact_vs_unkindness_effect`      | `vs_unkindness_modifier`      |
| `agot_create_artifact_vs_widows_wail_effect`     | `vs_widows_wail_modifier`     |

**Generic cultural style swords** (selected via variable, not modifier):

- `agot_create_artifact_vs_andal_armingsword_gold_effect` (variable:
  `andal_armingsword_gold_artifact`)
- `agot_create_artifact_vs_andal_armingsword_silver_effect`
- `agot_create_artifact_vs_andal_longsword_gold_effect`
- `agot_create_artifact_vs_andal_longsword_silver_effect`
- `agot_create_artifact_vs_firstman_armingsword_gold_effect` / silver / bronze
- `agot_create_artifact_vs_firstman_longsword_gold_effect` / silver / bronze
- `agot_create_artifact_vs_valyrian_armingsword_gold_effect` / silver
- `agot_create_artifact_vs_valyrian_longsword_gold_effect` / silver

Fallback: `agot_create_artifact_vs_sword_forged_effect` -- plain generic VS
sword.

Note the difference: forgeable effects set `valyrian_steel_generic = yes` in
addition to `valyrian_steel = yes`. Some forgeables also set a style-specific
variable (e.g. `andal_armingsword_gold_artifact`).

### Artifact Modifiers (Stats)

File: `common/modifiers/00_agot_artifact_modifiers.txt`

All VS swords give base `prowess_no_portrait = 9` plus prestige bonuses. Some
have unique extras:

```
vs_blackfyre_modifier = {
    prowess_no_portrait = 9
    monthly_dynasty_prestige_mult = 0.05
    monthly_prestige = 0.2
    vassal_opinion = 10
    vassal_limit = 10
}

vs_ice_modifier = {
    prowess_no_portrait = 9
    monthly_dynasty_prestige_mult = 0.05
    monthly_prestige = 0.2
    short_reign_duration_mult = -0.32
    domain_limit = 1
}

vs_dawn_modifier = {
    prowess_no_portrait = 10      # Strongest VS sword
    monthly_dynasty_prestige_mult = 0.05
    monthly_prestige = 0.5
    monthly_martial_lifestyle_xp_gain_mult = 0.10
    general_opinion = 15
}

vs_longclaw_modifier = {
    prowess_no_portrait = 9
    monthly_dynasty_prestige_mult = 0.05
    monthly_prestige = 0.2
    health = 0.05
    forest_advantage = 6
    majorroad_forest_advantage = 6
    minorroad_forest_advantage = 6
}

vs_generic_andal_modifier = {
    prowess_no_portrait = 9
    monthly_dynasty_prestige_mult = 0.05
    monthly_prestige = 0.2
}
```

### Artifact Templates

File: `common/artifacts/templates/00_agot_historical_artifacts_equipment.txt`

All VS templates follow the same pattern:

```
vs_blackfyre_template = {
    can_equip = {
        always = yes
    }
    can_benefit = {
        is_capable_adult = yes
    }
    fallback = {
        #always = yes
    }
    unique = yes
    ai_score = {
        value = 100
    }
}
```

The `unique = yes` flag means only one instance of this artifact can exist at a
time.

### Key Scripted Trigger

File: `common/scripted_triggers/00_agot_artifact_triggers.txt`

```
agot_artifact_can_take = {
    has_none_of_variables = {
        name = maesterwork
        name = historical_throne
        name = white_book
        name = agot_swiper_no_swiping
    }
}
```

This controls which artifacts can be forcibly taken. VS swords pass this check
unless someone manually sets `agot_swiper_no_swiping` on them.

## Interactions

File: `common/character_interactions/00_agot_valyrian_steel_interactions.txt`

### `offer_dawn_interaction`

The Dayne dynast offers Dawn to a dynasty member.

- **Category:** `interaction_category_friendly`
- **Icon:** `icon_valyrian_steel`
- **Shown when:** Actor is Dayne dynast, owns Dawn, recipient is Dayne dynasty
  member age 12+
- **AI accept:** Base 0; +500 if `worthy_sword_of_the_morning_trigger = yes`;
  negative modifiers for unworthy + humble/craven/content traits
- **On accept:** Recipient gets Dawn, nickname
  `nick_agot_the_sword_of_the_morning`, character flag `is_sword_of_morning`,
  massive prestige, +1 prestige level
- **On decline:** Toast sent to dynast about refusal

### `take_claimed_vs_sword_interaction`

Take a claimed VS sword from a prisoner.

- **Category:** `interaction_category_hostile`
- **Shown when:** Recipient has a VS sword claimable by actor
  (`can_be_claimed_by`, `agot_artifact_can_take`, `var:valyrian_steel = yes`);
  both human
- **Valid when:** Not at war with each other; actor not imprisoned; recipient
  imprisoned by actor
- **Auto-accept:** `yes` (no negotiation)
- **On accept:**
  - Transfers sword with `type = stolen` history
  - Adds personal + house artifact claims to victim
  - Opinion penalty (-10 insult) and potential rivalry
  - If victim is the `agot_artifact_keeper` (artifact merchant), triggers sell
    event

## Events

File: `events/agot_events/agot_valyrian_steel_events.txt`

### Dawn Bestowal Chain (0001-0004)

- **0001:** Dayne dynast has Dawn + a worthy candidate -> option to grant or
  deny
- **0002:** Knight receives Dawn. If
  `worthy_sword_of_the_morning_trigger = yes`: gets nickname, flag, massive
  prestige
- **0003:** Hidden death event. If a Dayne with Dawn dies, returns it to the
  dynast. Fires 0004 after 30 days
- **0004:** Dynast picks a new Sword of the Morning from eligible dynasty
  members

### Battle Looting Chain (1000-1012)

- **1000:** VS holder killed in battle. Slayer decides: claim sword (adds house
  claim for victim's house, -30 opinion from house head) or return it (+20
  grateful opinion)
- **1001:** VS holder captured alive. Captor decides: take sword (prestige loss,
  stolen history, house claim added) or let them keep it
- **1010:** Letter to house head: sword was returned honorably
- **1011:** House head responds to theft. Options:
  - Start a **House Feud** + `steal_back_artifact` scheme (with bonus success
    modifier)
  - Start `steal_back_artifact` scheme only
  - Set rival relation with the thief
  - Let it go (massive prestige loss, house members angry)
- **1012:** Letter informing the thief of the house head's decision

### Lamentation Quest Chain (2000+)

Triggered via filler events (`agot_filler_events_on_actions.txt`, weight 100).
Exclusively for Royce dynasty members in King's Landing.

- **2000:** Royce member discovers clues about lost Lamentation. Option to
  search or pray
- **2001:** Search begins in the Dragon Pit. Randomly determines location:
  ruins, Dragonstone, or held by house Wheaton
- Subsequent events continue the quest based on
  `global_var:lamentation_location`

### Targaryen Sword Equip Event (3000-3001)

- **3000:** Hidden event on artifact equip. If a Targaryen equips Dark Sister or
  Blackfyre, triggers 3001 (flavor event about wielding an ancestral blade)

### VS Customizer (8100)

- **8100:** Ruler Designer event. Triggered at game start if character has
  `vs_customizer` trait
- Uses `agot_artifact_selection` widget + text entry for naming
- Calls `agot_build_vs_forgeables_list_for_selection_effect` then
  `agot_create_selected_vs_forgeable`
- After: removes `vs_customizer` trait, cleans up variables

### Death Inheritance (9000)

- **9000:** Hidden on_death event. For every VS sword owned (except Dawn), calls
  `give_vs_sword_to_appropriate_heir`

### Debug/Display (9999)

- **9999:** "Show me the Steel" -- displays all VS swords in the game via the
  `agot_artifact_valyrian_steel_selection` widget

## Sub-Mod Recipes

### Adding a New Valyrian Steel Sword

To add a new historical VS sword (e.g. "Frostbite" for House Karstark):

**1. Artifact modifier** (`common/modifiers/my_mod_artifact_modifiers.txt`):

```
vs_frostbite_modifier = {
    prowess_no_portrait = 9
    monthly_dynasty_prestige_mult = 0.05
    monthly_prestige = 0.2
    winter_advantage = 5
}
```

**2. Artifact template** (`common/artifacts/templates/my_mod_artifacts.txt`):

```
vs_frostbite_template = {
    can_equip = {
        always = yes
    }
    can_benefit = {
        is_capable_adult = yes
    }
    unique = yes
    ai_score = {
        value = 100
    }
}
```

**3. Artifact visuals** -- add entries in `common/artifacts/visuals/`
referencing your sword's GFX asset (or reuse an existing one like `longsword`).

**4. Creation effect** (`common/scripted_effects/my_mod_vs_effects.txt`):

```
my_mod_create_artifact_vs_frostbite_effect = {
    $OWNER$ = {
        save_scope_as = owner
    }
    set_artifact_rarity_illustrious = yes
    create_artifact = {
        name = vs_frostbite_name
        visuals = vs_frostbite_visuals    # or reuse: longsword
        description = vs_frostbite_description
        type = sword
        wealth = scope:wealth
        quality = scope:quality
        template = vs_frostbite_template
        history = {
            type = created_before_history
            date = 7800.1.1
        }
        modifier = vs_frostbite_modifier
        save_scope_as = newly_created_artifact
        decaying = no
    }
    scope:newly_created_artifact ?= {
        equip_artifact_to_owner_replace = yes
        set_variable = { name = valyrian_steel value = yes }
        set_variable = { name = historical_unique_artifact value = yes }
        set_variable = {
            name = traditional_house_owner
            value = dynasty:dynn_Karstark.dynasty_founder.house
        }
        # Add history entries as needed
        agot_add_artifact_history = {
            ARTIFACT = this
            TYPE = inherited
            DATE = 8200.1.1
            RECIPIENT = character:Karstark_1
        }
    }
}
```

**5. Localization** (`localization/english/my_mod_artifacts_l_english.yml`):

```yaml
l_english:
  vs_frostbite_name: "Frostbite"
  vs_frostbite_description:
    "A pale blade of Valyrian steel, cold to the touch even in summer."
```

**6. Spawn it** -- call the effect from game start or an event:

```
# In an on_action or event immediate block:
character:Karstark_1 = {
    save_scope_as = owner
    set_variable = { name = wealth value = 100 }    # or use set_artifact_rarity_illustrious pattern
    set_variable = { name = quality value = 100 }
    my_mod_create_artifact_vs_frostbite_effect = { OWNER = scope:owner }
}
```

Important: you must ensure `scope:wealth` and `scope:quality` are set before
calling the creation effect. AGOT uses `set_artifact_rarity_illustrious` to set
these.

### Custom VS Forging Event

To add your own VS forging event chain (e.g. a master smith in Qohor):

```
namespace = my_mod_forge

# Player initiates forging
my_mod_forge.0001 = {
    type = character_event
    title = my_mod_forge.0001.t
    desc = my_mod_forge.0001.desc
    theme = stewardship

    trigger = {
        gold >= 500
        location = { has_county_modifier = qohor_smiths_modifier }
    }

    # Use AGOT's selection widget for sword choice
    widgets = {
        widget = {
            gui = "agot_artifact_selection"
            container = "custom_widgets_container"
        }
    }

    immediate = {
        save_scope_as = viewer
        hidden_effect = {
            agot_build_vs_forgeables_list_for_selection_effect = {
                VIEWER = scope:viewer
            }
        }
    }

    option = {
        name = my_mod_forge.0001.a
        remove_short_term_gold = 500

        # Find the court smith or use self as creator
        if = {
            limit = { employs_court_position = court_smith_court_position }
            random_court_position_holder = {
                type = court_smith_court_position
                save_scope_as = court_smith
            }
        }
        else = {
            save_scope_as = court_smith
        }

        agot_create_selected_vs_forgeable = {
            OWNER = scope:viewer
            CREATOR = scope:court_smith
        }
    }

    option = {
        name = my_mod_forge.0001.b
    }

    after = {
        remove_variable = selected_artifact
        clear_variable_list = possible_artifacts
    }
}
```

### Modifying VS Inheritance

To change how VS swords pass on death, you can override
`give_vs_sword_to_appropriate_heir` or add your own on_death event.

Example: always pass VS swords to the primary heir instead of the house head:

```
namespace = my_mod_vs_inherit

# Fire on death, after AGOT's 9000
my_mod_vs_inherit.0001 = {
    hidden = yes

    trigger = {
        any_character_artifact = {
            has_variable = valyrian_steel
            NOT = { has_artifact_modifier = vs_dawn_modifier }
        }
    }

    immediate = {
        every_character_artifact = {
            limit = {
                has_variable = valyrian_steel
                NOT = { has_artifact_modifier = vs_dawn_modifier }
            }
            save_scope_as = vs_sword
            # Override: give to player heir
            if = {
                limit = { exists = root.player_heir }
                scope:vs_sword = {
                    set_owner = {
                        target = root.player_heir
                        history = {
                            type = inherited
                            actor = root
                            recipient = root.player_heir
                            location = root.location
                        }
                    }
                }
            }
        }
    }
}
```

Register in an on_action that fires on death:

```
# common/on_action/my_mod_on_actions.txt
on_death = {
    events = {
        my_mod_vs_inherit.0001
    }
}
```

Note: this will conflict with AGOT's `agot_valyrian_steel.9000`. Consider load
order -- your event should fire after AGOT's, and the last `set_owner` wins.

## Pitfalls

### Missing Variables

Every VS sword MUST have `set_variable = { name = valyrian_steel value = yes }`.
Without it:

- The sword will not be recognized by the inheritance system
  (`agot_valyrian_steel.9000`)
- The `take_claimed_vs_sword_interaction` will not show it
- Battle looting events will ignore it
- The debug event `agot_valyrian_steel.9999` will not list it

### Scope Requirements

The creation effects expect `scope:wealth` and `scope:quality` to exist before
they are called. AGOT sets these via `set_artifact_rarity_illustrious`. If you
call a creation effect directly without setting these scoped values, the
artifact will have 0 wealth and 0 quality.

### `decaying = no` is Mandatory

Without `decaying = no` in `create_artifact`, the sword will lose durability
over time. This is thematically wrong for Valyrian steel and will eventually
destroy it.

### Dawn is Special

Dawn has completely separate inheritance logic (`agot_valyrian_steel.0003`) that
returns it to the Dayne dynast on death. It is explicitly excluded from the
general VS inheritance (`NOT = { has_artifact_modifier = vs_dawn_modifier }`).
If you create a sword with similar "always returns to house" behavior, you must
add your own on_death event and exclude it from the standard logic.

### `equip_artifact_to_owner_replace` Matters

All creation effects call `equip_artifact_to_owner_replace = yes` after creating
the sword. Without this, the sword exists in the owner's inventory but is not
equipped, so the modifier bonuses do not apply.

### Template `unique = yes`

If your template has `unique = yes`, only one instance can exist at a time.
Attempting to create a second one will silently fail. If you need multiple
copies of a sword (e.g. for testing), remove this flag from the template.

### Forgeable vs Historical Distinction

Historical swords take `$OWNER$` only. Forgeable swords take `$OWNER$` and
`$CREATOR$`. If you call a forgeable effect without `$CREATOR$`, the script will
error. Forgeables also set `valyrian_steel_generic = yes`, which may be checked
elsewhere.

### House Claims on Theft

When a sword is stolen in battle (events 1000/1001), the original house gets an
artifact claim via `add_house_artifact_claim`. If you create custom theft
mechanics, always add these claims -- without them the
`take_claimed_vs_sword_interaction` (which requires `can_be_claimed_by`) will
not work, and the AI house head will not attempt recovery.

### The `agot_swiper_no_swiping` Variable

Setting `agot_swiper_no_swiping` on an artifact makes it immune to the
`take_claimed_vs_sword_interaction` and other "take artifact" checks via
`agot_artifact_can_take`. Do not set this on VS swords unless you intentionally
want to prevent them from ever being seized from prisoners.

### On-Action Load Order

AGOT's death on_action fires `agot_valyrian_steel.9000` and `.0003` (Dawn). If
your sub-mod overrides `on_death`, make sure these events still fire. The safest
approach is to add your events to the list rather than replacing the file.
