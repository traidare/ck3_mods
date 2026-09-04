# AGOT MPD - CK3 1.19 Runtime Rebase

Narrow runtime repair for **AGOT - More Personality Depth** on current A Game of
Thrones and CK3 1.19.

## Requirements and load order

Load immediately after **AGOT - More Personality Depth** and before the **AGOT -
More Personality Depth + Dragon Wives Compatch**.

## What it repairs

- Removes four parameterized culture-weight modifiers. AGOT does not define the
  `*_trait_more_common` / `*_trait_less_common` parameters for every personality
  trait, so CK3 rejects many of the calculator's instantiated effects at load.
- Guards the court-owner and wet-nurse task lookups so they no longer read unset
  scopes and variables.
- Names the XP track explicitly when granting and reading personality XP,
  instead of relying on a shorthand that silently creates a second track.
- Moves the 37 opinion fields to trait scope, where CK3 1.19 expects them.
- Makes the cumulative personality counters threshold-safe: a missed threshold
  catches up on the next qualifying action, and the highest earned level is
  applied first.
- Neutralizes **Immersive Personalities**' conflicting `paranoid` override, so
  More Personality Depth remains the single source of that trait's XP track. If
  you run both mods, More Personality Depth's version wins.

Faith, guardian, parent, guardian-influence, and wet-nurse weighting are
otherwise unchanged.

## Scope

This mod repairs executable More Personality Depth behaviour only and is useful
without Dragon Wives. The shared character-window GUI merge lives in the
separate **AGOT - More Personality Depth + Dragon Wives Compatch**.
