# AGOT MPD 0.3.0 - CK3 1.19 Runtime Rebase

Narrow runtime repair for Workshop mod **AGOT - More Personality Depth**
(`3717990443`, version `0.3.0-rebalance`) on AGOT `0.4.39` / CK3 `1.19`.

Load this mod immediately after **AGOT - More Personality Depth** and before the
local MPD + Dragon Wives GUI compatch.

## Override

- `common/scripted_effects/mpd_xp_calculator.txt`
- `common/scripted_effects/mpd_119_shift_helpers.txt`

## Repairs

- Removes the four parameterized culture-weight modifiers. AGOT does not define
  the generated `*_trait_more_common` / `*_trait_less_common` parameters for
  every personality trait, so CK3 rejects many instantiated calculator effects
  during post-validation.
- Uses optional `court_owner ?=` scoping and checks
  `has_variable = mpd_wn_active_task` before comparing the wet-nurse task
  variable.
- Explicitly selects the shorthand XP track named after `$TRAIT$` for both
  `has_trait_xp` and `add_trait_xp`. This fixes the observed `paranoid`
  multiple-track error and is valid for MPD's single-track personality trait
  overrides.
- Keeps the threshold-safe cumulative counter helpers previously housed in the
  Dragon Wives compatch. These are MPD-only runtime repairs: missed thresholds
  catch up on the next qualifying action, the highest earned level is applied
  first, and all XP operations now select their shorthand tracks explicitly.

Faith, guardian, parent, guardian-influence, and wet-nurse weighting are
otherwise unchanged.

Recompare this override after every update to Workshop mod `3717990443`.

## Why this remains separate from the Dragon Wives compatch

This rebase repairs executable MPD behavior and is useful without Dragon Wives.
The Dragon Wives compatch owns only the shared `window_character.gui` merge.
Keeping the layers separate isolates volatile MPD script rebases from the
genuine cross-mod GUI merge.
