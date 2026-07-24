# AGOT Personal Playset Compatch

This combines:

- MFA timing with LoV's coronation, tournament, and dragon-hatching changes;
- the temporary More Dragon Eggs + LoV hatching activity;
- LoV tournament guards, MFA's cooldown, and CaFG's granular county-faith
  conversion in `contest_events.txt`;
- CaFG county/province controls with LoV ruin restoration in the county view;
- current NOW 1.2.4 titles with COW's Dunstonbury/Sisterton expectations,
  including corrected province 2709/2716/2717 history and localization;
- LoV + NOW + Seasons regional definitions, repaint actions, map modes, seasonal
  effects, and FX.

The accompanying narrow runtime layers also repair:

- NOW 1.2.4's CK3 1.19-invalid effects and game-start scoping;
- AGOT MPD's startup calculator parameter, variable, and XP-track failures;
- Grand Remembrance's no-character chronicle visibility loop;
- Legacy Of The Dragon's Linux-sensitive lowercase texture path;
- Essos Expanded's 54 CK3 1.19-invalid title-history capital tokens; and
- CaFG's four references to AGOT-absent `tradition_steppe_tolerance`, handled
  directly by the CaFG AGOT compatch.

The rebase also repairs current-parent defects encountered during validation:
NOW's `d_lychester` creation check still referenced removed `d_medway`; the
NOW/Seasons region merge put duchy `d_ironwater` in a county list and retained
removed county `c_sunvane`. These now resolve to `d_lychester`, `c_ironwater`,
and `c_brittlebush`.

## Required load order

Keep each ordinary parent mod in its existing relative position, then place the
local compatibility layers in this order:

1. `Legacy Of The Dragon - Linux Texture Fix`, immediately after Legacy Of The
   Dragon
2. `AGOT NOW 1.2.4 - CK3 1.19 Rebase`, immediately after NOW
3. `AGOT 0.4.39 - Much Faster Activities Rebase`, immediately after MFA
4. `Grand Remembrance 1.8.1 - CK3 1.19 Runtime Fix`, immediately after the Grand
   Remembrance AGOT compatibility submod
5. `AGOT MPD 0.3.0 - CK3 1.19 Runtime Rebase`, immediately after AGOT MPD and
   before the local MPD + Dragon Wives compatch
6. `Essos Expanded + LoV - CK3 1.19 History Rebase`, immediately after Essos
   Expanded and before its TempLoV compatch
7. `AGOT NOW + Legacy of Valyria + Essos Expanded Map Compatch`, after the Essos
   Expanded LoV compatch
8. `AGOT Personal Playset Compatch`, last

Disable these superseded Workshop compatches:

- `3742055253` — AGOT NOW-COW Compatch
- `3753608966` — AGOT Seasons-NoW Compatch
- `3762893385` — Temporary Seasons of Valyria compatch
- `3766038754` — NOW/LoV/Seasons fork

Their necessary behavior is rebased here; loading them as well only restores
whole-file overrides already present in this layer.
