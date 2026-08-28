# agot_mayham_aow_compatch — module state

Generated final-integration layer over A Game of Thrones, aGoT: Mayham, and
AGOT - Armies of Westeros (with Armies of Westeros REMASTERED optional).

## Ownership

The module owns same-key tradition overrides in one uniquely named tradition
file plus a same-path Armies of Westeros rebase. It does not use `replace_path`,
and it is save-compatible.

- **Merged traditions.** Armies of Westeros' culture-tradition definitions are
  the baseline; Mayham's 49 balance changes are reapplied across the 45 affected
  traditions. Current AGOT's Stormlands, Frozen Shoremen, Harbormen, Stoneborn,
  and Wolfswood Clansmen traditions are carried through because Armies of
  Westeros defines them with divergent values; Mayham's own Stoneborn and
  Wolfswood deltas apply on top. This preserves Armies of Westeros' MAA unlocks,
  parameters, costs, and AI behavior alongside Mayham's opinion values and
  AGOT's current cultural-tradition bonuses.
- **Arbor token repair.** Armies of Westeros ships one bare
  `reveler_traits_more_valued` token in the Arbor tradition; CK3 treats it as
  malformed parameter syntax during load. The generated same-path rebase
  preserves the complete AoW file and adds only the missing `= yes`. The later
  merged definitions still own the intentional Mayham/AoW/AGOT semantics.

## Generation

The `mod.toml` manifest declares the AGOT, Mayham, and Armies of Westeros
sources and the generator's owned outputs. Regenerate from the repository root:

```sh
ck3mm mod generate agot_mayham_aow_compatch
ck3mm mod generate agot_mayham_aow_compatch --apply
```

## Re-audit

The generator verifies the complete AGOT-to-Mayham delta manifest and fails
rather than silently emitting an incomplete merge on:

- a missing definition,
- an unexpected upstream change,
- the malformed Arbor token changing,
- Armies of Westeros omitting any AGOT definition from a file it overrides
  wholesale, or
- an ambiguous field.

Any of those failures is the re-audit trigger.
