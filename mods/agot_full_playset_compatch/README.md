# AGOT Playset Compatch

The final integration layer for this AGOT playset. It resolves the remaining
genuine cross-mod overlaps that need a single deliberate winner.

## What it merges

- Much Faster Activities' timing with Legacy of Valyria's coronation,
  tournament, and dragon-hatching changes.
- The temporary More Dragon Eggs + Legacy of Valyria hatching activity.
- Legacy of Valyria's tournament guards, Much Faster Activities' cooldown, and
  Culture and Faith Granularity's granular county-faith conversion in the same
  tournament events.
- Culture and Faith Granularity's county and province controls with Legacy of
  Valyria's ruin restoration in the county view.
- Special-building model detection from AGOT, Additional Models, and Crowns of
  Westeros, with Nobility of Westeros' Dunstonbury and Sisterton province
  remaps, while keeping Legacy of Valyria's later graphical backgrounds.
- Crowns of Westeros' Dunstonbury and Sisterton province history and text, while
  the Seasons of Valyria fork supplies its maintained regional definitions,
  repaint actions, map modes, seasonal effects, interface, situations, and text.
- Nobility of Westeros' title names, so its renamed and newly added titles are
  not lost behind the Dunstonbury and Sisterton barony names.
- The dragon on-action file shipped by both More Dragon Eggs and More Dragon
  Events, so the canon egg-clutch pulse and the extra owned-dragon events both
  keep working instead of one mod's file replacing the other's.

It also owns three cross-parent overrides of its own: the three historical Dance
of the Dragons starts begin in autumn rather than waiting through summer, the
shared Seasons shader threshold, and the Seasons regional cleanup — which keeps
the Iron Islands specific and covers Legacy of Valyria's regions without
applying seasons to wilderness ruins. A narrow rule change also stops CK3 from
erroring when it evaluates raiding without a raider.

## Required load order

1. `VIET 1.3.0 - AGOT CK3 1.19 Runtime Rebase`, immediately after VIET
2. `AGOT+ 1.0.0 - CK3 1.19 Runtime Rebase`, immediately after AGOT: Canon
   Children EZ Mode
3. `Legacy Of The Dragon - Linux Texture Fix`, immediately after Legacy Of The
   Dragon
4. `AGOT NOW - CK3 1.19 Rebase`, immediately after NOW
5. `AGOT 0.4.40 - Much Faster Activities Rebase`, immediately after MFA
6. `Grand Remembrance 1.9.0 - CK3 1.19 Runtime Fix`, immediately after the Grand
   Remembrance AGOT compatibility submod
7. `AGOT MPD 0.4.0 - CK3 1.19 Runtime Rebase`, immediately after AGOT MPD and
   before the MPD + Dragon Wives compatch
8. `Legacy of Valyria - AGOT 0.5.1 Bridge - CK3 1.19 Runtime Rebase`,
   immediately after `Legacy of Valyria - AGOT 0.5.1`
9. `Essos Expanded: The Further East - CK3 1.19 History Rebase`, immediately
   after `Essos Expanded: The Further East` and before its TempLoV compatch
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

- `COW-AGOT: Nobility of Westeros Compatch`
- `TEMPORARY Seasons of Valyria - LoV & Seasons REBASED Compatch`
- `Legacy of Valyria - AGOT 0.5.1 Compatch (Beta)`
