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

The rebase also repairs current-parent defects encountered during validation:
NOW's `d_lychester` creation check still referenced removed `d_medway`; the
NOW/Seasons region merge put duchy `d_ironwater` in a county list and retained
removed county `c_sunvane`. These now resolve to `d_lychester`, `c_ironwater`,
and `c_brittlebush`.

## Required load order

Keep each ordinary parent mod in its existing relative position, then place the
local compatibility layers in this order:

1. `AGOT 0.4.39 - Much Faster Activities Rebase`, immediately after MFA
2. `AGOT NOW + Legacy of Valyria + Essos Expanded Map Compatch`, after the Essos
   Expanded LoV compatch
3. `AGOT LoV + Essos Full Playset Compatch`, last

Disable these superseded Workshop compatches:

- `3742055253` — AGOT NOW-COW Compatch
- `3753608966` — AGOT Seasons-NoW Compatch
- `3762893385` — original temporary Seasons of Valyria compatch
- `3766038754` — on-hold NOW/LoV/Seasons bundle

Their necessary behavior is rebased here; loading them as well only restores
stale whole-file overrides.
