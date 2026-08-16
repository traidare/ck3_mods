# Culture and Faith Granularity + AGOT Compatch

Makes **[Kei] Culture and Faith Granularity** work in **A Game of Thrones**.

## Requirements and load order

1. `[Kei] Culture and Faith Granularity`
2. `A Game of Thrones`
3. This compatch

## What it does

Culture and Faith Granularity is written for vanilla CK3. AGOT replaces the
culture, faith, men-at-arms, and decision databases it relies on, so a large
part of it points at content that no longer exists. This compatch keeps
everything that still works and repairs the rest.

**County culture and faith conversion** is integrated with AGOT's own conversion
events, so granular per-province conversion applies to AGOT's cultures and
faiths.

**Startup tolerance laws.** AGOT does not have the steppe-tolerance tradition
Culture and Faith Granularity checks. Those four checks are dropped and every
other criterion is kept, which stops the repeated errors while initial laws are
picked for rulers.

**Cultural men-at-arms boons.** AGOT and later playset mods remove 35 of the
unit types Culture and Faith Granularity can gift, which produced 105 failures
every time a boon was evaluated. Only the gifts whose unit no longer exists are
removed; the 18 valid ones are untouched. Where every outcome of a nested roll
was invalid, the whole branch is removed so the boon cannot pick an empty
result. Eleven further branches whose traditions AGOT does not have are removed
too — the pastoralist boon keeps its plains and steppe conditions, the pilgrim
boon grants the ordinary pilgrim trait instead of querying vanilla Islam, and
the scholar-official reward keeps its character bonus without the vanilla Han
language and Confucian education steps.

**The five-year cultural-benefit pulse** queried three traditions and one
heritage pillar that AGOT does not define. Those four alternatives are removed;
the isolationist, fiercely independent, ruling-caste, cultivated-sophistication,
communal, tolerant-law, and xenophilic modifiers all still apply.

**Vanilla-only decisions and definitions are disabled.** Culture and Faith
Granularity re-adds a Persian faith-adoption decision, an Outremer culture
decision, and three files of vanilla-only definitions that AGOT deliberately
removes. None of them can be used in AGOT, and their repeatedly evaluated
conditions produced roughly 13,500 invalid lookups. They are prevented from
loading, without changing any AGOT decision.
