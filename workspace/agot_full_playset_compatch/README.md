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
- AGOT, Additional Models, and COW special-building model detection with the
  NOW-COW 1.0.2 Dunstonbury/Sisterton province remaps, while retaining LoV's
  later graphical-background definitions;
- COW's Dunstonbury/Sisterton province history and localization, while the
  enabled Seasons-of-Valyria Workshop fork supplies its maintained regional
  definitions, repaint actions, map modes, seasonal effects, GUI, situations,
  and localization.

## Activity merges

Much Faster Activities regenerates its overrides from vanilla, so each of its
files carries vanilla lines AGOT had already replaced alongside the timing edits
that are the mod's purpose. Both are its delta as `git merge-file` sees it, and
the vanilla ones conflict with every AGOT-derived parent. `tournament.txt`
therefore restores AGOT's text for the two the file contains — the jungle
terrain test AGOT abstracts behind `agot_is_jungle_terrain`, and the archery
bonus AGOT disables with the tradition itself — before merging, and asserts each
is present exactly once, so a release that drops or moves either fails
generation.

The merge base is AGOT for every parent that derives from AGOT, and vanilla for
CaFG, which edits vanilla and never saw AGOT. `contest_events.txt` needs both,
one after the other. Each merge asserts that the parent's textual delta reaches
the output unchanged, so an upstream release that starts touching lines another
parent also touches fails rather than silently dropping one side.

`coronation.txt`, `coronation_events.txt`, and `agot_dragon_hatching.txt` carry
deltas of this layer's own on top of their merges: the five coronation holy-site
tests are guarded with `exists = barony.holder`, because CK3 discards the whole
clause when the barony is unheld and a restored or ruined holy site would
otherwise read as an invalid location; the court chaplain is summoned through
`?=` and a scope test, because the effect that moves them runs outside the one
that established the activity; and both dragon-hatching variants let AGOT: Canon
Continuity spare a protected host from the accident.

The LoV parent is the enabled `lov-agot-bridge` for every file except
`contest_events.txt`, which takes the unenabled `lov-agot-compatch` beta — the
only parent carrying the tournament summary guards that keep an unset
`last_versus_match` out of a comparison.

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

New Personality Events for Children owns the effective
`childhood_on_actions.txt` and retains its personality event while omitting
AGOT's `on_10th_birthday_tame_canon_dragon` dispatch. The generated canon-dragon
birthday file extends `on_10th_birthday` from a unique path, so CK3 merges the
missing AI canon-rider action without replacing either parent's file. The
generator asserts AGOT still owns the expected guarded action and that New
Personality Events has not added the dispatch itself.

Iron and Salt adds three final-integration boundaries. Its `hud.gui` is the
naval and kraken owner, while the Dynamic Family Portrait AGOT bridge owns the
bottom-left family stack and carries More Dragon Eggs' sized dragon portrait.
The generator three-way merges both AGOT-derived deltas and asserts the bridge's
delta is reproduced exactly. Its `map_icon_layer.gui` similarly keeps the kraken
icon while preserving the LoV AGOT bridge's removal of the stale
`find_elder_interaction` datacontext.

The merged `hud.gui` carries Iron and Salt's Dragonlord Regime main tab
unchanged, so the tiger baseline records
`file gfx/interface/hud/maintab_dragonlord_oligarchy.dds does not exist` against
this module as the effective last writer. The tab is gated on
`dragonlord_oligarchy_government`, which no mod in the playset defines, so it
cannot become visible and the missing icon is never drawn. Drop the baseline
entry and re-audit the tab once a mod defining that government joins the
playset.

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
LoV, Further East, and the temporary Additional Models/LoV compatch all claim,
so the last of them silently drops every court scene the others registered. The
temporary compatch loads last and registers a superset of every other claimant's
scenes, so no override is needed here. A scene with no entry never progresses a
visual culture level and nothing reports it at runtime, so the generator asserts
that coverage still holds and fails if the file has to be merged again.

The regional cleanup is written to
`map_data/geographical_regions/north_sans_neck.txt`, the same path the Seasons
fork uses: `replace/` is a plain subfolder there with no engine meaning, so a
copy inside it would load _alongside_ the fork's file and define every shared
region twice.

Ten of those regions also name a title a broader entry of the same region
already contains — a duchy under a listed kingdom, or a county under a listed
duchy — which makes CK3 read the province twice and log
`Region 'N' has multiple entries for the province 'N'` once per repeat at world
init. The generator resolves each named title to its provinces through the
landed titles AGOT, NOW, Legacy of Valyria, the LoV AGOT bridge, and Essos
Expanded place, in load order, then drops any entry whose provinces another
retained entry already covers. The prune is subtractive only: a region keeps
exactly the provinces it had, an entry covering nothing is always kept, and
generation fails if a named title resolves to no province, if the set of
removals changes, or if a region the prune touched still lists a province twice
— which would mean its entries only partly overlap and dropping one would have
cost real coverage. Two Rhoyne regions do overlap that way and are left alone.

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

The generated `zzz_agot_playset_is_diarch_valid.txt` is the single final writer
for `is_diarch_valid`. Two parents extend AGOT's one-line rule and only one
definition of a rule key survives: the LoV AGOT bridge wraps AGOT's call in an
`exists = this` guard inside its `00_rules.txt`, and AGOT: The Long Night & Azor
Ahai adds a Night's Watch clause in `zz_ln_diarch_rules.txt`, which parses later
and drops the guard. The generator asserts AGOT's rule is still a bare
`is_diarch_valid_trigger` call, that the bridge's is still exactly that call
wrapped in its guard, and that the Long Night's is still AGOT's plus one
`trigger_if`; it then nests the Long Night's clause inside the guarded branch.
The bridge's `is_diarch_able` guard needs no entry, because only the bridge and
AGOT define that key and both do so in `00_rules.txt`, where load order decides.

Rule keys resolve by parse order, not mod position. This module now also loads
after the Long Night chain, while its `zzz_agot_playset_` file remains the later
parsed definition. Parse order walks every top-level file in
`common/scripted_rules/` in name order and only then its subdirectories, so
re-audit if any playset mod starts shipping rules from a subdirectory or from a
name sorting after `zzz_agot_playset_`.

`history/provinces/replace/00_k_the_vale_prov.txt` takes the same path as AGOT
Nobility of Westeros' own file, so it shadows that file whole rather than
merging with it. The Sisterton culture and holding change is this layer's
intended delta; every other province entry must therefore reproduce Nobility of
Westeros', or the province silently falls back to AGOT's — `2326` to
`holding = none`, the holdingless-barony case the Bloodlines game-start guard
exists to work around. The file is generated from that parent and carries only
the Sisterton delta, so an entry the parent gains, drops, or re-numbers follows
without an audit, and a change to the three provinces the delta names fails
generation.

## Canon-continuity guard

The merged dragon-hatching activity carries one guard. Both
`activity_dragon_hatching` and `activity_dragon_hatching_no_dlc` kill the host
in `on_complete` when the hatching went wrong, and that `limit` now also
requires `agot_cc_event_death_protected_trigger = no`, a trigger the AGOT: Canon
Continuity module defines and its own game rule switches off. Guests flagged by
the same catastrophe die in AGOT's hatching events file, which this module does
not own, so they are unaffected.

## Repairs owned elsewhere

This module deliberately does not carry runtime repairs. The accompanying narrow
layers repair:

- NOW's unsaved Great Fork title-change scope and optional Summerhall candidate
  comparisons;
- AGOT MPD's startup calculator parameter, variable, and XP-track failures;
- Landed Knights, House Founders, Succession Crisis (including its copied call
  to AGOT-disabled `misc.0001` and its nonexistent Kurdish-culture gate), and
  AGOT/LoV tour-event optional-scope failures;
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
- AGOT and the temporary Additional Models/LoV compatch evaluating court-scene
  culture triggers without a valid royal-court owner;
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
New Personality Events, NOW, Seasons-fork, dragon-mod, MFA, CaFG, Iron and Salt,
Dynamic Family Portrait, LoV, the LoV bridge, Essos Expanded, Long Night, Great
Councils, and vanilla sources. LoV and Essos Expanded are read only for their
landed titles, which the seasonal-region prune above resolves membership
against. It also declares the Additional Models, AMSB/LoV compatch, and the two
disabled mods — the COW-AGOT/NOW compatch and the LoV AGOT compatch beta — that
back the assertions and merges above. Its portable source metadata lives here,
outside the installed runtime payload.

## Re-audit

Re-audit whenever any merged parent updates — in particular AGOT or New
Personality Events' tenth-birthday on-actions, NOW, the Seasons-of-Valyria
Workshop fork, LoV, MFA, COW, CaFG, Iron and Salt, Dynamic Family Portrait, or
Great Councils, and the Long Night's diarch rule. Remove the canon-dragon
birthday bridge if the effective parent restores AGOT's dispatch itself.
