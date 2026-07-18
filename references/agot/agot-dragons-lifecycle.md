# AGOT: Dragon Eggs, Genetics & Dragonpit

## Overview

AGOT implements dragons as full CK3 characters with the `dragon` trait. Dragon
eggs are artifacts that can hatch into dragon characters. The mod includes a
genetics system for congenital traits inherited from dragon parents, a visual
appearance system driven by color variables and gene parameters, and a dragonpit
mechanic that governs where dragons are housed and how they grow.

This guide documents the scripted API that sub-modders can use to create eggs,
spawn dragons, manage genetics, control appearance, and operate dragonpits.

### Source Files Covered

| File                                                                   | Purpose                                                           |
| ---------------------------------------------------------------------- | ----------------------------------------------------------------- |
| `common/scripted_effects/00_agot_dragon_eggs_effects.txt`              | Egg creation, color selection, egg-to-dragon parentage            |
| `common/scripted_effects/00_agot_dragon_spawning_effects.txt`          | Spawning dragons of various ages, hatching from eggs              |
| `common/scripted_effects/00_agot_dragon_congenital_traits_effects.txt` | Genetics inheritance for congenital traits                        |
| `common/scripted_effects/00_agot_dragon_appearance_effects.txt`        | Visual appearance genes (color, horns, body shape)                |
| `common/scripted_effects/00_agot_dragonpit_effects.txt`                | Dragonpit add/remove/toggle, dragonkeeper generation              |
| `common/scripted_effects/00_agot_dragon_effects.txt`                   | Aging, growth, ownership, bonding, trait clearing                 |
| `common/scripted_effects/00_agot_dragon_tree_effects.txt`              | Dragon family tree (story-based GUI structure)                    |
| `common/traits/00_agot_dragon_traits.txt`                              | Dragon base trait, personality, congenital, education traits      |
| `common/traits/00_agot_canon_dragon_traits.txt`                        | Hidden identity traits for canon dragons (Balerion, Vhagar, etc.) |
| `events/agot_events/agot_dragon_egg_events.txt`                        | Egg cradling, dud handling, hatching events                       |
| `events/agot_events/agot_dragon_pits_events.txt`                       | Dragonpit restoration, dragon storage events                      |

---

## Key Concepts

### Dragon Eggs as Artifacts

Dragon eggs are CK3 artifacts with the type `dragon_egg`. Each egg stores its
color in a variable:

```pdx
# On the artifact scope:
set_variable = { name = dragon_egg_color value = flag:red }
set_variable = { name = dragon_egg value = yes }
```

Key artifact variables on an egg:

- `dragon_egg` -- marks this artifact as a dragon egg
- `dragon_egg_color` -- a flag value like `flag:red`, `flag:gold`, `flag:frost`,
  etc.
- `dragon_parent` -- reference to the mother/father dragon (if egg was laid)
- `dragon_parent_other` -- second parent dragon (if known)
- `cradled_egg` -- set when the egg is assigned to cradle with a child
- `cradled_egg_year` -- the year cradling started
- `dud_egg` -- marks the egg as permanently unable to hatch (no living dragons)
- `pitted_egg` -- set when egg is stored in a dragonpit

### Dragon Hatching Flow

1. A character owns an egg artifact (given at birth, found, or received).
2. The egg is cradled with a child (`cradled_egg` variable set).
3. When conditions are met, `agot_spawn_bonded_hatchling_from_egg_effect` is
   called.
4. This creates a dragon character, sets parentage from the egg, inherits
   genetics, bonds it to the owner, and destroys the egg artifact.

### Dragon as Characters

Dragons are characters with `has_trait = dragon`. They are courtiers of their
owner. Key flags:

- `owned_dragon` -- dragon belongs to a character
- `in_dragonpit` -- dragon is currently housed in a dragonpit
- Variable `current_rider` -- the character who rides this dragon
- Variable `current_dragon` (on rider) -- the dragon they ride

### Dragon Growth and Aging

Dragons grow via `agot_apply_dragon_aging_effect`, called periodically:

- **Age < 11**: +3 prowess, +3 size per cycle
- **Age 11-14**: +2 prowess, +2 size per cycle
- **Age 15+**: random growth (70% chance +1, 20% chance +2, 10% no growth)
- **In dragonpit**: reduced growth (60% chance +1, 10% chance +2, 30% no growth)
- **Dragonstone dragonpit**: less reduced (55% +1, 15% +2, 5% no growth) --
  volcanic magic

The `dragon_destined` trait grants +40 prowess and +40 size after the first
year.

---

## AGOT Scripted API

### Egg Effects

All egg effects live in `00_agot_dragon_eggs_effects.txt` (~2466 lines).

#### Creating Eggs

The core egg creation chain is:

```
create_artifact_dragon_egg_<COLOR>_effect = { OWNER = <character> }
  -> create_artifact_dragon_egg_wrapper_effect = { OWNER = ... COLOR = <color> }
    -> create_artifact_dragon_egg_effect = { OWNER = ... COLOR = <color> TYPE = dragon_egg }
```

The base `create_artifact_dragon_egg_effect` does:

1. Creates an illustrious-rarity artifact with `type = dragon_egg`
2. Sets `dragon_egg` and `dragon_egg_color` variables on it
3. If `agot_dragon_population_alive = yes` -- egg is viable
4. If no living dragons -- marks it as `dud_egg` and reforges to pedestal type
5. If `scope:dragon_parent` exists -- sets parent variables and inherits
   congenital traits

**Available egg colors** (53 total):

| Plain Colors                                                                                                                                        | Fancy/Multicolor                                                                                                                                                                                                                                                                                         | Metallic                                                                                     |
| --------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| red, palered, orange, yellow, pink, white, black, grey_1, grey_2, blue, darkblue, green_1, green_2, purple, brown, lightBrown, teal, lime, greyBlue | blackdarkred, blackred, darkred, magma, sunburst, flame, blackyellow, yellowgreen, greygreenyellow, blackgreen, greenorange, greengrey, frost, icefire, palebluepink, darkpurple, pinkspot, palepink, rainbow, brownspots, tan, redYellow, blackWhite, weirwood, redGreen, tealSpot, spotPurple, america | bronze, silver, gold, rainbowgold, goldpink, purplegold, bluebronze, whitegold, redblackgold |

#### Random Egg Generation

```pdx
# Equal weight across all 53 colors:
agot_create_random_dragon_egg_artifact = { OWNER = root }

# 75% plain / 25% fancy -- weighted by color rarity:
agot_create_weighted_dragon_egg_artifact = { OWNER = root }

# Color-family randoms:
agot_create_random_red_dragon_egg_artifact = { OWNER = root }
agot_create_random_black_dragon_egg_artifact = { OWNER = root }
agot_create_random_white_dragon_egg_artifact = { OWNER = root }
agot_create_random_orange_dragon_egg_artifact = { OWNER = root }
agot_create_random_yellow_dragon_egg_artifact = { OWNER = root }
```

#### Egg Selection and Duplication

```pdx
# Recreate an egg based on a previously selected artifact's color variable:
agot_create_dragon_egg_from_selection = { OWNER = root }
# Reads: $OWNER$.var:selected_artifact_tall.var:dragon_egg_color

# Create one of every egg (debug):
agot_create_every_dragon_egg_artifact = { OWNER = root }
```

#### Egg Removal and Duds

```pdx
# Destroy an egg artifact:
agot_remove_dragon_egg = { EGG = scope:egg }  # Simply calls destroy_artifact

# Turn a viable egg into a dud (decorative pedestal):
agot_dudify_egg = yes  # Called on artifact scope
# Removes cradled_egg, pitted_egg; sets dud_egg; reforges to pedestal
```

#### Egg Parentage

```pdx
# After hatching, set the dragon's CK3 parents from egg variables:
agot_set_dragon_parents = { EGG = scope:egg }
# Reads var:dragon_parent and var:dragon_parent_other from the egg
# Sets mother/father and house on scope:dragon
```

### Spawning Effects

All spawning effects live in `00_agot_dragon_spawning_effects.txt`.

#### Spawning by Age Category

Each uses a template and saves the result as `scope:dragon`:

```pdx
# Hatchling (age 0, from egg):
agot_spawn_owned_hatchling_from_egg_effect = { OWNER = root EGG = scope:egg }

# Bonded hatchling (hatches + bonds to owner + creates memory):
agot_spawn_bonded_hatchling_from_egg_effect = { OWNER = root EGG = scope:egg }

# Wild hatchling (no owner):
agot_spawn_wild_hatchling_from_egg_effect = { EGG = scope:egg }

# Owned adult (age 30-100, random):
agot_spawn_owned_adult_dragon_effect = yes  # Scoped to owner character

# Wild adult (age 30-100):
agot_spawn_wild_dragon_effect = yes

# Wild child (age 0):
agot_spawn_wild_child_dragon_effect = yes

# Age-specific (used in history setup):
agot_spawn_young_dragon_effect = yes   # agot_young_dragon_template
agot_spawn_adult_dragon_effect = yes   # agot_adult_dragon_template
agot_spawn_old_dragon_effect = yes     # agot_old_dragon_template
agot_spawn_monster_dragon_effect = yes # agot_monster_dragon_template
```

#### Hatching Flow Detail

`agot_spawn_bonded_hatchling_from_egg_effect` does the following:

1. Calls `agot_spawn_owned_hatchling_from_egg_effect` (which creates the dragon
   character)
2. Creates a `agot_hatched_egg` character memory
3. Calls `agot_bond_dragon_relation_effect` to establish the rider-dragon bond
4. If `scope:cradlemate` exists and has `destiny_child` variable, adds
   `dragon_destined` trait

Inside `agot_spawn_owned_hatchling_from_egg_effect`:

1. Checks for canon dragon spawning (if `agot_canon_dragons_enabled`)
2. Otherwise creates character with `agot_dragon_hatchling_template`
3. Calls `agot_set_as_owned_dragon` to make it a courtier of the owner
4. Calls `agot_set_dragon_parents` to establish CK3 parentage from egg
5. Calls `agot_dragon_tree_creation_effect` to add to the dragon family tree GUI
6. Calls `agot_remove_dragon_egg` to destroy the egg artifact

#### Ownership

```pdx
# Make a dragon owned by a character:
agot_set_as_owned_dragon = { OWNER = scope:owner DRAGON = scope:dragon }
# Adds dragon as courtier, sets owned_dragon flag, handles dragonpit removal if needed

# Bond a dragon (taming relationship):
agot_bond_dragon_relation_effect = { ACTOR = scope:rider DRAGON = scope:dragon }
# Sets agot_dragon relation, creates memory, removes "the Dragonless" nickname if present

# Tame a dragon (full taming):
agot_tame_dragon = { TAMER = scope:tamer DRAGON = scope:dragon }
```

### Genetics Effects

Defined in `00_agot_dragon_congenital_traits_effects.txt`. The genetics system
uses a parent-inheritance model with five probability tiers.

#### Inheritance Probability Tiers

Each congenital trait is checked against the dragon's parents using scripted
triggers:

| Trigger                                                              | Meaning                                          |
| -------------------------------------------------------------------- | ------------------------------------------------ |
| `agot_dragon_inheritance_both_parents_have_active_trait`             | Both parents have the trait (active)             |
| `agot_dragon_inheritance_both_parents_have_active_or_inactive_trait` | Both parents carry it (one active, one inactive) |
| `agot_dragon_inheritance_one_parent_has_active_trait`                | One parent has it active                         |
| `agot_dragon_inheritance_both_parents_have_inactive_trait`           | Both parents carry it inactive                   |
| `agot_dragon_inheritance_one_parent_has_inactive_trait`              | One parent carries it inactive                   |

Each trigger maps to a script value (e.g.,
`agot_dragon_inheritance_both_parents_active_trait_value`) that determines the
percentage chance. The system also supports inactive inheritance (recessive
genes) using `make_trait_inactive` instead of `add_trait`.

For leveled traits (like physique_good_1/2/3), AGOT uses extended triggers:

```pdx
agot_dragon_inheritance_both_parents_have_active_or_inactive_leveled_trait = {
    DRAGON = scope:dragon
    TRAIT = dragon_physique_good_3
    ALT_TRAIT_1 = dragon_physique_good_2
    ALT_TRAIT_2 = dragon_physique_good_1
}
```

#### Congenital Trait Effects

Each trait category has a dedicated effect:

```pdx
# Physique (leveled: 1/2/3, good and bad):
agot_dragon_physique_good_effect = { DRAGON = scope:dragon }
agot_dragon_physique_bad_effect = { DRAGON = scope:dragon }

# Binary congenital traits:
agot_dragon_swift_effect = { DRAGON = scope:dragon }
agot_dragon_slow_effect = { DRAGON = scope:dragon }
agot_dragon_spindly_effect = { DRAGON = scope:dragon }
agot_dragon_majestic_effect = { DRAGON = scope:dragon }
agot_dragon_ugly_effect = { DRAGON = scope:dragon }
agot_dragon_fertile_effect = { DRAGON = scope:dragon }
```

Each effect:

1. Checks the highest-level trait first (e.g., physique_good_3)
2. Rolls for active inheritance based on parent matching
3. If no active trait was given, rolls for inactive (recessive) inheritance
4. For leveled traits, checks each level in descending order, skipping if a
   higher level was already assigned

#### Clearing Genetics

```pdx
agot_clear_dragon_genetic_traits_effect = yes
# Removes all congenital traits from the dragon (used in redesign/debug)
```

### Appearance Effects

Defined in `00_agot_dragon_appearance_effects.txt`. The appearance system sets
gene variables on dragon characters that the 3D model system reads.

#### Main Entry Point

```pdx
agot_gen_appearance_variables = yes  # Called on dragon scope
```

This effect:

1. Checks for `baby_dragon` variable (hatchling from egg)
2. Generates or uses existing `primary_color`, `secondary_color`,
   `tertiary_color` variables
3. Assigns color genes via `agot_assign_primary_color_effect` etc.
4. If egg color is metallic, sets `gene_dragon_metallic_scales_strength`
5. Generates all morphology genes (eye color, horn color, brow, cheek, chin,
   crest, head shape, horn shape, body shading)

#### Color System

Colors are stored as flag variables: `flag:white`, `flag:grey`, `flag:black`,
`flag:red`, `flag:orange`, `flag:yellow`, `flag:green`, `flag:teal`,
`flag:blue`, `flag:purple`, `flag:pink`, `flag:fuschia`.

The assignment effects map each flag to specific HSV-like gene values:

```pdx
# Example from agot_assign_primary_color_effect:
switch = {
    trigger = var:primary_color
    flag:white = {
        set_variable = { name = gene_dragon_primary_color_hue value = {0 0} }
        set_variable = { name = gene_dragon_primary_color_value value = { dragon_value_white_min dragon_value_white_max } }
    }
    flag:red = {
        set_variable = { name = gene_dragon_primary_color_hue value = { ... } }
        # ...
    }
}
```

#### Gene Variables Set

| Variable                               | Range | Description                    |
| -------------------------------------- | ----- | ------------------------------ |
| `gene_dragon_primary_color_hue`        | 0-1   | Primary scale color hue        |
| `gene_dragon_primary_color_value`      | 0-1   | Primary scale brightness       |
| `gene_dragon_secondary_color_hue`      | 0-1   | Secondary/accent color hue     |
| `gene_dragon_secondary_color_value`    | 0-1   | Secondary brightness           |
| `gene_dragon_tertiary_color_hue`       | 0-1   | Tertiary/detail color hue      |
| `gene_dragon_tertiary_color_value`     | 0-1   | Tertiary brightness            |
| `gene_dragon_metallic_scales_strength` | 0-1   | How metallic the scales appear |
| `gene_dragon_eye_color_hue`            | 0-1   | Eye color hue                  |
| `gene_dragon_eye_color_value`          | 0-1   | Eye color brightness           |
| `gene_dragon_horn_color_hue`           | 0-1   | Horn coloring                  |
| `gene_dragon_horn_color_value`         | 0-1   | Horn brightness                |
| `gene_dragon_brow_width`               | 0-1   | Brow ridge width               |
| `gene_dragon_cheek_width`              | 0-1   | Cheek width                    |
| `gene_dragon_chin_profile`             | 0-1   | Chin shape                     |
| `gene_dragon_crest_depth`              | 0-1   | Head crest depth               |
| `gene_dragon_head_roundness`           | 0-1   | Head roundness                 |
| `gene_dragon_horns_eyebrow_length`     | 0-1   | Eyebrow-horn length            |
| `gene_dragon_main_horn_shape_template` | 1-10  | Horn shape template index      |
| `gene_dragon_main_horn_shape_value`    | 0-1   | Horn shape variation           |
| `gene_dragon_body_shading_template`    | 1-11+ | Body shading pattern           |

### Dragonpit Effects

Defined in `00_agot_dragonpit_effects.txt`.

#### Setting Up a Dragonpit

```pdx
# Called when a generic dragonpit building is constructed:
agot_create_generic_dragonpit_scripted_effect = { DRAGON_PIT_OWNER = root }
# Triggers agot_dragonkeepers.0001 event
# Sets has_dragonkeeper_order variable on the county
# Adds dragonpit_close_family_law
# Sets dragonpit amenity level to 3 (if EP1 DLC)
```

#### Sending Dragons to the Dragonpit

```pdx
# Full version (with event triggers):
agot_send_to_dragonpit_effect = {
    DRAGON = scope:dragon
    DRAGONPIT_HOLDER = scope:owner
    DRAGONPIT_COUNTY = scope:county
}
# Adds in_dragonpit flag, agot_dragon_in_dragonpit modifier
# Sets pitted_dragon_location variable
# Adds dragon to county's dragons_in_pit list variable
# Removes agot_roaming_dragon county modifier if no free dragons remain

# Silent version (no events):
agot_send_to_dragonpit_no_event = {
    DRAGON = scope:dragon
    DRAGONPIT_COUNTY = scope:county
}
```

#### Removing Dragons from the Dragonpit

```pdx
# Full version (with roaming dragon event):
agot_remove_from_dragonpit_effect = {
    DRAGON = scope:dragon
    DRAGONPIT_HOLDER = scope:owner
    DRAGONPIT_COUNTY = scope:county
}
# Removes in_dragonpit flag, modifier, pitted_dragon_location
# Removes from county's dragons_in_pit list
# If dragon is old enough (dragon_poses_a_danger_age), triggers agot_dragon_pits.1100

# Silent version:
agot_remove_from_dragonpit_no_event = { DRAGON = ... DRAGONPIT_COUNTY = ... }

# Skip county effects (uses stored location):
agot_remove_from_dragonpit_skip_county_effects = { DRAGON = scope:dragon }
```

#### Toggling Dragonpit Status

```pdx
# Player-facing toggle (checks for multiple pits, fires events):
agot_change_dragonpit_status = yes  # Called on dragon scope

# AI version:
agot_change_dragonpit_status_ai = { OWNER = scope:owner DRAGON_REC = scope:dragon }
```

The toggle logic checks `has_character_flag = in_dragonpit`:

- If in pit: removes from dragonpit
- If owned but not in pit: sends to dragonpit
- If wild: forces wild dragon into dragonpit (triggers `agot_dragon_pits.1200`)

#### War Transitions

```pdx
# Temporarily remove from pit for war (preserves return location):
agot_remove_from_dragonpit_war = { DRAGON = scope:dragon }
# Stores return_pitted_dragon_location before removing

# Return to pit after war:
agot_send_to_dragonpit_war = { DRAGON = scope:dragon }
# Reads return_pitted_dragon_location to restore position
```

#### Dragonpit Buildings

The system recognizes these buildings:

- `generic_dragon_pit_01` -- generic dragonpit (castle holding)
- `dragonpit_01` -- historical King's Landing Dragonpit
- `dragonpit_ruins_03` -- fully restored ruin version
- `agot_dragonmont_01` -- Dragonstone's Dragonmont

#### Dragonkeeper Generation

```pdx
agot_generate_head_dragonkeeper = yes  # Called on pit holder scope
```

Generates a Head Dragonkeeper character using templates based on amenity funding
level (1-5):

- `agot_head_dragonkeeper_lowest_funding_template` (level 1)
- `agot_head_dragonkeeper_low_funding_template` (level 2)
- `agot_head_dragonkeeper_med_funding_template` (level 3)
- `agot_head_dragonkeeper_high_funding_template` (level 4)
- `agot_head_dragonkeeper_grand_funding_template` (level 5)

The amenity type is `agot_dragonpit_amenities`. Without EP1 DLC, a random
template is used.

---

## Dragon Traits

### Base Trait

`dragon` -- Applied to all dragon characters. Grants:

- `health = 5`, `life_expectancy = 150`
- `can_have_children = no`, `fertility = 0.0`
- `character_travel_speed = 150`, `character_travel_safety = 200`
- Blocks inheritance, marriage, combat leadership
- Dynamic name: shows as Wild, Owned, Tamed, or Bound depending on status

### Rider Traits

| Trait                    | Description                                                                                                                         |
| ------------------------ | ----------------------------------------------------------------------------------------------------------------------------------- |
| `dragonrider`            | Active rider. Tracks: `dragon_training` (30/65/100) and `dragon_bond` (30/65/100). Grants prestige, dread, martial, vassal opinion. |
| `dragonless_dragonrider` | Former rider whose dragon died but rider survived.                                                                                  |
| `dragonwidowed`          | Rider whose dragon died (health penalty: -0.2).                                                                                     |

### Personality Traits (Opposite Pairs)

| Trait                 | Opposite              | Key Flags                              |
| --------------------- | --------------------- | -------------------------------------- |
| `dragon_aggressive`   | `dragon_friendly`     | +dread, -temperament, -taming, +combat |
| `dragon_friendly`     | `dragon_aggressive`   | -dread, +temperament, +taming, -combat |
| `dragon_solitary`     | `dragon_cooperative`  | -dread, -taming                        |
| `dragon_cooperative`  | `dragon_solitary`     | +temperament, +taming                  |
| `dragon_imperious`    | `dragon_supporting`   | +dread, -temperament, -taming          |
| `dragon_supporting`   | `dragon_imperious`    | -dread, +temperament, +taming          |
| `dragon_impulsive`    | `dragon_calculating`  | -temperament, -taming, +combat         |
| `dragon_calculating`  | `dragon_impulsive`    | +temperament, +taming, +combat         |
| `dragon_voracious`    | `dragon_restrained`   | +dread, -temperament, +taming          |
| `dragon_restrained`   | `dragon_voracious`    | +temperament, -taming                  |
| `dragon_defiant`      | `dragon_accepting`    | -temperament, -taming                  |
| `dragon_accepting`    | `dragon_defiant`      | +temperament, +taming                  |
| `dragon_bloodthirsty` | `dragon_skittish`     | +dread, -temperament, -taming, +combat |
| `dragon_skittish`     | `dragon_bloodthirsty` | +temperament, +taming, -combat         |

Special: `dragon_cannibal` (no opposite) -- +dread, -temperament, -taming

### Congenital Traits (genetic = yes)

| Trait                        | Opposite                     | Leveled        | Key Effects                      |
| ---------------------------- | ---------------------------- | -------------- | -------------------------------- |
| `dragon_physique_good_1/2/3` | `dragon_physique_bad_1/2/3`  | Yes (3 levels) | +health, +size modifier, +energy |
| `dragon_physique_bad_1/2/3`  | `dragon_physique_good_1/2/3` | Yes (3 levels) | -health, -size modifier, -energy |
| `dragon_swift`               | `dragon_slow`                | No             | +combat, +health, +energy        |
| `dragon_slow`                | `dragon_swift`               | No             | -combat, -health, -energy        |
| `dragon_spindly`             | --                           | No             | +combat, -size, +dread, -health  |
| `dragon_majestic`            | `dragon_ugly`                | No             | +rider prestige, +health         |
| `dragon_ugly`                | `dragon_majestic`            | No             | -rider prestige, -health         |
| `dragon_fertile`             | --                           | No             | +0.5 fertility                   |
| `dragon_destined`            | --                           | No             | +health, early growth boost      |

### Education Traits

| Trait                | Flags                      |
| -------------------- | -------------------------- |
| `education_dragon_1` | -temperament 8, -taming 15 |
| `education_dragon_2` | -temperament 4             |
| `education_dragon_3` | +temperament 4, +taming 10 |
| `education_dragon_4` | +temperament 8, +taming 15 |
| `education_dragon_5` | (highest level)            |

### Canon Dragon Identity Traits

Hidden traits in `00_agot_canon_dragon_traits.txt` identify specific named
dragons: `is_dragon_balerion`, `is_dragon_vhagar`, `is_dragon_meraxes`,
`is_dragon_caraxes`, `is_dragon_vermithor`, `is_dragon_silverwing`,
`is_dragon_dreamfyre`, `is_dragon_meleys`, `is_dragon_quicksilver`,
`is_dragon_sheepstealer`, `is_dragon_cannibal`, etc.

These are `physical = no`, hidden from encyclopedia, and used by scripted
triggers to identify canon dragons for special event logic.

---

## Sub-Mod Recipes

### Adding a Custom Dragon Egg Type

To add a new egg color (e.g., "crimson"):

**Step 1: Define the color effect** in your scripted effects file:

```pdx
create_artifact_dragon_egg_crimson_effect = {
    create_artifact_dragon_egg_wrapper_effect = {
        OWNER = $OWNER$
        COLOR = crimson
    }
}
```

**Step 2: Add the artifact visuals.** You need localization keys and an artifact
visual definition:

- `dragon_egg_crimson` (artifact name loc)
- `dragon_egg_crimson_desc` / `dragon_egg_crimson_desc_living` (descriptions)
- Visual asset registered under the name `dragon_egg_crimson`

**Step 3: Add to random pools** if you want your egg to appear naturally.
Override the relevant `random_list` blocks in the egg effects file, or create
your own wrapper:

```pdx
my_mod_create_random_egg = {
    random_list = {
        10 = { agot_create_random_dragon_egg_artifact = { OWNER = $OWNER$ } }
        1 = { create_artifact_dragon_egg_crimson_effect = { OWNER = $OWNER$ } }
    }
}
```

**Step 4: Add appearance mapping.** In your appearance effects, map the egg
color to dragon primary/secondary/tertiary colors. The egg's `var:egg_color` is
read by `agot_gen_appearance_variables` to derive the hatchling's coloring.

### Creating a New Dragon Breed

A "breed" in AGOT is the combination of congenital traits passed through
genetics.

**Step 1: Define the congenital trait:**

```pdx
# In common/traits/my_dragon_traits.txt
dragon_fireproof = {
    desc = trait_dragon_fireproof_desc
    shown_in_ruler_designer = no
    potential = { has_trait = dragon }

    flag = add_fire_resistance_100
    health = 0.5

    genetic = yes
    physical = yes
    good = yes
}
```

**Step 2: Create the inheritance effect** following the AGOT pattern:

```pdx
my_dragon_fireproof_effect = {
    $DRAGON$ = { save_scope_as = dragon }
    scope:dragon = {
        random = {
            chance = {
                value = 0
                if = {
                    limit = {
                        agot_dragon_inheritance_both_parents_have_active_trait = {
                            DRAGON = scope:dragon
                            TRAIT = dragon_fireproof
                        }
                    }
                    add = agot_dragon_inheritance_both_parents_active_trait_value
                }
                # ... (follow the same pattern for other inheritance tiers)
            }
            scope:dragon = { add_trait = dragon_fireproof }
        }
        # Inactive (recessive) inheritance fallback:
        if = {
            limit = { scope:dragon = { NOT = { has_trait = dragon_fireproof } } }
            random = {
                chance = {
                    value = 0
                    # ... (inactive inheritance tiers)
                }
                scope:dragon = { make_trait_inactive = dragon_fireproof }
            }
        }
    }
}
```

**Step 3: Hook into the spawning pipeline.** You can call your effect after the
dragon is created. The best place is after `agot_dragon_tree_creation_effect` in
the spawning flow, or via an on_action that fires when a dragon is born.

**Step 4: Add to clearing effect** so debug/redesign works:

```pdx
# Override or extend agot_clear_dragon_genetic_traits_effect
# Add: remove_trait = dragon_fireproof
```

### Modifying the Dragonpit

#### Adding a New Dragonpit Building

To create a dragonpit in a new location, your building must be recognized by the
dragonpit toggle logic. The key check in `agot_change_dragonpit_status` is:

```pdx
any_county_province = {
    has_holding_type = castle_holding
    has_building_or_higher = generic_dragon_pit_01
}
```

Or the special buildings:

```pdx
has_building_or_higher = dragonpit_01
has_building = dragonpit_ruins_03
has_building = agot_dragonmont_01
```

If your building does not match any of these, the toggle decision will not find
it.

**Option A:** Make your building upgrade from `generic_dragon_pit_01` so
`has_building_or_higher` catches it.

**Option B:** Override `agot_change_dragonpit_status` and
`agot_change_dragonpit_status_ai` to add your building to the OR block:

```pdx
OR = {
    any_county_province = {
        has_holding_type = castle_holding
        has_building_or_higher = generic_dragon_pit_01
    }
    any_county_province = {
        OR = {
            has_building_or_higher = dragonpit_01
            has_building = dragonpit_ruins_03
            has_building = agot_dragonmont_01
            has_building = my_custom_dragonpit  # Your addition
        }
    }
}
```

#### Custom Dragonpit Growth Rates

The growth penalty for dragonpits is in `agot_apply_dragon_aging_effect`.
Dragonstone (`title:c_dragonstone`) gets special treatment with better growth
odds. To add similar treatment for your location:

```pdx
# In the dragonpit growth section of agot_apply_dragon_aging_effect:
if = {
    limit = {
        var:pitted_dragon_location ?= title:c_my_volcanic_island
    }
    # Custom growth rates
    random_list = {
        5 = {}
        55 = { add_prowess_skill = 1  change_dragon_size = { VALUE = 1 } }
        15 = { add_prowess_skill = 2  change_dragon_size = { VALUE = 2 } }
    }
}
```

---

## Pitfalls

1. **Egg artifact type matters.** Eggs must have `type = dragon_egg` in their
   `create_artifact` call. Many AGOT triggers check `has_variable = dragon_egg`
   on the artifact scope. If you create an egg without this variable, hatching
   logic will not find it.

2. **Dud eggs are permanent.** Once `dud_egg` is set on an egg artifact, the
   standard hatching flow will never trigger for it. If you want to "revive" a
   dud egg, you must explicitly `remove_variable = dud_egg` and reforge the
   artifact back to `dragon_egg` type.

3. **Dragon parentage requires variables on the egg, not the dragon.** The
   `agot_set_dragon_parents` effect reads `var:dragon_parent` from the **egg
   artifact** scope, not from the dragon. If your custom spawning skips egg
   creation, you must manually set mother/father on the dragon character.

4. **Dragonpit county variable is critical.** The `has_dragonkeeper_order`
   variable on the county is what gates the dragonpit toggle. If you construct a
   dragonpit building but skip the setup effect, the decision/toggle will not
   find the pit.

5. **Growth stunting is probabilistic, not deterministic.** Dragons in pits have
   a 30% chance of zero growth per cycle (vs 10% for free dragons). Over time
   this compounds significantly. The Dragonstone exception reduces this to 5%.

6. **Canon dragon checks gate spawning.** The
   `agot_spawn_owned_hatchling_from_egg_effect` prioritizes canon dragon
   spawning if `agot_canon_dragons_enabled = yes`. If your sub-mod adds eggs
   that should never produce canon dragons, ensure the canon trigger does not
   match.

7. **Metallic egg colors get special appearance treatment.** Eggs with metallic
   colors (bronze, silver, gold, and their multicolor variants) trigger
   `override_metal_strength_values` in the appearance system. If you add a new
   metallic color, add it to the OR block in `agot_gen_appearance_variables` or
   your dragon will not have metallic scales.

8. **The dragon family tree uses story cycles.** The
   `agot_dragon_tree_creation_effect` stores parent-child relationships in
   `agot_dragon_tree_parent` and `agot_dragon_tree_structure` story types owned
   by `title:c_ruins.holder`. If this holder does not exist or changes, the tree
   GUI can break.

9. **Inactive traits are recessive genes.** The genetics system distinguishes
   between active traits (visible) and inactive traits (hidden/recessive). A
   dragon can carry `has_inactive_trait = dragon_swift` without displaying it,
   but still pass it to offspring. Use `make_trait_inactive` rather than
   `add_trait` for recessive inheritance.

10. **Amenity levels require EP1 DLC.** The dragonkeeper quality system uses
    `amenity_level` which requires the Royal Court DLC. Without it, dragonkeeper
    generation falls back to random template selection. Always guard amenity
    logic with `has_ep1_dlc_trigger = yes`.
