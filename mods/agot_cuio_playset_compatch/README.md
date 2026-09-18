# AGOT Playset – Character UI Overhaul Compatch

Compatibility owner for the GUI overlaps between Character UI Overhaul and the
AGOT playset, plus Artifact Manager's two artifact-icon atlases.

## Requirements and load order

Load after **A Game of Thrones**, **Better Barbershop**, **AGOT Dragon Wives**,
**More Interactive Vassals**, **Artifact Manager**, **AGOT More Personality
Depth**, its runtime rebase, **AGOT - More Personality Depth + Dragon Wives
Compatch**, **AGOT Iron and Salt**, and **Character UI Overhaul**.

## Character sheet

Character UI Overhaul is the layout authority, and the compatible AGOT and More
Personality Depth changes are merged into it: dragon-family rows, personality
visibility, AGOT character names and interaction controls, loyalist-faction
protection, rescue and revenge war controls, and More Interactive Vassals'
vassal-muster opinion breakdown. Artifact Manager's `artifact_bg.dds` and
`artifact_unique.dds` remain the effective icons.

AGOT keeps the alternate dragon, hidden-character, and fake-death sheets, and
the shared window keeps AGOT's 650-pixel width, because those sheets and AGOT's
relationship rows are authored for that shell rather than vanilla's 610-pixel
sidebar. CUIO's top control strip is restricted to normal characters; each
alternate sheet supplies its own controls.

The relationship tab keeps AGOT's bodyguard and dragon rows and its four
reduced-width Friends variants. The ordinary CUIO Friends rows appear only when
no bodyguard or dragon row consumes their space, so you get one bounded row
rather than two layouts expanding side by side.

## Family tab

CUIO's inline and expanded secondary-spouse rows own the vanilla polygamy path
and are hidden for Valyrian characters, where Dragon Wives owns it instead, so
each character sees exactly one of the two designs. The Dragon Wives grandparent
and spouse rows are lifted into CUIO's first family row.

## Krakens

AGOT Iron and Salt replaces the character sheet, character lists, and portrait
tooltip to keep human-only interface off krakens, which on its own undoes
everything above. Its kraken handling is merged in here instead, so kraken
tooltips, list rows, and character view all work with the CUIO layout kept.

Dragon portrait tooltips suppress the human sex icon, and the opinion badge
suppresses dread on dragons and opinion values on characters who faked death.

## Notes

Hometowns, and the HUD, map icon, and creature-check parts of the Iron and Salt
integration, are deliberately left to later mods in the playset.
