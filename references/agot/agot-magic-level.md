# AGOT: Magic Level System

## Overview

The AGOT mod tracks the state of magic in the world through a single **global
variable** called `magic_level`. This integer variable (values 0, 1, or 2) is
driven entirely by the number of living dragons. It acts as a global toggle that
other systems -- glass candles, dragon eggs, artifact visuals, foresight traits
-- check to decide what is possible.

The variable is stored on the global scope and accessed as
`global_var:magic_level`.

## Key Concepts

### Magic Level Values

| Value | Meaning    | Condition                 |
| ----- | ---------- | ------------------------- |
| `0`   | No magic   | Zero living dragons       |
| `1`   | Some magic | 1-9 living dragons        |
| `2`   | High magic | 10 or more living dragons |

The living dragon count comes from the global list `living_dragons`.

### Initialization

At game start the effect `agot_init_magic_level_effect` sets the initial value
based on the current dragon population:

```pdx
agot_init_magic_level_effect = {
    if = {
        limit = {
            agot_is_any_dragon_alive = no
        }
        set_global_variable = {
            name = magic_level
            value = 0 # no magic
        }
    }
    else_if = {
        limit = {
            any_in_global_list = {
                variable = living_dragons
                count < 10
            }
        }
        set_global_variable = {
            name = magic_level
            value = 1 # some magic
        }
    }
    else = {
        set_global_variable = {
            name = magic_level
            value = 2 # more magic
        }
    }
}
```

**Source:** `common/scripted_effects/00_agot_magic_effects.txt`

This effect is called from `common/scripted_effects/00_agot_dragon_effects.txt`
during the dragon system's startup routine.

### Dynamic Updates

The magic level is recalculated every time a dragon is born or dies, via two
dedicated effects:

- **`agot_dragon_birth_magic_effect`** -- called when a dragon hatches/is born.
  Promotes `0 -> 1` when the first dragon appears, and `1 -> 2` when the 10th
  dragon appears.
- **`agot_dragon_death_magic_effect`** -- called when a dragon dies. Demotes
  `2 -> 1` when the count drops below 10, and `1 -> 0` when the last dragon
  dies.

Both effects also call `agot_update_glass_candles_effect` to reforge all glass
candle artifacts with the appropriate modifier tier.

## Scripted API

### Triggers

Located in `common/scripted_triggers/00_agot_magic_triggers.txt`:

| Trigger                       | Scope | What it checks                                                         |
| ----------------------------- | ----- | ---------------------------------------------------------------------- |
| `agot_is_world_magic_trigger` | Any   | `global_var:magic_level > 0` -- true when at least one dragon is alive |

Located in `common/scripted_triggers/00_agot_dragon_triggers.txt`:

| Trigger                          | Scope | What it checks                                                               |
| -------------------------------- | ----- | ---------------------------------------------------------------------------- |
| `agot_dragon_population_extinct` | Any   | `global_var:magic_level = 0` (with existence guard)                          |
| `agot_dragon_population_alive`   | Any   | `exists = global_var:magic_level` AND `NOT = { global_var:magic_level = 0 }` |

### Effects

Located in `common/scripted_effects/00_agot_magic_effects.txt`:

| Effect                           | Scope  | Purpose                                            |
| -------------------------------- | ------ | -------------------------------------------------- |
| `agot_init_magic_level_effect`   | Any    | Sets initial `magic_level` based on dragon count   |
| `agot_dragon_birth_magic_effect` | Dragon | Promotes magic level when dragon population grows  |
| `agot_dragon_death_magic_effect` | Dragon | Demotes magic level when dragon population shrinks |

### Checking the Variable Directly

You can read the value anywhere with:

```pdx
# Boolean check: is there any magic at all?
global_var:magic_level > 0

# Exact level check
global_var:magic_level = 2

# Existence guard (good practice)
exists = global_var:magic_level
```

## Systems Affected by Magic Level

### Glass Candles

Glass candles are artifacts that change behavior based on magic level. Three
systems coordinate:

1. **Artifact template**
   (`common/artifacts/templates/00_agot_misc_templates.txt`): The
   `glass_candle_artifact_template` uses a `can_benefit` block that requires
   `NOT = { global_var:magic_level = 0 }`. When magic is absent, the candle
   falls back to a weaker modifier (`learning = 1`, `monthly_prestige = 0.1`).

2. **Artifact modifiers** (`common/modifiers/00_agot_artifact_modifiers.txt`):
   Two tiers of modifier exist:
   - `glass_candle_modifier` (magic level 1): `diplomatic_range_mult = 0.5`,
     `monthly_prestige = 0.25`, `learning = 1`
   - `glass_candle_modifier_higher` (magic level 2):
     `diplomatic_range_mult = 0.75`, `monthly_prestige = 0.5`, `learning = 1`

3. **Reforge on transition**
   (`common/scripted_effects/00_agot_artifact_effects.txt`):
   `agot_update_glass_candles_effect` iterates `every_glass_candle` and reforges
   each one with the appropriate modifier when the magic level changes. At magic
   level 2, candles are reforged with `glass_candle_modifier_higher`.

4. **Visual switching** (`common/artifacts/visuals/00_agot_filler_visuals.txt`):
   Glass candle 3D models swap between lit and unlit variants based on
   `agot_is_world_magic_trigger`. Six candle colors (black, green, blue, purple,
   white, red) each have a `_entity` (lit) and `_unlit_entity` variant.

5. **Custom localization**
   (`common/customizable_localization/00_agot_artifact_custom_loc.txt`): The
   `GetCandleMagic` custom loc key returns `agot_glass_candle_unlit_desc` when
   `global_var:magic_level = 0`, and `agot_glass_candle_lit_desc` otherwise.

### Dragon Eggs

When magic drops to level 0 (last dragon dies), the effect
`agot_dragon_extinction_effect` is called. It iterates every artifact with the
`dragon_egg` variable and calls `agot_dudify_egg` on each one, turning them into
inert "dud" eggs that cannot hatch.

When magic returns to level 1 (first dragon born), `agot_dragon_revival_effect`
is called. It resets the dud status on eggs and re-enables cradled-egg hatching
mechanics.

### Foresight Traits

The magic triggers file also contains
`agot_dragon_dream_scheme_discovery_trigger` and
`agot_greensight_scheme_discovery_trigger`, and
`agot_prevent_harm_event_with_foresight_trigger`. While these triggers do not
directly check `magic_level`, they are co-located in the magic system and relate
to the supernatural abilities that are thematically tied to the presence of
dragons and magic in the world.

## Sub-Mod Recipes

### Adding a New Magic-Gated Feature

Gate any feature behind the magic level by checking the global variable:

```pdx
# In a decision, event, or trigger:
trigger = {
    exists = global_var:magic_level
    global_var:magic_level >= 1  # requires at least some magic
}
```

### Creating a Magic-Sensitive Artifact

Follow the glass candle pattern -- use a template with `can_benefit` that checks
magic level, and provide a `fallback` block for the no-magic state:

```pdx
my_magic_artifact_template = {
    can_benefit = {
        custom_tooltip = {
            text = my_artifact_requires_magic.tt
            NOT = { global_var:magic_level = 0 }
        }
    }
    fallback = {
        monthly_prestige = 0.1  # weak stats when magic is absent
    }
    ai_score = {
        value = 100
    }
}
```

### Two-Tier Modifiers (Level 1 vs Level 2)

To give an artifact different power at magic levels 1 and 2, define two
modifiers and reforge based on the level (same pattern as glass candles):

```pdx
# In a scripted effect that runs when magic level changes:
if = {
    limit = { global_var:magic_level = 2 }
    reforge_artifact = {
        type = my_magic_item
        modifier = my_item_modifier_higher
        generate_history = no
    }
}
else = {
    reforge_artifact = {
        type = my_magic_item
        modifier = my_item_modifier
        generate_history = no
    }
}
```

Remember to hook your reforge logic into the magic-level transition. You can do
this by adding your own effect call inside a patch that extends or wraps
`agot_dragon_birth_magic_effect` and `agot_dragon_death_magic_effect`.

### Forcing a Magic Level (Debug/Testing)

```pdx
set_global_variable = {
    name = magic_level
    value = 2
}
agot_update_glass_candles_effect = yes
```

This sets high magic without needing actual dragons. Useful for testing, but
will desync from the real dragon count.

## Pitfalls

1. **Always guard with `exists`**: The variable may not be set yet at game
   start. Always check `exists = global_var:magic_level` before comparing its
   value, especially in on_actions that fire early.

2. **The variable is an integer, not a flag**: Use `=`, `>`, `>=`, `<`
   comparisons. Do not treat it as a boolean (`magic_level = yes` will not
   work).

3. **Transitions trigger side effects**: Changing the magic level is not just
   setting a number. The birth/death effects also call
   `agot_update_glass_candles_effect`, `agot_dragon_revival_effect`, and
   `agot_dragon_extinction_effect`. If you set `magic_level` directly without
   calling these, glass candles will not update and eggs will not change state.

4. **Dragon death edge case**: The `agot_dragon_death_magic_effect` has a
   comment noting uncertainty about whether a dying dragon is still counted in
   `living_dragons` at the time the effect fires. The code checks `count = 1`
   (meaning the dying dragon is the last one), suggesting the dragon is still in
   the list when checked.

5. **No game rule for magic level**: Unlike dragon bloodlines or culling, there
   is no game rule to directly configure the magic level. It is purely derived
   from dragon population. If you want a game-rule override, you would need to
   add one yourself and hook it into the init effect.

6. **`every_glass_candle` is a custom iterator**: This is not a vanilla CK3
   scope -- it is defined by AGOT. Only use it in contexts where the AGOT mod is
   loaded.

7. **Desync risk with manual overrides**: If you `set_global_variable` for
   `magic_level` without matching the actual dragon count, the next dragon birth
   or death will recalculate and potentially overwrite your value. For
   persistent overrides, you need to also patch the birth/death effects.
