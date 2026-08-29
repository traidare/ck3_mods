# agot_now_lov_ee_map_compatch — module state

Map-data merge across AGOT, NOW, Legacy of Valyria, the LoV AGOT bridge, Essos
Expanded, and Further East.

Load position: after all parents. The local `agot_now_119_rebase` must load
immediately after NOW and before this map layer; the local
`essos_expanded_further_east_rebase` must load **after** Further East, because
it now generates from Further East's history. The three Workshop compatches must
follow that history rebase, in this order, before this module:

1. `AGOT NOW-Season of Ice and Fire Compatch`
2. `Seasons of Valyria - TempLoV/NOW/Seasons Compatch`
3. `Essos Expanded - TempLoV/NOW Compatch`

## Ownership

Further East v4 adopted AGOT 0.5's native 8233-9400 province band and ships a
canonical 27,589-province map. This layer therefore starts from that map and
carries only the Westeros deltas the effective playset would otherwise lose. It
owns six files under `gfx/map/map_object_data` and `map_data`:

- the province table, keeping Further East's 27,589 rows and applying the
  thirteen rows NOW changes that Further East still inherits unchanged from
  AGOT;
- the two locator files and the two map-object files, merged record by record;
- the geographical regions file, carrying NOW's island deltas.

It ships **no rasters, heightmaps, landed titles, or history.** Further East
supplies all of them, so this layer needs no province renumbering, title
retirement, or capital relocation of its own.

It deliberately does **not** own `00_agot_character_data_effects.txt`: the third
Workshop compatch owns its upstream dispatcher and the later
`agot_now_lov_ee_lore_governments` module applies the final lore-specific
transform.

## Merge rules

Every merge is semantic, never a last-writer copy. Records are keyed by their
stable identity (locator id, map-object `name`, region name) and compared with
comments and whitespace ignored, so a source that only reformats a record makes
no delta. Locator parsing accepts both editor-style multiline records and
single-line records, while retaining the source file's surrounding frame.

Each overlay is diffed against the baseline it was actually authored against:
NOW against AGOT, and the COW/NOW compatch against NOW, which it extends.
Diffing a derived source against AGOT would read its shared ancestry as
conflict.

Where only one side moved a record, that side wins. Where both moved it:

- **Map objects** merge structurally. A mesh's instance list is a set of unique,
  order-independent placement rows with a `count=` field that must match its
  length, so adding or removing one road segment always collides textually.
  Replaying each side's additions and removals against AGOT's rows and
  recomputing `count` is exact where a text merge is not. `Minor Road_15 short`
  resolves to Further East's removal plus NOW's five additions: 101 instances.
- **Locators** fall back to `git merge-file`, and a real conflict fails
  generation rather than picking a winner. The one reviewed exception is pinned
  in `LOCATOR_RESOLUTIONS`, field by field, with a digest of all three inputs so
  any upstream change re-raises it.

The single reviewed conflict is special-building locator `3462` (`b_cuy`).
Further East re-placed the building and, as it does at every locator it
re-places, reset height and scale to the editor defaults; NOW instead
deliberately resized the same model from 0.267 to 0.468. The resolution keeps
Further East's placement and NOW's scale, so neither source loses its intent.

## Generation

The `mod.toml` generator stages output and only promotes a complete declared
output set. Its source manifest pins every input file, so an upstream update
must be reviewed explicitly:

```sh
ck3mm mod generate agot_now_lov_ee_map_compatch
ck3mm mod generate agot_now_lov_ee_map_compatch --apply
```

The COW/NOW compatch (`3742055253`) is consumed as a generator source only. It
stays disabled as a standalone mod.

## Re-audit

- A pinned-source or pinned-count mismatch fails generation; that failure is the
  general re-audit trigger.
- Re-audit the thirteen NOW province rows whenever Further East begins authoring
  any of them itself; generation fails rather than overwriting Further East.
- Re-audit locator `3462` when its digest pin trips, and re-review rather than
  re-pinning the new inputs unchanged.
- Further East may omit a locator file; the generator then uses the
  corresponding Essos Expanded parent file as the native baseline. For
  `building_locators.txt`, AGOT's records replace the parent's stale 8233-9400
  band because Further East restored AGOT's province identities there while
  Essos Expanded still assigns those ids to Anogaria.
- Re-audit the whole baseline if Further East stops shipping the canonical map
  or diverges from AGOT's province band again.
