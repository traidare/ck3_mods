# agot_longnight_submodcore_dfp_compatch — module state

Optional animation-only final-integration layer for AGOT, AGOT Submod Core,
Dynamic Family Portrait, its AGOT bridge, and AGOT: The Long Night & Azor Ahai.

## Ownership

The module owns only `gfx/portraits/portrait_animations/animations.txt`. The
generated file starts from the Long Night parent, preserving its five wight
poses and AGOT's animation body, then adds Submod Core's bow pose and the DFP
AGOT pose region. DFP's obsolete `CIP_agressive_longsword` and active
`use_longsword_default_trigger` are intentionally omitted.

All four consumed animation files are SHA-256 pinned. Generation also asserts
196 retained DFP poses, five wight poses, one bow pose, and one long-axe pose.

## Load order

Load after every parent and after the optional Long Night runtime fix. It is the
final writer only when the Long Night parent is enabled; disable this module
whenever that parent is disabled.

## Generation

```sh
ck3mm mod generate agot_longnight_submodcore_dfp_compatch
ck3mm mod generate agot_longnight_submodcore_dfp_compatch --apply
```

## Re-audit

Re-audit after any update to AGOT, AGOT Submod Core, Dynamyc Family Portrait
(AGOT), or AGOT: The Long Night & Azor Ahai. A pin or structural assertion
failure means the corresponding parent delta must be reviewed before updating
the generated output.
