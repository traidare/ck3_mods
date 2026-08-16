# AGOT Playset – Character UI Overhaul Compatch

Compatibility owner for the eight GUI overlaps between Character UI Overhaul and
the AGOT playset, plus Artifact Manager's two artifact-icon atlases.

## Requirements and load order

Load after **A Game of Thrones**, **Better Barbershop**, **AGOT Dragon Wives**,
**More Interactive Vassals**, **Artifact Manager**, **AGOT More Personality
Depth**, its runtime rebase, **AGOT - More Personality Depth + Dragon Wives
Compatch**, and **Character UI Overhaul**. Keep it before **AGOT Playset Runtime
Fixes** and the final **AGOT Personal Playset Compatch**.

## What it merges

Character UI Overhaul is the layout authority. The compatible AGOT and More
Personality Depth changes are merged in, and the overlapping AGOT interfaces are
explicitly restored: dragon-family rows, personality visibility, AGOT character
names and interaction controls, loyalist-faction protection, rescue and revenge
war controls, and More Interactive Vassals warnings. Artifact Manager's
`artifact_bg.dds` and `artifact_unique.dds` remain the effective icons.

## Character and relationship views

Character UI Overhaul remains the layout owner for the normal character sheet,
while AGOT owns the alternate dragon, hidden-character, and fake-death sheets.
The shared character window keeps AGOT's 650-pixel width, because those
alternate sheets and AGOT's relationship rows are authored for that shell rather
than vanilla's 610-pixel sidebar. CUIO's standalone top control strip is
restricted to normal characters; each AGOT alternate sheet supplies its own
window controls. CUIO also remains the single layout owner for the normal
sheet's name, age, and health row; AGOT supplies only its localized
character-name text and tooltip.

The relationship tab keeps AGOT's bodyguard and dragon rows together with its
four reduced-width Friends variants. The ordinary CUIO Friends rows appear only
when no bodyguard or dragon row consumes their space, so you get one bounded row
rather than two layouts expanding side by side.

## Family tab

CUIO's inline and expanded secondary-spouse rows own the vanilla polygamy path
and are hidden for Valyrian characters; Dragon Wives owns the Valyrian path.
Each character therefore sees exactly one of the two designs. The Dragon Wives
grandparent and spouse rows are lifted into CUIO's first family row, and the
expanded spouses view is CUIO's scrollbox carrying AGOT's secondary-spouses
header.

Hometowns is deliberately not owned here — **AGOT Playset Runtime Fixes**
remains its effective writer.
