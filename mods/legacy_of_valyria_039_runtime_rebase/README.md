# Legacy of Valyria RC71 - CK3 1.19 Runtime Rebase

Narrow runtime repair for **Legacy of Valyria - AGOT 0.4.39 Temporary Compatch
RC71** (`3719888822`) against the current AGOT 0.4.40 source.

Load immediately after the RC71 compatch and before Essos Expanded.

## Pirate succession repair

RC71 changes AGOT's `pirate_succession_law` eligibility from duchy-or-higher to
county-or-higher and assigns the elective law to 34 LoV county titles. A
county-only pirate can have no eligible election candidate, which makes CK3
repeatedly report:

```text
Failed build succession ... due to unhandled succession order [invalid]
```

This rebase:

- restores current AGOT's duchy-or-higher eligibility for pirate elective;
- removes the elective law from the 34 LoV counties; and
- preserves the law on `d_the_three_snakes`, `d_eastern_isles`, and
  `d_the_western_isles`.

The affected counties retain their LoV holder, government, liege, and holding
history. Without a special title law they use ordinary realm succession, while
the three pirate duchies continue to use AGOT's pirate elective.

The four title-history overrides are intentionally copied from RC71 rather than
base LoV, so RC71's other CK3 1.19 compatibility changes remain intact.

They also discard six inert invalid liege assignments inherited from RC71: four
counties pointed at the deliberately unhistoried `d_fields_of_hunger`, and two
unheld Rhoynar counties tried to become vassals of an also-unheld `k_volantis`
in 7300. Tiger confirms that those assignments have no effect; removing them
therefore preserves the runtime state while eliminating the malformed history
operations.
