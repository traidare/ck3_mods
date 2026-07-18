# AGOT: Coronation

## Overview

The AGOT Coronation system replaces vanilla CK3's coronation DLC feature with a
custom activity (`activity_agot_coronation`) designed around Westerosi lore. It
gives independent feudal kings and emperors a multi-phase ceremony that includes
choosing an officiant, selecting a crown artifact, receiving vassal reactions,
and earning legitimacy/piety/prestige rewards based on ceremony options.

The system activates when the `coronations` DLC feature is **not** present
(checked via `agot_uses_agot_coronations_trigger`). When the DLC is present,
AGOT defers to vanilla coronation laws instead.

**Key files at a glance:**

| Area                                       | Path (relative to mod root)                                                              |
| ------------------------------------------ | ---------------------------------------------------------------------------------------- |
| Activity definition                        | `common/activities/activity_types/agot_coronation.txt`                                   |
| Coronation triggers                        | `common/scripted_triggers/00_agot_coronation_triggers.txt`                               |
| Crown triggers                             | `common/scripted_triggers/00_agot_crown_triggers.txt`                                    |
| Main effects                               | `common/scripted_effects/00_agot_coronation_effects.txt`                                 |
| Reward effects                             | `common/scripted_effects/00_agot_coronation_reward_effects.txt`                          |
| Officiant AI selection                     | `common/scripted_effects/00_agot_coronation_select_officiant_effects.txt`                |
| AI crown selection                         | `common/scripted_effects/00_agot_coronation_ai_select_crown_effects.txt`                 |
| Accolade glory                             | `common/scripted_effects/00_agot_coronation_accolades_scripted_effects.txt`              |
| Interaction (invite)                       | `common/character_interactions/00_agot_coronation_interactions.txt`                      |
| On-actions (vanilla phases)                | `common/on_action/activities/coronation_on_actions.txt`                                  |
| On-actions (AGOT extras)                   | `common/on_action/activities/agot_coronation_on_actions.txt`                             |
| AGOT coronation events                     | `events/activities/agot_coronation_activity/agot_coronation_events.txt`                  |
| Crown commission events                    | `events/activities/agot_coronation_activity/agot_coronation_crown_commission_events.txt` |
| Decision events (officiant/crown/crowning) | `events/agot_events/agot_coronation_decision_events.txt`                                 |
| Coronation memories                        | `common/character_memory_types/agot_coronation_memories.txt`                             |

---

## Key Concepts

### Who Can Hold a Coronation

The trigger `agot_ruler_requires_coronation` gates access:

```pdx
agot_ruler_requires_coronation = {
    highest_held_title_tier >= tier_kingdom
    agot_is_independent_ruler = yes
    is_landed = yes
    government_has_flag = government_is_feudal
}
```

Additionally the character must be **uncrowned**
(`agot_is_uncoronated_trigger = yes`), at least 7 years old, alive, not
imprisoned, and not at war (for AI).

### Uncoronated State

AGOT tracks the uncrowned state through multiple overlapping markers:

- **Inactive trait:** `not_had_coronation` (an inactive trait that gets toggled)
- **Character flag:** `not_had_coronation`
- **Character modifiers:** `uncoronated_modifier` and
  `uncoronated_child_modifier`

The cleanup effect `agot_remove_any_uncoronated_effect` strips all of these:

```pdx
agot_remove_any_uncoronated_effect = {
    hidden_effect = {
        if = {
            limit = { has_inactive_trait = not_had_coronation }
            make_trait_active = not_had_coronation
            remove_trait = not_had_coronation
        }
    }
    if = {
        limit = { has_character_flag = not_had_coronation }
        remove_character_flag = not_had_coronation
    }
    if = {
        limit = { has_character_modifier = uncoronated_child_modifier }
        remove_character_modifier = uncoronated_child_modifier
    }
    if = {
        limit = { has_character_modifier = uncoronated_modifier }
        remove_character_modifier = uncoronated_modifier
    }
}
```

### Officiant Selection

The player picks an officiant through event `coronation_decision.0001`. Eligible
candidates are gathered from:

1. The court chaplain (`cp:councillor_court_chaplain`)
2. Empire-tier vassals
3. Kingdom-tier vassals
4. Duchy-tier vassals

They are shown via the `agot_character_selection_three_options` widget. The
player can also choose to **crown themselves**
(`has_character_flag = crowning_self`), which costs `major_legitimacy_loss`.

For AI, the `officiant_ai_choose_character_from_list_effect` uses an
`ordered_in_list` with a detailed scoring system:

| Factor                              | Score |
| ----------------------------------- | ----- |
| Castellan councillor                | +100  |
| Powerful vassal                     | +125  |
| Regular councillor (non-Kingsguard) | +100  |
| Empire-tier title                   | +100  |
| Kingdom-tier title                  | +75   |
| Duchy-tier title                    | +50   |
| County-tier title                   | +25   |
| Head of faith (zealous AI)          | +1000 |
| Different faith (zealous AI)        | -200  |
| Head of faith (cynical AI)          | -1000 |
| Adult heir                          | +150  |
| Consort                             | +150  |
| Sibling                             | +125  |
| Extended family                     | +40   |
| Best friend                         | +200  |
| Friend                              | +60   |
| Soulmate                            | +100  |
| Lover                               | +60   |
| Rival                               | -100  |
| Nemesis                             | -1000 |

The officiant is stored as the special guest `coronation_officiant`. Non-High
Septon officiants receive the nickname `nick_agot_the_kingmaker` or
`nick_agot_the_queenmaker`.

### Crown Selection

After choosing an officiant, `coronation_decision.0002` fires for crown
selection.

**For players:** All artifacts in the `helmet` slot are shown via the
`agot_artifact_selection` widget. The selected crown gets
`set_variable = coronation_crown`.

**For AI:** The `ai_choose_crown_effect` builds a `possible_crowns` temporary
list from all `helmet`-slot artifacts and scores them with `ordered_in_list`.
The scoring heavily favors lore-accurate pairings:

- **+1000** for the historically correct crown (e.g., Aegon I's crown for
  `is_Targaryen_27`, Jaehaerys I's crown for `is_Targaryen_35`)
- **+100** for any crown of the correct dynasty (e.g., any Targaryen crown for
  `dynasty:dynn_Targaryen`)
- Specific character flags like `is_Baratheon_2` (Robert) map to
  `robertI_crown_artifact`, `is_Baratheon_3` (Stannis) to
  `stannis_crown_artifact`, etc.

Crown artifact variables used for identification include:
`crown_aegon_i_artifact`, `crown_aenys_artifact`, `crown_jaehaerys_artifact`,
`crown_aegon_iii_artifact`, `crown_baelor_artifact`, `crown_aegon_iv_artifact`,
`crown_maekar_artifact`, `daenerys_crown_artifact`, `robertI_crown_artifact`,
`stannis_crown_artifact`, `renly_crown_artifact`, `joffreyI_crown_artifact`,
`crown_daemonblackfyre_artifact`, `valyrian_crown1_artifact`,
`valyrian_crown2_artifact`, `westerosi_valyrian_crown1_artifact`,
`westerosi_valyrian_crown2_artifact`, `crown_of_the_tides_artifact`.

### Crown Commission (During Coronation)

If a ruler has no crown, the event `agot_activity_commission_crown.0001` fires
during the coronation preparation. This uses the same `agot_artifact_selection`
widget and creates dynasty-specific, realm-specific, or religion-specific crowns
via dedicated creation effects. Categories include:

- **Character-specific:** Aegon I, Aenys, Jaehaerys, Aegon III, Baelor, Aegon
  IV, Maekar, Daenerys, Robert I, Stannis, Renly, Joffrey I, Daemon Blackfyre
- **Dynasty/House:** Stark, Lannister, Arryn, Tyrell, Martell, Greyjoy,
  Baratheon, Bolton, Tully, Velaryon, Hightower, etc.
- **Regional:** North, Riverlands, Iron Islands, Vale, Reach, Dorne, Stormlands,
  Westerlands, Beyond the Wall
- **Religious:** Drowned God (driftwood crown), R'hllor, the Seven, Old Gods,
  First Men, Andals, Valyrian

Each crown type has a matching trigger (`agot_<name>_crown_trigger`) and
creation effect (`agot_create_artifact_<name>_crown_effect`).

### Rewards System

The `disburse_agot_coronation_activity_rewards` effect distributes rewards based
on the three option categories:

**Pomp** (`coronation_option_pomp`):

| Option                        | Piety     | Legitimacy | Modifier (20yr)                   | Courtly/Glory Hound | Parochial | Zealot (no HoF)  | Zealot (HoF officiant) |
| ----------------------------- | --------- | ---------- | --------------------------------- | ------------------- | --------- | ---------------- | ---------------------- |
| `coronation_pomp_grandiose`   | miniscule | major      | `coronation_grandiose_modifier`   | +30                 | -30       | -30              | +30                    |
| `coronation_pomp_impressive`  | minor     | medium     | `coronation_impressive_modifier`  | +30 / +15           | -15       | -15              | +30                    |
| `coronation_pomp_appropriate` | major     | minor      | `coronation_appropriate_modifier` | -15                 | +30       | +15              | +30                    |
| `coronation_pomp_humble`      | massive   | miniscule  | `coronation_humble_modifier`      | -30                 | +15       | +30 (same faith) | --                     |

Key insight: `zealot` vassals get +30 opinion via
`hof_officiated_coronation_opinion` if
`scope:activity.special_guest:coronation_officiant ?= faith.religious_head`. If
the officiant is NOT the Head of Faith, zealots are penalized.

**Entertainment** (`wedding_option_entertainment` -- reuses wedding categories):

- `wedding_entertainment_good`: +900 prestige to host, `major_prestige_gain` to
  guests
- `wedding_entertainment_normal`: +600 prestige, `medium_prestige_gain`
- `wedding_entertainment_bad`: +300 prestige, `minor_prestige_gain`

**Food** (`wedding_option_food` -- reuses wedding categories):

- `wedding_food_good`: +30 opinion, `lifestyle_reveler` XP/trait, +15
  `came_to_my_coronation_opinion`
- `wedding_food_normal`: +20 opinion, reveler XP, +10
  `came_to_my_coronation_opinion`
- `wedding_food_bad`: +5 opinion, reveler XP, +5 `came_to_my_coronation_opinion`

**Venue bonuses** are checked via `scope:coronation_venue`:

- Tier 3 buildings (`royal_garden_03`, `leisure_palace_03`, `the_red_keep_03`,
  `holy_site_great_sept_01`, `holy_site_starry_sept_01`):
  `massive_stress_impact_loss` + `major_dynasty_prestige_gain`
- Tier 2 buildings: `major_stress_impact_loss` + `minor_dynasty_prestige_gain`
- Tier 1 buildings: `medium_stress_impact_loss` + 10 dynasty prestige
- Holy site: `major_piety_gain`
- Capital province: `minor_gold_value`

**Additional rewards:**

- `promote_rule_intent`: `minor_legitimacy_gain`
- `raise_dynasty_prestige_intent`: `medium_dynasty_prestige_gain`
- Prestige level increase: if host's prestige level <= 2,
  `add_prestige_level = 1`
- Accolade glory via `accolades_activity_complete_coronation_glory_effect`

### Officiant Bonuses (Crowning Event)

In `coronation_decision.0003`, the officiant identity determines rewards:

| Officiant       | Coronation Target Gets                                  | Officiant Gets                                                       |
| --------------- | ------------------------------------------------------- | -------------------------------------------------------------------- |
| Head of Faith   | `major_piety_gain` + `major_legitimacy_gain`            | `major_piety_gain` + `major_legitimacy_gain` + `major_prestige_gain` |
| Same dynasty    | `major_dynasty_prestige_gain` + `major_legitimacy_gain` | `major_prestige_gain`                                                |
| Powerful vassal | 750 legitimacy                                          | `major_prestige_gain` + "Kingmaker"/"Queenmaker" nickname            |
| Other           | `major_prestige_gain` + `major_legitimacy_gain`         | `major_prestige_gain` + nickname                                     |

---

## AGOT Scripted API

### Triggers

| Trigger                                     | Scope     | Purpose                                                                |
| ------------------------------------------- | --------- | ---------------------------------------------------------------------- |
| `agot_ruler_requires_coronation`            | character | Independent feudal king+                                               |
| `agot_is_coronated_trigger`                 | character | Checks if coronated (AGOT path or vanilla law path)                    |
| `agot_is_uncoronated_trigger`               | character | Inverse of above                                                       |
| `agot_has_any_uncoronated_trigger`          | character | Checks all 4 uncoronated markers                                       |
| `agot_uses_agot_coronations_trigger`        | any       | `NOT = { has_dlc_feature = coronations }`                              |
| `is_valid_coronation_special_guest_trigger` | character | alive, human, not at war, not imprisoned                               |
| `needs_crown_for_coronation_trigger`        | character | Has any `helmet` slot artifact                                         |
| `iron_throne_valid_trigger`                 | any       | Iron Throne title exists and is held                                   |
| `activity_agot_coronation_is_valid_guest`   | character | age >= 3, not at war, not imprisoned, no other activity, not incapable |

### Effects

| Effect                                                | Scope     | Purpose                                                        |
| ----------------------------------------------------- | --------- | -------------------------------------------------------------- |
| `agot_remove_any_uncoronated_effect`                  | character | Strips all uncoronated markers                                 |
| `disburse_agot_coronation_activity_rewards`           | character | Main reward distribution (call on `scope:host`)                |
| `accolades_activity_complete_coronation_glory_effect` | character | Accolade glory based on option quality                         |
| `officiant_ai_choose_character_from_list_effect`      | any       | AI officiant scoring; params: `$LIST_TYPE$`, `$LIST$`, `$MAX$` |
| `ai_choose_crown_effect`                              | any       | AI crown scoring; param: `$SELECTOR$`                          |

### Key Scopes Used Across the System

- `scope:host` -- the character hosting the activity (same as coronation target)
- `scope:coronation_target` -- the ruler being crowned (same as host; stored as
  `special_guest:coronation_target`)
- `scope:officiant` -- the character performing the crowning (stored as
  `special_guest:coronation_officiant`)
- `scope:activity` -- the activity itself
- `scope:coronation_venue` -- the province where the coronation takes place
- `scope:selected_crown_for_coronation` -- the chosen crown artifact
- `scope:root_scope` -- alias for the root character in reward effects

### Key Variables and Flags

| Name                            | Type                            | Purpose                                              |
| ------------------------------- | ------------------------------- | ---------------------------------------------------- |
| `not_had_coronation`            | character flag / inactive trait | Marks uncrowned state                                |
| `crowning_self`                 | character flag                  | Set if ruler chooses to self-crown                   |
| `officiant`                     | character flag                  | Set on the officiant character                       |
| `coronation_crown`              | artifact variable               | Marks the artifact selected for the ceremony         |
| `coronation_refund_pot`         | activity variable               | Tracks gold spent on options for invalidation refund |
| `coronation_already_started`    | activity variable               | Prevents re-triggering phase start                   |
| `coronation_claimant`           | character flag                  | A claimant disrupting the coronation                 |
| `designated_saboteur`           | character flag                  | Guest planning sabotage                              |
| `planning_to_steal_crown`       | character variable              | Sabotage: steal the crown                            |
| `planning_to_sabotage_throne`   | character variable              | Sabotage: damage the throne                          |
| `planning_to_convince_claimant` | character variable              | Sabotage: recruit a claimant                         |
| `planning_to_cause_feud_fight`  | character variable              | Sabotage: start a fight                              |
| `removed_as_officiant`          | character flag                  | Officiant was replaced                               |
| `has_backup_officiant`          | activity variable               | A backup officiant was set                           |
| `busy_in_coronation_event`      | character flag                  | Prevents event overlap during ceremony               |

---

## Interactions & Activities

### Interaction: `coronation_invite_to_activity_interaction`

**File:** `common/character_interactions/00_agot_coronation_interactions.txt`

A simple diplomacy interaction to invite characters to an ongoing coronation.
Shown only when:

- The actor has an involved activity
- That activity is `activity_agot_coronation`
- The activity has not started its active phase yet
- The recipient can join the activity

```pdx
is_shown = {
    exists = scope:actor.involved_activity
    scope:actor = scope:actor.involved_activity.activity_host
    scope:actor.involved_activity = {
        is_current_phase_active = no
        has_activity_type = activity_agot_coronation
    }
    scope:recipient = { can_join_activity = scope:actor.involved_activity }
}
```

### Activity: `activity_agot_coronation`

**File:** `common/activities/activity_types/agot_coronation.txt`

**Cost:** 100 gold base + 25 \* `activity_cost_scale_by_tier`. Free for AI.
Option costs are additional (pomp: 40/80/120/240; entertainment and food reuse
wedding option costs: 20/60/180 each).

**Province selection:** Favors Red Keep (150/200/300 by tier), Great Sept of
Baelor (+150), Starry Sept (+150), Pyke (+300), holy sites (+50), capital (+75),
royal gardens and leisure palaces (30-125 by tier).

**Special guests:**

| Key                    | Required | Description                                                                                               |
| ---------------------- | -------- | --------------------------------------------------------------------------------------------------------- |
| `coronation_target`    | yes      | The ruler being crowned (always `root`)                                                                   |
| `coronation_officiant` | yes      | The character who crowns; must share faith/HoF with host, be adult, and meet standard availability checks |

**Phases:**

1. **`coronation_phase_ceremony`** (order 1): 75-day duration. Weekly pulse
   fires `coronation_ceremony_ongoing_event_pulse`. On end, host gets
   `coronation.0002` for the ceremony proper.
2. **`coronation_phase_homage`** (order 2): Short 5-10 day phase. Fires
   `coronation.0150` (homage/oath) and `coronation.0151` (attendee reactions).

**Guest configuration:**

- `max_guests = 400`
- Default invites include: Head of Faith, Kingsguard, spouses, player heir,
  friends, close family, vassals, high lords, fellow vassals, courtiers, guests
- Optional invites: minor lords, rivals, extended family, neighboring rulers, MP
  players

**Host intents:** `reduce_stress_intent`, `promote_rule_intent`,
`raise_dynasty_prestige_intent`, `murder_attendee_intent`,
`woo_attendee_intent`, `befriend_attendee_intent`

**Guest intents:** `reduce_stress_intent`, `raise_dynasty_prestige_intent`,
`legitimize_bastard_intent`, `vie_for_council_seat_intent`,
`sabotage_coronation_intent`, `murder_attendee_intent`, `woo_attendee_intent`,
`befriend_attendee_intent`, `diplomatic_intent`

**Invalidation causes:** Coronation target dies, is imprisoned, loses land, goes
to war, becomes incapable, loses tier requirements, or abdicates. All cases
refund gold via `coronation_gold_recoup_value`.

---

## Events

### AGOT-Specific Coronation Events (`coronation` namespace)

**File:**
`events/activities/agot_coronation_activity/agot_coronation_events.txt`

This is a very large file (430KB+). Key event ranges:

| Event ID               | Description                                     |
| ---------------------- | ----------------------------------------------- |
| `coronation.0001`      | Arrival event for all attendees                 |
| `coronation.0002`      | Host: Begins the ceremony chain                 |
| `coronation.0006`      | War invalidation -- chance to crown immediately |
| `coronation.0009`      | Government change handler                       |
| `coronation.0100`      | Phase 1 active -- ceremony begins               |
| `coronation.0150`      | Homage phase -- oath event                      |
| `coronation.0151`      | Attendee reactions to oath                      |
| `coronation.0154`      | Host: End of homage phase                       |
| `coronation.0900-0999` | Invalidation/death events                       |
| `coronation.1000`      | Relative criticizes your options                |
| `coronation.1010`      | Diplomacy/seduce opportunity                    |
| `coronation.1030`      | Good/bad omen                                   |
| `coronation.1120`      | Bastard legitimization intent                   |
| `coronation.1130-1143` | Sabotage intent chain                           |
| `coronation.1150`      | Seduction intent scouting                       |
| `coronation.1160`      | Gatecrashers                                    |
| `coronation.1190`      | Religious guest complaints                      |
| `coronation.1210`      | Political talk                                  |
| `coronation.2000-2015` | Claimant disruption chain                       |

### Decision Events (`coronation_decision` namespace)

**File:** `events/agot_events/agot_coronation_decision_events.txt`

| Event ID                   | Description                                                                                                                               |
| -------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| `coronation_decision.0001` | Choose officiant (uses `agot_character_selection_three_options` widget)                                                                   |
| `coronation_decision.0002` | Choose crown (uses `agot_artifact_selection` widget, or `ai_choose_crown_effect` for AI)                                                  |
| `coronation_decision.0003` | The crowning itself -- different desc paths for officiant/self-crowner/guest/ruler with or without crown, and Iron Throne vs other realms |

### Crown Commission Events (`agot_activity_commission_crown` namespace)

**File:**
`events/activities/agot_coronation_activity/agot_coronation_crown_commission_events.txt`

| Event ID                              | Description                                                                                                                                                 |
| ------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `agot_activity_commission_crown.0001` | Commission a new crown during coronation or via decision. Uses `agot_artifact_selection` widget. Creates one of 60+ dynasty/realm/religion-specific crowns. |

### On-Action Phase Events

**File:** `common/on_action/activities/coronation_on_actions.txt`

| On-Action                             | Phase         | Description                                                                                                                                            |
| ------------------------------------- | ------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `coronation_first_phase_host_events`  | Prelude       | 30+ random events for the host                                                                                                                         |
| `coronation_first_phase_guest_events` | Prelude       | 30+ random events for guests, plus intent events                                                                                                       |
| `coronation_second_phase_events`      | Ceremony      | Scripted chain (not random): ceremony begins -> clergy approval -> nobility approval -> popular approval -> blessing -> anointment -> crowning -> oath |
| `coronation_third_phase_host_events`  | Banquet       | 70+ random feast-style events                                                                                                                          |
| `coronation_third_phase_guest_events` | Banquet       | 70+ random events for guests                                                                                                                           |
| `coronation_failed_oath_on_action`    | Post-activity | Triggers `coronation_events.0150` after 3 days                                                                                                         |

**Ceremony chain (Phase 2) -- always fires in order for host:**

1. `coronation_events.0205` -- ceremony begins
2. `coronation_events.6120` -- clergy approval
3. `coronation_events.6121` -- nobility approval
4. `coronation_events.6122` -- popular approval
5. `coronation_events.6123` -- guest summary of approvals
6. `coronation_events.6110` -- blessing of regnal artifact
7. `coronation_events.6130` -- anointment
8. `coronation_events.6000` / `6001` / `6002` -- being crowned / crowning
   yourself / enthronement with regalia
9. `coronation_events.0100` -- oath event

**AGOT-specific on-actions:**

**File:** `common/on_action/activities/agot_coronation_on_actions.txt`

| On-Action                                 | Description                                                                                                        |
| ----------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| `coronation_ceremony_ongoing_event_pulse` | Weekly random events during ceremony phase (coronation.1000, 1010, 1030, 1120, 1130, 1135, 1150, 1160, 1190, 1210) |
| `on_government_change`                    | Fires `coronation.0009`                                                                                            |

---

## Sub-Mod Recipes

### Recipe 1: Add a Custom Crown for a New Dynasty

Create a trigger and artifact creation effect, then register them in the
commission event.

```pdx
# common/scripted_triggers/my_mod_crown_triggers.txt
agot_my_dynasty_crown_trigger = {
    dynasty ?= dynasty:dynn_MyDynasty
    highest_held_title_tier >= tier_kingdom
}
```

```pdx
# common/scripted_effects/my_mod_crown_effects.txt
agot_create_artifact_my_dynasty_crown_effect = {
    $OWNER$ = {
        create_artifact = {
            name = my_dynasty_crown_name
            description = my_dynasty_crown_desc
            type = helmet
            visuals = helmet_royal_01  # use an appropriate visual key
            modifier = my_dynasty_crown_modifier
            save_scope_as = newly_created_artifact
        }
        scope:newly_created_artifact = {
            set_variable = my_dynasty_crown_artifact
        }
    }
}
```

Then add to the AI crown scoring in a separate file or override:

```pdx
# Patch ai_choose_crown_effect or add to agot_coronation_crown_commission_events
if = {
    limit = {
        root = { agot_my_dynasty_crown_trigger = yes }
    }
    agot_create_artifact_my_dynasty_crown_effect = { OWNER = this }
    root = {
        add_to_variable_list = {
            name = possible_artifacts
            target = scope:newly_created_artifact
        }
        if = {
            limit = { NOT = { has_variable = selected_artifact } }
            set_variable = { name = selected_artifact value = scope:newly_created_artifact }
        }
    }
}
```

### Recipe 2: Add a Custom Coronation Event to the Ceremony Phase

Add your event to `coronation_ceremony_ongoing_event_pulse` via a load-order
override:

```pdx
# common/on_action/activities/zz_my_mod_coronation_on_actions.txt
coronation_ceremony_ongoing_event_pulse = {
    trigger = {
        NOT = { has_character_flag = busy_in_coronation_event }
    }
    random_events = {
        chance_to_happen = 100
        50 = my_coronation_event.0001
    }
}
```

Your event should be `type = activity_event` and should set/clear
`busy_in_coronation_event`:

```pdx
my_coronation_event.0001 = {
    type = activity_event
    title = my_coronation_event.0001.t
    desc = my_coronation_event.0001.desc
    theme = coronation_ceremony_activity

    trigger = {
        this = scope:host
        NOT = { has_character_flag = busy_in_coronation_event }
    }

    immediate = {
        set_character_flag = busy_in_coronation_event
    }

    option = {
        name = my_coronation_event.0001.a
        # your effects here
    }

    after = {
        remove_character_flag = busy_in_coronation_event
    }
}
```

### Recipe 3: Change Officiant Rewards Based on Custom Conditions

Override `coronation_decision.0003` to add a new reward branch. Insert your
condition before the `else` fallback:

```pdx
# The officiant is a Maester
else_if = {
    limit = {
        scope:officiant = {
            has_trait = maester
        }
    }
    add_legitimacy = medium_legitimacy_gain
    add_learning_skill = 2
}
```

### Recipe 4: Grant a Custom Modifier After Coronation

Hook into the `on_complete` of the activity, or add to
`disburse_agot_coronation_activity_rewards`:

```pdx
# In your own scripted_effects file, call after the main rewards
scope:host = {
    if = {
        limit = {
            has_title = title:h_the_iron_throne
            scope:activity.special_guest:coronation_officiant ?= faith.religious_head
        }
        add_character_modifier = {
            modifier = blessed_by_the_seven_modifier
            years = 10
        }
    }
}
```

---

## Pitfalls

1. **DLC gate:** The entire AGOT coronation system is disabled when
   `has_dlc_feature = coronations` is true. If you are testing and have the
   Roads to Power / Chapter III DLC, AGOT will use vanilla coronation laws
   (`crowned_king`, `crowned_emperor`, `uncrowned`) instead of the custom
   activity. Your sub-mod must check `agot_uses_agot_coronations_trigger` before
   adding features.

2. **Wedding option category reuse:** Entertainment and food options use
   `wedding_option_entertainment` / `wedding_option_food` and
   `wedding_entertainment_good` / `wedding_food_good` etc. -- these are NOT
   coronation-specific categories. Do not create options with
   `coronation_option_entertainment`; they will not match the reward checks.

3. **`busy_in_coronation_event` flag:** All events in the ceremony weekly pulse
   must respect this flag in their `trigger` block and clean it up in `after`.
   Failing to check it causes event overlap; failing to remove it soft-locks the
   ceremony.

4. **Officiant special guest is required:** If the `coronation_officiant`
   special guest cannot be filled (refuses, dies, etc.), the entire activity is
   invalidated. Sub-mods adding custom officiant restrictions must ensure at
   least one eligible candidate always exists.

5. **Crown artifact slot type:** Crown detection checks
   `artifact_slot_type = helmet`, not a custom crown type. Any artifact in the
   helmet slot will appear in the crown selection UI. If your sub-mod adds
   non-crown helmets, they will show up in the coronation crown picker.

6. **Self-crowning legitimacy penalty:** Choosing to crown yourself
   (`crowning_self` flag) costs `major_legitimacy_loss` immediately at decision
   time. This is separate from the rewards in `coronation_decision.0003`.
   Sub-mods should not remove this flag prematurely or the event chain's desc
   triggers will break.

7. **`scope:coronation_venue` vs activity location:** Venue bonus checks use
   `scope:coronation_venue`, which is the province object. Building checks use
   `has_building` / `has_building_or_higher` directly on this scope. Do not
   confuse with `scope:activity.activity_location` which is the barony-level
   title.

8. **AI crown scoring is purely additive:** The `ai_choose_crown_effect` uses
   `order_by` with additive `if` blocks. If multiple crowns match at the same
   score, the first in iteration order wins. There is no tie-breaking beyond
   insertion order.

9. **On-action file naming:** AGOT disables several vanilla events in the
   on-actions by commenting them out (marked `#AGOT Disabled`). These include
   Iberian/Persian struggle events (`coronation_events_klank.1009`, `1010`),
   hashish events (`ach_coronation.0027`), choir events
   (`coronation_events.1031`), and faith warrior events (`ach_coronation.0017`).
   Sub-mods should not re-enable these unless they add the required Westerosi
   equivalents.

10. **Accolade glory checks reuse wedding option IDs:** The
    `accolades_activity_complete_coronation_glory_effect` checks for
    `wedding_entertainment_good`, `wedding_food_good`, and
    `coronation_pomp_grandiose` as the "perfect" combination. This is
    intentional, not a bug -- the activity reuses the vanilla wedding
    food/entertainment system.
