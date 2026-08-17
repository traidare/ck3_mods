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
- The court grandeur levels claimed by AGOT, Additional Models, AGOT+, Legacy of
  Valyria, and the temporary Additional Models compatch, so the Lorath, Norvos,
  and Lokiria courts still gain visual culture levels.

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
6. `Grand Remembrance 1.8.2 - CK3 1.19 Runtime Fix`, immediately after the Grand
   Remembrance AGOT compatibility submod
7. `AGOT MPD 0.4.0 - CK3 1.19 Runtime Rebase`, immediately after AGOT MPD and
   before the MPD + Dragon Wives compatch
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

- AGOT NOW-COW Compatch
- Temporary Seasons of Valyria compatch
