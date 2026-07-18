# AGOT: Dragon Combat & Warfare

## Overview

AGOT implements three distinct systems where dragons participate in conflict:

1. **Dragon Duels (Dragon-vs-Dragon combat)** -- A multi-round, move-based duel
   system between two dragonriders, triggered when opposing dragonriders meet on
   the battlefield. Managed via the `agot_dragon_combat` event namespace and the
   `dsc_*` scope prefix ("dragon single combat").
2. **Dragon Warfare Events** -- One-off narrative events where a dragon
   terrorizes enemy knights and commanders during regular army combat. Managed
   via `agot_dragon_warfare` events.
3. **Dragon Siege** -- Dragons burning holdings during sieges, dealing county
   damage. Managed via `agot_dragon_siege` events.

All three systems rely on `dragon_combat_effectiveness` (a script value on the
dragon character) as the core stat that determines modifier tiers and outcomes.

## Key Concepts

### Dragon Combat Effectiveness

The central stat is `dragon_combat_effectiveness`, checked on the dragon
character. It is compared against tiered script values `level_two_dragon_combat`
through `level_ten_dragon_combat` to determine which modifier tier to apply.
This drives army modifiers, prowess bonuses, and warfare event outcomes.

### The DSC Scope Convention

Dragon duels use a consistent scope naming convention:

| Scope                         | Meaning                                                         |
| ----------------------------- | --------------------------------------------------------------- |
| `scope:dsc_initiator`         | Who started the combat (receives output/invalidation events)    |
| `scope:dsc_attacker`          | The attacking rider (character)                                 |
| `scope:dsc_defender`          | The defending rider (character)                                 |
| `scope:dsc_attacker_dragon`   | The attacker's dragon (`scope:dsc_attacker.var:current_dragon`) |
| `scope:dsc_defender_dragon`   | The defender's dragon (`scope:dsc_defender.var:current_dragon`) |
| `scope:dsc_chance_of_winning` | Variable on each rider, starts at 50                            |
| `scope:my_foe`                | The opponent (used contextually in the round event)             |
| `dragon_combat_current_round` | Variable on `scope:dsc_defender`, tracks current round          |

### Combat Moves System

Dragon duels are turn-based. Each round, both riders select from a randomized
pool of combat moves presented as event options. Moves are organized into
**three tiers** based on when they unlock, plus a **special moves** category.

Each move:

- Sets a `dsc_attacker_last_move` or `dsc_defender_last_move` flag (used for loc
  and repeat-prevention).
- Calls `adjust_dragon_risk_reward_effect` with a `DUEL_SUCCESS` parameter that
  shifts `dsc_chance_of_winning`.
- May inflict `wound_dragon` on the opponent dragon or have other side effects.

### Win Condition

A duel ends when either rider's `dsc_chance_of_winning` reaches **100 or more**.
If the `round_cap_limit` is hit without a winner, the dragon with higher
`dragon_combat_effectiveness` wins (sudden death), or a coin flip if equal.

### Warfare Scopes

Dragon warfare events expect these scopes:

| Scope                              | Meaning                              |
| ---------------------------------- | ------------------------------------ |
| `scope:dragon_in_battle`           | The dragon fighting                  |
| `scope:dragonrider_in_battle`      | The rider                            |
| `scope:dragon_commander_in_battle` | Army commander (may equal the rider) |
| `scope:enemy_knight`               | A random enemy knight                |
| `scope:enemy_dragonrider`          | Enemy dragonrider, if present        |
| `scope:enemy_commander_in_battle`  | Enemy army commander                 |
| `scope:battle_location`            | Location of the battle               |

### Dragonrider Warfare Protection

AGOT gates vanilla combat phase events behind
`is_current_dragonrider_warfare = no`, meaning dragonriders on dragons cannot be
wounded, maimed, or killed by standard knight/commander phase events. They are
instead processed through the dragon-specific combat systems.

---

## AGOT Scripted API

### Combat Effects (`00_agot_dragon_combat_effects.txt`)

#### `configure_start_dragon_combat_effect`

The entry point for starting a dragon duel. Parameters:

```pdx
configure_start_dragon_combat_effect = {
    DSC_INITIATOR = scope:dragonrider_in_battle
    DSC_ATTACKER = scope:dragonrider_in_battle
    DSC_DEFENDER = scope:enemy_dragonrider
}
```

This effect:

1. Saves the three participant scopes and resolves their dragons.
2. Calls `remove_dragon_combat_info_effect` to clean state.
3. Sets `engaged_in_single_combat` and `engaged_in_dragon_combat` variables on
   both riders.
4. Initializes `dsc_chance_of_winning = 50` on both riders.
5. Sets `dragon_combat_current_round = 1` on the defender.
6. Fires `agot_dragon_combat.1001` on the defender to begin round 1.

#### `select_dragon_tier_1_move_effect` / `select_dragon_tier_2_move_effect` / `select_dragon_tier_3_move_effect`

Each uses a two-layer `random_list`: 70% chance for an ordinary move, 30% for a
special move (if not already used). Within the ordinary branch, moves are
equally weighted at 1000 but have a `sce_regular_combat_repeat_down_weight`
modifier to reduce repeats.

#### `select_special_dragon_tier_move_effect`

Selects from special moves. Key entries:

- **Chomp** (weight 9999) -- requires `can_dragon_chomp` trigger, instant kill.
- **Motivate** -- requires `diplomacy >= very_high_skill_rating` and own dragon
  wounded.
- **Technique from Legend** -- requires `learning >= very_high_skill_rating`.
- **Like a Viper** -- requires `intrigue >= very_high_skill_rating`.
- **Martial Voice** -- requires `martial >= very_high_skill_rating`, opponent
  must be noble.
- **Mocking Boast** -- requires higher `prestige_level` than opponent, opponent
  not `humble`.
- **Terrain moves** (Desert Warrior, Jungle Stalker, Open Terrain Expert, Rough
  Terrain Expert, Forest Fighter) -- require the corresponding terrain trait and
  matching terrain at location.

#### `adjust_dragon_risk_reward_effect`

Shifts `dsc_chance_of_winning` based on the `DUEL_SUCCESS` parameter:

| DUEL_SUCCESS                     | Shift to self | Shift to opponent |
| -------------------------------- | ------------- | ----------------- |
| `dragon_duel_success_none`       | +0            | +0                |
| `dragon_duel_success_low`        | +15           | -15               |
| `dragon_duel_success_medium`     | +30           | -30               |
| `dragon_duel_success_high`       | +45           | -45               |
| `dragon_duel_success_very_high`  | +60           | -60               |
| `dragon_duel_success_guaranteed` | +300          | -300              |

#### `finalise_dragon_combat_results_effect`

Called when a victor is determined. Determines a `dragon_death_rattle` flag
based on the victor's last move (e.g., `sudden_strike`, `dragonfire`,
`driven_to_ground`, `disemboweled`, `eviscerated`, `chomp`). Fires result events
`agot_dragon_combat.1003` (loser) and `agot_dragon_combat.1004` (victor).

#### `wound_dragon`

Called on a dragon character to increment its wound level:

```pdx
scope:dsc_defender_dragon = {
    wound_dragon = yes
}
```

Cycles through `dragon_wounded_1` to `dragon_wounded_5` traits. At
`dragon_wounded_5`, further wounds are capped.

#### `can_dragon_chomp` (scripted trigger)

```pdx
can_dragon_chomp = {
    CHOMPING_DRAGON = scope:dsc_attacker_dragon
    CHOMPED_DRAGON = scope:dsc_defender_dragon
}
```

Compares `dragon_combat_weight_class` values. The chomping dragon must exceed
the target by more than 2 weight classes (or 1 in silly mode).

### Combat Move Effects (`00_agot_dragon_combat_moves_effects.txt`)

Each move has a corresponding `dragon_combat_move_<name>_effect`. The pattern
is:

```pdx
dragon_combat_move_<name>_effect = {
    # Optional side effects (wound_dragon, add_trait, add_stress, etc.)

    # Track last move for loc
    if = {
        limit = { this = scope:dsc_attacker }
        save_scope_value_as = {
            name = dsc_attacker_last_move
            value = flag:dragon_<name>
        }
    }
    if = {
        limit = { this = scope:dsc_defender }
        save_scope_value_as = {
            name = dsc_defender_last_move
            value = flag:dragon_<name>
        }
    }

    # Adjust win chance
    adjust_dragon_risk_reward_effect = {
        DUEL_SUCCESS = dragon_duel_success_<level>
    }
}
```

#### Complete Move Reference

**Tier 1 (always available):**

| Move                   | Flag                            | DUEL_SUCCESS | Side Effect                   |
| ---------------------- | ------------------------------- | ------------ | ----------------------------- |
| Wait and Hope          | `dragon_wait_and_hope`          | none         | --                            |
| Unsure Attack          | `dragon_unsure_attack`          | low          | --                            |
| Enthusiastic Onslaught | `dragon_enthusiastic_onslaught` | high         | 30% chance own dragon wounded |
| Underbelly             | `dragon_underbelly`             | medium       | 50% wound to each dragon      |
| Tail Smash             | `dragon_tail_smash`             | low          | Always wounds opponent dragon |

**Tier 2:**

| Move              | Flag                       | DUEL_SUCCESS | Side Effect                                                                                  |
| ----------------- | -------------------------- | ------------ | -------------------------------------------------------------------------------------------- |
| Guard             | `dragon_guard`             | medium       | --                                                                                           |
| Probing Attack    | `dragon_probing_attack`    | medium       | 20/110 chance wound opponent                                                                 |
| Onslaught         | `dragon_onslaught`         | high         | --                                                                                           |
| Surprise Attack   | `dragon_surprise_attack`   | variable     | Very high vs `trusting`, else random low/medium/high                                         |
| Taunt             | `dragon_taunt`             | none         | Adds `dragon_combat_move_taunt_modifier` to opponent. Requires opponent is AI and not `calm` |
| Go for the Gonads | `dragon_go_for_the_gonads` | high         | 20% wound opponent                                                                           |

**Tier 3:**

| Move              | Flag                       | DUEL_SUCCESS | Side Effect                          |
| ----------------- | -------------------------- | ------------ | ------------------------------------ |
| Strict Guard      | `dragon_strict_guard`      | high         | --                                   |
| Confident Attack  | `dragon_confident_attack`  | medium       | 75% wound opponent                   |
| Expert Onslaught  | `dragon_expert_onslaught`  | very high    | --                                   |
| Lightning Assault | `dragon_lightning_assault` | high         | Always wounds opponent. Only round 1 |
| Tire Opponent     | `dragon_tire_opponent`     | medium       | --                                   |

**Special Moves:**

| Move                  | Flag                           | DUEL_SUCCESS | Requirement                                                                             |
| --------------------- | ------------------------------ | ------------ | --------------------------------------------------------------------------------------- |
| Chomp                 | `dragon_chomp`                 | guaranteed   | `can_dragon_chomp` (2+ weight class difference)                                         |
| Motivate              | `dragon_motivate`              | none         | `diplomacy >= very_high_skill_rating`, own dragon wounded. Heals 1 wound level          |
| Technique from Legend | `dragon_technique_from_legend` | high         | `learning >= very_high_skill_rating`. 50% add `dragon_burned` to opponent               |
| Like a Viper          | `dragon_like_a_viper`          | very high    | `intrigue >= very_high_skill_rating`                                                    |
| Martial Voice         | `dragon_martial_voice`         | very high    | `martial >= very_high_skill_rating`, opponent is noble                                  |
| Mocking Boast         | `dragon_mocking_boast`         | low          | Higher `prestige_level`, opponent not `humble`. Adds stress to opponent, gives prestige |
| Desert Warrior        | `dragon_desert_warrior`        | high         | `has_trait = desert_warrior`, desert/drylands/oasis terrain                             |
| Jungle Stalker        | `dragon_jungle_stalker`        | high         | `has_trait = jungle_stalker`, jungle terrain                                            |
| Open Terrain Expert   | `dragon_open_terrain_expert`   | high         | `has_trait = open_terrain_expert`, farmlands/plains/steppe                              |
| Rough Terrain Expert  | `dragon_rough_terrain_expert`  | high         | `has_trait = rough_terrain_expert`, hills/mountains/wetlands                            |
| Forest Fighter        | `dragon_forest_fighter`        | high         | `has_trait = forest_fighter`, forest/taiga                                              |

All terrain moves also wound the opponent dragon and are canceled if both riders
share the same terrain trait.

### Warfare Effects (`00_agot_dragon_warfare_effects.txt`)

#### `base_dragon_army_modifier_effect`

Applied to the army commander when they have a dragonrider knight. Adds a timed
(2-day) character modifier `base_dragon_army_modifier_1` through
`base_dragon_army_modifier_10` based on the dragon's
`dragon_combat_effectiveness`.

```pdx
base_dragon_army_modifier_effect = {
    DRAGON = var:current_dragon
}
```

#### `dragon_combat_modifier_effect`

A stronger version applied after dragon warfare events fire. Uses
`dragon_combat_modifier_1` through `dragon_combat_modifier_10`, lasting 10 days.

```pdx
dragon_combat_modifier_effect = {
    DRAGON = scope:dragon_in_battle
}
```

#### `dragon_army_modifier_calculation`

The main recalculation effect, called from on-actions. It:

1. Checks the commander is leading an army not in combat.
2. Removes all existing base modifiers via `remove_base_dragon_army_modifiers`.
3. Re-applies `base_dragon_army_modifier_effect` for the commander if they are a
   dragonrider.
4. Iterates all dragonrider knights in the army and applies the same modifier
   for each.
5. Marks each dragon with `dragon_supporting_army` modifier and a
   `supporting_army_of` variable.

#### `agot_give_dragon_battle_prowess`

Gives the dragonrider a prowess modifier (`dragon_battle_prowess_modifier_1`
through `_5`) for 10 days based on dragon combat effectiveness.

#### `base_dragon_army_scorpions_counter_effect`

Applies a counter-modifier (`base_dragon_army_modifier_scorpions_counter_1`
through `_10`) when the enemy has `scorpions` MaA, reducing the dragon's army
bonus.

#### `base_dragon_army_water_wizards_counter_effect`

Same pattern as scorpions but for water wizards:
`base_dragon_army_modifier_water_wizards_counter_1` through `_10`.

#### `agot_call_dragon_warfare_events`

The central dispatcher called from combat phase events. Logic:

1. **If an enemy dragonrider exists** and neither rider is already in a duel:
   triggers `agot_dragon_combat.0001` (dragon duel opening).
2. **Else**, rolls from a weighted `random_list`:
   - Weight 200: Nothing happens (doubled if enemy has scorpions).
   - Weight 20: **A Shattering Roar** (`agot_dragon_warfare.0001`) -- dragon
     roars, applies combat modifier.
   - Weight 20: **A Mad Charge** (`agot_dragon_warfare.0006`) -- knight charges
     the dragon, risk of death.
   - Weight 20: **A Fiery Arrangement** (`agot_dragon_warfare.0011`) -- dragon
     burns enemy formations, scales with combat effectiveness.
   - Weight 20: **A Tail Thwack** (`agot_dragon_warfare.0016`) -- requires a
     brave enemy commander.
   - Weight 0 (modified): **Scorpion event** (`agot_dragon_warfare.0020`).
   - Weight 0 (modified): **Water wizard event** (`agot_dragon_warfare.0040`).

#### `agot_dragon_damage_county_effect`

Used during sieges. Adds the `agot_dragon_fire` county modifier and rolls to
apply progressive `agot_dragon_damage_1` through `agot_dragon_damage_10` tiers,
with stronger dragons burning more effectively.

### Slay Effects (`00_agot_dragon_slay_effects.txt`)

The dragon slaying system (human-vs-dragon, not dragon-vs-dragon) uses a
separate entry point:

#### `agot_configure_start_dragon_slay_effect`

```pdx
agot_configure_start_dragon_slay_effect = {
    INITIATOR = <character>
    HUMAN = <character>
    DRAGON = <dragon character>
    LOCALE = <flag: cave_exterior|cave_interior|wilderness_scope|terrain_scope|battlefield|throne_room|army_camp|agot_icecave>
    PROXIMITY = <0|1|2>
    INVALIDATION_EVENT = <event_id>
}
```

**Locale flags** determine the dragon's abilities:

- Most locales allow `can_fly` flag.
- `cave_interior` and `agot_icecave` allow `can_shake` flag instead (no flying
  indoors).
- `PROXIMITY` controls starting distance (0 = close, 2 = far); values outside
  0-2 default to 2.

Fires `agot_dragon_slaying_events.0100` (proximity 1/2) or
`agot_dragon_slaying_events.0101` (proximity 0).

#### `agot_ds_burn_effect`

Burns the human during dragon slaying. Wrapper around `agot_burn_effect` that
adds `burned` trait XP. If XP reaches 100, sets `ds_death` flag.

```pdx
agot_ds_burn_effect = { MIN = 10 MAX = 30 }
```

#### `agot_dragon_combat_inflict_wounds_effect`

Wounds the human, tracking wound rank. If wounds would exceed rank 3, sets
`ds_death` flag instead.

```pdx
agot_dragon_combat_inflict_wounds_effect = { RANK = 2 }
```

#### `agot_ds_get_dragon_skill_effect`

Sets `var:dragon_skill` (1-10) on the dragon based on `ds_combat_effectiveness`
thresholds.

---

## Combat Phase Events

AGOT modifies both `common/combat_phase_events/00_commander_phase_events.txt`
and `00_knight_phase_events.txt`.

### Commander Phase Changes

Every commander phase event (wound, maim, kill, etc.) adds:

```pdx
is_valid = {
    has_character_flag = calculated_dragon_modifier  # Run dragon calcs first
}
```

Negative events (wound, maim, kill) additionally require:

```pdx
is_current_dragonrider_warfare = no
```

This means dragonriders mounted on dragons bypass standard combat injuries
entirely.

### Knight Phase Changes

Similarly, knight events like `knight_berserker_attack` add
`is_current_dragonrider_warfare = no` to both the knight performing the action
and target selection:

```pdx
is_valid = {
    has_trait = berserker
    # ...
    is_current_dragonrider_warfare = no  # AGOT Added
}
```

This prevents dragonriders from being targeted by or participating in
ground-level knight duels.

---

## Dragon Warfare Event Flow

### Battle Initialization

When a combat phase fires, `agot_call_dragon_warfare_events` is called on the
dragonrider. The full flow:

1. **Phase event triggers** on the knight/commander (vanilla
   combat_phase_events).
2. The `calculated_dragon_modifier` flag gates vanilla events until dragon
   modifiers are processed.
3. `agot_call_dragon_warfare_events` decides between a dragon duel (if enemy
   dragonrider exists) or a warfare event.
4. Warfare events apply `dragon_combat_modifier_effect` to the commander for 10
   days.

### Warfare Event Structure

Each warfare event group follows a **handler pattern**:

```
0001 = hidden handler  -->  fires 0002 (knight), 0003 (commander), 0004 (enemy), 0005 (rider)
```

The handler applies the gameplay effect; individual character events are
narrative with `show_as_tooltip` of the effect.

Example -- A Shattering Roar (`agot_dragon_warfare.0001`):

```pdx
agot_dragon_warfare.0001 = {
    hidden = yes
    immediate = {
        scope:enemy_knight = { trigger_event = { id = agot_dragon_warfare.0002 } }
        if = {
            limit = { NOT = { scope:dragon_commander_in_battle = scope:dragonrider_in_battle } }
            scope:dragon_commander_in_battle = { trigger_event = { id = agot_dragon_warfare.0003 } }
        }
        scope:enemy_commander_in_battle = { trigger_event = { id = agot_dragon_warfare.0004 } }
        scope:dragonrider_in_battle = { trigger_event = { id = agot_dragon_warfare.0005 } }
        scope:dragon_commander_in_battle = {
            dragon_combat_modifier_effect = { DRAGON = scope:dragon_in_battle }
        }
    }
}
```

### A Mad Charge (0006-0010)

An enemy knight charges the dragon. The knight event (`0007`) presents a
fight-or-flee choice:

- **Fight**: Weighted by dragon prowess. 99/1 chance the knight dies (eaten) vs.
  kills the dragon. A dragonslayer who kills the dragon gets the `dragonslayer`
  trait, 1000 prestige, and `nick_the_dragonslayer`.
- **Flee**: Knight takes stress, dragon commander gets combat modifier.

If the dragon dies, the rider is wounded and can optionally duel the enemy
knight via `configure_start_single_combat_effect`.

---

## Sub-Mod Recipes

### Adding a Custom Dragon Combat Move

To add a new move to the dragon duel system, you need three things:

**1. Register the move in the selection effect.** Add it to the appropriate tier
in `00_agot_dragon_combat_effects.txt`. For a Tier 2 ordinary move:

```pdx
# In select_dragon_tier_2_move_effect, inside the "70 = { random_list = {" block:
# My Custom Dive Bomb
1000 = {
    trigger = {
        NOT = { exists = local_var:dragon_combat_move_dive_bomb_flag }
        # Custom requirement: dragon must not be wounded
        OR = {
            AND = {
                this = scope:dsc_attacker
                scope:dsc_attacker_dragon = {
                    NOR = {
                        has_trait = dragon_wounded_1
                        has_trait = dragon_wounded_2
                        has_trait = dragon_wounded_3
                        has_trait = dragon_wounded_4
                        has_trait = dragon_wounded_5
                    }
                }
            }
            AND = {
                this = scope:dsc_defender
                scope:dsc_defender_dragon = {
                    NOR = {
                        has_trait = dragon_wounded_1
                        has_trait = dragon_wounded_2
                        has_trait = dragon_wounded_3
                        has_trait = dragon_wounded_4
                        has_trait = dragon_wounded_5
                    }
                }
            }
        }
    }
    set_local_variable = {
        name = dragon_combat_move_dive_bomb_flag
        value = yes
    }
    # Weight down repeat moves
    modifier = {
        add = sce_regular_combat_repeat_down_weight
        OR = {
            AND = {
                exists = scope:dsc_defender_last_move
                this = scope:dsc_defender
                scope:dsc_defender_last_move = flag:dragon_dive_bomb
            }
            AND = {
                exists = scope:dsc_attacker_last_move
                this = scope:dsc_attacker
                scope:dsc_attacker_last_move = flag:dragon_dive_bomb
            }
        }
    }
}
```

**2. Create the move effect** in `00_agot_dragon_combat_moves_effects.txt`:

```pdx
dragon_combat_move_dive_bomb_effect = {
    # Side effect: wound opponent dragon
    if = {
        limit = { this = scope:dsc_attacker }
        scope:dsc_defender_dragon = { wound_dragon = yes }
        save_scope_value_as = {
            name = dsc_attacker_last_move
            value = flag:dragon_dive_bomb
        }
    }
    if = {
        limit = { this = scope:dsc_defender }
        scope:dsc_attacker_dragon = { wound_dragon = yes }
        save_scope_value_as = {
            name = dsc_defender_last_move
            value = flag:dragon_dive_bomb
        }
    }

    adjust_dragon_risk_reward_effect = {
        DUEL_SUCCESS = dragon_duel_success_high
    }
}
```

**3. Add the option to event `agot_dragon_combat.1001`.** Each move needs an
`option` block with the same pattern as existing moves, plus localization
entries for the move name, tooltip, and feedback descriptions.

### Modifying Dragon Warfare Behavior

To add a new warfare event (e.g., a dragon breathing ice instead of fire):

**1. Create the event chain** following the handler pattern:

```pdx
namespace = my_dragon_warfare

# Handler
my_dragon_warfare.0001 = {
    hidden = yes
    immediate = {
        scope:enemy_knight = { trigger_event = { id = my_dragon_warfare.0002 } }
        scope:dragonrider_in_battle = { trigger_event = { id = my_dragon_warfare.0003 } }
        # Apply the combat modifier
        scope:dragon_commander_in_battle = {
            dragon_combat_modifier_effect = { DRAGON = scope:dragon_in_battle }
        }
    }
}

# Knight narrative event
my_dragon_warfare.0002 = {
    type = character_event
    title = my_dragon_warfare.0002.t
    desc = my_dragon_warfare.0002.desc
    theme = war
    # ... portraits, background ...
    option = {
        name = my_dragon_warfare.0002.a
    }
}
```

**2. Register it in `agot_call_dragon_warfare_events`.** Add a new entry to the
`random_list` in the `else` block:

```pdx
20 = { # Ice Breath
    modifier = {
        factor = 0
        NOT = { exists = scope:enemy_knight }
    }
    # Custom: only for ice dragons
    modifier = {
        factor = 0
        NOT = { scope:dragon_in_battle = { has_trait = dragon_ice } }
    }
    trigger_event = my_dragon_warfare.0001
}
```

### Adding a Dragon Counter (like Scorpions)

AGOT already has patterns for counters:

1. Define a new MaA type (e.g., `dragonbane_archers`).
2. Create a `base_dragon_army_<counter>_counter_effect` following the pattern of
   `base_dragon_army_scorpions_counter_effect`.
3. Register the counter modifiers in `remove_base_dragon_army_modifiers`.
4. Add the check to `agot_call_dragon_warfare_events` "Nothing" weight modifier.
5. Optionally create a warfare event for when the counter triggers.

---

## Pitfalls

### Scope Confusion Between Systems

The dragon duel system uses `dsc_*` scopes while warfare events use
`dragon_in_battle` / `dragonrider_in_battle` / etc. Do not mix them. A common
mistake is trying to reference `scope:dsc_attacker` inside a warfare event or
`scope:dragon_in_battle` inside a duel event.

### Engaged-in-Combat Guards

Both `engaged_in_single_combat` and `engaged_in_dragon_combat` variables must be
cleaned up. If a duel is interrupted (character death, etc.),
`remove_dragon_combat_info_effect` handles cleanup. If you add early-exit paths,
always call this effect.

### Modifier Duration and Stacking

`base_dragon_army_modifier_*` lasts 2 days and is recalculated on every army
action tick via `dragon_army_modifier_calculation`. `dragon_combat_modifier_*`
lasts 10 days and is applied once per warfare event. The 2-day modifiers can
stack if multiple dragonriders are in the same army; each dragon knight adds its
own modifier tier to the commander.

### Round Cap and Sudden Death

If `round_cap_limit` rounds pass without either side reaching 100, sudden death
uses raw `dragon_combat_effectiveness`, not accumulated `dsc_chance_of_winning`.
This means a smaller dragon can win on moves but still lose in sudden death if
the larger dragon survives.

### Chomp Is Nearly Unavoidable

`dragon_chomp` has weight 9999 in the special move selection, meaning it will
always be chosen if the `can_dragon_chomp` trigger passes (2+ weight class
difference). AI also has `factor = 0` on engaging if they would be chomped.
Sub-modders should be aware that very small dragons will almost never survive
against much larger ones.

### Combat Phase Event Dependencies

The `has_character_flag = calculated_dragon_modifier` check in `is_valid` means
all vanilla combat phase events are gated until dragon modifiers are processed.
If you add new combat phase events, include this check or your events will fire
before dragon army modifiers are applied.

### Dragon Slaying Proximity

The `PROXIMITY` parameter in `agot_configure_start_dragon_slay_effect` must be
0, 1, or 2. Any other value silently defaults to 2 (far). At proximity 0 the
fight starts immediately; at 1-2 there is an approach phase.

### Localization Volume

Each combat move requires localization for: the option name, tooltip,
`my_feedback` desc, and `opponent_response` desc -- for a total of 4+ loc keys
per move. Missing any of these will show raw keys in the dragon duel UI.
