# Grand Remembrance - CK3 1.19 Runtime Fix

Narrow runtime repair for **Grand Remembrance** and its AGOT compatibility
submod on CK3 1.19.

## Requirements and load order

1. A Game of Thrones
2. Grand Remembrance
3. Grand Remembrance AGOT compatibility submod
4. This fix

Load immediately after the AGOT compatibility submod.

## What it repairs

**Obituaries against AGOT's database.** Grand Remembrance's obituary processor
assumes the vanilla and RICE databases. AGOT removes its fame traits, religion
tags, culture heritages, and elective title laws, so the first processed death
produced a large batch of invalid lookups. Only those unsupported flavor
classifications are disabled. Core memories, stats, personality, education,
health, heir, score, and AGOT-submod obituary data stay active.

The RICE-presence recheck is removed too: it identifies RICE by looking up a
RICE-only faith, which is itself an invalid lookup when RICE is absent, and the
RICE classifiers it guards are already disabled.

**A broken opinion lookup** in NPC obituaries, which CK3 1.19 rejects as an
opinion trigger without a target. The recorded opinion value is now read while
both characters are valid and stored on the obituary.
