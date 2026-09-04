# agot_playset_runtime_fixes — module state

Narrow generated repairs for evidenced executable-script failures across the
current AGOT playset on CK3 `1.19`. Load position: after every repaired parent
and after the Long Night chain and excommunication balance override, but before
the final `agot_full_playset_compatch`. The Tiger dependency stack includes
those non-owned late modules so the Long Night's on-action registrations are
validated alongside this module's repaired registrations in effective order.

## Ownership

Each entry below names the parent it repairs, the diagnosed failure, and — where
the repair depends on being the effective last writer — why that is safe. This
module owns only the files needed for those repairs; genuine cross-mod
integration stays in `agot_full_playset_compatch`.

## Repairs and evidence

### Stability guards

These repairs remove script faults that execute on recurring pulses or during
game start, where an unset scope or a surplus macro argument is dereferenced.
Each is justified by the effective source below, and each is pinned so a parent
change re-raises it.

- **Naval contact stability (Workshop 3772178688, 3781577713):** the contact
  loop writes reciprocal variables through an iterator scope the engine reports
  as weak — `set_variable effect [ This scope doesn't support variables. Scope:`
  … `weak (Character - N)! ]` at `naval_combat_effects.txt` lines 1250-1251 in
  `naval_combat_update_contact_effect`. The repair stores the contact target on
  the root character and re-enters it for both writes, and restores the living
  character gate. Iron and Salt owns the effective event file, so its changes
  are retained. `naval_combat.0100` drives the loop on every naval pulse, so the
  fault recurs for as long as the mods are enabled.
- **Appointment score guards:**
  `appointment_candidate_accumulated_score trigger [ Target title` …
  `doesn't use appointment succession ]`. Every
  `appointment_candidate_accumulated_score(scope:target)` call is wrapped in a
  `trigger_if` on the target title's own `appointment_type_succession` flag,
  with a `trigger_else = { always = no }`. The guard is applied per call rather
  than to the enclosing modifier because CK3 evaluates these triggers eagerly,
  so a surrounding gate does not prevent the score from being computed on a
  title without the law.
- **Beyond-the-Wall queued maintenance:**
  `title_province trigger [ Failed context switch ]`. The repair requires both
  `scope:title` and its province before entering `title_province`, so the queued
  event fails closed instead of dereferencing an unset province.
- **Coastal raiding tooltip:** inlines the ten-percent-of-target-gold,
  minimum-one calculation for both transfers so the tooltip and the applied
  value agree; the stored value is retained only for the follow-up event.
- **Dragon template storage guards:**
  `Failed to fetch variable for 'gene_dragon_fire_color_template' due to not being set`,
  and the same for `gene_dragon_fire_smoke_template`, each preceded by
  `Event target link 'var' returned an unset scope`. The templates start from a
  numeric fallback and read `gl_dragon_variable_storage` entries only inside
  list entries that actually carry them.
- **Adventurer's Beneficiary CB (Workshop 3349316031):**
  `Failed to fetch variable for 'val_beneficiary' due to not being set`. The
  trigger returns false when the attacker has no `val_beneficiary` variable
  instead of dereferencing it. The same file also drops one surplus
  `TITLE_GIVER` argument passed to `ep3_become_landed_warning_effect`. Every
  definition of that effect in the playset declares only `$TITLE$` and
  `$TITLE_RECEIVER$`, and supplying an undeclared parameter is a documented
  crash cause. The removal is anchored to that call: the adjacent
  `ep3_landless_invasion_titles_taken_effect` call does declare `$TITLE_GIVER$`
  and keeps it.
- **Landmarks of Westeros special buildings (Workshop 3692879370):** six reader
  faults in `zzz_landmarks_agot_special_buildings_westeros.txt`, each of which
  drops the field it names before the database sees it. Four buildings cost
  `normal_building_tier_9_cost`, which
  `Failed to read named value or literal from normal_building_tier_9_cost`
  reports because AGOT declares tiers 1 through 8 only; the repair moves them to
  the highest tier AGOT does declare, and asserts that both the undefined tier
  and four uses are still present. One building declares
  `forest_development_growth_faction`, a misspelling of the terrain development
  tag. One declares `fort_level` as a direct child of the building rather than
  inside a `province_modifier`, which `"Unexpected token: fort_level"` reports;
  every other `fort_level` in the file sits in a `province_modifier`, and the
  generator asserts that ratio before wrapping the stray one. The generated file
  is also written with the UTF-8 BOM the reader asks for.
- **Landmarks of Westeros / COW-AGOT compatch (Workshop 3697008412):** the High
  Tide completion effect enters a `holding` scope, which does not exist —
  `"Unknown trigger: holding"` — so the reader discards the block and the castle
  upgrade never runs. A building's `on_complete` runs in the province scope,
  which is how the file's sibling blocks reach `barony.holder`, so the wrapper
  is dropped and the building check made directly. Three further `on_complete`
  blocks do nothing but `trigger_event = agot_cities.5000`, and no mod in the
  playset declares that namespace —
  `trigger_event effect [ Event [agot_cities.5000] not found ]`. Those blocks
  hold nothing else and are removed; the generator asserts that no reference to
  the namespace survives.
- **Kraken events (Workshop 3781577713):**
  `"Unexpected token: override_environment"` in `events/kraken_events.txt`. CK3
  1.19 no longer accepts the field, and the parser rejects the surrounding
  blocks. Removing all 13 lets the events fall back to their normal environment.

### General repairs

- **Voluntary become-adventurer decision:** AGOT owns the decision and More
  Dragon Eggs owns the effective voluntary event. The generated decision
  override consumes the generic `unlock_voluntary_laampdom_trait` flag (so
  Immersive Personalities' gpt_tiger and gpt_wolf traits work) and lets stranded
  landless pirates use the route. It retains AGOT's intentional faith-unlock
  exclusion. The same-path More Dragon Eggs event rebase removes that mod's
  child-succession game-rule gate from the voluntary event while retaining its
  actual succession-event restrictions and every other event change. This is
  static-source evidence; re-audit after Workshop `2962333032`, `3388366564`, or
  `3596393244` changes.
- **Mari's AGOT Makeovers:** removes 1,173 obsolete `gene_GH_marker_*` bookmark
  and DNA entries plus eight references to the removed earrings gene, and
  deletes a stray backtick that made the rest of Aegon V's DNA block fail to
  parse. Removed crown, clothing, and jewelry templates are mapped to current
  AGOT categories, and a malformed Mace Tyrell height value is repaired. The
  effective Viserys bookmark is among the broken portrait files, which display
  clothing and hair without a proper character body.
- **Faster Transitions:** rebases its event-transition types onto CK3 1.19 by
  restoring the current fullscreen and compact pivotal-event effect layers and
  the event-transition widget's input-handling property. The Workshop copy is
  based on the pre-1.19 widget definitions, which end in a GUI-thread SIGSEGV
  while an empty window is visible.
- **Upgrade House Banners 3:** restores the already-localized close option to
  its visible house-banner rarity event. Without it the event has no options and
  opens as an empty blocking popup.
- **Additional Models / AGOT+ / LoV:** the Workshop compatch owns its LoV-aware
  artifact setup, which this module leaves alone; its holding art and
  illustration triggers are repaired separately below.
- **A Landed Knights Mod:** replaces the nonexistent `is_army_owner` trigger and
  makes the father comparison safe for fatherless knights.
- **Expanded Court Position:** replaces obsolete `grumpy`, `depressed`, and
  `merciful` stress-impact keys with current CK3/AGOT traits, including both
  active depression variants.
- **[LOT] Legitimacy Over Time:** prevents its AI sway event from starting a
  scheme when the scripted recipient is missing or has died.
- **The Red Keep (Hegemony Updates):** saves the Hand event scope only when the
  castellan council position has a holder. Its government override replaces
  AGOT's whole government database to add one estate domicile, so whenever that
  copy lags behind AGOT it drops the governments AGOT has added since — a
  missing `lorathi_principality_government` produces
  `change_government effect [ target government type was null ]` during Lorath's
  three-princes game-start setup. This module is therefore the last writer for
  `00_agot_government_types.txt`: it restates current AGOT and re-applies only
  the `lp_feudal_government` domicile line, so the database stays whatever AGOT
  ships. The Red Keep's copy also predates AGOT moving `first_ranger_government`
  into `zz_agot_government_types.txt`, and restating AGOT drops that stale
  second definition. Generation fails if The Red Keep's file ever holds a line
  current AGOT does not, since such an edit is one this rebase would discard.
- **Essos Expanded: The Further East:** rebases its sole
  `zz_eetlv_gov_dev_on_actions.txt` startup owner while omitting only
  `zz_eetlv_gov_dev_effect` and `zz_eetlv_cannibal_confederation_effect`. The
  exact repeated signature is
  `change_government effect [ Trying to set illegal government ]`: all Leng,
  Moraq, Norvos, and Cannibal Sands assignments are rejected. Workshop
  `3768149491` is the only provider of the source on-action; this generated
  module is its effective last writer. The quarantine is narrow because
  development, innovations, buildings, roads, culture conversions, claims,
  armies, and all unrelated setup calls remain intact. The Cannibal Sands
  confederation cannot form when its prerequisite nomad conversions are all
  rejected. Re-audit after Workshop `3768149491` changes or when those
  governments are moved to valid static holding/title history.
- **Automated Squire Training:** repairs five malformed interface-message
  tooltips and removes an `ai_chance` block nested inside a random-list result;
  both forms prevented parts of the automated training event from parsing. Its
  copied AGOT downtime event also displays the knight scope it actually saves,
  rather than an unavailable `second_squire`.
- **AGOT: The Knighting Ceremony:** removes the obsolete `is_triggered_only`
  field from its hidden relay event; CK3 1.19 event files do not accept that
  field.
- **AGOT: House Founders:** uses optional `top_liege` and `primary_title` scopes
  when checking whether a reveal-bastard story can start. This prevents unlanded
  interaction recipients from repeatedly failing the context switch. Its dynasty
  on-actions are also rebased onto current AGOT while preserving the human
  dynasty-name event. The exact repeated signature is
  `Caught signal 11 (SIGSEGV)` with the faulting worker at
  `common/on_action/dynasty_on_actions.txt (on_became_dynasty_head)`. Making its
  effect empty still registered the same faulting effect chain, so the generated
  last writer now queues a hidden cleanup event one day later instead of
  synchronously removing `denounced` and `disinherited`.
- **Additional Models decision illustrations:** replaces three references to the
  parent's nonexistent `agot_court/throne.dds` with AGOT's existing Iron Throne
  room illustration.
- **Additional Models holding art:** binds the 565 `@holding_illustration_*`
  references in the compatch's merged `zz_am_lov_nv_holding_art.txt` to literal
  art paths. `@` constants are file-scoped, and the merge folds castle, city,
  and temple keys into one file that declares none, so every reference reached
  the VFS as its own literal name and failed on each frame that drew a holding.
  AGOT binds the same constant names to different art per holding type, so each
  reference resolves against the AGOT file its block came from: 292 castle and
  273 city, with temple blocks using none. The generator asserts those counts,
  that every target file exists, and that no constant survives in the output.
- **Additional Models illustration cultures:** removes six `culture:shadowmen`
  references from `scripted_illustrations/ingame.txt`. The culture does not
  exist under any spelling the playset resolves, and `character_view_bg`
  re-evaluates on every portrait redraw, so each one cost a failed lookup per
  frame. Every line sits in an `OR` beside the `shadowman` line it misspells,
  which the generator asserts before dropping it, so the intended coverage is
  unchanged.
- **Succession Crisis:** makes comparisons with the optional
  `crisis_special_character` scope safe and removes its copied vanilla call to
  `misc.0001`, which AGOT intentionally disables; its copied landless-title
  naming table also follows AGOT by removing the nonexistent Kurdish-culture
  gate. Its terminal handlers now use optional `scope:war` switches, so CK3 can
  build victory, defeat, white-peace, and invalidation tooltips without an
  unavailable war event target. Its `succession_crisis_misc.0012` handler now
  captures a candidate before removing their old war side, then joins only if
  they are still absent from the crisis war and not at war with a current
  participant; this removes the repeated invalid `add_attacker` and
  `add_defender` loop.
- **More Interactive Vassals:** rechecks all participants immediately before
  each direct or indirect civil-war join. A vassal already in that war, or at
  war with any current participant, is skipped rather than passed to
  `add_attacker` or `add_defender`; its three references to the unavailable
  `has_warden_contract` flag are explicitly false on CK3 1.19.
- **AGOT war AI:** returns a neutral house-relation score when either war
  participant has no house, before evaluating the original house-relation
  scoring logic.
- **Artifact Manager:** repairs four invalid scripted-GUI saved-scope
  declarations, inlines a bare trigger that could not be defined in a
  scripted-GUI file, and uses the current optional global-variable scope syntax.
  It also removes 49 upgrade checks for vanilla artifact modifiers unavailable
  under AGOT. These parse and database failures disabled several artifact
  upgrade, combination, and inventory controls. The repair also fixes two
  malformed variable removals, the distribution GUI's saved-scope declaration,
  batch-sale artifact/owner scopes, named repair-cost scopes, optional
  giveaway-recipient guards, and the batch-combination routine's invalid `else`
  syntax. Its direct-upgrade routine now targets AGOT's actual maximum prowess
  modifier and skips vanilla-only merit and Confucian modifier families absent
  from AGOT. The distribution event now uses current stress-impact constants and
  a typed saved scope for its highlighted family portrait.
- **Advanced Character Search:** makes its generated filters compatible with
  AGOT's total-conversion database: 36 references to unavailable
  imperial-minister titles are removed, vanilla-only trait/religion/minister
  filters are made explicitly false (with inverse filters true), and unavailable
  accolade traditions and innovations are removed from otherwise valid
  alternatives. Existing AGOT-compatible filters and numeric GUI filter indices
  are preserved. Its main window is now hidden until a valid player exists, and
  its filter state is initialized from the guarded in-game scripted GUI rather
  than only from a widget that can be created before the game state. The
  initializer's malformed global-list iterator is repaired as well.
- **Any New Traditions:** makes dynasty-modifier checks safe for characters
  without a dynasty, repairs two malformed `OR` blocks, and restores four
  renown-grant effects that incorrectly used a comparison operator.
- **AGOT Great Councils:** passes typed `trait:` values to current AGOT
  religious scripted triggers and uses AGOT's current High Septon check.
- **AGOT - Suggest Dragon Bonding:** uses trigger iterators while finding
  available dragons, replaces the removed busy-event trigger, and repairs
  diplomacy/dread AI acceptance modifiers.
- **AGOT/LoV tour events:** prevents dinner, cultural-festival, tour-general,
  and Az tour events from evaluating or firing without their required
  `stop_host_scope` and `visiting_liege` saved scopes.
- **Adventurer's Beneficiary:** verifies that the selected-beneficiary variable
  exists before comparing the interaction recipient with it.
- **AGOT: All Men Must Serve:** replaces its CK3 1.19-invalid negative
  `add_gold` service fee with the positive-value `remove_short_term_gold`
  deduction effect.
- **Artifact succession:** skips title-following ownership logic when a newly
  created title has no previous holder.
- **Artifact feature patterns:** evaluates the owner-faith restrictions on 12
  AGOT decorative-pattern triggers only after an artifact owner exists. Artifact
  generation can query these before assigning an owner, where an unconditional
  scope switch fails repeatedly.
- **Startup banners:** falls back to AGOT's existing location-less
  created-banner path when a royal-court owner has no capital province, while
  still creating and granting the house or dynasty banner.
- **Deadly CK3 AGOT / clouded eyes:** retains its health-event weights while
  skipping the glare, sunlight, and shade modifiers for characters without a
  current location.
- **Deadly CK3 AGOT / infirm:** restores the current named `infirm` XP track and
  age-related flags while retaining Deadly CK3's harsher static penalties.
- **Court-scene culture selection:** preserves AGOT's named throne rooms and the
  temporary Additional Models/AGOT+/LoV compatch's generic room routing, but
  returns false instead of evaluating character triggers when CK3 transiently
  supplies no royal-court owner. It also carries Additional Models' current
  throne-room exclusions into the compatch's own copies of those scenes, so no
  generic room can preempt a dedicated AMSB one. The compatch replaces
  Additional Models' whole scene-culture file, so the guarded set is read back
  out of Workshop `3319354609` per scene name rather than listed here; a scene
  gaining or losing its exclusion upstream follows automatically, and a guarded
  scene the compatch does not define fails generation.
- **AGOT startup maintenance:** excludes rulers without capital counties from
  maester seeding and rulers without capital provinces from the Westerosi
  starting-legitimacy branch.
- **Chaotic Kurultai succession:** repairs two invalid scopes in AGOT's copy of
  CK3's `09_dlc_mpo_scripted_effects.txt`, and guards all 17 direct
  `primary_title.previous_holder` accesses in the chaotic-Kurultai event file
  (including `mpo_chaotic_kurultai_succession.0005`). The generated overrides
  reuse the newly created `inheritor_char` for the liege change, compare each
  county's `holder` with the new ruler, and fail closed when the parent title
  has no previous holder. Workshop `2962333032` is the effective parent and no
  later enabled mod owns those scripts.
- **Better AI Education & Ward Limit BOL:** rebases its stale whole-file vanilla
  copies on the effective AGOT interactions, nickname effect, and travel event.
  The intended ward limit, education AI, and language-tutor changes remain, but
  invalid vanilla culture/religion branches are never loaded; AGOT's
  deliberately disabled university paths remain disabled. BAIE's
  `medium_gold_value` retunes are the one delta not replayed: they retarget gold
  gates AGOT has already commented out, so they have no parent line to apply to.
- **Character UI Overhaul / Hometowns:** guards birth-location and birthplace
  access before dereferencing those scopes, removes a county modifier only when
  the saved birthplace is known, and replaces its vanilla historical-title
  mapping event with an inert same-id event. New AGOT births retain the safe
  Hometowns setup without evaluating absent historical title IDs.
- **Essos Expanded:** replaces its disabled-realm calls to
  `agot_remove_realm_effect` with a direct wilderness initializer. It preserves
  AGOT's noble-title, court, province-pool, landless-company, and title cleanup,
  but converts every county straight through the effective LoV
  `make_settlement_county_wilderness` effect—never through `c_unknown` or
  `Local_Rulers`. The disabled root title is then removed with its now-unlanded
  former holder. Family generation runs after the lobby, only for landed,
  capital-valid rulers in enabled Essos realms; every recursive generation uses
  that valid ruler as its court location. Former county holders now lose their
  court regardless of how many counties they held, matching AGOT's removal
  semantics. Empires Essos Expanded still lists but Further East's landed titles
  no longer define — Lorath, Norvos, and Qohor, which AGOT covers natively — are
  dropped from the dispatcher, the removal actions, and the family filter, so no
  game-start effect dispatches at an undefined title. The surviving set is read
  from Workshop `3768149491`'s landed titles rather than listed, and generation
  fails if it stops defining most Essos empires. The generator pins the Essos
  startup and family blocks, AGOT removal semantics, and LoV's wilderness
  effect. Re-audit when Workshops `3682802751`, `2962333032`, or `3719888822`
  change those blocks.
- **Tour pulse:** makes the vanilla monthly pulse a no-op when MFA relays it
  before the activity has a `stop_host` variable, rather than dereferencing the
  missing itinerary stop.
- **LoV nomad title-gain setup (Workshop 3719888822):** guards yurt main
  buildings with the current vanilla construction requirements. The upstream
  1200/1300 branches attempted to add `yurt_main_03` and `yurt_main_04` without
  checking nomadic authority or the previous building, producing the repeated
  `Domicile owner failed to meet triggered requirements` and
  `Cannot construct an upgrade when previous building has not been built`
  errors. The 900/1100 branches also avoid duplicate main-building additions.
- **LoV noble-family title churn (Workshop 3719888822):** routes both
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
- **Dragon Wives marriage modifiers (Workshop 3541596590):** replaces two
  unguarded `var:legitimate_house` comparisons with AGOT's
  `title_is_not_held_by_legitimate_house` trigger, which verifies both variables
  before comparing them. This removes the invalid-left-side,
  failed-variable-fetch, and unset-event-target cascade seen in marriage AI.
- **AGOT court event `court_events.3020`:** removes the optional
  `scope:physician ?=` block from `court_scene.roles`. Optional scope syntax is
  valid in event effects but not in court-scene role declarations; the physician
  and architect descriptions/cleanup remain conditional.
- **Same-path event rebases:** the court-events, AGOT artifact, and Deadly CK3
  health repairs replace their parent paths with complete generated files,
  retaining every sibling event while changing only the diagnosed block. This is
  required because CK3 replaces event files by relative path; the generator
  checks the parent namespace and exact replacement count before writing them.
- **LoV Aurion recovery fallback (Workshop 3719888822):** makes the RC61
  title-gain fallback inert. The recovery event remains owned by LoV's travel
  movement/arrival on-actions, while the title-gain copy was attached to every
  title transfer and correlated with repeated unique-title holder collisions.
- **COW-AGOT province setup (Workshop 2971198450):** removes a Lordsport
  holder-change block whose `change` object is commented out but whose
  `scope:change` is still dereferenced during game start. It also rebases COW's
  stale trade-port, ironwood, Cheesemonger, Bear Island, and Harlaw mines
  identifiers onto current AGOT definitions; Lordsport's current holder and
  province setup remain intact.
- **MPO nomad event guard:** changes AGOT's two MPO nomad event references to
  `the_great_steppe` into optional scope switches. AGOT deliberately disables
  that situation, so the events fail closed instead of evaluating an unset
  scope.

## Canon-enforcement guards

Four files this module already owns carry the guards for deaths a character does
not choose: `travel_events.4003/4007/4032` in
`travel_events/travel_events_james.txt`, `kraken.0100/1105` in
`kraken_events.txt`, the failed treatments and mysterious deaths
`health.3107/3200/4105/6200/6203/6204/6207/6208` in `health_events.txt`, and the
drinking, dessert and choking accidents `host_dinner_events.1002/3060/3061/3080`
in `tour_phase_host_a_dinner.txt`.

`guard_event_deaths` in `runtime_fixes/common.py` wraps every `death` in a named
event in `agot_ce_event_death_protected_trigger = no` and asserts how many it
found, so a parent release that adds a lethal outcome fails generation instead
of leaving it unguarded. The trigger is defined by the AGOT: Canon Enforcement
module and switched off by that module's own game rule. Murder, execution,
sacrifice and witch-burning deaths in the same files are chosen deaths and stay
reachable.

## Generation

The files are generated from current Workshop sources by:

```sh
ck3mm mod generate agot_playset_runtime_fixes
ck3mm mod generate agot_playset_runtime_fixes --apply
```

The `mod.toml` manifest declares this module's parents and destination-specific
staged generator. It checks exact replacement counts and stops when a parent
update invalidates an assumption.

## Re-audit

Individual repairs above carry their own narrower triggers. In general, re-run
the generator and review the resulting diff after any update to Workshop IDs
`2962333032`, `3388366564`, `3596393244`, `3361162762`, `2967263410`,
`3713902872`, `3719888822`, `3319354609`, `3241130652`, `3371298408`,
`3621472324`, `3324579171`, `3349316031`, `3761342990`, `3445965581`,
`3676293022`, `3305687550`, `3662281614`, `3674548216`, `3673468355`,
`2886417277`, `3084203091`, `3225355262`, `3235061780`, `3377641022`,
`3692879370`, `3697008412`, `3462342647`, `3437814875`, `3709868073`,
`3541596590`, `3719888822`, or `2971198450`, `3732116186`, or `2519175282`, and
after CK3 updates that change `04_dlc_ep2_tour_effects.txt`. Re-run it after
updates to `3682802751` because the Essos cleanup validates that parent's game
rules and startup actions, and after updates to `3719888822` because the same
repair is pinned to LoV's effective wilderness-conversion effect. Re-run it
after updates to `3762892081` because the generated court-scene selector follows
that compatch's current room-routing rules.

The stability guards are pinned by file or top-level block hash and fail closed
when a parent changes. Re-run the generator and review the diff after any update
to Workshop `3772178688` (CK3 Naval Combat) or `3781577713` (AGOT Iron and
Salt); the latter owns both the effective naval event file and the kraken
events. Re-run it after updates to `3349316031`, whose Adventurer's Beneficiary
CB carries both the beneficiary guard and the `TITLE_GIVER` removal, and after
CK3 or AGOT updates that change `ep3_become_landed_warning_effect` or
`ep3_landless_invasion_titles_taken_effect`, because the removal depends on
which parameters those effects declare.
