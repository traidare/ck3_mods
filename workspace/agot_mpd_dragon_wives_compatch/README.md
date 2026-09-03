# agot_mpd_dragon_wives_compatch — module state

Hand-authored final-integration layer over A Game of Thrones, AGOT Dragon Wives,
AGOT - More Personality Depth, and the local `agot_mpd_119_rebase`. Load after
all four parents.

## Ownership

The module owns exactly one file: the shared `window_character.gui` merge. It
combines Dragon Wives' special family rows with AGOT's current character window
and carries More Personality Depth's two deltas: the personality display
unhidden for player characters, and the `mpd_view_hook` widget that drives the
`mpd_gui_roll_xp` scripted GUI.

More Personality Depth's own `window_character.gui` lags AGOT — it still carries
superseded portrait offsets and omits AGOT's newer preparation-lobby guards and
`agot_pre_war_liege_portrait_vbox`. Take MPD's named deltas into the merge,
never its file wholesale. The merge otherwise tracks AGOT verbatim; deviations
from it should be only Dragon Wives' family rows and the two MPD deltas above.

It deliberately owns nothing else. MPD's calculator and cumulative-counter
runtime repairs live in the preceding `agot_mpd_119_rebase`, so they remain
useful without Dragon Wives and can be rebased independently.

## Generation

None. This module has no `mod.toml` and no generator; the payload is
hand-authored. `ck3-tiger.conf` declares the dependency load order for static
validation only.

```sh
ck3mm mod validate agot_mpd_dragon_wives_compatch
```

## Re-audit

Manual. Recompare the merged window against all three parents after any update
to AGOT, AGOT Dragon Wives, or AGOT - More Personality Depth that touches
`window_character.gui`, and whenever `agot_mpd_119_rebase` changes its trait or
GUI surface.
