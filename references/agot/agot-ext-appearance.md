# AGOT Extension: Ethnicities & DNA

## Overview

AGOT completely replaces CK3's ethnicity and DNA systems to populate Planetos
with lore-accurate character appearances. Instead of vanilla's real-world ethnic
groups (Mediterranean, Slavic, etc.), AGOT defines custom ethnicities for
Westerosi regions (Andal, First Men, Dornish variants), Essosi city-states
(Lyseni, Myrish, Tyroshi, etc.), exotic peoples (Summer Islanders, Ibbenese,
Brindled Men), Valyrians (High Valyrian, Westerosi Valyrian), and even dragons.

The system works in three layers:

1. **Base templates** -- reusable ethnicity blocks that define shared gene
   distributions (e.g., `ethnicity_template`, `caucasian_base`)
2. **Ethnicity definitions** -- named ethnicity blocks that set hair/eye/skin
   color palettes and gene ranges, optionally inheriting from a template
3. **Ethnicity presets** -- numbered individual face presets (e.g., `Andal_1`
   through `Andal_21`) that cultures reference by weighted random selection

Cultures map to these presets in their `ethnicities = { }` block. When the game
generates a character's appearance, it picks a preset based on the weights, then
applies gene distributions from that preset and its template chain.

## What AGOT Changes

AGOT replaces or extends the following vanilla directories:

| Directory                  | What AGOT does                                                                                                                             |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| `common/ethnicities/`      | Adds ~600+ files: base templates, ethnicity definitions, and numbered face presets for every Planetos culture group                        |
| `common/dna_data/`         | Adds ~40 region-based DNA files (`agot_dna_north.txt`, `agot_dna_dragonstone.txt`, etc.) with hand-crafted faces for historical characters |
| `common/genes/`            | Adds AGOT-specific genes: jewelry accessories, dragon morph genes, EPE color/morph genes, salt-and-pepper hair                             |
| `common/scripted_effects/` | Adds `00_agot_appearance_effects.txt` and `00_agot_dragon_appearance_effects.txt` for scripted hair/appearance management                  |

Key files added by AGOT in `common/ethnicities/`:

- `00_ethnicities_templates.txt` -- Modified vanilla base template
  (`ethnicity_template`)
- `00_ethnicities_templates_2.txt` -- Second base template variant
  (`ethnicity_template_2`)
- `00_epe_ethnicities_templates_base.txt` -- EPE (Enhanced Portrait Essosi) base
  template
- `00_epe_base_template_essosi_*.txt` -- EPE templates for Essosi sub-groups
  (Andalosi, Lyseni, Myrish, Norvoshi, Pentoshi, Tyroshi, Valyrian)
- `00_agot_base_template_*.txt` -- AGOT-specific base templates (Free Folk, Sand
  Dornish, Summer Islander sub-groups, Ibbenese, Brindled Men)
- `02_agot_ethnicities_andal.txt` -- Andal-family ethnicity definitions (andal,
  reachman, riverman, stormlander, valeman, westerman)
- `02_agot_ethnicities_first_man.txt` -- First Men ethnicity definitions
  (first_man, crannogman)
- `02_agot_ethnicities_valyrian.txt` -- Valyrian family (essosi_valyrian,
  valyrian, high_valyrian, lyseni, volantene)
- `03_agot_dragon.txt` -- Dragon ethnicity with custom color and morph genes
- `andal_1.txt` through `andal_21.txt` -- Numbered Andal face presets
- `agot_essosi_high_valyrian_01.txt` through `_22.txt` -- High Valyrian face
  presets
- Many more regional presets: `northman_*.txt`, `reachmen_*.txt`,
  `salt_dornish_*.txt`, `westerosi_valyrian_*.txt`, etc.

## AGOT Ethnicity Groups

AGOT organizes ethnicities into the following major groups. Each group has a
base ethnicity definition and numbered face presets.

### Westerosi (Andal-descended)

Defined in `02_agot_ethnicities_andal.txt`. All use
`template = "ethnicity_template"`. These share the same color palettes
(brown/hazel/green/blue/grey eyes, blonde-to-black hair) but have
region-specific face presets:

- **andal_ethnicity** -- Generic Andal base. Used by `Andal_*` presets.
- **reachman_ethnicity** -- Reachmen
- **riverman_ethnicity** -- Riverlanders
- **stormlander_ethnicity** -- Stormlanders
- **valeman_ethnicity** -- Valemen
- **westerman_ethnicity** -- Westermen

Each regional ethnicity has 21 numbered presets (e.g., `crownlander_1` through
`crownlander_21`). These presets use the `using` keyword to inherit from the
ethnicity definition and then override individual genes for facial structure.

### Westerosi (First Men)

Defined in `02_agot_ethnicities_first_man.txt`. Use
`template = "caucasian_base"`:

- **first_man_ethnicity** -- Northmen, with restricted hair colors (no light
  blonde) and brown/hazel/grey eyes only. Taller height distribution.
- **crannogman_ethnicity** -- Crannogmen, notably shorter height distribution
  (`range = { 0.35 0.4 }` to `{ 0.45 0.5 }`).

### Valyrian

Defined in `02_agot_ethnicities_valyrian.txt`:

- **essosi_valyrian_ethnicity** -- Base template (`template = "caucasian_base"`)
  with refined eyebrow shapes and sparse body hair.
- **valyrian_ethnicity** -- No template (standalone). Silver/gold hair, pale
  skin, purple/indigo eye colors across the full AGOT custom palette. Includes
  detailed face morph genes, height distribution, body shape, bust, and head
  asymmetry.
- **high_valyrian_ethnicity** -- `template = "valyrian_ethnicity"`. Adds
  extremely detailed facial feature ranges for every gene (chin, jaw, nose,
  eyes, forehead, mouth, ears, etc.) to create the "high Valyrian look."
- **lyseni_ethnicity** -- `template = "caucasian_base"`. Mix of
  green/blue/purple eyes, silver/gold hair.
- **volantene_ethnicity** -- No template. Diverse skin tones (pale to dark),
  mixed eye/hair colors reflecting Volantis's mixed ancestry.

### Essosi City-States (EPE System)

AGOT uses the Enhanced Portrait Essosi (EPE) system for Free Cities. Each city
has:

- A base template in `00_epe_base_template_essosi_*.txt`
- 50 numbered face presets (e.g., `agot_essosi_lyseni_01.txt` through `_50.txt`)

Cities covered: Andalosi, Lyseni, Myrish, Norvoshi, Pentoshi, Tyroshi.

### Free Folk

Base template in `00_agot_base_template_free_folk.txt` with sub-groups:

- Fangmen (30 presets)
- Forestmen (21 presets)
- Lakefolk (30 presets)
- Thenn (30 presets)

Uses the `using = "thenn"` keyword to inherit from a named morph block.

### Dornish

Three separate ethnicity groups reflecting Dornish diversity:

- **Sand Dornish** (14 presets) -- Rhoynish descent, base template in
  `00_agot_base_template_sand_dornish.txt`
- **Salt Dornish** (15 presets) -- Mixed descent
- **Stone Dornish** (15 presets) -- Andal/First Men descent

### Exotic Peoples

- **Summer Islanders** -- Five sub-groups with dedicated base templates: Jhalani
  (50 presets), Moluuni (40 presets), Naathi (30 presets), Omboruni (30
  presets), Walani (30 presets)
- **Ibbenese** -- `00_agot_base_template_essosi_ibbenese.txt` with 1 preset
- **Brindled Men of Sothoryos** --
  `00_agot_base_template_sothoryi_brindled_men.txt` with 10 presets

### Dragons

Defined in `03_agot_dragon.txt`. A completely custom ethnicity with
dragon-specific genes for color, morphology, and aging. See the Gene
Modifications section.

## DNA Data System

AGOT's `common/dna_data/` directory contains hand-crafted DNA for historical and
notable characters, organized by region:

```
agot_dna_north.txt              agot_dna_north_ancestors.txt
agot_dna_crownlands.txt         agot_dna_crownlands_ancestors.txt
agot_dna_dragonstone.txt        agot_dna_dragonstone_ancestors.txt
agot_dna_dorne.txt              agot_dna_dorne_ancestors.txt
agot_dna_reach.txt              agot_dna_reach_ancestors.txt
agot_dna_riverlands.txt         agot_dna_riverlands_ancestors.txt
agot_dna_riverlands_freys.txt
agot_dna_stormlands.txt         agot_dna_stormlands_ancestors.txt
agot_dna_vale.txt               agot_dna_vale_ancestors.txt
agot_dna_westerlands.txt        agot_dna_westerlands_ancestors.txt
agot_dna_iron_islands.txt       agot_dna_iron_islands_ancestors.txt
agot_dna_braavos.txt            agot_dna_braavos_ancestors.txt
agot_dna_pentos.txt             agot_dna_pentos_ancestors.txt
agot_dna_three_daughters.txt    agot_dna_three_daughters_ancestors.txt
agot_dna_btw.txt                agot_dna_btw_ancestors.txt
agot_dna_btw_craster.txt        agot_dna_btw_thenn.txt
agot_dna_stepstones.txt
agot_dna_nightswatch.txt        agot_dna_mercenaries.txt
agot_dna_contest.txt            agot_dna_contest_ancestors.txt
agot_dna_valyria_ancestors.txt
agot_dna_vanity.txt             agot_dna_vanity_ancestors.txt
agot_dna_a_historical_heroes.txt
agot_dna_andalos_ancestors.txt
```

### DNA Data Format

Each entry is a named DNA block with a `portrait_info` containing `genes`. Gene
values use integer format (0-255) rather than the float ranges used in ethnicity
files:

```pdx
Brightflame_1 = {
    portrait_info = {
        genes = {
            hair_color = { 16 43 16 43 }
            skin_color = { 107 42 107 42 }
            eye_color = { 236 66 236 66 }
            gene_chin_forward = { "chin_forward_pos" 157 "chin_forward_pos" 157 }
            gene_chin_height = { "chin_height_pos" 133 "chin_height_pos" 133 }
            # ... every gene specified with exact values
            gene_height = { "normal_height" 125 "normal_height" 135 }
            gene_bs_body_type = { "body_fat_head_fat_low" 130 "body_fat_head_fat_low" 130 }
            gene_age = { "old_1" 179 "old_1" 179 }
            # ... accessory genes, complexion, etc.
        }
    }
}
```

The format for each gene is `{ "variant_name" value "variant_name" value }`
where the four values represent: maternal gene name, maternal gene value,
paternal gene name, paternal gene value. Color genes (hair, skin, eye) use raw
integers `{ x y x y }` mapping to palette positions.

DNA entries are referenced in history files to give specific characters their
crafted appearance. The `_ancestors` files provide DNA for dynasty founders
whose genes propagate to descendants.

## Gene Modifications

### AGOT Custom Genes (`common/genes/`)

AGOT adds several gene files beyond vanilla:

**`agot_genes_accessories_jewelry.txt`** -- Defines the
`special_accessories_jewelry` accessory gene category with AGOT-specific items:

```pdx
special_genes = {
    accessory_genes = {
        special_accessories_jewelry = {
            no_jewelry = {
                index = 0
                male = { 100 = empty }
                female = { 100 = empty }
                boy = male
                girl = male
            }
            red_priest_necklace_sphere = {
                index = 1
                male = { 1 = empty }
                female = { 1 = red_priest_necklace_sphere_01 }
                boy = male
                girl = female
            }
            it_handchain = {
                index = 3
                male = { 1 = it_male_handchain }
                female = { 1 = fem_it_male_handchain }
                boy = male
                girl = female
            }
            male_headgear_maester_chain_1 = { ... }
            male_headgear_maester_chain_2 = { ... }
            male_headgear_maester_chain_3 = { ... }
        }
    }
}
```

**`epe_color_genes_morph.txt`** -- Adds morph genes for color variation:

- `skin_color_saturation` -- Shifts skin HSV saturation via curve
- `eye_color_saturation` -- Shifts eye HSV saturation via curve

Both use `inheritable = yes` and apply an HSV shift curve from -1.0 to +1.0.

**`dragon_morph_genes.txt`** -- Dragon-specific morph genes:

- `gene_dragon_aging` -- Custom aging for dragons
- `gene_camera_zoom` -- Controls portrait camera zoom (used for dragon size
  display)
- `dragon_size_portrait_camera` -- Decal-based camera zoom for dragon portraits

**`dragon_accessory_genes.txt`** -- Dragon accessory genes for visual traits.

**`salt_n_pepper.txt`** -- Hair graying gene.

**`gene_age_override.txt`** -- Age appearance overrides.

**`hide_body_gene.txt`** -- Body visibility gene (for dragon portraits).

### Dragon Ethnicity Genes

The dragon ethnicity (`03_agot_dragon.txt`) introduces a large set of custom
genes not found in vanilla:

**Color genes:**

- `gene_dragon_primary_color_hue` / `gene_dragon_primary_color_value` -- Primary
  scale color
- `gene_dragon_secondary_hue` / `gene_dragon_secondary_value` -- Secondary color
- `gene_dragon_tertiary_hue` / `gene_dragon_tertiary_value` -- Tertiary color
- `gene_dragon_eye_color_hue` / `gene_dragon_eye_color_value` -- Dragon eye
  color
- `gene_dragon_horn_color_hue` / `gene_dragon_horn_color_value` -- Horn color

**Morph genes (facial structure):**

- `gene_dragon_brow_width`, `gene_dragon_cheek_width`,
  `gene_dragon_chin_profile`
- `gene_dragon_crest_depth`, `gene_dragon_head_roundness`
- `gene_dragon_jaw_width`, `gene_dragon_lower_jaw_height`,
  `gene_dragon_lower_jaw_width`
- `gene_dragon_snout_height`, `gene_dragon_snout_length`,
  `gene_dragon_snout_profile`, `gene_dragon_snout_width`,
  `gene_dragon_snout_end_width`
- `gene_dragon_upper_jaw_width`, `gene_dragon_outer_brow_height`
- `gene_dragon_old_neck`, `gene_dragon_neck_length`

**Accessory/feature genes:**

- `gene_dragon_main_horn_shape` -- Named horn variants: `dragon_horns_meleys`,
  `dragon_horns_balerion`, `dragon_horns_cannibal`, `dragon_horns_curvy`,
  `dragon_horns_dreamfyre`, `dragon_horns_grey_ghost`, `dragon_horns_long`,
  `dragon_horns_meraxes`, `dragon_horns_silverwing`, `dragon_horns_drogon`
- `gene_dragon_horns_eyebrow_length`, `gene_dragon_horns_eyebrow`
- `gene_dragon_center_fin_size`, `gene_dragon_side_fin_size`
- `gene_dragon_back_spike_size`, `gene_dragon_neck_spike_size`
- `gene_dragon_tail_length`
- `gene_dragon_metallic_scales_strength`
- `gene_dragon_body_shading` -- 16 variants for body region color mapping
  (lower/upper/front/back + black/white/secondary/tertiary)
- `gene_dragon_wings_shading` -- 20 variants for wing region color mapping
- `gene_dragon_size`, `gene_dragon_aging`, `gene_dragon` (base dragon gene)
- `gene_no_portrait` -- Hides portrait (used for eggs/hatchlings)

Dragon color variants are also defined: `dragon_black`, `dragon_white`,
`dragon_ginger`, `dragon_grey` -- each inherits from `dragon` template and
constrains color value ranges.

## AGOT-Specific Template

Use this template when creating a new ethnicity preset for an AGOT submod:

```pdx
# File: common/ethnicities/mymod_myculture_01.txt

@neg1_min = 0.4
@neg1_max = 0.5
@neg2_min = 0.3
@neg2_max = 0.4
@neg3_min = 0.1
@neg3_max = 0.3
@pos1_min = 0.5
@pos1_max = 0.6
@pos2_min = 0.6
@pos2_max = 0.7
@pos3_min = 0.7
@pos3_max = 0.9
@beauty1min = 0.35
@beauty1max = 0.65
@beauty2min = 0.38
@beauty2max = 0.62
@beauty3min = 0.41
@beauty3max = 0.59
@blend1min = 0.0
@blend1max = 0.2
@blend2min = 0.2
@blend2max = 0.5
@blend3min = 0.5
@blend3max = 0.8

mymod_myculture_01 = {

    template = "ethnicity_template"  # or another AGOT base template
    using = "andal"                  # optional: inherit from a named ethnicity

    # Override specific color palettes
    skin_color = {
        10 = { 0.0 0.11 0.6 0.28 }
    }
    eye_color = {
        # Brown
        100 = { 0.13 0.83 0.13 0.83 }
        # Blue
        100 = { 0.89 0.25 0.89 0.25 }
    }
    hair_color = {
        # Brown
        100 = { 0.26 0.97 0.26 0.97 }
        # Black
        100 = { 0.0 0.96 0.0 0.96 }
    }

    # Override specific facial genes
    gene_chin_forward = {
        100 = { name = chin_forward_pos    range = {0.44 0.58} }
    }
    gene_eye_angle = {
        100 = { name = eye_angle_neg       range = {0.45 0.6} }
    }

    # Height distribution
    gene_height = {
        5 = { name = normal_height    range = { 0.35 0.4 } }
        15 = { name = normal_height   range = { 0.45 0.55 } }
        15 = { name = normal_height   range = { 0.55 0.65 } }
        5 = { name = normal_height    range = { 0.65 0.7 } }
    }
}
```

Then reference your presets in a culture definition:

```pdx
# In common/culture/cultures/mymod_cultures.txt
my_culture = {
    # ... other culture properties ...
    ethnicities = {
        1 = mymod_myculture_01
        1 = mymod_myculture_02
        1 = mymod_myculture_03
        # equal weights = equal chance of each preset
    }
}
```

## Annotated AGOT Example

This is the actual `first_man_ethnicity` from
`02_agot_ethnicities_first_man.txt`:

```pdx
first_man_ethnicity = {
    template = "caucasian_base"     # Inherits face morph distributions from vanilla caucasian base
    visible = no                    # Not directly selectable in ruler designer

    eye_color = {
        # No green or blue -- First Men have darker/greyer eyes
        # weight = { min_palette max_palette min_palette max_palette }
        100 = { 0.13 0.83 0.13 0.83 }    # Brown
        100 = { 0.03 0.99 0.03 0.99 }    # Black
        100 = { 0.39 0.61 0.39 0.61 }    # Hazel
        100 = { 0.86 0.18 0.86 0.18 }    # Light Blue / Gray
        100 = { 0.89 0.05 0.89 0.05 }    # Grey
    }
    hair_color = {
        # No light blonde -- First Men have darker hair
        100 = { 0.19 0.83 0.19 0.83 }    # Dirty Blonde
        100 = { 0.26 0.97 0.26 0.97 }    # Brown
        100 = { 0.44 0.87 0.44 0.87 }    # Light Brown
        100 = { 0.8 0.55 0.8 0.55 }      # Red
        100 = { 0.89 0.89 0.89 0.89 }    # Auburn
        100 = { 0.0 0.96 0.0 0.96 }      # Black
    }
    skin_color = {
        10 = { 0.0 0.1 0.5 0.15 }        # Pale northern skin
    }

    # Heavier eyebrows than Andals
    gene_eyebrows_shape = {
        15 = { name = avg_spacing_avg_thickness     range = { 0.5 1.0 } }
        5 = { name = avg_spacing_high_thickness      range = { 0.5 1.0 } }
        15 = { name = avg_spacing_low_thickness      range = { 0.5 1.0 } }
        10 = { name = avg_spacing_lower_thickness    range = { 0.5 1.0 } }
        15 = { name = far_spacing_avg_thickness      range = { 0.5 1.0 } }
        5 = { name = far_spacing_high_thickness      range = { 0.5 1.0 } }
        15 = { name = far_spacing_low_thickness      range = { 0.5 1.0 } }
        10 = { name = far_spacing_lower_thickness    range = { 0.5 1.0 } }
    }

    gene_mouth_open = {
        10 = { name = mouth_open_neg    range = { 0.0 0.0 } }
        10 = { name = mouth_open_pos    range = { 0.0 0.0 } }
    }

    # Taller than average -- wide distribution
    gene_height = {
        5 = { name = normal_height    range = { 0.35 0.4 } }
        5 = { name = normal_height    range = { 0.4 0.45 } }
        15 = { name = normal_height   range = { 0.45 0.55 } }
        15 = { name = normal_height   range = { 0.55 0.65 } }
        5 = { name = normal_height    range = { 0.65 0.7 } }
        5 = { name = normal_height    range = { 0.7 0.75 } }
    }
}
```

Then `crannogman_ethnicity` in the same file overrides height to make Crannogmen
distinctly shorter:

```pdx
crannogman_ethnicity = {
    template = "caucasian_base"
    visible = no
    # ... same colors as first_man but with wider eye/hair variety ...

    gene_height = {
        20 = { name = normal_height    range = { 0.35 0.4 } }
        10 = { name = normal_height    range = { 0.4 0.45 } }
        5 = { name = normal_height     range = { 0.45 0.5 } }
    }
}
```

## Key Differences from Vanilla

| Aspect                       | Vanilla CK3                                      | AGOT                                                                                                                   |
| ---------------------------- | ------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------- |
| **Number of ethnicities**    | ~15 base groups (Caucasian, Mediterranean, etc.) | 20+ base ethnicity definitions, 600+ numbered presets                                                                  |
| **Ethnicity naming**         | Real-world ethnic groups                         | Planetos-specific: `andal_ethnicity`, `valyrian_ethnicity`, `first_man_ethnicity`                                      |
| **Color palettes**           | Standard real-world hair/eye colors              | Custom palettes with purple/indigo eyes for Valyrians, restricted palettes for First Men                               |
| **Face presets per culture** | Typically a few shared presets                   | 10-50 unique numbered presets per culture, each with full gene overrides                                               |
| **Template hierarchy**       | `ethnicity_template` -> presets                  | Multi-layer: `ethnicity_template` -> `valyrian_ethnicity` -> `high_valyrian_ethnicity` -> `high_valyrian_ethnicity_01` |
| **`using` keyword**          | Rarely used                                      | Widely used to compose presets (e.g., `using = "andal"`, `using = "thenn"`)                                            |
| **Gene categories**          | Standard human genes                             | Adds dragon morph genes (30+ custom genes), jewelry accessories, color saturation morphs                               |
| **DNA data files**           | Vanilla characters                               | 40+ region-based files with hand-crafted DNA for historical Planetos characters                                        |
| **Scripted appearance**      | Minimal                                          | Complex scripted effects for hair style management via character flags, scheduled age-based updates                    |
| **EPE system**               | Does not exist                                   | Enhanced Portrait Essosi: dedicated template + 50 presets per Free City                                                |

## AGOT Pitfalls

### 1. Missing scripted variables at file top

Every numbered ethnicity preset file in AGOT repeats the
`@neg1_min`...`@blend3max` variable block at the top. If you forget these, any
gene range using `@pos1_min` or similar will fail silently and default to 0.

### 2. Template chain resolution

AGOT uses deep template chains: `ethnicity_template` -> `valyrian_ethnicity` ->
`high_valyrian_ethnicity` -> numbered preset. Each layer overrides or adds
genes. If you reference a template that does not exist (typo or load order
issue), the game may silently generate default-looking characters with no error
in the log.

### 3. `visible = no` is required on base ethnicities

All base ethnicity definitions (`andal_ethnicity`, `valyrian_ethnicity`, etc.)
set `visible = no`. Only the final numbered presets (referenced by cultures)
should be "visible" (which they are by default if `visible` is not set). If you
set `visible = yes` on a base ethnicity, it may appear in the ruler designer
with incomplete gene data.

### 4. Color format is palette-based, not RGB

Color entries like `100 = { 0.89 0.25 0.89 0.25 }` are NOT RGB values. The four
floats represent
`{ maternal_palette_x maternal_palette_y paternal_palette_x paternal_palette_y }`
-- positions on the game's color palette textures. Guessing RGB values will
produce wrong colors.

### 5. DNA integer vs ethnicity float format

Ethnicity files use float ranges (`range = { 0.45 0.55 }`), but DNA data files
use integer values 0-255 (`"chin_forward_pos" 157`). These are different
representations of the same 0.0-1.0 range. Integer 128 = float 0.5. Do not mix
formats.

### 6. Weight distribution matters

In a culture's `ethnicities = { }` block, AGOT uses equal weights for most
presets (e.g., `1 = Andal_1`, `1 = Andal_2`). The weights are relative --
`10 = preset_A` and `10 = preset_B` give equal probability, same as
`1 = preset_A` and `1 = preset_B`. Using very unequal weights (e.g.,
`100 = preset_A`, `1 = preset_B`) will make preset_B extremely rare.

### 7. `using` vs `template` confusion

- `template = "name"` inherits from a base ethnicity definition (the entire
  block)
- `using = "name"` inherits from a named morph preset block (typically a gene
  set from a `_base` or definition file)

Both can be combined. The `using` keyword is less documented but widely used in
AGOT for composing presets.

### 8. Dragon genes require matching gene definitions

If you reference dragon genes like `gene_dragon_primary_color_hue` in an
ethnicity file, the corresponding gene definition must exist in `common/genes/`.
AGOT defines these in `dragon_morph_genes.txt` and `dragon_accessory_genes.txt`.
Creating a new dragon variant ethnicity without these gene files loaded will
produce errors.

### 9. File load order prefix matters

AGOT uses prefixes to control load order:

- `00_` -- Base templates (loaded first, available as templates for everything
  else)
- `01_` -- Vanilla ethnicity overrides
- `02_` -- AGOT ethnicity definitions
- `03_` -- Special ethnicities (dragons)
- No prefix -- Numbered presets (loaded last, reference everything above)

If your submod files load before AGOT's templates, template references will
fail.

### 10. Scripted hair system

AGOT manages hairstyles through character flags
(`hair_trait_male_hair_western_01`, etc.) applied via
`00_agot_appearance_effects.txt`. The
`agot_schedule_scripted_hair_update_effect` schedules appearance changes at
specific ages. If you add new hairstyles, you must also update the scripted
effects and the gene accessory definitions, or the hairstyles will not display.
