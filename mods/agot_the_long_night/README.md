# AGOT: The Long Night

## Requirements

- A Game of Thrones
- AGOT Submod Core
- AGOT : Seasons of Ice and Fire
- Roads to Power DLC

Use this load order:

1. A Game of Thrones
2. AGOT Submod Core
3. AGOT : Seasons of Ice and Fire
4. AGOT: The Long Night

The default start is the first winter at or after the canonical 298 AC
threshold, preceded by omens. The invasion uses an AI-controlled herald of the
Great Other, bounded threat milestones, a Horn-of-Winter Wall breach, a
political War for the Dawn, and the existing deep refugee and northern aftermath
systems.

Regenerate the vendored payload with:

```sh
ck3mm mod check agot_the_long_night
ck3mm mod generate agot_the_long_night
```

The `workspace/agot_the_long_night/mod.toml` manifest declares the staged
generator and pins Seasons Workshop item `3377641022`'s
`events/season_events.txt`. It was last rebased for manifest
`2065378484774676314` (SHA-256
`f5f618b90ff2f5697517310b4d3c63f95c44ecf56150a2d1ad4cb3e26b217c04`). Re-audit
and regenerate whenever that hash changes.
