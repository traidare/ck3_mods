# AGOT NOW + Legacy of Valyria + Essos Expanded Map Compatch

Load after AGOT, AGOT Nobility of Westeros (NOW), Legacy of Valyria (LoV), the
AGOT 0.4.39 LoV temporary compatch, Essos Expanded, and its LoV compatch. The
local `AGOT NOW - CK3 1.19 Rebase` must load immediately after NOW and before
this map layer. The local `Essos Expanded + LoV - CK3 1.19 History Rebase` must
load immediately after Essos Expanded and before its TempLoV compatch.

The three Workshop compatches must follow the history rebase, in this order,
before this module:

1. `AGOT NOW-Season of Ice and Fire Compatch`
2. `Seasons of Valyria - TempLoV/NOW/Seasons Compatch`
3. `Essos Expanded - TempLoV/NOW Compatch`

This is a semantic merge rather than a last-writer copy:

- keeps Essos Expanded's province table and applies the eleven province rows
  changed by NOW 1.2.4;
- preserves NOW's exact 3,470-pixel AGOT heightmap delta against the original
  Essos Expanded source under
  `content_source/heightmap/heightmap_now_delta_unpacked.png`;
- keeps LoV/Essos map objects outside NOW's Westeros edit rectangle and NOW
  objects inside it, merging locator records by numeric id;
- accepts the noncanonical indentation used by several EE/LoV locator records
  and verifies that no locator id is skipped or duplicated during generation;
- composites the two generator masks changed by NOW;
- resolves the two verified AGOT 0.4.40 title-localization fallback conflicts to
  NOW's warden/master rules, while failing generation for any other merge
  conflict.

It deliberately does not own `00_agot_character_data_effects.txt`: the third
Workshop compatch owns its upstream dispatcher and the later Lore Governments
module applies the final lore-specific transform. Keeping map data and
character-title dispatch separate prevents a map rebase from restoring stale
government behavior.

The `workspace/agot_now_lov_ee_map_compatch/mod.toml` generator stages generated
output and only promotes a complete declared output set into the local module.
Its granular source manifest pins all text and image inputs, so an upstream
update must be reviewed explicitly:

```sh
ck3mm mod generate agot_now_lov_ee_map_compatch
ck3mm mod generate agot_now_lov_ee_map_compatch --apply
```

After reviewing an intentional upstream map or mask change, update the granular
source-manifest asset and run the full generator so the image composites are
rebuilt with the text outputs.
