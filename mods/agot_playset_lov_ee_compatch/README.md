# AGOT Playset Compatch - Essos Expanded + Further East

The Essos Expanded add-on to **AGOT Playset Compatch**, for a large AGOT playset
on CK3 1.19. Enable it whenever Essos Expanded: The Further East is enabled, and
disable it together with that family.

## What it does

**Map.** The Further East supplies the world map; this module carries onto it
the Westeros work that would otherwise be lost — Nobility of Westeros' retuned
provinces, its buildings and map decorations, and its island regions over AGOT's
full set of map regions. Stray far-eastern pixels inside a Riverlands province
colour are repainted, so Westerosi realms no longer war and colonize across a
border that does not exist. Building, army, combat, siege, and activity markers
move into the province they belong to, and provinces missing one are given one.

**Terrain.** Eastern provinces no parent assigns terrain to are filled in from
reference maps, the heightmap, and the map's water classes; an upstream opinion
always wins. Graphical regions follow, and the displaced `c_rutting` provinces
return to the western visual style.

**Governments.** Essos gets lore-appropriate rule: nomadic Dothraki and Jogos
Nhai, theocratic Dosh Khaleen and Red Priesthood, administrative or oligarchic
Free Cities, Ghiscari cities, the Valyrian Freehold, Qarth, celestial Yi Ti, and
mandala Leng. Norvos, Lorath, and Qohor are left to AGOT; Ibben follows the
God-King until the Doom and the Sound after it.

**Repairs.** AGOT's game-start script, which the Legacy of Valyria bridge
silently reverted, is restored with the bridge's own additions kept. The Further
East's repeated capital declarations in dated title history, which current CK3
rejects, are removed, and its lay-clergy temple baronies — a source of invalid
rulers and repeated succession errors — become cities.

Landed-title structure, holdings, names, dynasties, and unrelated faith history
are untouched.

## Required load order

Everything below is required, in this order, before this module, which loads
last of all:

1. A Game of Thrones
2. AGOT Nobility of Westeros, then its CK3 1.19 rebase
3. Legacy of Valyria, then Legacy of Valyria - AGOT 0.5.2.1 Compatch (Beta)
4. Essos Expanded, then Essos Expanded: The Further East
5. AGOT NOW-Season of Ice and Fire Compatch
6. Seasons of Valyria - TempLoV/NOW/Seasons Compatch
7. Essos Expanded - TempLoV/NOW Compatch
8. AGOT Playset Compatch
9. AGOT Playset Compatch - Legacy of Valyria
