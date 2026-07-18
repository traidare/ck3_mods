# AGOT: The Long Night+ + Submod Core + DFP Compatch

Compatibility patch for:

- A Game of Thrones
- AGOT Submod Core
- Dynamic Family Portrait
- Dynamyc Family Portrait
- AGOT: The Long Night+

## Load order

1. A Game of Thrones
2. AGOT Submod Core
3. Dynamic Family Portrait
4. Dynamyc Family Portrait (AGOT)
5. AGOT: The Long Night+
6. AGOT: Long Night+ - Submod Core & DFP Compatch

## What this merges

All five dependencies replace
`gfx/portraits/portrait_animations/animations.txt`. This compatch uses The Long
Night+'s current file as its base and restores:

- Dynamic Family Portrait's custom `CIP_*` poses
- AGOT Submod Core's `hold_bow_idle` pose
- The Long Night+'s five fixed wight poses
- Current AGOT animation behavior, including `hold_long_axe_idle`

The DFP AGOT patch contains two active references to AGOT's disabled
`use_longsword_default_trigger`. This compatch removes the unreachable
`CIP_agressive_longsword` variant and makes `CIP_agressive` use DFP's generic
one-handed sword presentation. This avoids the corresponding unknown-trigger
errors without adding a global compatibility trigger.
