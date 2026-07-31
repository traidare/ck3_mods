# AGOT Playset Runtime Fixes

Narrow generated repairs for executable-script failures observed in the current
AGOT `0.4.40` playset on CK3 `1.19`.

Load this module after **AGOT Additional Models and Special Buildings**, **A
Landed Knights Mod**, **Expanded Court Position - Search and Recruit**, **[LOT]
Legitimacy Over Time**, **The Red Keep (Hegemony Updates)**, **Automated Squire
Training - AGOT Micro Mod**, **AGOT: The Knighting Ceremony**, **AGOT: House
Founders**, **Succession Crisis**, **Any New Traditions**, **AGOT Great
Councils**, **AGOT - Suggest Dragon Bonding**, **Adventurer's Beneficiary**,
**AGOT: All Men Must Serve**, and **Deadly ck3 AGOT**. Keep it after **Any New
Traditions Compatibility AGOT** and **TEMPORARY AGOT Additional Models / AGOT+ /
LoV Compatch (1.19 Fixed)** as well. It must also load after **Artifact
Manager** and **Advanced Character Search**, and before the final **AGOT
Personal Playset Compatch**.

## Repairs

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
  room illustration. The missing path produced 578 asset errors in the
  2026-07-31 crash bundle.
- **Succession Crisis:** makes comparisons with the optional
  `crisis_special_character` scope safe and removes its copied vanilla call to
  `misc.0001`, which AGOT intentionally disables; its copied landless-title
  naming table also follows AGOT by removing the nonexistent Kurdish-culture
  gate.
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
  are preserved.
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
- **Tour pulse:** makes the vanilla monthly pulse a no-op when MFA relays it
  before the activity has a `stop_host` variable, rather than dereferencing the
  missing itinerary stop.

The files are generated from current Workshop sources by:

```sh
scripts/generate-agot-playset-runtime-fixes.py
```

The generator checks exact replacement counts and stops when a parent update
invalidates an assumption. Re-run it and review the resulting diff after any
update to Workshop IDs `2962333032`, `3361162762`, `2967263410`, `3713902872`,
`3719888822`, `3319354609`, `3241130652`, `3371298408`, `3621472324`,
`3324579171`, `3349316031`, `3761342990`, `3445965581`, `3676293022`,
`3305687550`, `3662281614`, `3674548216`, `3673468355`, `2886417277`, or
`3084203091`, and after CK3 updates that change `04_dlc_ep2_tour_effects.txt`.
Re-run it after updates to `3762892081` as well, because the generated
court-scene selector follows that compatch's current room-routing rules.
