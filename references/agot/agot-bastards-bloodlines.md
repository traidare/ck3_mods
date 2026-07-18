# AGOT: Bastards & Bloodlines

## Overview

AGOT replaces vanilla CK3's minimal bastard handling with a lore-accurate
Westerosi system featuring:

- **Regional bastard surnames** (Snow, Sand, Rivers, etc.) implemented as hidden
  inactive traits
- **Legitimization** via house head interaction or liege petition, with
  AGOT-specific feudal restrictions
- **Bastard cadet branches** -- landed bastards with children automatically form
  a cadet house (controlled by game rule `agot_bastard_cadets`)
- **Royal bastard revelation** -- a story cycle (`agot_royal_bastard_story`)
  driving the political consequences of exposing an Iron Throne claimant's true
  parentage (the "Jon Snow" pipeline)
- **Custom secret type** `secret_agot_disputed_heritage` for characters whose
  real parents differ from their legal parents
- **Dragonblood inheritance** -- bastard cadet houses inherit the
  `dragonrider_house_modifier` from their parent house, preserving
  dragon-bonding eligibility across bastard lines

All bastard surname logic is gated on faith doctrine:
`has_doctrine_parameter = bastards_none` skips surname assignment entirely
(e.g., Dornish faiths that do not stigmatize bastards).

## Key Concepts

### Bastard Traits

Three mutually-exclusive traits control bastard status, defined in
`common/traits/00_traits.txt`:

| Trait                 | Effect                                                         | Inheritance       |
| --------------------- | -------------------------------------------------------------- | ----------------- |
| `bastard`             | -1 Diplomacy, -15 dynasty opinion, `inheritance_blocker = all` | Blocks all        |
| `legitimized_bastard` | -1 Diplomacy, -10 dynasty opinion, -5% legitimacy gain         | None (legitimate) |
| `bastard_founder`     | -1 Diplomacy, `inheritance_blocker = all`                      | Blocks all        |

The `bastard_founder` trait is given when a bastard with children has their
secret exposed -- they keep inheritance-blocking but their children get
reorganized into a new cadet house.

### Regional Bastard Surnames

AGOT defines 9 surname traits in `common/traits/00_agot_hidden_traits.txt`. Each
is a hidden trait (`shown_in_encyclopedia = no`) applied as an **inactive
trait** via `make_trait_inactive`:

| Surname Trait     | Region           | Cultures                                                                                                                                                                                                                                             |
| ----------------- | ---------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `surname_snow`    | The North        | `northman`, `skagosi`, `crannogman`, `barrowman`, `bearman`, `fangman`, `first_man`, `forestman`, `frozen_shoreman`, `harborman`, `northern_clan`, `hornfoot`, `ice_riverman`, `krakenman`, `lakefolk`, `nightrunner`, `thenn`, `wolfswood_clansman` |
| `surname_sand`    | Dorne            | `greenblood`, `salt_dornish`, `sand_dornish`, `stone_dornish`                                                                                                                                                                                        |
| `surname_rivers`  | The Riverlands   | `riverman_main`                                                                                                                                                                                                                                      |
| `surname_flowers` | The Reach        | `honeywiner`, `marcher`, `reachman`, `shieldman`, `vineman`                                                                                                                                                                                          |
| `surname_storm`   | The Stormlands   | `stormlander_main`                                                                                                                                                                                                                                   |
| `surname_stone`   | The Vale         | `valeman_finger`, `valeman_upper`, `valeman_main`, `sisterman`, `moon_clan`                                                                                                                                                                          |
| `surname_hill`    | The Westerlands  | `westerman_main`                                                                                                                                                                                                                                     |
| `surname_pyke`    | The Iron Islands | `ironborn`                                                                                                                                                                                                                                           |
| `surname_waters`  | The Crownlands   | `clawman`, `crownlander`, `westerosi_valyrian`                                                                                                                                                                                                       |

The surname is **inactive** -- CK3 uses inactive traits to display a "nickname"
on the character portrait without applying stat effects. The `bastard` trait in
`00_traits.txt` has `triggered_desc` blocks that check for each inactive surname
and display the appropriate description (e.g., `trait_bastard_flowers_desc`).

### Dragonblood & Bastard Houses

When `agot_create_bastard_cadet_effect` creates a cadet branch for a bastard, it
checks whether the parent house has `dragonrider_house_modifier`. If so, the new
bastard house receives the same modifier:

```pdx
# From 00_agot_bastard_effects.txt
agot_create_bastard_cadet_effect = {
    save_scope_as = bastard_branch_creator
    house = { save_scope_as = former_house }
    create_cadet_branch = { }
    house = {
        save_scope_as = new_house
        if = {
            limit = {
                scope:former_house = { has_house_modifier = dragonrider_house_modifier }
            }
            add_house_modifier = dragonrider_house_modifier
        }
        set_variable = { name = bastard_house_of value = scope:former_house }
        # COA handling...
        generate_coa = bastards
    }
    trigger_event = agot_dynastic_stability.1002
}
```

This means a Targaryen bastard who founds House Blackfyre (or a generated
bastard house) will have `dragonrider_house_modifier`, making their descendants
eligible for dragon bonding via `agot_is_dragonblood_character`. The trigger
checks `house ?= { has_house_modifier = dragonrider_house_modifier }` as one of
its conditions.

### The `secret_agot_disputed_heritage` Secret Type

Defined in `common/secret_types/agot_secret_types.txt`, this secret type is used
for characters like Jon Snow whose legal parents differ from their biological
parents. Key behaviors:

- **is_valid**: `secret_target` must have both `real_mother` and `real_father`
  that differ from `mother` and `father`
- **on_owner_death**: Transfers ownership to the secret target if they know the
  secret
- **on_discover**: If the discoverer IS the secret target, they create their own
  copy of the secret
- **on_expose**: Calls `set_father`/`set_mother` to the real parents, reassigns
  house, and if the real father's line held the Iron Throne, adds unpressed
  claims to `title:h_the_iron_throne` and related titles, then fires
  `agot_events_bastard.0950` to launch the royal bastard story cycle

## AGOT Scripted API

### Scripted Effects (common/scripted_effects/)

**File: `00_agot_bastard_effects.txt`**

| Effect                                             | Parameters                                 | Purpose                                                                                                                                                                                                |
| -------------------------------------------------- | ------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `agot_add_birthplace_bastard_nickname_effect`      | `BIRTHPLACE` (province scope)              | Assigns regional surname trait based on birthplace `geographical_region`. Called from `on_birth_child` in `child_birth_on_actions.txt`. If character already has a surname, removes the old one first. |
| `agot_add_custom_bastard_nickname_effect`          | none                                       | Assigns surname based on `location` (current province), not birthplace. Fallback: `surname_waters`.                                                                                                    |
| `agot_remove_bastard_nickname_effect`              | none                                       | Removes all surname traits via `make_trait_active` + `remove_trait`. Also recursively removes surnames from legitimate children who inherited them.                                                    |
| `agot_legitimize_bastard_effect`                   | `BASTARD`, `LEGITIMIZER`                   | Removes `bastard`, adds `legitimized_bastard`, adds `legitimized_me_opinion`, removes surname, adds `favor_hook`, and propagates house to lowborn children (3 generations deep).                       |
| `agot_create_bastard_cadet_effect`                 | none (uses `this`)                         | Creates cadet branch, copies `dragonrider_house_modifier`, sets `bastard_house_of` variable, generates `bastards` COA, fires `agot_dynastic_stability.1002`.                                           |
| `agot_crown_bastard_nickname_effect`               | none                                       | Replaces surname trait with a crowned nickname (e.g., `nick_agot_snowcrowned`, `nick_agot_sandcrowned`). Used when a bastard takes the throne.                                                         |
| `agot_children_of_bastard_surname_effect`          | none (uses `scope:father`, `scope:mother`) | Propagates the bastard surname to legitimate children of a bastard who marries (matrilineal/patrilineal aware). Skips if parent has `legitimized_bastard` or `bastard_founder`.                        |
| `agot_update_noble_bastard_house_and_descendants`  | `OLD_HOUSE`, `NEW_HOUSE`                   | Reassigns house for a bastard and all descendants (3 generations) when house changes.                                                                                                                  |
| `agot_update_common_bastard_house_and_descendants` | `NEW_HOUSE`                                | Same as above but without an old house reference (for lowborn bastards).                                                                                                                               |

**File: `00_bastard_effects.txt` (vanilla override)**

| Effect                                    | Purpose                                                                                                                                                   |
| ----------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `set_parent_house_effect`                 | AGOT-modified: removes the `bastard_legitimacy_change_cutoff_age` check (bastardry changes have no cutoff in ASOIAF). Excludes `house:house_Most_Devout`. |
| `add_bastard_trait_based_on_faith_effect` | Adds `bastard` or `wild_oat` based on faith doctrine `bastards_none`.                                                                                     |

### Scripted Triggers (common/scripted_triggers/)

**File: `00_agot_bastard_triggers.txt`**

| Trigger                                | Purpose                                                                                                                                                                                                        |
| -------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `real_paternal_held_iron_throne_claim` | Checks if the character's `real_father` (or grandparent) was a past holder of `title:h_the_iron_throne` and did not have flag `mw_gave_up_crown_after_megawar`.                                                |
| `knows_self_royal_bastard_secret`      | Returns yes if the character knows a `secret_agot_disputed_heritage`, `secret_disputed_heritage`, or `secret_unmarried_illegitimate_child` about themselves AND their real father's line held the Iron Throne. |
| `knows_other_royal_bastard_secret`     | Same as above but for secrets about OTHER characters, and only if `can_be_exposed_by` the checker.                                                                                                             |
| `agot_royal_bastard_should_give_up`    | AI heuristic: returns yes if military strength <= 1000 or primary title is a barony.                                                                                                                           |
| `agot_bastard_surname_trigger`         | Returns yes if the character has any active bastard surname (either via inactive trait OR via culture+bastard trait match). Used in `00_traits.txt` for `triggered_desc` on the `bastard` trait.               |

### Game Rules

**File: `common/game_rules/00_agot_game_rules.txt`**

```pdx
agot_bastard_cadets = {
    default = agot_bastard_cadets_landed_only
    agot_bastard_cadets_everyone = {}
    agot_bastard_cadets_landed_only = {}
}
```

Controls whether cadet branches are created for all bastards with children or
only landed ones. Checked in `agot_dynastic_stability.1000`.

## Interactions & Decisions

### Character Interactions

**File: `common/character_interactions/00_house_head_interactions.txt`**

**`legitimize_bastard_interaction`** -- The standard CK3 legitimization,
AGOT-modified:

- `is_shown`: Requires `has_doctrine_parameter = bastards_legitimize` on actor,
  house head, AND the bastard. Actor must not be in a feudal government without
  being an `agot_is_independent_ruler`. Actor must not be Night's Watch
  (`government_is_nw`).
- `cost`: `bastard_legitimization_prestige_cost`
- `on_accept`: Calls `legitimize_bastard_interaction_opinions_effect` and
  `agot_legitimize_bastard_effect`

**File: `common/character_interactions/00_agot_bastard_interactions.txt`**

**`legitimize_bastard_liege_interaction`** -- Petition your liege/top liege to
legitimize your bastard:

- Category: `interaction_category_vassal`
- Redirects `scope:recipient` to `scope:actor.top_liege`
- Only available to non-independent, non-concubine, non-Night's Watch characters
- `ai_accept` base: -80 (very reluctant), modified by prestige level, hooks,
  opinion, dread
- `auto_accept` if actor is independent OR has a strong hook on the liege
- Cost: prestige + renown (if dynast and human)

**`reveal_royal_bastardry_interaction`** -- Tell a character about their true
royal parentage:

- Category: `interaction_category_friendly`
- Requires knowing a `secret_agot_disputed_heritage`,
  `secret_disputed_heritage`, or `secret_unmarried_illegitimate_child` about the
  recipient whose real father's line held the Iron Throne
- Actor must not have `has_character_flag = told_true_parentage`
- `auto_accept = yes`
- Fires `agot_events_bastard.0900`

### Decisions

**File: `common/decisions/agot_decisions/00_agot_bastard_decisions.txt`**

**`agot_expose_true_parentage_decision`** -- Reveal a royal bastard's true
parentage to the realm:

- `decision_group_type = major`
- Requires `knows_other_royal_bastard_secret = yes` and the bastard must be
  adult
- Has special flavor text for Ned Stark (`character:Stark_3`) revealing Jon
  Snow's secret
- Fires `agot_events_bastard.0900`
- AI: Influenced by `honest`, `just` (positive), `deceitful` (negative), opinion
  of Iron Throne holder

**`agot_expose_my_true_parentage_decision`** -- Reveal YOUR OWN true royal
parentage:

- Requires `knows_self_royal_bastard_secret = yes` and not already owning
  `agot_royal_bastard_story`
- Must be adult, landed, prestige level >= 1
- Effect: Adds unpressed claims to Iron Throne and related titles
  (`title:h_the_iron_throne`, `title:e_the_crownlands`,
  `title:k_the_blackwater`, `title:d_kings_landing`, `title:c_kings_landing`,
  `title:k_dragonstone`, `title:d_dragonstone`, `title:c_dragonstone`)
- Fires `agot_events_bastard.0950` after 7-14 days

**`agot_royal_bastard_claim_decision`** -- Press your claim on the Iron Throne
as a known royal bastard:

- Requires `has_character_flag = royal_bastard` and various state flags to
  prevent re-firing
- Must be landed, adult, capable, at home, not at war, no truces with IT holder,
  prestige >= 2
- If character previously forswore claims
  (`has_character_flag = forswore_royal_claims`), applies
  `agot_reversed_claim_forswear` modifier and -150 prestige
- Creates `agot_royal_bastard_story` story cycle

## Events

**File: `events/agot_events/agot_bastard_events.txt`**

Namespace: `agot_events_bastard`

The event file is organized into three major blocks:

### Secret Management (0900-0949)

| Event       | Description                                                                                                                                                               |
| ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `0900`      | Hidden handler -- dispatches to 0901 (parent reveals), 0903 (non-parent reveals), or 0912 (employer reveals). Sets `royal_bastard` and `awaiting_bastardry_result` flags. |
| `0901`      | Parent tells child about their true parentage. Special Jon Snow / Ned Stark flavor.                                                                                       |
| `0902`      | Child responds to parent's revelation (did not know).                                                                                                                     |
| `0903`      | Non-parent shares the secret with the bastard via letter.                                                                                                                 |
| `0904`      | Child responds to letter from non-parent.                                                                                                                                 |
| `0905`      | Parent reveals to child who already knew.                                                                                                                                 |
| `0906`      | Parent responds to child's decision to keep parentage hidden.                                                                                                             |
| `0907`      | Child responds to letter, having already known.                                                                                                                           |
| `0908-0909` | Sharer responds / does not receive reply.                                                                                                                                 |
| `0910`      | Parent responds to child asking for advice.                                                                                                                               |
| `0911`      | Special: Catelyn Tully confronts Ned about Jon (requires `character:Stark_3` married to `character:Tully_4`).                                                             |
| `0912-0916` | Employer-courtier revelation chain.                                                                                                                                       |
| `0917-0919` | Proximity-based revelation (someone who knows is in the same location).                                                                                                   |
| `0920`      | Jon discovers the secret by accident.                                                                                                                                     |

### Announcement & Realm Notification (0950-0969)

| Event       | Description                                                                                 |
| ----------- | ------------------------------------------------------------------------------------------- |
| `0950`      | Handler: creates `agot_royal_bastard_story`, notifies realm via `agot_events_bastard.0951`. |
| `0951`      | Realm lords receive notification letter.                                                    |
| `0952-0955` | Parent/sharer notification chains.                                                          |
| `0956-0957` | Child alerted to non-consensual sharing.                                                    |
| `0958`      | Revealer is notified of consequences.                                                       |
| `0959`      | King is alerted to the claimant.                                                            |
| `0960`      | Special: Robert reads Ned's letter.                                                         |
| `0961-0963` | King responds: harshly, lightly, or to same-dynasty reveal.                                 |

### Demand Responses & War (0970-1019)

| Event       | Description                                                                                                        |
| ----------- | ------------------------------------------------------------------------------------------------------------------ |
| `0970`      | Employer responds to king's demand (unlanded claimant).                                                            |
| `0971`      | Bastard responds to king's demand (landed claimant).                                                               |
| `0980-0985` | Realm notification letters for various demands (execution, Night's Watch, imprisonment, hostage, forswear claims). |
| `0990`      | Pre-war marriage for alliance.                                                                                     |
| `0991-0993` | War declaration events (rebel and king sides).                                                                     |
| `0994-0996` | War end events (king wins, bastard wins, helped bastard win).                                                      |
| `1001-1006` | Ruler notified of acceptance (execute, NW, imprison, hostage, forswear).                                           |
| `1019`      | Maintenance: cleanup if resolution takes > 1 year.                                                                 |

### Story Cycle

**File: `common/story_cycles/agot_story_cycle_royal_bastard.txt`**

The `agot_royal_bastard_story` story cycle manages the entire political
aftermath of a royal bastard revelation. It stores variables for `revealer`,
`bastard`, `real_mother`, `real_father`, `employer`, and `it_ruler` (Iron Throne
holder). On setup, it notifies all de jure county holders of the Iron Throne via
`agot_events_bastard.0951`.

### Dynastic Stability Events

**File: `events/agot_events/agot_dynastic_stability_events.txt`**

| Event                          | Description                                                                                                                                 |
| ------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------- |
| `agot_dynastic_stability.1000` | Hidden handler: when a bastard inherits a title, checks game rule `agot_bastard_cadets` and routes to cadet creation or house reassignment. |
| `agot_dynastic_stability.1001` | Rejoins parent house via `agot_set_parent_house_effect`.                                                                                    |
| `agot_dynastic_stability.1002` | Cadet house name generator (custom COA).                                                                                                    |
| `agot_dynastic_stability.1003` | Unlanded bastard: rejoins parent house, removes `bastard_founder`.                                                                          |

## Sub-Mod Recipes

### Recipe 1: Add a Custom Bastard Surname for a New Region

To add bastard surname "Storm" for a custom Essos region:

**Step 1** -- Define the hidden trait in
`common/traits/my_mod_hidden_traits.txt`:

```pdx
surname_myregion = {
    physical = no
    shown_in_ruler_designer = no
    shown_in_encyclopedia = no
    name = trait_hidden
    desc = trait_hidden_desc
}
```

**Step 2** -- Add an `else_if` branch in a copy of
`agot_add_birthplace_bastard_nickname_effect`:

```pdx
else_if = {
    limit = { $BIRTHPLACE$ = { geographical_region = world_essos_my_region } }
    custom_description = {
        text = agot_gain_surname_myregion_effect
        object = this
        make_trait_inactive = surname_myregion
    }
}
```

**Step 3** -- Add matching branches in `agot_remove_bastard_nickname_effect` and
`agot_add_custom_bastard_nickname_effect`.

**Step 4** -- Add `triggered_desc` to the `bastard` trait definition in
`00_traits.txt` for the new surname.

**Step 5** -- Add the check to `agot_bastard_surname_trigger` in
`00_agot_bastard_triggers.txt`.

**Step 6** -- Add localization for `agot_gain_surname_myregion_effect` and
`agot_lose_surname_myregion_effect`.

### Recipe 2: Grant Dragonblood to a Bastard House

If you create a custom bastard house that should have dragon-bonding potential:

```pdx
# In your event or effect
house:house_my_bastard_house = {
    add_house_modifier = dragonrider_house_modifier
}
```

This makes all members pass the `agot_is_dragonblood_character` trigger, which
checks:

```pdx
house ?= { has_house_modifier = dragonrider_house_modifier }
```

Note: `agot_create_bastard_cadet_effect` already handles this automatically for
bastards of dragonblood houses. You only need manual assignment for houses not
created through that effect.

### Recipe 3: Create a Custom Legitimization Path

To add a legitimization tied to a specific event (e.g., a council decree):

```pdx
# In your event's option
agot_legitimize_bastard_effect = {
    BASTARD = scope:target_bastard
    LEGITIMIZER = root
}
```

This single call handles: trait swap (`bastard` -> `legitimized_bastard`),
surname removal, opinion modifier, favor hook, and house propagation to
children.

### Recipe 4: Trigger a Royal Bastard Claim Storyline

To programmatically start the royal bastard story for a character:

```pdx
scope:my_bastard = {
    # Set up required variables
    set_variable = { name = revealer_passthrough value = scope:revealer }
    set_variable = { name = bastard_passthrough value = scope:my_bastard }
    set_variable = { name = real_father_passthrough value = scope:my_bastard.real_father }
    set_variable = { name = real_mother_passthrough value = scope:my_bastard.real_mother }
    # Flag and create story
    add_character_flag = royal_bastard
    create_story = agot_royal_bastard_story
}
```

The story cycle's `on_setup` reads these variables and cleans them up.

## Pitfalls

### 1. Surname Traits Must Be Inactive

The surname traits (e.g., `surname_snow`) must be applied via
`make_trait_inactive`, never `add_trait`. Using `add_trait` would make them
visible as a regular trait with no icon and the generic "hidden trait" name. The
`make_trait_inactive` approach integrates with the `bastard` trait's
`triggered_desc` for proper display.

### 2. Removing Surnames Requires Two Steps

You cannot simply `remove_trait` an inactive trait. You must first
`make_trait_active` and THEN `remove_trait`:

```pdx
make_trait_active = surname_snow
remove_trait = surname_snow
```

Skipping `make_trait_active` will silently fail.

### 3. The `bastards_none` Doctrine Gate

All surname assignment checks
`faith = { NOT = { has_doctrine_parameter = bastards_none } }`. If you create a
new faith where bastards are not stigmatized, no surnames will be assigned. Your
sub-mod must respect this gate or intentionally override it.

### 4. Cadet Branch COA

`agot_create_bastard_cadet_effect` calls `generate_coa = bastards` to create a
bastard-appropriate coat of arms. If the character has
`has_character_flag = has_personal_coa`, it uses `var:my_personal_coa.house`
instead. Sub-mods that set personal COAs on bastards should set this flag and
variable before the cadet creation fires.

### 5. House Propagation Depth Limit

Both `agot_update_noble_bastard_house_and_descendants` and
`agot_update_common_bastard_house_and_descendants` only propagate house changes
3 generations deep (children, grandchildren, great-grandchildren). Characters
beyond this depth will not be updated.

### 6. AGOT Feudal Legitimization Restriction

Unlike vanilla CK3, AGOT requires the legitimizer to be an
`agot_is_independent_ruler` (or non-feudal) to use
`legitimize_bastard_interaction`. Feudal vassals must petition their top liege
via `legitimize_bastard_liege_interaction` instead. Sub-mods adding new
legitimization paths should respect this restriction.

### 7. The `bastard_founder` Trap

When a bastard's `secret_agot_disputed_heritage` is exposed and they have
children, the `on_expose` handler swaps `bastard` for `bastard_founder` and
creates a cadet branch. The `bastard_founder` trait still blocks inheritance
(`inheritance_blocker = all`). Sub-mods should check for BOTH `bastard` and
`bastard_founder` when testing bastard status.

### 8. The Royal Bastard Story Requires Variable Setup

You cannot call `create_story = agot_royal_bastard_story` without first setting
the `revealer_passthrough`, `bastard_passthrough`, `real_father_passthrough`,
and `real_mother_passthrough` variables on the story owner. The `on_setup` block
reads and removes these variables. Missing variables will cause errors.

### 9. Dragon Blood Inheritance via Bastard Lines

The `dragonrider_house_modifier` is copied to bastard cadet houses automatically
by `agot_create_bastard_cadet_effect`. However, if a bastard is legitimized
BEFORE creating a cadet branch (i.e., they return to the parent house via
`agot_legitimize_bastard_effect`), the modifier is not separately applied --
they inherit it from the parent house directly. Sub-mods manipulating dragon
blood should be aware of both paths.

### 10. `told_true_parentage` Flag Is One-Shot

Both `agot_expose_true_parentage_decision` and
`reveal_royal_bastardry_interaction` set
`has_character_flag = told_true_parentage`, which permanently prevents the
character from revealing again. There is no built-in way to reset this flag.
