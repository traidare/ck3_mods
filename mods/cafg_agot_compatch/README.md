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
