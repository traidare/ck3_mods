# Grand Remembrance 1.8.1 - CK3 1.19 Runtime Fix

Narrow runtime repair for **Grand Remembrance** (`3678529052`, version `1.8.1`)
with its AGOT compatibility submod (`3683507542`).

Load this mod immediately after the Grand Remembrance AGOT compatibility submod.

## Repair

The chronicle window's `is_shown` trigger was evaluated while the GUI had no
character scope. Its first trigger, `is_alive = yes`, then emitted an untyped
`(no character)` error on every GUI refresh.

This mod overrides only the `gr_chronicle_window` scripted-GUI entry. It:

- saves the possibly absent GUI character as a temporary scope;
- requires `exists = scope:character` before entering that scope;
- uses the null-safe `scope:character ?=` form for character-only checks; and
- gates the variable comparison behind `has_variable`.

The archived full-playset crash log contained 7,794 errors from the original
`gr_chronicle_window:is_shown` line.

Recompare this override after every update to Workshop mod `3678529052`.
