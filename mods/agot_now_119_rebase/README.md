# AGOT NOW - CK3 1.19 Rebase

Narrow executable-script repair for:

1. A Game of Thrones 0.4.40
2. AGOT Nobility of Westeros 1.2.5
3. This rebase

Load immediately after NOW and before the local NOW + LoV + Essos Expanded map
compatch.

This whole-file rebase preserves the parent logic while:

- using the existing `blackwater_change` title-change scope for Great Fork
  instead of the nonexistent `great_fork_change`;
- making Summerhall candidate comparisons optional while the events search for a
  second or third eligible family member, rather than dereferencing an unset
  saved scope; and
- redeclaring `namespace = agot_coa_events` in NOW's separate personal-COA event
  file, without which CK3 rejects `agot_coa_events.0003` and leaves its three
  calling decisions with a missing event.

The generated overrides are built from the current NOW source by:

```sh
scripts/generate-agot-playset-runtime-fixes.py
```

The generator checks all 39 candidate comparisons and stops when a NOW update
invalidates the source assumptions.

Recompare this file with NOW after every Workshop update.

Validated inputs:

- AGOT Workshop ID `2962333032`, version `0.4.40`
- NOW Workshop ID `3664900993`, version `1.2.5`
- CK3 `1.19.0.6`
