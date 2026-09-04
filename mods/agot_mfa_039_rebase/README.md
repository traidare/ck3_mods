# Much Faster Activities - AGOT CK3 1.19 Runtime Rebase

Rebases AGOT - Much Faster Activities onto current A Game of Thrones and CK3
1.19, so its faster activities keep working without dragging vanilla logic back
in.

## Requirements and load order

1. A Game of Thrones
2. AGOT - Much Faster Activities
3. This rebase

Load it immediately after Much Faster Activities and before any compatibility
layer that merges MFA with Legacy of Valyria, Culture and Faith Granularity,
Citadel University, or other activity mods. MFA's additive files still come from
the Workshop parent.

## What it repairs

Much Faster Activities replaces 27 AGOT activity, event, and GUI files
wholesale. This rebase keeps MFA's verified timing, pulse relay, cooldown,
wait-time, and activity-window behaviour while fixing what that replacement
breaks:

- MFA restores vanilla's `tradition_land_of_the_bow` tournament block even
  though AGOT removes that tradition. The rebase keeps AGOT's block disabled.
- A playdate can end before MFA's delayed relay runs, so the relay now checks
  that the activity still exists before reading its phase.
- MFA's delayed relays lose the engine-supplied province scope of the pulses
  they replace. Across 28 on-action files, 695 event-selection checks pointed at
  that unavailable scope; they now use the activity's location instead. This
  covers accelerated education, coronations, chariot races, feasts, festivals,
  funerals, hunts, pilgrimages, playdates, tours, tournaments, weddings, and
  witch rituals.
- The hunt relay ran from a character rather than an activity, breaking six
  event-selection checks, its success weight, and its province-owner check. All
  now use the relay's activity scope, removing the repeated type mismatch and
  the null relationship and opinion targets that followed it.
- Five event-selection lists used 19 fractional weights, which CK3 1.19 treats
  as zero and silently disables. Every weight in those lists is scaled by ten,
  preserving the original relative probabilities.
