# agot_full_playset_compatch — module state

The final integration layer of the AGOT playset. Load position: last, after
`agot_playset_runtime_fixes` and every parent it merges.

## Ownership

Whole-file merges of paths that several parents genuinely contest:

- MFA timing with LoV's coronation, tournament, and dragon-hatching changes;
- the temporary More Dragon Eggs + LoV hatching activity;
- LoV tournament guards, MFA's cooldown, and CaFG's granular county-faith
  conversion in `contest_events.txt` — a superset of the two-file
  [cafg_agot_lov_compatch](../cafg_agot_lov_compatch/README.md) variant, which
  carries the LoV + CaFG merge for playsets without MFA;
- CaFG county/province controls with LoV ruin restoration in the county view;
- AGOT, Additional Models, and COW special-building model detection with the
  NOW-COW 1.0.2 Dunstonbury/Sisterton province remaps, while retaining LoV's
  later graphical-background definitions;
- COW's Dunstonbury/Sisterton province history and localization, while the
  enabled Seasons-of-Valyria Workshop fork supplies its maintained regional
  definitions, repaint actions, map modes, seasonal effects, GUI, situations,
  and localization.

Beyond those merges the generated layer owns eight cross-parent whole-file
overrides: the five seasonal, title-name, and dragon-on-action boundaries below,
plus the three Iron and Salt boundaries described afterward. The regional
cleanup rebases `c_sallydance` and `d_greenbelt` onto NOW's tokens; it also
keeps the Iron Isles specific and covers LoV regions without applying seasons to
wilderness ruins.

`mde_yearly_on_actions.txt` is shipped by both AGOT More Dragon Eggs and AGOT -
More Dragon Events, so the later of them drops the other's file whole. Their
definitions are disjoint — the canon egg-clutch pulse and its game-start
variable on one side, an `agot_yearly_owned_dragon_pulse` extension on the other
— so the override is their union. CK3 merges on_action declarations across
files, and More Dragon Events' pulse is a copy of AGOT's 38 entries plus its own
14, so only the 14 additions are emitted: re-emitting the copy would merge
AGOT's entries a second time and halve the chance of no event firing. The
generator asserts the copied part still matches AGOT's declaration exactly, so
an upstream rebalance fails generation instead of being silently discarded.

Iron and Salt adds three final-integration boundaries. Its `hud.gui` is the
naval and kraken owner, while the Dynamic Family Portrait AGOT bridge owns the
bottom-left family stack and carries More Dragon Eggs' sized dragon portrait.
The generator three-way merges both AGOT-derived deltas and asserts the bridge's
delta is reproduced exactly. Its `map_icon_layer.gui` similarly keeps the kraken
icon while preserving the LoV AGOT bridge's removal of the stale
`find_elder_interaction` datacontext.

The generated `zzz_agot_playset_is_human.txt` is the single final writer for
`is_human`. CK3 resolves scripted-trigger definitions by filename across the
merged VFS, so Great Councils' `zzz_Great_Councils_replaced_triggers.txt` sorts
after Iron and Salt's `zz_kraken_character_triggers.txt` and would otherwise
drop the kraken exclusion. The generator asserts that both parent definitions
remain AGOT's body plus exactly one clause, then emits AGOT's dragon and dummy
guards with the kraken and Great Councils exclusions together. Re-audit when a
later-sorting `is_human` writer joins the playset.

The title-name overrides are NOW's files verbatim plus the three barony names
the NOW-COW province remap needs — `b_breakwater_castle`, `b_breakwater_watch`,
and `b_dordon` — which NOW does not name, so AGOT's originals would otherwise
stand against `zzz_agot_cow_building_model_trigger.txt`'s remapped models. The
generator asserts NOW still leaves those three unnamed, so it fails rather than
shadowing an upstream name. It also repairs the Spanish `d_crackclaw_point`
value, which NOW ships without its closing quote; that repair is keyed to the
exact upstream line and fails once NOW fixes it.

Both files are generated rather than hand-maintained precisely because NOW
rewrites them: a stale hand copy silently drops every title NOW has renamed or
added since the copy was taken, falling those titles back to AGOT's names.

`grandeur_levels.txt` is a single whole-file path that AGOT, Additional Models,
the AGOT+ compatch, LoV, Further East, and the temporary Additional
Models/AGOT+/LoV compatch all claim, so the last of them silently drops every
court scene the others registered. The temporary compatch loads last and
registers a superset of every other claimant's scenes, so no override is needed
here. A scene with no entry never progresses a visual culture level and nothing
reports it at runtime, so the generator asserts that coverage still holds and
fails if the file has to be merged again.

The regional cleanup is written to
`map_data/geographical_regions/north_sans_neck.txt`, the same path the Seasons
fork uses: `replace/` is a plain subfolder there with no engine meaning, so a
copy inside it would load _alongside_ the fork's file and define every shared
region twice.

`zzz_agot_cow_building_model_trigger.txt` is hand-merged rather than generated,
and the COW-AGOT/NOW compatch it takes its province remaps from is not enabled —
that mod's `map_object_data` would shadow the map compatch. It is declared as a
source anyway, hash-pinned like every other, and the generator asserts each
province/building model pair it defines is still carried by the merged trigger.
A remap upstream therefore fails generation rather than leaving the wrong model
on Dunstonbury or Sisterton.

A narrow `can_raid` scripted-rule override also returns false when CK3 evaluates
the rule without a potential-raider character, while delegating unchanged to
AGOT's `can_raid_trigger` for every valid character.

## Repairs owned elsewhere

This module deliberately does not carry runtime repairs. The accompanying narrow
layers repair:

- AGOT+'s CK3 1.19-invalid canon-child creation and dead-character perk
  assignments;
- NOW's unsaved Great Fork title-change scope and optional Summerhall candidate
  comparisons;
- AGOT MPD's startup calculator parameter, variable, and XP-track failures;
- Grand Remembrance's no-character chronicle visibility loop;
- Grand Remembrance's vanilla/RICE-only obituary classification against AGOT's
  removed traits, religion tags, heritages, and elective laws;
- Legacy Of The Dragon's Linux-sensitive lowercase texture path;
- Landed Knights, House Founders, Succession Crisis (including its copied call
  to AGOT-disabled `misc.0001` and its nonexistent Kurdish-culture gate), Any
  New Traditions, and AGOT/LoV tour-event optional-scope failures;
- Great Councils' untyped trait parameters and Suggest Dragon Bonding's stale
  trigger iterators, availability check, and AI modifiers;
- Adventurer's Beneficiary's unset selection variable, title-following artifacts
  without a previous title holder, startup banners for capital-less royal-court
  owners, capital-less startup rulers, and MFA tour pulses dispatched before an
  itinerary stop exists;
- MFA's delayed playdate relay running after its activity scope has expired,
  plus 695 delayed activity-pulse references to a province scope that those
  on-actions do not carry, and five random lists whose fractional weights CK3
  otherwise treats as zero;
- All Men Must Serve's invalid negative `add_gold` service-cost effect;
- Seasons' winter-combat trigger switching through `location` a second time
  after AGOT already entered a province scope, and Seasons manifest
  `2065378484774676314` passing the bare token `autumn` to
  `current_season_autumn` instead of `yes`;
- Deadly CK3 AGOT's clouded-eyes event evaluating environmental weights for
  characters without a current location, and its stale `infirm` definition
  removing the CK3 1.19 trait track used by AGOT;
- AGOT and the temporary Additional Models/AGOT+/LoV compatch evaluating
  court-scene culture triggers without a valid royal-court owner;
- VIET's vanilla-only events, region selectors, and missing heritage helpers;
- the LoV AGOT bridge's invalid county-tier pirate elective assignments;
- Essos Expanded's 54 CK3 1.19-invalid title-history capital tokens; and
- CaFG's four references to AGOT-absent `tradition_steppe_tolerance`, handled
  directly by the CaFG AGOT compatch, plus its 35 cultural-boon MAA types
  removed by AGOT's same-file overrides.

## Generation

```sh
ck3mm mod generate agot_full_playset_compatch
ck3mm mod generate agot_full_playset_compatch --apply
```

The `mod.toml` manifest regenerates the owned outputs from the declared AGOT,
NOW, Seasons-fork, dragon-mod, Iron and Salt, Dynamic Family Portrait, LoV
bridge, and Great Councils sources. It also declares the Additional Models,
AGOT+/LoV compatch, and disabled COW-AGOT/NOW source that back the assertions
above. Its portable source metadata lives here, outside the installed runtime
payload.

## Re-audit

Re-audit whenever any merged parent updates — in particular NOW, the
Seasons-of-Valyria Workshop fork, LoV, MFA, COW, CaFG, Iron and Salt, Dynamic
Family Portrait, or Great Councils — since every owned file is a whole-file
merge that silently absorbs upstream changes.
