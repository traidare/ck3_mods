# agot_playset_lov_compatch — module state

The Legacy of Valyria part of the AGOT playset compatch: everything the playset
needs once Legacy of Valyria is enabled, and nothing that also holds without it.
Enable it together with the Legacy of Valyria family; the always-enabled
[agot_playset_compatch](../agot_playset_compatch/README.md) carries the rest.

## Playset compatch modules

| module                         | enable when                                 |
| ------------------------------ | ------------------------------------------- |
| `agot_playset_compatch`        | always                                      |
| `agot_playset_lov_compatch`    | Legacy of Valyria is enabled                |
| `agot_playset_lov_ee_compatch` | Essos Expanded: The Further East is enabled |

Load position: directly after `agot_playset_compatch`, after every parent this
module merges or repairs. Its `ck3-tiger.conf` loads `agot_playset_compatch`
beneath it and omits the Essos Expanded family, so it is validated against the
profile it is written for. Sixteen of its files restate a path
`agot_playset_compatch` also owns; in those, that module's copy is the same
repair or merge computed without Legacy of Valyria, and this one wins wherever
both are enabled.

## Ownership

Whole-file merges of paths that several parents genuinely contest:

- MFA timing with LoV's coronation, tournament, and dragon-hatching changes;
- Travelers' AGOT travel wrappers and imprisonment checks with the LoV bridge's
  optional-scope and restored-Valyria travel behavior;
- A Living Westeros' wedding backgrounds and guest-right rules with MFA timing,
  LoV's optional scopes, and the Long Night's dead-character exclusion;
- More Dragon Eggs' hatching activity, cradling, hatching events, ruins, and
  landless dragonpit handling with LoV's volcano and ruin behavior;
- LoV tournament guards, MFA's cooldown, and CaFG's granular county-faith
  conversion in `contest_events.txt`;
- AGOT, Additional Models, and COW special-building model detection with the
  NOW-COW 1.0.2 Dunstonbury/Sisterton province remaps, while retaining LoV's
  later graphical-background definitions;
- COW's Dunstonbury/Sisterton localization;
- the LoV map: `definition.csv`, the NOW-compatible `adjacencies.csv`,
  `island_region.txt`, the two mapobject files, and the pinned locator files.

The narrow runtime repairs whose effective source is a Legacy of Valyria parent
also live here: the LoV bridge's yurt and noble-family title on-actions, its
support-candidacy appointment guards, the High Septon nickname, the tour-general
guard ordering, the generated accolade squire effect, the Aurion title-gain
fallback, the Additional Models/LoV holding art and generic court scenes, and
`is_diarch_valid`. The first four are the LoV-sourced counterparts of repairs
`agot_playset_compatch` rebases from AGOT's own copies of the same paths.

- **Additional Models illustration cultures (check only):** the Additional
  Models/LoV compatch spells all six `character_view_bg` culture triggers in
  `scripted_illustrations/ingame.txt` as `culture:shadowman`, which AGOT
  defines, so this module ships no copy of that file. Generation asserts AGOT
  still defines `shadowman` and not `shadowmen`, that the parent still carries
  exactly six live references, and that all six use `culture:shadowman`. Any of
  those assertions failing means the file needs to be owned again.

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

`coronation.txt` and `agot_dragon_hatching.txt` carry deltas of this layer's own
on top of their merges: the five coronation holy-site tests are guarded with
`exists = barony.holder`, because CK3 discards the whole clause when the barony
is unheld and a restored or ruined holy site would otherwise read as an invalid
location; and both dragon-hatching variants let AGOT: Canon Continuity spare a
protected host from the accident. `coronation_events.txt` needs no delta of its
own: the LoV bridge already summons the court chaplain through `?=` and a scope
test, which is required because the effect that moves them runs outside the one
that established the activity, and the generator asserts the merge keeps it.

The dragon activity, cradling on-action, and hatching event are direct three-way
merges of current More Dragon Eggs and the current LoV bridge over AGOT. The
activity then receives MFA's timing and Canon Continuity's death guard. Exact
parent deltas ensure the MDE variable-driven settings, LoV volcano locations,
and MFA pacing all survive.

`agot_ruins_events.txt` uses More Dragon Eggs as the whole-file owner and adds
LoV's mine-state save/restore and high-Valyrian conversion exemptions. The
generator proves that those are LoV's complete semantic delta over AGOT before
applying them to MDE. A later-sorting scripted-effect file owns only
`agot_change_dragonpit_status` and its AI counterpart: it keeps MDE's landless
adventurer branch and adds LoV's `lv_has_dragon_pit_building` detection. The
output contains no MDE mover or travel-event calls.

The LoV parent is `lov-agot-bridge` for every file it contributes, including
`contest_events.txt`, where it carries the tournament summary guards that keep
an unset `last_versus_match` out of a comparison.

`wedding.txt` uses A Living Westeros' current AGOT-derived file as one parent
and applies MFA's timing delta over it. MFA's copy restores two vanilla
`terrain = farmlands` tests, so the generator first restores AGOT's
`agot_is_farmlands_terrain` abstraction at both sites. It then asserts the MFA
wait-time option and four relay families, all three Living Westeros ceremony
backgrounds, and every AGOT farmlands predicate.

## Travel and activity-guest merges

Travelers AGOT Compatibility owns AGOT's three travel interface files after
Travelers. The LoV bridge would otherwise replace two of them later in the
playset. The generated `travel_on_actions.txt` keeps Travelers' seven wrapper
on-actions, prison checks, same-location entourage filters, and caravan-master
modifier lifecycle while applying LoV's optional scopes and restored-Valyria
danger gate. The two parents make eight equivalent scope edits with different
comments; the generator normalizes those lines and pins the one overlapping
caravan-master resolution before merging.

The generated `travel_options.txt` keeps every Travelers option and replaces
only `hire_experienced_mercenaries_option` with the LoV version plus Travelers'
prison and leader-availability checks. `agot_travel_options.txt` starts from
current AGOT, retaining the sailing-activity exclusion that the Travelers patch
predates, then adds its prison guard. AGOT's inherited
`owner_modifier_description` field is not documented for travel options and is
recorded in the Tiger baseline while this module is the effective file owner.

Three parents redefine `can_be_activity_guest`, and only the last filename is
effective. `zzz_agot_playset_can_be_activity_guest.txt` starts from the LoV
bridge's current AGOT rule, adds the Long Night's dead-character exclusion, and
appends A Living Westeros' denied-house and guest-right-breaker clauses. The
generator asserts that the Long Night still differs from AGOT only by its dead
test and optional host scope, and that Living Westeros still differs only by its
two final clauses.

Beyond those merges the generated layer owns eight cross-parent whole-file
overrides: the seasonal, title-name, dragon-on-action, and EP3 landing
boundaries below, plus the three Iron and Salt boundaries described afterward.
The regional cleanup rebases `c_sallydance` and `d_greenbelt` onto NOW's tokens;
it also keeps the Iron Isles specific and covers LoV regions without applying
seasons to wilderness ruins.

`mde_yearly_on_actions.txt` is shipped by both AGOT More Dragon Eggs and AGOT -
More Dragon Events, so the later of them drops the other's file whole. Their
definitions are disjoint — MDE's yearly setup, canon egg-clutch pulse, and list
cleanup on one side, an `agot_yearly_owned_dragon_pulse` extension on the other
— so the override is their union. CK3 merges on_action declarations across
files, and More Dragon Events' pulse is a copy of AGOT's 38 entries plus its own
14, so only the 14 additions are emitted: re-emitting the copy would merge
AGOT's entries a second time and halve the chance of no event firing. The
generator asserts the copied part still matches AGOT's declaration exactly, so
an upstream rebalance fails generation instead of being silently discarded.

`common/scripted_effects/07_dlc_ep3_scripted_effects.txt` is a final integration
between current More Dragon Eggs and Seasons. MDE performs its dragonpit
transfer directly in `ep3_become_landed_transfer_effect`; the generated file
contains no `more_dragon_eggs_events.0013` dispatch. The generated file
preserves that MDE delta and Seasons' weather delta against AGOT. The Seasons
text this file also carries for `random_rain_snow_chance_effect` and
`refill_maa_with_provisions_effect` is inert: the Legacy of Valyria compatch
(Workshop `3788296332`) redefines both in
`zzzz_lv_agot_scripted_effect_runtime_overrides_v0_2_2.txt`, and CK3 resolves
duplicate scripted-effect keys by filename traversal order, so `zzzz_` is read
after `07_` regardless of mod load order. LoV's copy omits Seasons' four
`winter_*_modifier` checks, so that Seasons weather branch is already inactive
in this playset independent of this module. Carrying Seasons' text here stays
correct-by-construction; taking the key back would need a file that sorts after
LoV's own `zzzzz_` override, which this module deliberately does not do.

New Personality Events for Children owns the effective
`childhood_on_actions.txt` and retains its personality event while omitting
AGOT's `on_10th_birthday_tame_canon_dragon` dispatch. The generated canon-dragon
birthday file extends `on_10th_birthday` from a unique path, so CK3 merges the
missing AI canon-rider action without replacing either parent's file. The
generator asserts AGOT still owns the expected guarded action and that New
Personality Events has not added the dispatch itself.

Iron and Salt adds three final-integration boundaries. Its `hud.gui` is the
naval and kraken owner, while the Dynamic Family Portrait AGOT bridge owns the
bottom-left family stack and instantiates MDE's dragon portrait. MDE defines
that portrait and its baby, normal, and giant sizes in additive `mde_hud.gui`;
the generator asserts the external type and does not duplicate it in `hud.gui`.
Its `map_icon_layer.gui` similarly keeps the kraken icon while preserving the
LoV AGOT bridge's removal of the stale `find_elder_interaction` datacontext.

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

The Seasons-of-Valyria bridge places `SKIP_VALUE` in a global `Code` block
before `PixelShader`, so vertex and pixel shaders both see it. The bridge owns
`province_effects.fxh`; generation asserts the global placement and the disabled
shader-local declaration.

Seventeen of those regions name a title no parent defines: the Seasons fork
builds its regions from the NOW-Seasons compatch, which names titles at tiers
the current stack does not have — NOW demoted each of them to a barony or a
county, or never had it. CK3 resolves a membership entry by title key, so an
undefined key contributes no province and only logs at world init; the generator
drops those lines by name and fails when the set of them changes, so a new one
is reviewed rather than shipped. `d_yronwood` is the exception: NOW renamed it
`d_greenbelt`, so it is rebased rather than dropped.

Ten regions also name a title a broader entry of the same region already
contains — a duchy under a listed kingdom, or a county under a listed duchy —
which makes CK3 read the province twice and log
`Region 'N' has multiple entries for the province 'N'` once per repeat at world
init. The generator resolves each named title to its provinces through the
landed titles AGOT, NOW, Legacy of Valyria, the LoV AGOT bridge, and Essos
Expanded place, in load order, then drops any entry whose provinces another
retained entry already covers. The prune is subtractive only: a region keeps
exactly the provinces it had, an entry covering nothing is always kept, and
generation fails if a declared title resolves to no province and is not one of
the two titular names that hold none, if the set of removals changes, or if a
region the prune touched still lists a province twice — which would mean its
entries only partly overlap and dropping one would have cost real coverage. Two
Rhoyne regions do overlap that way and are left alone.

`c_heapsdown` is the one overlap the prune cannot see:
`world_barrowlands_seasons` and `world_whiteknife_seasons` both name it and both
belong to `world_group_one`, so the group reads its provinces twice and the
seasons situation carries two claims on them. Barrowlands keeps the county and
the Whiteknife entry is dropped.

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

Rule keys resolve by parse order, not mod position. This module loads after the
Long Night chain, while its `zzz_agot_playset_` file remains the later parsed
definition. Parse order walks every top-level file in `common/scripted_rules/`
in name order and only then its subdirectories, so re-audit if any playset mod
starts shipping rules from a subdirectory or from a name sorting after
`zzz_agot_playset_`.

## Canon-continuity guard

The merged dragon-hatching activity carries one guard. Both
`activity_dragon_hatching` and `activity_dragon_hatching_no_dlc` kill the host
in `on_complete` when the hatching went wrong, and that `limit` also requires
`agot_cc_event_death_protected_trigger = no`, a trigger the AGOT: Canon
Continuity module defines and its own game rule switches off. Guests flagged by
the same catastrophe die in AGOT's hatching events file, which this module does
not own, so they are unaffected.

## Legacy of Valyria runtime repairs

Each entry names the Legacy of Valyria parent it repairs and the diagnosed
failure. Every one is pinned to that parent's effective definition, so a parent
change fails generation rather than producing a stale override.

- **LoV nomad title-gain setup (Workshop 3788296332):** guards yurt main
  buildings with the current vanilla construction requirements. The upstream
  1200/1300 branches attempted to add `yurt_main_03` and `yurt_main_04` without
  checking nomadic authority or the previous building, producing the repeated
  `Domicile owner failed to meet triggered requirements` and
  `Cannot construct an upgrade when previous building has not been built`
  errors. The 900/1100 branches also avoid duplicate main-building additions.
- **LoV noble-family title churn (Workshop 3788296332):** routes both
  `on_vassal_change` calls to `create_noble_family_effect` through
  `agot_playset_request_noble_family_title_effect`, which sets a 30-day
  `agot_playset_nf_title_requested` flag and defers the creation to
  `agot_playset_noble_family.1` (top-liege direct vassal) or `.2` (independent
  administrative ruler) one day later. Each event re-checks the caller's own
  guard before creating anything. Upstream calls the effect synchronously from
  inside an in-flight title/vassal change, so an AI appointment cascade
  re-enters `on_vassal_change` repeatedly within one tick for the same character
  and nests unbounded `x_nf_*` landed-title creation inside that batch.
  Signature:
  `Executing change nested in 1 other change(s), originating from file: CreateNobleFamilyTitle line: 297`
  interleaved with repeated
  `(create_noble_family_effect[...]): Create noble family title for <same character>`.
  Effective last writer for `common/on_action/title_on_actions.txt` is this
  module, which loads after LoV. The repair is narrow because it changes only
  when the creation runs and how often it may be requested; the creation itself
  still calls LoV's unmodified `create_noble_family_effect`, and the deferred
  triggers reproduce the upstream guards verbatim. Re-audit when LoV changes
  either `on_vassal_change` call site or the guards around them; a character who
  legitimately needs a noble-family title but fails the deferred trigger retries
  once the flag expires.
- **LoV Aurion recovery fallback (Workshop 3788296332):** makes the title-gain
  fallback inert. The recovery event remains owned by LoV's travel
  movement/arrival on-actions, while the title-gain copy was attached to every
  title transfer and correlated with repeated unique-title holder collisions.

## Repairs owned elsewhere

The playset's parent-specific repairs that do not depend on Legacy of Valyria
live in `agot_playset_compatch` or in their own narrow modules. Those layers
repair:

- NOW's unsaved Great Fork title-change scope and optional Summerhall candidate
  comparisons;
- AGOT MPD's startup calculator parameter, variable, and XP-track failures;
- Landed Knights, House Founders, Succession Crisis (including its copied call
  to AGOT-disabled `misc.0001` and its nonexistent Kurdish-culture gate), and
  AGOT's tour-event optional-scope failures;
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
- AGOT and Additional Models evaluating court-scene culture triggers without a
  valid royal-court owner; the same guard on the Additional Models/LoV
  compatch's replacement of that file is owned here;
- VIET's vanilla-only events, region selectors, and missing heritage helpers;
- the LoV AGOT bridge's invalid county-tier pirate elective assignments;
- Essos Expanded's 54 CK3 1.19-invalid title-history capital tokens; and
- CaFG's four references to AGOT-absent `tradition_steppe_tolerance`, handled
  directly by the CaFG AGOT compatch, plus its 35 cultural-boon MAA types
  removed by AGOT's same-file overrides.

## Generation

```sh
ck3mm mod generate agot_playset_lov_compatch
ck3mm mod generate agot_playset_lov_compatch --apply
```

The `mod.toml` manifest regenerates the owned outputs from the declared AGOT,
New Personality Events, NOW, Seasons-fork, More Dragon Eggs, dragon-mod, MFA,
CaFG, Iron and Salt, Dynamic Family Portrait, LoV, the LoV bridge, Long Night,
Great Councils, Travelers, Travelers AGOT Compatibility, A Living Westeros, and
vanilla sources. LoV is read only for its landed titles, which the
seasonal-region prune above resolves membership against. It also declares the
Additional Models, AMSB/LoV compatch, and the two disabled mods — the
COW-AGOT/NOW compatch and the LoV AGOT compatch beta — that back the assertions
and merges above. Its portable source metadata lives here, outside the installed
runtime payload.

This module declares no Essos Expanded source: nothing it owns is computed from
that family, and every Essos Expanded parent belongs to
[agot_playset_lov_ee_compatch](../agot_playset_lov_ee_compatch/README.md). The
merges above share
[`tools/agot_playset/final_integration.py`](../../tools/agot_playset/final_integration.py)
with `agot_playset_compatch`, which exposes a core and a LoV entry point over
the same merge helpers, so a parent change is reviewed once and lands in both.

## Re-audit

Re-audit whenever any merged parent updates — in particular AGOT or New
Personality Events' tenth-birthday on-actions, NOW, the Seasons-of-Valyria
Workshop fork, More Dragon Eggs, the LoV AGOT bridge, LoV, MFA, COW, CaFG, Iron
and Salt, Dynamic Family Portrait, or Great Councils, Travelers, Travelers AGOT
Compatibility, A Living Westeros, and the Long Night's diarch or activity-guest
rules. Remove the canon-dragon birthday bridge if the effective parent restores
AGOT's dispatch itself. Drop the three travel overrides if a maintained upstream
compatch incorporates LoV's guards; drop the wedding or activity-guest override
if its parent integrations become native upstream.
