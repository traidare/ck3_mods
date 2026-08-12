# VIET 1.3.0 - AGOT CK3 1.19 Runtime Rebase

Compatibility rebase for **VIET Events 1.3.0** (`2227658180`) and current **A
Game of Thrones 0.4.40** (`2962333032`).

Load immediately after VIET.

## What it repairs

VIET targets the vanilla CK3 culture, faith, religion, title, and geographical
region databases. AGOT replaces those databases. In the 258 A.C. full-playset
run, VIET consequently generated the largest group in the 28 MB error log:

- 151 event definitions contained references that are invalid under AGOT;
- 43 of those events were repeatedly evaluated by VIET pulse on-actions;
- four event-background selectors evaluated hundreds of absent vanilla regions;
- three customizable-localization selectors evaluated absent regions, cultures,
  and religions; and
- 17 top-level scripted triggers directly evaluated absent vanilla cultures,
  faiths, religions, titles, or geographical regions;
- three decisions directly evaluated absent vanilla religions; and
- twelve vanilla heritage helpers, `is_christian_trigger`, and the optional
  `ek_character_setup_effect` were absent.

The generated overrides:

- retain every compatible VIET event unchanged;
- replace only the 151 evidenced incompatible events with inert, same-id stubs;
- remove those ids from VIET's random pulse lists;
- retain the four affected backgrounds using their original generic fallback
  artwork;
- retain safe generic cactus, dumpling, and fruit localization; and
- rebase the 17 source-pinned database trigger definitions onto AGOT cultural
  analogues or inert false conditions, rather than only shadowing them later in
  load order;
- hide the three source-pinned religion-specific decisions before CK3 can
  evaluate their vanilla religion IDs; and
- supply AGOT-aware analogues for VIET's broad heritage-category helpers;
- repair four artifact events that called AGOT's feature-reference effect
  without its required `scope:owner`; and
- correct six invalid or misspelled portrait-animation names;
- restore character scope to four delayed/on-death ping events;
- remove two duplicate event-window widget declarations;
- correct six fallback branches written as `else_if` without a `limit`; and
- move seven random outcome rolls out of interface-toast blocks so the displayed
  result and executed result cannot be rolled independently.

The same-id event stubs preserve references from surviving event chains without
allowing an incompatible event body to load or execute.

## Regeneration

The event, selector, trigger, and decision files are generated directly from the
current Workshop source:

```bash
ck3mm mod generate viet_agot_119_runtime_rebase
ck3mm mod generate viet_agot_119_runtime_rebase --apply
```

The `workspace/viet_agot_119_runtime_rebase/mod.toml` manifest declares VIET as
a portable source, the staged generator, and its owned outputs. The
evidence-derived disabled-event manifest is a generator asset below
`workspace/viet_agot_119_runtime_rebase/`. The trigger and decision replacements
pin the exact source blocks, so generation stops for review if VIET changes
them. Re-run a full playtest and re-audit that asset and the pinned database
blocks whenever VIET updates.
