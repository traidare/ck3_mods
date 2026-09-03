# agot_long_night_azor_ahai_runtime_fix — module state

Optional narrow runtime repair for AGOT: The Long Night & Azor Ahai on CK3
`1.19`. It is independent of the animation compatch and is enabled only with the
Workshop parent.

## Ownership and evidence

### Special morph genes

`common/genes/zz_long_night_genes.txt`. CK3-Tiger reports each of the parent's
18 special morph genes with the fatal signature:

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

### Service gate

`common/scripted_triggers/zz_ln_service_triggers.txt`. The parent's
`ln_may_serve_trigger` pairs a `trigger_if` with a `trigger_else_if` and no
terminator, which CK3 1.19 rejects:

> `trigger_else_if trigger [ trigger_else_if with no trigger_else ]`
>
> `PostValidate of trigger 'trigger_else_if' returned false`

The failure makes the whole gate return false, so its four call sites —
`can_be_knight_trigger`, `base_court_position_validity_trigger`, and
`can_be_councillor_basics_trigger` in this file, plus
`can_be_commander_basic_trigger` in the parent's commander override — refuse
every candidate rather than only the dead. The generated last writer is the
parent file with `trigger_else = { always = yes }` appended to that chain, which
is the living-candidate-under-a-living-lord case the parent documents as
silently permitted. Nothing else in the file changes, so the three AGOT trigger
bodies the parent copies stay as the parent shipped them.

The file is SHA-256 pinned, and generation asserts all three in-file call sites
and that the chain still lacks a terminator.

## Load order

Load immediately after AGOT: The Long Night & Azor Ahai and before the optional
Long Night + DFP animation compatch.

## Generation

```sh
ck3mm mod generate agot_long_night_azor_ahai_runtime_fix
ck3mm mod generate agot_long_night_azor_ahai_runtime_fix --apply
```

## Re-audit

Re-audit when the Workshop parent changes either owned file, when CK3 changes
special morph-gene handling, or when CK3 accepts an unterminated
`trigger_else_if` chain again. Each source hash, the exact field/gene counts,
and the call-site assertions intentionally fail generation instead of silently
carrying an obsolete repair; generation also fails once the parent adds its own
`trigger_else`.
