# agot_mpd_dragon_wives_compatch — module state

Final-integration layer over A Game of Thrones, AGOT Dragon Wives, AGOT - More
Personality Depth, and the local `agot_mpd_119_rebase`. Load after all four
parents.

## Ownership

The shared `window_character.gui` merge: Its base is Dragon Wives' file, which
carries AGOT's current character window plus the family rows the mod exists for.
Onto that go More Personality Depth's two deltas: the `mpd_view_hook` widget
that drives the `mpd_gui_roll_xp` scripted GUI, and the personality display
unhidden for player characters.

MPD's own `window_character.gui` lags AGOT — it still carries superseded
portrait offsets and omits AGOT's preparation-lobby guards and
`agot_pre_war_liege_portrait_vbox` — so only its two named deltas are taken, and
they are lifted out of its file by their surrounding anchors rather than
restated locally.

Generation also reads AGOT's file, purely to check that Dragon Wives has kept up
with it.

It deliberately owns nothing else. MPD's calculator and cumulative-counter
runtime repairs live in the preceding `agot_mpd_119_rebase`, so they remain
useful without Dragon Wives and can be rebased independently.

## Generation

```sh
ck3mm mod generate agot_mpd_dragon_wives_compatch
ck3mm mod generate agot_mpd_dragon_wives_compatch --apply
```

`ck3-tiger.conf` declares the dependency load order for static validation.

## Re-audit

`ck3mm upstream` reports which of the three pinned `window_character.gui` files
moved. The generator's anchors and the Dragon Wives currency check cover the
rest.
