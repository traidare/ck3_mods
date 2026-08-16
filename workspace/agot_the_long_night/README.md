# agot_the_long_night — module state

Standalone AGOT submod adding the Long Night invasion. Parents: A Game of
Thrones, AGOT Submod Core, AGOT : Seasons of Ice and Fire, and the Roads to
Power DLC.

## Ownership

The module owns its own additive content: the winter start threshold and omens,
the AI herald of the Great Other, the bounded threat milestones, the
Horn-of-Winter Wall breach, the political War for the Dawn, and the refugee and
northern aftermath systems. It does not own parent content.

## Generation

```sh
ck3mm mod generate agot_the_long_night
ck3mm mod generate agot_the_long_night --apply
```

The `mod.toml` manifest declares the staged generator and pins Seasons Workshop
item `3377641022`'s `events/season_events.txt`.

## Re-audit

The vendored Seasons payload was last rebased for manifest `2065378484774676314`
(SHA-256 `f5f618b90ff2f5697517310b4d3c63f95c44ecf56150a2d1ad4cb3e26b217c04`).
Re-audit and regenerate whenever that hash changes.
