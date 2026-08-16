# agot_debug_house_transfer — module state

A temporary player-facing debug tool, not a compatch layer and not a runtime
repair. It was kept out of `agot_playset_runtime_fixes` because that module is
reserved for evidenced executable-script failures, and because its generator
owns the whole `common/` tree, so a hand-authored file there would be deleted on
the next `ck3mm mod generate`.

Load position: anywhere after AGOT. It defines new keys only and overrides no
parent path, so it has no load-order requirement beyond AGOT itself.

## Ownership

Three hand-authored files, all new keys:

| path                                                                    | contents                                                                 |
| ----------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| `common/character_interactions/zz_debug_house_transfer_interaction.txt` | `zz_debug_join_my_house_interaction`                                     |
| `common/scripted_effects/zz_debug_house_transfer_effects.txt`           | `zz_debug_set_house_effect`, `zz_debug_move_descendants_to_house_effect` |
| `localization/english/zz_debug_house_transfer_l_english.yml`            | interaction name, description, two option labels                         |

## Design notes

- The interaction sits in AGOT's `interaction_category_agot_debug` (Workshop
  `2962333032`, `01_agot_character_interaction_categories.txt`), which is the
  only red debug category the playset defines. Unlike AGOT's own debug
  interactions it deliberately omits `debug_only = yes`, so it is usable without
  launching CK3 with `-debug_mode`.
- `set_house = <dynasty_house>` is the documented character effect
  (`script_docs/effects.log`); it is what AGOT's own
  `agot_convert_house_and_descendants_effect` uses.
- The descendant walk mirrors AGOT's four-generation `every_child` nest in
  `00_agot_dynasty_effects.txt`. Paradox Script has no recursion, so depth is
  fixed; descendants beyond the fifth generation are not moved.
- The optional coat-of-arms reset follows AGOT's
  `set_coa = <new house>.house_founder.dynasty` pattern, guarded by `exists`
  because a revived or scripted house need not have a living founder.
- It does **not** replicate AGOT's wider house-conversion bookkeeping: the
  `legitimate_house` title variables, house-relation modifiers, and
  `agot_coa_events.0001` are untouched. That is intentional for a debug tool —
  the effects there are large and reach every member of the destination house.
  If a transfer ever needs to look like a canonical house revival, call
  `agot_convert_house_and_descendants_effect` instead.

## Generation

None. This module has no `mod.toml` and no generator; the payload is
hand-authored. Validate with:

```sh
ck3mm mod validate agot_debug_house_transfer
```

## Re-audit

**Manual, and this module is meant to be deleted.** It was added on 2026-08-16
as a temporary tool at the user's request. Remove it once the save it was needed
for is fixed. While it exists, recheck after AGOT updates that
`interaction_category_agot_debug` still exists and that `set_house` and
`house_founder` are still current, and confirm no other playset mod has claimed
the `zz_debug_` key prefix.
