# AGOT MPD 0.3.0 - CK3 1.19 Runtime Rebase

Narrow runtime repair for Workshop mod **AGOT - More Personality Depth**
(`3717990443`, version `0.3.0-rebalance`) on AGOT `0.4.40` / CK3 `1.19`.

Load this mod immediately after **AGOT - More Personality Depth** and before the
local MPD + Dragon Wives GUI compatch.

## Override

- `common/scripted_effects/mpd_xp_calculator.txt`
- `common/scripted_effects/mpd_119_shift_helpers.txt`
- `common/traits/01_personality_overrides.txt`
- `common/traits/99_replaced_traits.txt`

## Repairs

- Removes the four parameterized culture-weight modifiers. AGOT does not define
  the generated `*_trait_more_common` / `*_trait_less_common` parameters for
  every personality trait, so CK3 rejects many instantiated calculator effects
  during post-validation.
- Uses optional `court_owner ?=` scoping and checks
  `has_variable = mpd_wn_active_task` before comparing the wet-nurse task
  variable.
- Uses the trait key as the explicit track key in `has_trait_xp` and
  `add_trait_xp`. CK3's `track = { ... }` shorthand creates one track named
  after the trait.
- Moves 111 invalid `same_opinion`, `same_opinion_if_same_faith`, and
  `opposite_opinion` fields out of 25 trait-track modifier blocks. CK3 1.19
  accepts these only as trait properties, so the rebase preserves each trait's
  normal (level-50) opinion values at trait scope. Other valid modifiers keep
  MPD's intended track scaling. The generated whole-file override also copies
  AGOT's six compatibility reader variables so it is self-contained.
- Keeps the threshold-safe cumulative counter helpers previously housed in the
  Dragon Wives compatch. These are MPD-only runtime repairs: missed thresholds
  catch up on the next qualifying action, the highest earned level is applied
  first, and all XP operations select the trait's shorthand track.
- Replaces **Immersive Personalities**' same-path `paranoid` override
  (`3596393244`) with an empty compatibility file. This leaves MPD's earlier
  definition as the sole source of the shorthand `paranoid` track. Re-declaring
  MPD's track in a later `zzz_` file creates two accumulated tracks and makes
  parameterized `add_trait_xp` calls fail.

Faith, guardian, parent, guardian-influence, and wet-nurse weighting are
otherwise unchanged.

Recompare this override after every update to Workshop mods `3717990443` or
`3596393244`.

Regenerate the Workshop-derived personality override with:

```sh
ck3mm mod generate agot_mpd_119_rebase
ck3mm mod generate agot_mpd_119_rebase --apply
```

The per-mod manifest declares both Workshop parents, the staged generator, and
the exact output paths it owns.

## Why this remains separate from the Dragon Wives compatch

This rebase repairs executable MPD behavior and is useful without Dragon Wives.
The Dragon Wives compatch owns only the shared `window_character.gui` merge.
Keeping the layers separate isolates volatile MPD script rebases from the
genuine cross-mod GUI merge.
