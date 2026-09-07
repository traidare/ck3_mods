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
- Special-building model detection from AGOT, Additional Models, and COW-AGOT,
  with Nobility of Westeros' Dunstonbury and Sisterton province remaps, while
  keeping Legacy of Valyria's later graphical backgrounds.
- COW-AGOT's Dunstonbury and Sisterton province history and text, while the
  Seasons of Valyria fork supplies its maintained regional definitions, repaint
  actions, map modes, seasonal effects, interface, situations, and text.
- Nobility of Westeros' title names, so its renamed and newly added titles are
  not lost behind the Dunstonbury and Sisterton barony names.
- The dragon on-action file shipped by both More Dragon Eggs and More Dragon
  Events, so the canon egg-clutch pulse and the extra owned-dragon events both
  keep working instead of one mod's file replacing the other's.
- New Personality Events for Children's tenth-birthday events with AGOT's
  AI-only canon-rider bonding, so both systems fire for eligible children.
- Iron and Salt's naval and kraken HUD with Dynamyc Family Portrait's AGOT
  portrait stack and More Dragon Eggs' sized dragon portrait.
- Iron and Salt's kraken map icon with the Legacy of Valyria AGOT bridge's map
  icon correction.
- Iron and Salt's kraken exclusion with AGOT's creature rules and Great
  Councils' character exclusion.
- The Long Night & Azor Ahai's rule keeping a sworn brother of the Night's Watch
  from serving as regent outside the Watch, with the Legacy of Valyria AGOT
  bridge's guard against the same rule being asked about no one at all.

It also owns three cross-parent overrides of its own: the three historical Dance
of the Dragons starts begin in autumn rather than waiting through summer, the
shared Seasons shader threshold, and the Seasons regional cleanup — which keeps
the Iron Islands specific and covers Legacy of Valyria's regions without
applying seasons to wilderness ruins. A narrow rule change also stops CK3 from
erroring when it evaluates raiding without a raider.

## Required load order

`New Personality Events for Children` must be enabled after AGOT and before this
compatch. Keep the integration layers in this order:

1. `VIET - AGOT CK3 1.19 Runtime Rebase`, immediately after VIET
2. `AGOT NOW - CK3 1.19 Rebase`, immediately after NOW
3. `AGOT NOW-Season of Ice and Fire Compatch`, immediately after the NOW rebase
4. `Much Faster Activities - AGOT CK3 1.19 Runtime Rebase`, immediately after
   MFA
5. `AGOT MPD - CK3 1.19 Runtime Rebase`, immediately after AGOT MPD and before
   the MPD + Dragon Wives compatch
6. `Legacy of Valyria - AGOT 0.5.2.1 Compatch (Beta)`, immediately after
   `Legacy of Valyria`
7. `Essos Expanded: The Further East`, immediately after `Essos Expanded`
8. `Seasons of Valyria - TempLoV/NOW/Seasons Compatch`
9. `Essos Expanded - TempLoV/NOW Compatch`
10. `AGOT NOW + Legacy of Valyria + Essos Expanded Compatch`
11. `CK3 Naval Combat`
12. `AGOT Iron and Salt`
13. `Character UI Overhaul`
14. `AGOT Playset - Character UI Overhaul Compatch`
15. `AGOT: Canon Continuity`
16. `AGOT: The Long Night & Azor Ahai`
17. `AGOT: The Long Night & Azor Ahai - CK3 1.19 Runtime Fix`
18. `AGOT: The Long Night & Azor Ahai + DFP Compatch`
19. `AGOT - Excommunication Balance`
20. `AGOT Playset Runtime Fixes`
21. `AGOT Playset Compatch`
