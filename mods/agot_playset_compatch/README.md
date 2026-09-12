# AGOT Playset Compatch

A compatch for a large AGOT playset on CK3 1.19. It repairs script errors the
playset's mods produce and resolves the cross-mod overlaps that need one
deliberate winner. Everything here holds whether or not Legacy of Valyria and
Essos Expanded are enabled, so it can stay on in any of those combinations.

## What it repairs

Roughly fifty parent mods are touched, and gameplay intent from every one is
preserved — only the code CK3 rejects is changed.

- **Effects CK3 1.19 no longer accepts** — removed triggers, obsolete event
  fields, negative gold costs, malformed tooltips.
- **Unset or missing scopes** — a father, capital, war, or activity host read
  without checking it exists, erroring repeatedly from game start onward.
- **References to content AGOT removes**, and **stale whole-file copies** that
  silently revert AGOT's own content. One such copy left newly elected High
  Septons with no displayed name at all.
- **Broken succession and war joins**, including revalidated accolade
  successors. Automatic agents are disabled for Promote, Raid Estate, and Expand
  Power Base as the stability tradeoff.
- **Runaway title creation** — noble-family titles are rate-limited and created
  a day later, so realms stop accumulating duplicates.
- **Special-building fields the game discards while reading them**, so landmark
  bonuses, garrisons, and follow-ups actually arrive.
- **Portrait, interface, and art-lookup breakage**, including art retried on
  every redraw for as long as the affected view is open.

## What it merges

Much Faster Activities' timing against AGOT's coronation, tournament, and
dragon-hatching definitions; A Living Westeros' wedding and guest-right rules
against that timing and the Long Night's dead-character exclusion; Culture and
Faith Granularity's county-faith conversion in tournament events;
special-building model detection across AGOT, Additional Models and COW-AGOT
with Nobility of Westeros' province remaps; and the seasonal region survey,
restated once so no region carries two conflicting definitions.

## Required load order

Load this module after every mod it repairs or merges. Keep **Travelers**
immediately after AGOT and **Travelers AGOT Compatibility** immediately after
it. Keep **New Personality Events for Children**, **AGOT: Canon Continuity**,
the **AGOT: The Long Night & Azor Ahai** chain, and **AGOT - Excommunication
Balance** before this module.
