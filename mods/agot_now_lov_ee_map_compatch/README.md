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
  `content_source/heightmap/heightmap_now_delta_unpacked.png`, then composites
  AGOT's heights;
- keeps LoV/Essos map objects outside NOW's Westeros edit rectangle and NOW
  objects inside it, merging locator records by numeric id;
- accepts the noncanonical indentation used by several EE/LoV locator records
  and verifies that no locator id is skipped or duplicated during generation;
- composites the two generator masks changed by NOW;
- resolves the two verified AGOT 0.4.40 title-localization fallback conflicts to
  NOW's warden/master rules, while failing generation for any other merge
  conflict.

## AGOT 0.5.0's new region

AGOT 0.5.0 added 1,168 provinces at ids 8233-9400 — Ibben, the Axe, Norvos,
Qohor, Lorath and the Rhoyne. The effective map already spends those ids on
Essos Expanded's authored baronies, and no map parent has rebased onto 0.5.0.
This module renumbers AGOT's region onto **26421-27588**, above the Essos
Expanded ceiling, and leaves every parent id untouched. `map_merge.py` builds
the table; `artifacts/map_data/agot_new_province_remap.json` records it. Only
one colour collided, `b_punulea_sar`, which is recoloured to `255 255 254`.

Taking AGOT's region wholesale is a deliberate choice, made with the trade-off
measured. AGOT's new land overlaps Essos Expanded's authored content on 35.7% of
its 927,787 pixels, almost all of it under `e_rhoyne`, where the two mods detail
the same valley. The paste empties 970 Essos Expanded province rows, 345 of them
authored baronies rather than generated `R<r>G<g>B<b>` filler. Those counts are
pinned in `map_merge.py`, so a changed footprint fails generation instead of
quietly consuming more.

The landed-titles graft follows the same line. This module owns
`common/landed_titles/01_agot_landed_titles.txt` and adds AGOT's `e_rhoyne`,
`k_lorath`, `k_norvos`, `k_qohor`, `k_the_axe` and `b_vornegollo` — 1,380 titles
over 1,109 renumbered provinces — into the file NOW wins. It does **not** graft
`d_knellstone`, `d_ninestars`, `d_the_northern_mountains` or `c_tormore`: those
are AGOT 0.5.0 restructuring Westeros de jure, they carry no new-region
province, and NOW owns that structure on purpose.

The graft replaces two upstream trees rather than relying on duplicate-title
load semantics:

- LoV's `lv_rhoyne_titles.txt` puts `e_rhoyne` and 299 baronies on provinces
  9039-9337. This module re-emits that file without the old tree.
- Essos Expanded's `k_lorath` holds 143 generated placeholder titles on 111
  provinces, so this module removes that subtree from `01_landed_titles.txt`
  before AGOT's authored Lorath loads later.

Fourteen old provinces retained only 578 edge pixels after the paste. Because
their parent trees are replaced, the generator absorbs those slivers into the
surrounding AGOT region. It then re-emits the three affected landed-title files
without all 980 baronies on pixel-free provinces and recursively removes empty
ancestors. Of 1,208 source titles stripped, 11 are supplied again by the AGOT
graft; `artifacts/map_data/removed_titles.json` records the 1,197 titles that
are genuinely gone.

The same generation drops 17 upstream title-history blocks for removed titles.
The later Lore Governments generator consumes `removed_titles.json` and drops
another 215 effective history blocks, preventing its full-file overrides from
restoring them. AGOT's 1,109 land-province history blocks are replayed at
26421-27588 in `history/provinces/zz_agot_new_region_prov.txt`; the 59 remaining
ids are AGOT's lakes, mountains, and sea zones.

Expect the renumbering to unwind once NOW, LoV and Essos Expanded publish their
own 0.5.0 rebases, which will most likely adopt AGOT's native 8233-9400. The
remap table is the only place that encodes it, so unwinding is a deletion.

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
