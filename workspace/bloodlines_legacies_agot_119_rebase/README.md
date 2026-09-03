# bloodlines_legacies_agot_119_rebase — module state

Compatibility rebase for **Bloodlines: Legacies of AGOT** (`3522779004`) against
current **A Game of Thrones 0.5.1** (`2962333032`) on CK3 1.19. Load position:
immediately after Bloodlines.

## Ownership

Generated same-path overrides of the Bloodlines files that still carry a defect,
plus eleven re-encoded textures. Files Bloodlines has corrected itself are left
to load unmodified, so this module's scope shrinks as upstream catches up. It
owns nothing AGOT provides.

## Repairs and evidence

- Rebases Bloodlines' stale `execute_prisoner_interaction` override onto current
  AGOT while retaining both AGOT's and Bloodlines' Bolton flaying perks. The
  flaying option's dynasty check is guarded, because AGOT and Bloodlines both
  enter the dynasty scope unconditionally and raise
  `dynasty trigger [ Failed context switch ]` for a dynastyless executioner;
  this module is the effective last writer for the interaction.
- Guards each of the 57 active game-start special-building additions so it skips
  a barony that already carries a special building from the expanded map stack
  and a barony that has no holding at all. Under the module's default game rules
  this is the only Bloodlines work that runs at game start, and the expanded map
  leaves some targets holdingless, so the unguarded effect reached a holding
  that does not exist. The upstream file keeps a further sixteen assignments
  commented out; the count assertion covers only the active ones.
- Repairs the malformed child-birth and Riverlands script blocks, whose brace
  and indentation errors stop later events in the same file from loading while
  the yearly pulse continues to call them.
- Migrates removed traits, title ids, event backgrounds, portrait scopes, and
  animation names.
- Removes explicit durations from CK3 1.19's self-decaying opinion modifiers.
- Restores missing Bloodlines opinion-modifier definitions and values. The three
  `*_by_trident_lord_bla` modifiers and `attended_trident_council_bla` are
  declared as opinion modifiers here, carrying the `vassal_opinion` value the
  upstream static modifiers declare, because their call sites pass no explicit
  opinion. `betrayed_opinion` and `claimant_opinion` exist as keys only, since
  every call site supplies its own value.
- Repairs invalid county/character modifier scope usage.
- Makes the scripted great-project sound reference self-contained.
- Re-encodes eleven invalid block-compressed DDS files without resizing their
  artwork.

### Crownlands pack

The Crownlands content is newer than the rest of Bloodlines and carries its own
class of defects, each repaired against the current CK3 tag or effect:

- 55 modifier fields in `00_agot_crownlands_modifiers_BLA.txt` name tokens CK3
  1.19 rejects, so the parser drops the line and the modifier loads without it.
  `popular_opinion` becomes `county_opinion_add`, the two `hostile_scheme_*`
  fields become the corresponding success-chance tags with resistance expressed
  as a negative, `building_construction_time`/`_cost` become
  `holding_build_speed`/`holding_build_gold_cost` with the time sign inverted,
  `county_tax_mult` becomes `tax_mult`, and `marriage_acceptance` becomes
  `attraction_opinion`. Generation asserts the exact count of each and that none
  survives in the output.
- 47 event options grant dynasty prestige straight from a character scope, which
  raises `Inconsistent effect scopes (character vs. dynasty)` and grants
  nothing. Each is wrapped in AGOT's own `dynasty ?= { ... }` idiom. The
  generator walks block headers to find the scope an effect really runs in, so
  the pack's on-action and legacy grants — which already enter a dynasty — are
  untouched.
- Four `create_character` blocks declare no gender data and fail PostValidate.
  The pack's one valid block uses `gender_female_chance`, so the repair uses
  that field: `0` where the event text has no gendered getters, AGOT's generic
  `20` where the text is written with adaptive pronouns. The Celtigar block also
  drops its `location`, which CK3 rejects alongside an `employer`.
- The Stepstones decision compares an iterated title with `has_title`, a
  character trigger, raising
  `Inconsistent trigger scopes (landed_title vs. character)` for all eight
  reward titles. Under the iterator they become `this = title:…`; the same
  trigger is correct in the character scopes elsewhere in the file and is left
  alone.
- Four Velaryon modifiers mix character-only monthly gains with province- or
  county-valid fields, so `add_province_modifier`/`add_county_modifier` rejects
  the application whole and nothing is applied. They are applied to the ruler
  instead, where development growth, build speed, and county opinion all keep a
  meaning that covers the county in question. The tradeoff is that they now
  cover the ruler's realm rather than one province.
- The Darklyn events compare `dynn_Darke`, `dynn_Darkwood`, and `dynn_Dargood`
  as dynasties. AGOT defines all three as cadet houses of `dynn_Darklyn`, and
  the `dynn_*` string is each house's own name key, so every one of the twelve
  comparisons resolves to nothing and closes the restoration gates it exists
  for. They become `house = house:house_…`. The same file's `add_prowess` and
  `has_liege` become `add_prowess_skill` and `exists = liege`, and its
  bought-claim option's second `trigger` block is merged into the first, because
  an option may declare only one and the gold and prestige requirements were
  being dropped.
- `00_agot_artifact_effects_BLA.txt` misspells `set_artifact_rarity_illustrious`
  in one creation effect — every sibling in the same file spells it correctly —
  and names the artifact ownership effect `set_artifact_owner` rather than
  `set_owner`.
- `agot_riverlands_events_bla.txt` calls the nonexistent effect `add_knight` on
  a created hedge knight. CK3 has no knighthood effect: knights are selected
  from eligible courtiers, which the preceding `set_employer` already makes the
  character, and the creation block already grants the `knight` trait, so the
  call is removed.

## Generation

Generated files come from the current Workshop sources:

```bash
ck3mm mod generate bloodlines_legacies_agot_119_rebase
ck3mm mod generate bloodlines_legacies_agot_119_rebase --apply
```

The `mod.toml` manifest declares the parents, staged entrypoint, and owned
outputs.

## Re-audit

The generator asserts expected replacement counts. Re-run it and re-audit this
module whenever Bloodlines or AGOT updates.
