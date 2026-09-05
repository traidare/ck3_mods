# agot_now_lov_ee_map_compatch — module state

Map-data merge across AGOT, NOW, Legacy of Valyria, the LoV AGOT bridge, Essos
Expanded, and Further East.

Load position: after all parents. The local `agot_now_119_rebase` must load
immediately after NOW, followed by `AGOT NOW-Season of Ice and Fire Compatch`.
The local `essos_expanded_further_east_rebase` must load **after** Further East,
because it now generates from Further East's history. The remaining two Workshop
compatches must follow that history rebase, in this order, before this module:

1. `Seasons of Valyria - TempLoV/NOW/Seasons Compatch`
2. `Essos Expanded - TempLoV/NOW Compatch`

## Ownership

Further East v4 adopted AGOT 0.5's native 8233-9400 province band and ships a
canonical 27,589-province map. This layer therefore starts from that map and
carries only the Westeros deltas the effective playset would otherwise lose. It
owns eleven files under `gfx/map/map_object_data` and `map_data`:

- the province table, keeping Further East's 27,589 rows and applying the
  thirteen rows NOW changes that Further East still inherits unchanged from
  AGOT;
- the province raster, carrying Further East's pixels with the reclaims under
  [Raster reclaims](#raster-reclaims) applied and nothing else changed;
- the building and special-building locator files and the two map-object files,
  merged record by record;
- the player-stack, combat, siege and activity locator files, carried verbatim
  from the Essos compatch that is their effective last writer and changed only
  by the locator repair below;
- the geographical regions file, carrying NOW's island deltas over a baseline
  restored to AGOT's full region set.

It ships **no heightmaps, landed titles, or history**, and no raster beyond
`provinces.png`. Further East supplies all of them, so this layer needs no
province renumbering, title retirement, or capital relocation of its own.

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

Each overlay is diffed against the baseline it was actually authored against —
currently NOW against AGOT. Diffing a derived source against AGOT would read its
shared ancestry as conflict, so the overlay stack keeps that pairing explicit.

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

Three baronies render the larger castle meshes from COW-AGOT (`2971198450`),
which no map source in this merge accounts for. `LOCATOR_PINS` overrides their
records field by field — Dunstonbury and Planky Town in both locator files,
Ryamsport's scale in the special-building file — and each entry states the
merged value it overrides, so a later Further East or NOW re-placement fails
generation instead of being silently discarded. `OBJECT_INSTANCE_SUPPRESSIONS`
pairs with the Planky Town scale by dropping NOW's Greenblood bridge instance
there, which would otherwise cross COW's mesh.

## Geographical regions

AGOT writes this file and Further East overrides it wholesale, so what this
layer ships is the effective definition of every region AGOT script names.
Further East's copy defines fewer regions than AGOT's, and a region it omits is
a gap in its fork rather than a removal: AGOT still resolves the name, and a
`region = <key>` that resolves to nothing is a load failure rather than a
missing feature. The baseline is therefore AGOT's region set with Further East's
own block kept wherever both define one, and generation fails when an AGOT
region other than a reviewed dissolution does not reach the shipped file.

Carrying a region forward places AGOT's text over a map this layer does not own,
so each restored region is checked before it is merged: every duchy and county
it names must exist in the effective landed-title stack, and every province id
it names must be the same barony in AGOT's province table and in the one this
layer ships. Either mismatch means the region would cover land AGOT did not
name, which fails generation rather than shipping.

Regions may overlap and reference each other in either direction, so a restored
region coexists with whatever Further East flattened its territory into and its
position in the file carries no meaning. `DISSOLVED_REGIONS` is the reviewed
exception where an absence is deliberate.

The same reading applies inside a region. NOW writes `coastal_counties` from its
own Westeros survey, so the block it ships names no Rhoynish, Shivering Sea or
Stepstones coast while its `landed_titles` still define every one of those
counties as land. `NOW_REGION_GAPS` records that territory as a gap in a
Westeros fork rather than a removal, and the merge restores it into NOW's own
block; honouring the omission would drop the whole Essos coast out of AGOT's
sailing activity and the three great projects that filter provinces through this
region. `c_tormore` is deliberately not in the gap set: NOW retires that county
with the Sisters rework, so its absence is the one removal NOW means.

## Raster reclaims

Further East's `provinces.png` is the baseline for the raster this layer emits,
and this layer supplies `definition.csv`, so the two are read as a pair. That
pairing is exact: the thirteen NOW colour edits form a closed permutation within
a set of neighbouring ids, so every colour this layer names is painted in
Further East's raster and refers to the pixels NOW intended.

Further East's newest provinces carry placeholder names of the form
`R<r>G<g>B<b>` recording the colour they were painted with before their
definition row was given a different one. Fifteen of those recorded colours are
also colours this map assigns to an existing province, so any pixel a recolour
missed reads back as that unrelated province. CK3 derives province adjacency
from pixel adjacency alone, which makes the two provinces neighbours wherever
they sit on the map, and every neighbour-scoped rule follows: a realm that owns
the misread province can wage war on, and colonize into, a region it has no
border with.

`RASTER_RECLAIMS` repaints such pixels back to the province they belong to. Each
entry pins the province reclaimed, the province the pixels currently read as,
and the exact count and inclusive bounds the repair may touch, so a changed
raster fails generation rather than being silently repainted. An entry also
fails if reclaiming would leave the misread province unpainted, which
distinguishes a leak from a province that genuinely lives there.

`assert_compact_provinces` is the general form of the same check: a province
painted in one place has a compact bounding box, so any province whose pixels
span more than `MAX_COMPACT_SPAN` is either one of the reviewed map-spanning
zones in `WIDE_PROVINCES` or an unrepaired leak, and the two sets must match
exactly. The reviewed members are the sea and impassable zones that reach the
map edges, plus two Further East ids painted in two places whose intended
province no source records; both of those lie wholly inside the far-east range,
so neither creates a cross-continent neighbour.

## Locator repair

Against the reclaimed raster, a locator position is either inside the province
its record belongs to or it is not. Merged positions that are not are rewritten
to the province's centroid, or to the painted pixel nearest the centroid where
the centroid falls in a neighbour or in the sea, as it does for concave and
split provinces. Land provinces with no record at all gain one. Rotation and
scale are never touched, so an author's deliberate orientation or sizing
survives a position repair, and `LOCATOR_PINS` records are exempt because they
sit outside their province on purpose.

Along with the raster reclaims, this is where the layer derives data rather than
merging it. It is needed because Further East ships no `building_locators.txt`:
the fallback Essos Expanded file positions every id in 9401-26420 against Essos
Expanded's own map, which Further East redrew.
`artifacts/map_data/merge_audit.json` records the per-file repair counts.

The residue is provinces `definition.csv` names but the raster paints nowhere.
They have no position to be given, they are reported as `unplaceable` in the
audit, and they are left alone rather than guessed at.

The single reviewed conflict is special-building locator `3462` (`b_cuy`).
Further East re-placed the building and, as it does at every locator it
re-places, reset height and scale to the editor defaults; NOW instead
deliberately resized the same model from 0.267 to 0.468. The resolution keeps
Further East's placement and NOW's scale, so neither source loses its intent.

## Untitled province quarantine

A province that is passable in `default.map` but carries no landed title is an
invalid map state: the engine expects every passable province to belong to a
barony. The effective playset leaves 1,000 such provinces, because this layer
takes Further East's province table while the title stack across AGOT, NOW,
Legacy of Valyria, and the LoV bridge assigns no barony to them.

The generator resolves the effective `landed_titles` files by load order across
those parents, parses both inline and multiline `province = <id>` assignments,
and computes the province definitions that are neither water nor already
impassable and carry no title. All 1,000 are unpainted in the winning raster, so
they are map-table residue rather than territory, and making them impassable
removes nothing a player can see or hold.

Those ids are appended to a generated `map_data/default.map` as deterministic,
chunked `impassable_mountains` lists between explicit begin/end markers, leaving
Further East's own 1,710 impassable entries untouched and non-overlapping. The
generator asserts the computed set matches the reviewed
`assets/untitled_province_quarantine.json`, that every quarantined province is
unpainted, and that no passable untitled definition remains.

Quarantine is deliberately preferred over wilderness conversion here. Wilderness
is a state applied to an existing county title, and these provinces have no
title at all; converting them would require synthesizing baronies, counties, de
jure parents, capitals, history, and localization. Where a real county title
exists, wilderness conversion remains the correct tool and is handled elsewhere.

## Generation

The `mod.toml` generator stages output and only promotes a complete declared
output set. `sources.lock.json` records every input file it consumes, so an
upstream update remains visible even when generated bytes do not move:

```sh
ck3mm mod generate agot_now_lov_ee_map_compatch
ck3mm mod generate agot_now_lov_ee_map_compatch --apply
```

## Re-audit

- A pinned-source or pinned-count mismatch fails generation; that failure is the
  general re-audit trigger.
- Re-audit the quarantine whenever the computed untitled set stops matching
  `assets/untitled_province_quarantine.json`. A shrinking set means a parent
  supplied the missing titles, and those ids should be released from quarantine
  rather than re-pinned. A growing set, or any quarantined province that is
  painted in the raster, means real territory is about to be made impassable and
  must be reviewed before the asset is replaced. Landed-title changes in AGOT,
  NOW, Legacy of Valyria, the LoV bridge, or Further East can all move it.
- Re-audit the thirteen NOW province rows whenever Further East begins authoring
  any of them itself; generation fails rather than overwriting Further East.
- Re-audit locator `3462` when its digest pin trips, and re-review rather than
  re-pinning the new inputs unchanged.
- Re-audit the region set when generation reports an AGOT region dropped without
  review, or a restored region naming territory the playset lacks. The first
  means the merge stopped carrying AGOT's set forward; the second means AGOT's
  regions and Further East's map have diverged, and the region needs remapping
  rather than carrying.
- Re-audit a `NOW_REGION_GAPS` entry when generation reports that it no longer
  holds. NOW naming the territory again, or AGOT dropping it, means the omission
  has stopped being a fork's blind spot, and the entry belongs gone rather than
  re-pinned.
- Re-audit a `RASTER_RECLAIMS` entry when its pixel count or bounds stop
  matching. Fewer pixels means Further East finished the recolour and the entry
  belongs gone; more, or moved, means the province was repainted and the repair
  must be re-derived rather than re-pinned.
- Re-audit `WIDE_PROVINCES` when `assert_compact_provinces` reports a change. A
  newly wide province is a leak to be traced to the province that should own it
  and given a reclaim entry, not added to the reviewed set; a province that
  stops being wide means an upstream repair landed and the entry belongs gone.
- Re-audit the locator repair if Further East begins shipping its own
  `building_locators.txt`, or if the audit's `unplaceable` counts move: a rising
  count means the province table and the raster are drifting apart.
- Further East may omit a locator file; the generator then uses the
  corresponding Essos Expanded parent file as the native baseline. For
  `building_locators.txt`, AGOT's records replace the parent's stale 8233-9400
  band because Further East restored AGOT's province identities there while
  Essos Expanded still assigns those ids to Anogaria.
- Re-audit the whole baseline if Further East stops shipping the canonical map
  or diverges from AGOT's province band again.
