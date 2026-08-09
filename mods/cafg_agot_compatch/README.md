# Culture and Faith Granularity + AGOT Compatch

Compatibility patch for `[Kei] Culture and Faith Granularity` and
`A Game of Thrones`.

Load order:

1. `[Kei] Culture and Faith Granularity`
2. `A Game of Thrones`
3. This compatch

In addition to the county culture/faith integrations, this layer rebases CaFG's
startup tolerance-law triggers for AGOT's culture database. AGOT does not define
the vanilla `tradition_steppe_tolerance`; the four invalid checks are omitted
while all surviving CaFG criteria are preserved. This prevents the repeated
`has_cultural_tradition` null-target failures seen while initial laws are
selected for rulers.

## Cultural men-at-arms boons

AGOT and later playset mods replace several vanilla men-at-arms files by
filename. CaFG's cultural-boon tables still instantiated its generic regiment
refill effect for 35 unit types removed from the resulting database. CK3
post-validated each parameterized instance three times, producing the 105
`is_maa_type` database failures in the 258 A.C. playtest.

The two generated scripted-effect overrides remove only weighted branches whose
unit type does not exist. Eighteen valid AGOT/playset unit gifts remain
unchanged. When all outcomes of a nested random list are invalid, its enclosing
weighted branch is removed so the boon selection cannot choose an empty outcome.

The same rebase removes eleven other weighted branches whose vanilla/TGP
traditions do not exist in AGOT. It retains the pastoralist boon using its
plains/steppe conditions without the removed `world_steppe` region, gives the
ordinary `pilgrim` trait instead of querying vanilla Islam for `hajjaj`, and
keeps the scholar-official character reward without vanilla Han-language and
Confucian-education operations.

Regenerate these overrides from current CaFG Workshop sources with:

```sh
ck3mm mod check cafg_agot_compatch
ck3mm mod generate cafg_agot_compatch
```

The `.ck3mm/mod.toml` manifest declares CaFG as a portable source and limits the
staged generator to this compatch's owned outputs. The generator verifies the
exact missing type and branch counts and stops if a CaFG update changes the
source assumptions.

## Cultural-benefit trigger chance

CaFG's five-year benefit pulse queried three traditions and the Chinese heritage
pillar that do not exist in AGOT's replaced culture database. The generated
script-value override removes those four invalid alternatives while preserving
the remaining isolationist, fierce-independence, ruling-caste,
cultivated-sophistication, communal, tolerant-law, and xenophilic modifiers.
This repairs the null `has_cultural_tradition` targets recorded at lines 78, 80,
and 110 of the parent file in the 2026-07-31 crash logs.

## Disabled vanilla-only decisions

CaFG also ships whole-file replacements for two vanilla decisions that have no
valid counterpart in AGOT:

- `adopt_a_new_faith_for_persia_decision`, which requires the Persian Struggle,
  Islam, its vanilla faiths, and vanilla head-of-faith titles; and
- `embrace_outremer_culture_decision`, which requires vanilla Catholic/Arabic
  cultures, titles, and Middle Eastern geographical regions.

Because decision `is_shown` blocks are evaluated repeatedly, these otherwise
unreachable definitions generated roughly 13,500 invalid database-scope script
locations during the 258 A.C. playtest. Exact-path, intentionally empty
overrides prevent CaFG's two definitions from loading without changing any
AGOT-native decision.

CaFG also reintroduces three files of vanilla-only definitions that AGOT
explicitly disables: the Zanj rebellion casus belli, seven vanilla regional
decision effects, and five Persian-Struggle effects. Those definitions cannot
execute in AGOT and fail load-time validation against removed wars, doctrines,
faiths, effects, and script values. Generated empty exact-path overrides now
keep them disabled, matching AGOT's source rather than compiling unreachable
vanilla content into the total conversion.
