# agot_now_lov_ee_world_data — module state

Generated terrain and graphical-region integration for the current AGOT, NOW,
Legacy of Valyria, and Essos Expanded playset. Load position: immediately after
`agot_now_lov_ee_map_compatch`.

## Ownership

This module is a **gap filler**. It same-path overrides no upstream terrain
file: its single output is
`common/province_terrain/zzzz_agot_now_lov_ee_world_data.txt`, whose `zzzz_`
prefix places it last in ASCIIbetical order so it loads alongside Further East's
own files rather than instead of them. Every province Further East, AGOT, NOW,
or LoV assigns therefore keeps its own author's terrain.

It intentionally owns:

- generated terrain for the 1,435 provinces in the 10946-26420 range that **no**
  effective module assigns a real terrain to. Generation fails if that output
  would collide with any upstream assignment, so every province Further East,
  AGOT, NOW, or LoV has an opinion about keeps its own author's value; and
- the graphical geographical-region keys emitted in
  `map_data/geographical_regions/zzzz_agot_now_lov_ee_world_data.txt`.

Further East v4 sets this module's scope. It authors terrain for 14,040 of the
15,475 provinces in the classified range, leaving the 1,435 gaps above. The
classifier measures Further East's own raster and definition table, so the ids
it classifies describe the land it samples.

It does not own map definitions, map images, landed titles, province/title
history, governments, or holders. In particular, it does not change Maegon
Harderback or the gameplay policy for Oros.

The graphical output also restores the five NOW-displaced `c_rutting` provinces,
1697 through 1701, to `graphical_western`.

Each emitted graphical key is a complete replacement, and same-key regions in
different files are resolved by last path rather than merged, so this file is
the sole effective definition of the eight keys it touches. Every one of them
expresses each classified province exactly once, in exactly one region. The
generator starts from the inherited block, which already covers the whole map,
keeps the `duchies`, `counties`, `kingdoms`, and `regions` entries that reach
only provinces outside the classified range or provinces this run still assigns
to that style, drops the entries whose classified provinces moved to another
style, and then lists explicitly only the ids no retained entry already covers.
Generation fails if a single membership entry straddles the reassignment, and
again before writing unless the emitted blocks reproduce the classification
exactly. Without both, CK3 reports
`Province 'N' lies in multiple graphical regions` and
`Region 'N' has multiple entries for the province 'N'` at world init and
resolves an ambiguous province to whichever style it reaches first, which
decides that province's unit, building, and clothing art.

NOW's winning `graphical_siberia` block references `world_westeros_skagos`. That
helper is not visible after the later geographical-region replacements in this
playset, and repeating the reference causes Tiger's fatal
`region world_westeros_skagos not defined` diagnostic. The generator preserves
the helper's intended coverage directly with `d_skagos`, `d_deepdown`, and
`d_driftwood_hall`.

## Generation

The `mod.toml` generator reads its declared Workshop parents, the local map
compatch, and its two declared repository reference images. Their coastlines and
major landmarks share the CK3 map's full-world projection. The generator
resamples them to a common analysis grid and aggregates their biome evidence by
exact province pixels.

The generated terrain combines:

- the empire-level macro-biomes in `terrain_lore_regions.csv`;
- forest, jungle, arid, snow, and mountain evidence from
  `KnownWorldDetailed.jpg` and `KnownWorldGoogleMaps.jpg`;
- slope from EE's 16-bit heightmap for province-wide hill and mountain relief;
- strong semantic terrain-mask evidence for oasis, floodplain, wetland, jungle,
  frozen, and farmland exceptions; and
- water classes from EE's `default.map`.

The mask classifier remains in the audit as an independent comparison only; its
spatial holdout score is too low to determine final terrain. Graphical-style
generation does not use it.

```sh
ck3mm mod generate agot_now_lov_ee_world_data
ck3mm mod generate agot_now_lov_ee_world_data --apply
```

`terrain_decisions.csv` is reserved for explicit province exceptions; the
current lore-rule baseline needs none. Generation also refreshes the complete
evidence table.

## Re-audit

Re-run the audit after every update to Workshop mods `2962333032`, `3664900993`,
`3403938445`, `3719888822`, `3682802751`, or `3768149491`, or after regenerating
`agot_now_lov_ee_map_compatch`. When an upstream input or reference image
changes, review the source diff and structural assertions, then update the
source diff before regenerating. The exact files consumed by the generator and
their hashes are recorded in `sources.lock.json`.

Specific triggers carried over from the Further East v4 rebase:

- `EXPECTED_GAP_COUNT` shrinking is the signal that this module is approaching
  retirement. When Further East covers the range completely, delete it.
- `EXPECTED_NAMED_TARGETS` and `EXPECTED_TITLE_COUNT` pin how much of the range
  Further East has authored; either moving means re-reading its structure before
  trusting the classifier's scope.
- The empire tier is optional. Further East leaves 146 provinces under top-level
  `k_R43G49B154`, mapped to `graphical_western` because Further East already
  assigns them that region upstream. Re-check that mapping if it gains a parent.
- `e_lorath`, `e_norvos`, and `e_qohor` were dropped from both asset configs:
  AGOT owns them natively now and Further East adopted its province band, so
  they left the classified range.
- `e_lhazar` and `e_lower_sarne_dothraki` are each two landmasses under Further
  East v4. Both components take the same style, so the disconnection is accepted
  rather than reviewed province by province.
