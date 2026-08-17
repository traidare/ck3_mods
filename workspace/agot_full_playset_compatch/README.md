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

Beyond those merges the generated layer owns four cross-parent whole-file
overrides: the three historical Dance-of-the-Dragons season starts (autumn
rather than a summer-to-autumn delay), the shared Seasons shader skip threshold,
the Seasons regional cleanup memberships, and NOW's English and Spanish title
names. The regional cleanup rebases `c_sallydance` and `d_greenbelt` onto NOW's
tokens; it also keeps the Iron Isles specific and covers LoV regions without
applying seasons to wilderness ruins.

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
the AGOT+ compatch, LoV, and the temporary Additional Models/AGOT+/LoV compatch
all claim, so the last of them silently drops every court scene the others
registered. The temporary compatch carries the AGOT+, LoV, and Essos entries
that Additional Models lacks, so it stays the base and only Additional Models'
extra court scenes are added: `lorath_court` and `norvos_court`, which are
AGOT's, plus its own `amsb_lokiria_court`. Without them those courts never
progress a visual culture level, even though `agot_playset_runtime_fixes`
already routes the Lorath and Norvos scene-culture selectors. The generator
asserts that set exactly, so it fails rather than quietly absorbing a new court.

That cleanup is written to `map_data/geographical_regions/north_sans_neck.txt`,
the same path the Seasons fork uses: `replace/` is a plain subfolder there with
no engine meaning, so a copy inside it would load _alongside_ the fork's file
and define every shared region twice.

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
- LoV RC71's invalid county-tier pirate elective assignments;
- Essos Expanded's 54 CK3 1.19-invalid title-history capital tokens; and
- CaFG's four references to AGOT-absent `tradition_steppe_tolerance`, handled
  directly by the CaFG AGOT compatch, plus its 35 cultural-boon MAA types
  removed by AGOT's same-file overrides.

## Generation

```sh
ck3mm mod generate agot_full_playset_compatch
ck3mm mod generate agot_full_playset_compatch --apply
```

The `mod.toml` manifest regenerates the owned outputs from the declared NOW and
Seasons-fork sources. Its portable source metadata lives here, outside the
installed runtime payload.

## Re-audit

Re-audit whenever any merged parent updates — in particular NOW, the
Seasons-of-Valyria Workshop fork, LoV, MFA, COW, or CaFG — since every owned
file is a whole-file merge that silently absorbs upstream changes.
