# AGOT Submod Core — Compatibility Framework

## Overview

**AGOT Submod Core** (Workshop ID: `3034473189`, version 1.5.3) is a utility mod
by the AGOT team that solves portrait/accessory compatibility between AGOT
sub-mods. It does nothing visible on its own — it exists purely as a shared
dependency.

**Mod path:**

```
C:/Program Files (x86)/Steam/steamapps/workshop/content/1158310/3034473189
```

**The problem it solves:** CK3's gene files, font files, and certain scripted
effects use "last loaded wins" — if two mods both provide
`05_genes_special_accessories_clothes.txt`, only one survives. The Core provides
a single merged version containing entries from all supported sub-mods.

## Supported Sub-Mods

| Abbreviation | Mod Name                | Detection Trigger                   | Global Variable           |
| ------------ | ----------------------- | ----------------------------------- | ------------------------- |
| COW          | Crowns of Westeros      | `is_crowns_westeros_loaded_trigger` | `Crowns_westeros_enabled` |
| AotK         | Armor of the Kingsguard | `is_aotk_loaded_trigger`            | `Aotk_enabled`            |
| LotD         | Legacy of the Dragon    | `is_lotd_loaded_trigger`            | `Lotd_enabled`            |
| VS           | Valyrian Steel          | `is_valyrian_steel_loaded_trigger`  | `valyrian_steel_enabled`  |
| AGOT+        | AGOT Plus               | `is_agot_plus_loaded_trigger`       | `asoiaf_enabled`          |
| TGC          | The Golden Company      | `is_tgc_loaded_trigger`             | `tgc_enabled`             |
| Brightboar   | Brightboar              | `is_brightboar_loaded_trigger`      | `brightboar_enabled`      |

## Architecture

The Core provides three mechanisms:

### 1. Centralized Conflict-Prone Files

These files can only exist once — CK3 takes "last loaded wins":

| File                                                     | Purpose                                              |
| -------------------------------------------------------- | ---------------------------------------------------- |
| `common/genes/05_genes_special_accessories_clothes.txt`  | Master clothes gene pool (vanilla + all sub-mods)    |
| `common/genes/06_genes_special_accessories_headgear.txt` | Master headgear gene pool (crowns, helms)            |
| `common/genes/07_genes_special_accessories_misc.txt`     | Master legwear gene pool                             |
| `common/genes/08_genes_special_visual_traits.txt`        | Visual trait morphs (pregnancy, plague, etc.)        |
| `common/genes/hk_accessories_misc.txt`                   | Hedge Knight props (shields)                         |
| `common/genes/tgc_accessories_misc.txt`                  | Golden Company props                                 |
| `common/genes/valyrian_steel_accessories_misc.txt`       | Valyrian Steel weapon props                          |
| `common/genes/lotd_accessories_misc.txt`                 | Legacy of the Dragon props                           |
| `common/genes/smc_genes_accessories_jewellery.txt`       | Core's own jewelry gene (Red Priest necklaces, etc.) |
| `fonts/fonts.font`                                       | Font config (adds Valyrian Glyphs font)              |
| `common/scripted_effects/00_agot_death_effects.txt`      | Death portrait-freezing effect                       |

### 2. Mod-Detection API

Each participating sub-mod sets a `global_var` at game start. The Core provides
standardized triggers to check presence:

```pdx
# In your sub-mod's on_game_start:
set_global_variable = { name = my_submod_enabled value = yes }

# In your scripted trigger file (added to the Core):
is_my_submod_loaded_trigger = {
    has_global_variable = my_submod_enabled
}
```

**Usage in scripts:**

```pdx
# Conditionally run logic only when another sub-mod is present
if = {
    limit = { is_crowns_westeros_loaded_trigger = yes }
    # COW-specific behavior
}
```

### 3. Shared Trait Registry

The Core defines ~140+ hidden traits in `common/traits/00_SC_hidden_traits.txt`.
These are invisible portrait-system markers:

```pdx
equipped_crown_of_aegon_artifact = {
    physical = no
    shown_in_ruler_designer = no
    name = trait_hidden
    desc = trait_hidden_desc
    icon = scholar.dds
}
```

**How it works:**

1. Character equips a crown artifact → sub-mod adds the hidden trait
2. Portrait modifier system checks the trait → selects the correct 3D crown
   model
3. Character dies → `agot_apply_inactive_traits_on_death` makes the trait
   inactive (preserves portrait)

**Crown categories covered:**

- Base AGOT Targaryen crowns (Aegon, Jaehaerys, Maekar, etc.)
- Regional Westerosi crowns (Stark, Lannister, Baratheon, Martell, Gardener,
  etc.)
- Crowns of Westeros additions (Rhaegar, Viserys, Jon Snow, etc.)
- Legacy of the Dragon crowns (Aegon's crown with/without gems)
- Blackfyre and house-specific crowns

## Key Triggers

### Crown Eligibility

```pdx
# Can this character wear a crown in portraits?
agot_can_wear_crown_trigger = yes
# Checks: independent ruler, spouse/heir of independent ruler, or coronated

# Should the default crown display behavior apply?
agot_default_wear_crown_trigger = yes
# Integrates with COW's game rule: show_crowns_without_coronation_enabled
```

### Artifact Detection (for portrait selection)

```pdx
# Does this character have a specific equipped weapon?
portrait_has_unique_sword_trigger = yes   # Blackfyre, Dark Sister, etc.
portrait_has_unique_dagger_trigger = yes
portrait_has_unique_spear_trigger = yes
portrait_has_unique_mace_trigger = yes
portrait_has_unique_axe_trigger = yes
portrait_has_unique_hammer_trigger = yes

# Specific crown checks
portrait_should_wear_aegoncrown_trigger = yes
portrait_should_wear_aegoncrown_nogems_trigger = yes
```

### Targaryen/Blackfyre Portrait Check

```pdx
# Is this character Targaryen or Blackfyre (for special clothing)?
portrait_valyrian_clothing_targ_trigger = yes
```

## Death Effect

`agot_apply_inactive_traits_on_death` is the critical shared effect. When a
character dies, it runs `make_trait_inactive` on ALL crown hidden traits from
ALL supported sub-mods. This freezes the portrait.

If you add a new crown sub-mod, your `equipped_*_artifact` trait **must** be
added to this effect, or dead characters will lose their crown portrait.

## Portrait Accessories

The Core includes accessory declarations organized by sub-mod:

| Sub-Mod                     | Files                                                                                                                    | Content                                                  |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------- |
| Kingsguard (KG)             | `KGClothing.txt`, `KGHeadgear.txt`, `KGLegwear.txt`, `KGCloak.txt`                                                       | Kingsguard armor, helms, white cloaks                    |
| Golden Company (TGC)        | `TGCClothing.txt`, `TGCHeadgear.txt`, `TGCLegwear.txt`, `TGCAccessories.txt`                                             | Golden Company armor, shields, swords                    |
| Legacy of the Dragon (LotD) | `valyrian_clothing_lotd.txt`, `valyrian_headgear_lotd.txt`, `valyrian_legwear_lotd.txt`, `valyrian_accessories_lotd.txt` | Valyrian nobility clothing, Aegon's crown, Viserys masks |
| Crowns of Westeros (COW)    | `COW_Headgear.txt`                                                                                                       | House-specific crown headgear entities                   |
| Hedge Knight (HK)           | `HKAccessories.txt`                                                                                                      | Shields as held props                                    |
| Core (SMC)                  | `smc_clothing.txt`                                                                                                       | Alicent Hightower dresses                                |

## Sub-Mod Recipes

### Recipe 1: Register Your Sub-Mod with the Detection API

If you want other sub-mods to detect yours:

1. Add a global variable in your game start on-action:

```pdx
# common/on_action/my_mod_on_actions.txt
on_game_start_after_lobby = {
    effect = {
        set_global_variable = { name = my_mod_enabled value = yes }
    }
}
```

2. Request the Core team to add your trigger (or include it in your own mod as a
   stopgap):

```pdx
# common/scripted_triggers/my_mod_loaded_trigger.txt
is_my_mod_loaded_trigger = {
    has_global_variable = my_mod_enabled
}
```

### Recipe 2: Add a Custom Crown (with Core integration)

1. Define the hidden trait:

```pdx
# This needs to be added to the Core's 00_SC_hidden_traits.txt
# (or ship in your own mod as a temporary measure)
equipped_my_custom_crown_artifact = {
    physical = no
    shown_in_ruler_designer = no
    name = trait_hidden
    desc = trait_hidden_desc
    icon = scholar.dds
}
```

2. Add the crown artifact with trait assignment:

```pdx
# When equipped, add the hidden trait
on_equip = {
    owner = { add_trait = equipped_my_custom_crown_artifact }
}
on_unequip = {
    owner = { remove_trait = equipped_my_custom_crown_artifact }
}
```

3. Create a portrait modifier that checks the trait:

```pdx
# gfx/portraits/portrait_modifiers/99_my_crown.txt
my_crown_portrait = {
    usage = game
    selection_behavior = max
    priority = 90

    headgear = {
        gene = gene_headgear
        value = my_crown_headgear_01
        template = my_crown_headgear_01
        range = { 0 1 }
        weight = {
            base = 0
            modifier = {
                add = 500
                has_trait = equipped_my_custom_crown_artifact
            }
        }
    }
}
```

4. Request the Core team add `equipped_my_custom_crown_artifact` to
   `agot_apply_inactive_traits_on_death`.

### Recipe 3: Add Portrait Accessories Without the Core

If your mod doesn't need crown/weapon integration:

```pdx
# You CAN add new accessories directly in your mod
# gfx/portraits/accessories/my_mod_clothing.txt
my_custom_outfit = {
    entity = { node = "Portrait_Torso" entity = "my_outfit_entity" }
}
```

But you **cannot** add entries to the numbered gene files (`05_*`, `06_*`, etc.)
without conflicting. If you need gene entries, coordinate with the Core.

## Pitfalls

1. **Never ship your own version of `05_genes_special_accessories_clothes.txt`
   (or `06_`/`07_`/`08_`).** These are the most conflict-prone files in the AGOT
   ecosystem. Use the Core's versions and coordinate additions through the Core
   team.

2. **The death effect must know about ALL crown traits.** If you add a crown but
   don't add it to `agot_apply_inactive_traits_on_death`, dead characters will
   lose their crown portrait.

3. **The `fonts.font` file is a full override.** If your sub-mod also needs to
   add fonts, you must merge with the Core's version or coordinate.

4. **Global variable names for detection are not standardized.** Note the
   inconsistent casing: `Crowns_westeros_enabled` vs. `tgc_enabled` vs.
   `Aotk_enabled`. Always check the exact variable name.

5. **The Core must load between AGOT and your sub-mod.** Load order: AGOT →
   Submod Core → your mod. If you depend on both, list both in `dependencies`.

6. **Gene entries reference accessory names.** If you add an accessory in your
   mod, the gene file in the Core must have the matching entry. Shipping
   accessories without gene entries means they won't appear.

7. **Portrait modifiers from multiple mods can conflict on priority.** If your
   crown uses the same priority as another mod's crown, the last-loaded one
   wins. Use unique priority values.

8. **The Core is updated alongside AGOT.** When AGOT updates, the Core typically
   updates too. Coordinate timing with the Core team.

9. **Not all AGOT sub-mods use the Core.** Gameplay-only mods (events,
   decisions, buildings, map) typically don't need it. Only portrait/accessory
   mods do.

10. **The `agot_can_wear_crown_trigger` integrates with COW's game rule.** If
    you check crown eligibility, use this trigger — don't roll your own, or your
    mod will ignore the player's COW settings.
