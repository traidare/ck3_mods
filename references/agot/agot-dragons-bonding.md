# AGOT: Dragon Bonding & Taming

## Overview

In AGOT, dragons are implemented as **full CK3 characters** with the `dragon`
trait. They live in courts, have personality traits (e.g. `dragon_aggressive`,
`dragon_friendly`), grow over time via prowess and a custom `dragon_size`
variable, and form relationships with human characters through a custom
`agot_dragon` relation type.

The bonding/taming pipeline has three distinct phases:

1. **Bonding** -- establishing the `agot_dragon` relation between a human and an
   unbonded dragon (scheme-based).
2. **Taming** -- mounting and riding a bonded (or wild) dragon, which grants the
   `dragonrider` trait and sets `current_rider`/`current_dragon` variables.
3. **Deepening the bond** -- increasing the `dragon_bond` XP track on the
   `dragonrider` trait (scheme-based).

A separate path exists for **hatching** -- cradling a dragon egg artifact until
it hatches, which creates a new dragon character already bonded.

There is also a **dragon horn** path that bypasses heritage requirements but
requires a sacrifice.

---

## Key Concepts

### Dragon as Character

Every dragon is a CK3 character created via `create_character` with
`template = agot_dragon_template` (or age-specific variants). Dragons are added
as courtiers of their owner's court. Key character flags on dragons:

| Flag/Variable                       | Meaning                                          |
| ----------------------------------- | ------------------------------------------------ |
| `has_trait = dragon`                | Identifies the character as a dragon             |
| `has_character_flag = owned_dragon` | Dragon is owned by someone                       |
| `has_character_flag = in_dragonpit` | Dragon is housed in a dragonpit                  |
| `var:current_rider`                 | Points to the human character riding this dragon |
| `var:past_riders`                   | List variable of previous riders                 |
| `var:pitted_dragon_location`        | County title where the dragon is pitted          |
| `var:cradlemate`                    | The human whose cradle-egg hatched this dragon   |
| `var:lair`                          | Province where a wild dragon lairs               |

### Bond Relationship Model

The system uses a **custom CK3 relation** (`agot_dragon`) plus **variables** on
both sides:

- **Human side:** `var:current_dragon` points to their dragon; the `dragonrider`
  trait is added when tamed.
- **Dragon side:** `var:current_rider` points to their rider;
  `var:current_rider_list` is a list variable for iteration.
- **Relation:** `set_relation_agot_dragon` / `has_relation_agot_dragon` /
  `remove_relation_agot_dragon` manage the CK3 relation.

The `dragonrider` trait has two XP tracks:

- **`dragon_bond`** -- strength of the bond (0-100), increased by the deepen
  bond scheme.
- **`dragon_training`** -- training level, increased by
  `agot_add_dragon_training_xp`.

### Taming vs. Claiming vs. Hatching

| Path                 | Mechanism                                     | Requires Heritage                       | Grants Bond             | Grants Rider                                      |
| -------------------- | --------------------------------------------- | --------------------------------------- | ----------------------- | ------------------------------------------------- |
| **Bond scheme**      | `bond_with_dragon_scheme` (diplomacy)         | Yes (unless `dragons_anyone` game rule) | Yes                     | No (triggers taming event if dragon large enough) |
| **Tame interaction** | `tame_dragon_interaction` (direct)            | Yes (unless `dragons_anyone`)           | Yes (auto)              | Yes                                               |
| **Dragon horn**      | `blow_dragon_horn_interaction`                | No (artifact required)                  | Via horn binding        | Via horn taming                                   |
| **Egg hatching**     | `agot_spawn_bonded_hatchling_from_egg_effect` | N/A (owner hatches)                     | Yes (automatic)         | No (hatchling too small)                          |
| **Dragonpit visit**  | `visit_dragonpit_with_child_interaction`      | Yes                                     | Starts bond for a child | No                                                |

---

## AGOT Scripted API

### Triggers (from `00_agot_dragon_triggers.txt`)

#### Dragon State

```pdx
# True if character is alive, not incapable, not imprisoned, not a hostage,
# has dragonrider trait, and has a living dragon relation not housed separately.
is_current_dragonrider = yes
```

```pdx
# Same as above, plus age >= 14 and NOT { has_character_flag = agot_not_using_dragon }
is_current_dragonrider_warfare = yes
```

```pdx
# True if a pitted dragon's location differs from its rider's capital.
# Called on the dragon. Parameter: DRAGON = <dragon_scope>
dragon_homed_separate_from_rider = { DRAGON = scope:my_dragon }
```

#### Dragonblood Heritage

```pdx
# Core check: does the character have dragonblood?
# Checks: dragonrider_house_modifier, dragonrider/dragonless_dragonrider/dragonwidowed traits,
# historical_dragonseed flag, agot_dragon relation, and game-rule-dependent culture checks.
agot_is_dragonblood_character = yes
```

```pdx
# Extended heritage check including ancestors up to 2-3 generations.
# Used for taming/bonding eligibility.
agot_has_dragonblood_heritage = yes
```

```pdx
# Culture-level check for Valyrian dragonblood cultures.
# True for high_valyrian, westerosi_valyrian, essosi_valyrian, mantaryan, tolosi
# and their children, excluding Free City divergences.
agot_has_dragonblood_culture = yes
```

#### Scheme Eligibility

```pdx
# Can the character start a bond_with_dragon_scheme against TARGET?
# Checks: is_human, no existing dragon relation, dragonblood heritage, target is a dragon with no bond.
can_use_bond_with_dragon_scheme = { TARGET = scope:target_dragon }
```

```pdx
# Can the character start a deepen_bond_with_dragon_scheme against TARGET?
# Checks: has dragonrider trait, has agot_dragon relation with target, bond XP < 100.
can_use_deepen_bond_with_dragon_scheme = { TARGET = scope:target_dragon }
```

#### Dragonpit Access

```pdx
# Check if a pitted dragon is accessible to an actor.
# Respects: banned locations, granted access, realm laws (close_family, extended_family, vassal, open).
agot_can_tame_or_bond_or_etc_with_pitted_dragons = { DRAGON = scope:dragon ACTOR = scope:actor }
```

```pdx
# Character-scoped: does this ruler have an active dragonpit with a dragonkeeper order?
agot_has_an_active_dragonpit = yes

# Does this ruler have multiple active dragonpits?
agot_has_multiple_active_dragonpits = yes

# Title-scoped: is this county title an active dragonpit?
agot_title_is_an_active_dragonpit = yes
```

#### Dragon Naming

```pdx
# Can this character name the given dragon?
# Requires: is_ai = no, dragon is young (age < dragon_maturity_age),
# and either has agot_dragon relation OR is house head of the dragon's bonded character.
allow_naming_of_dragon_trigger = yes  # with $DRAGON$ parameter
```

---

### Effects (from `00_agot_dragon_effects.txt`)

#### Core Bonding Pipeline

These effects form a layered API. Higher-level effects call lower-level ones.

```
agot_tame_dragon              (top level -- full taming)
  +-- agot_set_as_rider       (sets rider variables + dragonrider trait)
  +-- agot_bond_dragon_relation_effect  (sets relation + ownership)
        +-- agot_set_as_owned_dragon    (courtier management + dragonpit removal)
```

##### `agot_tame_dragon`

Full taming effect. Sets rider, grants bond XP, and establishes the relation.

```pdx
# File: common/scripted_effects/00_agot_dragon_effects.txt
agot_tame_dragon = {
    agot_set_as_rider = { RIDER = $TAMER$ DRAGON = $DRAGON$ }
    # Grants dragon_bond XP (30 if cradlemate + dynasty perk, else 5-15 if already bonded)
    agot_bond_dragon_relation_effect = { ACTOR = $TAMER$ DRAGON = $DRAGON$ }
}
```

**Usage:**

```pdx
agot_tame_dragon = { TAMER = scope:character DRAGON = scope:dragon }
```

##### `agot_set_as_rider`

Sets the `current_dragon`/`current_rider` variables, adds the `dragonrider`
trait, creates a memory, and notifies all players.

```pdx
# File: common/scripted_effects/00_agot_dragon_effects.txt
agot_set_as_rider = {
    $RIDER$ = {
        set_variable = { name = current_dragon value = $DRAGON$ }
        remove_trait = dragonless_dragonrider  # if applicable
        add_trait = dragonrider
        create_character_memory = { type = agot_tamed_a_dragon ... }
    }
    $DRAGON$ = {
        set_variable = { name = current_rider value = $RIDER$ }
        clear_variable_list = current_rider_list
        add_to_variable_list = { name = current_rider_list target = var:current_rider }
    }
}
```

##### `agot_bond_dragon_relation_effect`

Establishes ownership and the `agot_dragon` relation. Does NOT set rider
variables.

```pdx
# File: common/scripted_effects/00_agot_dragon_effects.txt
agot_bond_dragon_relation_effect = {
    agot_set_as_owned_dragon = { OWNER = $ACTOR$ DRAGON = $DRAGON$ }
    $ACTOR$ = {
        set_relation_agot_dragon = { reason = test_friend_desc target = $DRAGON$ }
        create_character_memory = { type = agot_bonded_a_dragon ... }
    }
}
```

**Usage:**

```pdx
agot_bond_dragon_relation_effect = { ACTOR = scope:owner DRAGON = scope:dragon }
```

##### `agot_set_as_owned_dragon`

Low-level effect that moves the dragon into the owner's court, handling
dragonpit removal if necessary. Adds `owned_dragon` flag.

```pdx
agot_set_as_owned_dragon = { OWNER = scope:owner DRAGON = scope:dragon }
```

#### Untaming / Unbonding

```pdx
# Full untaming: unbonds, removes rider variables, removes dragonrider trait,
# adds dragonless_dragonrider trait (unless horn-bound), dragon flees.
agot_untame_dragon = { OWNER = scope:owner DRAGON = scope:dragon }
```

```pdx
# Removes the agot_dragon relation and court membership. Dragon flees if alive and not pitted.
agot_unbond_dragon = { OWNER = scope:owner DRAGON = scope:dragon }
```

```pdx
# Called directly on the dragon. Clears rider list, removes owned_dragon and in_dragonpit flags.
agot_free_dragon = yes
```

```pdx
# Called on the dragon. Frees and moves dragon to a neighboring county (avoiding Beyond the Wall).
# Sets var:lair if the dragon did not already have one.
agot_dragon_flees_province = yes
```

#### Taming Attempt (with failure outcomes)

```pdx
# The main taming roll. Uses agot_dragon_taming_modifier for success weight
# and agot_dragon_taming_inverse_modifier for failure weight.
# On success: calls agot_tame_dragon.
# On failure: random_list with outcomes -- death (eaten), burned, wounded, or dragon flees.
agot_try_tame_dragon_effect = { TAMER = scope:character DRAGON = scope:dragon }
```

Failure outcomes in `agot_try_tame_dragon_effect`:

- **Death** (weight 5, reduced by 4 if dragon is in dragonpit)
- **Burned** (weight 10) -- adds `burned` trait with 50-200 XP
- **Wounded** (weight 10) -- `increase_wounds_effect`
- **Dragon flees** (weight 25, only if dragon is in dragonpit or tamer has
  dynasty legacy 3)

#### Dragon Bond XP

```pdx
# Adds dragon_training XP, doubled if dynasty has dragonrider_dynasty_legacy_4.
agot_add_dragon_training_xp = { VALUE = 10 }
```

#### Dragon Aging

```pdx
# Called yearly. Adds prowess and size based on age bracket and dragonpit status.
# Young dragons (<11): +3 prowess, +3 size
# Adolescent (11-14): +2 prowess, +2 size
# Mature (15+): random growth, reduced in dragonpits (especially non-Dragonstone pits).
# Also degrades dragon_bond XP by -5 if rider is far from the pit.
agot_apply_dragon_aging_effect = { DRAGON = scope:dragon }
```

```pdx
# Retroactively applies growth for a dragon's full age. Used at character creation only.
agot_back_apply_dragon_aging_effect = yes
```

---

## Character Interactions

Source file:
`common/character_interactions/00_agot_dragon_bond_interactions.txt`

### `tame_dragon_interaction`

The primary interaction for claiming and riding a dragon.

| Property    | Value                                  |
| ----------- | -------------------------------------- |
| Category    | `interaction_category_diplomacy`       |
| Priority    | 999 (always top)                       |
| Auto-accept | Yes                                    |
| Cooldown    | 1 year (global), 10 years (per dragon) |

**Visibility (`is_shown`):**

- Actor is human, does not have `dragonrider` trait.
- Actor has dragonblood heritage OR has an equipped `dragon_horn` artifact (+ is
  landed with available sacrifice/courtier).
- If actor already has an `agot_dragon` relation, the dragon must be that
  specific relation.
- Recipient (the dragon) has `dragon` trait, no `current_rider`, no other
  `agot_dragon` relation.

**Validation (`is_valid_showing_failures_only`):**

- Actor: not imprisoned, age >= 10, no active `bond_with_dragon_scheme`, not
  beyond the wall, not `dragonwidowed`, no `agot_dragon_disinterest` modifier.
- Dragon: `dragon_size >= dragon_taming_minimum_size`, not in dragon combat.
- Dragonpit access check passes.

**On accept:**

- If actor is NOT bonded to the dragon: fires `dragon_taming_events.0100`
  (unbonded handler).
- If actor IS bonded: fires `dragon_taming_events.0200` (bonded handler).

### `bond_with_dragon_interaction`

Starts the `bond_with_dragon_scheme` against a target dragon.

| Property        | Value                            |
| --------------- | -------------------------------- |
| Category        | `interaction_category_diplomacy` |
| Priority        | 90                               |
| Scheme launched | `bond_with_dragon_scheme`        |

**Visibility:** Delegates to `can_use_bond_with_dragon_scheme` trigger.

### `deepen_bond_with_dragon_interaction`

Starts the `deepen_bond_with_dragon_scheme` to increase `dragon_bond` XP.

| Property        | Value                            |
| --------------- | -------------------------------- |
| Category        | `interaction_category_friendly`  |
| Priority        | 90                               |
| Scheme launched | `deepen_bond_with_dragon_scheme` |

**Visibility:** Delegates to `can_use_deepen_bond_with_dragon_scheme` trigger.

### `blow_dragon_horn_interaction`

Re-taming a dragon that was horn-bound but whose binding is unstable.

| Property | Value                            |
| -------- | -------------------------------- |
| Category | `interaction_category_diplomacy` |
| Priority | 999                              |
| Cooldown | 1 year                           |

**Key requirements:**

- Dragon's `var:horn_binder` must equal the actor.
- Actor must have an equipped `dragon_horn` artifact.
- Dragon must be in actor's `imminent_release` variable list (binding is
  unstable).
- Actor must have an available courtier or prisoner to blow the horn.

**On accept:** Fires `dragon_taming_events.0304`.

### `visit_dragonpit_with_child_interaction`

Allows a ruler to bring a child (age 10-17) to a dragonpit to begin bonding with
an unbonded dragon.

| Property | Value                                |
| -------- | ------------------------------------ |
| Category | `interaction_category_friendly`      |
| Cooldown | 1 year (global), 2 years (per child) |

**Requirements:** Actor has an active dragonpit (or Dragonstone access).
Recipient is a child of appropriate age/house, not already a
dragonrider/dragonwidowed, has dragonblood heritage, and there is an unbonded
dragon in the pit.

### `cradle_egg` (in `00_agot_dragon_interactions.txt`)

Marks a dragon egg artifact as being cradled by the actor.

| Property    | Value                                            |
| ----------- | ------------------------------------------------ |
| Target type | Artifact                                         |
| Filter      | Actor's own artifacts with `dragon_egg` variable |

Sets `cradled_egg` and `cradled_egg_year` variables on the egg artifact. Only
one egg can be cradled at a time.

### `give_egg` (in `00_agot_dragon_interactions.txt`)

Transfers a dragon egg artifact to another character.

---

## Schemes

Source files: `common/schemes/scheme_types/agot_bond_with_dragon_scheme.txt` and
`agot_deepen_bond_with_dragon_scheme.txt`

### `bond_with_dragon_scheme`

| Property           | Value     |
| ------------------ | --------- |
| Skill              | Diplomacy |
| Base progress goal | 365 days  |
| Base max success   | 65%       |
| Minimum success    | 0%        |
| Cooldown           | 5 years   |
| Uses resistance    | No        |

**Allow:** `can_use_bond_with_dragon_scheme`, age >= 6, not imprisoned. Target
dragon must also be age >= 6 and not imprisoned.

**Valid (ongoing):** Owner has no `agot_dragon` relation, no `dragonwidowed`
trait, no `agot_dragon_disinterest` modifier. Target is a dragon with no
existing `agot_dragon` relation. Dragonpit access still valid.

**On phase completed:** Fires `dragon_bond_events.0001` which rolls
success/failure based on `scheme_success_chance`. Canon rider-dragon pairs are
guaranteed to succeed (failure factor = 0).

### `deepen_bond_with_dragon_scheme`

| Property           | Value     |
| ------------------ | --------- |
| Skill              | Diplomacy |
| Base progress goal | 365 days  |
| Base max success   | 95%       |
| Minimum success    | 20%       |
| Cooldown           | 2 years   |

**Valid (ongoing):** Owner has `agot_dragon` relation with target. Target has
`dragon` trait.

**On phase completed:** Fires `dragon_bond_events.2000`, rolling
success/failure. Success grants 12-15 `dragon_bond` XP (or 15-30 if cradlemate +
dynasty legacy 2).

**Monthly (`on_monthly`):** Fires `dragon_strengthen_bonding_ongoing` on_action,
which triggers ongoing bonding events (e.g. feeding the dragon charred meat at
`dragon_bond_events.3000`).

---

## Events & Story Cycles

### Taming Events (`events/agot_events/agot_dragon_taming_events.txt`)

**Namespace:** `dragon_taming_events`

| ID Range  | Purpose                 |
| --------- | ----------------------- |
| 0100-0199 | Taming unbonded dragons |
| 0200-0299 | Taming bonded dragons   |
| 0300+     | Dragon horn events      |

**`dragon_taming_events.0100`** -- Hidden handler for unbonded dragon taming.
Routes to `0101`.

**`dragon_taming_events.0101`** -- Main taming event. Player chooses:

- **Option A:** Attempt taming (calls `agot_try_tame_dragon_effect`). AI weighs
  traits like arrogant, ambitious, and dynasty perks.
- **Option B (Dragon Horn):** Available only with equipped `dragon_horn`
  artifact + available sacrifice. Routes to `dragon_taming_events.0300`.
- **Option C:** Back out (resets cooldowns).

**`dragon_taming_events.0200`** -- Hidden handler for bonded dragon taming.
Routes to `0201`.

**`dragon_taming_events.0201`** -- Taming a dragon the character is already
bonded with. Calls `agot_try_tame_dragon_effect`. Still carries failure risks.

**`dragon_taming_events.0300`** -- Dragon horn selection event. Player picks a
courtier or prisoner to blow the horn. The blower typically dies from the horn's
effects.

### Bond Events (`events/agot_events/agot_dragon_bond_events.txt`)

**Namespace:** `dragon_bond_events`

**`dragon_bond_events.0001`** -- Handler for `bond_with_dragon_scheme`
completion. Rolls success (`1000`) or failure (via `dragon_bonding_failure`
on_action).

**Success path:**

- **`dragon_bond_events.1000`** -- Bond established. Calls
  `agot_bond_dragon_relation_effect`. If dragon is large enough
  (`dragon_size >= dragon_taming_minimum_size`), immediately fires
  `dragon_taming_events.0201` for taming.

**Failure paths:**

- **`dragon_bond_events.1001`** -- Default failure. Stress gain. Scheme ends.
- **`dragon_bond_events.1002`** -- Dragon burns you (weighted by
  `dragon_bloodthirsty`, `dragon_aggressive`, `dragon_impulsive`). Adds `burned`
  trait + wounds.
- **`dragon_bond_events.1003`** -- Dragon kills you. Death reason:
  `death_dragon_fire_failed_tame`. Only triggers for unowned
  aggressive/bloodthirsty dragons.

**Deepen bond path:**

- **`dragon_bond_events.2000`** -- Handler for `deepen_bond_with_dragon_scheme`.
- **`dragon_bond_events.2001`** -- Success. Grants `dragon_bond` XP (12-15 base,
  15-30 with cradlemate + dynasty perk). Dragon gains positive opinion of rider.
- **`dragon_bond_events.2002`** -- Failure. Dragon gains negative opinion
  (`failed_to_bond_with_me`).

**Ongoing bond events (3000+):**

- **`dragon_bond_events.3000`** -- Feed the dragon a charred meal. Options:
  sheep (medium gold), pig (minor gold), ox (major gold). Each has
  success/failure modifiers applied to the scheme.

### Dragon Spawning (`common/scripted_effects/00_agot_dragon_spawning_effects.txt`)

Key spawning effects, all saving the new dragon as `scope:dragon`:

```pdx
# Spawns an adult dragon (age 30-100) already owned by the calling character.
agot_spawn_owned_adult_dragon_effect = yes

# Spawns a hatchling from an egg, owned by OWNER. Handles canon dragon logic.
# Removes the egg artifact.
agot_spawn_owned_hatchling_from_egg_effect = { OWNER = scope:owner EGG = scope:egg }

# Spawns a hatchling AND establishes the bond relation. Used for cradle-hatched eggs.
# If the cradlemate has destiny_child, the dragon gets dragon_destined trait.
agot_spawn_bonded_hatchling_from_egg_effect = { OWNER = scope:owner EGG = scope:egg }

# Spawns a wild hatchling from an egg (no owner, no bond).
agot_spawn_wild_hatchling_from_egg_effect = { EGG = scope:egg }

# Spawns a wild adult dragon (age 30-100) as a courtier of the calling character.
agot_spawn_wild_dragon_effect = yes

# Age-specific spawning (no owner set):
agot_spawn_young_dragon_effect = yes     # Uses agot_young_dragon_template
agot_spawn_adult_dragon_effect = yes     # Uses agot_adult_dragon_template
agot_spawn_old_dragon_effect = yes       # Uses agot_old_dragon_template
agot_spawn_monster_dragon_effect = yes   # Uses agot_monster_dragon_template
```

---

## Sub-Mod Recipes

### Adding a New Taming Interaction

To add a custom interaction that lets a character attempt to tame a dragon with
different conditions (e.g., a maesters-only scholarly approach):

```pdx
# my_mod/common/character_interactions/my_scholarly_tame_interaction.txt
scholarly_tame_dragon_interaction = {
    icon = icon_scheme_dragon
    category = interaction_category_diplomacy
    interface_priority = 90
    auto_accept = yes
    cooldown = { years = 2 }

    is_shown = {
        scope:actor = {
            is_human = yes
            NOT = { has_trait = dragonrider }
            has_trait = education_learning_4  # Only master scholars
            # Reuse AGOT's heritage check
            agot_has_dragonblood_heritage = yes
        }
        scope:recipient = {
            has_trait = dragon
            NOT = { has_variable = current_rider }
            NOR = {
                any_relation = {
                    type = agot_dragon
                    NOT = { this = scope:actor }
                }
            }
        }
    }

    is_valid_showing_failures_only = {
        scope:actor = {
            is_imprisoned = no
            age >= 16
        }
        scope:recipient = {
            dragon_size >= dragon_taming_minimum_size
        }
        # Reuse AGOT's dragonpit access check
        agot_can_tame_or_bond_or_etc_with_pitted_dragons = {
            DRAGON = scope:recipient ACTOR = scope:actor
        }
    }

    on_accept = {
        # Use the existing AGOT taming effect
        agot_try_tame_dragon_effect = {
            TAMER = scope:actor
            DRAGON = scope:recipient
        }
    }
}
```

### Modifying Bond Behavior

To grant extra `dragon_bond` XP when a character with a specific trait tames a
dragon, create a scripted effect that wraps the AGOT one:

```pdx
# my_mod/common/scripted_effects/my_dragon_bond_effects.txt
my_enhanced_tame_dragon = {
    # Call the base AGOT taming
    agot_tame_dragon = { TAMER = $TAMER$ DRAGON = $DRAGON$ }

    # Extra bond XP for characters with our custom trait
    $TAMER$ = {
        if = {
            limit = { has_trait = my_dragon_whisperer_trait }
            add_trait_xp = {
                trait = dragonrider
                track = dragon_bond
                value = 20
            }
        }
    }
}
```

Then reference `my_enhanced_tame_dragon` in your interaction's `on_accept`
instead of calling the AGOT effects directly.

### Custom Dragon Bonding Events

To add events that fire during the deepen bond scheme's monthly tick, create
events triggered by the `dragon_strengthen_bonding_ongoing` on_action:

```pdx
# my_mod/events/my_dragon_bond_events.txt
namespace = my_dragon_bond

my_dragon_bond.0001 = {
    type = character_event
    title = my_dragon_bond.0001.t
    desc = my_dragon_bond.0001.desc
    theme = dragon

    # Weight so it does not always fire
    weight_multiplier = {
        base = 0
        modifier = {
            scope:target = { has_trait = dragon_friendly }
            add = 1
        }
    }

    # Guard: only fire if deepen bond scheme is active
    trigger = {
        any_scheme = { scheme_type = deepen_bond_with_dragon_scheme }
    }

    left_portrait = root
    right_portrait = {
        character = scope:target
        animation = dragon_main
        camera = camera_dragon_event_standing
        outfit_tags = { linear_camera_zoom }
    }

    option = {
        name = my_dragon_bond.0001.a
        add_trait_xp = {
            trait = dragonrider
            track = dragon_bond
            value = 5
        }
    }
}
```

Register your event in the on_action (or use AGOT's existing on_action file as a
load-order override).

---

## Pitfalls

### 1. Forgetting to call the full effect chain

Do not set `current_rider`/`current_dragon` manually. Always use
`agot_tame_dragon` or at minimum `agot_set_as_rider` +
`agot_bond_dragon_relation_effect`. These effects handle courtier management,
dragonpit removal, memory creation, player notifications, and variable
bookkeeping that are easy to miss.

### 2. Not checking `is_alive` guards

Many AGOT effects include `is_alive = yes` checks because the same code paths
run from history files where characters may be dead. If you call
`agot_set_as_rider` in a history context, the variable-setting blocks will
silently skip dead characters.

### 3. Dragonpit access checks

If your interaction targets pitted dragons, you **must** include
`agot_can_tame_or_bond_or_etc_with_pitted_dragons`. Forgetting this bypasses
realm laws (`dragonpit_close_family_law`, etc.) and ban lists, which will
confuse players and break balance.

### 4. Dragon size minimum for taming

A dragon must have `dragon_size >= dragon_taming_minimum_size` (currently 30) to
be ridden. The bond scheme's success event (`dragon_bond_events.1000`) checks
this before offering taming. If you skip this check, the game will allow
mounting hatchlings, which is not intended.

### 5. Confusing bond vs. tame

**Bonding** (`agot_bond_dragon_relation_effect`) creates the relationship but
does NOT make the character a dragonrider. **Taming** (`agot_tame_dragon`) does
both. A character can be bonded to a hatchling but not be a dragonrider until
the dragon grows large enough and they tame it.

### 6. The `agot_` prefix convention

All AGOT scripted triggers and effects use the `agot_` prefix. When searching
for APIs, always search with this prefix. Note that some older effects (like
`dragon_homed_separate_from_rider`) lack the prefix -- these are exceptions, not
the rule.

### 7. Dragon personality traits affect outcomes

Dragon traits like `dragon_aggressive`, `dragon_bloodthirsty`,
`dragon_impulsive`, `dragon_friendly`, `dragon_cooperative`, etc. directly
influence bonding failure weights and taming outcomes. Sub-mods that add new
dragon personalities should add corresponding `weight_multiplier` entries to
bonding failure events.

### 8. Horn-bound dragons need special handling

Dragons tamed via `dragon_horn` get the `dragon_by_horn` flag on the rider. When
untamed, these riders do NOT receive the `dragonless_dragonrider` trait (they
lose the flag instead). The dragon also has a `var:horn_binder` variable. Horn
bindings can become unstable (added to `imminent_release` list), requiring the
`blow_dragon_horn_interaction` to re-stabilize.

### 9. The `dragonwidowed` trait blocks all dragon interactions

Characters who lost their dragon to death receive `dragonwidowed`, which blocks
taming, bonding, and dragonpit visits. If your sub-mod wants to allow re-bonding
for dragonwidowed characters, you must explicitly handle the trait removal.

### 10. Always test with both `dragons_anyone` game rule states

Many visibility triggers contain `trigger_if` blocks that only check
`agot_has_dragonblood_heritage` when `dragons_anyone` is disabled. Your sub-mod
should respect this pattern to remain compatible with both game rule settings.
