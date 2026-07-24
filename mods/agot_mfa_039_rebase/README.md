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
that tradition; the rebase keeps AGOT's block disabled.

MFA's additive files remain supplied by the Workshop parent. Load this mod
immediately after MFA and before compatibility layers that merge MFA with LoV,
CaFG, Citadel University, or other activity mods.

Validated inputs:

- AGOT Workshop ID `2962333032`, version `0.4.39`
- MFA Workshop ID `3723597729`, version `1.1.1`
