# AGOT Playset Compatch

This combines:

- MFA timing with LoV's coronation, tournament, and dragon-hatching changes;
- the temporary More Dragon Eggs + LoV hatching activity;
- LoV tournament guards, MFA's cooldown, and CaFG's granular county-faith
  conversion in `contest_events.txt`;
- CaFG county/province controls with LoV ruin restoration in the county view;
- current NOW 1.2.4 titles with COW's Dunstonbury/Sisterton expectations,
  including corrected province 2709/2716/2717 history and localization;
- AGOT, Additional Models, and COW special-building model detection with the
  NOW-COW 1.0.2 Dunstonbury/Sisterton province remaps, while retaining LoV's
  later graphical-background definitions;
- LoV + NOW + Seasons regional definitions, repaint actions, map modes, seasonal
  effects, and FX, with AGOT 0.4.40's shader-wide skip threshold retained for
  both pixel- and vertex-shader consumers.

The accompanying narrow runtime layers also repair:

- AGOT+'s CK3 1.19-invalid canon-child creation and dead-character perk
  assignments;
- NOW 1.2.4's CK3 1.19-invalid effects, game-start scoping, and optional
  Summerhall candidate comparisons;
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
- LoV RC65's invalid county-tier pirate elective assignments;
- Essos Expanded's 54 CK3 1.19-invalid title-history capital tokens; and
- CaFG's four references to AGOT-absent `tradition_steppe_tolerance`, handled
  directly by the CaFG AGOT compatch, plus its 35 cultural-boon MAA types
  removed by AGOT's same-file overrides.

The rebase also repairs current-parent defects encountered during validation:
NOW's `d_lychester` creation check still referenced removed `d_medway`; the
NOW/Seasons region merge put duchy `d_ironwater` in a county list and retained
removed county `c_sunvane`. These now resolve to `d_lychester`, `c_ironwater`,
and `c_brittlebush`. A narrow `can_raid` scripted-rule override also returns
false when CK3 evaluates the rule without a potential-raider character, while
delegating unchanged to AGOT's `can_raid_trigger` for every valid character.

## Required load order

1. `VIET 1.3.0 - AGOT CK3 1.19 Runtime Rebase`, immediately after VIET
2. `AGOT+ 1.0.0 - CK3 1.19 Runtime Rebase`, immediately after AGOT: Canon
   Children EZ Mode
3. `Legacy Of The Dragon - Linux Texture Fix`, immediately after Legacy Of The
   Dragon
4. `AGOT NOW 1.2.4 - CK3 1.19 Rebase`, immediately after NOW
5. `AGOT 0.4.40 - Much Faster Activities Rebase`, immediately after MFA
6. `Grand Remembrance 1.8.1 - CK3 1.19 Runtime Fix`, immediately after the Grand
   Remembrance AGOT compatibility submod
7. `AGOT MPD 0.3.0 - CK3 1.19 Runtime Rebase`, immediately after AGOT MPD and
   before the local MPD + Dragon Wives compatch
8. `Legacy of Valyria RC65 - CK3 1.19 Runtime Rebase`, immediately after the LoV
   RC65 compatch
9. `Essos Expanded + LoV - CK3 1.19 History Rebase`, immediately after Essos
   Expanded and before its TempLoV compatch
10. `AGOT NOW + Legacy of Valyria + Essos Expanded Map Compatch`, after the
    Essos Expanded LoV compatch
11. `AGOT NOW + Legacy of Valyria + Essos Expanded World Data`
12. `AGOT NOW + Legacy of Valyria + Essos Expanded Lore Governments`
13. `AGOT Playset Runtime Fixes`
14. `AGOT Playset Compatch`

Disable these superseded compatch mods:

- `3742055253` — AGOT NOW-COW Compatch
- `3753608966` — AGOT Seasons-NoW Compatch
- `3762893385` — Temporary Seasons of Valyria compatch
- `3766038754` — NOW/LoV/Seasons fork
