# AGOT 0.4.40 - Much Faster Activities Rebase

Pinned compatibility layer for:

1. A Game of Thrones 0.4.40
2. AGOT - Much Faster Activities 1.1.1
3. This rebase

The Workshop mod has 27 whole-file overrides of AGOT activity, event, and GUI
files. The generated rebase was revalidated unchanged against AGOT 0.4.40, so
the verified MFA 1.1.1 timing, pulse relay, cooldown, wait-time, and
activity-window behavior is retained. One unrelated generated override was
corrected: MFA had restored vanilla's `tradition_land_of_the_bow` tournament
block even though AGOT removes that tradition; the rebase keeps AGOT's block
disabled. Its delayed playdate relay now also verifies that the activity scope
still exists before checking its phase, because a playdate can end before the
delayed relay executes.

MFA's delayed relays retain `scope:activity`, but do not inherit the
engine-supplied `scope:province` from the pulses they replace. Across 28
on-action files, 695 event-selection checks still used that unavailable scope.
The generated rebase points those checks to the equivalent preserved
`scope:activity.activity_location`. This covers accelerated education,
coronations, chariot races, feasts, festivals, funerals, hunts, pilgrimages,
playdates, tours, tournaments, weddings, and witch rituals.

The hunt relay also ran from a character root while six event-selection checks
dereferenced `root.activity_host`, which requires an activity. Its success
weight likewise read an activity script value from that character root. Both now
use the relay's preserved `scope:activity`; its province-owner check also
compares participation against that activity instead of the character root. This
removes the repeated `activity_host` type mismatch and the null
relationship/opinion targets that followed it in the 2026-07-31 crash logs.

Five of those event-selection lists used 19 fractional top-level weights. CK3
1.19 treats fractional random-list weights as zero, silently disabling the
affected rare outcomes. The generator multiplies every weight in each affected
list by ten, preserving the original relative probabilities with integral
weights.

The delayed-pulse on-action overrides are generated from current MFA sources by:

```sh
ck3mm mod check agot_mfa_039_rebase
ck3mm mod generate agot_mfa_039_rebase
```

The `.ck3mm/mod.toml` manifest selects the MFA source and this module's
destination-specific generator. It checks the exact playdate relay block, the
expected per-file count of all 695 location references, the hunt relay's six
host links, one success value, and one participant check, and all five affected
random lists with their 19 fractional weights. It stops when an MFA update
invalidates any source assumption.

MFA's additive files remain supplied by the Workshop parent. Load this mod
immediately after MFA and before compatibility layers that merge MFA with LoV,
CaFG, Citadel University, or other activity mods.

Validated inputs:

- AGOT Workshop ID `2962333032`, version `0.4.40`
- MFA Workshop ID `3723597729`, version `1.1.1`
