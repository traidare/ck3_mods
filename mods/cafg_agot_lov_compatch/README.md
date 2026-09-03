# Culture and Faith Granularity + AGOT Compatch - Legacy of Valyria

Add-on for players running **Legacy of Valyria** alongside the **Culture and
Faith Granularity + AGOT Compatch**.

## Requirements and load order

1. `[Kei] Culture and Faith Granularity`
2. `A Game of Thrones`
3. `Culture and Faith Granularity + AGOT Compatch`
4. `Legacy of Valyria` and its AGOT compatibility patch
5. This add-on, last among these five

Do not use this on its own — it only carries two files and expects the base
compatch underneath.

## Why it exists

CK3 replaces county-view windows and event files as a whole, not piece by piece.
That leaves exactly two files where the base compatch and Legacy of Valyria both
need to win: the county view and the tournament contest events. Without this
add-on, whichever loads last silently reverts the other — you either lose Legacy
of Valyria's ruin restoration and tournament changes, or you lose Culture and
Faith Granularity's province controls and granular county-faith conversion.

This add-on rebuilds Culture and Faith Granularity's hooks on top of Legacy of
Valyria's own versions of those two files, so both work at once. It changes
nothing else.
