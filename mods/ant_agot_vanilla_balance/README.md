# Any New Traditions - AGOT Vanilla Balance

Balance patch for **Any New Traditions** when its game rule is set to **Vanilla
Version** (`ary_rule_vv`) in an **A Game of Thrones** playset.

## Load order

Load this mod after:

1. A Game of Thrones
2. Any New Traditions
3. Any New Traditions Compatibility AGOT

The patch uses same-key overrides and no `replace_path`, so it is compatible
with existing saves. Existing traditions, modifiers, MAA regiments, and
buildings adopt the patched values after loading the save.

The fantasy traditions are not rebalanced. Shared common buildings used by the
Vanilla ruleset are rebalanced globally, and AI construction is enabled for both
variants of ANT's player-only duchy buildings.

## Regeneration

The per-mod manifest declares both ANT Workshop dependencies and the staged
generator. Regenerate from the repository root:

```sh
ck3mm mod generate ant_agot_vanilla_balance
ck3mm mod generate ant_agot_vanilla_balance --apply
```

The generator fails when an expected source definition or required field is
missing instead of silently emitting an incomplete patch.
