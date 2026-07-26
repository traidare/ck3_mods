# AGOT 0.4.39 - Much Faster Activities Rebase

Pinned compatibility layer for:

1. A Game of Thrones 0.4.39
2. AGOT - Much Faster Activities 1.1.1
3. This rebase

The Workshop mod has 27 whole-file overrides of AGOT activity, event, and GUI
files. Those AGOT files are identical in 0.4.38 and 0.4.39, so the verified MFA
1.1.1 timing, pulse relay, cooldown, wait-time, and activity-window behavior is
retained. One unrelated generated override was corrected: MFA had restored
vanilla's `tradition_land_of_the_bow` tournament block even though AGOT removes
that tradition; the rebase keeps AGOT's block disabled. Its delayed playdate
relay now also verifies that the activity scope still exists before checking its
phase, because a playdate can end before the delayed relay executes.

MFA's delayed relays retain `scope:activity`, but do not inherit the
engine-supplied `scope:province` from the pulses they replace. Across 28
on-action files, 695 event-selection checks still used that unavailable scope.
The generated rebase points those checks to the equivalent preserved
`scope:activity.activity_location`. This covers accelerated education,
coronations, chariot races, feasts, festivals, funerals, hunts, pilgrimages,
playdates, tours, tournaments, weddings, and witch rituals.

Five of those event-selection lists used 19 fractional top-level weights. CK3
1.19 treats fractional random-list weights as zero, silently disabling the
affected rare outcomes. The generator multiplies every weight in each affected
list by ten, preserving the original relative probabilities with integral
weights.

The delayed-pulse on-action overrides are generated from current MFA sources by:

```sh
scripts/generate-agot-playset-runtime-fixes.py
```

The generator checks the exact playdate relay block, the expected per-file count
of all 695 location references, and all five affected random lists with their 19
fractional weights. It stops when an MFA update invalidates any source
assumption.

MFA's additive files remain supplied by the Workshop parent. Load this mod
immediately after MFA and before compatibility layers that merge MFA with LoV,
CaFG, Citadel University, or other activity mods.

Validated inputs:

- AGOT Workshop ID `2962333032`, version `0.4.39`
- MFA Workshop ID `3723597729`, version `1.1.1`
