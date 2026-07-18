# AGOT: Dragon Tree, Story Cycles & Dreams

## Overview

AGOT implements dragons as full CK3 characters with the `dragon` trait, managed
through an interconnected set of systems:

- **Dragon Tree** -- a genealogy-tracking structure stored via story cycles and
  global variable lists, displayed in a custom GUI.
- **Dragon Story Cycles** -- persistent `story_*` types that handle dragon
  lifecycle (alive, at war, duels, variable storage, doll crafting).
- **Dragon Dreams** -- the `dragon_dreams` trait and associated events that
  allow prophetic scheme discovery and harm prevention.
- **Dragon Personalities** -- 14 personality traits organized in 7 opposing
  pairs, plus congenital/physical traits and education tiers.

All dragon state is anchored to `title:c_ruins.holder` (a hidden holder) for
tree structure, while individual dragon data lives on the dragon character and
its associated `story_dragon_variable_storage` story.

---

## Key Concepts

### Dragons as Characters

Every dragon is a CK3 character with `has_trait = dragon`. The base `dragon`
trait (defined in `common/traits/00_agot_dragon_traits.txt`) sets:

- `can_have_children = no`, `fertility = 0.0` (overridable by `dragon_fertile`)
- `health = 5`, `life_expectancy = 150`
- `character_travel_speed = 150`, `character_travel_safety = 200`
- Dynamic name via `first_valid` triggered_desc: `trait_dragon_bound`
  (horn-bound), `trait_dragon_tamed` (has rider), `trait_dragon_owned` (owned
  but no rider), `trait_dragon_wild` (alive, no owner)

Key variables on dragon characters:

- `var:current_rider` -- the character currently riding this dragon
- `var:pitted_dragon_location` -- county title where the dragon is pitted
- `has_character_flag = owned_dragon` -- dragon is claimed
- `has_character_flag = in_dragonpit` -- dragon is in a dragonpit

### Dragonrider Trait

The `dragonrider` trait uses CK3's `tracks` system with two progression axes:

```pdx
tracks = {
    dragon_training = {
        30 = { dread_baseline_add = 15 }
        65 = { dread_baseline_add = 15 }
        100 = { dread_baseline_add = 20 }
    }
    dragon_bond = {
        30 = { diplomacy = 1 }
        65 = { learning = 1  monthly_lifestyle_xp_gain_mult = 0.05  vassal_opinion = 15 }
        100 = { martial = 1  movement_speed = 0.1  monthly_lifestyle_xp_gain_mult = 0.10 }
    }
}
```

Related rider traits: `dragonless_dragonrider` (lost dragon, still alive) and
`dragonwidowed` (dragon died, gives `health = -0.2`).

---

## Dragon Tree Structure

The dragon tree is a genealogy viewer for dragon bloodlines. It is **not** a
decision/interaction tree -- it is a family-tree-like data structure tracking
parent-child relationships among dragons.

### Storage Architecture

The tree uses two story cycle types, both owned by `title:c_ruins.holder`:

| Story Type                   | Purpose                | Key Variables                                                                                                                    |
| ---------------------------- | ---------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| `agot_dragon_tree_parent`    | One per parent dragon  | `var:this_parent` (the parent dragon), `child_container` (variable list of children)                                             |
| `agot_dragon_tree_structure` | One per tree (lineage) | `var:dragon_tree_founder`, `parent_story_container` (variable list of parent stories), `dragon_tree_gui` (variable list for GUI) |

Trees are tracked globally via `known_dragon_trees` (a global variable list).

### Tree Effects API

**File:** `common/scripted_effects/00_agot_dragon_tree_effects.txt`

#### `agot_dragon_tree_creation_effect`

Called when a dragon is spawned (hatching or creation). Determines parentage and
registers the dragon in the tree.

```pdx
agot_dragon_tree_creation_effect = {
    $DRAGON$ = { save_scope_as = dragon }
    if = {
        limit = {
            exists = scope:dragon.mother
            scope:dragon.mother = { has_trait = dragon }
        }
        agot_add_to_dragon_tree = { PARENT = scope:dragon.mother CHILD = scope:dragon }
    }
    # ... fallback for historical dragons like dragon_vermax
}
```

**Usage in spawning effects** (`00_agot_dragon_spawning_effects.txt`):

```pdx
agot_dragon_tree_creation_effect = { DRAGON = scope:dragon }
```

#### `agot_add_to_dragon_tree`

The core insertion logic. Handles three cases:

1. **Parent already in a tree with an existing parent story** -- adds child to
   existing `child_container` list.
2. **Parent in a tree but no parent story yet** -- creates a new
   `agot_dragon_tree_parent` story, adds child, links it to the structure story.
3. **Parent not in any tree** -- creates both a new `agot_dragon_tree_structure`
   and `agot_dragon_tree_parent` story, sets founder, registers in
   `known_dragon_trees` global list.

```pdx
agot_add_to_dragon_tree = {
    $PARENT$ = { save_scope_as = parent }
    $CHILD$ = { save_scope_as = child }
    # Check if parent exists in any known tree...
    # Case 1: add to existing parent story's child_container
    # Case 2: create parent story, link to existing structure
    # Case 3: create full new tree
}
```

### Tree GUI (Scripted GUIs)

**File:** `common/scripted_guis/00_agot_dragon_tree_scripted_gui.txt`

| Scripted GUI             | Purpose                                                                                |
| ------------------------ | -------------------------------------------------------------------------------------- |
| `agot_dragon_tree_top`   | Shown if character `has_variable = dragon_tree_stump`                                  |
| `agot_dragon_tree_child` | Shown if `scope:tree_story` has a parent story where `var:this_parent = root`          |
| `agot_dragon_tree_check` | Returns true if character appears anywhere in `known_dragon_trees`                     |
| `agot_open_dragon_tree`  | Sets display variables (`dragon_tree_being_shown`, `dragon_tree_stump`, member counts) |
| `agot_close_dragon_tree` | Cleans up all display variables                                                        |

### Tree Script Values

**File:** `common/script_values/00_agot_dragon_tree_values.txt`

- `dragon_tree_members_count` -- total members (founder + all children across
  all parent stories)
- `dragon_tree_members_alive_count` -- living members only
- `list_dragon_tree_members_count` -- same but scoped from a dragon character
  via global list lookup
- `dragon_tree_count` -- total number of known trees (debug)
- `dragon_tree_teacher_count` -- total parent stories across all trees (debug)

---

## Dragon Story Cycles

**File:** `common/story_cycles/agot_story_cycle_dragon.txt` and related files.

### `story_dragon_alive`

The main lifecycle story for every living dragon. Runs daily effect groups that
handle:

- **Location sync** -- ensures dragon stays at rider's location or in their
  dragonpit
- **Dragonpit management** -- moves dragons between pits when rider relocates
- **War detection** -- creates `story_dragon_at_war` when rider joins an army
- **Rider death cleanup** -- moves dead rider to `past_riders` variable list,
  clears `current_rider`
- **Wild dragon maintenance** -- handles lair behavior for unowned dragons

### `story_dragon_variable_storage`

**File:** `common/story_cycles/agot_story_cycle_dragon_variables.txt`

Stores all dragon visual/gene data on a story rather than the character. On
setup, it reads every gene variable from the dragon character and copies them to
story variables, then removes them from the character. Variables include:

- Size: `dragon_age`, `dragon_size_base`, `dragon_size`
- Colors: `gene_dragon_primary_color_hue/value`,
  `gene_dragon_secondary_hue/value`, `gene_dragon_tertiary_hue/value`
- Eyes: `gene_dragon_eye_color_hue/value`
- Morphology: `gene_dragon_horn_color_*`, `gene_dragon_brow_width`,
  `gene_dragon_cheek_width`, `gene_dragon_snout_*`, `gene_dragon_jaw_width`,
  etc.
- Features: `gene_dragon_center_fin_size`, `gene_dragon_back_spike_size`,
  `gene_dragon_neck_spike_size`, etc.

A daily effect group keeps `dragon_size` in sync with the current scripted value
calculation.

### `agot_dragonrider_forced_duel_story`

**File:** `common/story_cycles/agot_story_cycle_dragon_duels.txt`

Manages aerial dragon combat during wars:

- Maintains a `agot_dragonrider_forced_duel_list` of enemy riders
- Daily checks: adds new riders from `temp_rider_list`, selects opponents via
  `agot_dragonrider_opponent_selection_trigger`, triggers
  `agot_dragon_duel_effect`
- Auto-ends when the owner is no longer at war

### `story_dragon_doll`

**File:** `common/story_cycles/agot_story_cycle_dragon_doll.txt`

A childhood story cycle where a child crafts a dragon toy. Tracks crafting
progress via `var:events_fired` and creates doll variations using flag
combinations:

- Color: `vibrant_fit`, `vibrant_off`, `simple_complement`, `monotone`, etc.
- Wings: `large_fit`, `small_undersized`, `proportional_lopsided`, etc.
- Eyes: `buttons`, `gems_off`, `gems_pop`

---

## Dragon Personalities

**File:** `common/traits/00_agot_dragon_traits.txt`

### Personality Trait Pairs

Dragons get personality traits that affect taming, temperament, combat, and
dread. All have `category = personality` and
`potential = { has_trait = dragon }`.

| Trait                 | Opposite              | Key Flags                                                                                                               | AI Boldness |
| --------------------- | --------------------- | ----------------------------------------------------------------------------------------------------------------------- | ----------- |
| `dragon_aggressive`   | `dragon_friendly`     | `add_draconic_dread_10`, `subtract_temperament_12`, `subtract_taming_chance_10`, `add_combat_effectiveness_modifier_10` | 50          |
| `dragon_friendly`     | `dragon_aggressive`   | `subtract_draconic_dread_5`, `add_temperament_12`, `add_taming_chance_25`, `subtract_combat_effectiveness_modifier_5`   | -10         |
| `dragon_solitary`     | `dragon_cooperative`  | `subtract_draconic_dread_10`, `subtract_taming_chance_20`                                                               | 20          |
| `dragon_cooperative`  | `dragon_solitary`     | `add_temperament_4`, `add_taming_chance_5`                                                                              | -10         |
| `dragon_imperious`    | `dragon_supporting`   | `add_draconic_dread_2`, `subtract_temperament_5`, `subtract_taming_chance_4`                                            | 50          |
| `dragon_supporting`   | `dragon_imperious`    | `subtract_draconic_dread_2`, `add_temperament_9`, `add_taming_chance_8`                                                 | -50         |
| `dragon_impulsive`    | `dragon_calculating`  | `subtract_temperament_4`, `subtract_taming_chance_6`, `add_combat_effectiveness_modifier_2`                             | 50          |
| `dragon_calculating`  | `dragon_impulsive`    | `add_temperament_10`, `add_taming_chance_5`, `add_combat_effectiveness_modifier_10`                                     | -50         |
| `dragon_voracious`    | `dragon_restrained`   | `add_draconic_dread_4`, `subtract_temperament_5`, `add_taming_chance_9`                                                 | 20          |
| `dragon_restrained`   | `dragon_voracious`    | `add_temperament_4`, `subtract_taming_chance_4`                                                                         | -10         |
| `dragon_defiant`      | `dragon_accepting`    | `subtract_temperament_7`, `subtract_taming_chance_15`                                                                   | -50         |
| `dragon_accepting`    | `dragon_defiant`      | `add_temperament_5`, `add_taming_chance_8`                                                                              | 0           |
| `dragon_bloodthirsty` | `dragon_skittish`     | `add_draconic_dread_15`, `subtract_temperament_10`, `subtract_taming_chance_25`, `add_combat_effectiveness_modifier_10` | 20          |
| `dragon_skittish`     | `dragon_bloodthirsty` | `add_temperament_11`, `add_taming_chance_20`, `subtract_combat_effectiveness_modifier_15`                               | 0           |

Special non-paired: `dragon_cannibal` (`category = fame`,
`add_draconic_dread_7`, `subtract_temperament_25`, `subtract_taming_chance_10`).

### Flag System

Personality effects are not hard-coded modifiers -- they use `flag = `
declarations read by scripted triggers/values elsewhere. The naming convention
is `{action}_{stat}_{amount}`:

- `add_draconic_dread_X` / `subtract_draconic_dread_X`
- `add_temperament_X` / `subtract_temperament_X`
- `add_taming_chance_X` / `subtract_taming_chance_X`
- `add_combat_effectiveness_modifier_X` /
  `subtract_combat_effectiveness_modifier_X`

### Congenital & Physical Traits

Tiered genetic traits:

- **Physique:** `dragon_physique_good_1/2/3` and `dragon_physique_bad_1/2/3` --
  affect health and `add_size_modifier_X`/`subtract_size_modifier_X` flags
- **Speed:** `dragon_swift` vs `dragon_slow` --
  `add/subtract_combat_effectiveness_modifier_15`
- **Appearance:** `dragon_majestic` vs `dragon_ugly` --
  `add/subtract_rider_monthly_prestige_1`
- **Special:** `dragon_spindly` (combat+, size-, dread+), `dragon_fertile`
  (fertility = 0.5), `dragon_destined` (health+, `add_early_growth`)

### Education Tiers

Five tiers from `education_dragon_1` (worst: `subtract_temperament_8`,
`subtract_taming_chance_15`) to `education_dragon_5` (best:
`add_temperament_12`, `add_taming_chance_20`).

### Health Traits

- `dragon_wounded_1` through `dragon_wounded_5` -- escalating health penalties
  (-2 to -10) and combat debuffs
- `dragon_burned`, `dragon_ill`, `dragon_blind`
  (`subtract_combat_effectiveness_modifier_75`), `dragon_depressed`

---

## Dragon Dreams

**File:** `events/agot_events/agot_dragon_dreams_events.txt`

The `dragon_dreams` trait (`common/traits/00_agot_traits.txt`) grants:

- `intrigue = 4`, `stress_gain_mult = 0.25`
- `same_opinion = 15`, `general_opinion = -10`, `high_valyrian_opinion = 10`
- `enemy_hostile_scheme_phase_duration_add = medium_scheme_phase_duration_malus_value`

### Event: Scheme Discovery (`agot_dragon_dreams.0001`)

Triggered when a dragon dreamer discovers a hostile scheme. Uses
`scope:dragon_dreamer` and `scope:scheme`.

The description uses layered `first_valid` blocks to handle:

1. How the dreamer communicates the vision (own dream, visit, letter)
2. Scheme type (murder, abduction, elopement, artifact theft)
3. Who the target is (self, dreamer, someone else)
4. Whether this is a new or known dreamer (child discovering gift,
   self-discovery, known dreamer)

```pdx
immediate = {
    play_music_cue = "mx_cue_murder"
    scope:dragon_dreamer = {
        add_stress = major_stress_gain
        add_character_flag = {
            flag = dreamt
            days = 730
        }
    }
}
```

On choosing to act, new dreamers gain the trait:

```pdx
option = {
    trait = dragon_dreams
    scope:dragon_dreamer = {
        if = {
            limit = { has_character_flag = dragon_dreams }
            remove_character_flag = dragon_dreams
            add_trait = dragon_dreams
        }
    }
    scope:scheme = { expose_scheme = yes }
}
```

### Event: Harm Prevention (`agot_dragon_dreams.0100`)

A simpler event for visions that prevent harm. Uses
`has_character_flag = root_is_dreamer` or `var:dreamer` to determine
perspective.

---

## Dragon Animation Effects

**File:** `common/scripted_effects/00_agot_dragon_animation_effects.txt`

Two utility effects for event portrait animations:

### `agot_set_dragon_animation_flag_effect`

```pdx
agot_set_dragon_animation_flag_effect = {
    if = {
        limit = { NOT = { has_character_flag = $FLAG$ } }
        add_character_flag = $FLAG$
    }
    if = {
        limit = { $RIDING_DRAGON$ = yes }
        add_character_flag = currently_riding_dragon
    }
}
```

Valid `$FLAG$` values: `dragon_roar`, `dragon_flying`, `dragon_idle`,
`dragon_hover`.

### `agot_clear_dragon_animation_flags`

Removes all animation flags. Checks `is_alive = yes` before each removal to
avoid error log spam from dead characters.

---

## Sub-Mod Recipes

### Adding a Custom Dragon Personality Trait

Create a new trait file or append to an existing one. Follow the AGOT pattern
exactly:

```pdx
# common/traits/my_dragon_traits.txt
dragon_cunning = {
    category = personality
    desc = {
        first_valid = {
            triggered_desc = {
                trigger = { NOT = { exists = this } }
                desc = trait_dragon_cunning_desc
            }
            desc = trait_dragon_cunning_character_desc
        }
    }
    opposites = {
        dragon_naive  # Define the opposite trait too
    }
    potential = {
        has_trait = dragon
    }
    birth = 0
    random_creation = 0.0
    random_creation_weight = 0
    shown_in_ruler_designer = no

    ai_boldness = 10
    ai_rationality = 30
    ai_sociability = -10

    # Use the AGOT flag naming convention so existing scripted values pick them up
    flag = add_temperament_6
    flag = add_taming_chance_5
    flag = add_combat_effectiveness_modifier_5
}
```

You must also add localization keys: `trait_dragon_cunning`,
`trait_dragon_cunning_desc`, `trait_dragon_cunning_character_desc`.

### Creating a Dragon Story Cycle

To add a recurring behavior to dragons (e.g., a feeding cycle):

```pdx
# common/story_cycles/my_dragon_feeding_story.txt
story_dragon_feeding = {
    on_setup = {
        story_owner = {
            save_scope_as = dragon
        }
        set_variable = {
            name = hunger_level
            value = 0
        }
    }

    on_end = {}

    on_owner_death = {
        scope:story = { end_story = yes }
    }

    effect_group = {
        months = 3  # Check every 3 months
        triggered_effect = {
            trigger = {
                story_owner = {
                    has_trait = dragon
                    is_alive = yes
                    NOT = { has_character_flag = recently_fed }
                }
            }
            effect = {
                scope:story = {
                    change_variable = {
                        name = hunger_level
                        add = 1
                    }
                }
                story_owner = {
                    trigger_event = my_dragon_feeding.0001
                }
            }
        }
    }
}
```

Start the story from an event or scripted effect:

```pdx
scope:dragon = {
    create_story = story_dragon_feeding
}
```

### Custom Dragon Dreams

To add a new type of prophetic dream, fire the event with the right scopes:

```pdx
# events/my_dragon_dreams.txt
namespace = my_dragon_dreams

my_dragon_dreams.0001 = {
    type = character_event
    title = my_dragon_dreams.0001.t
    desc = my_dragon_dreams.0001.desc
    theme = mystic

    trigger = {
        has_trait = dragon_dreams
        NOT = { has_character_flag = dreamt }  # Respect the 730-day cooldown
    }

    weight_multiplier = {
        base = 1
        modifier = {
            add = 2
            has_trait = mystic_2
        }
    }

    immediate = {
        add_character_flag = {
            flag = dreamt
            days = 730
        }
        add_stress = medium_stress_gain
    }

    option = {
        name = my_dragon_dreams.0001.a
        # The prophetic outcome
    }
}
```

Key points:

- Check `has_character_flag = dreamt` to respect the AGOT-wide 730-day cooldown
  between dreams.
- Dragon dreams always cost stress (`add_stress`).
- Use `scope:dragon_dreamer` if integrating with the AGOT scheme discovery
  pipeline.

---

## Pitfalls

1. **Tree anchor is `title:c_ruins.holder`** -- all dragon tree stories are
   owned by this hidden character. If you create stories on the wrong scope, the
   tree GUI will not find them. Always use
   `title:c_ruins.holder = { create_story = { ... } }` for tree-related stories.

2. **Variable list vs variable** -- the tree uses `add_to_variable_list`
   extensively. Do not use `set_variable` where a list is expected
   (`child_container`, `parent_story_container`, `dragon_tree_gui`,
   `known_dragon_trees`). Using `set_variable` would overwrite the entire list.

3. **Dragon personality flags are string-matched** -- the
   `flag = add_taming_chance_25` declarations are parsed by scripted
   values/triggers elsewhere. If you invent a new flag name, you must also add
   the corresponding scripted value logic that reads it. Existing AGOT values
   only check for the flags already defined.

4. **Animation flags on dead characters** -- always guard flag removal with
   `is_alive = yes` as AGOT does in `agot_clear_dragon_animation_flags`.
   Removing flags from dead characters produces error log spam.

5. **Dream cooldown** -- the `dreamt` character flag lasts 730 days. If your
   sub-mod fires dream events without checking this flag, players can get
   dream-spammed. Always check `NOT = { has_character_flag = dreamt }`.

6. **Dragon trait `can_have_children = no`** -- dragons cannot reproduce through
   normal CK3 mechanics. AGOT handles dragon breeding through custom scripted
   effects and egg systems. Do not rely on vanilla birth events.

7. **`story_dragon_variable_storage` cleans up character variables** -- after
   setup, the story removes all gene variables from the dragon character and
   stores them on itself. If your code reads dragon gene variables directly from
   the character after the story runs, they will be gone. Read them from the
   story instead.

8. **The `dragonrider` tracks system** -- `dragon_training` and `dragon_bond`
   are CK3 trait tracks. Modifying track values requires the `add_trait_xp`
   effect targeting the `dragonrider` trait. Do not try to set track values
   directly.

9. **Widowed story pattern** -- the AGOT `story_agot_widowed` cycle (in
   `events/agot_story_cycles/agot_story_cycle_widowed_events.txt`) demonstrates
   the general pattern: `create_story` with a type, store key data as story
   variables, fire chained events, `end_story = yes` on resolution. Dragon story
   cycles follow this same architecture but with daily/monthly effect groups
   instead of one-shot event chains.
