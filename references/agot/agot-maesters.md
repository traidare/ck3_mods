# AGOT: Maesters & Citadel

## Overview

The AGOT mod implements a full Maester system: the Citadel institution, acolyte
training with chain links, maester assignment to courts, the Grand Maester role,
archmaesters with specialties, and the Seneschal election cycle. The system is
built on top of a custom court position (`maester_court_position`), the
`maester` trait with XP progression, artifact-based chain links, and a
`story_maester` story cycle that drives yearly maintenance and death succession.

**Core files:**

- `common/scripted_effects/00_agot_citadel_effects.txt` -- all major effects
- `common/scripted_triggers/00_agot_maester_triggers.txt` -- eligibility
  triggers
- `common/story_cycles/agot_story_cycle_maester.txt` -- yearly tick + death
  handling
- `events/agot_events/agot_maester_events.txt` -- player-facing events
- `events/agot_government_events/agot_citadel_maintenance_events.txt` -- Citadel
  upkeep
- `common/decisions/agot_decisions/00_agot_maester_decisions.txt` -- employ
  maester decisions
- `common/court_positions/types/00_agot_court_positions.txt` --
  `maester_court_position`

## Key Concepts

### The `maester` Trait and XP Progression

The `maester` trait uses CK3's trait XP system as a rank tracker:

| XP Range | Rank           | Notes                                   |
| -------- | -------------- | --------------------------------------- |
| 0        | Novice         | Just sent to Citadel, no links yet      |
| 1-33     | Novice (early) | First link earned bumps XP to 34        |
| 34-99    | Acolyte        | Earning links, +6 XP per link           |
| 100      | Full Maester   | Chain complete, eligible for assignment |

When a character's first link artifact is created, XP jumps to 34 (novice to
acolyte). Each subsequent link adds 6 XP. Reaching 100 XP triggers
`agot_progress_to_maester_effect`, which reforges the link collection into a
`maester_chain` artifact.

### Chain Links as Artifacts

Links are artifacts of three types representing progression:

- `maester_link` -- a single link (first link earned)
- `maester_link_collection` -- reforged from a single link once 2+ links are
  collected
- `maester_chain` -- the final chain, reforged when XP reaches 100

Each artifact tracks individual link metals via variables (e.g.,
`black_iron_links`, `silver_links`, `vs_links`). A complete chain has **12
links**. The `agot_complete_chain_effect` fills remaining links up to 12.

### Link Metals and Their Subjects

The system defines 22 link metals, each representing a field of study. These
metals also map to archmaester specialties and candidate flags:

| Metal                 | Subject              | Candidate Flag           |
| --------------------- | -------------------- | ------------------------ |
| `black_iron`          | Ravenry              | `black_iron_candidate`   |
| `brass`               | Genealogy            | `brass_candidate`        |
| `bronze`              | Astronomy            | `bronze_candidate`       |
| `copper`              | History              | `copper_candidate`       |
| `electrum`            | Cyphers              | `electrum_candidate`     |
| `yellow_gold`         | Money and Accounts   | `yellow_gold_candidate`  |
| `red_gold`            | (unspecified)        | `red_gold_candidate`     |
| `iron`                | (Warcraft)           | `iron_candidate`         |
| `lead`                | Poisons              | `lead_candidate`         |
| `pewter`              | Architecture         | `pewter_candidate`       |
| `platinum`            | Agriculture          | `platinum_candidate`     |
| `silver`              | Medicine / Healing   | `silver_candidate`       |
| `steel`               | (unspecified)        | `steel_candidate`        |
| `tin`                 | (unspecified)        | `tin_candidate`          |
| `bismuth`             | Faiths               | `bismuth_candidate`      |
| `cast_iron`           | Husbandry            | `cast_iron_candidate`    |
| `antimony`            | Geography            | `antimony_candidate`     |
| `nickel`              | Alchemy              | `nickel_candidate`       |
| `white_copper`        | Political Science    | `white_copper_candidate` |
| `aluminum`            | Logistics and Supply | `aluminum_candidate`     |
| `zinc`                | Engineering          | `zinc_candidate`         |
| `vs` (Valyrian Steel) | Higher Mysteries     | `vs_candidate`           |

When a maester reaches full rank, `agot_progress_to_maester_effect` sets flags
like `silver_candidate` (2 links in that metal) or `silver_candidate_lesser` (1
link). These flags drive archmaester eligibility and personality trait
assignment.

### Link Inclination

When a character is sent to the Citadel, their previous education focus is
recorded as a `link_inclination` variable (e.g., `flag:diplomacy`,
`flag:martial`). This influences which link types they tend to earn. The
variable is set in `agot_send_to_citadel_effect`.

### The Citadel as a Title

The Citadel is tracked via `global_var:citadel_title`, a barony-level title
(default: `title:b_the_citadel`). The holder of this title is the current
Seneschal. All acolytes, novices, and archmaesters are courtiers of the
Seneschal.

Characters at the Citadel get `blocked_from_leaving` flag to prevent AI
wandering.

### Maester Court Position

Maesters serve via `maester_court_position` (defined in
`00_agot_court_positions.txt`), limited to `max_available_positions = 1`. The
position replaces the vanilla court physician role -- assignment is done via
`set_court_physician_effect`.

### Hierarchy: Maester -> Archmaester -> Grand Maester -> Seneschal

- **Maester**: Full chain (XP = 100), assigned to a lord's court
- **Archmaester**: Has `archmaester` trait + an inactive specialty trait (e.g.,
  `archmaester_silver`). Owns mask, ring, and rod artifacts. 22 seats total.
- **Grand Maester**: Has inactive `grandmaester` trait. Serves the Iron Throne
  holder. Wears a `grandmaester_chain` artifact.
- **Seneschal**: The archmaester who holds `global_var:citadel_title`. Elected
  by peers. Rotates with `recent_seneschal` cooldown flag (10 years).

## AGOT Scripted API

### Key Triggers (`00_agot_maester_triggers.txt`)

```
# Is the character from a culture that can have maesters?
agot_maester_culture_trigger = {
    OR = {
        culture = { has_cultural_pillar = heritage_andal }
        culture = { has_cultural_pillar = heritage_rhoynar }
        culture = { has_cultural_pillar = heritage_first_man }
    }
}

# Is the character eligible to be recruited as a maester candidate?
agot_is_maester_candidate = {
    culture = { has_innovation = innovation_maesters }
    is_lowborn = yes
    is_ruler = no
    age < 30
    learning > 10
    is_adult = yes
    is_male = yes
    # ...plus NOR checks for nightswatch, kingsguard, maester, devoted, septon
}

# Has the character completed their chain?
agot_is_maester = {
    has_trait_xp = { trait = maester  value = 100 }
}

# Is there any full maester currently at the Citadel?
agot_any_maester_in_citadel = {
    global_var:citadel_title.holder ?= {
        OR = {
            any_courtier_or_guest = {
                has_trait_xp = { trait = maester  value = 100 }
                NOT = { root = this }
            }
            AND = { # Seneschal counts too
                has_trait_xp = { trait = maester  value = 100 }
                NOT = { root = this }
            }
        }
    }
}

# Is the character eligible for archmaester promotion?
agot_is_archmaester_candidate = {
    has_trait_xp = { trait = maester  value = 100 }
    age > 15
    NOR = {
        has_trait = archmaester
        has_inactive_trait = grandmaester
        has_trait = nightswatch
    }
}

# Does the character have the right specialty for a vacated archmaester seat?
# Requires scope:old_archmaester to be set
agot_is_field_qualified = { ... }       # 2 links in the metal
agot_is_field_qualified_lesser = { ... } # 1 link in the metal

# Can the character serve as maester for a given employer?
can_be_maester_of = {
    is_courtier_of = $EMPLOYER$
    is_adult = yes
    basic_is_available_ai = yes
    NOT = { has_trait = incapable }
}

# Can a maester be expelled (with or without banish reason)?
agot_can_be_expelled_maester_trigger = { ... }
```

### Key Effects (`00_agot_citadel_effects.txt`)

**Sending to the Citadel:**

```
# Fully processes a character joining the Citadel.
# Divorces spouses, breaks betrothals, removes guardians/wards,
# drops concubines, sets education to learning, records link_inclination,
# adds maester trait, creates story_maester, moves to Citadel court.
agot_send_to_citadel_effect = { MAESTER_CANDIDATE = $CHARACTER$ }
```

**Chain link progression:**

```
# Adds one link to the character's chain/collection artifact.
# If no artifact exists, creates one. Adds 6 trait XP.
# If XP reaches 100, calls agot_progress_to_maester_effect.
agot_add_chain_link_effect = { OWNER = root  MAESTER = scope:maester }

# Fills remaining links to reach 12 total.
agot_complete_chain_effect = yes

# Adds a random number (1-11) of links.
agot_add_partial_chain_effect = yes
```

**Rank progression:**

```
# Reforges link_collection into maester_chain, assigns personality trait,
# sets up archmaester candidate flags, may flag as maester_researcher.
agot_progress_to_maester_effect = { ACOLYTE = root }

# Promotes to archmaester: assigns specialty trait, creates/transfers
# mask + ring + rod artifacts, moves to Citadel if needed.
agot_progress_to_archmaester_effect = { ARCHMAESTER_CANDIDATE = $CHARACTER$ }

# Promotes to Grand Maester: adds grandmaester trait, creates/transfers
# grandmaester_chain, moves to Iron Throne holder's court.
agot_progress_to_grandmaester_effect = { GRANDMAESTER_CANDIDATE = $CHARACTER$ }
```

**Maester assignment and retrieval:**

```
# Finds a maester for a ruler: checks pool, then Citadel courtiers,
# then creates one from template if needed. Saves as scope:new_maester.
agot_grab_new_maester_effect = yes

# Seeds maesters for all qualifying rulers at game start.
agot_seed_maesters_effect = yes

# Finds and appoints a new Grand Maester (used on death/expulsion).
agot_find_new_grandmaester_effect = yes
```

**Expulsion and removal:**

```
# Routes to correct expulsion effect based on rank.
agot_expel_appropriate_maester_effect = yes

# Strips chain, adds disgraced_maester trait, exiles to Essos.
agot_expel_maester_effect = yes

# Strips archmaester rank, triggers replacement election, then expels.
agot_expel_archmaester_effect = yes

# Strips grandmaester title, finds replacement.
agot_expel_grandmaester_effect = yes

# Cleanly removes maesterhood without disgrace (no disgraced_maester trait).
agot_remove_maesterhood_effect = yes

# Destroys chain/link artifacts.
agot_remove_maester_chain_effect = yes
```

**Citadel administration:**

```
# Elects a new Seneschal from archmaesters. Transfers title and courtiers.
agot_seneschal_election_effect = { CURRENT_SENESCHAL = $CHARACTER$ }

# Seeds 22 archmaesters at game start using archmaester_character template.
agot_seed_archmaesters_effect = yes

# Seeds 30 acolytes at Citadel using acolyte_character template.
agot_seed_acolytes_effect = yes

# Recovers lost maesters (sends strays back to Citadel or kills landed ones).
agot_citadel_recover_lost_rats_effect = yes

# Relocates Citadel to a new barony in the Reach (for destruction scenarios).
agot_citadel_transfer_effect = yes
```

## Decisions

### `decision_employ_maester` (Westeros)

**File:** `common/decisions/agot_decisions/00_agot_maester_decisions.txt`

Shown to landed rulers in the Seven Kingdoms whose culture has
`innovation_maesters`, who do not already employ a maester. Triggers
`agot_maester.0001` after 7 days, which calls `agot_grab_new_maester_effect` to
find or create a maester and offer them to the player.

Key conditions:

- Capital or top liege capital in `world_westeros_seven_kingdoms`
- `culture = { has_innovation = innovation_maesters }`
- Not the Iron Throne holder (Grand Maester is handled separately)
- 60-day cooldown via `recently_employed_maester` flag

### `essos_decision_employ_maester` (Essos / Landless)

Same file. For rulers outside the Seven Kingdoms or landless adventurers.
Instead of guaranteed Citadel delivery, the outcome is randomized:

| Weight | Event               | Result                             |
| ------ | ------------------- | ---------------------------------- |
| 4      | `agot_maester.0008` | A former acolyte arrives (cheaper) |
| 1      | `agot_maester.0005` | A disgraced maester appears        |
| 2      | `agot_maester.0006` | A traveling maester appears        |
| 3      | `agot_maester.0007` | Nobody shows up                    |

Cooldown is 1 year (vs. 60 days for Westeros).

## Events & Story Cycles

### Story Cycle: `story_maester`

**File:** `common/story_cycles/agot_story_cycle_maester.txt`

Created for every character with the `maester` trait via
`create_story = story_maester` in `agot_send_to_citadel_effect`. Runs a yearly
tick (`effect_group` with `days = 365`) that handles:

1. **Cleanup**: Ends the story if the owner no longer has the `maester` trait.
2. **Recovery**: Calls `agot_citadel_recover_lost_rats_effect` to drag stray
   novices/acolytes back to the Citadel.
3. **Archmaester artifact maintenance**: Re-equips unequipped archmaester
   artifacts.
4. **Citadel courtier maintenance**: If the owner is the Seneschal, runs
   `agot_citadel_maintenance_effect` on all courtiers.
5. **Acolyte advancement**: If the owner has XP < 100 and age >= 8, triggers
   `agot_citadel_maintenance.0101`.

**On owner death (`on_owner_death`):**

- Destroys chain artifacts.
- If the dead character was an **archmaester**, finds a replacement via
  `agot_is_field_qualified` and calls `agot_progress_to_archmaester_effect`.
- If the dead character was the **Grand Maester**, calls
  `agot_find_new_grandmaester_effect`.
- If the dead character was the **Seneschal**, triggers
  `agot_seneschal_election_effect`.

### Citadel Maintenance Events

**File:** `events/agot_government_events/agot_citadel_maintenance_events.txt`

- `agot_citadel_maintenance.0001` -- Removes all women from the Citadel court
  (strips maesterhood if applicable, moves to Oldtown).
- `agot_citadel_maintenance.0003` -- Initializes the Citadel: blocks
  non-maesters, ensures all maesters have `story_maester`, seeds 30 acolytes.
- `agot_citadel_maintenance.0101` -- Yearly advancement for novices/acolytes:
  rolls up to 3 chances to earn a link via `agot_maester.0003`. Intellect,
  diligence, and ambition boost chances; laziness and impatience reduce them.

### Maester Events (`agot_maester.*`)

| Event ID            | Type      | Description                                             |
| ------------------- | --------- | ------------------------------------------------------- |
| `agot_maester.0001` | Character | A maester arrives from the Citadel (Westeros employ)    |
| `agot_maester.0002` | Character | Grand Maester transferral on Iron Throne succession     |
| `agot_maester.0003` | Hidden    | Produce 1 chain link for an acolyte                     |
| `agot_maester.0004` | Hidden    | Form complete chain (debug/template use)                |
| `agot_maester.0005` | Character | A disgraced maester appears (Essos employ)              |
| `agot_maester.0006` | Character | A traveling maester appears (Essos employ)              |
| `agot_maester.0007` | Character | No maester available                                    |
| `agot_maester.0008` | Character | A former acolyte appears (Essos employ)                 |
| `agot_maester.0009` | Hidden    | Add partial chain (random 1-11 links)                   |
| `agot_maester.1000` | Character | Child wishes to join the maesters (parent event)        |
| `agot_maester.1001` | Character | Your maester is promoted to archmaester                 |
| `agot_maester.1002` | Character | Conclave has chosen a new Grand Maester                 |
| `agot_maester.1003` | Character | New Grand Maester arrives at court                      |
| `agot_maester.1004` | Character | New Grand Maester died en route                         |
| `agot_maester.1005` | Character | Your maester recommends a child for the Citadel         |
| `agot_maester.1006` | Character | A disgraced maester has been expelled to your court     |
| `agot_maester.2000` | Letter    | Citadel acceptance letter (send-to-citadel interaction) |
| `agot_maester.2001` | Letter    | Citadel rejection letter                                |
| `agot_maester.9012` | Hidden    | Pick a new archmaester (replacement)                    |
| `agot_maester.9904` | Hidden    | Seneschal yearly succession check                       |

## Sub-Mod Recipes

### Recipe 1: Add a Custom Link Metal

To add a new chain link metal (e.g., "orichalcum" for Valyrian history):

1. Add the link type to `agot_generate_random_link_types_effect` in the artifact
   effects file.
2. In `agot_progress_to_maester_effect`, add a block after the existing metals
   to check for `orichalcum_links` and set `orichalcum_candidate` /
   `orichalcum_candidate_lesser` flags.
3. Add `archmaester_orichalcum` as an inactive trait in your trait definitions.
4. Add a case in `agot_progress_to_archmaester_effect` to handle the new seat.
5. Update `agot_is_field_qualified` and `agot_is_field_qualified_lesser`
   triggers.

```
# In your scripted_effects override:
if = { # Orichalcum
    limit = {
        any_character_artifact = {
            artifact_type = maester_chain
            has_variable = orichalcum_links
            save_temporary_scope_value_as = {
                name = links
                value = var:orichalcum_links
            }
        }
    }
    if = {
        limit = { scope:links = 2 }
        add_character_flag = orichalcum_candidate
    }
    else = {
        add_character_flag = orichalcum_candidate_lesser
    }
}
```

### Recipe 2: Grant a Maester to a Non-Standard Ruler

If your sub-mod adds rulers outside the Seven Kingdoms who should receive
Citadel maesters:

```
# In a scripted effect or event immediate block:
scope:my_ruler = {
    save_scope_as = ruler
    agot_grab_new_maester_effect = yes
    if = {
        limit = { exists = scope:new_maester }
        set_court_physician_effect = {
            EMPLOYER = scope:ruler
            PHYSICIAN = scope:new_maester
        }
    }
}
```

The key is that `agot_grab_new_maester_effect` checks the pool, then the Citadel
courtiers, then creates from the `maester_character` template as a fallback.

### Recipe 3: Force-Graduate an Acolyte

To immediately complete an acolyte's training (e.g., for a story event):

```
# Target must already have the maester trait
scope:my_acolyte = {
    agot_complete_chain_effect = yes
    # This fills to 12 links and sets XP to 100
    # agot_progress_to_maester_effect is called internally
    # when XP hits 100 during link addition
}
```

### Recipe 4: Custom Maester Expulsion Event

```
scope:bad_maester = {
    agot_expel_appropriate_maester_effect = yes
    # This routes to the correct handler:
    # - archmaester -> agot_expel_archmaester_effect (triggers replacement)
    # - grandmaester -> agot_expel_grandmaester_effect (finds new one)
    # - regular maester -> agot_expel_maester_effect (disgraced + exiled)
}

# To then get a replacement:
scope:ruler = {
    save_scope_as = ruler
    agot_grab_new_maester_effect = yes
}
```

## Pitfalls

### 1. Always check `global_var:citadel_title` exists

Many effects reference `global_var:citadel_title.holder`. If the Citadel has
been destroyed or not yet initialized, this will error. Guard with:

```
if = {
    limit = { exists = global_var:citadel_title }
    # ...safe to use global_var:citadel_title.holder
}
```

### 2. Trait XP = 100 means full maester, not just "has maester trait"

A character can have `has_trait = maester` with XP 0 (novice) or 34 (acolyte).
Always use `agot_is_maester` or check XP explicitly:

```
# WRONG - matches novices and acolytes too
has_trait = maester

# RIGHT - matches only full maesters
has_trait_xp = { trait = maester  value = 100 }
```

### 3. The `blocked_from_leaving` flag

Acolytes and Citadel residents get `blocked_from_leaving` to prevent AI
departure. If you move a maester out of the Citadel, remove this flag first:

```
if = {
    limit = { has_character_flag = blocked_from_leaving }
    remove_character_flag = blocked_from_leaving
}
```

### 4. Artifact type progression matters

Do not check for only `maester_chain` when looking for a maester's links. The
artifact progresses through types:

```
# Check all three stages:
any_character_artifact = {
    OR = {
        artifact_type = maester_link
        artifact_type = maester_link_collection
        artifact_type = maester_chain
    }
}
```

### 5. The `maester_researcher` flag

Some maesters (10-35% chance, boosted by high learning, intellect, and Valyrian
steel links) get `maester_researcher` on graduation. These maesters stay at the
Citadel and are excluded from `agot_grab_new_maester_effect`. Do not assign them
to courts.

### 6. Seneschal is not a trait -- it is a title

The Seneschal is whoever holds `global_var:citadel_title`. There is no
`seneschal` trait. To find the current Seneschal:

```
global_var:citadel_title.holder = { ... }
```

### 7. Archmaester specialties are inactive traits

Archmaester specialty traits (e.g., `archmaester_silver`, `archmaester_vs`) are
stored as **inactive** traits. Use `has_inactive_trait`, not `has_trait`:

```
# WRONG
has_trait = archmaester_silver

# RIGHT
has_inactive_trait = archmaester_silver
```

### 8. Grand Maester uses inactive trait too

The `grandmaester` trait is made inactive via `make_trait_inactive` after
appointment. Check with `has_inactive_trait = grandmaester`.

### 9. The `recently_employed_maester` flag cooldown

After employing a maester, the ruler gets a `recently_employed_maester` flag (60
days for Westeros, 1 year for Essos). If your event grants a maester through a
side channel, consider removing this flag so the decision does not appear
blocked:

```
remove_character_flag = recently_employed_maester
```

### 10. Women are ejected from the Citadel

`agot_citadel_maintenance.0001` removes all female courtiers from the Citadel
court every tick. If your sub-mod allows female maesters, you must override or
patch this event.
