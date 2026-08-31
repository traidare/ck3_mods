# agot_long_night_azor_ahai_runtime_fix — module state

Optional narrow runtime repair for AGOT: The Long Night & Azor Ahai on CK3
`1.19`. It is independent of the animation compatch and is enabled only with the
Workshop parent.

## Ownership and evidence

The module owns only `common/genes/zz_long_night_genes.txt`. CK3-Tiger reports
each of the parent's 18 special morph genes with the fatal signature:

> adding a group to a gene under special_genes will make the ruler designer
> crash

It also reports each adjacent `inheritable` field as unknown. Vanilla CK3 and
AGOT special morph genes carry neither field. The generated last writer copies
the parent file and removes exactly those 36 lines while preserving every gene
key, template, index, curve, and the `special_genes/morph_genes` structure.

This avoids moving the genes into persistent DNA, which would recreate the
parent's documented `Persistent portrait info missing gene` flood. The tradeoff
is that ruler presets saved against older Long Night gene layouts are not
guaranteed to load without missing-gene messages.

## Load order

Load immediately after AGOT: The Long Night & Azor Ahai and before the optional
Long Night + DFP animation compatch.

## Generation

```sh
ck3mm mod generate agot_long_night_azor_ahai_runtime_fix
ck3mm mod generate agot_long_night_azor_ahai_runtime_fix --apply
```

## Re-audit

Re-audit when the Workshop parent changes this gene file or CK3 changes special
morph-gene handling. The source hash and exact field/gene counts intentionally
fail generation instead of silently carrying an obsolete repair.
