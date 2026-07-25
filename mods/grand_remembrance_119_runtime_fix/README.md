# Grand Remembrance 1.8.1 - CK3 1.19 Runtime Fix

Narrow runtime repair for **Grand Remembrance** (`3678529052`, version `1.8.1`)
with its AGOT compatibility submod (`3683507542`).

Load this mod immediately after the Grand Remembrance AGOT compatibility submod.

## Repair

The chronicle window exists before a playable character does. Its original
`visible` expression always constructed `GetPlayer.MakeScope`, so the `is_shown`
trigger was sometimes invoked with an invalid character root and emitted an
untyped `(no character)` error on every GUI refresh.

This mod overrides:

- `gui/gr_chronicle_window.gui`, copied from Grand Remembrance with only its
  visibility expression changed to check `GetPlayer.IsValid` before invoking the
  scripted GUI; and
- the `gr_chronicle_window` scripted-GUI entry, retaining the parent's normal
  character-scope checks once the GUI has supplied a valid player.

The invalid test guard attempted in version `0.1.0` could not work: trigger
logic cannot repair a root scope that is already invalid before `is_shown`
begins evaluating.

Recompare this override after every update to Workshop mod `3678529052`.
