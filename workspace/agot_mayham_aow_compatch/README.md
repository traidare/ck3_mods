# agot_mayham_aow_compatch — module state

Generated final-integration layer over A Game of Thrones, aGoT: Mayham, and
AGOT - Armies of Westeros (with Armies of Westeros REMASTERED optional).

## Ownership

The module owns same-key tradition overrides in one uniquely named tradition
file plus a same-path Armies of Westeros rebase. It does not use `replace_path`,
and it is save-compatible.

- **Merged traditions.** Armies of Westeros' culture-tradition definitions are
  the baseline; Mayham's 48 balance changes are reapplied across the 44 affected
  traditions. Current AGOT's Stormlands, Frozen Shoremen, Harbormen, Stoneborn,
  and Wolfswood Clansmen traditions are carried through because Armies of
  Westeros defines them with divergent values; Mayham's own Stoneborn and
  Wolfswood deltas apply on top. This preserves Armies of Westeros' MAA unlocks,
  parameters, costs, and AI behavior alongside Mayham's opinion values and
  AGOT's current cultural-tradition bonuses.
- **Four restored traditions.** Armies of Westeros' whole-file tradition
  overrides omit `tradition_agot_ib`, `tradition_agot_ibbenese`,
  `tradition_agot_ibbatese`, and `tradition_agot_sarese`, and it loads after
  both parents, so nothing else can supply them. AGOT's Ibbenese, Sarese, and
  Ibbatese cultures each reference two of the four, which fails their key
  references at load and leaves each culture two traditions short. All four are
  restored from current AGOT with Mayham's balance deltas applied.
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
- a change to the set of definitions Armies of Westeros omits, or
- an ambiguous field.

Any of those failures is the re-audit trigger.
