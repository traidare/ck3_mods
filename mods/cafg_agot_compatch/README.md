# Culture and Faith Granularity + AGOT Compatch

Makes **[Kei] Culture and Faith Granularity** work in **A Game of Thrones**.

## Requirements and load order

1. `[Kei] Culture and Faith Granularity`
2. `A Game of Thrones`
3. This compatch

If you also run **Legacy of Valyria**, add the companion item
`Culture and Faith Granularity + AGOT Compatch - Legacy of Valyria` after Legacy
of Valyria and after this one. Without it, whichever of the two loads last wins
the county view and the tournament events outright.

## What it does

Culture and Faith Granularity is written for vanilla CK3. AGOT replaces the
culture, faith, men-at-arms, and decision databases it relies on, so a large
part of it points at content that no longer exists. This compatch keeps
everything that still works and repairs the rest.

**County conversion** is integrated with AGOT's own conversion events, so
granular per-province conversion applies to AGOT's cultures and faiths.

**Startup tolerance laws** no longer check a steppe tradition AGOT lacks. Those
four checks are dropped and every other criterion kept, which stops the repeated
errors while initial laws are picked for rulers.

**Cultural men-at-arms boons.** AGOT and later playset mods remove 35 of the
unit types this mod can gift, which produced 105 failures per evaluation. Only
gifts whose unit is gone are removed; the 18 valid ones are untouched, and a
branch whose every outcome was invalid is dropped whole so no boon picks an
empty result. Eleven branches needing traditions AGOT lacks are reworked
instead: the pastoralist boon keeps its plains and steppe conditions, the
pilgrim boon grants the ordinary pilgrim trait, and the scholar-official reward
keeps its character bonus without the vanilla Han language and Confucian
education steps.

**The five-year cultural-benefit pulse** no longer queries three traditions and
a heritage pillar AGOT does not define. The isolationist, fiercely independent,
ruling-caste, cultivated-sophistication, communal, tolerant-law, and xenophilic
modifiers all still apply.

**Vanilla-only decisions and definitions are disabled** — a Persian
faith-adoption decision, an Outremer culture decision, and three files of
definitions AGOT deliberately removes. None can be used in AGOT, and their
repeatedly evaluated conditions produced roughly 13,500 invalid lookups. No AGOT
decision is changed.

## Known incompatibility

**Better AI Education & Ward Limit BOL.** This compatch ships a complete copy of
the hold-court event file, because CK3 replaces event files whole and rejects
duplicate event IDs. Loading this compatch after that mod reverts its hold-court
changes. There is no way to keep both.
