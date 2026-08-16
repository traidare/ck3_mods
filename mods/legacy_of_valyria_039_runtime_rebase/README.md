# Legacy of Valyria RC71 - CK3 1.19 Runtime Rebase

Startup-script rebase for **Legacy of Valyria - AGOT Temporary Compatch RC71**
onto current A Game of Thrones.

## Requirements and load order

Load immediately after the Legacy of Valyria AGOT temporary compatch, and before
Essos Expanded.

## What it does

The compatch ships a whole-file copy of AGOT's game-start script that has fallen
behind AGOT. This rebase rebuilds that file from AGOT's current version and
reapplies Legacy of Valyria's own additions: the dummy-ruler rehome hook, the
Mantaryan traits, the estate innovation and slot guards, and the 39 estate
dynasties. AGOT's Narrow Sea gate, Lorath setup, confederations, scenarios,
sailing setup, and all other startup behaviour come back with it.

The supersiren distributor now picks each county capital, requires a valid
culture and faith, and only kills the source ruler once every county has
transferred.

Pirate succession laws and title history are not touched here; they stay with
the Legacy of Valyria compatch and later playset layers.
