# AGOT NOW - CK3 1.19 Rebase

Narrow executable-script repair for:

1. A Game of Thrones 0.4.40
2. AGOT Nobility of Westeros 1.2.4.1
3. This rebase

Load immediately after NOW and before the local NOW + LoV + Essos Expanded map
compatch.

The current NOW `agot_now_on_actions.txt` uses three forms rejected by CK3 1.19.
This whole-file rebase preserves the parent logic while:

- making its seven population modifiers permanent by omitting the duration,
  matching current CK3 and AGOT permanent province-modifier examples;
- replacing `set_government` with `change_government`;
- replacing `set_de_jure_liege` with `set_de_jure_liege_title`;
- giving the scope-less game-start hook a dedicated effect that explicitly
  scopes the three command-title holders;
- using the existing `blackwater_change` title-change scope for Great Fork
  instead of the nonexistent `great_fork_change`; and
- correcting the dummy Great Fork title's invalid `c_great_for` capital
  reference to `c_great_fork`;
- making Summerhall candidate comparisons optional while the events search for a
  second or third eligible family member, rather than dereferencing an unset
  saved scope; and
- redeclaring `namespace = agot_coa_events` in NOW's separate personal-COA event
  file, without which CK3 rejects `agot_coa_events.0003` and leaves its three
  calling decisions with a missing event.

The Summerhall and personal-COA event overrides are generated from the current
NOW source by:

```sh
scripts/generate-agot-playset-runtime-fixes.py
```

The generator checks all 39 candidate comparisons and stops when a NOW update
invalidates the source assumptions.

Recompare this file with NOW after every Workshop update.

Validated inputs:

- AGOT Workshop ID `2962333032`, version `0.4.40`
- NOW Workshop ID `3664900993`, version `1.2.4.1`
- CK3 `1.19.0.6`
