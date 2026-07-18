# AGOT: Kingsguard

## Overview

The AGOT Kingsguard system models the seven-member royal bodyguard of the Iron
Throne. It is built entirely on top of vanilla CK3's **council position**
system: the Lord Commander occupies the `kingsguard_lord_commander` council
slot, while the remaining six brothers fill `kingsguard_1` through
`kingsguard_6`. Members receive the `kingsguard` trait, are forced into
celibacy, break betrothals, and cannot leave court. A parallel **White Book**
subsystem records every appointment, promotion, and departure as a browsable
in-game chronicle.

Key source files (all paths relative to the AGOT mod root):

| Area               | File                                                                |
| ------------------ | ------------------------------------------------------------------- |
| Core effects       | `common/scripted_effects/00_agot_kingsguard_effects.txt`            |
| White Book effects | `common/scripted_effects/00_agot_kingsguard_white_book_effects.txt` |
| Triggers           | `common/scripted_triggers/00_agot_kingsguard_triggers.txt`          |
| Council triggers   | `common/scripted_triggers/00_agot_councillor_triggers.txt`          |
| Interactions       | `common/character_interactions/00_agot_kingsguard_interactions.txt` |
| Decisions          | `common/decisions/agot_decisions/00_agot_kingsguard_decisions.txt`  |
| Events             | `events/agot_events/agot_kingsguard_events.txt`                     |
| White Book events  | `events/agot_events/agot_kingsguard_white_book_events.txt`          |

---

## Key Concepts

### Appointment

A character joins the Kingsguard through `agot_join_kingsguard_effect`. This
effect:

1. Adds `trait = kingsguard` and `character_flag = blocked_from_leaving`.
2. Removes the `refusing_marriage` trait and `training_for_kingsguard` modifier
   if present.
3. Creates a White Book page entry via
   `agot_kingsguard_create_dynamic_white_book_page_join`.
4. Moves the character to the king's court (`add_courtier ?= scope:kingsguard`).
5. Assigns the character to the first free council slot (`kingsguard_1` through
   `kingsguard_6`), and stores a matching variable on the king's
   `primary_title`.

Parameters:

```pdx
agot_join_kingsguard_effect = { KINGSGUARD = <char_scope> KING = <char_scope> }
```

When the `on_get` callback fires (via the council position definition),
`agot_on_get_kingsguard` also breaks any existing betrothal and adds
`blocked_from_leaving`.

### Dismissal / Removal

`agot_remove_kingsguard_effect` handles all removal paths (death, dismissal,
fleeing):

1. If the removed member is Lord Commander, calls `white_book_transfer` to
   return the White Book artifact to the king.
2. Unless the member is dead (`scope:dead_kingsguard` exists), removes the
   `kingsguard` trait, adds `agot_former_kingsguard` modifier, destroys
   kingsguard armor artifacts, and fires the councillor.
3. Cleans up the title variable (`kingsguard_lord_commander`,
   `kingsguard_1`...`kingsguard_6`) on `title:h_the_iron_throne`.
4. Triggers White Book update event `agot_kingsguard_white_book.1000`.
5. For the king: if the removed member was Lord Commander, fires either
   `agot_kingsguard.1010` (player) or `agot_kingsguard.9001` (AI) to prompt a
   new LC appointment. Then fires `agot_kingsguard.1001` (player) or
   `agot_kingsguard.9002` (AI) to replace the vacant slot.

```pdx
agot_remove_kingsguard_effect = { KINGSGUARD = <char_scope> }
```

### Lord Commander

The Lord Commander holds `title:d_kingsguard` and occupies the
`kingsguard_lord_commander` council position. Appointment is handled by
`agot_assign_lord_commander_effect`:

1. Creates a `agot_kingsguard_lord_commander_memory` memory on the commander.
2. Updates the White Book page to record the LC promotion.
3. Recreates the White Book artifact if the commander does not already own one.
4. Adds `character_flag = lord_commander`.
5. Removes the commander from their ordinary `kingsguard_N` slot and variable;
   sets `kingsguard_lord_commander` variable on the king's primary title.
6. Transfers the White Book artifact from the king to the commander.
7. Grants `title:d_kingsguard` via `create_title_and_vassal_change` +
   `change_title_holder`, then swears fealty to the king.
8. Copies title history from `title:d_dummy_kingsguard` for CoA preservation.

```pdx
agot_assign_lord_commander_effect = { COMMANDER = <char_scope> KING = <char_scope> }
```

### The White Book

The White Book is an in-game artifact (`has_variable = white_book`) held by the
Lord Commander. Each member's page is actually a **dead character** (created
from `agot_hedgeknight_character` template, immediately killed via
`death_vanished`) whose `first_name` localization key stores the page text.
Pages are linked to members through province variables (`kingsguard_member`,
`kingsguard_white_book_page`).

A global variable list `kingsguard_white_book` tracks every member who has ever
served. The decision `agot_view_white_book` lets the player browse it.

The White Book is disabled in multiplayer games:

```pdx
agot_is_white_book_enabled = {
    NOR = {
        has_multiple_players = yes
        has_game_rule = agot_multiplayer_safe_on
    }
}
```

### Bodyguard Task

Kingsguard members can be assigned to guard royal family members through the
councillor task system. The bodyguard task uses the `bodyguard` relation and
adds the `kingsguard_bodyguard` modifier to the guarded character. Target must
share the king's dynasty or be married into it, and must not already have a
bodyguard (`num_of_relation_bodyguard = 0`).

---

## AGOT Scripted API

### Scripted Effects

| Effect                                  | Parameters                              | Purpose                                                                               |
| --------------------------------------- | --------------------------------------- | ------------------------------------------------------------------------------------- |
| `agot_join_kingsguard_effect`           | `KINGSGUARD`, `KING`                    | Full appointment: trait, court move, council slot, White Book                         |
| `agot_assign_lord_commander_effect`     | `COMMANDER`, `KING`                     | Promote existing KG to Lord Commander                                                 |
| `agot_remove_kingsguard_effect`         | `KINGSGUARD`                            | Full removal: trait, artifacts, council, variables, replacement events                |
| `agot_kingsguard_fled_effect`           | (uses `scope:actor`, `scope:recipient`) | Oath-breaking escape with prowess duel; may die, flee to Essos, or join Night's Watch |
| `agot_kingsguard_destroy_artifacts`     | (none, operates on `this`)              | Destroys any artifact with `kingsguard_armor` variable                                |
| `agot_end_kingsguard_effect`            | (none)                                  | Dissolves the entire Kingsguard; fires all members, removes traits/artifacts          |
| `agot_on_get_kingsguard`                | (none, council callback)                | Breaks betrothals, adds `blocked_from_leaving`                                        |
| `agot_on_get_kingsguard_lord_commander` | (none, council callback)                | Same as above plus `lord_commander` flag and slot variable cleanup                    |
| `agot_on_fired_from_kingsguard`         | (none, council callback)                | Removes `blocked_from_leaving`                                                        |
| `agot_on_start_kingsguard_bodyguard`    | (none, task callback)                   | Fires `agot_kingsguard.2001` on liege to pick bodyguard target                        |
| `agot_start_bodyguarding`               | `TARGET`                                | Sets `bodyguard` relation and starts councillor travel                                |
| `agot_on_cancel_kingsguard_bodyguard`   | (none, task callback)                   | Clears bodyguard relation and travel                                                  |
| `white_book_transfer`                   | (none, operates on `this`)              | Transfers White Book artifact back to `top_liege`                                     |

### White Book Effects

| Effect                                                              | Parameters           | Purpose                                                     |
| ------------------------------------------------------------------- | -------------------- | ----------------------------------------------------------- |
| `agot_kingsguard_get_page_effect`                                   | `KINGSGUARD`         | Retrieves the White Book page scope for a member            |
| `agot_kingsguard_create_historical_white_book_page`                 | `KINGSGUARD`         | Creates a static historical page (used at game start)       |
| `agot_kingsguard_create_dynamic_white_book_page_join`               | `KINGSGUARD`, `KING` | Creates a page when a character joins mid-game              |
| `agot_kingsguard_update_white_book_page_lc`                         | `KINGSGUARD`, `KING` | Updates page when promoted to Lord Commander                |
| `agot_kingsguard_update_white_book_page_sent_to_nightswatch_update` | `KINGSGUARD`, `KING` | Updates page when sent to the Night's Watch                 |
| `agot_kingsguard_update_white_book_page_removed_update`             | `KINGSGUARD`, `KING` | Updates page when dismissed                                 |
| `agot_kingsguard_update_white_book_page_died_update`                | `KINGSGUARD`, `KING` | Updates page when the member dies                           |
| `agot_kingsguard_init_white_book`                                   | (none)               | Initializes all historical White Book entries at game start |

### Scripted Triggers

| Trigger                                      | Scope     | Purpose                                                                                                                                                                                    |
| -------------------------------------------- | --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `title_has_kingsguard_trigger`               | title     | `tier >= tier_empire` AND `has_variable = kingsguard`                                                                                                                                      |
| `ruler_has_kingsguard_trigger`               | character | Any held title passes `title_has_kingsguard_trigger`                                                                                                                                       |
| `ruler_primary_title_has_kingsguard_trigger` | character | Primary title passes `title_has_kingsguard_trigger`                                                                                                                                        |
| `can_be_kingsguard_trigger`                  | character | Full eligibility: not ruler (unless already LC), unmarried, capable adult, human, male, can be knight, no conflicting traits (nightswatch, dragon, order_member, devoted, septon, maester) |
| `valid_kingsguard_gender_trigger`            | character | `is_male = yes` (override this for female Kingsguard)                                                                                                                                      |
| `highborn_kingsguard_candidate`              | character | Highborn, not heir, not betrothed, has `education_martial_prowess`                                                                                                                         |
| `can_have_kingsguard`                        | character | `ruler_primary_title_has_kingsguard_trigger = yes`                                                                                                                                         |
| `is_kingsguard_trigger`                      | character | Has any KG council position (1-6, not LC)                                                                                                                                                  |
| `valid_kingsguard_bodyguard_target`          | character | Shares dynasty with liege or married into it, has no existing bodyguard                                                                                                                    |
| `valid_kingsguard_bodyguard_court`           | character | Target court contains a valid bodyguard target                                                                                                                                             |
| `agot_is_white_book_enabled`                 | (any)     | Not multiplayer and not multiplayer-safe game rule                                                                                                                                         |

---

## Interactions & Decisions

### `invite_to_kingsguard_interaction`

Category: `interaction_category_diplomacy`. Sent by the king to a courtier/guest
in the realm.

**is_shown conditions:**

- Actor holds a kingsguard-eligible primary title.
- Actor has at least one open `kingsguard_N` slot (checks
  `var:kingsguard_1`...`var:kingsguard_6`).
- Recipient is human, male, has `kingsguard` trait = no, not a maester, under
  actor's top liege.

**is_valid conditions:**

- Recipient is unlanded, unmarried, capable adult, can be a knight, no
  clergy/order/NW traits.
- No `kingsguard_position_rejected` flag (cannot re-invite someone who
  declined).

**Auto-accept:** Only if recipient has `training_for_kingsguard` modifier.

**AI acceptance** (base 50): boosted by `training_for_kingsguard` (+100),
positive opinion, lowborn (+25), honor, zeal, boldness. Penalized by betrothal
(-50), wrong faith (-100), being heir (-100/-35), greed, lustful/reveler/seducer
traits (-50).

**On accept:** Fires `agot_kingsguard.1005` (letter event) on the king, leading
to `agot_kingsguard.1006` (the actual appointment chain).

**On decline:** Sets `kingsguard_position_rejected` flag. Fires
`agot_kingsguard.1007`.

### `appoint_lord_commander_interaction`

Category: `interaction_category_diplomacy`. Sent by the king to an existing
Kingsguard member.

**is_shown conditions:**

- Actor has no current Lord Commander
  (`NOT { exists = cp:kingsguard_lord_commander }`).
- Recipient has `kingsguard` trait and is under actor's top liege.

**is_valid conditions:**

- Recipient holds one of `kingsguard_1` through `kingsguard_6`.

**Auto-accept:** Always.

**On accept:** Calls `agot_assign_lord_commander_effect`.

### `agot_view_white_book` (Decision)

Shown only to the Iron Throne holder or the White Book artifact holder when
White Book is enabled. AI never takes this decision. Fires
`agot_kingsguard_white_book.0001` which opens the browsable member list using
`kingsguard_white_book` global variable list.

---

## Events

### Namespace `agot_kingsguard` -- Appointment & Maintenance (1000-1999)

| Event ID | Type      | Purpose                                                                                  |
| -------- | --------- | ---------------------------------------------------------------------------------------- |
| `1000`   | hidden    | On-death maintenance; fires `agot_remove_kingsguard_effect` with `scope:dead_kingsguard` |
| `1001`   | character | Player notification of KG death/removal; offers 3 replacement strategies                 |
| `1002`   | character | "Greatest Knights": presents top-prowess candidates from realm                           |
| `1003`   | character | "Powerful Lords' Sons": presents highborn candidates who auto-accept                     |
| `1004`   | character | Candidate acceptance interaction; determines if the chosen candidate joins               |
| `1005`   | letter    | Acceptance letter from candidate to king                                                 |
| `1006`   | character | Actually performs the appointment (recurring for multi-slot fills)                       |
| `1007`   | letter    | Rejection letter from candidate                                                          |
| `1008`   | character | Bestowing ceremony event                                                                 |
| `1009`   | character | Relatives' reaction to the appointment                                                   |
| `1010`   | character | Lord Commander death/removal (player version); pick new LC                               |
| `1011`   | character | Lord Commander succession step 2                                                         |
| `1012`   | hidden    | New KG setup: memory, prestige, knighthood, celibacy                                     |
| `1013`   | hidden    | On title gain: remove `training_for_kingsguard` and `refusing_marriage`                  |
| `1014`   | character | Additional appointment logic                                                             |

### Namespace `agot_kingsguard` -- Councillor & Chain Events (2000-2999)

| Event ID | Type      | Purpose                                                  |
| -------- | --------- | -------------------------------------------------------- |
| `2001`   | character | Bodyguard task: pick target from king's family           |
| `2002`   | character | Kingsguard imprisonment attempt; Barristan-style fleeing |
| `2003`   | character | Fleeing KG's relative helps them escape                  |
| `2004`   | character | Flee to Essos (KG edition)                               |

### Namespace `agot_kingsguard` -- Flavour Events (3000-3999)

| Event ID | Type      | Purpose                                                     |
| -------- | --------- | ----------------------------------------------------------- |
| `3001`   | character | Child wishes to join the Kingsguard                         |
| `3002`   | character | Honorable Kingsguard gains the `gallant` trait              |
| `3003`   | character | Kingsguard caught in an affair (Lucamore the Lusty)         |
| `3004`   | character | "Make way for the Kingsguard!" -- street encounter          |
| `3005`   | character | Powerful foreign warrior offers service (Sandoq the Shadow) |
| `3017`   | character | Kingsguard found dead outside a brothel (Owen Bush)         |

### Namespace `agot_kingsguard` -- AI Maintenance (9000+)

| Event ID | Type   | Purpose                                                                                                      |
| -------- | ------ | ------------------------------------------------------------------------------------------------------------ |
| `9001`   | hidden | AI picks a new Lord Commander                                                                                |
| `9002`   | hidden | AI fills vacant KG slot; searches realm for eligible candidates (prowess >= 15, `education_martial_prowess`) |
| `9003`   | hidden | AI KG maintenance helper                                                                                     |
| `9004`   | hidden | AI KG maintenance helper                                                                                     |
| `9005`   | hidden | AI KG maintenance helper                                                                                     |
| `9007`   | hidden | Grab lost Kingsguard, send them home to the king's court                                                     |
| `9008`   | hidden | AI KG maintenance helper                                                                                     |
| `9100`   | hidden | Initialization/setup event                                                                                   |
| `9101`   | hidden | Initialization/setup event                                                                                   |

### Namespace `agot_kingsguard_white_book`

| Event ID | Type      | Purpose                                                                 |
| -------- | --------- | ----------------------------------------------------------------------- |
| `0001`   | character | Browse the White Book: displays member list with selection widget       |
| `0002`   | character | View a specific member's page                                           |
| `1000`   | hidden    | Updates the White Book on member death, removal, or Night's Watch exile |

---

## Sub-Mod Recipes

### Recipe 1: Allow Female Kingsguard

Override the gender trigger. Create a file that loads after AGOT:

```pdx
# common/scripted_triggers/99_my_mod_kingsguard_triggers.txt
valid_kingsguard_gender_trigger = {
    always = yes
}
```

This single override is enough because `can_be_kingsguard_trigger` delegates
gender checks to `valid_kingsguard_gender_trigger`.

### Recipe 2: Add a Custom Kingsguard for Another Empire

AGOT gates the Kingsguard on `has_variable = kingsguard` on the primary title.
To give another empire its own guard, set the variable in history or via event:

```pdx
# events/my_custom_guard_events.txt
my_mod.0001 = {
    hidden = yes
    immediate = {
        title:e_my_empire = {
            set_variable = { name = kingsguard value = yes }
        }
    }
}
```

The ruler of `e_my_empire` will then pass
`ruler_primary_title_has_kingsguard_trigger` and gain access to all appointment
interactions and events. Council positions will be assigned to their court.

### Recipe 3: Custom Event on Kingsguard Appointment

Hook into the existing flow by firing your event from `agot_kingsguard.1012`
(the hidden setup event that runs after every appointment). Add an `on_action`
or override the event to chain your own:

```pdx
# events/my_mod_kingsguard_events.txt
namespace = my_mod_kg

my_mod_kg.0001 = {
    type = character_event
    title = my_mod_kg.0001.t
    desc = my_mod_kg.0001.desc
    theme = court

    left_portrait = {
        character = scope:new_kingsguard
        animation = personality_honorable
    }

    option = {
        name = my_mod_kg.0001.a
        # Your custom logic here
    }
}
```

Then trigger it from a scripted effect that wraps the vanilla one, or use an
`on_action` tied to trait gain:

```pdx
# common/on_action/my_mod_kg_on_actions.txt
on_trait_added = {
    trigger = {
        trait = kingsguard
    }
    events = {
        my_mod_kg.0001
    }
}
```

### Recipe 4: Modify AI Candidate Selection Criteria

The AI fills vacant slots in `agot_kingsguard.9002`. It searches
`every_vassal_or_below > every_courtier_or_guest` with these conditions:

```pdx
can_be_kingsguard_trigger = { COURT_OWNER = scope:king }
prowess >= 15
has_trait = education_martial_prowess
```

To change minimum prowess or add/remove requirements, override this event. For
example, to also accept characters with `blademaster` traits regardless of
education:

```pdx
# In your overridden copy of the event, adjust the limit block:
limit = {
    can_be_kingsguard_trigger = { COURT_OWNER = scope:king }
    top_liege = root
    OR = {
        AND = {
            prowess >= 15
            has_trait = education_martial_prowess
        }
        has_trait = blademaster_3
    }
    NOR = {
        has_trait = kingsguard
        # ... rest of exclusions
    }
}
```

### Recipe 5: Add a White Book Entry for a Custom Historical Character

In your mod's history or on_action, call the historical page creation:

```pdx
agot_kingsguard_create_historical_white_book_page = { KINGSGUARD = character:my_custom_knight }
add_to_global_variable_list = {
    name = kingsguard_white_book
    target = character:my_custom_knight
}
```

Make sure the character exists in your `history/characters/` files and that the
call happens after `agot_kingsguard_init_white_book` runs.

---

## Pitfalls

### 1. Council slot overflow

There are exactly 7 slots: 1 Lord Commander + 6 ordinary. The
`agot_join_kingsguard_effect` checks each slot in order (`kingsguard_1` through
`kingsguard_6`) via `else_if` chains. If all slots are filled, the character
gets the `kingsguard` trait but is NOT assigned to a council position, creating
an orphaned Kingsguard member. Always check slot availability before calling the
join effect.

### 2. Variable / council position desync

Each slot is tracked in two places: the council position (`cp:kingsguard_N`) and
a variable on the king's primary title (`var:kingsguard_N`). If you manipulate
one without the other (e.g., calling `fire_councillor` without clearing the
variable), the system breaks. Always use `agot_remove_kingsguard_effect` for
clean removal.

### 3. The `blocked_from_leaving` flag

Kingsguard members get `character_flag = blocked_from_leaving` which prevents
them from wandering off. If you remove the `kingsguard` trait manually without
also removing this flag, the character becomes permanently stuck in court. Use
`agot_on_fired_from_kingsguard` or `agot_remove_kingsguard_effect` instead.

### 4. White Book disabled in multiplayer

All White Book effects are gated behind `agot_is_white_book_enabled`. If your
sub-mod depends on White Book pages existing, it will silently fail in
multiplayer or with the multiplayer-safe game rule enabled. Always check this
trigger or provide a fallback.

### 5. Lord Commander title grants

`agot_assign_lord_commander_effect` grants `title:d_kingsguard` and swears
fealty. If the commander is lowborn, the effect temporarily records this
(`scope:lc_is_lowborn`) and calls `set_to_lowborn = yes` afterward to prevent
the title grant from auto-founding a dynasty. If you bypass this effect, lowborn
characters will unexpectedly gain a dynasty.

### 6. The `can_fire_kingsguard` flag

Before firing a councillor from a KG slot, the code adds
`character_flag = can_fire_kingsguard`. The council position's `can_fire` block
likely checks for this flag. If you call `fire_councillor` without setting it
first, the operation may be silently blocked.

### 7. Interaction rejection is permanent

When a character declines `invite_to_kingsguard_interaction`, they receive
`character_flag = kingsguard_position_rejected` with no expiry. The interaction
checks `NOT { has_character_flag = kingsguard_position_rejected }` in
`is_valid`. To allow re-invitation, you must manually remove this flag.

### 8. Death reason for fleeing Kingsguard

`agot_kingsguard_fled_effect` uses a prowess duel. On failure, the character
dies with `death_reason = death_kg_fleeing`. If you are adding custom
death-reason handling or tooltips, make sure this death reason is defined in
your localization.

### 9. `title:h_the_iron_throne` vs `primary_title` for variables

The removal effect cleans up variables on `title:h_the_iron_throne`, while the
join effect stores them on the king's `primary_title`. These are normally the
same title, but in edge cases (e.g., a pretender scenario where the Iron Throne
holder's primary title changes) they could diverge, causing orphaned variables.

### 10. Overriding `agot_kingsguard_init_white_book`

This effect creates historical entries for ~90 canonical Kingsguard members
gated by `game_start_date`. If you override it to add entries, you must include
all the original entries or they will be lost. Prefer calling
`agot_kingsguard_create_historical_white_book_page` from your own separate
on_action rather than replacing this massive effect.
