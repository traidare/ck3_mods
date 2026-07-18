# AGOT Extension: GFX

> This guide extends [references/patterns/gfx.md](../patterns/gfx.md) with
> AGOT-specific changes.

## What AGOT Changes

AGOT makes extensive modifications to the GFX system:

- **Dragon portrait system** -- Full 3D dragon models displayed as character
  portraits via custom genes, trait portrait modifiers, dedicated cameras, and
  animation sets
- **Region-specific court rooms** -- Unique 3D throne rooms for iconic locations
  (Red Keep, Winterfell, Pyke, Casterly Rock, Dragonstone, Highgarden, Eyrie,
  Sunspear court)
- **Culture-specific building models** -- Dozens of new holding GFX sets for
  Westerosi and Essos cultures (andal, first_man, ironborn, ghis, qartheen,
  etc.)
- **Special building models** -- Unique 3D models for major locations
  (Harrenhal, The Wall, Braavos Titan, Storm's End, The Twins, etc.)
- **Massive CoA expansion** -- ~1173 custom colored emblems, ~68 custom
  patterns, AGOT-specific textured emblems, and a custom color palette
- **Portrait accessories overhaul** -- AGOT-specific clothes, cloaks, headgear,
  hairstyles, beards, legwear, jewelry, plus dragon-related accessories
  (saddles, egg props, sword props)
- **Accessory variations by region** -- Texture/color variations for Dornish,
  Crownlander, Reach, Stormlander, Westerlander, Northern, Ironborn, Maester,
  Kingsguard, etc.
- **Custom map items** -- Dragon statues, Valyrian sphinxes, Nagga's ribs,
  barrows, causeways, ferry crossings, icebergs, lion/wolf statues, walls
- **Custom shaders and FX** -- Modified court scene shaders, event shaders,
  camera utilities, terrain rendering, portrait rendering
- **AGOT-specific animals** -- Dragon 3D model with animations on the map, plus
  raven added to environment models
- **Custom artifact models** -- Dragon skulls (baby/small/medium/large), dragon
  eggs, iron throne, glass candles, dragonbinder, Valyrian swords, and many more
- **Custom particles** -- Stained glass shadow projections and window light
  effects for court rooms
- **Portrait environments** -- Custom lighting setups for AGOT throne rooms
  (e.g., `portrait_environments_agot.txt`)
- **Dragon-specific portrait cameras** -- Cameras tuned for dragon size/framing
  (`zz_agot_dragon_portrait_cameras.txt`)
- **Appearance overrides** -- Height modifiers (smol_tol, tol), ear shapes, hair
  dye overrides, visible disfigurements, heterochromia eyes

## AGOT GFX Structure

AGOT's `gfx/` directory mirrors vanilla but adds significant content:

```
gfx/
  FX/                              # Custom shaders (court_scene, event, portrait, terrain)
    agot_event_shaders.shader
    court_scene.shader
    cw/agot_camera.fxh
    gh_*.fxh                       # Terrain, portrait, pdxmesh overrides
  coat_of_arms/
    color_palettes/agot_coa_designer_palettes.txt   # AGOT color names
    colored_emblems/               # ~1173 DDS + 50_coa_designer_emblems.txt
    patterns/                      # ~68 DDS (agotp_*.dds) + 50_coa_designer_patterns.txt
    textured_emblems/              # Region-specific (crownlands, reach, vale, west) + 49_coa_designer_emblems.txt
  court_scene/
    character_roles/00_default_roles.txt
    scene_cultures/agot_default_cultures.txt         # Location-based court selection
    scene_environment/                               # Per-location lighting/post-processing
      iron_throne_court_scene_environment.txt
      winterfell_court_scene_environment.txt
      casterly_rock_court_scene_environment.txt
      pyke_court_scene_environment.txt
      high_garden_court_scene_environment.txt
    scene_settings/                                  # Per-location scene configs + grandeur levels
  editor_terrain/                  # Reference overlays for map editing
  interface/
    bookmarks/                     # Bookmark start buttons
    coat_of_arms/frames/           # CoA frame textures
    icons/                         # Full icon set: traits, buildings, faiths, cultures, etc.
      traits/                      # AGOT trait icons
      building_types/
      faith/
      faith_doctrines/
      government_types/
      patron_gods/
      terrain_types/
      ... (40+ icon categories)
  map/
    environment/                   # Map lighting/atmosphere
    terrain/                       # Custom terrains (redmountain, redsand) + masks
    map_object_data/               # Map item placement data
    rivers/, water/, textures/     # Map rendering overrides
  models/
    animals/                       # Dragon model + vanilla animals
      dragon_01/                   # Dragon_01_diffuse.dds, Dragon_01_normal.dds
    artifacts/agot/                # ~30 unique artifact models
    buildings/
      holdings/                    # ~24 culture-specific building GFX sets
      special/                     # ~47 unique location models
    court/rooms/                   # 8 unique throne room models
    environment/                   # Map-placed entities (dragon_01, raven, etc.)
    mapitems/                      # Custom map decorations (16 categories)
  particles/                       # Court room light effects
  portraits/
    accessories/                   # 14 agot_*.txt files defining portrait accessories
    accessory_variations/          # ~20 agot_*.txt files for regional texture variations
    cameras/                       # Dragon and coronation cameras
    environments/                  # AGOT portrait lighting
    portrait_animations/           # Dragon, egg, sword animations
    portrait_modifiers/            # ~40 files: dragon genes, appearance, clothes, etc.
    trait_portrait_modifiers/      # Dragon trait modifiers, AGOT trait modifiers
  skins/hud_skins/                 # HUD skin overrides
```

## Dragon Models & Textures

AGOT implements dragons as characters that display 3D dragon models instead of
human portraits. This is the most complex GFX addition.

### Dragon 3D Model (Map Entity)

The map-placed dragon model lives at `gfx/models/environment/dragon_01/`:

```
gfx/models/environment/dragon_01/
  dragon_01.asset      # pdxmesh + entity definition
  dragon_01.mesh       # 3D mesh file
  dragon_idle_1.anim   # Idle animation variant 1
  dragon_idle_2.anim   # Idle animation variant 2
```

The asset file defines both mesh and entity with animation states:

```
pdxmesh = {
    name = "dragon_01_mesh"
    file = "dragon_01.mesh"
    scale = 0.35
    animation = { id = "dragon_idle_1" type = "dragon_idle_1.anim" }
    animation = { id = "dragon_idle_2" type = "dragon_idle_2.anim" }
    meshsettings = {
        name = "jorodoxShape"
        index = 0
        texture_diffuse = "Dragon_01_diffuse.dds"
        texture_normal = "Dragon_01_normal.dds"
        texture_specular = "whale_properties.dds"
        shader = "standard"
        shader_file = "gfx/FX/pdxmesh.shader"
    }
}

entity = {
    name = "dragon_01_entity"
    pdxmesh = "dragon_01_mesh"
    get_state_from_parent = no
    default_state = "idle"
    state = {
        name = "idle"
        animation = "dragon_idle_1"
        chance = 4
        looping = no
        next_state = idle
    }
    state = {
        name = "idle"
        animation = "dragon_idle_2"
        chance = 1
        looping = no
        next_state = idle
    }
}
```

Dragon textures (diffuse, normal) are in `gfx/models/animals/dragon_01/`.

### Dragon Portrait Accessories

Dragons appear in the portrait system via custom accessory genes defined in
`gfx/portraits/accessories/agot_dragon.txt`:

```
dragon = {
    entity = {  node = "dragon_origin"  entity = "dragon_entity" }
}

dragon_shadow = {
    entity = {  node = "dragon_origin"  entity = "dragon_shadow_entity" }
}

saddle = {
    entity = {  node = "dragon_origin"  entity = "saddle_entity" }
}
```

These are attached via trait portrait modifiers in
`gfx/portraits/trait_portrait_modifiers/agot_dragon_trait_modifiers.txt`, which
triggers on the `dragon` trait and applies custom genes:

- `gene_dragon` / `gene_dragon_shadow` -- The dragon 3D model and its shadow
- `gene_no_portrait` -- Removes the human body from the portrait
- `gene_age` -- Disables child aging effects that interfere with the camera
- Color genes: `gene_dragon_primary_color_hue`,
  `gene_dragon_primary_color_value`, `gene_dragon_secondary_hue`,
  `gene_dragon_secondary_value`, `gene_dragon_tertiary_hue`,
  `gene_dragon_tertiary_value`, `gene_dragon_eye_color_hue`,
  `gene_dragon_eye_color_value`, `gene_dragon_horn_color_hue`,
  `gene_dragon_horn_color_value`
- Shape genes: `gene_dragon_size`, `gene_dragon_brow_width`,
  `gene_dragon_cheek_width`
- Camera gene: `gene_camera_zoom` (scaled by `dragon_size_svalue`)

### Dragon Cameras

Dedicated cameras in
`gfx/portraits/cameras/zz_agot_dragon_portrait_cameras.txt`:

```
camera_dragon = {
    camera = {
        position = cylindrical{ 200 40 15 }
        position_node = { default = dragon_origin }
        look_at = { 0 40 0 }
        look_at_node = { default = dragon_origin }
        fov = 35
        camera_near_far = { 50 10000 }
    }
    unknown = "gfx/portraits/unknown_portraits/unknown_unclickable_small.dds"
}
```

Note the large `camera_near_far` range (50-10000) needed for dragon scale.

### Dragon Animations

Defined in `gfx/portraits/portrait_animations/e_agot_dragon_animations.txt`:

```
dragon_main = {
    male = {
        default = { head = "idle" torso = "dragon_idle" }

        dragon_idle = {
            animation = { head = "idle" torso = "dragon_idle" }
            weight = {
                base = 0
                modifier = {
                    add = 100
                    OR = {
                        AND = {
                            portrait_has_trait_trigger = { TRAIT = dragon }
                            NOT = {
                                has_character_flag = dragon_flying
                                has_character_flag = dragon_roar
                                has_character_flag = dragon_hover
                            }
                        }
                        has_character_flag = dragon_idle
                    }
                }
            }
            portrait_modifier = { camera_zoom = dragon_camera_1_zoom }
        }

        dragon_flying = {
            animation = { head = "idle" torso = "dragon_flying" }
            weight = {
                base = 0
                modifier = { add = 500  has_character_flag = dragon_flying }
            }
            portrait_modifier = { camera_zoom = dragon_camera_1_zoom }
        }

        dragon_roar = { ... }
        dragon_hover = { ... }
    }
    ...
}
```

Animation variants are selected using character flags: `dragon_idle`,
`dragon_flying`, `dragon_roar`, `dragon_hover`.

### Dragon Artifact Models

Dragon skull artifacts come in multiple sizes at
`gfx/models/artifacts/agot/dragon skulls/`:

| Path                                                         | Entity                             |
| ------------------------------------------------------------ | ---------------------------------- |
| `dragon skulls/dragon_skull_main.asset`                      | `dragon_skull_main_entity` (large) |
| `dragon skulls/medium dragon/dragon_skull_main_medium.asset` | Medium skull                       |
| `dragon skulls/small dragon/dragon_skull_main_small.asset`   | Small skull                        |
| `dragon skulls/baby_dragon_skull/baby_dragon_skull.asset`    | Baby skull                         |

Artifact models use the `portrait_attachment` shader:

```
meshsettings = {
    shader = "portrait_attachment"
    shader_file = "gfx/FX/jomini/portrait.shader"
}
```

Other dragon-related artifacts: `dragonbinder/`, `dragondolls/`, `dragonegg/`.

## Portrait Modifications

AGOT completely overhauls the portrait system with region-specific clothing and
ASOIAF-themed accessories.

### Portrait Accessories (`gfx/portraits/accessories/`)

| File                      | Content                           |
| ------------------------- | --------------------------------- |
| `agot_clothes.txt`        | Region-specific clothing          |
| `agot_cloaks.txt`         | Kingsguard, regional cloaks       |
| `agot_headgear.txt`       | Crowns, helms, religious headwear |
| `agot_hairstyles.txt`     | Culture-specific hairstyles       |
| `agot_beards.txt`         | Beard styles                      |
| `agot_jewelry.txt`        | Chains, necklaces, rings          |
| `agot_legwear.txt`        | Boots, leggings                   |
| `agot_bodyparts.txt`      | Body modifications                |
| `agot_custom_stuff.txt`   | Miscellaneous accessories         |
| `agot_dragon.txt`         | Dragon model, shadow, saddle      |
| `agot_egg_props.txt`      | Dragon egg held props             |
| `agot_sword_props.txt`    | Sword held props                  |
| `agot_animal_friends.txt` | Companion animals                 |

### Accessory Variations (`gfx/portraits/accessory_variations/`)

Region-based texture/color variations for clothing and armor:

| File                                   | Purpose                       |
| -------------------------------------- | ----------------------------- |
| `AGOT_coa_armors.txt`                  | CoA-emblazoned armor textures |
| `agot_crownlander.txt`                 | Crownlands color schemes      |
| `agot_dornish.txt`                     | Dornish styles                |
| `agot_reach.txt`                       | Reach styles                  |
| `agot_stormlander.txt`                 | Stormlands styles             |
| `agot_westerlander.txt`                | Westerlands styles            |
| `agot_the_north.txt`                   | Northern styles               |
| `agot_pirate_and_free_cities.txt`      | Essos styles                  |
| `agot_qolab.txt`                       | Qohor/Lorath styles           |
| `agot_kingsguard_cloak.txt`            | White cloak variations        |
| `agot_maester.txt`                     | Maester chain variations      |
| `agot_faction_colors.txt`              | Faction-colored accessories   |
| `agot_dragon_saddle.txt`               | Dragon saddle textures        |
| `agot_heterochromia_eye.txt`           | Heterochromia eye colors      |
| `agot_historical_clothes_patterns.txt` | Historical character outfits  |

### Portrait Modifiers (`gfx/portraits/portrait_modifiers/`)

AGOT adds a layered system of portrait modifiers with numbered prefixes for load
order:

- `00_agot_appearance_overrides.txt` -- Height, ear shape, scripted appearance
  DNA
- `00_agot_dragon_genes.txt` -- Strips all clothing/accessories from dragon
  portraits
- `00_agot_hair_dye_overrides.txt` -- Hair color overrides
- `00_agot_custom_jewelry.txt` -- Custom jewelry selection
- `00_agot_misc_dna.txt` -- Miscellaneous DNA overrides
- `00_agot_visible_disfigurement_overrides.txt` -- Disfigurement visual effects
- `00_agot_camera_zoom.txt` -- Camera zoom adjustments
- `01_*_base.txt` -- Base clothing/hair/beard/headgear/cloak/legwear/jewelry
  selection
- `02_agot_beard_traits.txt`, `02_agot_hair_traits.txt` -- Trait-based
  hair/beard
- `02_all_agot_characters.txt`, `02_all_historical_characters.txt` --
  Character-specific overrides
- `03_clothes_religious.txt`, `03_headgear_religious.txt` -- Religious garb
- `04_clothes_armor.txt`, `04_headgear_armor.txt` -- Armor sets
- `05_clothes_situational.txt`, `05_headgear_situational.txt` --
  Context-dependent outfits
- `06_agot_epe_makeup.txt`, `06_clothes_special.txt`, `06_headgear_special.txt`
  -- Special overrides
- `99_special.txt` -- Final overrides

### Trait Portrait Modifiers (`gfx/portraits/trait_portrait_modifiers/`)

- `00_trait_modifiers.txt` -- Base trait visual effects
- `agot_dragon_trait_modifiers.txt` -- Dragon gene application (replaces
  portrait with dragon model)
- `agot_trait_modifiers.txt` -- AGOT-specific trait visual effects

### Portrait Animations

- `animations.txt` -- Overridden vanilla animations
- `b_agot_animations.txt` -- AGOT character animations
- `c_agot_eggs_animations.txt` -- Dragon egg display animations
- `d_agot_sword_animations.txt` -- Sword display animations
- `e_agot_dragon_animations.txt` -- Dragon portrait animations (idle, flying,
  roar, hover)

### Portrait Cameras and Environments

- `gfx/portraits/cameras/zz_agot_dragon_portrait_cameras.txt` -- Dragon cameras
- `gfx/portraits/cameras/zz_agot_coronation_cameras.txt` -- Coronation event
  cameras
- `gfx/portraits/cameras/zz_agot_portrait_cameras.txt` -- General portrait
  cameras
- `gfx/portraits/environments/portrait_environments_agot.txt` -- AGOT-specific
  lighting for throne rooms (Braavos, etc.)

## Coat of Arms

AGOT adds a massive library of heraldic assets for Westerosi and Essos houses.

### Custom Colored Emblems

~1173 custom DDS files in `gfx/coat_of_arms/colored_emblems/`. Naming
conventions:

- `ce_*` -- Standard colored emblems (follow vanilla convention)
- `asoiaf_*` -- ASOIAF-specific emblems (e.g., `asoiaf_knight_poised.dds`)
- `ce_blacktyde.dds` -- House-specific emblems
- Division/ordinary emblems: `1_division_*.dds`, `1_ordinary_*.dds`,
  `2_charge_*.dds`

The designer catalog is
`gfx/coat_of_arms/colored_emblems/50_coa_designer_emblems.txt` (note: `50_`
prefix ensures it loads after vanilla's `49_`).

### Custom Patterns

~68 pattern DDS files in `gfx/coat_of_arms/patterns/`. AGOT patterns use the
`agotp_` prefix:

- `agotp_bend_sinister_01.dds`
- `agotp_chevrony_01.dds`
- `agotp_diagonal_01.dds`, `agotp_diagonal_02.dds`
- `agotp_gyronny_1.dds`, `agotp_gyronny_2.dds`
- `agotp_myr_pattern01.dds`
- `agotp_potenty_01.dds`
- `agotp_quarter01.dds`, `agotp_quarter02.dds`

Designer catalog: `gfx/coat_of_arms/patterns/50_coa_designer_patterns.txt`.

### Custom Textured Emblems

Region-specific textured emblems in `gfx/coat_of_arms/textured_emblems/`:

- `crownlands_leek.dds`
- `reach_tarly.dds`
- `vale_marks.dds`, `vale_bommenstone_rottenapple.dds`
- `west_taves.dds`
- `te_citadel_chain.dds`, `te_bird_robin_01.dds`, `te_woman_01.dds`

Designer catalog:
`gfx/coat_of_arms/textured_emblems/49_coa_designer_emblems.txt`.

### Custom Color Palette

`gfx/coat_of_arms/color_palettes/agot_coa_designer_palettes.txt` defines
AGOT-specific named colors for the CoA designer:

- Vanilla-mapped colors: `agot_red`, `agot_blue`, `agot_yellow`, `agot_green`,
  `agot_black`, `agot_white`, `agot_purple`, `agot_orange`, `agot_grey`,
  `agot_brown`, `agot_blue_light`, `agot_green_light`, `agot_yellow_light`
- AGOT additions: `agot_cream`, `agot_bone`, `agot_mud`, `agot_russet`, and more

## Court Scenes

### Location-Based Court Rooms

AGOT assigns unique court rooms based on the ruler's capital county. The mapping
is in `gfx/court_scene/scene_cultures/agot_default_cultures.txt`:

```
pyke = {
    trigger = { capital_county = title:c_pyke }
}

ironthrone = {
    trigger = { capital_county = title:c_kings_landing }
}

casterlyrock = {
    trigger = { capital_county = title:c_casterly_rock }
}

highgarden = {
    trigger = {
        capital_county = title:c_highgarden
        NOT = { any_equipped_character_artifact = { has_variable = restored_oakenseat } }
    }
}

highgarden_new = {
    trigger = {
        capital_county = title:c_highgarden
        any_equipped_character_artifact = { has_variable = restored_oakenseat }
    }
}

dragonstone = {
    trigger = {
        capital_county = title:c_dragonstone
        any_character_artifact = { has_variable = painted_table  is_equipped = yes }
    }
}
```

Note: Some courts have variant conditions (Highgarden with/without Oakenseat,
Dragonstone with/without painted table).

### Court Room 3D Models

Located in `gfx/models/court/rooms/`:

- `redkeep/` -- Iron Throne / Red Keep
- `winterfell/` -- Winterfell Great Hall
- `pyke/` -- Pyke Seastone Chair
- `casterlyrock/` -- Casterly Rock
- `dragonstone/` -- Dragonstone (with painted table variants)
- `highgarden/` -- Highgarden
- `eyrie/` -- The Eyrie
- `suncourt/` -- Dornish court

### Scene Environments

Per-location post-processing and lighting in
`gfx/court_scene/scene_environment/`:

- `iron_throne_court_scene_environment.txt`
- `winterfell_court_scene_environment.txt`
- `casterly_rock_court_scene_environment.txt`
- `pyke_court_scene_environment.txt`
- `high_garden_court_scene_environment.txt`

These configure exposure, tonemapping, bloom, SSAO, shadow maps, and color
balance per court.

## AGOT-Specific Template

### Adding a New CoA Emblem for AGOT

1. Create your emblem DDS at `gfx/coat_of_arms/colored_emblems/ce_my_emblem.dds`
2. Register it in a new designer file (do NOT modify
   `50_coa_designer_emblems.txt`):

```
# gfx/coat_of_arms/colored_emblems/99_my_submod_emblems.txt
ce_my_emblem.dds = { colors = 2 category = animals }
```

### Adding a New Dragon Accessory Variation

```
# gfx/portraits/accessory_variations/my_dragon_saddle.txt
variation = {
    name = "my_dragon_saddle_01"
    pattern = {
        weight = 1
        r = { textures = "leather_plain_01"  layout = "western_silk_brocade_01_layout" }
        g = { textures = "leather_plain_01"  layout = "plain_fabric_layout" }
        b = { textures = "leather_plain_01"  layout = "small_trim_layout" }
        a = { textures = "all_silver_plain_rough_01"  layout = "plain_fabric_layout" }
    }
    color_palette = {
        weight = 1
        texture = "gfx/portraits/accessory_variations/textures/my_saddle_palette.dds"
    }
}
```

### Adding a New Map Item

1. Create model files: `.mesh`, `_diffuse.dds`, `_normal.dds`, `_properties.dds`
2. Define asset + entity in a `.asset` file under `gfx/models/mapitems/my_item/`
3. Reference the entity in map object data files

### Adding a New Artifact Model

Follow the AGOT pattern at `gfx/models/artifacts/agot/`:

```
# gfx/models/artifacts/agot/my_artifact/my_artifact.asset
pdxmesh = {
    name = "my_artifact_mesh"
    file = "my_artifact.mesh"
    meshsettings = {
        name = "my_artifactShape"
        index = 0
        texture_diffuse = "my_artifact_diffuse.dds"
        texture_normal = "my_artifact_normal.dds"
        texture_specular = "my_artifact_properties.dds"
        shader = "portrait_attachment"
        shader_file = "gfx/FX/jomini/portrait.shader"
    }
}

entity = {
    name = "my_artifact_entity"
    pdxmesh = "my_artifact_mesh"
}
```

## Building Model Creation Pipeline

AGOT implements culture-specific building GFX sets that replace vanilla's
generic building models on the map. Each set follows a standardized pipeline
from 3D mesh to in-game rendering.

### Pipeline Overview

```
.mesh file (3D model)
    |
    v
.asset file (pdxmesh + entity definition)
    |
    v
Entity referenced by building type definitions (common/buildings/)
    |
    v
graphical_culture assignment (common/culture/cultures/)
```

### Andal Building Set Example (magyar)

The `andal_building_gfx` set uses a magyar sub-style. File structure at
`gfx/models/buildings/holdings/andal_building_gfx/magyar/`:

```
magyar_castle_01/    # Castle upgrade level 1
magyar_castle_02/    # Castle upgrade level 2
magyar_castle_03/    # Castle upgrade level 3
magyar_castle_04/    # Castle upgrade level 4
magyar_cities/       # City holding models
magyar_walls_03/     # Wall upgrade level 3
magyar_walls_04/     # Wall upgrade level 4
```

Each subfolder contains a `.mesh` file, a `.asset` file, and optional unique
textures. The asset file (`magyar_castle_01.asset`):

```
pdxmesh = {
    name = "magyar_castle_01_mesh"
    file = "magyar_castle_01.mesh"
    scale = 1.1

    meshsettings = {
        name = "magyar_castle_01Shape"
        index = 0
        texture_diffuse = "building_western_atlas_diffuse.dds"
        texture_normal = "building_western_atlas_normal.dds"
        texture_specular = "building_western_atlas_properties.dds"
        texture = { file = "magyar_castle_01_unique.dds" index = 5 }
        shader = "standard_atlas"
        shader_file = "gfx/FX/pdxmesh.shader"
    }
}

entity = {
    name = "magyar_castle_01_entity"
    pdxmesh = "magyar_castle_01_mesh"
}
```

Key observations:

- Uses `standard_atlas` shader -- shares a common texture atlas
  (`building_western_atlas_*.dds`) with a per-model unique overlay at texture
  index 5
- The `scale = 1.1` adjusts the model size relative to default
- Entity name follows the convention `{model_name}_entity`

### First Man Building Set Example (brythonic)

The `first_man_building_gfx` set uses a Celtic/brythonic style. File structure
at `gfx/models/buildings/holdings/first_man_building_gfx/`:

```
brythonic_castle_01_a/   # Castle variant A
brythonic_castle_01_b/   # Castle variant B
brythonic_castle_02/     # Castle level 2
brythonic_castle_03/     # Castle level 3
brythonic_castle_04/     # Castle level 4
brythonic_wall_01/       # Wall model
celtic_citites/          # City holding models
celtic_druid_tower/      # Druid tower (religion building)
celtic_dyke_tower/       # Dyke tower
celtic_tribal/           # Tribal holding model
celtic_wall_01/          # Celtic wall variant 1
celtic_wall_01_a/        # Celtic wall variant 1a
celtic_wall_02/          # Celtic wall variant 2
```

The brythonic castle asset (`brythonic_castle_01_a.asset`):

```
pdxmesh = {
    name = "brythonic_castle_01_a_mesh"
    file = "brythonic_castle_01_a.mesh"

    meshsettings = {
        name = "brythonic_castle_01_a"
        index = 0
        texture_diffuse = "building_celtic_02_diffuse.dds"
        texture_normal = "building_celtic_02_normal.dds"
        texture_specular = "building_celtic_02_properties.dds"
        texture = { file = "brythonic_castle_01_a_unique.dds" index = 5 }
        shader = "snap_to_terrain_atlas"
        shader_file = "gfx/FX/pdxmesh.shader"
    }
}

entity = {
    name = "brythonic_castle_01_a_entity"
    pdxmesh = "brythonic_castle_01_a_mesh"
}
```

Key differences from the andal set:

- Uses `snap_to_terrain_atlas` shader -- the model conforms to terrain height
  rather than floating
- Has its own Celtic texture set (`building_celtic_02_*.dds`) separate from the
  western atlas
- Also uses the unique texture overlay at index 5

### Special Building Models

Special buildings are unique 3D models for specific locations. They use simpler
asset definitions without atlas textures.

**Winterfell** (`gfx/models/buildings/special/Winterfell/winterfell_new.asset`):

```
pdxmesh = {
    name = "winterfell_new_mesh"
    file = "winterfell_new.mesh"

    meshsettings = {
        name = "winterfell_new_outerShape"
        index = 0
        texture_diffuse = "winterfell_new_outer_diffuse.dds"
        texture_normal = "winterfell_new_outer_normal.dds"
        texture_specular = "winterfell_new_outer_properties.dds"
        shader = "standard_winter"
        shader_file = "gfx/FX/pdxmesh.shader"
    }

    meshsettings = {
        name = "winterfell_new_innerShape"
        index = 0
        texture_diffuse = "winterfell_new_inner_diffuse.dds"
        texture_normal = "winterfell_new_inner_normal.dds"
        texture_specular = "winterfell_new_inner_properties.dds"
        shader = "standard_winter"
        shader_file = "gfx/FX/pdxmesh.shader"
    }
}

entity = {
    name = "winterfell_new_entity"
    pdxmesh = "winterfell_new_mesh"
}
```

Note: Winterfell uses `standard_winter` shader for snow rendering and has two
mesh settings (outer walls and inner courtyard) with separate texture sets.

**Harrenhal**
(`gfx/models/buildings/special/Harrenhal/building_special_Harrenhal_keep_ruined.asset`):

```
pdxmesh = {
    name = "building_special_Harrenhal_keep_ruined_mesh"
    file = "building_special_Harrenhal_keep_ruined.mesh"

    meshsettings = {
        name = "building_special_Harrenhal_keep_ruinedShape"
        index = 0
        texture_diffuse = "building_special_Harrenhal_keep_ruined_diffuse.dds"
        texture_normal = "building_special_Harrenhal_keep_ruined_normal.dds"
        texture_specular = "building_special_Harrenhal_keep_ruined_properties.dds"
        shader = "snap_to_terrain"
        shader_file = "gfx/FX/pdxmesh.shader"
    }
    meshsettings = {
        name = "building_special_Harrenhal_wallsShape"
        index = 0
        texture_diffuse = "building_special_Harrenhal_walls_diffuse.dds"
        texture_normal = "building_special_Harrenhal_walls_normal.dds"
        texture_specular = "building_special_Harrenhal_walls_properties.dds"
        shader = "snap_to_terrain"
        shader_file = "gfx/FX/pdxmesh.shader"
    }
}

entity = {
    name = "building_special_Harrenhal_keep_ruined_entity"
    pdxmesh = "building_special_Harrenhal_keep_ruined_mesh"
}
```

Note: Harrenhal uses `snap_to_terrain` shader (no atlas, no winter) and
separates keep and walls into distinct mesh settings with their own textures.

### Building Shader Summary

| Shader                  | Usage                          | Behavior                                            |
| ----------------------- | ------------------------------ | --------------------------------------------------- |
| `standard_atlas`        | Andal holdings                 | Shared atlas + unique overlay, raised above terrain |
| `snap_to_terrain_atlas` | First Man holdings             | Shared atlas + unique overlay, conforms to terrain  |
| `snap_to_terrain`       | Special buildings (Harrenhal)  | Dedicated textures, conforms to terrain             |
| `standard_winter`       | Special buildings (Winterfell) | Dedicated textures, snow rendering                  |
| `standard`              | Map entities (dragons)         | Standard rendering                                  |

## Holding GFX Sets Inventory

All culture-specific building GFX sets in `gfx/models/buildings/holdings/`:

| Folder                          | Culture/Region               | Description                                       |
| ------------------------------- | ---------------------------- | ------------------------------------------------- |
| `agot_building_ruin_gfx/`       | Ruins                        | Ruined building variants for destroyed holdings   |
| `andal_building_gfx/`           | Andal (magyar)               | Westeros generic Andal castle/city/wall models    |
| `barrow_building_gfx/`          | Barrowlands                  | Barrow Kings-style buildings                      |
| `crannog_building_gfx/`         | Crannogmen                   | Swamp stilt-house buildings (The Neck)            |
| `dawnbringer_god_gfx/`          | Dawnbringer faith            | Religious building models                         |
| `first_man_building_gfx/`       | First Men (brythonic/celtic) | Northern-style stone buildings                    |
| `fots_god_gfx/`                 | Faith of the Seven           | Sept/religious building models                    |
| `ghis_building_gfx/`            | Ghiscari                     | Slaver's Bay pyramid/brick architecture           |
| `hyrkoon_building_gfx/`         | Hyrkoon                      | Eastern fortress architecture                     |
| `ironborn_building_gfx/`        | Ironborn                     | Iron Islands longhouse/fortress style             |
| `lyseni_building_gfx/`          | Lysene/Free Cities           | Pleasure-city architecture                        |
| `norvoshi_building_gfx/`        | Norvoshi                     | Norvos beehive-tower architecture                 |
| `old_gods_gfx/`                 | Old Gods faith               | Weirwood groves and godswood buildings            |
| `qartheen_building_gfx/`        | Qartheen                     | Qarth walled-city architecture                    |
| `reach_building_gfx/`           | Reach                        | Highgarden-style verdant architecture             |
| `riverlander_building_gfx/`     | Riverlander                  | Riverlands-style buildings                        |
| `summer_god_gfx/`               | Summer Islands faith         | Tropical religious building models                |
| `summer_islander_building_gfx/` | Summer Islanders             | Tropical island architecture                      |
| `westerman_building_gfx/`       | Westermen                    | Westerlands gold-accented architecture            |
| `wildling_building_gfx/`        | Wildlings/Free Folk          | Beyond-the-Wall primitive structures              |
| `yitish_building_gfx/`          | Yi Ti                        | Far Eastern pagoda/palace architecture            |
| `yitish_god_gfx/`               | Yi Ti faith                  | Yi Ti religious building models                   |
| `atlas/`                        | Shared                       | Common atlas texture sheets used by multiple sets |

Total: 23 building GFX sets (including atlas).

## Special Building Models Inventory

All unique location models in `gfx/models/buildings/special/`:

| Folder                   | Location              | Description                                              |
| ------------------------ | --------------------- | -------------------------------------------------------- |
| `Bitterbridge/`          | Bitterbridge          | Bridge crossing on the Mander                            |
| `Braavos/`               | Braavos               | Braavosi canal city architecture                         |
| `Bridge of Skulls/`      | Bridge of Skulls      | Narrow passage in the Mountains of the Moon              |
| `Casterly Rock/`         | Casterly Rock         | The Lannister seat carved into the Rock                  |
| `Castle Black/`          | Castle Black          | Night's Watch headquarters                               |
| `Docks/`                 | Various ports         | Generic dock/harbor models                               |
| `Dragonstone/`           | Dragonstone           | Targaryen island fortress                                |
| `Eastwatch/`             | Eastwatch-by-the-Sea  | Eastern Night's Watch castle                             |
| `Empty/`                 | (fallback)            | Empty/placeholder models                                 |
| `Fist of the First Men/` | Fist of the First Men | Ancient ringfort beyond the Wall                         |
| `Ghaston Grey/`          | Ghaston Grey          | Dornish island prison                                    |
| `Gulltown/`              | Gulltown              | Major Vale port city                                     |
| `Hammerhorn/`            | Hammerhorn            | Iron Islands fortress                                    |
| `Hardhome/`              | Hardhome              | Ruined wildling settlement                               |
| `Harrenhal/`             | Harrenhal             | Massive ruined castle (with Redo subfolder for variants) |
| `Highgarden/`            | Highgarden            | Tyrell seat with garden architecture                     |
| `Hoare Castle/`          | Hoare Castle          | Ancient Ironborn castle                                  |
| `Inn at the Crossroads/` | Inn at the Crossroads | Famous Riverlands inn                                    |
| `Kings Landing/`         | King's Landing        | Capital city of the Seven Kingdoms                       |
| `Lannisport/`            | Lannisport            | Major Westerlands port city                              |
| `Lonely Light/`          | Lonely Light          | Westernmost Iron Island                                  |
| `Lys/`                   | Lys                   | Free City of pleasure                                    |
| `Moat Cailin/`           | Moat Cailin           | Ruined fortress guarding the Neck                        |
| `Myr/`                   | Myr                   | Free City of craftsmen                                   |
| `Oldtown/`               | Oldtown               | Hightower and Citadel                                    |
| `Pentos/`                | Pentos                | Free City on the Narrow Sea                              |
| `Pyke/`                  | Pyke                  | Greyjoy seat on the Iron Islands                         |
| `Riverrun/`              | Riverrun              | Tully seat at the confluence of rivers                   |
| `Sea Dragon Point/`      | Sea Dragon Point      | Northern peninsula                                       |
| `Shadow Tower/`          | Shadow Tower          | Western Night's Watch castle                             |
| `Storms End/`            | Storm's End           | Baratheon seat, storm-resistant fortress                 |
| `Summerhall/`            | Summerhall            | Ruined Targaryen palace                                  |
| `Sunspear/`              | Sunspear              | Martell seat in Dorne                                    |
| `Ten Towers/`            | Ten Towers            | Harlaw seat on the Iron Islands                          |
| `The Bloody Gate/`       | The Bloody Gate       | Mountain pass fortress guarding the Vale                 |
| `The Childrens Tower/`   | The Children's Tower  | Ancient tower                                            |
| `The Dreadfort/`         | The Dreadfort         | Bolton seat                                              |
| `The Eyrie/`             | The Eyrie             | Arryn seat in the Mountains of the Moon                  |
| `The Twins/`             | The Twins             | Frey twin castles spanning the Green Fork                |
| `The Wall/`              | The Wall              | 700-foot ice wall spanning the North                     |
| `Titan of Braavos/`      | Titan of Braavos      | Giant statue guarding Braavos harbor                     |
| `Tower of Joy/`          | Tower of Joy          | Remote tower in the Red Mountains                        |
| `Tyrosh/`                | Tyrosh                | Free City of dyers                                       |
| `Weirwood Circles/`      | Various               | Sacred weirwood grove models                             |
| `White Harbour/`         | White Harbour         | Major Northern port city                                 |
| `Winterfell/`            | Winterfell            | Stark seat with inner/outer walls                        |
| `gravensteen/`           | Gravensteen           | Castle model                                             |

Total: 47 special building locations.

## Map Object Placement

AGOT places 3D objects on the map using files in `gfx/map/map_object_data/`.
These define positioned entities for walls, animals, special structures, trees,
and environmental effects.

### Map Object Data Format

Each file contains one or more `object={}` blocks. The format:

```
object={
    name="hadrians wall 04"
    render_pass=MapUnderWater
    clamp_to_water_level=no
    generated_content=no
    layer="temp_layer"
    pdxmesh="hadrians_wall_01_d_mesh"
    count=183
    transform="X Y Z  qX qY qZ qW  sX sY sZ
    X Y Z  qX qY qZ qW  sX sY sZ
    ..."
}
```

### Transform Data Format

Each transform entry is 10 floating-point values on a single line:

```
posX posY posZ  quatX quatY quatZ quatW  scaleX scaleY scaleZ
```

- **Position** (X, Y, Z): World coordinates on the map. Y is the height axis.
- **Rotation** (quatX, quatY, quatZ, quatW): Quaternion rotation. `0 0 0 1` = no
  rotation.
- **Scale** (scaleX, scaleY, scaleZ): Uniform scale is common (all three values
  identical).

### Object Properties

| Property               | Values                 | Description                                            |
| ---------------------- | ---------------------- | ------------------------------------------------------ |
| `name`                 | String                 | Display name for the editor                            |
| `render_pass`          | `Map`, `MapUnderWater` | Rendering layer priority                               |
| `clamp_to_water_level` | `yes`/`no`             | Whether object sticks to water surface                 |
| `generated_content`    | `yes`/`no`             | Whether engine auto-generates placement                |
| `layer`                | String                 | Editor layer for grouping (see below)                  |
| `entity`               | String                 | Entity name to render (from .asset files)              |
| `pdxmesh`              | String                 | Alternative: reference mesh directly instead of entity |
| `count`                | Integer                | Number of instances placed                             |
| `transform`            | Float values           | Quoted string of all instance transforms               |

### AGOT Map Object Layers

AGOT defines custom layers for organizing map objects:

| Layer                        | Used For                                                 |
| ---------------------------- | -------------------------------------------------------- |
| `AGOT_building_layer`        | Special building meshes (Pyke bridges, Bridge of Skulls) |
| `AGOT_animal_layer`          | Animal entities (whales, bears, crocodiles)              |
| `building_layer`             | Standard building placements                             |
| `tree_high_layer`            | Tree objects including weirwood trees                    |
| `temp_layer`                 | Wall segments (The Wall/Hadrian's wall)                  |
| `coast_foam_layer`           | Coast splash and wave effects                            |
| `env_effect_mountains_layer` | Environmental fog/effects                                |

### AGOT-Specific Map Object Files

| File                            | Content                                                                                      |
| ------------------------------- | -------------------------------------------------------------------------------------------- |
| `agot_animals.txt`              | Animal placements: crocodiles (35), brown bears (21+), whales (64)                           |
| `agot_building_layer.txt`       | Special structures: Pyke Bridge, docks, weirwood trees (50+), Bridge of Skulls               |
| `agot_misc_entities.txt`        | Coast splashes, sea fog, whale entities                                                      |
| `agot_map_crowned_stag.txt`     | Crowned stag bookmark map items                                                              |
| `agot_map_golden_age.txt`       | Golden age bookmark map items                                                                |
| `agot_map_penny_kings.txt`      | Penny kings bookmark map items                                                               |
| `agot_map_rogue_prince.txt`     | Rogue prince bookmark map items                                                              |
| `agot_map_rr.txt`               | Robert's Rebellion bookmark map items                                                        |
| `special.txt`                   | The Wall segments (183 wall pieces), Hadrian's wall, mines, barrow markers, weirwood circles |
| `special_building_locators.txt` | Game object locators linking special buildings to map positions                              |

### The Wall: A Case Study in Map Object Placement

The Wall is constructed from 183+ individual wall segment meshes placed
end-to-end. From `special.txt`:

```
object={
    name="hadrians wall 04"
    render_pass=MapUnderWater
    clamp_to_water_level=no
    generated_content=no
    layer="temp_layer"
    pdxmesh="hadrians_wall_01_d_mesh"
    count=183
    transform="1507.925659 0.000000 4421.604492 0.000000 -0.718042 0.000000 -0.696001 1.000000 1.000000 1.000000
1506.201538 0.000000 4462.084473 0.000000 -0.714856 0.000000 0.699272 1.000000 1.000000 1.000000
..."
}
```

Each wall piece is placed at Y=0 (ground level) with quaternion rotation to
follow the Wall's curved path across the map. Uniform scale of 1.0 maintains
consistent wall height.

### Weirwood Trees Placement

Weirwood trees are placed as map objects, not generated content. From
`agot_building_layer.txt`:

```
object={
    name="Weirwood1"
    render_pass=Map
    clamp_to_water_level=no
    generated_content=no
    layer="tree_high_layer"
    pdxmesh="mapitem_trees_weirwood_01_mesh"
    count=50
    transform="1976.068481 0.000000 2632.345703 0.000000 0.000000 0.000000 1.000000 1.000317 1.000317 1.000317
..."
}
```

50 individual weirwood trees are hand-placed across the map at sacred locations.

## Court Room Creation Pipeline

AGOT implements 8 unique court rooms for iconic Westerosi locations. Creating a
new court room requires 4 connected components.

### Pipeline Overview

```
3D room model (.mesh + textures)
    |
    v
Asset file (.asset) -- pdxmesh + entity definition
    |
    v
Scene settings file -- cameras, lights, character positions, assets
    |
    v
Scene cultures trigger -- which ruler gets this court
    |
    v
Scene environment -- post-processing, exposure, bloom, SSAO
```

### Step 1: Room Model (Asset File)

Court room assets use the `court` shader (not `standard` or `snap_to_terrain`).
The Red Keep room (`gfx/models/court/rooms/redkeep/agot_court_redkeep_1.asset`)
has 10 mesh settings for different architectural elements:

```
pdxmesh = {
    name = "agot_court_redkeep_1_mesh"
    file = "agot_court_redkeep_1.mesh"

    meshsettings = {
        name = "RK_Flr_Mrbl"
        index = 0
        texture_diffuse = "RK_Flr_Mrbl_01_diffuse.dds"
        texture_normal = "RK_Flr_Mrbl_01_normal.dds"
        texture_specular = "RK_Flr_Mrbl_01_properties.dds"
        shader = "court"
        shader_file = "gfx/FX/court_scene.shader"
    }
    # ... 9 more meshsettings for walls, pillars, windows, etc.
}

entity = {
    name = "agot_court_redkeep_1_entity"
    pdxmesh = "agot_court_redkeep_1_mesh"
}
```

The Red Keep model components: `RK_Flr_Mrbl` (marble floor), `RK_Lgt_Brk` (light
brick), `RK_Misc` (miscellaneous), `RK_Pil` (pillars), `RK_Pil_Brz_Rof_Dor`
(bronze pillar/roof/door), `RK_Wal_Brk` (wall brick), `RK_Wnd_Arch` (window
arches), `RK_Wnd_Glas_Sky` (sky-facing glass), `RK_Wnd_Glas_Throne` (throne
window glass), `RK_Wnd_Glas_Wal` (wall glass).

The Winterfell room
(`gfx/models/court/rooms/winterfell/agot_court_winterfell.asset`) demonstrates
particle effects attached to model nodes:

```
entity = {
    name = "agot_court_winterfell_entity"
    pdxmesh = "agot_court_winterfell_mesh"
    default_state = "idle"
    state = {
         name = "idle" state_time = 5 looping = yes
         event = {
             time = 0
             node = "wf_Candleflame_01"
             particle = "roco_candle"
             trigger_once = yes
             keep_particle = yes
         }
         # ... 15 more candle flame events on nodes wf_Candleflame_02 through _16
    }
}
```

This entity spawns candle particle effects at 16 pre-placed nodes in the 3D
mesh, creating the warm candlelit atmosphere.

### Court Room Model Inventory

| Folder          | Files                                                   | Notes                                  |
| --------------- | ------------------------------------------------------- | -------------------------------------- |
| `redkeep/`      | `agot_court_redkeep_1.*`, shadow mesh                   | 10 mesh components, stained glass      |
| `winterfell/`   | `agot_court_winterfell.*`                               | 4 mesh components, 16 candle particles |
| `pyke/`         | `agot_court_pyke_1.*`, `_2.*`, `_3.*`                   | 3 grandeur level variants              |
| `casterlyrock/` | `agot_court_casterlyrock.*`, shadow mesh                | Standard + shadow mesh                 |
| `dragonstone/`  | `agot_court_dragonstone.*`, hdri, painted_table, shadow | Variant with/without painted table     |
| `highgarden/`   | `agot_court_highgarden_old.*`, `_new.*`, hdri, shadow   | Old (with Oakenseat) and new variants  |
| `eyrie/`        | `agot_court_eyrie.*`, hdri, shadow                      | Standard + HDRI lighting mesh          |
| `suncourt/`     | `agot_sun_court.*`                                      | Dornish/Sunspear court                 |

### Step 2: Scene Settings

The scene settings file defines cameras, lights, character placements, and asset
positions. Located at `gfx/court_scene/scene_settings/`.

**Red Keep** (`scene_settings_redkeep_1.txt`) header:

```
name="RedKeep_1"
culture=ironthrone
visual_culture_level=1
cubemap="gfx/portraits/environments/agot_env_red_keep_01.dds"
environment="gfx/court_scene/scene_environment/court_scene_environment.txt"
audio_culture=1.000000
```

Key fields:

- `culture` -- Must match a scene_cultures entry name (e.g., `ironthrone`)
- `visual_culture_level` -- Grandeur tier (1, 2, or 3)
- `cubemap` -- HDRI environment map for reflections
- `environment` -- Path to post-processing settings file

**Camera definitions** (Red Keep has 30+ cameras):

```
camera={ {
    description="Default View"
    fov=50.000000
    position={ -59.460823 170.668350 -846.687439 }
    pitch=-7.055373
    yaw=0.240921
    camera_near_far={ 70.000000 2600.000000 }
    is_camera_used_for_screenshots=yes
    royal_court_camera_name_key="ROYAL_COURT_COURT_VIEW_CAMERA"
} ... }
default_camera=2
```

**Light definitions** use animated point/spot/disc/sphere lights for atmosphere:

```
lights={ {
    description="Fire Throne 01"
    light={
        type="point_light"
        radius=500.000000
        intensity=75.000000
        position={ -930.000000 158.000000 590.000000 }
        color={ 1.000000 0.385863 0.085938 }
        position_variation=0.250000
        position_variation_frequency=200.000000
        intensity_variation=6.000000
        intensity_variation_frequency=198.000000
        animation=yes
    }
    shadow_camera={ ... }
} ... }
```

**Character placements** define where courtiers stand:

```
characters={ {
    position={ 0.000000 437.300018 -120.399773 }
    locator="Ruler"
    description="Ruler"
    camera="Throne View"
    roles={ ruler }
} ... }
```

**Asset placements** put the room model and decorations in the scene:

```
assets={ {
    position={ 0.000000 0.000000 -500.000000 }
    scale=100.000000
    description="Red Keep"
    asset="agot_court_redkeep_1_entity"
} ... }
```

The Red Keep scene includes: the room entity at scale 100, Iron Throne model, 7
fireplace pairs (particles + logs), 6 stained glass shadow projections, god
rays, dust motes, and a shadow mesh for ambient occlusion.

**Artifact slot definitions**:

```
artifacts={ {
    locator="artifact_wall_large_1"
    position={ -1770.000000 1385.500000 -901.197998 }
    direction=-90.000000
    scale=4.800000
    slot=wall_big_1
} ... }
```

**Support type mappings** link artifact pedestal types to entities:

```
support_type={
    lectern=ep1_western_lectern_01_a_entity
    tall=ep1_western_pedestal_tall_01_a_entity
    cradle=egg_cradle_pedestal_bronze_entity
    armorstand=ep1_western_armorstand_01_entity
    short=ep1_western_pedestal_short_01_a_entity
}
```

### Step 3: Scene Culture Trigger

In `gfx/court_scene/scene_cultures/agot_default_cultures.txt`, map the scene to
a capital county (as documented in the Court Scenes section above). The
`culture` field in the scene settings must match the trigger name.

### Step 4: Scene Environment

Post-processing settings in `gfx/court_scene/scene_environment/`. The Iron
Throne environment (`iron_throne_court_scene_environment.txt`):

```
cubemap_intensity = 0.25

saturation_scale = 1.0
value_scale = 1.0
colorbalance = { 1 1 1 }
levels_min = hsv{ 0 0 0 }
levels_max = hsv{ 0 0 1 }

exposure_function = "FixedExposure"
exposure = 0.99

tonemap_function = "Uncharted"
tonemap_curve = {
    shoulder_strength = 0.22
    linear_strength = 0.29
    linear_angle = 0.1
    toe_strength = 0.2
    toe_numerator = 0.01
    toe_denominator = 0.3
    linear_white = 11.2
}

shadowmap_kernelscale = 7     #AGOT Modified, used to be 8
shadowmap_fadefactor = 0.75   #AGOT Modified, used to be 0.7

bloom_width = 3.0
bloom_scale = 0.35
bright_threshold = 1.0

ssao = {
    enabled = yes
    samples = 16
    radius = 25.167
    max_radius = 80.447
    blend_factor = 0.4
    # ... additional SSAO parameters
}
```

AGOT scene settings file inventory:

| File                                      | Court                               | Notes                   |
| ----------------------------------------- | ----------------------------------- | ----------------------- |
| `scene_settings_redkeep_1.txt`            | Red Keep / Iron Throne              | Single grandeur level   |
| `scene_settings_winterfell.txt`           | Winterfell                          | Single grandeur level   |
| `scene_settings_pyke_g1/g2/g3.txt`        | Pyke                                | 3 grandeur levels       |
| `scene_settings_casterlyrock_g1.txt`      | Casterly Rock                       | Single grandeur level   |
| `scene_settings_dragonstone.txt`          | Dragonstone (with painted table)    | Conditional variant     |
| `scene_settings_dragonstone_no_table.txt` | Dragonstone (without painted table) | Conditional variant     |
| `scene_settings_highgarden.txt`           | Highgarden (old)                    | Without Oakenseat       |
| `scene_settings_highgarden_new.txt`       | Highgarden (new)                    | With restored Oakenseat |
| `scene_settings_the_eyrie.txt`            | The Eyrie                           | Single grandeur level   |

## Custom Terrain Textures

AGOT adds custom terrain types to render the unique geography of Planetos. These
are defined in `gfx/map/terrain/materials.settings`.

### AGOT-Added Terrain Materials

After the vanilla materials (marked with `#AGOT Added Below`), AGOT adds these
custom terrain types:

**Unique Westerosi terrains:**

| ID              | Name          | Description                                 |
| --------------- | ------------- | ------------------------------------------- |
| `stone_tile`    | Stone tile    | Paved stone surfaces (castles, roads)       |
| `kingsroad`     | Kingsroad     | The King's Road surface texture             |
| `neckwater`     | Neckwater     | Boggy water terrain for The Neck            |
| `saltflats`     | Salt flats    | Flat salt terrain                           |
| `hardened_lava` | Hardened lava | Cooled volcanic rock (Valyria, Dragonstone) |
| `lava`          | Lava          | Active molten lava                          |
| `fallows`       | Fallows       | Fallow farmland                             |
| `wetlands_03`   | Wetlands 03   | Additional wetland variant                  |

**Flower fields** (for the Reach and other verdant areas):

| ID                     | Name                 |
| ---------------------- | -------------------- |
| `red_flower_fields`    | Red flower fields    |
| `blue_flower_fields`   | Blue flower fields   |
| `purple_flower_fields` | Purple flower fields |
| `yellow_flower_fields` | Yellow flower fields |

**Red Mountain terrains** (for Dorne's Red Mountains, stored in `redmountain/`
subfolder):

| ID                           | Path Prefix    | Description                   |
| ---------------------------- | -------------- | ----------------------------- |
| `red_coastline_cliff_desert` | `redmountain/` | Red-tinted desert cliffs      |
| `red_hills_01_rocks_medi`    | `redmountain/` | Red rocky hills               |
| `red_mountain_02_d_desert`   | `redmountain/` | Red mountain desert variant D |
| `red_mountain_02_desert_c`   | `redmountain/` | Red mountain desert variant C |
| `red_mountain_02_desert`     | `redmountain/` | Red mountain desert base      |

**Red sand terrains** (for the Red Waste, stored in `redsand/` subfolder):

| ID                          | Path Prefix | Description               |
| --------------------------- | ----------- | ------------------------- |
| `desert_red_flat_01`        | `redsand/`  | Flat red desert           |
| `desert_red_wavy_01`        | `redsand/`  | Wavy red sand dunes       |
| `desert_red_wavy_larger_01` | `redsand/`  | Large wavy red sand dunes |

**ELIS terrain pack** -- AGOT includes hundreds of terrain textures from the
ELIS (Extended Landscape Improvement Set) pack, covering categories: `frozen_*`,
`grass_*`, `gravel_*`, `ground_*`, `rock_*`, `stone_*`, `rusty_*`, `clay_*`,
`crack_*`, `road_*`, `mjgrass_*`. These provide fine-grained terrain detail
across the entire map.

### Terrain Material Definition Format

Each terrain material in `materials.settings` follows this structure:

```
{
    name = "red mountain 02 desert"
    diffuse = "redmountain/red_mountain_02_desert_diffuse.dds"
    normal = "redmountain/red_mountain_02_desert_normal.dds"
    material = "redmountain/red_mountain_02_desert_properties.dds"
    mask = "redmountain/red_mountain_02_desert_mask.bmp"
    id = "red_mountain_02_desert"
}
```

- `diffuse` -- Color/albedo texture
- `normal` -- Normal map for surface detail
- `material` -- Properties/specular map (roughness, metallic, etc.)
- `mask` -- Black/white mask (`.bmp` or `.png`) controlling where this material
  appears on the map
- `id` -- Unique string identifier used internally

### Terrain Masks

Masks are stored in `gfx/map/terrain/masks/` for dynamic weather effects:

| Mask                      | Purpose                                                |
| ------------------------- | ------------------------------------------------------ |
| `drought_mask.png`        | Areas affected by drought (currently disabled in AGOT) |
| `drought_cracks_mask.png` | Cracked ground during drought (currently disabled)     |
| `flood_mask.png`          | Flood-affected areas (currently disabled)              |
| `summer_grass_mask.png`   | Summer green grass overlay (currently disabled)        |
| `winter_effect_mask.png`  | Winter snow overlay (currently disabled)               |

Note: AGOT has disabled the dynamic weather terrain effects (drought, flood,
summer grass, winter) by commenting them out in `materials.settings`. The mask
files exist but are not active.

### Terrain Settings Overrides

AGOT modifies base terrain rendering in `settings.terrain`:

```
detail_blend_range = 1          # Vanilla: 0.25 (smoother terrain blending)
detail_tile_factor = 450        # Vanilla: 337.5 (denser texture tiling)
normal_height_scale = 0.75      # Vanilla: 0.8 (slightly flatter normals)
normal_step_size = 1            # Vanilla: 1.6 (finer normal detail)
```

These changes make AGOT's larger map render with appropriate texture density and
smoother terrain transitions.

### Detail Data Settings

`gfx/map/terrain/detail_data.settings` controls the terrain detail system:

```json
{
  "materials_limit": 4,
  "material_intensity_bias": 0
}
```

`materials_limit = 4` means each map pixel can blend at most 4 terrain materials
simultaneously.

## Key Differences from Vanilla

| Aspect                      | Vanilla                                        | AGOT                                                                        |
| --------------------------- | ---------------------------------------------- | --------------------------------------------------------------------------- |
| Portrait subjects           | Humans only                                    | Humans + full 3D dragon models as portraits                                 |
| Court rooms                 | Culture-based (Western, Mediterranean, Indian) | Location-based (specific castles: Red Keep, Winterfell, etc.)               |
| Court room selection        | Culture group triggers                         | Capital county triggers with artifact condition variants                    |
| CoA colors                  | Standard heraldic colors                       | AGOT-named colors (`agot_red`, `agot_cream`, `agot_bone`, etc.)             |
| Building GFX sets           | ~6 culture groups                              | ~24 culture-specific sets (andal, first_man, ironborn, ghis, crannog, etc.) |
| Special buildings           | A few vanilla landmarks                        | ~47 unique location models (Harrenhal, The Wall, Braavos, etc.)             |
| Portrait modifier numbering | Not strictly ordered                           | Strict `00_`-`99_` prefix system for load order                             |
| Accessory variations        | Culture-based                                  | Region-based (Dornish, Northern, Reach, etc.) + faction colors              |
| Shaders                     | Vanilla defaults                               | Custom `gfx/FX/` overrides for terrain, court scene, portraits, camera      |
| Map animals                 | None with custom models                        | Dragon entity on map with idle animations                                   |
| Portrait cameras            | Standard human framing                         | Additional dragon cameras with large near/far range (50-10000)              |

## AGOT Pitfalls

- **Do NOT modify AGOT's `50_coa_designer_emblems.txt`** -- Use a
  higher-numbered file (e.g., `99_my_submod_emblems.txt`) so your additions load
  separately and do not conflict on update.
- **CoA color names differ** -- AGOT replaces vanilla color names. Use
  `agot_red` etc. in your CoA definitions, not vanilla `red`. Check
  `agot_coa_designer_palettes.txt` for available names.
- **Dragon portrait conflicts** -- The dragon trait portrait modifier strips all
  human accessories and replaces the portrait body. If you add new portrait
  accessories, ensure they do not conflict with `gene_no_portrait` and
  `gene_dragon` when the `dragon` trait is present.
- **Portrait modifier load order matters** -- AGOT uses strict numeric prefixes
  (`00_` through `99_`). If adding new portrait modifiers, choose a prefix that
  places your file at the correct priority level. Higher numbers override lower
  numbers.
- **Court scene culture triggers use capital_county** -- Unlike vanilla (which
  uses culture group), AGOT court selection is location-based. A submod adding a
  new unique court must add a new entry in `scene_cultures/` with the correct
  capital county trigger.
- **Court room variants with artifact conditions** -- Some courts (Highgarden,
  Dragonstone) have conditional variants based on equipped artifacts. Be aware
  of this if modifying court selection logic.
- **Building GFX set naming** -- AGOT uses `*_building_gfx` directory naming.
  New culture building sets must follow this convention and be referenced
  correctly in building type definitions.
- **Shader overrides are fragile** -- AGOT overrides multiple core FX files
  (`court_scene.shader`, `pdxmesh.fxh`, portrait shaders). Submods overriding
  the same shaders will conflict.
- **Dragon camera near/far range** -- Dragon cameras use
  `camera_near_far = { 50 10000 }` due to dragon scale. Standard portrait camera
  ranges will clip dragon models.
- **`portrait_attachment` shader for artifacts** -- AGOT artifact models use
  `portrait_attachment` shader (not `standard`). Using the wrong shader will
  cause rendering issues in the portrait/artifact display.
- **Map terrain overrides** -- AGOT adds custom terrain types (redmountain,
  redsand) with their own masks. Submods overriding terrain textures must
  account for these.
- **Accessory variation textures** -- AGOT stores palette textures in
  `gfx/portraits/accessory_variations/textures/`. New variation DDS files must
  be placed there, not in the root variation folder.
