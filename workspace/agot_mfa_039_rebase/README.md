# agot_mfa_039_rebase — module state

Pinned narrow runtime rebase of AGOT - Much Faster Activities onto current AGOT
and CK3 1.19. Load position: immediately after MFA, before any MFA + LoV / CaFG
/ Citadel University compatibility layer.

## Ownership

Every file the module ships is derived by the generator, and it ships only the
files it changes. MFA's additive files, and the whole-file overrides it needs no
repair to, remain supplied by the Workshop parent one load position below and
are not copied here: an override identical to the provider beneath it changes
nothing at runtime, and only offers a way to freeze stale content across the
next MFA release.

## Canon-continuity guards

`tournament_events.txt` carries the guards for the tournament deaths a
contestant does not choose: the pas d'armes bouts `1110`, `1141` and `1151`, the
disappearance in `1230`, and the collapsing stands in `1280`. Each wraps its
`death` in `agot_cc_event_death_protected_trigger = no`, a trigger the AGOT:
Canon Continuity module defines and its own game rule switches off. The
duplicate deaths inside `show_as_tooltip` are display copies of those same
outcomes and are left alone. The melee accident is not guarded here; it runs
through `tournament_accidental_death_effect`, which that module redefines.

## Repairs and evidence

- **`tradition_land_of_the_bow`.** MFA restores vanilla's tournament block for a
  tradition AGOT removes; the rebase keeps AGOT's block disabled.
- **Delayed playdate relay.** A playdate can end before the delayed relay
  executes, so the relay verifies the activity scope still exists before
  checking its phase.
- **695 province-scope references.** MFA's delayed relays retain
  `scope:activity` but do not inherit the engine-supplied `scope:province` from
  the pulses they replace. Across 28 on-action files, 695 event-selection checks
  still used that unavailable scope; they are pointed at the equivalent
  preserved `scope:activity.activity_location`. Covers accelerated education,
  coronations, chariot races, feasts, festivals, funerals, hunts, pilgrimages,
  playdates, tours, tournaments, weddings, and witch rituals.
- **Hunt relay.** It ran from a character root while six event-selection checks
  dereferenced `root.activity_host`, which requires an activity; its success
  weight likewise read an activity script value from that character root. Both
  now use the relay's preserved `scope:activity`, and its province-owner check
  compares participation against that activity instead of the character root.
  This removes the repeated `activity_host` type mismatch and the null
  relationship and opinion targets that follow it.
- **19 fractional weights.** Five of those event-selection lists used fractional
  top-level weights. CK3 1.19 treats fractional random-list weights as zero,
  silently disabling the affected rare outcomes. The generator multiplies every
  weight in each affected list by ten, preserving relative probabilities with
  integral weights.

## Generation

```sh
ck3mm mod generate agot_mfa_039_rebase
ck3mm mod generate agot_mfa_039_rebase --apply
```

The `mod.toml` manifest selects the MFA source and this module's
destination-specific generator.

## Re-audit

The generator checks the exact playdate relay block, the expected per-file count
of all 695 location references, the hunt relay's six host links, one success
value, one participant check, and all five affected random lists with their 19
fractional weights. It stops when an MFA update invalidates any source
assumption; that failure is the re-audit trigger.

The exact upstream files the generator consumed, and their hashes, are recorded
in `sources.lock.json`.
