# AGOT Playset Runtime Fixes

Narrow generated repairs for executable-script failures observed in the current
AGOT `0.4.40` playset on CK3 `1.19`.

Load this module after **A Game of Thrones**, **Battle Graphics AGOT
Compatibility Patch**, **AGOT : Seasons of Ice and Fire**, **Mari's AGOT
Makeovers**, **Faster Transitions**, **AGOT Additional Models and Special
Buildings**, **A Landed Knights Mod**, **Expanded Court Position - Search and
Recruit**, **[LOT] Legitimacy Over Time**, **The Red Keep (Hegemony Updates)**,
**Automated Squire Training - AGOT Micro Mod**, **AGOT: The Knighting
Ceremony**, **AGOT: House Founders**, **Succession Crisis**, **Any New
Traditions**, **More Interactive Vassals**, **AGOT Great Councils**, **AGOT -
Suggest Dragon Bonding**, **Adventurer's Beneficiary**, **AGOT: All Men Must
Serve**, and **Deadly ck3 AGOT**. Keep it after **Any New Traditions
Compatibility AGOT** and **TEMPORARY AGOT Additional Models / AGOT+ / LoV
Compatch (1.19 Fixed)** as well. It must also load after **Artifact Manager**,
**Advanced Character Search**, and **Upgrade House Banners 3**, and before the
final **AGOT Personal Playset Compatch**. For the Essos Expanded repair, it must
also load after **Essos Expanded** and **Essos Expanded - TempLoV Compatch**.
The wilderness conversion also requires **Legacy of Valyria - AGOT 0.4.39
Temporary Compatch RC71**, whose colonization effect is the effective last
writer in this playset.

## Repairs

- **Mari's AGOT Makeovers:** removes 1,173 obsolete `gene_GH_marker_*` bookmark
  and DNA entries plus eight references to the removed earrings gene, and
  deletes a stray backtick that made the rest of Aegon V's DNA block fail to
  parse. Removed crown, clothing, and jewelry templates are mapped to current
  AGOT categories, and a malformed Mace Tyrell height value is repaired. The
  effective Viserys bookmark was among the broken portrait files in the retry
  that displayed clothing and hair without a proper character body.
- **Faster Transitions:** rebases its event-transition types onto CK3 1.19 by
  restoring the current fullscreen and compact pivotal-event effect layers and
  the event-transition widget's input-handling property. The Workshop copy is
  still based on the pre-1.19 widget definitions; the 2026-07-31 19:40 retry
  ended in a GUI-thread SIGSEGV while an empty window was visible.
- **Upgrade House Banners 3:** restores the already-localized close option to
  its visible house-banner rarity event. CK3 reported the event as having no
  options, allowing it to open as an empty blocking popup.
- **Additional Models / AGOT+ / LoV:** the rebuilt compatch owns its LoV-aware
  artifact setup.
- **A Landed Knights Mod:** replaces the nonexistent `is_army_owner` trigger and
  makes the father comparison safe for fatherless knights.
- **Expanded Court Position:** replaces obsolete `grumpy`, `depressed`, and
  `merciful` stress-impact keys with current CK3/AGOT traits, including both
  active depression variants.
- **[LOT] Legitimacy Over Time:** prevents its AI sway event from starting a
  scheme when the scripted recipient is missing or has died.
- **The Red Keep (Hegemony Updates):** saves the Hand event scope only when the
  castellan council position has a holder.
- **Automated Squire Training:** repairs five malformed interface-message
  tooltips and removes an `ai_chance` block nested inside a random-list result;
  both forms prevented parts of the automated training event from parsing. Its
  copied AGOT downtime event also displays the knight scope it actually saves,
  rather than an unavailable `second_squire`.
- **AGOT: The Knighting Ceremony:** removes the obsolete `is_triggered_only`
  field from its hidden relay event; CK3 1.19 event files no longer accept that
  field.
- **AGOT: House Founders:** uses optional `top_liege` and `primary_title` scopes
  when checking whether a reveal-bastard story can start. This prevents unlanded
  interaction recipients from repeatedly failing the context switch.
- **Additional Models decision illustrations:** replaces three references to the
  parent's nonexistent `agot_court/throne.dds` with AGOT's existing Iron Throne
  room illustration.
- **Succession Crisis:** makes comparisons with the optional
  `crisis_special_character` scope safe and removes its copied vanilla call to
  `misc.0001`, which AGOT intentionally disables; its copied landless-title
  naming table also follows AGOT by removing the nonexistent Kurdish-culture
  gate. Its terminal handlers now use optional `scope:war` switches, so CK3 can
  build victory, defeat, white-peace, and invalidation tooltips without an
  unavailable war event target.
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
  generation can query these before assigning an owner; the prior unconditional
  scope switch emitted repeated failures.
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
  throne-room exclusions into the compatch's Indian, Japanese, and Southeast
  Asian fallbacks so those generic scenes cannot preempt a dedicated AMSB room.
- **AGOT startup maintenance:** excludes rulers without capital counties from
  maester seeding and rulers without capital provinces from the Westerosi
  starting-legitimacy branch.
- **Chaotic Kurultai succession:** repairs two invalid scopes in AGOT's copy of
  CK3's `09_dlc_mpo_scripted_effects.txt`. The generated override reuses the
  newly created `inheritor_char` for the liege change and compares each county's
  `holder` with the new ruler. Workshop `2962333032` is the effective parent and
  no later enabled mod owns either effect. Only those two top-level effects are
  redefined; their parent-block hashes and both exact replacements are checked.
  Re-audit after AGOT or CK3 changes either nomadic effect.
- **Essos Expanded:** replaces each of its 27 disabled-realm calls to
  `agot_remove_realm_effect` with a direct wilderness initializer. It preserves
  AGOT's noble-title, court, province-pool, landless-company, and title cleanup,
  but converts every county straight through the effective LoV
  `make_settlement_county_wilderness` effect—never through `c_unknown` or
  `Local_Rulers`. The disabled root title is then removed with its now-unlanded
  former holder. Family generation runs after the lobby, only for landed,
  capital-valid rulers in enabled Essos realms; every recursive generation uses
  that valid ruler as its court location. The generator pins the Essos startup
  and family blocks, AGOT removal semantics, and LoV wilderness effect. Re-audit
  when Workshops `3682802751`, `2962333032`, or `3719888822` change those
  blocks.
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
- **LoV pirate succession (Workshop 3719888822):** rebases both the title-gain
  handler and RC70 reconciliation effect from a county floor to the duchy floor
  required by the owned `pirate_succession_law` definition. This preserves the
  earlier LoV law/history repair while preventing invalid county-level
  `add_title_law` calls.
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

The files are generated from current Workshop sources by:

```sh
scripts/generate-agot-playset-runtime-fixes.py
```

The generator checks exact replacement counts and stops when a parent update
invalidates an assumption. Re-run it and review the resulting diff after any
update to Workshop IDs `2962333032`, `3361162762`, `2967263410`, `3713902872`,
`3719888822`, `3319354609`, `3241130652`, `3371298408`, `3621472324`,
`3324579171`, `3349316031`, `3761342990`, `3445965581`, `3676293022`,
`3305687550`, `3662281614`, `3674548216`, `3673468355`, `2886417277`,
`3084203091`, `3225355262`, `3235061780`, `3377641022`, `3462342647`,
`3437814875`, `3709868073`, `3541596590`, `3719888822`, or `2971198450`, and
after CK3 updates that change `04_dlc_ep2_tour_effects.txt`. Re-run it after
updates to `3682802751` because the Essos cleanup validates that parent's game
rules and startup actions, and after updates to `3719888822` because the same
repair is pinned to LoV's effective wilderness-conversion effect. Re-run it
after updates to `3762892081` because the generated court-scene selector follows
that compatch's current room-routing rules.
