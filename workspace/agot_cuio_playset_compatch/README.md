# agot_cuio_playset_compatch — module state

Generated final-integration layer owning the AGOT playset's eight Character UI
Overhaul GUI overlaps and Artifact Manager's two artifact-icon atlases.

## Ownership

Character UI Overhaul is the layout authority. The generator three-way merges
the compatible AGOT and MPD changes onto it and explicitly restores the
overlapping AGOT interfaces: dragon-family rows, personality visibility, AGOT
character names and interaction controls, loyalist-faction protection,
rescue/revenge war controls, and More Interactive Vassals warnings. Artifact
Manager's `artifact_bg.dds` and `artifact_unique.dds` remain the effective
icons.

Hometowns is intentionally **not** owned here; the later
`agot_playset_runtime_fixes` module remains its effective repaired writer.

AGOT keeps its culture cooltip body in the additive
`gui/shared/agot_cooltip.gui` and calls it from `cooltip.gui` by type reference,
so the merged `cooltip.gui` must keep the `agot_culture_tooltip_insert` and
`agot_culture_tooltip_click` call sites rather than any inlined copy of that
body. The generator asserts both, and asserts `Culture.HasFascination` twice:
AGOT gates the fascination row _and_ the divider above it, where vanilla and
CUIO gate only the row.

### Character and relationship views

CUIO owns the normal character sheet; AGOT owns the alternate dragon,
hidden-character, and fake-death sheets. The shared `character_window` keeps
AGOT's 650-pixel width, because those alternate sheets and AGOT's relationship
rows are authored for that shell rather than vanilla's 610-pixel sidebar. CUIO's
standalone top control strip is restricted to normal characters; each AGOT
alternate sheet supplies its own window controls. CUIO remains the single layout
owner for the normal sheet's name, age, and health row; AGOT supplies only its
localized character-name text and tooltip.

The relationship tab keeps AGOT's bodyguard and dragon rows together with its
four reduced-width Friends variants. The ordinary CUIO Friends rows are shown
only when no bodyguard or dragon row consumes their space, preserving one
bounded row rather than allowing both layouts to expand horizontally.

Both icon pairs in the status row — CUIO's plain sex icons and the sexuality
icons — are gated on AGOT's `agot_<gender>_gender_shown` scripted GUI rather
than the bare `Character.IsFemale` check. That gate also excludes dragons, which
are characters in AGOT and would otherwise draw a human sex icon. The gating is
anchored on each icon's texture, because the bare condition is no longer unique.

More Personality Depth contributes two behaviours the CUIO-first merge would
otherwise resolve away: the AI personality row shown for player characters, and
the zero-size `mpd_view_hook` widget that runs its XP roller. The hook is
re-attached to the `character_window` block itself, so CUIO layout changes
cannot displace it.

**Re-audit** this ownership whenever CUIO changes the character-window width or
relationship row structure, or AGOT changes its alternate sheets and
relationship types.

### Family tab

CUIO's `secondary_spouses_inline` and `secondary_spouses` rows own the vanilla
polygamy path and are gated on `Not(dw_valyrian_special)`; Dragon Wives owns the
Valyrian path, so each character sees exactly one of the two designs. The Dragon
Wives grandparent and spouse rows are lifted into CUIO's first family row, ahead
of its trailing `expand`. Its four-wives row is named
`secondary_spouses_special` and carries only the Valyrian condition.

The expanded spouses view is CUIO's scrollbox, named `family_spouses_expanded`
and carrying AGOT's `AGOT_SECONDARY_SPOUSES` header. AGOT ships an equivalent
scrollbox of its own; because the three-way merge is line-based and CUIO moved
the family tab, that copy merges without conflict into `vbox_filter_group`,
where the row's `CharacterWindow` relation lookups have no datacontext to
resolve against. The generator removes it and keeps CUIO's row as the single
owner.

**Re-audit** this split whenever CUIO or the Dragon Wives compatch changes the
family tab, and whenever CUIO moves the family tab or AGOT moves its expanded
relation scrollboxes.

## Generation

```sh
ck3mm mod generate agot_cuio_playset_compatch
ck3mm mod generate agot_cuio_playset_compatch --apply
```

`mod.toml` declares the Workshop sources and owns `gfx` and `gui` wholesale.
Every input file is pinned by SHA-256 in the generator's `PINS` table, checked
by `pinned_text` and `pinned_bytes`. Regeneration stops on any upstream change,
forcing an explicit re-audit rather than silently applying a stale GUI merge. A
hash mismatch is the re-audit trigger for this module.
