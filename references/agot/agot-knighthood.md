# AGOT: Knighthood & Squirehood

## Overview

The AGOT mod replaces vanilla CK3 knight mechanics with a lore-accurate
knighthood system built around the Faith of the Seven. Characters progress from
**squire** to **knight** through a leveled trait track (`squire` trait with
`knight` track), scripted relations (`agot_squire` / `agot_knight`), character
interactions, story cycles, and dedicated event chains.

Key files at a glance:

| Layer                  | File(s)                                                                                                                                                        |
| ---------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Scripted Effects       | `common/scripted_effects/00_agot_knighthood_effects.txt`                                                                                                       |
| Knight Tree Effects    | `common/scripted_effects/00_agot_knight_tree_effects.txt`                                                                                                      |
| Scripted Triggers      | `common/scripted_triggers/00_agot_knighting_triggers.txt`                                                                                                      |
| Character Interactions | `common/character_interactions/00_agot_knight_interactions.txt`                                                                                                |
| Scripted Relations     | `common/scripted_relations/00_agot_scripted_relations_knighting.txt`                                                                                           |
| Opinion Modifiers      | `common/opinion_modifiers/agot_opinion_modifiers_knighting.txt`                                                                                                |
| Story Cycles           | `common/story_cycles/agot_story_cycle_squire_ongoing.txt`, `agot_story_cycle_knight_tree.txt`                                                                  |
| On-Actions             | `common/on_action/agot_on_actions/agot_knight_on_actions.txt`, `relations/agot_knight_relation_on_actions.txt`, `agot_story_cycles/agot_squire_on_actions.txt` |
| Events                 | `events/agot_events/agot_knighthood_events.txt`, `agot_knighthood_maintenance_events.txt`, `agot_squirehood_ongoing_events.txt`                                |
| Script Values          | `common/script_values/00_agot_knight_tree_values.txt`                                                                                                          |
| Game Concepts          | `common/game_concepts/00_agot_knighthood_game_concepts.txt`                                                                                                    |

---

## Key Concepts

### The Squire Trait and Knight Track (PTK)

AGOT uses a **leveled trait** called `squire` with a secondary track called
`knight`. The XP on this track is informally referred to as **PTK** (Progress To
Knighthood).

- **PTK 0-65**: Active squire, still training.
- **PTK 66+**: Eligible for knighting (threshold checked by interactions and
  story cycle).
- **PTK 100**: The character is considered a knight (`is_agot_knight_trigger`).

When a character is knighted via `agot_become_a_knight_effect`, the trait XP is
set to 100:

```pdx
add_trait_xp = {
    trait = squire
    track = knight
    value = 100
}
```

If the character does not already have the `squire` trait, it is added first.
The vanilla `knight` trait also exists and is checked: `is_agot_knight_trigger`
returns true for either `has_trait = knight` OR `squire` track XP >= 100
(without an active ongoing squire story).

### Scripted Relations

Defined in `00_agot_scripted_relations_knighting.txt`:

```pdx
agot_squire = {
    corresponding = agot_knight
    special_guest = no
    title_grant_target = no
}

agot_knight = {
    corresponding = agot_squire
    special_guest = no
    title_grant_target = no
}
```

These are **bidirectional**: setting `set_relation_agot_squire` on a knight
automatically creates the `agot_knight` relation on the squire. A knight can
have up to **2 squires** (`num_of_relation_agot_squire < 2` in
`agot_can_take_squire_trigger`).

### The `can_grant_knighthood` Doctrine Parameter

Throughout the system, the faith doctrine parameter `can_grant_knighthood` gates
religious legitimacy. Characters whose faith has this parameter gain extra
prestige and piety from knighting and being knighted. Characters whose faith
lacks it are heavily penalized in AI acceptance (-200 in most interactions).

### Opinion Modifiers

All opinion modifiers are defined in `agot_opinion_modifiers_knighting.txt` and
are **decaying** (`monthly_change = 0.1`):

| Modifier Key                   | Context                                                                 |
| ------------------------------ | ----------------------------------------------------------------------- |
| `made_me_squire_opinion`       | Squire toward their knight (+15)                                        |
| `became_my_squire_opinion`     | Knight toward their squire (+10)                                        |
| `knighted_me_opinion`          | New knight toward their knight-maker (+25 or +50 with knighthood tenet) |
| `i_made_you_a_knight_opinion`  | Knight-maker toward the new knight (+25)                                |
| `removed_me_as_squire_opinion` | Former squire toward former knight (-50)                                |
| `removed_my_squire_opinion`    | Former knight toward ruler who removed the squire (-50)                 |
| `stripped_my_knighthood`       | Stripped knight toward the one who stripped them (-50)                  |

---

## AGOT Scripted API (Triggers and Effects)

### Triggers (from `00_agot_knighting_triggers.txt`)

#### `is_agot_knight_trigger`

Returns yes if the character is a knight.

```pdx
is_agot_knight_trigger = {
    OR = {
        has_trait = knight
        AND = {
            has_trait_xp = { trait = squire  track = knight  value >= 100 }
            NOT = { any_owned_story = { story_type = story_agot_squire_ongoing } }
        }
    }
}
```

#### `is_eligible_for_agot_squirehood_trigger`

Checks if a character can become a squire:

- Male, or female with `agot_tomboy_modifier` + high prowess/martial.
- Age 9-21 (inclusive).
- Not already a squire (unless knightless).
- No disqualifying traits.
- Not imprisoned.
- No existing knight relation (`num_of_relation_agot_knight = 0`).

#### `agot_has_traits_preventing_knighthood_trigger`

Blocks knighthood for characters with: `blind`, `dwarf`, `clubfooted`,
`one_legged`, `one_handed`, `incapable`, `infirm`, `physique_bad_1/2/3`,
`crippled`, `septon`, `maester`, or already a knight.

#### `agot_can_become_a_knight_trigger`

Full eligibility for being knighted:

- No disqualifying traits.
- Male, or female with `squire` trait, or gender-equal/female-dominated faith.
- Not a `former_acolyte`.
- Age >= 16, or age 12-15 with `extremely_high_skill_rating` prowess.
- Not flagged `cannot_be_knighted` and no `stripped_knight` trait.

#### `agot_can_take_squire_trigger`

Checks if a character can be a knight-mentor:

- Adult, human, passes `is_agot_knight_trigger`.
- Has fewer than 2 squires.
- Not `incapable`, not imprisoned.

#### `is_squire_with_trait_xp`

Returns yes if the character is an active squire (has squire trait with PTK <
100 or has PTK >= 100 but still has the ongoing story).

#### `agot_is_squire_with_knight`

Squire with PTK >= 0 AND has an `agot_knight` relation.

#### `agot_can_revoke_knighthood_punishment_trigger`

Actor must: have `can_grant_knighthood` faith, be landed, hold title tier >=
`tier_empire` (king-level in AGOT). Recipient must be a knight and in actor's
realm.

### Effects (from `00_agot_knighthood_effects.txt`)

#### `agot_become_a_knight_effect`

**The core knighting effect.** Parameters: `KNIGHT_MAKER`, `KNIGHT_TO_BE`.

What it does:

1. Adds `squire` trait if missing, sets track XP to 100.
2. Removes `agot_knighthood_knightless_squire_flag` if present.
3. Removes the `agot_squire`/`agot_knight` relation between the two.
4. Handles court relocation post-squirehood.
5. Ends the `story_agot_squire_ongoing` story.
6. Notifies close family (`agot_knighthood.0320`).
7. Creates memories (different types for: normal, tourney prize, battlefield,
   bought).
8. Adds opinion modifiers and prestige/piety.
9. Calls `agot_add_to_knight_tree` (unless `skip_tree_assignment` flag is set).
10. Special lore hooks: Dayne dynasty triggers `agot_valyrian_steel.0001` (Sword
    of the Morning), Targaryen triggers Dark Sister event.

#### `agot_add_become_a_knight_prestige_effect`

Calculates prestige bonus based on the knight-maker's dynasty prestige level
(3-10), personal prestige level (4+), Kingsguard status, family relationship,
and the squire's heir status. Base is 50 prestige, can scale up to 225+.

#### `agot_offer_squire_interaction_effect`

Sets the `agot_squire` relation, adds `squire` trait, creates the
`story_agot_squire_ongoing` story, handles court movement, creates memories,
adds opinion modifiers.

#### `agot_offer_knight_tutelage_interaction_effect`

Similar to above but used for the cross-court knight tutelage interaction. Does
not add the initial `became_my_squire_opinion`/`made_me_squire_opinion` on the
knight.

#### `agot_set_squire_effect`

Simplified version for script use (e.g., hedge knight events). Sets relation,
adds trait, creates story, creates memories, handles movement. Does not use
hooks or stress.

#### `agot_strip_knighthood_as_punishment_effect`

Parameters: `STRIPPER`, `KNIGHT`. Removes knight trait or squire trait, adds
`stripped_knight` trait, applies prestige/piety loss, removes all squire
relations, flags `cannot_be_knighted`, creates memories.

#### `agot_add_squire_trait_xp_effect`

Adds PTK XP with a bonus if the squire's knight has the
`chivalric_dominance_perk`:

```pdx
agot_add_squire_trait_xp_effect = {
    add_trait_xp = {
        trait = squire
        track = knight
        value = {
            value = 0
            add = {
                integer_range = { min = $MIN_VALUE$ max = $MAX_VALUE$ }
                if = {
                    limit = {
                        any_relation = {
                            type = agot_knight
                            has_perk = chivalric_dominance_perk
                        }
                    }
                    add = { 5 10 }
                }
            }
        }
    }
}
```

#### `agot_init_squire_story_cycle_effect`

Creates `story_agot_squire_ongoing` if the character has not already had one,
then shows a toast notification.

#### `agot_tournament_reward_knighthood_prize`

Wrapper for knighting a tourney winner. Sets the
`agot_knighthood_as_tourney_prize` flag then calls
`agot_become_a_knight_effect`.

#### `agot_move_knight_for_education_or_squiring_purposes`

Complex court-movement logic: moves the squire to the knight's court (or vice
versa) depending on who is playable, landed, has a guardian, or holds a court
position.

---

## Character Interactions

All defined in `00_agot_knight_interactions.txt`.

### `agot_offer_knighthood_interaction`

**Category:** Diplomacy. **Cost:** Medium prestige.

The actor offers knighthood to the recipient. Shown when:

- Actor is an adult knight (or hegemony-tier ruler with knighthood doctrine).
- Recipient passes `agot_can_become_a_knight_trigger`.
- Recipient is a courtier, vassal, same court, guardian relation, or squire of
  actor.
- Recipient is a squire with PTK >= 66, or a knightless squire, or not a squire
  at all.

**Auto-accept:** If the recipient is the actor's squire
(`has_relation_agot_knight = scope:actor`).

AI acceptance weighs: boldness, zeal, greed, energy, honor, sociability,
education type, faith doctrine, relations, house feuds, prestige levels, and
lowborn/highborn dynamics.

### `agot_educate_squire_interaction`

**Category:** Diplomacy. **Auto-accept:** Yes (same-court).

Designates a knight and squire within the same court. Uses `secondary_actor`
(knight) and `secondary_recipient` (squire). Calls
`agot_offer_squire_interaction_effect`.

Redirect logic: if the actor is eligible for squirehood, they become the
secondary_recipient; if they can take a squire, they become the secondary_actor.

### `agot_offer_squire_interaction`

**Category:** Diplomacy.

Offers a squire from your court to a landed character's court. The recipient can
decline (unless a strong hook is used). AI acceptance factors: opinion, rank
difference, lowborn status, faith, age of squire candidate.

### `agot_offer_knight_tutelage_interaction`

**Category:** Diplomacy.

Offers a knight from your court to tutor a squire in another lord's court.
Mirror of the offer-squire interaction. Calls
`agot_offer_knight_tutelage_interaction_effect`.

### `agot_remove_my_squire_interaction`

**Category:** Diplomacy. **Auto-accept:** Yes.

A knight removes their own squire. Creates memories on both sides, applies -50
opinion (`removed_me_as_squire_opinion`), flags the squire with
`agot_knighthood_was_removed_as_a_squire_flag`.

### `remove_knight_interaction`

**Category:** Friendly. **Auto-accept:** Yes.

A ruler recalls their child from a knight's tutelage. Only shown if the child is
unlanded, is a child of the actor, and has an `agot_knight` relation. Returns
the child to the parent's court and fires maintenance events.

### `agot_train_squire_interaction`

**Category:** Diplomacy. **Auto-accept:** Yes. **Cooldown:** 32 days per
recipient.

A knight actively trains their squire, firing `agot_squirehood_ongoing.0400` --
a training event with multiple skill-focus options (Strategy, Swordsmanship,
Horsemanship, Ethics). Each option has weighted success/failure outcomes that
add PTK XP.

---

## Events & Story Cycles

### Story Cycle: `story_agot_squire_ongoing`

Defined in `common/story_cycles/agot_story_cycle_squire_ongoing.txt`. Created
when a squire is assigned a knight.

**On setup:** Sets `had_ongoing_squire_story` flag and `years_as_squire = 0`.

**On end:** Cleans up skill increment tracking variables
(`squirehood_skill_inc_check_diplomacy`, `_martial`, `_stewardship`,
`_learning`, `_prowess`).

**Effect groups:**

| Interval               | Purpose                                                                                                                             |
| ---------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| 21-32 days             | **AI training sim** for unplayable characters. Fires `agot_squirehood_ongoing.0400` (same event as the player interaction).         |
| ~100 days (65% chance) | **Random ongoing squire events** via `ongoing_squire_events` on-action (18 events, `agot_squirehood_ongoing.0001` through `.0018`). |
| 1 day                  | **Auto-promotion for unlanded AI squires** with PTK >= 66. Fires `agot_knighthood.0300`.                                            |
| 91-92 days             | **Auto-promotion for landed AI squires** with tier >= county and age >= 16. Fires `agot_knighthood_maintenance.0500`.               |
| 365 days               | **Age-out counter**: increments `years_as_squire` each year after age 22.                                                           |
| 365 days               | **Forced removal**: ends squirehood if `years_as_squire >= 15` via `agot_knighthood_maintenance.0400`.                              |
| 91-92 days             | **War check**: ends the knight-squire relation if either side (or their lieges) are at war with each other.                         |

### Ongoing Squire Events (`agot_squirehood_ongoing`)

18 random flavor events that fire during squirehood, each covering a different
activity:

- `.0001` - Horse riding practice (Martial)
- `.0002` - Cleaning armor (Martial)
- `.0003` - Swordsmanship with knight (Prowess)
- `.0004` - Swordsmanship with fellow squire (Prowess)
- `.0005` - Solo swordsmanship (Prowess)
- `.0006` - Cleaning knight's armor (Learning)
- `.0007` - Learning a new sigil (Learning)
- `.0008` - Rallying speech practice (Diplomacy)
- `.0009` - Chivalrous conduct practice (Diplomacy)
- `.0010` - Rendering village aid (Stewardship)
- `.0011` - Tending to animals (Stewardship)
- `.0012` - Training yard practice (Martial)
- `.0013` - Cleaning weapons (Martial)
- `.0014` - Carrying knight's arms on errands (Martial)
- `.0015` - Left in charge of pages (Diplomacy)
- `.0016` - Reciting known sigils (Learning)
- `.0017` - Battlefield commands with fellow squire (Diplomacy)
- `.0018` - Generic downtime training (Diplomacy or Martial options)

Each event uses `available_for_squirehood_events` as a trigger (requires
`agot_is_squire_with_knight` and a cooldown flag). Skill increases use
`try_squire_increment_skill_effect`, which has a 20% chance to add +1 to a
skill, capped at 2 increases per skill during squirehood.

### PTK Boost Events

- `agot_squirehood_ongoing.0230`: On 16th birthday, +5-10 PTK.
- `agot_squirehood_ongoing.0231`: Every birthday after 16, +1 PTK.
- `agot_squirehood_ongoing.0232`: One-time prowess-based PTK boost (+10 if high
  prowess, +10-15 if very high).

### Training Event (`agot_squirehood_ongoing.0400`)

Fired by both the `agot_train_squire_interaction` and the AI training sim in the
story cycle. The knight chooses between training focuses (Strategy,
Swordsmanship, Horsemanship, Ethics). Weighted outcomes grant PTK XP based on
the squire's traits and skills.

### Knighthood Events (`agot_knighthood`)

| Event ID      | Description                                                          |
| ------------- | -------------------------------------------------------------------- |
| `.0016`       | A hedge knight offers to make your son his squire                    |
| `.0017-.0019` | Follow-up events for hedge knight squire offer                       |
| `.0300`       | AI auto-knighting of a squire at PTK >= 66                           |
| `.0320`       | Notification to close family when someone is knighted                |
| `.0600-.0602` | **Battlefield knighting** chain (triggers on `on_combat_end_winner`) |
| `.0700-.0701` | Hedge knight offering knighthood to a lord's son                     |
| `.0800`       | Quarterly pulse: flavor event for knight characters                  |
| `.0801`       | Quarterly pulse: another knight flavor event                         |
| `.0802`       | Follow-up event                                                      |

### Battlefield Knighting Chain

Triggered via `on_combat_end_winner` on-action (600/950 weight).
`agot_knighthood.0600` fires on the combat side scope, checks if the side
commander is a knight and any side knight is eligible for knighthood. The
commander gets an event (`.0601`) to decide whether to knight the soldier. On
acceptance, `.0602` fires with the `agot_had_battlefield_knighthood` flag,
creating a battlefield-specific memory.

### Maintenance Events (`agot_knighthood_maintenance`)

| Event ID      | Description                                                                     |
| ------------- | ------------------------------------------------------------------------------- |
| `.0001`       | Hidden quarterly check: squire gained disqualifying traits                      |
| `.0005`       | Knight perspective: squire disqualified notification                            |
| `.0006`       | Squire perspective: disqualified notification                                   |
| `.0007`       | Knight and squire at war: relation dissolved                                    |
| `.0008-.0009` | Follow-up events for war dissolution                                            |
| `.0010`       | Knight died: squire mourns / needs new knight                                   |
| `.0011`       | Follow-up for knight death                                                      |
| `.0012`       | Deathbed knighting: knight with PTK >= 51 squire grants knighthood before dying |
| `.0300`       | Knightless squire cleanup timer (4 months AI / 1 year player)                   |
| `.0400`       | Forced squirehood end after 15 years over age 22                                |
| `.0500`       | Landed AI squire auto-promotion check                                           |
| `.0501`       | Follow-up for landed AI promotion                                               |
| `.0550-.0551` | Remove-knight interaction follow-ups                                            |

### On-Actions

**`agot_knight_on_actions.txt`:**

- `quarterly_playable_pulse` hooks `agot_knight_quarterly_playable_pulse`
  (random knight flavor events).
- `on_birthday` hooks `agot_knight_on_birthday` (PTK +1 per year after 16).
- `on_16th_birthday` hooks `agot_knight_on_16th_birthday` (PTK +5-10 boost).
- `on_combat_end_winner` hooks `agot_knight_on_combat_end_winner` (battlefield
  knighting).

**`agot_knight_relation_on_actions.txt`:**

- `on_death_relation_agot_squire`: When a knight dies, the squire either gets
  deathbed-knighted (if PTK >= 51 and age >= 14) or must find a new knight.
- `on_set_relation_agot_squire`: Adds `agot_has_squire_modifier` to the knight.
- `on_remove_relation_agot_squire`: Removes `agot_has_squire_modifier`.

**`agot_squire_on_actions.txt`:**

- `ongoing_squire_events`: Pool of 18 random squirehood events plus maintenance
  checks.

### Knight Tree System

The **Knight Tree** is a genealogy-style UI feature tracking who knighted whom.
It uses two story types stored on `title:c_ruins.holder`:

- `agot_knight_tree_structure`: The root story. Holds `knight_tree_founder`,
  `knight_tree_gui` (list), and `teacher_story_container` (list of teacher
  stories). Stored in global list `known_knight_trees`.
- `agot_knight_tree_teacher`: One per knight who has trained squires. Holds
  `this_teacher` and `student_container` (list of squires).

Key effects:

- `agot_add_to_knight_tree`: Called automatically when a character is knighted.
  Creates or extends tree structures. Lowborns are excluded unless they are
  Kingsguard.
- `agot_add_to_historical_knight_tree`: Same logic but for historical/bookmark
  setup.
- `agot_knight_tree_purge`: Removes trees irrelevant to the current player
  (keeps family-related and historical trees).

Each living character in a tree has `var:my_knight_tree` pointing to their tree
story for fast GUI lookup.

Script values in `00_agot_knight_tree_values.txt`:

- `knight_tree_count`: Total active trees globally.
- `knight_tree_teacher_count`: Total teacher-student pairs.
- `knight_tree_members_count` / `knight_tree_members_alive_count`: Members of a
  specific tree.
- `knight_trees_destroyed_count`: Running total of destroyed trees.

---

## Sub-Mod Recipes

### Recipe 1: Add a Custom Knighting Requirement

To require a specific trait (e.g., `brave`) before a character can be knighted,
override the trigger:

```pdx
# In your sub-mod: common/scripted_triggers/99_my_knighting_triggers.txt
agot_can_become_a_knight_trigger = {
    agot_has_traits_preventing_knighthood_trigger = no
    has_trait = brave  # NEW: Must be brave to earn knighthood
    OR = {
        is_male = yes
        AND = { is_male = no  has_trait = squire }
        AND = { is_male = no  faith = { has_doctrine = doctrine_gender_equal } }
        AND = { is_male = no  faith = { has_doctrine = doctrine_gender_female_dominated } }
    }
    NOT = { has_character_flag = former_acolyte }
    custom_tooltip = {
        text = agot_can_become_a_knight_trigger_age_tt
        OR = {
            age >= 16
            AND = { age < 16  age >= 12  prowess >= extremely_high_skill_rating }
        }
    }
    NOR = {
        custom_tooltip = {
            text = agot_knighthood_was_revoked_tt
            has_character_flag = cannot_be_knighted
        }
        has_trait = stripped_knight
    }
}
```

Because AGOT loads its triggers as `00_agot_knighting_triggers.txt`, a file
prefixed `99_` will overwrite the same-named trigger. Only the trigger contents
are replaced -- all effects and interactions that call it will pick up your new
version.

### Recipe 2: Knight Someone via Script (e.g., a Decision)

```pdx
# In common/decisions/my_knighting_decision.txt
my_knight_courtier_decision = {
    is_shown = {
        is_agot_knight_trigger = yes
        any_courtier = {
            agot_can_become_a_knight_trigger = yes
            NOT = { is_agot_knight_trigger = yes }
        }
    }
    effect = {
        random_courtier = {
            limit = {
                agot_can_become_a_knight_trigger = yes
                NOT = { is_agot_knight_trigger = yes }
            }
            weight = {
                base = 1
                modifier = { add = 10  has_trait = brave }
            }
            save_scope_as = my_new_knight
        }
        agot_become_a_knight_effect = {
            KNIGHT_MAKER = root
            KNIGHT_TO_BE = scope:my_new_knight
        }
    }
}
```

This uses the official AGOT effect, which handles: trait XP, memories, prestige,
piety, opinions, knight tree, family notifications, and lore-specific hooks
(Dayne/Targaryen). Always prefer calling `agot_become_a_knight_effect` over
manually setting trait XP.

### Recipe 3: Create a Squire Relationship via Script

```pdx
# Assign a squire to a knight programmatically
agot_set_squire_effect = {
    KNIGHT = scope:my_knight
    SQUIRE = scope:my_squire
}
```

This is the simplest squire-creation effect. It sets the relation, adds the
`squire` trait, creates the `story_agot_squire_ongoing` story, creates memories,
and handles court movement. If you need hook usage and stress (for
interactions), use `agot_offer_squire_interaction_effect` instead.

### Recipe 4: Add a Custom Ongoing Squire Event

Create a new event and add it to the on-action pool:

```pdx
# In events/my_squirehood_events.txt
namespace = my_squirehood

my_squirehood.0001 = {
    type = character_event
    title = my_squirehood.0001.t
    desc = my_squirehood.0001.desc
    theme = martial

    trigger = {
        available_for_squirehood_events = { NUM = my_0001 }
    }

    immediate = {
        add_character_flag = { flag = squirehood_ongoing_my_0001  months = 4 }
        random_relation = {
            type = agot_knight
            save_scope_as = my_knight
        }
    }

    option = {
        name = my_squirehood.0001.a
        agot_add_squire_trait_xp_effect = { MIN_VALUE = 3  MAX_VALUE = 5 }
    }
}
```

Then register it in an on-action override:

```pdx
# In common/on_action/agot_on_actions/agot_story_cycles/99_my_squire_on_actions.txt
ongoing_squire_events = {
    random_events = {
        200 = my_squirehood.0001
    }
}
```

CK3 merges on-action `random_events` blocks additively, so your event joins the
existing pool without overriding the base file.

### Recipe 5: Strip Knighthood via Script

```pdx
agot_strip_knighthood_as_punishment_effect = {
    STRIPPER = scope:actor
    KNIGHT = scope:recipient
}
```

This removes the knight/squire trait, adds `stripped_knight`, applies
prestige/piety loss, removes all squire relations, flags the character as
permanently unable to be re-knighted (`cannot_be_knighted`), and creates
memories.

---

## Pitfalls

### 1. Do NOT manually set trait XP to 100

Calling `add_trait_xp = { trait = squire track = knight value = 100 }` alone
skips: relation cleanup, story cycle termination, memory creation, opinions,
prestige, knight tree, and family notifications. Always use
`agot_become_a_knight_effect`.

### 2. The `squire` trait alone does not make a squire

A character needs both the `squire` trait AND an `agot_knight` relation for the
system to function. The story cycle, training events, and promotion checks all
require `agot_is_squire_with_knight` (which checks both). Use
`agot_set_squire_effect` or `agot_offer_squire_interaction_effect` to create
squires properly.

### 3. Overriding triggers vs. effects

AGOT scripted triggers in `00_agot_knighting_triggers.txt` can be overridden by
naming your file with a higher sort order (e.g., `99_`). However, effects in
`00_agot_knighthood_effects.txt` work the same way -- be careful not to
accidentally break the full knighting pipeline.

### 4. Knight Tree requires non-lowborn (or Kingsguard)

`agot_add_to_knight_tree` silently skips lowborn knights unless they have
`has_trait = kingsguard`. If your sub-mod creates lowborn knights and you want
them in the knight tree, you must override this trigger block.

### 5. The `story_agot_squire_ongoing` is single-instance

`agot_init_squire_story_cycle_effect` checks
`has_character_flag = had_ongoing_squire_story` before creating the story. A
character who was previously a squire, lost their knight, and becomes a squire
again will NOT get a new story cycle. The `had_ongoing_squire_story` flag is
only removed when the story ends on a living character.

### 6. Maximum 2 squires per knight

`agot_can_take_squire_trigger` enforces `num_of_relation_agot_squire < 2`. If
you want to allow more squires, override this trigger, but be aware the story
cycle training sim and events assume a single knight per squire.

### 7. Age windows matter

- Squire eligibility: age 9-21.
- Knighting: age 16+ (or 12-15 with extremely high prowess).
- Auto-cleanup: 15 years past age 22 without completing squirehood.

If your sub-mod adds characters at unusual ages, the squirehood system may
immediately try to clean them up.

### 8. Court movement side effects

`agot_move_knight_for_education_or_squiring_purposes` uses `visit_court_of` to
move characters between courts. This can conflict with guardianship, court
positions, and Kingsguard status. The effect has guards against these cases, but
custom court positions may not be checked.

### 9. Battlefield knighting fires on combat_side scope

`agot_knighthood.0600` uses `scope = combat_side`, not `character_event`. If you
want to add conditions to battlefield knighting, you must work within the combat
side scope (using `side_commander`, `any_side_knight`, etc.).

### 10. Faith doctrine is the master gate

Almost every AI weight and acceptance check includes
`has_doctrine_parameter = can_grant_knighthood`. If you create a custom faith
without this doctrine parameter, the knighthood system will be nearly inactive
for those characters. Add `can_grant_knighthood` to your faith's doctrines if
you want knighthood to function.
