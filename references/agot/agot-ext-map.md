# AGOT Extension: Map

> This guide extends
> [references/patterns/map-modding.md](../patterns/map-modding.md) with
> AGOT-specific changes.

## What AGOT Changes

AGOT is a total conversion mod that replaces the entire vanilla map with the
world of A Song of Ice and Fire. Every map file in `map_data/` is completely
replaced -- nothing from vanilla CK3's Europe/Asia map remains. Key differences:

- **8,232 provinces** (vs ~1,500 in vanilla) defined in `definition.csv`
- **Sea zones** in the range 6167-7258 and 8208-8231, with large portions marked
  as `impassable_seas` (the open ocean beyond the known world)
- **Impassable mountains** covering ranges 2224-2250, 6100-6166, and 7129-7150
  among others -- used for the Wall, mountain ranges, and map-edge barriers
- **Rivers** in ranges 6498-6598, 7129-7150, 7269-7279, and 8201-8207
- **Lakes** in range 6599-6618 plus provinces 7247-7248
- **3 custom dynamic terrain PNGs** in `map_data/`:
  `agot_dynamic_terrain_adjacency.png`, `agot_dynamic_terrain_proximity.png`,
  `agot_dynamic_terrain_regions.png` -- these are AGOT-specific and have no
  vanilla equivalent
- A completely custom `adjacencies.csv` with 287 entries (strait crossings,
  river crossings) connecting islands and landmasses across Westeros and Essos
- A minimal `climate.txt` -- only 8 provinces are assigned `mild_winter`; AGOT
  handles seasons through its own scripted systems rather than vanilla climate
  categories

## AGOT Map Structure (Westeros, Essos, etc.)

AGOT's world is divided into major landmasses, each reflected in both the
geographical region hierarchy and the title structure:

**Westeros** -- the primary continent, containing:

- Beyond the Wall (wildling lands)
- The Wall
- The North
- The Iron Islands
- The Riverlands
- The Vale
- The Westerlands
- The Crownlands (including Dragonstone)
- The Reach
- The Stormlands
- Dorne
- The Stepstones (island chain between Westeros and Essos)

**Essos** -- the eastern continent, containing:

- The Free Cities (Braavos, Pentos, Myr, Tyrosh, Lys, Qohor, and others)
- The Disputed Lands
- Andalos
- Valyria (ruins)
- The Rhoyne river region
- The Great Grass Sea (Dothraki lands)
- Qarth
- Yi Ti
- Hyrkoon
- Leng
- Moraq

**Other regions** (minimal or placeholder content):

- Sothoryos (largely `world_ruins`)
- Summer Islands (largely `world_ruins`)
- Jade Sea region (largely `world_ruins`)

## Province Layout

Province IDs are organized roughly by geographic area:

| ID Range  | Content                                                                                                         |
| --------- | --------------------------------------------------------------------------------------------------------------- |
| 1-6099    | Land provinces (Westeros, Essos, Beyond the Wall)                                                               |
| 6100-6166 | Impassable mountains                                                                                            |
| 6167-6497 | Navigable sea zones                                                                                             |
| 6498-6598 | River provinces                                                                                                 |
| 6599-6618 | Lakes                                                                                                           |
| 6619-7258 | Additional sea zones (most are `impassable_seas` -- open ocean)                                                 |
| 7267-7279 | Impassable mountains and rivers                                                                                 |
| 8201-8232 | Late additions: rivers, impassable terrain, sea zones, and individual provinces (e.g., `b_flea_bottom` at 8232) |

Counties often have many more baronies than vanilla. For example, `c_hardhome`
has 4 baronies (provinces 6070, 8222, 8223, 8224), and `c_storrolds_point` has 6
baronies. This density is common throughout the AGOT map.

## Default.map Structure

The file `map_data/default.map` is the master map configuration. AGOT's version
defines file references and all province category ranges:

**File references** (top of file):

```
definitions = "definition.csv"
provinces = "provinces.png"
rivers = "rivers.png"
topology = "heightmap.heightmap"
continent = "continent.txt"
adjacencies = "adjacencies.csv"
island_region = "island_region.txt"
seasons = "seasons.txt"
```

**Sea zones** -- navigable water provinces. AGOT uses multiple `RANGE` and
`LIST` declarations:

```
sea_zones = RANGE { 6167 6497 }
sea_zones = RANGE { 6621 7128 }
sea_zones = RANGE { 7151 7246 }
sea_zones = RANGE { 7249 7258 }
sea_zones = RANGE { 8208 8218 }
sea_zones = RANGE { 8227 8231 }
sea_zones = LIST { 2958 2959 2960 6619 }
```

Note: provinces 2958-2960 are land-range IDs repurposed as sea (likely inland
harbors or special water bodies). Province 6619 is in the lake range but
declared as sea.

**Impassable seas** -- sea zones that exist for rendering but block naval
movement. Most sea zones beyond the navigable coastal waters are also listed
here:

```
impassable_seas = RANGE { 6621 6780 }
impassable_seas = RANGE { 6786 6889 }
impassable_seas = RANGE { 6896 7128 }
impassable_seas = RANGE { 7151 7246 }
impassable_seas = RANGE { 7249 7258 }
impassable_seas = RANGE { 8208 8218 }
impassable_seas = RANGE { 8227 8231 }
impassable_seas = LIST { 2958 2959 2960 6619 }
```

This means sea zones 6167-6497 and 6781-6785 and 6890-6895 are the **navigable**
seas. Everything else is blocked. The overlap between `sea_zones` and
`impassable_seas` is intentional -- the provinces must appear in both lists.

**River provinces**:

```
river_provinces = RANGE { 6498 6598 }
river_provinces = RANGE { 7129 7150 }
river_provinces = RANGE { 7269 7279 }
river_provinces = RANGE { 8201 8207 }
```

**Lakes**:

```
lakes = RANGE { 6599 6618 }
lakes = LIST { 7247 7248 }
```

**Impassable mountains** -- land provinces that block all movement (the Wall,
mountain barriers, map edges):

```
impassable_mountains = RANGE { 2224 2250 }
impassable_mountains = RANGE { 6100 6166 }
impassable_mountains = RANGE { 7129 7139 }
impassable_mountains = RANGE { 7141 7150 }
impassable_mountains = RANGE { 7267 7279 }
impassable_mountains = LIST { 6620 8201 8202 8203 }
```

Note the overlap: ranges 7129-7150 appear as both `river_provinces` and
`impassable_mountains`. Province 7140 is excluded from impassable mountains (it
is a navigable river segment). Individual provinces 8201-8203 are listed as both
rivers and impassable mountains.

**Sub-mod impact**: When adding new provinces, you must add them to the correct
category in `default.map`. If you add a new sea zone, it needs to be in
`sea_zones`. If it should block travel, it also needs to be in
`impassable_seas`. Missing entries will cause crashes or broken pathfinding.

## Adjacencies System

AGOT's `map_data/adjacencies.csv` defines 287 connections between provinces that
are not physically adjacent on the map image. The CSV format is:

```
From;To;Type;Through;start_x;start_y;stop_x;stop_y;Comment
```

| Column      | Meaning                                                                                                           |
| ----------- | ----------------------------------------------------------------------------------------------------------------- |
| `From`      | Source province ID                                                                                                |
| `To`        | Destination province ID                                                                                           |
| `Type`      | Connection type: `sea` (strait crossing via water) or `river_large` (crossing over a river)                       |
| `Through`   | Province ID of the sea/river province the crossing passes through. For rivers, can include a suffix like `6597-1` |
| `start_x/y` | Visual start position of the crossing arrow on the map (`-1` = auto-calculated)                                   |
| `stop_x/y`  | Visual end position (`-1` = auto-calculated)                                                                      |
| `Comment`   | Human-readable label (e.g., location names and distances)                                                         |

The file ends with a terminator line: `-1;-1;;-1;-1;-1;-1;-1;`

**Types used in AGOT:**

- **`river_large`** -- River crossings. The first ~27 entries are all
  `river_large`, connecting provinces on opposite banks of major rivers (the
  Trident, the Mander, the Rhoyne, etc.). Example:

  ```
  1876;1887;river_large;6518;-1;-1;-1;-1;Fangfoss - Saltpans (5.39, legacy: no)
  ```

  This connects province 1876 (Fangfoss) to 1887 (Saltpans) across river
  province 6518. The comment often includes a distance value and whether it is a
  legacy crossing.

- **`sea`** -- Strait/water crossings. The remaining ~260 entries connect island
  provinces to mainlands or other islands across sea zones. Example:
  ```
  424;426;sea;6407;-1;-1;-1;-1;White Harbor - Seal Rock (5.0)
  ```
  This connects White Harbor (province 424) to Seal Rock (province 426) via sea
  zone 6407.

**Geographic distribution**: Adjacencies cover every part of the AGOT map --
from Beyond the Wall (Shadow Tower to Westwatch), through the Iron Islands
(dozens of inter-island crossings like Pyke to Neverharrow), to the Stepstones,
Lys, and far-eastern Essos. The Iron Islands alone account for dozens of entries
connecting each island's baronies.

## AGOT Terrain Types

AGOT extends vanilla's terrain system with a road-based tiering system and
entirely new terrain categories. Terrain types are defined across two files:

**`common/terrain_types/00_terrains.txt`** -- Contains 17 base terrain types
(mostly vanilla): `plains`, `sea`, `coastal_sea`, `farmlands`, `hills`,
`mountains`, `desert`, `desert_mountains`, `oasis`, `jungle`, `forest`, `taiga`,
`wetlands`, `steppe`, `floodplains`, `drylands`, `terraced_hills`

**`common/terrain_types/01_agot_terrains.txt`** -- Contains 60+ AGOT-specific
terrains, organized into three categories:

**Road variants of existing terrains** -- Every base terrain gets a `majorroad_`
and `minorroad_` prefix variant (e.g., `majorroad_plains`, `minorroad_plains`).
These represent provinces on major or minor road networks. The road tier
affects:

- `movement_speed` -- Major roads are fastest (2.00 for plains), minor roads are
  moderate (1.50), off-road base terrain is slowest
- `supply_limit_mult` -- Major roads have significantly higher supply
- `development_growth_factor` -- Major roads provide development bonuses
- `provision_cost` -- Road-connected provinces cost less provisions to traverse
- Combat effects remain similar to the base terrain

Road-variant terrains covered: `plains`, `farmlands`, `hills`, `mountains`,
`desert`, `desert_mountains`, `oasis`, `jungle`, `forest`, `taiga`, `wetlands`,
`steppe`, `floodplains`, `drylands`, `frozen_flats`, `glacier`, `canyon`,
`cloudforest`, `highlands`, `taiga_bog`, `urban`, `the_bog`, `hotsprings`,
`terraced_hills`

**New base terrains unique to AGOT** (no vanilla equivalent):

| Terrain        | Lore Use                                              | Movement | Combat Width | Key Traits                                                             |
| -------------- | ----------------------------------------------------- | -------- | ------------ | ---------------------------------------------------------------------- |
| `frozen_flats` | Lands of Always Winter, far North                     | 0.80     | 1.00         | Extreme provision cost, -0.60 supply, -0.50 dev growth                 |
| `glacier`      | Ice sheets beyond the Wall                            | 0.30     | 0.30         | Worst traversal in the game, +0.3 hard casualties, +0.4 retreat losses |
| `canyon`       | Red Mountains of Dorne, Bones of Essos                | 0.60     | 0.50         | +10 defender advantage, very restrictive                               |
| `cloudforest`  | Elevated forests of Essos (Sothoryos, Basilisk Isles) | 0.70     | 0.80         | +8 defender advantage, dense cover                                     |
| `highlands`    | Elevated open terrain (Vale, Westerlands uplands)     | 0.80     | 1.00         | -0.30 dev growth, moderate supply penalty                              |
| `taiga_bog`    | Swampy northern forests (the Neck, Crannogmen lands)  | 0.40     | 0.80         | +12 defender advantage, +0.5 retreat losses, extremely hostile         |
| `urban`        | Major cities (King's Landing, Oldtown, Braavos)       | 0.50     | 0.70         | +0.5 dev growth, high supply, +2 defender advantage                    |
| `the_bog`      | The deepest swamps (Neck interior)                    | 0.50     | 0.10         | -3.00 supply(!), +0.5 retreat losses, near-impassable combat width     |
| `hotsprings`   | Geothermally active areas                             | 1.00     | 1.00         | +0.10 dev growth, high fertility                                       |

Each of these also has `majorroad_` and `minorroad_` variants.

**Provision cost tiers** defined as script values:

```
@provisions_cost_minimal = 25
@provisions_cost_light = 50
@provisions_cost_medium = 80
@provisions_cost_high = 100
@provisions_cost_extreme = 150
```

## Roads System

AGOT implements a road network on its map through terrain types and visual map
objects. This system has no vanilla equivalent.

**How roads work mechanically**: Every land province is assigned one of three
terrain sub-types for its base terrain:

- **Base terrain** (e.g., `plains`) -- Off-road, no road infrastructure
- **Minor road** (e.g., `minorroad_plains`) -- Province is on a minor road
- **Major road** (e.g., `majorroad_plains`) -- Province is on a major road (the
  Kingsroad, the Roseroad, Valyrian roads, etc.)

The road tier is baked into the province's terrain assignment in
`history/provinces/` files. It is not dynamically calculated -- each province
permanently has a specific road-tier terrain.

**Scripted triggers** in
`common/scripted_triggers/00_agot_terrain_type_triggers.txt` provide helper
checks:

- `agot_is_majorroad_terrain` -- returns true if the province has any
  `majorroad_*` terrain
- `agot_is_minorroad_terrain` -- returns true if the province has any
  `minorroad_*` terrain
- `agot_is_urban_terrain` -- returns true for `urban`, `majorroad_urban`, or
  `minorroad_urban`

**Custom map mode for roads**: AGOT provides a roads map mode using dummy titles
in `common/landed_titles/04_agot_mapmodes_titles.txt`:

```
d_agot_roads_map_void = { color = { 40 40 40 } }     # Off-road provinces (dark)
d_agot_roads_map_major = { color = { 215 180 15 } }   # Major roads (gold)
d_agot_roads_map_minor = { color = { 215 220 120 } }  # Minor roads (light yellow)
d_agot_roads_map_urban = { color = { 195 15 15 } }    # Urban centers (red)
```

The map mode is activated via `agot_map_mode_setup_effect` in
`common/scripted_effects/00_agot_map_effects.txt`, which iterates over all
baronies and colors them using `set_color_from_title` based on their road tier.

**Visual road objects**: Road bridges and crossings are placed as 3D map objects
on the `AGOT_roads` and `AGOT_low_roads` layers (defined in
`gfx/map/map_object_data/game_object_layers.txt`). These include:

- `Bridge_European` (`bridge_western_mesh`) -- 38 instances across Westeros
- `Bridge_Wood` (`bridge_01_mesh`) -- 17 wooden bridges in northern/rural areas
- `Bridge_India` (`bridge_indian_mesh`) -- 7 bridges in Essos regions

These are purely visual -- the actual movement bonuses come from the terrain
type assignments.

## Dynamic Terrain PNGs

AGOT uses three custom PNG textures in `map_data/` that feed into a shader-based
dynamic terrain system. This system has no vanilla equivalent and is implemented
through custom HLSL shaders.

**The three textures:**

| File                                 | Shader Sampler                             | Filter | Purpose                                                                |
| ------------------------------------ | ------------------------------------------ | ------ | ---------------------------------------------------------------------- |
| `agot_dynamic_terrain_regions.png`   | `GH_DynamicTerrainRegionsMap` (index 31)   | Point  | Divides the map into discrete terrain regions using color-coded pixels |
| `agot_dynamic_terrain_adjacency.png` | `GH_DynamicTerrainAdjacencyMap` (index 32) | Point  | Encodes adjacency relationships between terrain regions                |
| `agot_dynamic_terrain_proximity.png` | `GH_DynamicTerrainProximityMap` (index 33) | Linear | Stores proximity/distance data with smooth interpolation               |

**How it works**: The shader code in `gfx/FX/gh_dynamic_terrain_textures.fxh`
loads these textures and uses them to select between terrain detail textures at
render time. The system supports multiple "terrain variants" -- indexed sets of
alternative detail textures. Currently AGOT defines one non-default variant:

- **Variant 3 (Arctic)**: Uses `gfx/map/terrain/agot_detail_index_arctic.png`
  and `gfx/map/terrain/agot_detail_intensity_arctic.png` to render arctic/frozen
  terrain differently from standard terrain.

The shader file is auto-generated from a Jinja template (`render_templates.py`)
-- the source template lives in `~DevFolders/DynamicTerrain/templates/`. Sub-mod
authors should not edit `gh_dynamic_terrain_textures.fxh` directly.

**Sub-mod impact**: If you change the map shape (adding new landmasses,
extending coastlines), the dynamic terrain PNGs will need to be regenerated or
manually edited to cover the new areas. Mismatched PNGs will cause visual
terrain glitches (wrong ground textures, missing snow, etc.).

## Map Objects and Locators

AGOT places hundreds of custom 3D objects on the map through files in
`gfx/map/map_object_data/`. Each file contains `object={ }` blocks with position
data.

**Object block format:**

```
object={
    name="Weirwood1"                         # Display name (for editor)
    render_pass=Map                          # Map or MapUnderWater
    clamp_to_water_level=no                  # Whether to snap to water surface
    generated_content=no                     # no = manually placed
    layer="tree_high_layer"                  # Visibility layer (controls fade distance)
    pdxmesh="mapitem_trees_weirwood_01_mesh" # 3D mesh reference (or entity= for animated)
    count=50                                 # Number of instances
    transform="X Y Z qX qY qZ qW sX sY sZ  # Per-instance: position, quaternion rotation, scale
    ..."
}
```

The `transform` string contains 10 floats per instance: 3 position (X, Y, Z), 4
quaternion rotation (qX, qY, qZ, qW), 3 scale (sX, sY, sZ).

**AGOT-specific layers** defined in
`gfx/map/map_object_data/game_object_layers.txt`:

| Layer                 | Fade Distance | Content                                                            |
| --------------------- | ------------- | ------------------------------------------------------------------ |
| `AGOT_animal_layer`   | 0-9           | Wildlife (whales, etc.)                                            |
| `AGOT_building_layer` | 0-16          | Lore buildings (Pyke Bridge, Braavos, weirwoods, barrow entrances) |
| `AGOT_roads`          | 0-16          | Road bridges and crossings                                         |
| `AGOT_low_roads`      | 0-16          | Lower-priority road objects                                        |

**Notable AGOT map objects across files:**

- **`agot_building_layer.txt`** -- Bridge of Skulls
  (`building_special_bridge_of_skulls`), Pyke Bridge
  (`building_special_PykeBridge_mesh`), Weirwood trees (50 hand-placed weirwoods
  across Westeros), Highgarden docks, barrow entrances (33 instances in the
  North)
- **`agot_misc_entities.txt`** -- Coast splash effects (27 locations), sea fog,
  whale animations (64 whales in oceans)
- **`agot_animals.txt`** -- Large file with animal entity placements
- **`new_mapobject_1.txt`** -- Braavos city model, European-style bridges (38
  instances on `AGOT_roads` layer)
- **`new_mapobject_2.txt`** -- Gulltown buildings (Arryn manor, houses), barrow
  entrances
- **`new_mapobject_3.txt`** -- Indian-style bridges (7 in Essos on `AGOT_roads`
  layer), Gulltown houses
- **`special.txt`** -- The Wall segments (Hadrian's wall meshes repurposed),
  using `hadrians_wall_01_d_mesh` with 183 instances forming the Wall structure
- **`bridges.txt`** -- Wooden bridges (17 on `AGOT_roads` layer)
- **Map table styles** -- Multiple bookmark-specific map tables:
  `agot_map_crowned_stag.txt`, `agot_map_rogue_prince.txt`, `agot_map_rr.txt`,
  `agot_map_penny_kings.txt`, `agot_map_golden_age.txt`

## Positions.txt

AGOT's `map_data/positions.txt` defines the visual positions of city markers,
unit positions, combat positions, and text labels for each province on the map.
The file is extremely large (entries for all 8,232 provinces) and is in a
binary/packed format -- it contains minimal readable text content (effectively a
single-line file).

Province positions are typically generated using the CK3 map editor tools rather
than edited by hand. Each province entry encodes:

- City/settlement icon position
- Unit stack position
- Combat position
- Name text position and rotation

**Sub-mod authors**: When adding new provinces, you must generate new position
entries. The easiest approach is to use the CK3 Nudge tool (launched via
`-nudge` command-line argument) to visually place markers and export the updated
file.

## Geographical Regions

AGOT defines 99 geographical regions in
`map_data/geographical_regions/00_agot_geographical_region.txt` (3,758 lines).
The hierarchy follows the lore:

```
world_westeros
├── world_westeros_beyond_the_wall
│   ├── world_westeros_beyond_the_wall_thenn
│   ├── world_westeros_beyond_the_wall_the_frostfangs
│   ├── world_westeros_beyond_the_wall_the_frozen_shore
│   ├── world_westeros_beyond_the_wall_the_ice_lakes
│   └── world_westeros_beyond_the_wall_first_forest
├── world_westeros_the_wall
├── world_westeros_the_north
├── world_westeros_the_iron_islands
├── world_westeros_the_riverlands
├── world_westeros_the_vale
├── world_westeros_the_westerlands
├── world_westeros_the_crownlands
├── world_westeros_the_reach
├── world_westeros_the_stormlands
└── world_westeros_dorne

world_essos
├── world_essos_free_cities
│   ├── world_essos_braavos
│   ├── world_essos_pentos
│   ├── world_essos_myr
│   ├── world_essos_tyrosh
│   ├── world_essos_lys
│   └── world_essos_andalos
├── world_essos_disputed_lands
├── world_essos_valyria
├── world_essos_rhoyne
├── world_essos_great_grass_sea
├── world_essos_qarth
├── world_essos_qohor
├── world_essos_yi_ti
├── world_essos_hyrkoon
├── world_essos_leng
└── world_essos_moraq

world_stepstones
world_sothoryos
world_summer_islands
world_jade_sea
```

**Convenience regions used by AGOT scripts:**

- `world_westeros_seven_kingdoms` -- Westeros minus Beyond the Wall
- `world_westeros_seven_kingdoms_without_dorne` -- Seven Kingdoms minus Dorne
- `world_westeros_seven_kingdoms_without_wall` -- Seven Kingdoms minus the Wall
- `world_westeros_wilding_raiding_zone` -- area where wildling camps can move
- `world_westeros_the_kingswood` -- specific forest region
- `world_westeros_dornish_marches` -- border zone split into
  Stormlands/Reach/Dorne sub-regions
- `world_innovation_elephants` -- maps to `world_essos` (controls elephant
  innovation spread)
- `world_innovation_camels` -- has `generate_modifiers = yes`
- `world_lands_less_traveled` -- used for epidemic containment

A second file, `map_data/geographical_regions/10_natural_disaster_regions.txt`,
defines `global_flood_region` for AGOT's natural disaster system.

**Sub-mod authors**: If you add new provinces, you must add them to the
appropriate AGOT geographical region. Use `regions = { }` to reference existing
AGOT regions, or add duchies/counties/provinces directly. Remember: sub-regions
must be declared before parent regions that reference them.

## Title Structure

AGOT's title files in `common/landed_titles/` are split across multiple files:

| File                                         | Purpose                                                                                            |
| -------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| `01_agot_landed_titles.txt`                  | Main de-jure hierarchy (empires, kingdoms, duchies, counties, baronies)                            |
| `02_agot_special_titles.txt`                 | Special scripted titles with `can_create` restrictions                                             |
| `03_agot_landed_titles_westeros_titular.txt` | Titular titles for Westeros (e.g., `e_blackfyre_rebellion`, `e_targaryen_host_title`)              |
| `03_agot_landed_titles_essos_titular.txt`    | Titular titles for Essos (e.g., `k_golden_company`)                                                |
| `04_agot_mapmodes_titles.txt`                | Dummy titles for custom map mode colors (e.g., `d_agot_roads_map_void`, `d_agot_roads_map_major`)  |
| `05_agot_laamps.txt`                         | "LAAMP" titles (Landless Adventurer And Minor Power) -- landless duchy-tier titles for minor lords |
| `05_agot_laamps_merc.txt`                    | LAAMP titles for mercenary companies                                                               |
| `06_agot_powerful_family_titles.txt`         | Titles for powerful noble families (e.g., Targaryen exiles)                                        |
| `07_agot_hegemony_titles.txt`                | Hegemony-tier titles (e.g., `h_the_iron_throne`)                                                   |

**Empire-tier titles in the main hierarchy:**

- `e_the_north`, `e_the_vale`, `e_the_iron_islands`, `e_the_crownlands`,
  `e_the_reach`, `e_the_stormlands`, `e_the_westerlands`, `e_the_riverlands`,
  `e_dorne`, `e_the_wall`
- `e_three_daughters`, `e_pentos`, `e_braavos` (Essos)
- `e_ruins`, `e_unknown`, `e_wilderness` (special/placeholder)

Note that each major Westerosi region is its own empire, unlike vanilla CK3
where empires are much larger. This is an intentional design choice to model the
Seven Kingdoms' political structure.

The title hierarchy nests deeply: empire > kingdom > duchy > county > barony,
with each barony having a `province = XXXX` mapping to a province ID in
`definition.csv`.

## Island Regions

AGOT defines extensive island regions in `map_data/island_region.txt` for AI
pathfinding. Notable island regions include:

- `island_region_skagos` -- Skagos island (4 counties)
- `island_region_the_sisters` -- The Three Sisters (duchy `d_the_sisters`)
- `island_region_bear_island` -- Bear Island
- Iron Islands: split into separate regions per island (`island_region_wyk`,
  `island_region_harlaw`, `island_region_orkmont`, `island_region_saltcliffe`,
  `island_region_pyke`, `island_region_blacktyde`, `island_region_lonely_light`)
- `island_region_dragonstone` -- Dragonstone, High Tide, and Driftmark
- `island_region_tarth` -- Tarth
- `island_region_the_arbor` -- The Arbor (5 counties + extra province)
- `island_region_estermont_isles` -- Estermont and surrounding islands

Each uses either `duchies = { }`, `counties = { }`, or `provinces = { }` to
define membership. Sub-mod islands MUST be added here or the AI will attempt
land pathfinding across water.

## Sub-Mod Map Recipes

### Adding a New Island or Landmass

1. Add provinces to `definition.csv` with unique RGB values (continue from the
   last used ID, currently 8232)
2. Paint the new land in `provinces.png` using exact RGB colors
3. Update `default.map` -- add sea zones to `sea_zones` (and `impassable_seas`
   if deep ocean), add any rivers or lakes
4. Add entries to `positions.txt` for all new land provinces
5. Create `adjacencies.csv` entries for any strait crossings to the new land
6. Define the title hierarchy in a new file (e.g.,
   `08_yourmod_landed_titles.txt`) or extend `01_agot_landed_titles.txt`
7. Add an `island_region_yourland` entry to `island_region.txt`
8. Add a new geographical region (e.g., `world_essos_yourland`) in a new file
   like `05_yourmod_geographical_region.txt` -- file load order is alphabetical,
   so prefix accordingly
9. Create province history files in `history/provinces/`

### Adding Provinces to an Existing AGOT Kingdom

1. Follow standard province-adding steps (definition.csv, provinces.png,
   positions.txt, etc.)
2. Add the new baronies to an existing county in `01_agot_landed_titles.txt`, or
   create new counties/duchies under an existing kingdom
3. Add to the correct AGOT geographical region -- use the sub-region level
   (e.g., `world_westeros_the_north_mainland` not `world_westeros`)
4. Create province history with appropriate AGOT cultures and religions

### Extending the Map Edge

AGOT's impassable mountains (ranges 2224-2250, 6100-6166, etc.) and impassable
seas define the playable world boundaries. To expand:

1. Replace the impassable provinces at the edge with new land provinces
2. Create new impassable provinces further out as the new boundary
3. Update `default.map` ranges to reflect the changes
4. Update the heightmap to show terrain for the newly opened area

### Adding a Strait Crossing

To connect two land provinces across water (e.g., adding a ferry between an
island and the mainland):

1. Identify the two land province IDs you want to connect and the sea zone
   province between them
2. Add a line to `map_data/adjacencies.csv` before the terminator line
   (`-1;-1;;-1;...`):
   ```
   FROM_ID;TO_ID;sea;SEA_ZONE_ID;-1;-1;-1;-1;Your Comment
   ```
   Example -- connecting a new island (province 8300) to the Stormlands coast
   (province 2650) via sea zone 6384:
   ```
   2650;8300;sea;6384;-1;-1;-1;-1;Stormlands Coast - New Island (3.0)
   ```
3. Using `-1` for start/stop coordinates lets the engine auto-calculate the
   crossing arrow position. To manually place the arrow, replace the `-1` values
   with pixel coordinates on the map
4. For river crossings (connecting provinces on opposite sides of a river), use
   `river_large` instead of `sea`:
   ```
   FROM_ID;TO_ID;river_large;RIVER_PROV_ID;-1;-1;-1;-1;Your Comment
   ```
5. The sea zone or river province referenced in the `Through` column must exist
   in `default.map`'s `sea_zones` or `river_provinces` respectively

### Adding Custom Terrain to a Province

To assign one of AGOT's custom terrain types (e.g., `urban`, `the_bog`,
`glacier`) to a province:

1. Set the terrain in the province's history file in `history/provinces/`.
   Example for an urban province:

   ```
   # history/provinces/8300.txt
   terrain = urban
   ```

   For a road-connected province, use the road-tier variant:

   ```
   terrain = majorroad_plains
   ```

2. The terrain key must match one defined in
   `common/terrain_types/00_terrains.txt` or `01_agot_terrains.txt`.
   AGOT-specific options include:
   - `frozen_flats`, `glacier` -- extreme cold terrain
   - `canyon`, `cloudforest`, `highlands` -- mountainous variants
   - `taiga_bog`, `the_bog` -- swamp terrain
   - `urban` -- cities
   - `hotsprings` -- geothermal areas
   - Any of these with `majorroad_` or `minorroad_` prefix for road connectivity

3. Each custom terrain needs icon and illustration DDS files in
   `gfx/interface/icons/terrain_types/` and
   `gfx/interface/illustrations/terrain_types/`. AGOT already provides these for
   all its terrains. If creating a wholly new terrain type, you must supply
   these textures.

### Placing Map Objects

To add 3D objects to the map (buildings, landmarks, decorative items):

1. Create or edit a file in `gfx/map/map_object_data/`. Use a new file (e.g.,
   `yourmod_objects.txt`) to avoid conflicts with AGOT files.

2. Add an object block. Example placing a single weirwood tree:

   ```
   object={
       name="My Weirwood"
       render_pass=Map
       clamp_to_water_level=no
       generated_content=no
       layer="AGOT_building_layer"
       pdxmesh="mapitem_trees_weirwood_01_mesh"
       count=1
       transform="1500.0 0.0 3000.0 0.0 0.0 0.0 1.0 1.0 1.0 1.0
   "}
   ```

   The transform values are:
   `posX posY posZ quatX quatY quatZ quatW scaleX scaleY scaleZ`
   - Position: X is east-west, Y is height, Z is north-south (in map pixels)
   - Rotation: quaternion (0 0 0 1 = no rotation)
   - Scale: uniform 1.0 = normal size

3. Choose the appropriate layer:
   - `AGOT_building_layer` -- for buildings and landmarks (fade at distance 16)
   - `AGOT_roads` -- for road-related objects like bridges (fade at distance 16)
   - `AGOT_animal_layer` -- for animated wildlife (fade at distance 9)
   - `tree_high_layer` -- for trees and foliage (fade at distance 16)

4. Use either `pdxmesh` (static mesh) or `entity` (animated entity) to reference
   the 3D model. Available AGOT meshes can be found by searching `.mesh` and
   `.asset` files in `gfx/models/`.

5. To find map coordinates for placement, use the CK3 console command
   `mapmode terrain` and hover over the target area to read coordinates, or
   examine nearby objects in existing map_object_data files.

## Key Differences from Vanilla

| Aspect               | Vanilla CK3                               | AGOT                                                                                            |
| -------------------- | ----------------------------------------- | ----------------------------------------------------------------------------------------------- |
| Total provinces      | ~1,500                                    | 8,232                                                                                           |
| Map scope            | Europe, Middle East, parts of Asia/Africa | Westeros, Essos, Stepstones                                                                     |
| Empire scale         | Large multi-kingdom empires               | Each Westerosi region is empire-tier                                                            |
| Climate system       | Vanilla `climate.txt` with 3 tiers        | Minimal `climate.txt` (8 provinces); seasons handled by scripted systems                        |
| Sea zones            | Ranges ~632-1050                          | Ranges 6167-7258, 8208-8231; heavy use of `impassable_seas`                                     |
| Dynamic terrain      | Not present                               | 3 custom PNGs + shader system for terrain variant rendering                                     |
| Terrain types        | 17 base terrains                          | 17 base + 60 AGOT terrains (road variants, urban, glacier, canyon, bog, etc.)                   |
| Road system          | Not present                               | Major/minor road terrain variants + visual bridge objects + roads map mode                      |
| Title files          | Single `00_landed_titles.txt`             | 9 separate files for different title categories (main, special, titular, LAAMP, hegemony, etc.) |
| Geographical regions | `world_europe_*`, `world_africa_*`, etc.  | `world_westeros_*`, `world_essos_*`, `world_stepstones`, etc.                                   |
| Barony density       | Typically 3-5 per county                  | Often 4-7 per county                                                                            |
| Island regions       | British Isles, Mediterranean islands      | Dozens of lore islands (Iron Islands split per-island, Dragonstone group, Arbor, Skagos, etc.)  |
| Map objects          | Standard buildings, trees                 | Weirwoods, The Wall (183 segments), Pyke Bridge, city models, whales, custom bridges            |
| Adjacencies          | ~50 entries                               | 287 entries (river crossings + strait crossings across all regions)                             |

## AGOT Pitfalls

- **Province ID collisions**: AGOT uses IDs up to 8232. If your sub-mod adds
  provinces starting at, say, 5000, you will collide. Always start after AGOT's
  highest ID
- **Impassable seas vs. sea zones**: AGOT lists many sea zones as BOTH
  `sea_zones` AND `impassable_seas`. This is intentional -- they exist for map
  rendering but block naval movement. Do not remove provinces from
  `impassable_seas` thinking it will "fix" navigation; it will break the map
  boundary
- **The Wall provinces**: The Wall itself uses impassable mountain provinces
  (range overlap with 7129-7150). These are critical for the Wall's gameplay
  mechanics. Do not reclassify them
- **LAAMP and special titles**: Files `05_agot_laamps.txt` and
  `06_agot_powerful_family_titles.txt` define landless titles that interact with
  AGOT's custom systems. Do not add `province =` entries to these titles
- **Dynamic terrain PNGs**: The three `agot_dynamic_terrain_*.png` files in
  `map_data/` are used by AGOT's custom terrain system. If you modify the map
  shape, you may need to update these images as well, or terrain visuals will
  not match your changes. The shader file
  `gfx/FX/gh_dynamic_terrain_textures.fxh` is auto-generated -- do not edit it
  directly
- **Road terrain assignments are permanent**: A province's road tier
  (`majorroad_*`, `minorroad_*`, or base) is set in its history file. There is
  no event or script that dynamically changes road connectivity. To add a road
  to a province, you must change its terrain type in its history file
- **Geographical region file ordering**: AGOT's main region file is
  `00_agot_geographical_region.txt`. If your sub-mod adds a new file, its prefix
  number determines load order. Sub-regions referenced by AGOT's parent regions
  must exist when the parent is parsed -- place new standalone regions in a file
  that loads after `00_`
- **Title file load order**: AGOT's title files are numbered `01_` through
  `07_`. A sub-mod title file prefixed `00_` would load before the AGOT
  hierarchy, causing undefined parent references. Use `08_` or higher
- **Climate is mostly unused**: Do not expect vanilla-style winter mechanics.
  AGOT's `climate.txt` assigns only 8 provinces to `mild_winter` and nothing to
  `normal_winter` or `severe_winter`. AGOT handles seasons through events and
  scripted effects, not the vanilla climate system
- **Hegemony titles**: The `h_` prefix (e.g., `h_the_iron_throne`) is an
  AGOT-specific title tier for supreme rulers. Do not confuse this with vanilla
  title tiers
- **Map mode dummy titles**: `04_agot_mapmodes_titles.txt` contains titles like
  `d_agot_roads_map_void` that exist purely for map mode coloring. They have
  `can_create = { always = no }` and should never be granted or referenced in
  gameplay scripts
- **Adjacency terminator line**: The last line of `adjacencies.csv` must always
  be `-1;-1;;-1;-1;-1;-1;-1;`. New entries must be added before this line, not
  after it
- **Map object transform precision**: When placing map objects, the transform
  coordinates must be precise float values matching the map's coordinate system.
  The Y coordinate (height) should generally be 0.0 for flat ground -- using
  incorrect heights will cause objects to float or sink into terrain
