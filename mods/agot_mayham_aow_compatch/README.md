# AGOT - Mayham + Armies of Westeros Compatch

Compatibility patch for:

1. A Game of Thrones
2. aGoT: Mayham
3. AGOT - Armies of Westeros
4. Armies of Westeros REMASTERED (optional)
5. This compatch

The compatch uses Armies of Westeros' culture-tradition definitions as its
baseline and reapplies Mayham's 55 balance changes across the 51 affected
traditions. It also carries forward AGOT 0.4.40's updated Stormlands, Frozen
Shoremen, Harbormen, and Wolfswood Clansmen traditions, which both Mayham and
Armies of Westeros still define using the older AGOT values. This preserves
Armies of Westeros' MAA unlocks, parameters, costs, and AI behavior while
retaining Mayham's intended opinion values and AGOT's current cultural-tradition
bonuses.

Armies of Westeros also ships one bare `reveler_traits_more_valued` token in the
Arbor tradition. CK3 treats it as malformed parameter syntax during load. The
generated same-path rebase preserves the complete AoW file and adds only the
missing `= yes`; the later merged definitions still own the intentional
Mayham/AoW/AGOT semantics.

It uses same-key overrides in one uniquely named tradition file and does not use
`replace_path`. It is compatible with existing saves; the merged tradition
definitions take effect after loading the save with the compatch enabled.

## Regeneration

Run `scripts/generate-agot-mayham-aow-compatch.py` from the repository root
after updating AGOT, Mayham, or Armies of Westeros. The generator verifies the
complete AGOT-to-Mayham delta manifest and fails on missing definitions,
unexpected upstream changes, the malformed Arbor token changing, or ambiguous
fields rather than silently emitting an incomplete merge.
