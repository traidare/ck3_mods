# AGOT: Faceless Men & Secret Identity

## Overview

AGOT implements two distinct but related systems:

1. **Faceless Men** -- The assassin-for-hire system based on the House of Black
   and White. Characters can hire a Faceless Man to kill a target (via an
   interaction tied to a murder scheme), and Faceless Men followers of the
   Many-Faced God can change their own appearance by wearing faces from killed
   victims or a global "Hall of Faces."

2. **Secret Identity** -- A parallel system where characters (typically children
   of deposed rulers) are given fake parentage, relocated, and live under a
   false name. Over time, the story cycle decides whether they reveal
   themselves, start wars, or stay hidden forever.

These two systems share some vocabulary (e.g., "face," "identity") but operate
through completely separate scripted effects, story cycles, and event chains.

---

## Key Concepts

### Hall of Faces (`global_var:hall_of_faces`)

A global variable pointing to a title whose `title_province` stores a variable
list called `faces`. This list holds dead character references whose appearances
can be "worn." It is initialized by event `agot_faceless_decision.9000`, which
creates 20 random dead characters via template `agot_faceless_character` and
stores them as faces.

### Hiring a Faceless Man

The flow begins with the character interaction
`agot_send_for_faceless_interaction`. The actor must:

- Have an active murder scheme against the target (`scheme_type = murder`)
- Be able to afford at least one payment type (gold, child, artifact, or blood)
- Have intrigue > 19, or a spymaster with intrigue > 19

On acceptance, a `story_hire_faceless` story cycle is created, which triggers
the pricing event after 10-20 days.

### Face-Wearing (for Faceless Men characters)

Characters with the `can_take_new_face` doctrine parameter can use two
decisions:

- `agot_take_new_face_decision` -- Change appearance only (same character)
- `agot_faceless_new_adventure_decision` -- Change identity entirely (creates a
  new character, transfers player control, kills the old one). Requires Roads to
  Power DLC.

Both are blocked by `has_character_flag = last_face` (the character fled the
order), `has_secret_identity`, and a 5-year cooldown (`taken_face_recently`).

### Secret Identity Lifecycle

1. **Creation**: `agot_start_secret_identity_effect` is called on a character
   (typically a child). It creates a "dupe" dead character with the original
   identity, creates fake parents, strips claims (saving them as variables),
   clears all relations, and gives the character `has_secret_identity` +
   `generic_secret_identity` flags and the `secret_agot_identity` secret type.

2. **Living in hiding**: The `secret_identity_story` story cycle runs monthly,
   counting down `secret_adventure_chance` from 50 to 0. When it reaches 0, the
   AI picks from: keep wandering, reveal identity, reveal + declare war, become
   adventurer under cover, or abandon identity permanently.

3. **Reveal**: `agot_end_secret_identity_effect` restores the original name,
   parents, house, and claims. It notifies relevant rulers via
   `agot_secret_events.2009`.

---

## AGOT Scripted API

### Scripted Effects (Secret Identity)

**File:** `common/scripted_effects/00_agot_secret_identity_effects.txt`

| Effect                                        | Scope                               | Purpose                                                                                                                                            |
| --------------------------------------------- | ----------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| `agot_start_secret_identity_effect`           | character (as `scope:secret_child`) | Full identity swap: creates dupe, fake parents, strips claims, clears relations, adds `has_secret_identity` flag and `secret_agot_identity` secret |
| `agot_end_secret_identity_effect`             | character (as `scope:secret_child`) | Restores original name, parents, house, claims; ends `secret_identity_story`; removes identity flags                                               |
| `agot_swap_secret_child_bodies`               | character                           | Swaps identity data between `scope:secret_child` and `scope:dupe_char`                                                                             |
| `agot_move_secret_child`                      | character                           | Relocates the secret child to a vassal of the claim holder (hostile vassal preferred)                                                              |
| `agot_get_secret_claims_generic_effect`       | character                           | Saves claim variables (`secret_claim_capital`, `secret_claim_capital_duchy`, etc.) based on house head's titles                                    |
| `agot_get_secret_claims_on_title_gain_effect` | character                           | Saves claim variables based on `scope:title` tier when identity is created on title loss                                                           |
| `agot_secret_identity_adventure_effect`       | character                           | AI decision fork: stay hidden, reveal, war, or become adventurer                                                                                   |
| `agot_secret_child_start_war_effect`          | character                           | Starts a claim war and spawns armies scaled to education tier                                                                                      |
| `agot_clear_all_relations`                    | character                           | Strips guardian, knight, friend, lover, rival, crush, victim, bully relations plus betrothal/marriage                                              |
| `agot_events_after_identity_reveal`           | character                           | Sends `agot_secret_events.2009` notification to relevant rulers                                                                                    |
| `agot_create_secret_character_army_effect`    | character                           | Spawns scaled MaA based on education tier and war target's rank                                                                                    |

### Scripted Effects (Faceless Men)

**File:** `common/scripted_effects/00_agot_effects.txt`

| Effect                              | Parameters             | Purpose                                                                                                                                                                  |
| ----------------------------------- | ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `agot_faceless_take_face`           | `NEW_FACE`, `OLD_FACE` | Copies appearance from a dead character onto current character. Creates/updates `story_wear_face`. Returns old face to Hall. 5-year cooldown flag `taken_face_recently`. |
| `agot_faceless_take_face_adventure` | `NEW_FACE`, `OLD_FACE` | Creates an entirely new character with the new face's appearance and old character's traits. Transfers gold, artifacts, player control. Kills old character.             |
| `agot_faceless_use_face_random`     | (none)                 | Spawns a temporary Faceless Man NPC using a random face from the Hall. Used to represent the assassin in events. Faith is `fc_pan_faceless`.                             |

### Scripted Effects (Faceless Interaction Events)

**File:**
`events/agot_interaction_events/agot_send_for_faceless_interaction_events.txt`

These are defined inline as `scripted_effect` blocks within the event file:

| Effect                          | Purpose                                                                                                                                 |
| ------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| `agot_faceless_assess_weight`   | Calculates `var:price_significance` (0-100+) based on target's rank, wars, feuds, inheritance position, dragon riding, intrigue/prowess |
| `agot_faceless_determine_price` | Sets `var:faceless_gold_price` to a flag tier (`no`/`extreme`/`high`/`low`/`minimal`) and determines alternative payments               |
| `agot_faceless_get_kill_price`  | Wrapper: calls assess_weight then determine_price. Parameters: `$PAYER$`, `$TARGET$`                                                    |

### Scripted Triggers

**File:** `common/scripted_triggers/00_agot_faceless_triggers.txt`

| Trigger                                   | Purpose                                                                                                                                      |
| ----------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| `agot_can_afford_faceless_price`          | OR of all four price checks below                                                                                                            |
| `agot_can_afford_faceless_gold_price`     | `gold > 300` and not already paid gold (`faceless_payed_gold_price` flag)                                                                    |
| `agot_can_afford_faceless_child_price`    | Has 2-3 children, at least one age <= 10 with no bad genetic traits and intrigue/martial >= 5                                                |
| `agot_can_afford_faceless_artifact_price` | Owns a dragon egg, Valyrian steel weapon, or dragon horn                                                                                     |
| `agot_can_afford_faceless_blood_price`    | Age < 50, no `incapable`/`depressed` traits, no bad genetic traits. Only offered when all other prices exhausted or gold price is `extreme`. |

**File:** `common/scripted_triggers/00_agot_secret_type_triggers.txt`

| Trigger                                    | Purpose                                                   |
| ------------------------------------------ | --------------------------------------------------------- |
| `secret_agot_identity_is_valid_trigger`    | Valid if owner `has_character_flag = has_secret_identity` |
| `secret_agot_identity_is_shunned_trigger`  | Always no                                                 |
| `secret_agot_identity_is_criminal_trigger` | Always no                                                 |

---

## Story Cycles

### `story_hire_faceless`

**File:** `common/story_cycles/agot_story_cycle_faceless.txt`

Drives the Faceless Man assassination contract.

```pdx
story_hire_faceless = {
    on_setup = {
        story_owner = {
            if = {
                limit = { has_variable = faceless_victim }
                scope:story = {
                    set_variable = {
                        name = faceless_victim
                        value = prev.var:faceless_victim
                    }
                }
                remove_variable = faceless_victim
                trigger_event = {
                    id = agot_faceless_interaction.0001
                    days = { 10 20 }
                }
            }
            else = {
                scope:story = { end_story = yes }
            }
        }
    }

    effect_group = {
        days = 30
        triggered_effect = {
            trigger = {
                var:faceless_victim ?= { is_alive = no }
            }
            effect = {
                story_owner = {
                    trigger_event = agot_faceless_interaction.0002
                }
            }
        }
    }
}
```

Key behavior:

- On setup, transfers `faceless_victim` variable from owner to story, then fires
  `agot_faceless_interaction.0001` (the pricing event) after 10-20 days.
- Every 30 days, checks if the victim is dead. If so, fires the "deed is done"
  event (`agot_faceless_interaction.0002`).

### `story_wear_face`

**File:** `common/story_cycles/agot_story_cycle_faceless.txt`

Tracks which face a Faceless Man character is currently wearing.

```pdx
story_wear_face = {
    on_setup = {
        story_owner = {
            # Transfers variables: new_face, old_face, faces_worn, original_char
        }
    }

    on_end = {
        # Returns current face to hall_of_faces (if different from old_face)
        if = {
            limit = {
                scope:story = {
                    has_variable = new_face
                    trigger_if = {
                        limit = { has_variable = old_face }
                        NOT = { var:old_face = var:new_face }
                    }
                }
            }
            global_var:hall_of_faces = {
                title_province = {
                    add_to_variable_list = {
                        name = faces
                        target = scope:story.var:new_face
                    }
                }
            }
        }
    }
}
```

Key variables stored on the story:

- `var:new_face` -- the dead character whose appearance is being worn
- `var:old_face` -- the original appearance (dummy character storing genetics)
- `var:faces_worn` -- counter incremented each face change
- `var:original_char` -- flag indicating the wearer is still the original
  character (not yet "adventured")

### `secret_identity_story`

**File:** `common/story_cycles/agot_story_cycle_secret_identity.txt`

Drives the secret identity lifecycle for hidden characters.

```pdx
secret_identity_story = {
    on_setup = {
        story_owner = { add_character_flag = secret_adventure_ongoing }
    }

    # Daily: end story if character lost generic_secret_identity or died
    effect_group = {
        days = 1
        triggered_effect = {
            trigger = {
                story_owner = {
                    OR = {
                        NOT = { has_character_flag = generic_secret_identity }
                        NOT = { is_alive = yes }
                        NOT = { agot_can_be_ruler = yes }
                    }
                }
            }
            effect = { scope:story = { end_story = yes } }
        }
    }

    # Monthly: count down secret_adventure_chance from 50
    effect_group = {
        months = 1
        # Randomly subtracts 1-3 (or 50 on rare occasion) per month
        # When <= 0, fires agot_secret_identity_adventure_effect
    }

    # Yearly: when child becomes adult, reset the adventure timer
    effect_group = {
        years = 1
        # Sets secret_adventure_chance = 50 when newly adult
    }
}
```

Average time to trigger: approximately 2.5 years after reaching adulthood.

---

## Interactions & Schemes

### `agot_send_for_faceless_interaction`

**File:** `common/character_interactions/00_agot_religious_interactions.txt`

```pdx
agot_send_for_faceless_interaction = {
    category = interaction_category_hostile
    cooldown = { years = 10 }

    is_shown = {
        exists = global_var:hall_of_faces
        scope:actor = {
            is_human = yes
            NOT = { any_owned_story = { story_type = story_hire_faceless } }
            any_scheme = {
                scheme_type = murder
                scheme_target_character = scope:recipient
            }
        }
    }

    is_valid = {
        scope:actor = {
            agot_can_afford_faceless_price = yes
            custom_tooltip = {
                text = required_intrigue_faceless.tt
                OR = {
                    any_councillor = {
                        has_council_position = councillor_spymaster
                        intrigue > 19
                    }
                    intrigue > 19
                }
            }
        }
    }

    on_accept = {
        scope:actor = {
            set_variable = { name = faceless_victim value = scope:recipient }
            create_story = { type = story_hire_faceless }
        }
    }

    auto_accept = yes
    ai_frequency = 12
}
```

**Requirements summary:**

- Player-only (is_human = yes)
- Must have active murder scheme against target
- No existing `story_hire_faceless`
- `global_var:hall_of_faces` must exist
- Gold > 300 OR eligible child OR Valyrian artifact OR blood price eligible
- Intrigue > 19 (self or spymaster)
- 10-year cooldown

No faceless-specific schemes exist. The system piggybacks on the vanilla murder
scheme, replacing it with the Faceless Man kill chain.

---

## Events

### Faceless Man Assassination Chain

**File:**
`events/agot_interaction_events/agot_send_for_faceless_interaction_events.txt`

| Event ID                         | Type            | Purpose                                                                                                                                                                          |
| -------------------------------- | --------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `agot_faceless_interaction.0001` | character_event | **Pricing event**: presents payment options (gold tiers, child, artifact, blood price, cancel). Gold tiers: minimal=300, low=900, high=1500, extreme=3000.                       |
| `agot_faceless_interaction.0002` | character_event | **Deed is done**: notifies the hirer. If blood price was chosen, the hirer dies. Various murder descriptions (oysters, furniture, horse, slip, fall, dog).                       |
| `agot_faceless_interaction.0003` | hidden          | **Dispatch**: ends the murder scheme, randomly picks one of 6 kill scenarios.                                                                                                    |
| `agot_faceless_interaction.0004` | character_event | Kill method: poisoned oysters (`death_oyster`). Coastal locations only.                                                                                                          |
| `agot_faceless_interaction.0005` | character_event | Kill method: falling crate (`death_accident`). Landed characters only.                                                                                                           |
| `agot_faceless_interaction.0006` | character_event | Kill method: kicked by horse (`death_accident`). Adults only.                                                                                                                    |
| `agot_faceless_interaction.0007` | character_event | Kill method: fatal slip (`death_accident`). Adults only.                                                                                                                         |
| `agot_faceless_interaction.0008` | character_event | Kill method: pushed from walls (`death_fall`).                                                                                                                                   |
| `agot_faceless_interaction.0009` | character_event | Kill method: mauled by dog (`death_dog_attack`).                                                                                                                                 |
| `agot_faceless_interaction.9001` | hidden          | **Fakeout trigger**: fires one of the kill events without `scope:murderer`, making them harmless near-miss encounters. One-time per character (`has_had_faceless_fakeout` flag). |

Each kill event (0004-0009) has dual paths:

- If `scope:murderer` exists: the victim dies and the hirer receives
  `agot_faceless_interaction.0002`.
- If `scope:murderer` does not exist: it is a "fakeout" -- an atmospheric false
  alarm event.

### Faceless Decision Events (Face-Wearing)

**File:** `events/agot_decisions_events/agot_faceless_decisions_events.txt`

| Event ID                      | Type               | Purpose                                                                                                                                                                                         |
| ----------------------------- | ------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `agot_faceless_decision.0001` | character_event    | Menu: choose from killed victims' faces or Hall of Faces                                                                                                                                        |
| `agot_faceless_decision.0002` | character_event    | Browse killed victims (uses widget `agot_character_selection_three_options`)                                                                                                                    |
| `agot_faceless_decision.0003` | character_event    | Browse Hall of Faces (shows up to 5 random faces, plus a "random unknown" option)                                                                                                               |
| `agot_faceless_decision.0004` | character_event    | Confirm selection. Two paths: `choosing_character` calls `agot_faceless_take_face_adventure`; `choosing_face` calls `agot_faceless_take_face`.                                                  |
| `agot_faceless_decision.0005` | character_event    | **Identity crisis**: after wearing too many faces (>5), a Faceless Man may come to reclaim your face. Options: die, or flee as a landless adventurer (losing Hall access via `last_face` flag). |
| `agot_faceless_decision.0010` | hidden             | **Sanity check**: after each face change, rolls against `faces_worn` count. If >5, increasing chance of triggering 0005.                                                                        |
| `agot_faceless_decision.9000` | scope=none, hidden | **Hall initialization**: creates 20 random dead characters as starting faces.                                                                                                                   |
| `agot_faceless_decision.9001` | scope=none, hidden | Makes all faces in the Hall unprunable.                                                                                                                                                         |

### Price Significance Breakdown

The `agot_faceless_assess_weight` effect calculates `var:price_significance` by
summing factors:

| Factor                                     | Points              |
| ------------------------------------------ | ------------------- |
| Payer is drunkard                          | +5                  |
| At war (primary belligerent)               | +25                 |
| At war (secondary)                         | +10                 |
| House feud with target                     | +40                 |
| Rival of target                            | +10                 |
| Nemesis of target                          | +20                 |
| First in succession                        | +30                 |
| Second in succession                       | +20                 |
| Third+ in succession                       | +10                 |
| Target is Hegemon                          | +100                |
| Target is Emperor                          | +75                 |
| Target is King                             | +50                 |
| Target is Duke                             | +25                 |
| Target is Count                            | +10                 |
| Target's spouse is ruler                   | +5 to +80 (by tier) |
| Target's close family is ruler             | +5 to +100          |
| Target is your liege                       | +20                 |
| Target rides a dragon                      | +25                 |
| Target has intrigue >= 20 or prowess >= 30 | +20                 |
| Target is incapable                        | -10                 |

Gold price mapping:

- `>= 100` -> `flag:no` (refuses gold, artifact/child/blood only)
- `>= 75` -> `flag:extreme` (3000 gold)
- `>= 50` -> `flag:high` (1500 gold)
- `>= 25` -> `flag:low` (900 gold)
- `< 25` -> `flag:minimal` (300 gold)

---

## Sub-Mod Recipes

### Recipe 1: Add a New Faceless Kill Method

Add a new random entry to event `agot_faceless_interaction.0003` and create a
matching event:

```pdx
# In your events file
namespace = my_mod_faceless

my_mod_faceless.0001 = {
    type = character_event
    theme = death
    override_background = { reference = gallows }
    title = my_mod_faceless.0001.t
    desc = {
        desc = my_mod_faceless.0001.desc
        first_valid = {
            triggered_desc = {
                trigger = { exists = scope:murderer }
                desc = my_mod_faceless.0001.desc_faceless
            }
            desc = my_mod_faceless.0001.desc_fakeout
        }
    }

    left_portrait = { character = root }

    immediate = {
        scope:murderer ?= {
            random_owned_story = {
                limit = { story_type = story_hire_faceless }
                set_variable = { name = murder_style value = flag:my_poison }
            }
        }
    }

    option = {
        trigger = { exists = scope:murderer }
        name = my_mod_faceless.0001.a
        death = { death_reason = death_poison }
    }

    option = {
        trigger = { NOT = { exists = scope:murderer } }
        name = my_mod_faceless.0001.a_fakeout
    }

    after = {
        scope:murderer ?= {
            trigger_event = agot_faceless_interaction.0002
        }
    }
}
```

Then override `agot_faceless_interaction.0003` to include your event in the
`random_list`.

### Recipe 2: Grant a Secret Identity to Any Character via Decision

```pdx
my_mod_give_secret_identity_decision = {
    picture = { reference = "gfx/interface/illustrations/decisions/decision_misc.dds" }

    is_shown = {
        is_landed = yes
        any_courtier = {
            is_adult = no
            NOT = { has_character_flag = has_secret_identity }
        }
    }

    effect = {
        # The target must be saved as scope:secret_child before calling the effect
        random_courtier = {
            limit = {
                is_adult = no
                NOT = { has_character_flag = has_secret_identity }
            }
            save_scope_as = secret_child
            agot_start_secret_identity_effect = yes
        }
    }
}
```

Important: `agot_start_secret_identity_effect` expects `scope:secret_child` to
be set. It optionally reads `scope:king_executioner` for an execution death
reason on the dupe.

### Recipe 3: Force-Reveal a Secret Identity

```pdx
# In an event or scripted effect:
scope:target_character = {
    save_scope_as = secret_child
    if = {
        limit = { has_character_flag = has_secret_identity }
        agot_end_secret_identity_effect = yes
    }
}
```

### Recipe 4: Add a New Faceless Price Type

Override `agot_can_afford_faceless_price` to add your trigger, then add a
matching option in `agot_faceless_interaction.0001`. The existing pattern:

```pdx
# In scripted_triggers, override:
agot_can_afford_faceless_price = {
    OR = {
        agot_can_afford_faceless_gold_price = yes
        agot_can_afford_faceless_child_price = yes
        agot_can_afford_faceless_artifact_price = yes
        agot_can_afford_faceless_blood_price = yes
        my_mod_can_afford_faceless_custom_price = yes  # Your addition
    }
}
```

---

## Pitfalls

1. **`scope:secret_child` is mandatory.** Both
   `agot_start_secret_identity_effect` and `agot_end_secret_identity_effect`
   operate on `scope:secret_child`. Forgetting to `save_scope_as = secret_child`
   before calling them will cause silent failures or crashes.

2. **The dupe character must not be pruned.** The secret identity system stores
   the original identity in `var:secret_identity_character`, a dead character
   reference. If CK3 prunes that character, the identity reveal breaks. AGOT
   uses `agot_make_unpruneable` to prevent this, and you should do the same for
   any characters you store as face/identity references.

3. **`global_var:hall_of_faces` must exist.** All Faceless Men interactions and
   decisions check `exists = global_var:hall_of_faces`. If your sub-mod runs
   before AGOT's initialization event `agot_faceless_decision.9000`, the Hall
   will not exist yet. Guard with the same check.

4. **Face-wearing has a sanity limit.** After wearing more than 5 faces
   (`var:faces_worn > 5`), each additional face change has an increasing chance
   to trigger `agot_faceless_decision.0005`, which can kill the character or
   force them to flee. Do not bypass this counter without understanding the
   consequences.

5. **Murder scheme is required for hiring.** The
   `agot_send_for_faceless_interaction` is only shown when the actor has an
   active murder scheme against the recipient. The Faceless Man kill chain ends
   the scheme (`end_scheme = yes`) before dispatching its own kill events. Do
   not try to keep the scheme alive alongside the Faceless contract.

6. **`has_character_flag = last_face` is permanent.** If a character flees the
   Many-Faced God in event 0005, the `last_face` flag is set without an expiry.
   This permanently blocks both face-changing decisions. There is no built-in
   way to remove it.

7. **Secret identity claims are stored per tier.** The variables
   `secret_claim_capital`, `secret_claim_capital_duchy`,
   `secret_claim_capital_kingdom`, `secret_claim_capital_empire`, and
   `secret_claim_capital_hegemony` are set independently. If you manually
   grant/remove claims, you must also update these variables or the war/reveal
   logic will break.

8. **Blood price kills the hirer.** If the player chooses the blood price option
   in `agot_faceless_interaction.0001`, their character dies in
   `agot_faceless_interaction.0002` after the target is killed. The flag
   `faceless_chose_blood_price` controls this. AI will never choose blood price
   (`ai_chance = { base = 0 }`).

9. **`choosing_face` vs `choosing_character` flags.** The face decision uses
   `choosing_face` (appearance change only), while the adventure decision uses
   `choosing_character` (full identity swap creating a new character). These
   flags gate which confirmation option appears in
   `agot_faceless_decision.0004`. Setting the wrong one leads to calling the
   wrong effect.

10. **10-year interaction cooldown persists on cancel.** If a human player
    cancels the faceless interaction, the cooldown is removed
    (`remove_interaction_cooldown`). But for AI, it is not removed -- this is
    intentional to prevent AI spam. If you allow AI to use the interaction, be
    aware of this asymmetry.
