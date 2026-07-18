# AGOT Extension: Buildings

> This guide extends
> [references/patterns/buildings.md](../patterns/buildings.md) with
> AGOT-specific changes.

## What AGOT Changes

AGOT completely overhauls the building system:

- **Vanilla buildings are overridden** -- `00_AAA_agot_overrides.txt` replaces
  vanilla building files. Castle buildings (`castle_05`, etc.) are fully
  redefined with AGOT-specific 3D assets, province-locked meshes, and graphical
  culture support.
- **Script value costs replace hardcoded numbers** -- costs use named script
  values like `expensive_building_tier_6_cost` and `normal_building_tier_3_cost`
  instead of raw gold amounts. Construction times use values like
  `very_slow_construction_time`, `slow_construction_time`,
  `standard_construction_time`, `quick_construction_time`, and
  `very_quick_construction_time`. These are defined in
  `common/script_values/00_building_values.txt`.
- **New holding types** -- AGOT adds `ruin_holding`, `settlement`, `wilderness`,
  and `pirate_den` holding types, each with their own building files.
- **The `agot_generic_is_special_building_enabled` trigger** -- nearly all AGOT
  special buildings use this shared scripted trigger in `is_enabled`. It checks
  that the county holder is a human player and the holding is not a ruin (unless
  the building has the `special_building_enabled_in_ruin_county` flag).
- **Ruin and rebuild mechanics** -- buildings like Harrenhal and Moat Cailin
  have multi-step ruin/rebuild chains with `on_start`, `on_complete`, and
  `on_cancelled` effects that fire events and track progress via character flags
  and variables.
- **Building history effects** --
  `common/scripted_effects/00_agot_building_history_effects.txt` contains
  per-region effects (e.g. `agot_add_building_on_start_the_crownlands`) that
  destroy and re-add buildings based on game start date. This replaces vanilla's
  static history.
- **Building destruction effects** --
  `common/scripted_effects/00_agot_building_effects.txt` provides parametric
  destruction effects like
  `agot_destroy_building_effect = { BUILDING = curtain_walls }` that remove the
  highest level of a building chain.
- **Pirate buildings** -- `00_agot_pirate_buildings.txt` defines buildings tied
  to pirate government via
  `government_has_flag = government_is_pirate_trigger_check`, using
  `cost_prestige` alongside `cost_gold`.
- **AGOT-specific terrain and culture triggers** -- buildings use custom terrain
  checks like `agot_is_desert_mountains_terrain`, `agot_is_forest_terrain`,
  etc., and custom culture triggers like `tradition_agot_riverlands`.

## AGOT Building Types

AGOT organizes buildings across many files by category:

| File                                            | Purpose                                                                    |
| ----------------------------------------------- | -------------------------------------------------------------------------- |
| `00_AAA_agot_overrides.txt`                     | Overrides vanilla buildings (visual reset helper)                          |
| `00_agot_castle_buildings.txt`                  | Redefined castle holding tiers with region-specific 3D assets              |
| `00_agot_city_buildings.txt`                    | City holding buildings                                                     |
| `00_agot_common_buildings.txt`                  | Common buildings available everywhere (e.g. `generic_dragon_pit_01`)       |
| `00_agot_duchy_buildings.txt`                   | Duchy capital buildings (e.g. `agot_vineyard_01`)                          |
| `00_agot_monastery_buildings.txt`               | Temple/monastery buildings                                                 |
| `00_agot_pirate_buildings.txt`                  | Pirate government buildings (e.g. `agot_pirate_control_01`)                |
| `00_agot_pirate_den_buildings.txt`              | Pirate den holding buildings                                               |
| `00_agot_ruin_buildings.txt`                    | Ruin holding buildings (e.g. `ruin_01`, `small_ruin_01`)                   |
| `00_agot_settlement_buildings.txt`              | Free Folk settlement holdings (e.g. `settlement_01`)                       |
| `00_agot_special_buildings.txt`                 | Iconic location buildings (Red Keep, Winterfell, Casterly Rock, etc.)      |
| `00_agot_special_buildings_beyond_the_wall.txt` | Beyond the Wall specials                                                   |
| `00_agot_special_buildings_essos.txt`           | Essos specials                                                             |
| `00_agot_special_buildings_the_wall.txt`        | Night's Watch specials                                                     |
| `00_agot_special_buildings_westeros.txt`        | Additional Westeros specials                                               |
| `00_agot_standard_economy_buildings.txt`        | Economy building overrides                                                 |
| `00_agot_standard_fortification_buildings.txt`  | Fortification building overrides                                           |
| `00_agot_temple_buildings.txt`                  | Temple buildings                                                           |
| `00_agot_terrain_specific_buildings.txt`        | Terrain-locked buildings (e.g. `building_moat_01`, `apiaries`, `godswood`) |
| `00_agot_unknown_buildings.txt`                 | Placeholder/unknown buildings                                              |
| `00_agot_wilderness_buildings.txt`              | Wilderness holding buildings (Beyond the Wall)                             |

## AGOT-Specific Template

### Regular Building (terrain-restricted)

```
# common/buildings/my_agot_buildings.txt

my_agot_building_01 = {
    construction_time = standard_construction_time       # Use AGOT script values, not raw numbers

    can_construct_potential = {
        building_requirement_castle_city_church = { LEVEL = 01 }
        building_requirement_tribal = no                  # Blocks tribal/nomadic holders
        scope:holder.culture = {
            has_cultural_tradition = tradition_agot_riverlands  # AGOT custom tradition
        }
        geographical_region = world_westeros_the_riverlands     # AGOT geographical region
    }

    can_construct_showing_failures_only = {
        building_requirement_tribal = no
    }

    cost_gold = normal_building_tier_1_cost               # Script value, not raw number

    max_garrison = normal_building_max_garrison_tier_1
    province_modifier = {
        monthly_income = poor_building_tax_tier_1
        fort_level = normal_building_fort_level_tier_1    # Script value modifiers
    }

    next_building = my_agot_building_02

    type_icon = "icon_building_curtain_walls.dds"

    ai_value = {
        base = 10
        ai_tier_1_building_modifier = yes                 # AGOT AI helper macros
        ai_general_building_modifier = yes
    }
}
```

### Special Building (iconic location)

```
# common/buildings/my_agot_special.txt

my_castle_01 = {
    construction_time = very_slow_construction_time

    type_icon = "icon_structure_my_castle.dds"

    can_construct_potential = {
        building_requirement_tribal = no
    }

    is_enabled = {
        agot_generic_is_special_building_enabled = yes    # Required for AGOT special buildings
    }

    asset = {
        type = pdxmesh
        name = "building_special_my_castle_mesh"
    }

    cost_gold = expensive_building_tier_6_cost

    next_building = my_castle_02

    character_modifier = {
        legitimacy_gain_mult = 0.1
        owned_legend_spread_mult = 0.1
    }

    province_modifier = {
        fort_level = 4
        defender_holding_advantage = 6
    }

    county_modifier = {
        county_opinion_add = 5
    }

    ai_value = {
        base = 100
        culture_likely_to_fortify_modifier = yes
    }

    type = special

    flag = travel_point_of_interest_martial
    flag = special_building_enabled_in_ruin_county        # Allows building to work in ruin holdings
}
```

### Duchy Capital Building

```
# common/buildings/my_agot_duchy.txt

my_duchy_building_01 = {
    construction_time = slow_construction_time

    can_construct_potential = {
        building_requirement_castle_city_church = { LEVEL = 01 }
        building_requirement_tribal = no
        NOR = {
            agot_is_desert_mountains_terrain = yes
            agot_is_glacier_terrain = yes
        }
    }

    can_construct_showing_failures_only = {
        culture = {
            has_innovation = innovation_manorialism
        }
    }

    is_enabled = {
        county.holder = { has_title = prev.duchy }        # Must hold duchy title
    }
    show_disabled = yes

    cost_gold = expensive_building_tier_3_cost

    duchy_capital_county_modifier = {
        monthly_county_control_growth_factor = 0.1
    }
    province_modifier = {
        monthly_income = excellent_building_tax_tier_2
    }

    next_building = my_duchy_building_02

    type_icon = "icon_building_vineyard.dds"
    type = duchy_capital

    ai_value = {
        base = 20
        modifier = {
            factor = 0
            free_building_slots > 0
        }
    }
}
```

## Annotated AGOT Example

The Red Keep from `00_agot_special_buildings.txt` (level 1 of 3):

```
the_red_keep_01 = {
    construction_time = very_quick_construction_time       # Script value, not days

    type_icon = "icon_structure_red_keep.dds"              # Custom AGOT icon

    can_construct_potential = {
        building_requirement_tribal = no                    # Blocks tribal holders
    }

    is_enabled = {
        agot_generic_is_special_building_enabled = yes      # Shared AGOT trigger:
                                                            #   - county holder must be human player
                                                            #   - holding must not be a ruin
                                                            #     (unless has flag special_building_enabled_in_ruin_county)
    }

    cost_gold = expensive_building_tier_1_cost              # Cheapest expensive tier

    next_building = the_red_keep_02                         # Chains to Maegor's Holdfast

    effect_desc = feast_cost_discount_max_desc              # Custom effect description loc key

    character_modifier = {
        legitimacy_gain_mult = 0.01
        court_grandeur_baseline_add = -5                    # Negative! Aegonfort was modest
        monthly_prestige_gain_mult = 0.1
    }

    max_garrison = normal_building_max_garrison_tier_2      # Script value garrison

    province_modifier = {
        fort_level = 1
        defender_holding_advantage = 2
    }

    county_modifier = {
        county_opinion_add = 5
    }

    ai_value = {
        base = 100
        culture_likely_to_fortify_modifier = yes            # AGOT AI macro
    }

    type = special

    flag = travel_point_of_interest_martial                 # Travel system integration
}
```

Moat Cailin level 2 -- example of `on_start`/`on_complete`/`on_cancelled`
rebuild chain:

```
moat_cailin_02 = {
    construction_time = very_slow_construction_time

    # ... asset, is_enabled, cost_gold ...

    can_construct = {
        OR = {
            title:c_moat_cailin.holder = {
                is_human = yes
                agot_is_independent_ruler = yes               # AGOT scripted trigger
            }
            custom_tooltip = {
                text = moat_cailin_top_liege_desc
                title:c_moat_cailin.holder.top_liege ?= {
                    has_title = title:e_the_north
                    agot_is_independent_ruler = yes
                }
            }
        }
    }

    on_start = {
        county.holder = {
            add_character_flag = rebuilding_moat_cailin
            add_character_flag = started_rebuilding_moat_cailin
            trigger_event = agot_ruins.3000                   # Fires rebuild event
        }
        set_variable = {
            name = constructor
            value = scope:character
        }
        title:c_ruins.holder = {
            trigger_event = {
                id = agot_rebuilding_ruins.1000
                months = { 11 37 }                            # Random delay between 11-37 months
            }
        }
    }

    on_cancelled = {
        root = { save_scope_as = province }
        county.holder = {
            add_character_flag = cancelled_cailin
            trigger_event = agot_ruins.9998
        }
    }

    on_complete = {
        county.holder = {
            trigger_event = agot_ruins.3001
        }
        remove_variable = constructor
    }

    type = special
    flag = travel_point_of_interest_martial
}
```

## Cost Tier Reference

All AGOT building costs are defined in
`common/script_values/00_building_values.txt` using a quadratic scaling formula.
Costs scale linearly for tiers 1-2, then quadratically from tier 3 onward
(multiplied by `tier * tier * scale * 0.1`). The base values, scale-per-tier
values, and resulting gold amounts are:

### Gold Cost Tiers

| Tier | `cheap_` | `normal_` | `expensive_` |
| ---- | -------- | --------- | ------------ |
| 1    | 100      | 150       | 200          |
| 2    | 150      | 250       | 350          |
| 3    | 195      | 340       | 485          |
| 4    | 275      | 500       | 725          |
| 5    | 400      | 750       | 1100         |
| 6    | 580      | 1110      | 1640         |
| 7    | 825      | 1600      | 2375         |
| 8    | 1145     | 2240      | 3335         |

Usage: `cost_gold = expensive_building_tier_6_cost` yields 1640 gold.

Two additional cost categories exist for special building types:

| Tier | `main_` (castle tiers) | `tribal_` |
| ---- | ---------------------- | --------- |
| 1    | 500                    | 75        |
| 2    | 1750                   | 100       |
| 3    | 3000                   | 125       |
| 4    | 4250                   | 150       |
| 5    | 5500                   | --        |

The `main_` costs are used for the castle holding tier buildings (`castle_01`
through `castle_05`). The `tribal_` costs are used for tribal-government
buildings like `palisades` and `longhouses`.

The underlying formula variables (from `00_building_values.txt`):

```
@cheap_cost_base = 100
@normal_cost_base = 150
@expensive_cost_base = 200
@main_cost_base = 500              # AGOT Modified (vanilla was 400)
@tribal_cost_base = 75

@cheap_cost_scale_addition_per_tier = 50
@normal_cost_scale_addition_per_tier = 100
@expensive_cost_scale_addition_per_tier = 150
@main_cost_scale_addition_per_tier = 1250    # AGOT Modified (vanilla was 400)

@building_cost_scaling_modifier_cheap = 0.1
@building_cost_scaling_modifier_normal = 0.1
@building_cost_scaling_modifier_expensive = 0.1
```

### Construction Time Values

| Script Value                   | Days | Approx. Years |
| ------------------------------ | ---- | ------------- |
| `very_quick_construction_time` | 365  | 1             |
| `quick_construction_time`      | 730  | 2             |
| `standard_construction_time`   | 1095 | 3             |
| `slow_construction_time`       | 1825 | 5             |
| `very_slow_construction_time`  | 2190 | 6             |

Castle holding tiers use their own construction times that increase per tier:

| Script Value                         | Days  | Approx. Years |
| ------------------------------------ | ----- | ------------- |
| `agot_main_tier_1_construction_time` | 1800  | ~5            |
| `agot_main_tier_2_construction_time` | 3800  | ~10.4         |
| `agot_main_tier_3_construction_time` | 5800  | ~15.9         |
| `agot_main_tier_4_construction_time` | 8800  | ~24.1         |
| `agot_main_tier_5_construction_time` | 12800 | ~35.1         |

## Graphical Cultures for Buildings

AGOT uses `graphical_cultures` inside `asset` blocks to assign different 3D
building models based on a province's culture region. This system maps each
culture's `_unit_gfx` to a `_building_gfx` identifier via
`common/graphical_unit_types/00_agot_graphical_unit_types.txt`.

### How the Mapping Works

1. Each culture in CK3 has a `graphical_culture` (e.g. `northman_unit_gfx`).
2. `00_agot_graphical_unit_types.txt` groups these into named sets:

```
# From common/graphical_unit_types/00_agot_graphical_unit_types.txt
andal = {
    graphical_cultures = {
        valeman_unit_gfx
        reachman_unit_gfx
        honeywiner_unit_gfx
        stormlander_unit_gfx
        westerman_unit_gfx
        riverlander_unit_gfx
        crownlander_unit_gfx
    }
}
firstman = {
    graphical_cultures = { northman_unit_gfx }
}
ironborn = {
    graphical_cultures = { ironborn_unit_gfx }
}
dornish = {
    graphical_cultures = { dornish_unit_gfx stone_dornish_unit_gfx }
}
```

3. Building definitions use `graphical_cultures = { xxx_building_gfx }` inside
   their `asset` blocks to pick which 3D model to show for that culture region.

### All AGOT Building GFX Identifiers

The following `_building_gfx` identifiers are used across AGOT castle buildings
(from `00_agot_castle_buildings.txt`):

| Identifier                     | Region/Culture                       |
| ------------------------------ | ------------------------------------ |
| `andal_building_gfx`           | Generic Andal (Vale fallback)        |
| `barrow_building_gfx`          | Barrowlands (Northern subregion)     |
| `braavosi_building_gfx`        | Braavos                              |
| `byzantine_building_gfx`       | Vanilla Byzantine (reused)           |
| `chinese_building_gfx`         | Vanilla Chinese (reused)             |
| `crannogman_building_gfx`      | Crannog (Neck)                       |
| `crownlands_building_gfx`      | Crownlands                           |
| `dornish_building_gfx`         | Dorne                                |
| `dothraki_building_gfx`        | Dothraki                             |
| `first_man_building_gfx`       | First Men / North                    |
| `ghis_building_gfx`            | Ghiscari / Slaver's Bay              |
| `high_valyrian_building_gfx`   | Valyrian (Dragonstone, old Freehold) |
| `hyrkoon_building_gfx`         | Hyrkoon / Patrimony                  |
| `ironmen_building_gfx`         | Iron Islands                         |
| `lorathi_building_gfx`         | Lorath                               |
| `lyseni_building_gfx`          | Lys                                  |
| `myrish_building_gfx`          | Myr                                  |
| `norvoshi_building_gfx`        | Norvos                               |
| `pentoshi_building_gfx`        | Pentos                               |
| `qartheen_building_gfx`        | Qarth                                |
| `qohorik_building_gfx`         | Qohor                                |
| `reach_building_gfx`           | The Reach                            |
| `red_andal_building_gfx`       | Red Andal variant                    |
| `riverlander_building_gfx`     | Riverlands                           |
| `sarnori_building_gfx`         | Sarnor                               |
| `stormlands_building_gfx`      | Stormlands                           |
| `summer_islander_building_gfx` | Summer Islands                       |
| `tyrosh_building_gfx`          | Tyrosh                               |
| `volantene_building_gfx`       | Volantis                             |
| `westerman_building_gfx`       | Westerlands                          |
| `wildling_building_gfx`        | Free Folk / Beyond the Wall          |
| `yitish_building_gfx`          | Yi Ti                                |

### How Buildings Select Assets by Culture and Province

In `00_agot_castle_buildings.txt`, each castle tier (e.g. `castle_05`) defines
many `asset` blocks. The game selects the matching block using two mechanisms:

- **`graphical_cultures = { xxx_building_gfx }`** -- matches when the province's
  culture belongs to that graphical culture group.
- **`provinces = { 2855 1310 ... }`** -- overrides for specific province IDs,
  used for unique locations like Casterly Rock, Shadow Tower, or the Neck's
  crannogs.

Province-specific overrides take priority. Example from `castle_05`:

```
# Default Western fallback
asset = {
    type = pdxmesh
    names = { "building_western_castle_04_mesh" }
    illustration = @holding_illustration_western
    soundeffect = { ... }
}

# The Neck -- crannog model for specific provinces
asset = {
    type = pdxmesh
    names = { "agot_holding_castle_crannog_03_mesh" }
    illustration = @holding_illustration_old_norse
    soundeffect = { ... }
    provinces = { 1310 1311 1312 ... }
}

# Crownlands culture-based
asset = {
    type = pdxmesh
    names = { "building_western_castle_04_mesh" }
    illustration = @holding_illustration_norse
    soundeffect = { ... }
    graphical_cultures = { crownlands_building_gfx }
}
```

### 3D Model File Locations

Building models are organized under `gfx/models/buildings/` in two directories:

- **`holdings/`** -- regular holding models, organized by `_building_gfx`
  subdirectory:
  - `holdings/andal_building_gfx/` -- Andal castle/wall meshes
  - `holdings/first_man_building_gfx/` -- Northern castle/tower meshes
  - `holdings/ironborn_building_gfx/` -- Iron Islands holdings, cities, walls
  - `holdings/reach_building_gfx/` -- Reach holdings, cities, walls
  - `holdings/riverlander_building_gfx/` -- Riverlands walls and moats
  - `holdings/wildling_building_gfx/` -- Tribal/igloo models for Free Folk
  - `holdings/dawnbringer_god_gfx/` -- R'hllor temple models
  - `holdings/fots_god_gfx/` -- Faith of the Seven temple models
  - `holdings/agot_building_ruin_gfx/` -- Ruin holding models
  - (and more per region)

- **`special/`** -- unique named location models:
  - `special/Kings Landing/` -- Red Keep, Flea Bottom meshes
  - `special/Harrenhal/` -- Ruined and restored Harrenhal meshes
  - `special/Highgarden/` -- Highgarden mesh
  - `special/Castle Black/` -- Castle Black mesh
  - `special/Braavos/` -- Braavos mesh
  - `special/Pyke/` -- Pyke cliff meshes
  - `special/Ten Towers/` -- Ten Towers mesh

## Building 3D Asset Pipeline

The path from a 3D model file to a visible building on the map follows this
pipeline:

### Step 1: Mesh File (`.mesh`)

The raw 3D model exported from a 3D modeling tool (e.g. Maya, Blender). Located
alongside the `.asset` file. Example:
`gfx/models/buildings/special/Kings Landing/breakup_so_sad/building_special_KL_RedKeep.mesh`

### Step 2: Asset Definition (`.asset`)

The `.asset` file defines a `pdxmesh` (linking the `.mesh` file to textures) and
an `entity` (giving it a referenceable name). Example from the Red Keep:

```
# gfx/models/buildings/special/Kings Landing/breakup_so_sad/building_special_KL_RedKeep.asset

pdxmesh = {
    name = "building_special_KL_RedKeep_mesh"        # Name referenced by building definitions
    file = "building_special_KL_RedKeep.mesh"         # The 3D mesh file

    meshsettings = {
        name = "building_special_KL_WallsShape"       # Sub-mesh within the model
        index = 0
        texture_diffuse = "building_special_KL_Walls_diffuse.dds"     # Color texture
        texture_normal = "building_special_KL_Walls_normal.dds"       # Normal map
        texture_specular = "building_special_KL_Walls_properties.dds" # Specular/properties
        shader = "standard_winter"
        shader_file = "gfx/FX/pdxmesh.shader"
    }
    # ... additional meshsettings blocks for Gardens, Maegors, TowerTops, etc.
}

entity = {
    name = "building_special_KL_RedKeep_entity"
    pdxmesh = "building_special_KL_RedKeep_mesh"
}
```

A simpler holding asset (from `agot_holding_reach_01.asset`):

```
pdxmesh = {
    name = "agot_holding_reach_01_mesh"
    file = "agot_holding_reach_01.mesh"

    meshsettings = {
        name = "agot_holding_reach_01Shape"
        index = 0
        texture_diffuse = "agot_holding_reach_diffuse.dds"
        texture_normal = "agot_holding_reach_normal.dds"
        texture_specular = "agot_holding_reach_properties.dds"
        shader = "standard_winter"
        shader_file = "gfx/FX/pdxmesh.shader"
    }
}

entity = {
    name = "agot_holding_reach_01_entity"
    pdxmesh = "agot_holding_reach_01_mesh"
}
```

### Step 3: Building Definition References the Mesh

In the building `.txt` file, the `asset` block references the mesh by its
`pdxmesh` name:

```
# In common/buildings/00_agot_special_buildings.txt
the_red_keep_01 = {
    asset = {
        type = pdxmesh
        name = "building_special_KL_RedKeep_mesh"    # Matches pdxmesh name from .asset file
    }
    # ...
}
```

For castle tiers with culture variants, the `asset` block uses `names` (plural)
and `graphical_cultures`:

```
# In common/buildings/00_agot_castle_buildings.txt
castle_05 = {
    asset = {
        type = pdxmesh
        names = { "building_western_castle_04_mesh" }
        graphical_cultures = { crownlands_building_gfx }
    }
    # ...
}
```

### Summary Pipeline

```
.mesh file (3D model)
    --> .asset file (pdxmesh + textures + entity)
        --> building .txt (asset block references pdxmesh name)
            --> graphical_cultures or provinces = {} (selects which model to show)
```

Each texture uses the CK3 standard three-texture setup:

- `_diffuse.dds` -- base color/albedo
- `_normal.dds` -- surface normal map
- `_properties.dds` -- specular/roughness/metallic properties

## Special Building Inventory

AGOT defines over 200 unique special buildings across five files. Below is a
selection of the major iconic buildings with their tier counts and locations.

### Major Westeros Special Buildings (`00_agot_special_buildings.txt`)

| Building                | Tiers       | Key Feature                                              |
| ----------------------- | ----------- | -------------------------------------------------------- |
| `the_red_keep`          | 3           | King's Landing. Legitimacy, prestige, court grandeur.    |
| `seven_gates`           | 1           | King's Landing city gates. Tax and control.              |
| `cobblers_square`       | 1           | King's Landing market square. Development.               |
| `holy_site_great_sept`  | 1           | Great Sept of Baelor. Religion-locked holy site.         |
| `dragonpit`             | 2 + 2 ruins | Dragon pit, can be ruined or restored.                   |
| `winterfell`            | 3           | Winterfell. Fort level, garrison, prestige.              |
| `the_eyrie`             | 1           | The Eyrie. Fort level, advantage, opinion.               |
| `casterly_rock`         | 4           | Casterly Rock. Massive fortification chain.              |
| `highgarden`            | 5           | Highgarden. Longest Westeros special chain.              |
| `pyke`                  | 1           | Pyke castle. Fort level, dread.                          |
| `sunspear`              | 1           | Sunspear. Prestige, opinion, development.                |
| `storms_end`            | 7           | Storm's End. Longest rebuild chain (7 tiers).            |
| `riverrun`              | 1           | Riverrun. Fort level, advantage.                         |
| `moat_cailin`           | 3           | Moat Cailin. Ruin rebuild chain with events.             |
| `the_bloody_gate`       | 1           | Bloody Gate. Massive defender advantage.                 |
| `dragonstone`           | 1           | Dragonstone. Valyrian-themed fortification.              |
| `the_hightower`         | 1           | The Hightower at Oldtown. Development, prestige.         |
| `the_citadel`           | 2           | The Citadel. Learning, development.                      |
| `holy_site_naggas_hill` | 1           | Nagga's Hill. Ironborn holy site.                        |
| `the_twins`             | 1           | The Twins (Frey). Tax, control, opinion.                 |
| `generic_harrenhal`     | 1           | Pre-ruin Harrenhal (Hoare-era). Needs empire title.      |
| `harrenhal`             | 1           | Restored Harrenhal. Same stats, different can_construct. |
| `ruins_harrenhal`       | 7           | Ruined Harrenhal rebuild chain (01 through 07).          |

### Additional Westeros Specials (`00_agot_special_buildings_westeros.txt`)

Selected highlights from the 150+ buildings in this file:

| Building                 | Tiers       | Region                  |
| ------------------------ | ----------- | ----------------------- |
| `agot_tower_of_joy`      | 1 + 1 ruin  | Dorne                   |
| `agot_the_water_gardens` | 1           | Dorne                   |
| `agot_ghaston_grey`      | 1           | Dorne (prison)          |
| `agot_starfall`          | 1           | Dorne                   |
| `agot_summerhall`        | 1 + 2 ruins | Stormlands              |
| `agot_griffins_roost`    | 1           | Stormlands              |
| `agot_castamere`         | 1 + 2 ruins | Westerlands             |
| `agot_banefort`          | 1           | Westerlands             |
| `agot_golden_tooth`      | 1           | Westerlands             |
| `agot_seagard`           | 1           | Riverlands              |
| `agot_oldstones`         | 2           | Riverlands (ruin chain) |
| `agot_raventree_hall`    | 1           | Riverlands              |
| `agot_white_harbor`      | 1           | The North               |
| `agot_dreadfort`         | 1           | The North               |
| `agot_barrow_keep`       | 1           | The North               |
| `agot_greywater_watch`   | 1           | The Neck                |
| `agot_last_hearth`       | 1           | The North               |
| `agot_bitterbridge`      | 2           | The Reach               |
| `agot_port_of_oldtown`   | 1           | The Reach               |
| `agot_ten_towers`        | 1           | Iron Islands            |
| `agot_hoare_castle`      | 2           | Iron Islands (ruin)     |
| `agot_hammerhorn`        | 1           | Iron Islands            |
| `agot_flea_bottom`       | 1           | Crownlands              |
| `agot_dragonmont`        | 1           | Crownlands              |
| `agot_grafton_keep`      | 1           | The Vale                |
| `agot_gates_of_the_moon` | 2           | The Vale                |
| `agot_runestone`         | 1           | The Vale                |

### Essos Specials (`00_agot_special_buildings_essos.txt`)

| Building                | Tiers       | Region         |
| ----------------------- | ----------- | -------------- |
| `agot_sealords_palace`  | 1           | Braavos        |
| `agot_iron_bank`        | 1           | Braavos        |
| `agot_titan`            | 1           | Braavos        |
| `agot_arsenal`          | 1           | Braavos        |
| `agot_isle_of_the_gods` | 1           | Braavos        |
| `agot_palace_of_truth`  | 1           | Braavos        |
| `agot_pentos`           | 1           | Pentos         |
| `agot_pentos_walls`     | 1           | Pentos         |
| `agot_tyrosh`           | 1           | Tyrosh         |
| `agot_myr`              | 1           | Myr            |
| `agot_lys_walls`        | 1           | Lys            |
| `agot_bleeding_tower`   | 1           | Tyrosh         |
| `agot_triarchy_council` | 1 + 2 ruins | Disputed Lands |
| `agot_valdrizes`        | 1           | Volantis       |

### The Wall (`00_agot_special_buildings_the_wall.txt`)

| Building                | Tiers | Notes                                                   |
| ----------------------- | ----- | ------------------------------------------------------- |
| `agot_the_wall`         | 1     | The Wall itself. `type = great_building`. 30 advantage. |
| `agot_castle_black`     | 1     | Castle Black. 50 defender advantage.                    |
| `agot_eastwatch`        | 1     | Eastwatch-by-the-Sea.                                   |
| `agot_shadow_tower`     | 1     | Shadow Tower.                                           |
| `agot_nightfort`        | 1     | The Nightfort.                                          |
| `agot_bridge_of_skulls` | 1     | Bridge of Skulls.                                       |

### Beyond the Wall (`00_agot_special_buildings_beyond_the_wall.txt`)

| Building                           | Tiers       | Notes                              |
| ---------------------------------- | ----------- | ---------------------------------- |
| `agot_gorms_port`                  | 2 + 2 ruins | Gorm's Port ruin/rebuild chain     |
| `agot_raymons_hall`                | 2 + 2 ruins | Raymon's Hall ruin/rebuild chain   |
| `agot_halgars_keep`                | 2 + 2 ruins | Halgar's Keep ruin/rebuild chain   |
| `agot_drekis_tunnels`              | 2 + 2 ruins | Dreki's Tunnels ruin/rebuild chain |
| `agot_ruins_fist_of_the_first_men` | 2           | Fist of the First Men (ruin only)  |
| `agot_thenn_valley`                | 1           | Thenn heartland                    |
| `agot_srunmued_copper_mines`       | 2           | Copper mines with ruin chain       |
| `agot_krih_tin_mines`              | 2           | Tin mines with ruin chain          |

## Building Destruction Effects Detail

AGOT uses parametric scripted effects in
`common/scripted_effects/00_agot_building_effects.txt` to destroy buildings.
These are called from the ruin/rebuild system when a holding becomes a ruin or
when war damage occurs.

### Parametric Destruction Effects

There are four destruction effect variants, each handling a different maximum
building chain length:

**`agot_destroy_building_effect`** -- handles chains up to 8 levels. Checks from
`$BUILDING$_08` down to `$BUILDING$_01` and removes the highest level found:

```
agot_destroy_building_effect = {
    if = {
        limit = { has_building = $BUILDING$_08 }
        remove_building = $BUILDING$_08
    }
    else_if = {
        limit = { has_building = $BUILDING$_07 }
        remove_building = $BUILDING$_07
    }
    # ... continues down to _01
}
```

**`agot_destroy_six_level_building_effect`** -- same pattern but checks `_06`
down to `_01`. Used for pirate buildings.

**`agot_destroy_four_level_building_effect`** -- checks `_04` down to `_01`.
Used for city walls.

**`agot_destroy_one_level_building_effect`** -- checks only `_01`. Used for
single-level buildings like `generic_dragon_pit`.

**`agot_destroy_tribal_building_effect`** -- checks `_02` down to `_01`. Used
for tribal buildings (palisades, war camps, etc.).

### The Master Destruction Effect

`agot_destroy_all_generic_buildings` calls all individual destruction effects
for every standard building type. This is invoked when a holding is converted to
a ruin. It covers:

- **Economy buildings**: `farm_estates`, `cereal_fields`, `pastures`,
  `orchards`, `plantations`, `logging_camps`, `quarries`, `peat_quarries`,
  `hill_farms`, etc.
- **Military buildings**: `barracks`, `military_camps`, `regimental_grounds`,
  `stables`, `camel_farms`, `horse_pastures`, `warrior_lodges`
- **Fortification buildings**: `curtain_walls`, `watchtowers`, `outposts`,
  `hill_forts`, `ramparts`
- **Infrastructure**: `guild_halls`, `breweries`, `workshops`, `windmills`,
  `watermills`, `caravanserai`, `common_tradeport`
- **Religious**: `scriptorium`, `monastic_schools`, `megalith`
- **AGOT-specific**: `agot_slave_camps`, `building_moat`, `apiaries`,
  `godswood`, `agot_urban_farms`, `agot_steppe_farms`
- **Pirate buildings**: `agot_pirate_control`, `agot_pirate_economic`,
  `agot_pirate_supply`, `agot_pirate_troop`, `agot_pirate_military`,
  `agot_pirate_fortification` (all using six-level variant)
- **City/temple**: `city_walls` (four-level), `generic_dragon_pit` (one-level)
- **Tribal**: `palisades`, `war_camps`, `longhouses`, `market_villages` (tribal
  variant)

If you add a new building type to AGOT, you must add a corresponding destruction
call to this effect, or ruined holdings will retain your building.

## Harrenhal Rebuild Chain Detail

Harrenhal is the most complex rebuild chain in AGOT, spanning 7 tiers from
`ruins_harrenhal_01` to `ruins_harrenhal_07`. It demonstrates every aspect of
the ruin/rebuild system.

### Chain Overview

```
ruins_harrenhal_01  (ruin base, can_construct = always = no, placed by history)
    --> ruins_harrenhal_02  (first rebuild tier, cost: expensive_tier_3 = 485g)
        --> ruins_harrenhal_03  (cost: expensive_tier_4 = 725g)
            --> ruins_harrenhal_04  (cost: expensive_tier_5 = 1100g)
                --> ruins_harrenhal_05  (cost: expensive_tier_6 = 1640g)
                    --> ruins_harrenhal_06  (cost: expensive_tier_7 = 2375g)
                        --> ruins_harrenhal_07  (fully restored, cost: expensive_tier_8 = 3335g)
```

Total gold to fully restore: 9660 gold across 6 construction phases, each taking
`very_slow_construction_time` (2190 days / 6 years). Total time: ~36 years
minimum.

There are also two alternative "fresh build" versions: `generic_harrenhal_01`
(requires Empire of the Riverlands + specific traits/dynasty) and `harrenhal_01`
(same but different `can_construct` gate). Both cost
`expensive_building_tier_8_cost` and produce the fully restored version in one
step.

### Ruin Base (`ruins_harrenhal_01`)

The base ruin level is not constructable (`can_construct = { always = no }`) --
it is placed by history effects. It provides negative modifiers representing the
curse of Harrenhal:

```
ruins_harrenhal_01 = {
    construction_time = very_slow_construction_time
    can_construct = { always = no }              # Cannot be built, only placed by history

    character_modifier = {
        monthly_prestige = 0.1
        dread_gain_mult = 0.25
        stress_gain_mult = 0.25                  # The curse!
    }
    county_modifier = {
        levy_size = -0.1                         # Ruins hurt levy
        development_growth_factor = -0.1         # Ruins hurt development
    }
    province_modifier = {
        defender_holding_advantage = 5
        fort_level = 5
        monthly_income = -2                      # Expensive upkeep for a ruin
    }

    next_building = ruins_harrenhal_02
    flag = special_building_enabled_in_ruin_county    # Works even in ruin holdings
}
```

### Rebuild Tiers (`ruins_harrenhal_02` through `_07`)

Each rebuild tier follows the same pattern:

1. **`on_start`** -- fires when construction begins:
   - Adds `rebuilding_harrenhal` and `started_rebuilding_harrenhal` character
     flags to the county holder
   - Fires a notification event (`agot_ruins.4000`, `.4002`, `.4004`, `.4006`,
     `.4008`, `.4010`)
   - Stores the builder in a `constructor` variable on the province
   - Schedules random ruin events via `agot_rebuilding_ruins.9999` with
     staggered month delays

2. **`on_cancelled`** -- fires if construction is cancelled:
   - Adds `cancelled_harrenhal` character flag
   - Fires cancellation event `agot_ruins.9998`
   - Removes the `constructor` variable

3. **`on_complete`** -- fires when construction finishes:
   - Fires completion event (`agot_ruins.4001`, `.4003`, `.4005`, `.4007`,
     `.4009`, `.4011`)
   - Removes the `constructor` variable

### Progressive Improvement

The stats improve with each tier while the "curse" penalties decrease:

| Tier          | Fort | Advantage | Garrison | Prestige | Stress Mult | Income | Levy |
| ------------- | ---- | --------- | -------- | -------- | ----------- | ------ | ---- |
| 01 (ruin)     | 5    | 5         | 1000     | 0.10     | +0.25       | -2.0   | -10% |
| 02            | 7    | 7         | 1500     | 0.15     | +0.20       | -2.1   | -8%  |
| 03            | 9    | 9         | 2000     | 0.20     | +0.15       | -2.2   | -6%  |
| 04            | 11   | 11        | 2500     | 0.25     | +0.10       | -2.4   | -4%  |
| 05            | 13   | 13        | 3000     | 0.275    | +0.075      | -2.6   | -2%  |
| 06            | 15   | 15        | 3500     | 0.30     | +0.05       | -2.8   | -1%  |
| 07 (restored) | 17   | 17        | 4000     | 0.30     | 0           | -3.0   | 0%   |

The final tier 07 matches the fully-built `harrenhal_01`/`generic_harrenhal_01`
stats and uses the `building_special_harrenhal_restored_mesh` model instead of
the ruined meshes. Each intermediate tier uses a progressively less-ruined 3D
model (`building_special_harrenhal_ruined_1_mesh` through `_5_mesh`).

### Visual Mesh Progression

Each tier references a different 3D mesh showing progressive restoration:

| Tier | Mesh Asset                                 |
| ---- | ------------------------------------------ |
| 01   | `building_special_harrenhal_ruined_mesh`   |
| 02   | `building_special_harrenhal_ruined_1_mesh` |
| 03   | `building_special_harrenhal_ruined_2_mesh` |
| 04   | `building_special_harrenhal_ruined_3_mesh` |
| 05   | `building_special_harrenhal_ruined_4_mesh` |
| 06   | `building_special_harrenhal_ruined_5_mesh` |
| 07   | `building_special_harrenhal_restored_mesh` |

These are located in `gfx/models/buildings/special/Harrenhal/` and the
`Harrenhal Redo/` subdirectory.

## Key Differences from Vanilla

| Aspect                          | Vanilla                              | AGOT                                                                                                                     |
| ------------------------------- | ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------ |
| **Cost values**                 | Raw numbers (`cost_gold = 100`)      | Script values (`cost_gold = expensive_building_tier_6_cost`)                                                             |
| **Construction time**           | Raw days (`construction_time = 365`) | Script values (`construction_time = very_slow_construction_time`)                                                        |
| **Garrison/modifiers**          | Raw numbers                          | Script values (`normal_building_max_garrison_tier_2`, `good_building_tax_tier_3`)                                        |
| **Special building is_enabled** | Custom per-building                  | `agot_generic_is_special_building_enabled = yes` (shared trigger)                                                        |
| **Government check**            | `has_government = tribal_government` | `building_requirement_tribal = no` (checks `government_has_flag`)                                                        |
| **Terrain checks**              | `terrain = farmlands`                | `agot_is_forest_terrain = yes` and similar AGOT scripted triggers                                                        |
| **Holding types**               | castle, city, temple, tribal         | + ruin, settlement, wilderness, pirate_den                                                                               |
| **Building history**            | Static in `history/provinces/`       | Dynamic via `agot_add_building_on_start_*` scripted effects per region/date                                              |
| **Rebuild chains**              | Not present                          | Multi-step `on_start`/`on_complete`/`on_cancelled` with events and flags                                                 |
| **AI macros**                   | `ai_value = { base = N }`            | Uses AGOT AI macros: `culture_likely_to_fortify_modifier`, `ai_tier_1_building_modifier`, `ai_general_building_modifier` |
| **Travel flags**                | Optional                             | Most special buildings have `flag = travel_point_of_interest_*`                                                          |

## AGOT Pitfalls

- **Using raw cost numbers instead of script values.** All AGOT buildings use
  the tiered cost system (`cheap_building_tier_1_cost` through
  `expensive_building_tier_8_cost`). Using raw numbers will make your building
  look out of place and break if AGOT rebalances costs. The tiers are: `cheap_`,
  `normal_`, `expensive_`, each from `_tier_1_cost` to `_tier_8_cost`.

- **Using raw construction times.** Always use `very_quick_construction_time`,
  `quick_construction_time`, `standard_construction_time`,
  `slow_construction_time`, or `very_slow_construction_time`.

- **Forgetting `agot_generic_is_special_building_enabled` in is_enabled.** All
  AGOT special buildings use this trigger. Without it, your special building
  will work in ruin holdings and for AI-only characters, which breaks AGOT's
  design intent.

- **Missing `building_requirement_tribal = no` in can_construct_potential.**
  AGOT has tribal, nomadic, and wanua government types that should not access
  most feudal buildings. The `building_requirement_tribal` trigger checks
  `government_has_flag` for all three.

- **Not handling ruin holdings.** If your special building should still provide
  bonuses in ruin counties, add
  `flag = special_building_enabled_in_ruin_county`. The shared
  `agot_generic_is_special_building_enabled` trigger checks for this flag.

- **Forgetting the building destruction effect.** If you add a new regular
  building, add it to `agot_destroy_all_generic_buildings` in
  `common/scripted_effects/00_agot_building_effects.txt` so AGOT's ruin/rebuild
  system can properly remove it. Use the matching parametric effect:
  `agot_destroy_building_effect` (8 levels),
  `agot_destroy_six_level_building_effect` (6 levels),
  `agot_destroy_four_level_building_effect` (4 levels), or
  `agot_destroy_one_level_building_effect` (1 level).

- **Not adding your building to history effects.** If your building should exist
  at game start, add it via the `agot_add_building_on_start_*` scripted effects
  in `common/scripted_effects/00_agot_building_history_effects.txt` using
  `agot_add_building_if_possible = { BUILDING = my_building_01 }` wrapped in
  date-range checks.

- **Using vanilla terrain triggers.** AGOT has its own terrain types and uses
  scripted triggers like `agot_is_forest_terrain`,
  `agot_is_desert_mountains_terrain`, `agot_is_glacier_terrain`, etc. The
  vanilla `terrain = farmlands` syntax may not match AGOT's terrain setup.

- **Using vanilla geographical regions.** AGOT defines its own regions like
  `world_westeros_the_riverlands`, `world_westeros_the_north`, etc. Check
  `common/scripted_triggers/` and `map_data/geographical_region.txt` for valid
  AGOT regions.

- **Pirate buildings without government check.** Pirate-only buildings must
  check `government_has_flag = government_is_pirate_trigger_check` in
  `is_enabled` and typically require `has_building_or_higher = pirate_den_01` in
  `can_construct_potential`.

- **Holy site buildings without religion check.** AGOT holy site buildings (like
  the Great Sept of Baelor) wrap religion checks in `custom_description` blocks
  with both a specific religion check (`religion = religion:the_seven_religion`)
  and a fallback holy site check
  (`barony = { is_holy_site_of = scope:holder.faith }`).

- **Missing `type_icon` for custom buildings.** AGOT buildings consistently
  specify `type_icon = "icon_xxx.dds"` to set the building icon. Without this,
  the building will use a default icon.
