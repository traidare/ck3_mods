# agot_excommunication_balance — module state

Narrow balance patch for excommunication requests in **A Game of Thrones**. Load
after AGOT and after any other mod that redefines
`request_excommunication_interaction`.

## Ownership

`common/character_interactions/zz_agot_excommunication_balance.txt` redefines
only `request_excommunication_interaction` by key. The source definition is
extracted from the current AGOT Workshop payload, so unrelated interactions in
AGOT's `00_religious_interactions.txt` remain untouched.

## Behavior

The religious head's `ai_accept` base is `-100` instead of AGOT's `-50`. A
request therefore needs 50 more acceptance from opinion, the target's sins, the
requester's religious traits, or a hook. A weak hook still contributes 50 but
does not guarantee acceptance by itself. AGOT's strong-hook auto-accept path,
piety requirements, costs, target restrictions, and AI request frequency are
unchanged.

## Generation

```sh
ck3mm mod generate agot_excommunication_balance
ck3mm mod generate agot_excommunication_balance --apply
```

The generator requires exactly one `base = -50` anchor in AGOT's
`request_excommunication_interaction`. If AGOT changes that acceptance block,
generation fails instead of silently retaining an obsolete balance override.

## Re-audit

Re-audit after any A Game of Thrones update, or whenever another enabled mod
begins redefining `request_excommunication_interaction`.
