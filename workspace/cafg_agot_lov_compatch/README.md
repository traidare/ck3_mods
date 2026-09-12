# cafg_agot_lov_compatch — module state

Thin variant of [cafg_agot_compatch](../cafg_agot_compatch/README.md) for
playsets that also run Legacy of Valyria. Load position: after the base compatch
and after LoV's AGOT compatibility patch. Publish candidate at `1.0.0`.

## Ownership

Three generated files, and nothing else:

- `gui/window_county_view.gui`
- `events/activities/tournaments/contest_events.txt`
- `events/lifestyles/governance_lifestyle/stewardship_domain_events.txt`

These are the paths where the base compatch and LoV genuinely contest the same
file. `gui/window_*.gui` and `events/*` both override whole-file, same path
only, so no keyed override can split them — a separate, later-loading item is
the only correct answer. Every other CaFG repair stays in the base compatch and
is not duplicated here.

`CONTESTED_EVENTS` in `implementation.py` is that list for the event files, and
membership is decided by which paths the bridge ships its own copy of. In
`stewardship_domain_events.txt` the two parents edit the same culture-clash
event without touching the same lines: the bridge adds the High Valyrian
offshoot-conversion branch that saves `scope:new_culture`, and CaFG replaces the
`set_county_culture` that consumes it with its granular
`E_kCAFG_convert_culture_in_all_county_provinces` call. Without this file the
bridge's copy is the last writer and CaFG's granular conversion is silently
reverted for every LoV playset.

## Generation

```sh
ck3mm mod generate cafg_agot_lov_compatch
ck3mm mod generate cafg_agot_lov_compatch --apply
```

`implementation.py` imports the base module's `merge_event_file`,
`generate_county_view`, and `EVENT_MERGES` table directly, substituting the LoV
AGOT bridge for AGOT as the parent source. The merge strategy, conflict
resolutions, county-view anchors, and post-merge assertions are therefore
defined once and cannot drift between the two published items. The
contest-events merge is conflict-free and asserts the same 1 `E_kCAFG_` call /
24 `#AGOT` markers as the base; the stewardship merge resolves the same single
`domain_conversion` hunk and asserts the same 1 call / 24 markers. Generation
fails if the base compatch stops merging either path, because the variant can
only rebase a merge the base still defines. The base generator is declared as a
`kind = "repository"` source and pinned in `sources.lock.json` like any other
input, so editing it shows up here as upstream drift.

## Pinned parent

The LoV source is Workshop item `3788296332`,
`Legacy of Valyria - AGOT 0.5.2.1 Compatch (Beta)` — **not** LoV base
`3403938445`. All three files must be built on the bridge's versions, because
the bridge is what actually loads in an AGOT playset.

The AGOT playset compatch modules keep their own `contest_events.txt` as the
local final-integration writer and load after this module:
[agot_playset_lov_compatch](../agot_playset_lov_compatch/README.md) merges AGOT,
LoV, MFA, and CaFG, and the always-on
[agot_playset_compatch](../agot_playset_compatch/README.md) merges the same file
without LoV for profiles that disable it. Both are supersets of the file here
and outrank it; this module stays the effective writer of the county view in
either case.

## Re-audit

**Two triggers.** Regenerate on any LoV bridge or CaFG update — the anchors and
marker counts will fail generation if either restructures. Separately, the pin
is to a bridge item that tracks one AGOT release: when LoV ships a bridge for a
newer AGOT version, repoint the source and regenerate rather than assuming this
item stays current.
