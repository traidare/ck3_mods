# AGOT Playset Compatch

The final integration layer for this AGOT playset. It resolves the remaining
genuine cross-mod overlaps that need a single deliberate winner.

## What it merges

- Much Faster Activities' timing with Legacy of Valyria's coronation,
  tournament, and dragon-hatching changes.
- The final temporary More Dragon Eggs + Legacy of Valyria hatching activity,
  while keeping ordinary eggs selectable when extant ceremonies are enabled.
- Legacy of Valyria's tournament guards, Much Faster Activities' cooldown, and
  Culture and Faith Granularity's granular county-faith conversion in the same
  tournament events.
- Special-building model detection from AGOT, Additional Models, and COW-AGOT,
  with Nobility of Westeros' Dunstonbury and Sisterton province remaps, while
  keeping Legacy of Valyria's later graphical backgrounds.
- COW-AGOT's Dunstonbury and Sisterton text, while the Seasons of Valyria fork
  supplies its maintained regional definitions, repaint actions, map modes,
  seasonal effects, interface, situations, and text.
- Nobility of Westeros' title names, so its renamed and newly added titles are
  not lost behind the Dunstonbury and Sisterton barony names.
- The dragon on-action file shipped by both More Dragon Eggs and More Dragon
  Events, so the canon egg-clutch pulse and the extra owned-dragon events both
  keep working instead of one mod's file replacing the other's.
- More Dragon Eggs' two dragonkeeper landing hooks with Seasons' later weather
  override, so becoming landed does not drop the dragonpit follow-up event.
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
- Travelers' AGOT travel behavior with Legacy of Valyria's travel safety fixes,
  while preserving AGOT's dragon-flight restriction during sailing activities.
- A Living Westeros' wedding backgrounds and guest-right restrictions with Much
  Faster Activities' wedding pace, Legacy of Valyria's safe activity scopes, and
  the Long Night's dead-character exclusion.

It also owns two cross-parent overrides of its own: the three historical Dance
of the Dragons starts begin in autumn rather than waiting through summer, and
the Seasons regional cleanup — which keeps the Iron Islands specific and covers
Legacy of Valyria's regions without applying seasons to wilderness ruins. A
narrow rule change also stops CK3 from erroring when it evaluates raiding
without a raider.

## Required load order

`New Personality Events for Children` must be enabled after AGOT and before this
compatch. Keep `Travelers` immediately after AGOT and
`Travelers AGOT Compatibility` immediately after Travelers. `Lifespan Traits`
can remain beside the other congenital-trait mods. Keep `AGOT More Dragon Eggs`
followed by `AGOT More Dragon Eggs - Fix for AGOT 0.5.2.1`, then
`AGOT expanded - Dragons`; the temporary More Dragon Eggs + LoV compatch stays
after the LoV bridge. Keep the integration layers in this order:

1. `VIET - AGOT CK3 1.19 Runtime Rebase`, immediately after VIET
2. `AGOT NOW - CK3 1.19 Rebase`, immediately after NOW
3. `AGOT NOW-Season of Ice and Fire Compatch`, immediately after the NOW rebase
4. `Much Faster Activities - AGOT CK3 1.19 Runtime Rebase`, immediately after
   MFA
5. `AGOT - A Living Westeros`, after the MFA runtime rebase
6. `AGOT Canon Wars`, after AGOT Great Councils
7. `AGOT MPD - CK3 1.19 Runtime Rebase`, immediately after AGOT MPD and before
   the MPD + Dragon Wives compatch
8. `Legacy of Valyria - AGOT 0.5.2.1 Compatch (Beta)`, immediately after
   `Legacy of Valyria`
9. `Essos Expanded: The Further East`, immediately after `Essos Expanded`
10. `Seasons of Valyria - TempLoV/NOW/Seasons Compatch`
11. `Essos Expanded - TempLoV/NOW Compatch`
12. `AGOT NOW + Legacy of Valyria + Essos Expanded Compatch`
13. `CK3 Naval Combat`
14. `AGOT Iron and Salt`
15. `Character UI Overhaul`
16. `AGOT Playset - Character UI Overhaul Compatch`
17. `AGOT: Canon Continuity`
18. `AGOT: The Long Night & Azor Ahai`
19. `AGOT: The Long Night & Azor Ahai - CK3 1.19 Runtime Fix`
20. `AGOT: The Long Night & Azor Ahai + DFP Compatch`
21. `AGOT - Excommunication Balance`
22. `AGOT Playset Runtime Fixes`
23. `AGOT Playset Compatch`
