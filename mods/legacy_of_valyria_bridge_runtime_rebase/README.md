# Legacy of Valyria - AGOT 0.5.1 Bridge - CK3 1.19 Runtime Rebase

Startup-script rebase for **Legacy of Valyria - AGOT 0.5.1** onto current A Game
of Thrones.

## Requirements and load order

Load immediately after the Legacy of Valyria AGOT bridge, and before Essos
Expanded.

## What it does

The bridge ships a whole-file copy of AGOT's game-start script, so everything
AGOT has changed there since that copy was taken is silently reverted. This
rebase rebuilds the file from AGOT's current version and reapplies Legacy of
Valyria's own additions: the dummy-ruler rehome hook, the Mantaryan traits, and
the estate innovation and slot guards. AGOT's Narrow Sea gate, Lorath setup,
confederations, scenarios, sailing setup, and all other startup behaviour come
back with it.

The supersiren distributor picks each county capital, requires a valid culture
and faith, and only kills the source ruler once every county has transferred.

Pirate succession laws and title history are not touched here; they stay with
the Legacy of Valyria bridge and later playset layers.
