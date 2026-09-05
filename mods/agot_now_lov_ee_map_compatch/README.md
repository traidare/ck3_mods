# AGOT NOW + Legacy of Valyria + Essos Expanded Map Compatch

Carries the Westeros map edits of Nobility of Westeros onto the world map that
Essos Expanded: The Further East now supplies, so no mod in the stack silently
overwrites another's work.

## Requirements and load order

Load after A Game of Thrones, AGOT Nobility of Westeros, Legacy of Valyria, the
AGOT LoV bridge, Essos Expanded, and Essos Expanded: The Further East.

- **AGOT NOW - CK3 1.19 Rebase** must load immediately after Nobility of
  Westeros and before this map layer.
- **AGOT NOW-Season of Ice and Fire Compatch** must load immediately after that
  NOW rebase.
- **Essos Expanded: The Further East - CK3 1.19 History Rebase** must load
  **after** Essos Expanded: The Further East.
- After the history rebase, load these two Workshop compatches in order before
  this module:
  1. Seasons of Valyria - TempLoV/NOW/Seasons Compatch
  2. Essos Expanded - TempLoV/NOW Compatch

## What it does

The Further East now ships the complete, canonical world map, including AGOT's
Ibben, the Axe, Norvos, Qohor, Lorath, and Rhoyne. This compatch no longer
renumbers provinces or ships its own terrain, heightmaps, or titles. It carries
only the Westeros details that would otherwise be lost, plus one map repair:

- the thirteen provinces Nobility of Westeros retunes;
- building and special-building placements, merged one record at a time;
- roads, bridges, and other map decorations, merged placement by placement;
- Nobility of Westeros' island regions, over A Game of Thrones' own complete set
  of map regions, so everything AGOT keys to a region still finds it.

## Stray province pixels

A handful of pixels in the far east of the world map were left in the colour of
a Riverlands province, which made the two provinces count as neighbours no
matter how far apart they sat. Realms in Westeros could therefore wage war on
and colonize into the far east across a border that does not exist. Those pixels
are repainted as the province that surrounds them; nothing else on the map is
touched, and the build stops if the area ever looks different from what the
repair expects.

This is a semantic merge, not a last-writer copy. Where two mods changed the
same thing, the merge keeps both intentions where they can coexist — a road mesh
keeps the Further East's removed segment alongside Nobility of Westeros' five
new ones, and the special building at Cuy keeps the Further East's new placement
at Nobility of Westeros' chosen size. Anything genuinely ambiguous stops the
build rather than picking a silent winner.

## Locator placement

Building, special-building, army, combat, siege, and activity markers are
checked against the world map itself and moved into the province they belong to
when they sit outside it. Provinces that had no marker at all are given one.

This matters most across Essos and the Further East, where the marker positions
the stack would otherwise fall back on were drawn for an older map: special
buildings and travel destinations appeared far from their province, and armies
and activities could fail to place at all. Deliberate placements are preserved —
a marker's facing and size are never changed, and hand-placed exceptions are
left where their author put them.
