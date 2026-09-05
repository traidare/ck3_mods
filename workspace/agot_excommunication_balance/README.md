# agot_excommunication_balance — module state

Narrow balance patch for the two excommunication interactions in **A Game of
Thrones**. Load after AGOT and after any other mod that redefines
`excommunicate_interaction` or `request_excommunication_interaction`.

## Ownership

`common/character_interactions/zz_agot_excommunication_balance.txt` redefines
`excommunicate_interaction` and `request_excommunication_interaction` by key.
Both definitions are extracted from the current AGOT Workshop payload, so
`lift_excommunication_interaction` and every other interaction in AGOT's
`00_religious_interactions.txt` remain untouched.

## Behavior

`excommunicate_interaction` is the head of faith acting unprompted. AGOT keeps
vanilla's `auto_accept = yes`, so there is no acceptance roll on this path and
the AI cadence and `ai_will_do` roll are the only levers:

- `ai_frequency_by_tier` is `county = 0`, `duchy = 120`, and `60` for kingdom,
  empire, and hegemony, against AGOT's `72 / 36 / 12`.
- `ai_will_do` starts at `10` instead of `50`, and `ai_vengefulness` weighs
  `0.25` instead of `0.5`, so the roll spans 0–35 rather than 0–100.
- The `factor = 0` target gate admits only `has_relation_nemesis` and
  `is_at_war_with`. AGOT also admits `has_relation_rival`, which the
  interaction's own `on_accept` then seeds through
  `set_relation_potential_rival` — a rivalry qualifying makes the path
  self-reinforcing.

`request_excommunication_interaction` is a third party asking the head of faith,
and it does roll for acceptance. Its `ai_accept` base is `-75` instead of AGOT's
`-50`, so a request needs 25 more acceptance from opinion, the target's sins,
the requester's religious traits, or a hook. A weak hook still contributes 50.
AGOT's strong-hook auto-accept path, both interactions' piety requirements,
costs, target restrictions, and the requester's own AI frequency are unchanged.

## Generation

```sh
ck3mm mod generate agot_excommunication_balance
ck3mm mod generate agot_excommunication_balance --apply
```

The generator requires each anchor it rewrites to appear exactly once in the
definition it belongs to: the request path's `base = -50`, and the head path's
verbatim `ai_frequency_by_tier` block, `base = 50`, `ai_vengefulness = 0.5`, and
rival/nemesis/at-war `factor = 0` modifier. If AGOT changes any of them,
generation fails instead of silently retaining an obsolete balance override.

## Re-audit

Re-audit after any A Game of Thrones update, or whenever another enabled mod
begins redefining either excommunication interaction.
