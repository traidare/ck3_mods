# agot_adventurer_tweaks — module state

Reimplements the intent of Workshop mod **AGOT - Small Tweaks for Adventurers**
(`3347454813`) as key-level overrides on current AGOT. Load position: after AGOT
and after anything else redefining the three owned definitions.

## Ownership

Three AGOT definitions, redefined by key in newly named files. No AGOT file is
overridden by path.

- `common/decisions/agot_decisions/zz_agot_adventurer_bastard_decisions.txt` —
  `agot_expose_my_true_parentage_decision`, `agot_royal_bastard_claim_decision`
- `common/character_interactions/zz_agot_adventurer_evict_interaction.txt` —
  `evict_adventurer_interaction`

## Why key-level redefinition, not the parent's layer

The parent ships whole-file overrides of `00_agot_bastard_decisions.txt`,
`06_ep3_laamp_interactions.txt`, and `00_artifact_interactions.txt`, forked from
an AGOT base several game versions old. Adopting that layer would revert every
upstream change in those files. Extracting only the changed definitions at
generation time lets unrelated AGOT edits flow through untouched, and reduces
the re-audit surface to three definitions.

## Changes and evidence

The parent's delta was separated from stale-fork drift by diffing each
definition's gating blocks against both current AGOT and current vanilla. A
parent line that also appears in either baseline is drift, not intent. Four
deliberate edits survive that filter; three are implemented here.

- `agot_expose_my_true_parentage_decision` and
  `agot_royal_bastard_claim_decision`: `is_landed = yes` becomes
  `OR = { is_landed = yes  is_landless_adventurer = yes }`. The parent dropped
  the gate outright in the second decision, which also admits ordinary unlanded
  courtiers; the landed-or-landless form keeps them out and matches what the
  same author did in the first.
- `evict_adventurer_interaction`: adds `highest_held_title_tier = tier_county`
  to the actor, and narrows AGOT's `target_is_same_character_or_above` subrealm
  check to `this = scope:actor`. Only the camp county's own holder can evict,
  and only at county tier. Counties held directly by a duke or above therefore
  cannot evict — an accepted consequence of the chosen rule.

## Deliberate exclusion

The parent's fourth edit lets landless adventurers steal illustrious dragon
eggs: a `has_variable = dragon_egg` exception to the steal-artifact rarity gate,
plus removal of the `agot_swiper_no_swiping` guard. That variable is set only by
AGOT's dragon-egg and dragonkeeper scripts and is read through
`agot_artifact_can_take`, so the edit is dragon-egg behavior in full. **AGOT
More Dragon Eggs** (`3388366564`) owns it. With that edit excluded,
`00_artifact_interactions.txt` carries no remaining delta and is not shipped.
`06_ep3_laamp_interactions.txt` contributes only the eviction change.

## Source assertions

- The AGOT bastard-decisions source must contain exactly two `is_landed = yes`
  occurrences. Both are patch anchors today; a third means AGOT gated another
  decision in that file.
- Each of the four replacements is exact-count checked, so a reworded or
  reordered upstream gate fails generation instead of silently emitting a stale
  definition.

Anchors are deliberately minimal, so unrelated upstream edits near them (an
adjusted `prestige_level`, for instance) regenerate cleanly rather than failing.

`ai_potential` in the eviction interaction raises a ck3-tiger deprecation
warning. It is AGOT's own code, carried through verbatim, and is not repaired
here.

## Generation

```sh
ck3mm mod generate agot_adventurer_tweaks
ck3mm mod generate agot_adventurer_tweaks --apply
```

## Re-audit

Recompare after every update to Workshop mod `2962333032`, and whenever another
playset mod begins defining any of the three owned keys — currently AGOT is the
only other definer.
