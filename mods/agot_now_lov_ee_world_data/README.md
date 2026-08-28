# AGOT NOW + LoV + Essos Expanded World Data

Fills in the last provinces of the eastern map that no mod gives terrain to, and
sets graphical regions so those lands use the right visual style.

## Requirements and load order

Load immediately after **AGOT NOW + Legacy of Valyria + Essos Expanded Map
Compatch**.

## What it changes

Essos Expanded: The Further East now authors terrain for almost all of the east,
and its terrain is always kept. This mod only covers what is left over:

- Terrain for the 1,435 eastern provinces no mod assigns any terrain to. It
  never overrides another mod's choice — if anything upstream has an opinion
  about a province, that opinion wins. The generated terrain is derived from the
  region's macro-biome, forest/jungle/arid/snow/mountain evidence from two
  known-world reference maps, slope from the heightmap, and the map's water
  classes.
- Graphical regions for the same area, so provinces use the right visual style.
- Restores the five displaced `c_rutting` provinces to the western graphical
  style.

It does not change map definitions, map images, landed titles, province or title
history, governments, or holders. In particular it does not change Maegon
Harderback or the gameplay policy for Oros.
