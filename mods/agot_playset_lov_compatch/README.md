# AGOT Playset Compatch - Legacy of Valyria

The Legacy of Valyria add-on to **AGOT Playset Compatch**, for a large AGOT
playset on CK3 1.19. Enable it whenever the Legacy of Valyria family is enabled
and disable it together with that family; on its own, **AGOT Playset Compatch**
already covers everything that holds without Legacy of Valyria.

## What it merges

- Much Faster Activities' timing with Legacy of Valyria's coronation,
  tournament, and dragon-hatching changes.
- More Dragon Eggs' hatching, cradling, ruin eggs, and landless dragonpit
  handling with Legacy of Valyria's volcano locations and restored mines.
- Legacy of Valyria's tournament guards, Much Faster Activities' cooldown, and
  Culture and Faith Granularity's county-faith conversion in the same events.
- Travelers' AGOT travel behavior with Legacy of Valyria's travel safety fixes,
  while preserving AGOT's dragon-flight restriction during sailing activities.
- A Living Westeros' wedding backgrounds and guest-right restrictions with Much
  Faster Activities' pace, Legacy of Valyria's safe activity scopes, and the
  Long Night's dead-character exclusion.
- The Long Night's rule keeping a sworn brother of the Night's Watch from
  serving as regent outside the Watch, with the Legacy of Valyria bridge's guard
  against that rule being asked about no one at all.
- Special-building model detection from AGOT, Additional Models, and COW-AGOT
  with Nobility of Westeros' province remaps, keeping Legacy of Valyria's later
  graphical backgrounds.
- Iron and Salt's kraken map icon with the Legacy of Valyria bridge's map icon
  correction, and its kraken exclusion with Great Councils' character exclusion.
- The Legacy of Valyria map, with an adjacency corrected onto the province
  Nobility of Westeros actually defines.

It also repairs Legacy of Valyria's own scripts: nomad yurt upgrades that asked
for buildings their prerequisites did not allow, noble-family titles created
from inside an in-flight title transfer, generated accolade successors who were
never eligible knights, an Aurion recovery fallback attached to every title
transfer, and a High Septon who was named but never nicknamed and so displayed
no name at all.

## Required load order

Keep **Legacy of Valyria - AGOT 0.5.2.1 Compatch (Beta)** immediately after
**Legacy of Valyria**, and the **Seasons of Valyria** and **Additional Models +
Legacy of Valyria** compatches after that. Keep **Culture and Faith Granularity

- AGOT Compatch - Legacy of Valyria** before this module as well, so its
  tournament events do not replace the merged ones. Load this module after all
  of them and after **AGOT Playset Compatch**.
