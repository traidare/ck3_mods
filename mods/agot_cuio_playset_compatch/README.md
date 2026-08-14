# AGOT Playset – Character UI Overhaul Compatch

Generated compatibility owner for the active AGOT playset's eight CUIO GUI
overlaps and Artifact Manager's two artifact-icon atlases.

Load after **A Game of Thrones**, **Better Barbershop**, **AGOT Dragon Wives**,
**More Interactive Vassals**, **Artifact Manager**, **AGOT More Personality
Depth**, its local runtime rebase, **AGOT - More Personality Depth + Dragon
Wives Compatch**, and **Character UI Overhaul**. Keep it before **AGOT Playset
Runtime Fixes** and the final **AGOT Personal Playset Compatch**.

The generator uses Character UI Overhaul as the layout authority, three-way
merges the compatible AGOT/MPD changes, and explicitly restores the overlapping
AGOT interfaces: dragon-family rows, personality visibility, AGOT character
names and interaction controls, loyalist-faction protection, rescue/revenge war
controls, and More Interactive Vassals warnings. Artifact Manager's
`artifact_bg.dds` and `artifact_unique.dds` remain the effective icons.

## Character and relationship views

CUIO remains the layout owner for the normal character sheet, while AGOT owns
the alternate dragon, hidden-character, and fake-death sheets. The shared
`character_window` keeps AGOT's 650-pixel width because those alternate sheets
and AGOT's relationship rows are authored for that shell rather than vanilla's
610-pixel sidebar. CUIO's standalone top control strip is restricted to normal
characters; each AGOT alternate sheet supplies its own window controls. CUIO
also remains the single layout owner for the normal sheet's name, age, and
health row; AGOT supplies only its localized character-name text and tooltip.

The relationship tab keeps AGOT's bodyguard and dragon rows together with its
four reduced-width Friends variants. The ordinary CUIO Friends rows are shown
only when no bodyguard or dragon row consumes their space, preserving one
bounded row rather than allowing both layouts to expand horizontally. Re-audit
this ownership whenever CUIO changes the character-window width or relationship
row structure, or AGOT changes its alternate sheets and relationship types.

## Family tab ownership

CUIO's `secondary_spouses_inline` and `secondary_spouses` rows own the vanilla
polygamy path and are gated on `Not(dw_valyrian_special)`; Dragon Wives owns the
Valyrian path, so each character sees exactly one of the two designs. The Dragon
Wives grandparent and spouse rows are lifted into CUIO's first family row, ahead
of its trailing `expand`. Its four-wives row is named
`secondary_spouses_special` and carries only the Valyrian condition. Re-audit
this split whenever CUIO or the Dragon Wives compatch changes the family tab.

The expanded spouses view is CUIO's scrollbox, named `family_spouses_expanded`
and carrying AGOT's `AGOT_SECONDARY_SPOUSES` header. AGOT ships an equivalent
scrollbox of its own; because the three-way merge is line-based and CUIO moved
the family tab, that copy merges without conflict into `vbox_filter_group`,
where the row's `CharacterWindow` relation lookups have no datacontext to
resolve against. The generator removes it and keeps CUIO's row as the single
owner. Re-audit whenever CUIO moves the family tab or AGOT moves its expanded
relation scrollboxes.

Every input file is pinned by SHA-256. Regeneration stops on any upstream
change, forcing an explicit re-audit rather than silently applying a stale GUI
merge. Hometowns is intentionally not owned here: the later **AGOT Playset
Runtime Fixes** module remains its effective repaired writer.
