# AGOT NOW + LoV + Essos Expanded World Data

Generated terrain and graphical-region integration for the current AGOT, NOW,
Legacy of Valyria, and Essos Expanded playset.

Load immediately after **AGOT NOW + Legacy of Valyria + Essos Expanded Map
Compatch**.

## Ownership

This module intentionally owns:

- `common/province_terrain/ee_province_terrain.txt`, replacing the TempLoV
  blanket `plains` assignments for Essos Expanded provinces 10946 through 26420;
  and
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

`scripts/generate-agot-now-lov-ee-world-data.py` reads the installed Workshop
parents, the local map compatch, and the two full-world reference images in
`.ignored/map_images/`. Their coastlines and major landmarks share the CK3 map's
full-world projection. The generator resamples them to a common analysis grid
and aggregates their biome evidence by exact province pixels.

Final terrain combines:

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
scripts/generate-agot-now-lov-ee-world-data.py --audit
scripts/generate-agot-now-lov-ee-world-data.py
scripts/generate-agot-now-lov-ee-world-data.py --check
```

`terrain_decisions.csv` is reserved for explicit province exceptions; the
current lore-rule baseline needs none. `--audit` writes the complete evidence
table without changing runtime output. `--update-source-manifest` is required
when an upstream input or either reference image changes; use it only after
reviewing the source diff and the generator's structural assertions.

Re-run the audit after every update to Workshop mods `2962333032`, `3664900993`,
`3403938445`, `3719888822`, `3682802751`, or `3768149491`, or after regenerating
`agot_now_lov_ee_map_compatch`.
