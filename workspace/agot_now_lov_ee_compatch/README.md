# agot_now_lov_ee_compatch — module state

The single compatch layer for the AGOT, NOW, Legacy of Valyria, and Essos
Expanded: The Further East stack. It covers the map merge, terrain and graphical
regions, the eastern government and faith history, and the two upstream rebases
that stack depends on.

Load position: after every parent below, and before the generic runtime-fix and
full-playset compatches.

1. AGOT (`2962333032`)
2. NOW (`3664900993`), then the local `agot_now_119_rebase`
3. Legacy of Valyria (`3403938445`), then its AGOT bridge (`3719888822`)
4. Essos Expanded (`3682802751`), then Further East (`3768149491`)
5. `AGOT NOW-Season of Ice and Fire Compatch` (`3753608966`)
6. `Seasons of Valyria - TempLoV/NOW/Seasons Compatch` (`3766038754`)
7. `Essos Expanded - TempLoV/NOW Compatch` (`3773608127`)

## Generator structure

`implementation.py` resolves one `compatch.RunInputs` — the Workshop roots, the
output root, the assets directory, and the reference maps — and runs five stages
in dependency order:

| stage                       | writes                                                                           |
| --------------------------- | -------------------------------------------------------------------------------- |
| `compatch.lov_bridge`       | `common/on_action/agot_on_actions/agot_game_start.txt`                           |
| `compatch.further_east`     | nothing; returns the repaired history texts in memory                            |
| `compatch.map_merge`        | `map_data/`, `gfx/map/map_object_data/`                                          |
| `compatch.world_data`       | `common/province_terrain/zzzz_*.txt`, `map_data/geographical_regions/zzzz_*.txt` |
| `compatch.lore_governments` | `history/`, `common/scripted_effects/replace/00_agot_character_data_effects.txt` |

Two results travel between stages in memory rather than through the payload. The
Further East history repair hands its `hist_titles.txt` and `k_generated.txt`
texts to the lore-government stage as the topmost layer, so each of those files
is written exactly once, already repaired and already governed. The map merge
hands its parsed province table to the world-data stage, which would otherwise
re-read the `definition.csv` it just wrote.

`compatch/context.py` holds the Workshop registry and the run inputs;
`compatch/pdx.py` the positional Clausewitz document model, the span-edit
helpers, and `top_level_blocks`; `compatch/layers.py` the load-order resolution
that answers which module supplies a file and which module's definition of a key
wins; `compatch/mapdata.py` the `definition.csv` row model. Everything narrower
than that lives in `gen`.

`map_data/geographical_regions/` carries two files from two stages. CK3 reads a
directory in filename order, so the `zzzz_` world-data file still wins the
duplicate region keys it redefines over the `00_agot_` map-merge file, which is
what the prefix is for.

## Ownership

The module owns `common/on_action/agot_on_actions/agot_game_start.txt`,
`common/province_terrain/`, `common/scripted_effects/replace/`,
`gfx/map/map_object_data/`, `history/`, and `map_data/`.

It ships **no heightmaps and no landed titles**, and no raster beyond
`provinces.png`. It does not own holdings, names, dynasties, or unrelated faith
history. In particular it does not change Maegon Harderback or the gameplay
policy for Oros.

### Startup script

The LoV AGOT bridge ships a whole-file copy of AGOT's game-start script, so it
silently reverts every AGOT startup change made since that copy was taken. The
generated file starts from AGOT's complete current script and reapplies only the
bridge's intentional additions: the LoV dummy-ruler rehome hook, the Mantaryan
trait hook, and the estate innovation and slot guards. AGOT's Narrow Sea gate,
Lorath setup, confederations, scenarios, sailing setup, and every other startup
behaviour come back with it. The supersiren distributor selects each county
capital, requires a valid culture and faith, and kills the source ruler only
after all counties transfer.

The bridge's game-start estate-owner lists now match AGOT's exactly — it drives
noble family estates from its own `title_on_actions.txt` instead — so no owner
list is ported. The stage compares both lists per tier and fails if the bridge
starts widening them at game start again, which would otherwise be dropped here
without a trace.

Both game-start inputs are pinned by source hash and every splice is a counted
replacement, so an upstream edit fails generation instead of producing a
half-rebased script.

### Further East history repairs

Further East repeats `capital = ...` inside 46 dated title-history blocks.
Current CK3 rejects `capital` in that context and emits 46 persistent-reader
errors. The same empire, kingdom, and duchy capitals are already declared in
Further East's landed titles, so only those invalid history tokens are removed;
every holder and government transition is preserved and the date blocks are
otherwise byte-for-byte intact.

Further East also generates 1,180 `church_holding` provinces. Of these, 410
secondary baronies use one of three AGOT faiths that combine lay clergy with
fixed spiritual appointment: `song_nefer` (375), `dothraki_faith` (21), and
`sarnori_faith` (14). AGOT's theocracy government rejects lay-clergy characters,
while its secular governments do not accept a church as their primary holding,
so CK3 generates invalid rulers for precisely these 410 baronies and repeatedly
reports `unhandled succession order [invalid]`. Those 410 secondary holdings
become `city_holding`, keeping the intended separately held, tax-producing
secondary-barony role without changing faith doctrine or creating extra feudal
domains. No county capital or other province field changes.

Each repair asserts its own count — 46 dated capitals, 1,180 church holdings,
410 conversions — so a Further East history change fails generation instead of
silently repairing more or fewer provinces than intended.

## Map merge

Further East v4 adopted AGOT 0.5's native 8233-9400 province band and ships a
canonical 27,589-province map. The merge starts from that map and carries only
the Westeros deltas the effective playset would otherwise lose:

- the province table, keeping Further East's 27,589 rows and applying the
  thirteen rows NOW changes that Further East still inherits unchanged from
  AGOT;
- the province raster, carrying Further East's pixels with the reclaims below
  applied and nothing else changed;
- the building and special-building locator files and the two map-object files,
  merged record by record;
- the player-stack, combat, siege and activity locator files, carried verbatim
  from the Essos compatch that is their effective last writer and changed only
  by the locator repair below;
- the geographical regions file, carrying NOW's island deltas over a baseline
  restored to AGOT's full region set.

Further East supplies heightmaps, landed titles, and history, so this merge
needs no province renumbering, title retirement, or capital relocation of its
own.

### Merge rules

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

### Geographical regions

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

### Raster reclaims

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

### Locator repair

Against the reclaimed raster, a locator position is either inside the province
its record belongs to or it is not. Merged positions that are not are rewritten
to the province's centroid, or to the painted pixel nearest the centroid where
the centroid falls in a neighbour or in the sea, as it does for concave and
split provinces. Land provinces with no record at all gain one. Rotation and
scale are never touched, so an author's deliberate orientation or sizing
survives a position repair, and `LOCATOR_PINS` records are exempt because they
sit outside their province on purpose.

Along with the raster reclaims, this is where the module derives data rather
than merging it. It is needed because Further East ships no
`building_locators.txt`: the fallback Essos Expanded file positions every id in
9401-26420 against Essos Expanded's own map, which Further East redrew.
`artifacts/map_data/merge_audit.json` records the per-file repair counts.

The residue is provinces `definition.csv` names but the raster paints nowhere.
They have no position to be given, they are reported as `unplaceable` in the
audit, and they are left alone rather than guessed at.

The single reviewed conflict is special-building locator `3462` (`b_cuy`).
Further East re-placed the building and, as it does at every locator it
re-places, reset height and scale to the editor defaults; NOW instead
deliberately resized the same model from 0.267 to 0.468. The resolution keeps
Further East's placement and NOW's scale, so neither source loses its intent.

### Untitled province quarantine

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

## Terrain and graphical regions

This stage is a **gap filler**. It same-path overrides no upstream terrain file:
its terrain output is
`common/province_terrain/zzzz_agot_now_lov_ee_world_data.txt`, whose `zzzz_`
prefix places it last in ASCIIbetical order so it loads alongside Further East's
own files rather than instead of them. Every province Further East, AGOT, NOW,
or LoV assigns therefore keeps its own author's terrain.

It intentionally owns:

- generated terrain for the 1,435 provinces in the 10946-26420 range that **no**
  effective module assigns a real terrain to. Generation fails if that output
  would collide with any upstream assignment; and
- the graphical geographical-region keys emitted in
  `map_data/geographical_regions/zzzz_agot_now_lov_ee_world_data.txt`.

Further East v4 sets this stage's scope. It authors terrain for 14,040 of the
15,475 provinces in the classified range, leaving the 1,435 gaps above. The
classifier measures Further East's own raster and the merged definition table,
so the ids it classifies describe the land it samples.

The graphical output also restores the five NOW-displaced `c_rutting` provinces,
1697 through 1701, to `graphical_western`.

Each emitted graphical key is a complete replacement, and same-key regions in
different files are resolved by last path rather than merged, so this file is
the sole effective definition of the eight keys it touches. Every one of them
expresses each classified province exactly once, in exactly one region. The
generator starts from the inherited block, which already covers the whole map,
keeps the `duchies`, `counties`, `kingdoms`, and `regions` entries that reach
only provinces outside the classified range or provinces this run still assigns
to that style, drops the entries whose classified provinces moved to another
style, and then lists explicitly only the ids no retained entry already covers.
Generation fails if a single membership entry straddles the reassignment, and
again before writing unless the emitted blocks reproduce the classification
exactly. Without both, CK3 reports
`Province 'N' lies in multiple graphical regions` and
`Region 'N' has multiple entries for the province 'N'` at world init and
resolves an ambiguous province to whichever style it reaches first, which
decides that province's unit, building, and clothing art.

That reassignment only sees classified provinces, so a membership entry whose
provinces all lie outside the classified range is kept by every inherited block
that names it. Generation therefore also fails when two emitted keys claim the
same entry, unless the winner is recorded — and fails again when a recorded
winner is no longer contested, so the resolution is dropped once upstream
settles. One is recorded today: `world_essos_rhoyne` stays in
`graphical_mediterranean` and leaves `graphical_mena`. AGOT draws the Rhoyne as
Mediterranean through its four southern sub-regions, which now hold the whole
river because the Essos redraw emptied their northern counterparts; Legacy of
Valyria's standalone region file moves the river to MENA, but its own AGOT
bridge loads later and restores the Mediterranean assignment, and Further East
then carries both.

NOW's winning `graphical_siberia` block references `world_westeros_skagos`. That
helper is not visible after the later geographical-region replacements in this
playset, and repeating the reference causes Tiger's fatal
`region world_westeros_skagos not defined` diagnostic. The generator preserves
the helper's intended coverage directly with `d_skagos`, `d_deepdown`, and
`d_driftwood_hall`.

The generated terrain combines:

- the empire-level macro-biomes in `terrain_lore_regions.csv`;
- forest, jungle, arid, snow, and mountain evidence from
  `KnownWorldDetailed.jpg` and `KnownWorldGoogleMaps.jpg`, whose coastlines and
  major landmarks share the CK3 map's full-world projection, resampled to a
  common analysis grid and aggregated by exact province pixels;
- slope from EE's 16-bit heightmap for province-wide hill and mountain relief;
- strong semantic terrain-mask evidence for oasis, floodplain, wetland, jungle,
  frozen, and farmland exceptions; and
- water classes from EE's `default.map`.

The mask classifier remains in the audit as an independent comparison only; its
spatial holdout score is too low to determine final terrain. Graphical-style
generation does not use it. `terrain_decisions.csv` is reserved for explicit
province exceptions; the current lore-rule baseline needs none.

## Lore governments and Ibben

The stage owns the effective history files it emits under `history/titles`,
`history/characters`, and `history/provinces`, plus the effective
`00_agot_character_data_effects.txt` scripted-effect file.

The full-file history overrides are generated because CK3 merges history by
filename and title/character/province key; small fragments cannot safely amend
every dated holder without risking duplicate keys or losing later parent
history. The stage reconstructs the effective LoV/EE source layer in playset
order — with the Further East repair from the earlier stage on top — then makes
only the audited government, culture, faith, legitimacy, and flavor-effect
changes.

Further East ships the last `common/landed_titles/01_landed_titles.txt` in the
playset, so it defines the whole eastern title tree and the stage reads the
effective title set straight from it. Every effective title history resolves
against that tree, so no title filtering is needed.

The effective character-title dispatcher starts with
`Essos Expanded - TempLoV/NOW Compatch`, the final Workshop compatch in the
required chain. This module transforms that dispatcher in place: it preserves
its AGOT mapping semantics, adds the two lore government fallbacks through
AGOT's feudal path, and carries no government lists of its own.

### Lore policy

The source of truth is `assets/lore_governments/government_lore_rules.csv`. Its
confidence and source columns distinguish direct lore from conservative gameplay
interpretations. In summary:

- Dothraki and Jogos Nhai rulers are nomadic; the Dosh Khaleen are theocratic.
- the Red Priesthood is theocratic. Norvos, Lorath, and Qohor have no rules
  here: AGOT owns those cities natively, and Further East ships their history
  files empty. Its `vassal_titles_e_qohor.txt` does hold a Qohorik-culture rump
  kingdom (`k_R43G49B154`, no empire parent), so a file-scoped rule keeps those
  54 holders on the Free City's administrative form rather than letting them
  fall to the engine default.
- the Free Cities use administrative or oligarchic forms according to their
  described ruling institutions;
- the Ghiscari slave cities, Valyrian Freehold, and Qarth use oligarchic
  government;
- Yi Ti uses celestial government for the God-Emperor and meritocratic
  government below him; Leng uses mandala government;
- poorly described or decentralized peoples use conservative tribal, clan, or
  feudal approximations recorded individually in the rules table; and
- explicit pirate, ruin, wilderness, unknown, and landless governments are
  preserved instead of being overwritten by geographic rules.

Ibben deliberately changes at the Doom on `7899.8.14`. Earlier rulers and
provinces retain `ib_ven_god_king`, with the island represented as a feudal
God-King realm. From the Doom onward, rulers and provinces use `ib_ven_sound`,
while the realm uses oligarchic government to represent the Shadow Council. A
later-bookmark God-King configuration is deliberately not used: the God-Kings
ended with the Doom, whereas the Sound/Shadow Council branch describes post-Doom
Ibben.

The audit CSVs record every government assignment, Jogos Nhai culture
correction, Ibben character faith transition, and Ibben province faith
transition.

The Jogos Nhai work splits in two. The scripted-effect side is handled upstream:
the Workshop bridge names `culture:jogos_nhai` in its own flavor branch, so the
generator only asserts that state instead of rewriting it. The character side is
not handled upstream: 277 Jogos rulers and relatives are authored as `nefer`,
and this module corrects them.

## Known upstream defects carried forward

Validation reports 79 errors from the history payload. Every one of them is
inherited verbatim from an upstream file this module re-emits, not introduced
here; the emitted holder, liege, and succession lines are byte-identical to
their sources.

- 16 `duplicate-character`. Further East renamed the Leng rulers into named
  Tengvar empresses in a new `zz_eetlv_leng_empresses.txt` instead of overriding
  the generated `bookmark_chars.txt`, so both definitions load and each id
  becomes two characters. Folding the file in the way this module folds the
  khal-name and bookmark overrides does not work: the renamed rulers are female,
  while Further East's own generated genealogy still references them through
  `father`, which trades 16 duplicates for 20 gender errors. Repairing it needs
  Further East's parentage reconciled, which is out of this module's scope.
- 60 `history` no-holder and 1 `missing-item`. Dated `liege` entries in the LoV
  bridge's `lv_*` files point at titles with no holder at that date.
- 2 `wrong-gender`. Further East's `gen_2495` (Lengoreth) is used as a `mother`
  but carries no `female = yes`.

## Generation

```sh
ck3mm mod generate agot_now_lov_ee_compatch
ck3mm mod generate agot_now_lov_ee_compatch --apply
```

The generator stages output and only promotes a complete declared output set.
`sources.lock.json` records every input file it consumes, so an upstream update
remains visible even when generated bytes do not move. One run performs the
raster merge and the terrain classification together; the world-data feature
cache under `.ignored/cache/agot_now_lov_ee_compatch/` absorbs the repeat cost
of the classifier, and its schema key changes whenever the merged definition
table or any parent does.

`artifacts/heightmap/` and `artifacts/map_objects/` hold unpacked sources for
[the heightmap repack workflow](../../docs/agot-heightmap-repack.md); they are
not declared outputs and are not regenerated by a normal run.

## Re-audit

A pinned-source or pinned-count mismatch fails generation; that failure is the
general re-audit trigger. Re-run the audit after every update to Workshop mods
`2962333032`, `3664900993`, `3403938445`, `3719888822`, `3682802751`,
`3768149491`, or `3773608127`. After an intentional upstream change, review the
source diff before regenerating. The exact files consumed and their hashes are
recorded in `sources.lock.json`.

Specific triggers:

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
- Re-audit the whole map baseline if Further East stops shipping the canonical
  map or diverges from AGOT's province band again.
- `EXPECTED_GAP_COUNT` shrinking is the signal that the terrain stage is
  approaching retirement. When Further East covers the range completely, drop
  it.
- `EXPECTED_NAMED_TARGETS` and `EXPECTED_TITLE_COUNT` pin how much of the range
  Further East has authored; either moving means re-reading its structure before
  trusting the classifier's scope.
- The empire tier is optional. Further East leaves 146 provinces under top-level
  `k_R43G49B154`, mapped to `graphical_western` because Further East already
  assigns them that region upstream. Re-check that mapping if it gains a parent.
- `e_lorath`, `e_norvos`, and `e_qohor` were dropped from both terrain asset
  configs: AGOT owns them natively now and Further East adopted its province
  band, so they left the classified range.
- `e_lhazar` and `e_lower_sarne_dothraki` are each two landmasses under Further
  East v4. Both components take the same style, so the disconnection is accepted
  rather than reviewed province by province.
- The counted history assertions surface the common Further East cases; a
  structural change to how it generates temple provinces needs the faith set
  re-derived by hand.
