# agot_now_119_rebase — module state

Narrow executable-script repair for AGOT Nobility of Westeros. Load position:
immediately after NOW and before the local NOW + LoV + Essos Expanded map
compatch.

## Ownership

Generated whole-file same-path rebases of the NOW files it repairs. It preserves
the parent logic while:

- using the existing `blackwater_change` title-change scope for Great Fork
  instead of the nonexistent `great_fork_change`;
- making Summerhall candidate comparisons optional while the events search for a
  second or third eligible family member, rather than dereferencing an unset
  saved scope; and
- redeclaring `namespace = agot_coa_events` in NOW's separate personal-COA event
  file, without which CK3 rejects `agot_coa_events.0003` and leaves its three
  calling decisions with a missing event.

## Generation

```sh
ck3mm mod generate agot_now_119_rebase
ck3mm mod generate agot_now_119_rebase --apply
```

The `mod.toml` manifest selects NOW and this module's destination-specific
generator.

## Re-audit

The generator checks all 39 candidate comparisons and stops when a NOW update
invalidates the source assumptions. Recompare these overrides with NOW after
every Workshop update.

Pinned inputs:

- AGOT Workshop ID `2962333032`, version `0.4.40`
- NOW Workshop ID `3664900993`, version `1.2.5`
- CK3 `1.19.0.6`
