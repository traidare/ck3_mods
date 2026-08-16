# ant_agot_vanilla_balance — module state

Balance patch for **Any New Traditions** under its `ary_rule_vv` (Vanilla
Version) game rule in an AGOT playset. Load position: after A Game of Thrones,
Any New Traditions, and Any New Traditions Compatibility AGOT.

## Ownership

Same-key overrides only; no `replace_path`, so the module is save-compatible and
existing traditions, modifiers, MAA regiments, and buildings adopt the patched
values on load.

The fantasy traditions are deliberately **not** rebalanced. Shared common
buildings used by the Vanilla ruleset are rebalanced globally, and AI
construction is enabled for both variants of ANT's player-only duchy buildings.

## Generation

The `mod.toml` manifest declares both ANT Workshop dependencies and the staged
generator. Regenerate from the repository root:

```sh
ck3mm mod generate ant_agot_vanilla_balance
ck3mm mod generate ant_agot_vanilla_balance --apply
```

## Re-audit

The generator fails when an expected source definition or required field is
missing instead of silently emitting an incomplete patch. That failure is the
re-audit trigger; regenerate and review the diff after any ANT update.
