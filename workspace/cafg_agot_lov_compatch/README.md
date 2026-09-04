# cafg_agot_lov_compatch — module state

Thin variant of [cafg_agot_compatch](../cafg_agot_compatch/README.md) for
playsets that also run Legacy of Valyria. Load position: after the base compatch
and after LoV's AGOT compatibility patch. Publish candidate at `1.0.0`.

## Ownership

Exactly two generated files, and nothing else:

- `gui/window_county_view.gui`
- `events/activities/tournaments/contest_events.txt`

These are the only two paths where the base compatch and LoV genuinely contest
the same file. `gui/window_*.gui` and `events/*` both override whole-file, same
path only, so no keyed override can split them — a separate, later-loading item
is the only correct answer. Every other CaFG repair stays in the base compatch
and is not duplicated here.

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
24 `#AGOT` markers as the base. The base generator is declared as a
`kind = "repository"` source and pinned in `sources.lock.json` like any other
input, so editing it shows up here as upstream drift.

## Pinned parent

The LoV source is Workshop item `3719888822`, `Legacy of Valyria - AGOT 0.5.1` —
**not** LoV base `3403938445`. Both files must be built on the bridge's
versions, because the bridge is what actually loads in an AGOT playset.

`mods/agot_full_playset_compatch` keeps its own three-way LoV + MFA + CaFG
`contest_events.txt` as the local final-integration writer. That file is a
superset of this one and is not replaced by it.

## Re-audit

**Two triggers.** Regenerate on any LoV bridge or CaFG update — the anchors and
marker counts will fail generation if either restructures. Separately, the pin
is to a bridge item that tracks one AGOT release: when LoV ships a bridge for a
newer AGOT version, repoint the source and regenerate rather than assuming this
item stays current.
