# cafg_agot_compatch — module state

Compatibility layer for `[Kei] Culture and Faith Granularity` (`3206891770`) on
`A Game of Thrones` (`2962333032`). Load position: after both parents. Publish
candidate; `descriptor.mod` is at `2.0.0`.

## Ownership

Every payload file is generated. The mechanism differs per content type because
CK3 resolves them differently:

| group                              | files | mechanism                                   |
| ---------------------------------- | ----- | ------------------------------------------- |
| culture/faith rebases              | 5     | `zzz_cafg_agot_*` keyed `common/` overrides |
| vanilla-only content AGOT disables | 5     | exact-path, intentionally empty             |
| CaFG event hooks                   | 11    | three-way merge against vanilla             |
| county view                        | 1     | AGOT's window plus two `using` lines        |

`common/` resolves per object, LIOS by ASCIIbetical filename and independent of
playset position, so `zzz_cafg_agot_*` wins over CaFG's `kei_`/`zz_`/`99_` files
without shadowing the ~200 neighbouring objects those files also define. A CaFG
edit to any untouched object now lands unchanged instead of being reverted by a
stale whole-file copy.

`events/` and `gui/window_*.gui` resolve whole-file, same path only. CK3 rejects
a duplicate event id outright (`Duplicated event ID '<id>' found.`), so there is
no per-event override and those files must carry the parent's complete text.

### Keyed common/ overrides

| output                                        | redefines                                                     |
| --------------------------------------------- | ------------------------------------------------------------- |
| `zzz_cafg_agot_culture_laws_triggers.txt`     | `T_kCAFG_should_start_with_{intolerant,tolerant}_culture_law` |
| `zzz_cafg_agot_faith_laws_triggers.txt`       | `T_kCAFG_should_start_with_{intolerant,tolerant}_faith_law`   |
| `zzz_cafg_agot_cultural_benefits_values.txt`  | `V_kCAFG_cultural_benefits_trigger_chance`                    |
| `zzz_cafg_agot_cultural_boons_effects.txt`    | 6 `E_kCAFG_cultural_boon_tradition_*` effects                 |
| `zzz_cafg_agot_cultural_benefits_effects.txt` | `E_kCAFG_apply_random_cultural_boon`                          |

The generator rebases the whole source file, then diffs it against the source
and emits only the definitions that actually changed, asserting the changed set
against the table above. A CaFG release that edits one of these objects — or
that stops needing the repair — fails generation instead of drifting.

**Tolerance laws.** AGOT does not define the vanilla
`tradition_steppe_tolerance`; the four invalid checks are omitted while every
surviving CaFG criterion is preserved. This prevents the repeated
`has_cultural_tradition` null-target failures seen while initial laws are
selected for rulers.

**Cultural men-at-arms boons.** AGOT and later playset mods replace several
vanilla men-at-arms files by filename. CaFG's cultural-boon tables still
instantiated its generic regiment refill effect for 35 unit types removed from
the resulting database; CK3 post-validates each parameterized instance three
times, producing 105 `is_maa_type` failures. The rebase removes only weighted
branches whose unit type does not exist — 18 valid AGOT/playset gifts remain —
and when all outcomes of a nested random list are invalid, the enclosing
weighted branch goes too, so the boon selection cannot choose an empty outcome.
It also removes eleven branches whose vanilla/TGP traditions AGOT lacks, retains
the pastoralist boon on its plains/steppe conditions without `world_steppe`,
gives the ordinary `pilgrim` trait instead of querying vanilla Islam for
`hajjaj`, and keeps the scholar-official character reward without the vanilla
Han-language and Confucian-education operations.

**Cultural-benefit trigger chance.** CaFG's five-year pulse queried three
traditions and the Chinese heritage pillar that AGOT's replaced culture database
does not define, producing null `has_cultural_tradition` targets. The four
invalid alternatives are removed; the isolationist, fierce-independence,
ruling-caste, cultivated-sophistication, communal, tolerant-law, and xenophilic
modifiers are preserved.

### Disabled vanilla-only content

CaFG reintroduces content AGOT explicitly disables: the vanilla Outremer culture
decision, the Persian-Struggle faith-adoption decision, the Zanj rebellion casus
belli, seven vanilla regional decision effects, and five Persian-Struggle
effects. None can execute under AGOT, and because decision `is_shown` blocks are
evaluated repeatedly the two decisions alone generate roughly 13,500 invalid
database-scope script locations.

A same-path, intentionally empty override is the only mechanism that stops a
file's definitions from loading at all — a single-object `common/` override can
change an object but never remove one, and CK3 parses the original file either
way. The generator asserts each named definition still exists in CaFG's source
before blanking the file, so an upstream removal is reported rather than
silently masked.

### Event merges

Vanilla is the common ancestor of both parents, so each file is merged with
`base = vanilla`, `ours = CaFG`, `theirs = AGOT`. Eight of the eleven merge
without conflict; the remaining four hunks all belong to one class — AGOT
disabled or retargeted the code CaFG hooked — and have explicit resolutions:

| file                            | hunk                                     | resolution                                                                                                                                 |
| ------------------------------- | ---------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| `hold_court_events_general.txt` | `hold_court.6050` / `.6051`              | take AGOT; the resolver fails unless AGOT's side is entirely comments                                                                      |
| `global_religion_events.txt`    | two neighbouring-faith conversion blocks | take AGOT, same assertion                                                                                                                  |
| `stewardship_domain_events.txt` | `stewardship_domain.1073`                | combine CaFG's `E_kCAFG_convert_culture_in_all_county_provinces` wrapper with AGOT's `scope:new_culture` target, keeping AGOT's annotation |

Post-merge counts are asserted per file so a parent update fails loudly:

| file                            | `E_kCAFG_` calls | `#AGOT` markers |
| ------------------------------- | ---------------- | --------------- |
| `hold_court_events_general.txt` | 1                | 63              |
| `contest_events.txt`            | 1                | 24              |
| `culture_emergence_events.txt`  | 2                | 29              |
| `ce1_decision_events.txt`       | 1                | 2               |
| `bp2_yearly_events_6.txt`       | 2                | 12              |
| `epidemic_events.txt`           | 1                | 49              |
| `fp3_misc_decision_events.txt`  | 6                | 6               |
| `global_religion_events.txt`    | 6                | 22              |
| `stewardship_domain_events.txt` | 1                | 24              |
| `faith_conversion_events.txt`   | 1                | 9               |
| `false_conversion_events.txt`   | 3                | 2               |

Converting from the previous hand-merged copies corrected three files that had
gone stale: `culture_emergence_events.txt` regained 13 AGOT
`agot_hairyman_flag_handling` blocks (16 → 29 markers) and lost two
`E_kCAFG_replace_county_culture` hooks current CaFG no longer has,
`bp2_yearly_events_6.txt` regained three AGOT terrain abstractions (9 → 12), and
`faith_conversion_events.txt` regained a guard CaFG had added. All eleven files
stay in the payload: every hooked event is reachable from AGOT's own on_actions
and decisions.

### County view

CaFG's entire county-view delta is two `using` lines; the widgets themselves
live in CaFG's own `gui/kei_cafg_county_view_additions.gui`, which loads
normally. The generator inserts them into AGOT's window with `replace_exact`
anchors, so a source restructure fails rather than silently producing a no-op.
The same code path builds the LoV variant's copy from the LoV AGOT bridge.

## Known incompatibility

`hold_court_events_general.txt` supersedes Better AI Education & Ward Limit BOL
for anyone running both. Events are whole-file only and BOL's copy is
vanilla-derived, so this is not solvable — it is documented in the Workshop
README rather than papered over. BOL does not touch `hold_court.8280`, the only
event this compatch needs.

## Generation

```sh
ck3mm mod generate cafg_agot_compatch
ck3mm mod generate cafg_agot_compatch --apply
```

`mod.toml` declares vanilla, CaFG, and AGOT as portable sources. The variant
module imports this generator directly so the merge strategy, conflict
resolutions, and county-view anchors are defined once — see
[cafg_agot_lov_compatch](../cafg_agot_lov_compatch/README.md).

## Known upstream findings

Twelve ck3-tiger errors are attributed to this module because it is the last
writer of the paths they sit in. All twelve are verbatim parent code that the
merge carries through, so they are not patched here — editing them would fork
vanilla-derived logic into a compatch that does not own it, and every one would
have to be re-resolved on each parent update.

| finding                                                | file                            | present in                |
| ------------------------------------------------------ | ------------------------------- | ------------------------- |
| `temporary-scope` on `scope:rumor_person` (×2)         | `hold_court_events_general.txt` | AGOT and CaFG, same lines |
| `strict-scopes` on `scope:warden` (×2)                 | `bp2_yearly_events_6.txt`       | AGOT and CaFG             |
| `strict-scopes` on `scope:peasant_1`, `scope:location` | `epidemic_events.txt`           | AGOT and CaFG             |
| `strict-scopes` on `scope:county` (×4)                 | `global_religion_events.txt`    | AGOT and CaFG             |
| `unknown-list` `kCAFG_cultures_pool`                   | `fp3_misc_decision_events.txt`  | CaFG                      |
| `unknown-list` `excluded_counties`                     | `stewardship_domain_events.txt` | AGOT and CaFG             |

The `strict-scopes` and `unknown-list` classes are ck3-tiger being conservative
across on-action dispatch and list construction it cannot order; the
`rumor_person` reads are already `?=`-guarded. None of the twelve appears in the
campaign `error.log`, which is the evidence that they do not fire. Report
`kCAFG_cultures_pool` to CaFG — it is the one finding a parent could fix without
diverging from vanilla.

Genuine playset-wide script errors belong in
[agot_playset_runtime_fixes](../agot_playset_runtime_fixes/README.md), not here;
this module's scope is the CaFG/AGOT merge itself.

## Re-audit

Re-audit on any CaFG or AGOT release. Every assertion above is a tripwire, so
the first signal is normally a generation failure rather than a silent
behavioural change. Also confirm source discovery never globs `.bak` — CaFG's
Workshop upload ships a stray `events/dlc/fp3/fp3_misc_decision_events.txt.bak`.
