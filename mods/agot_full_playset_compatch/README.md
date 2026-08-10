# AGOT Playset Compatch

This combines:

- MFA timing with LoV's coronation, tournament, and dragon-hatching changes;
- the temporary More Dragon Eggs + LoV hatching activity;
- LoV tournament guards, MFA's cooldown, and CaFG's granular county-faith
  conversion in `contest_events.txt`;
- CaFG county/province controls with LoV ruin restoration in the county view;
- AGOT, Additional Models, and COW special-building model detection with the
  NOW-COW 1.0.2 Dunstonbury/Sisterton province remaps, while retaining LoV's
  later graphical-background definitions;
- COW's Dunstonbury/Sisterton province history and localization, while the
  enabled Seasons-of-Valyria Workshop fork supplies its maintained regional
  definitions, repaint actions, map modes, seasonal effects, GUI, situations,
  and localization.

The accompanying narrow runtime layers also repair:

- AGOT+'s CK3 1.19-invalid canon-child creation and dead-character perk
  assignments;
- NOW 1.2.5's unsaved Great Fork title-change scope and optional Summerhall
  candidate comparisons;
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
- LoV RC71's invalid county-tier pirate elective assignments;
- Essos Expanded's 54 CK3 1.19-invalid title-history capital tokens; and
- CaFG's four references to AGOT-absent `tradition_steppe_tolerance`, handled
  directly by the CaFG AGOT compatch, plus its 35 cultural-boon MAA types
  removed by AGOT's same-file overrides.

The final generated layer owns only three cross-parent whole-file overrides: the
three historical Dance-of-the-Dragons season starts (autumn rather than a
summer-to-autumn delay), the shared Seasons shader skip threshold, and the
Seasons regional cleanup memberships. The latter rebases `c_sallydance` and
`d_greenbelt` onto NOW's tokens; it also keeps the Iron Isles specific and
covers LoV regions without applying seasons to wilderness ruins. It is written
to `map_data/geographical_regions/north_sans_neck.txt`, the same path the
Seasons fork uses: `replace/` is a plain subfolder there with no engine meaning,
so a copy inside it would load _alongside_ the fork's file and define every
shared region twice. The per-mod `workspace/agot_full_playset_compatch/mod.toml`
generator regenerates those outputs from the declared NOW and Seasons-fork
sources. Its portable source metadata now lives under
`workspace/agot_full_playset_compatch/` instead of the installed runtime
payload.

```sh
ck3mm mod check agot_full_playset_compatch
ck3mm mod generate agot_full_playset_compatch
```

A narrow `can_raid` scripted-rule override also returns false when CK3 evaluates
the rule without a potential-raider character, while delegating unchanged to
AGOT's `can_raid_trigger` for every valid character.

## Required load order

1. `VIET 1.3.0 - AGOT CK3 1.19 Runtime Rebase`, immediately after VIET
2. `AGOT+ 1.0.0 - CK3 1.19 Runtime Rebase`, immediately after AGOT: Canon
   Children EZ Mode
3. `Legacy Of The Dragon - Linux Texture Fix`, immediately after Legacy Of The
   Dragon
4. `AGOT NOW - CK3 1.19 Rebase`, immediately after NOW
5. `AGOT 0.4.40 - Much Faster Activities Rebase`, immediately after MFA
6. `Grand Remembrance 1.8.2 - CK3 1.19 Runtime Fix`, immediately after the Grand
   Remembrance AGOT compatibility submod
7. `AGOT MPD 0.3.0 - CK3 1.19 Runtime Rebase`, immediately after AGOT MPD and
   before the local MPD + Dragon Wives compatch
8. `Legacy of Valyria RC71 - CK3 1.19 Runtime Rebase`, immediately after the LoV
   RC71 compatch
9. `Essos Expanded + LoV - CK3 1.19 History Rebase`, immediately after Essos
   Expanded and before its TempLoV compatch
10. `AGOT NOW-Season of Ice and Fire Compatch`, after the Essos Expanded LoV
    compatch
11. `Seasons of Valyria - TempLoV/NOW/Seasons Compatch`
12. `Essos Expanded - TempLoV/NOW Compatch`
13. `AGOT NOW + Legacy of Valyria + Essos Expanded Map Compatch`
14. `AGOT NOW + Legacy of Valyria + Essos Expanded World Data`
15. `AGOT NOW + Legacy of Valyria + Essos Expanded Lore Governments`
16. `AGOT Playset Runtime Fixes`
17. `AGOT Playset Compatch`

Disable these superseded compatch mods:

- `3742055253` — AGOT NOW-COW Compatch
- `3762893385` — Temporary Seasons of Valyria compatch
