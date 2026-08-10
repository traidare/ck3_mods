# AGOT - Mayham + Armies of Westeros Compatch

Compatibility patch for:

1. A Game of Thrones
2. aGoT: Mayham
3. AGOT - Armies of Westeros
4. Armies of Westeros REMASTERED (optional)
5. This compatch

The compatch uses Armies of Westeros' culture-tradition definitions as its
baseline and reapplies Mayham's 48 balance changes across the 44 affected
traditions. It also carries forward current AGOT's updated Stormlands, Frozen
Shoremen, Harbormen, Stoneborn, and Wolfswood Clansmen traditions, which Armies
of Westeros still defines using older AGOT values. Mayham now matches current
AGOT on the first three and applies separate Stoneborn and Wolfswood balance
deltas. This preserves Armies of Westeros' MAA unlocks, parameters, costs, and
AI behavior while retaining Mayham's intended opinion values and AGOT's current
cultural-tradition bonuses.

Armies of Westeros also ships one bare `reveler_traits_more_valued` token in the
Arbor tradition. CK3 treats it as malformed parameter syntax during load. The
generated same-path rebase preserves the complete AoW file and adds only the
missing `= yes`; the later merged definitions still own the intentional
Mayham/AoW/AGOT semantics.

It uses same-key overrides in one uniquely named tradition file and does not use
`replace_path`. It is compatible with existing saves; the merged tradition
definitions take effect after loading the save with the compatch enabled.

## Regeneration

The `workspace/agot_mayham_aow_compatch/mod.toml` manifest declares the AGOT,
Mayham, and Armies of Westeros sources and the generator's owned outputs.
Regenerate from the repository root:

```sh
ck3mm mod generate agot_mayham_aow_compatch
ck3mm mod generate agot_mayham_aow_compatch --apply
```

The generator verifies the complete AGOT-to-Mayham delta manifest and fails on
missing definitions, unexpected upstream changes, the malformed Arbor token
changing, or ambiguous fields rather than silently emitting an incomplete merge.
