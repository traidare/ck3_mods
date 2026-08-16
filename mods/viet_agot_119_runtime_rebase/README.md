# VIET 1.3.0 - AGOT CK3 1.19 Runtime Rebase

Compatibility rebase for **VIET Events** on current **A Game of Thrones**.

## Requirements and load order

1. A Game of Thrones
2. VIET Events
3. This rebase

Load immediately after VIET.

## What it repairs

VIET targets vanilla CK3's culture, faith, religion, title, and geographical
region databases. AGOT replaces those databases, so a large part of VIET
referenced content that does not exist: 151 event definitions, 43 of them fired
repeatedly by VIET's own pulses, four event-background selectors evaluating
hundreds of absent regions, three localization selectors, 17 scripted triggers,
three decisions, and thirteen missing helper triggers.

The rebase:

- keeps every compatible VIET event unchanged;
- replaces only the 151 evidenced incompatible events with inert stubs that keep
  the same IDs, so surviving event chains still resolve, and removes those IDs
  from VIET's random pulse lists;
- keeps the four affected backgrounds on their generic fallback artwork and the
  safe generic cactus, dumpling, and fruit text;
- rebases the 17 database triggers onto AGOT cultural analogues or inert false
  conditions;
- hides the three religion-specific decisions before CK3 evaluates their vanilla
  religion IDs, and supplies AGOT-aware analogues for VIET's heritage helpers;
- repairs four artifact events that called AGOT's feature-reference effect
  without its required owner, six misspelled portrait animations, four delayed
  and on-death ping events that had lost character scope, two duplicate
  event-window widgets, and six fallback branches written without a limit; and
- moves seven random rolls out of interface-toast blocks, so the result you are
  shown and the result that happens can no longer differ.
