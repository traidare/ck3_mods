# AGOT NOW + Legacy of Valyria + Essos Expanded Map Compatch

Carries the Westeros map edits of Nobility of Westeros onto the world map that
Essos Expanded: The Further East now supplies, so no mod in the stack silently
overwrites another's work.

## Requirements and load order

Load after A Game of Thrones, AGOT Nobility of Westeros, Legacy of Valyria, the
AGOT LoV bridge, Essos Expanded, and Essos Expanded: The Further East.

- **AGOT NOW - CK3 1.19 Rebase** must load immediately after Nobility of
  Westeros and before this map layer.
- **Essos Expanded: The Further East - CK3 1.19 History Rebase** must load
  **after** Essos Expanded: The Further East.
- These three Workshop compatches must follow that history rebase, in order,
  before this module:
  1. AGOT NOW-Season of Ice and Fire Compatch
  2. Seasons of Valyria - TempLoV/NOW/Seasons Compatch
  3. Essos Expanded - TempLoV/NOW Compatch

## What it does

The Further East now ships the complete, canonical world map, including AGOT's
Ibben, the Axe, Norvos, Qohor, Lorath, and Rhoyne. This compatch no longer
renumbers provinces or ships its own terrain, heightmaps, or titles. It carries
only the Westeros details that would otherwise be lost:

- the eleven provinces Nobility of Westeros retunes;
- building and special-building placements, merged one record at a time;
- roads, bridges, and other map decorations, merged placement by placement;
- Nobility of Westeros' island regions.

This is a semantic merge, not a last-writer copy. Where two mods changed the
same thing, the merge keeps both intentions where they can coexist — a road mesh
keeps the Further East's removed segment alongside Nobility of Westeros' five
new ones, and the special building at Cuy keeps the Further East's new placement
at Nobility of Westeros' chosen size. Anything genuinely ambiguous stops the
build rather than picking a silent winner.
