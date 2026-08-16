# AGOT NOW + LoV + Essos Expanded World Data

Gives Essos Expanded's provinces real terrain and graphical regions instead of
placeholder plains, across the combined AGOT, Nobility of Westeros, Legacy of
Valyria, and Essos Expanded map.

## Requirements and load order

Load immediately after **AGOT NOW + Legacy of Valyria + Essos Expanded Map
Compatch**.

## What it changes

- Terrain for Essos Expanded provinces that still carry the temporary Legacy of
  Valyria compatch's `plains` placeholder. Wherever that compatch authors real
  terrain, its terrain is kept. The generated terrain is derived from the
  region's macro-biome, forest/jungle/arid/snow/mountain evidence from two
  known-world reference maps, slope from the heightmap, and the map's water
  classes.
- Graphical regions for the same area, so provinces use the right visual style.
- Restores the five displaced `c_rutting` provinces to the western graphical
  style.

It does not change map definitions, map images, landed titles, province or title
history, governments, or holders. In particular it does not change Maegon
Harderback or the gameplay policy for Oros.
