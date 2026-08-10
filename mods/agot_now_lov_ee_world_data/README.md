# AGOT NOW + LoV + Essos Expanded World Data

Generated terrain and graphical-region integration for the current AGOT, NOW,
Legacy of Valyria, and Essos Expanded playset.

Load immediately after **AGOT NOW + Legacy of Valyria + Essos Expanded Map
Compatch**.

## Ownership

This module intentionally owns:

- `common/province_terrain/ee_province_terrain.txt` for Essos Expanded provinces
  10946 through 26420, deferring to the TempLoV compatch wherever it authors a
  real terrain and supplying generated terrain only where it still leaves its
  `plains` placeholder; and
- the graphical geographical-region keys emitted in
  `map_data/geographical_regions/zzzz_agot_now_lov_ee_world_data.txt`.

It does not own map definitions, map images, landed titles, province/title
history, governments, or holders. In particular, it does not change Maegon
Harderback or the gameplay policy for Oros.

The graphical output also restores the five NOW-displaced `c_rutting` provinces,
1697 through 1701, to `graphical_western`.

NOW's winning `graphical_siberia` block references `world_westeros_skagos`. That
helper is not visible after the later geographical-region replacements in this
playset, and repeating the reference causes Tiger's fatal
`region world_westeros_skagos not defined` diagnostic. The generator preserves
the helper's intended coverage directly with `d_skagos`, `d_deepdown`, and
`d_driftwood_hall`.

## Generation

The `workspace/agot_now_lov_ee_world_data/mod.toml` generator reads its declared
Workshop parents, the local map compatch, and its two declared repository
reference images. Their coastlines and major landmarks share the CK3 map's
full-world projection. The generator resamples them to a common analysis grid
and aggregates their biome evidence by exact province pixels.

The generated terrain combines:

- the empire-level macro-biomes in `terrain_lore_regions.csv`;
- forest, jungle, arid, snow, and mountain evidence from
  `KnownWorldDetailed.jpg` and `KnownWorldGoogleMaps.jpg`;
- slope from EE's 16-bit heightmap for province-wide hill and mountain relief;
- strong semantic terrain-mask evidence for oasis, floodplain, wetland, jungle,
  frozen, and farmland exceptions; and
- water classes from EE's `default.map`.

The older mask classifier remains in the audit as an independent comparison, but
its low spatial holdout score no longer determines final terrain.
Graphical-style generation is unchanged.

```sh
ck3mm mod generate agot_now_lov_ee_world_data
ck3mm mod generate agot_now_lov_ee_world_data --apply
```

`terrain_decisions.csv` is reserved for explicit province exceptions; the
current lore-rule baseline needs none. Generation also refreshes the complete
evidence table. When an upstream input or reference image changes, review the
source diff and structural assertions, then update the granular source-manifest
asset before regenerating.

Re-run the audit after every update to Workshop mods `2962333032`, `3664900993`,
`3403938445`, `3719888822`, `3682802751`, or `3768149491`, or after regenerating
`agot_now_lov_ee_map_compatch`. The current reviewed baselines are NOW 1.2.5,
Essos Expanded 1.0, and its TempLoV compatch 2.5.0.
