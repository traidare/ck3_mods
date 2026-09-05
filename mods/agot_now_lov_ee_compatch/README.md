# AGOT NOW + Legacy of Valyria + Essos Expanded Compatch

One compatch for the combined A Game of Thrones, AGOT Nobility of Westeros,
Legacy of Valyria, and Essos Expanded: The Further East world — map, terrain,
and the history and governments of the east.

## Requirements and load order

All of the following are required, in this order, before this module. It loads
last of them and before any generic runtime-fix or full-playset compatch.

1. A Game of Thrones
2. AGOT Nobility of Westeros, then AGOT NOW - CK3 1.19 Rebase
3. Legacy of Valyria, then Legacy of Valyria - AGOT 0.5.1 Bridge
4. Essos Expanded, then Essos Expanded: The Further East
5. AGOT NOW-Season of Ice and Fire Compatch
6. Seasons of Valyria - TempLoV/NOW/Seasons Compatch
7. Essos Expanded - TempLoV/NOW Compatch

## What it does

**Map.** The Further East supplies the world map; this module carries the
Westeros work that would otherwise be lost onto it — the thirteen provinces
Nobility of Westeros retunes, its buildings, special buildings, and map
decorations merged one record at a time, and its island regions over AGOT's own
complete set of map regions. Where two parents changed the same thing both
intentions are kept; anything genuinely ambiguous stops the build rather than
picking a silent winner. Stray far-eastern pixels left in a Riverlands province
colour are repainted, so Westerosi realms can no longer war and colonize across
a border that does not exist. Building, army, combat, siege, and activity
markers are moved into the province they belong to, and provinces without one
are given one, with every marker's facing, size, and hand placement preserved.

**Terrain.** Eastern provinces no parent assigns terrain to are filled in from
macro-biome, forest, jungle, arid, snow, and mountain evidence in two
known-world reference maps, slope from the heightmap, and the map's water
classes. An upstream opinion always wins. Graphical regions follow for the same
area, and the displaced `c_rutting` provinces return to the western visual
style.

**Governments.** Essos gets lore-appropriate rule: nomadic Dothraki and Jogos
Nhai under a theocratic Dosh Khaleen, a theocratic Red Priesthood,
administrative or oligarchic Free Cities, oligarchic Ghiscari cities, Valyrian
Freehold, and Qarth, celestial and meritocratic Yi Ti, mandala Leng, and
conservative tribal, clan, or feudal forms where the source material is thin.
Norvos, Lorath, and Qohor are left to AGOT, and pirate, ruin, wilderness,
unknown, and landless governments are never overwritten. Before the Doom, Ibben
is a feudal realm following the God-King; from the Doom onward it follows the
Sound and turns oligarchic for the Shadow Council, so no later God-King bookmark
is offered. Jogos Nhai culture history is corrected alongside it.

**Repairs.** The Legacy of Valyria bridge's whole-file copy of AGOT's game-start
script is rebuilt from AGOT's current version with the bridge's own additions
reapplied, so AGOT's Narrow Sea gate, Lorath setup, confederations, scenarios,
and sailing setup are no longer silently reverted. The Further East's repeated
capital declarations inside dated title history, which current CK3 rejects, are
removed with every holder and government transition intact, and its generated
lay-clergy temple baronies — which produced invalid rulers and repeated
succession errors — become cities keeping their separately held, tax-producing
role.

It does not change landed-title structure, holdings, names, dynasties, or
unrelated faith history.
