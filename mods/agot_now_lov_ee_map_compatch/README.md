# AGOT NOW + Legacy of Valyria + Essos Expanded Map Compatch

Merges the map edits of Nobility of Westeros, Legacy of Valyria, and Essos
Expanded into one coherent world, and grafts AGOT 0.5.0's new Ibben, the Axe,
Norvos, Qohor, Lorath, and Rhoyne region onto it.

## Requirements and load order

Load after A Game of Thrones, AGOT Nobility of Westeros, Legacy of Valyria, the
AGOT LoV temporary compatch, Essos Expanded, and its LoV compatch.

- **AGOT NOW - CK3 1.19 Rebase** must load immediately after Nobility of
  Westeros and before this map layer.
- **Essos Expanded + LoV - CK3 1.19 History Rebase** must load immediately after
  Essos Expanded and before its TempLoV compatch.
- These three Workshop compatches must follow that history rebase, in order,
  before this module:
  1. AGOT NOW-Season of Ice and Fire Compatch
  2. Seasons of Valyria - TempLoV/NOW/Seasons Compatch
  3. Essos Expanded - TempLoV/NOW Compatch

## What it does

This is a semantic merge, not a last-writer copy. It keeps Essos Expanded's
province table with Nobility of Westeros' eleven changed rows, preserves
Nobility of Westeros' Westeros heightmap edit on top of AGOT's heights, keeps
Legacy of Valyria and Essos Expanded map objects outside the Westeros edit area
and Nobility of Westeros' objects inside it, and resolves the two title-name
conflicts to Nobility of Westeros' warden and master rules.

AGOT 0.5.0's new 1,168-province region is added in full. Because Essos Expanded
already occupies the province numbers AGOT uses, the new region is renumbered
above Essos Expanded's range, leaving every existing province untouched. AGOT's
Rhoyne, Lorath, Norvos, Qohor, and the Axe replace the Legacy of Valyria and
Essos Expanded versions of the same land — those two mods detail the same
valley, and the overlap costs 345 authored Essos Expanded baronies. Westeros de
jure structure stays with Nobility of Westeros.

Three counties whose original capital fell under the new region keep their land:
each capital's full history moves to the county's first surviving barony rather
than leaving it empty.
