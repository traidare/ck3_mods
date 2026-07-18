# AGOT Sub-Mod Setup

How to create a sub-mod that extends or patches the A Game of Thrones (AGOT)
total conversion mod for CK3.

## AGOT Mod Path

The AGOT mod is installed via Steam Workshop:

```
C:/Program Files (x86)/Steam/steamapps/workshop/content/1158310/2962333032
```

Workshop ID: `2962333032`

The mod contains the same folder structure as vanilla CK3 (`common/`, `events/`,
`gfx/`, `gui/`, `localization/`, `map_data/`, `history/`, etc.) but replaces
many vanilla paths entirely (see `replace_path` entries in `descriptor.mod`).

## Creating an AGOT Sub-Mod

An AGOT sub-mod is a regular CK3 mod that loads **after** AGOT. It can override
AGOT files, add new files, or patch AGOT systems.

### Step 1: Create the Mod

Use the CK3 launcher (see `references/setup.md`) or create manually:

**`descriptor.mod`:**

```
version="1.0.0"
name="My AGOT Sub-Mod"
tags={
	"Total Conversion"
	"Gameplay"
}
supported_version="1.18.*"
```

### Step 2: Set Load Order

Your sub-mod must load after AGOT. In the CK3 launcher, enable both AGOT and
your sub-mod. The launcher handles load order based on dependencies.

To enforce load order, add a `dependencies` block (CK3 1.12+):

**In your `.mod` file** (the one in the mod/ directory, NOT descriptor.mod):

```
dependencies={
	"A Game of Thrones"
}
```

### Step 3: Understand What AGOT Replaces

AGOT uses `replace_path` for these directories — vanilla files in these paths
are **completely ignored**:

- `common/achievements`
- `common/bookmarks/bookmarks`, `common/bookmarks/groups`
- `common/bookmark_portraits`
- `common/coat_of_arms/dynamic_definitions`
- `common/culture/cultures`, `common/culture/pillars`
- `common/dna_data`
- `common/dynasties`, `common/dynasty_houses`, `common/dynasty_house_mottos`,
  `common/dynasty_house_motto_inserts`
- `common/landed_titles`
- `common/religion/holy_sites`, `common/religion/religion_families`,
  `common/religion/religions`
- `history/characters`, `history/cultures`, `history/provinces`,
  `history/titles`, `history/wars`
- `common/defines/graphic`
- `map_data/geographical_regions`

**Key implication:** Your sub-mod works with AGOT's versions of these files, not
vanilla's.

## AGOT Naming Conventions

AGOT prefixes almost everything with `agot_`:

| Type              | Convention                          | Example                           |
| ----------------- | ----------------------------------- | --------------------------------- |
| Scripted effects  | `agot_<system>_<action>_effect`     | `agot_dragon_bond_effect`         |
| Scripted triggers | `agot_<system>_<condition>_trigger` | `agot_is_dragon_rider_trigger`    |
| Events            | `agot_<system>.<number>`            | `agot_dragon.0001`                |
| Event namespaces  | `agot_<system>`                     | `agot_dragon`, `agot_nw`          |
| Decisions         | `agot_<action>_decision`            | `agot_join_nights_watch_decision` |
| Interactions      | `agot_<action>_interaction`         | `agot_tame_dragon_interaction`    |
| Traits            | `agot_<name>`                       | `agot_dragonrider`, `agot_knight` |
| Character flags   | `agot_<description>`                | `agot_had_dragon_bond`            |
| Global variables  | `agot_<name>`                       | `agot_magic_level`                |
| On actions        | `agot_on_<event>`                   | `agot_on_dragon_death`            |
| Script values     | `agot_<name>_value`                 | `agot_dragon_taming_chance_value` |
| GUI files         | `agot_<name>.gui`                   | `agot_dragon_window.gui`          |

**For your sub-mod**, use your own prefix to avoid conflicts:

```
# Good — unique prefix
mymodnick_dragon_buff_effect

# Bad — could conflict with AGOT updates
agot_dragon_buff_effect
dragon_buff_effect
```

## AGOT Scripted API

AGOT exposes a large library of scripted effects and triggers that sub-mods
should use instead of reimplementing logic. Key files:

| File                                                       | Contents                                        |
| ---------------------------------------------------------- | ----------------------------------------------- |
| `common/scripted_effects/00_agot_dragon_effects.txt`       | Core dragon effects (bonding, unbonding, death) |
| `common/scripted_triggers/00_agot_dragon_triggers.txt`     | Dragon state checks                             |
| `common/scripted_effects/00_agot_banking_effects.txt`      | Banking/loan effects                            |
| `common/scripted_effects/00_agot_coronation_effects.txt`   | Coronation ceremony effects                     |
| `common/scripted_effects/00_agot_knighthood_effects.txt`   | Knight/squire effects                           |
| `common/scripted_effects/00_agot_nightswatch_effects.txt`  | Night's Watch effects                           |
| `common/scripted_effects/00_agot_kingsguard_effects.txt`   | Kingsguard effects                              |
| `common/scripted_effects/00_agot_colonization_effects.txt` | Colonization effects                            |
| `common/scripted_effects/00_agot_bastard_effects.txt`      | Bastard legitimization effects                  |
| `common/scripted_effects/00_agot_citadel_effects.txt`      | Maester/Citadel effects                         |

**Always search AGOT's scripted_effects/ and scripted_triggers/ before writing
custom logic.** AGOT likely has an effect or trigger for what you need.

### Commonly Used AGOT Triggers

```
# Check if character is a dragon rider
agot_is_dragon_rider_trigger = yes

# Check if character has a dragon
agot_has_dragon_trigger = yes

# Check if character is a knight
agot_is_knight_trigger = yes

# Check if character is in the Night's Watch
agot_is_nights_watch_trigger = yes

# Check if character is in the Kingsguard
agot_is_kingsguard_trigger = yes

# Check if character is a maester
agot_is_maester_trigger = yes
```

### Commonly Used AGOT Effects

```
# Bond a dragon to a character (scope: character, dragon passed as target)
agot_dragon_bond_effect = { DRAGON = scope:dragon }

# Knight a character
agot_knight_character_effect = yes

# Send character to Night's Watch
agot_send_to_nights_watch_effect = yes

# Start a loan from the Iron Bank
agot_take_iron_bank_loan_effect = { GOLD = 500 }
```

## AGOT Submod Core (Compatibility Framework)

If your sub-mod touches **portraits, crowns, clothing, accessories, or weapon
models**, you should depend on the **AGOT Submod Core** (Workshop ID:
`3034473189`).

Submod Core is a shared dependency mod maintained by the AGOT team that solves
the N-way compatibility problem between portrait sub-mods. Without it, any two
mods that modify gene files, crown traits, or the death effect will conflict.

**What it provides:**

- Merged gene files (`common/genes/05_*` through `08_*`) that include entries
  from all supported sub-mods
- ~140 hidden `equipped_*_artifact` traits for the crown/weapon portrait system
- Mod-detection API: `is_*_loaded_trigger` triggers for runtime sub-mod
  detection
- Centralized death effect that freezes portrait equipment traits
- Shared font file with Valyrian Glyphs

**When to depend on it:**

- You add custom crowns, helms, or headgear → your traits need to be in the
  Core's registry
- You add clothing or accessories → your gene entries need to be in the Core's
  gene files
- You need to detect if another sub-mod is loaded → use the Core's detection
  triggers
- You modify the death effects for portraits → must coordinate with the Core

**When you DON'T need it:**

- Pure gameplay mods (events, decisions, traits without portrait effects)
- Map mods, building mods, CB mods
- Anything that doesn't touch the portrait/gene system

**Adding dependency:**

```
dependencies={
	"A Game of Thrones"
	"AGOT Submod Core"
}
```

**Full guide:** [agot-submod-core.md](agot-submod-core.md)

## Source of Truth for AGOT Sub-Modding

```
1. AGOT source files (mod path above)     — The actual implementation
2. .info files (references/generated/info/)          — Paradox syntax docs (still valid for AGOT)
3. script_docs (references/generated/script_docs/)   — Vanilla triggers/effects (AGOT adds more)
4. AGOT guides (references/agot/)          — Patterns and pitfalls specific to AGOT
5. Vanilla patterns (references/patterns/) — Base patterns (check AGOT extension first)
```
