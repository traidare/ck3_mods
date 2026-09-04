# AGOT - Mayham + Armies of Westeros Compatch

Makes aGoT: Mayham's tradition balance and AGOT - Armies of Westeros'
men-at-arms overhaul work together instead of overwriting each other.

## Requirements and load order

1. A Game of Thrones
2. aGoT: Mayham
3. AGOT - Armies of Westeros
4. Armies of Westeros REMASTERED (optional)
5. This compatch

## What it does

Armies of Westeros' culture-tradition definitions are the baseline, and Mayham's
49 balance changes are reapplied across the 45 affected traditions. Current
AGOT's Stormlands, Frozen Shoremen, Harbormen, Stoneborn, and Wolfswood Clansmen
traditions are carried through as well, since Armies of Westeros defines them
with divergent values. Ibbenese and Ironmen use AGOT's complete definitions
because both balance parents omit current AGOT parameters. Mayham's own
Stoneborn and Wolfswood deltas apply on top. You keep Armies of Westeros'
men-at-arms unlocks, parameters, costs, and AI behaviour together with Mayham's
intended opinion values and AGOT's current cultural-tradition bonuses.
Greenborn, Ironborn, and Marcher remain owned by the complete Armies of Westeros
file rather than being declared twice.

It also repairs one malformed token in Armies of Westeros' Arbor tradition that
CK3 rejects during load.

## Compatibility

The compatch uses same-key overrides in one uniquely named tradition file and
does not use `replace_path`. It is save-compatible: the merged tradition
definitions take effect after loading a save with the compatch enabled.
