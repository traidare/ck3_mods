# AGOT NOW 1.2.4 - CK3 1.19 Rebase

Narrow executable-script repair for:

1. A Game of Thrones 0.4.39
2. AGOT Nobility of Westeros 1.2.4
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
  instead of the nonexistent `great_fork_change`.

Recompare this file with NOW after every Workshop update.

Validated inputs:

- AGOT Workshop ID `2962333032`, version `0.4.39`
- NOW Workshop ID `3664900993`, version `1.2.4`
- CK3 `1.19.0.6`
