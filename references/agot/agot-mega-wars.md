# AGOT: Mega Wars

## Overview

Mega Wars are AGOT's custom large-scale multi-front conflict system, designed to
simulate realm-shattering wars like Robert's Rebellion, the Dance of the
Dragons, or Blackfyre Rebellions. When a war meets certain tier and realm-size
thresholds, the standard CK3 war system is augmented with a Mega War layer that
forces every vassal in the realm to **choose a side**: loyalist, rebel, neutral,
or independence.

The system is built on two paired **story cycles** (`story_agot_mw_crown` and
`story_agot_mw_rebel`) that track all participants, manage temporary vassalage
reshuffling, and handle war resolution and post-war traitor punishment. The
primary author of the system is TitanRogue.

### Two Modes

| Mode                       | Variable                    | Trigger conditions                                                                                             | Neutral stance                          | Realm break-up |
| -------------------------- | --------------------------- | -------------------------------------------------------------------------------------------------------------- | --------------------------------------- | -------------- |
| **Regular** (`mw_regular`) | `mw_mode = flag:mw_regular` | Empire+ tier attacker or defender; kingdom+ tier vassal rebelling or claiming                                  | Yes (if `mw_realm_break_up = flag:yes`) | Yes            |
| **Lite** (`mw_lite`)       | `mw_mode = flag:mw_lite`    | Kingdom-tier internal conflicts; admin governments with realm_size >= 30; feudal realms with realm_size 35-149 | No (neutral blocked)                    | No             |

Lite mode is checked first; if it matches, regular mode is skipped. This
prevents smaller civil wars from triggering full realm breakup.

### Internal vs. External Wars

The variable `mw_source` distinguishes:

- `flag:mw_internal` -- vassal rebellions, faction wars, independence wars
  within a realm.
- `flag:mw_external` -- invasions from outside the realm (claim wars,
  `agot_targaryen_exile_invasion_war_cb`, `faegon_invasion_war_cb`,
  `agot_blackfyre_claim`, `dragon_subjugation_cb`, `vassalization_cb`,
  `tribal_subjugation_cb`).

---

## Key Concepts

### Side Assignment and the "Call the Banners" Event

When a war triggers a Mega War (via the `on_war_started` on_action in
`agot_war_on_actions.txt`), event `agot_mega_wars.0002` fires for the crown,
then `agot_mega_wars.0003` fires for each eligible vassal. Each vassal chooses
one of four stances:

1. **Loyalist** -- joins the crown side in all MW wars. Added to
   `mw_loyalist_list`.
2. **Neutral** -- stays out of direct combat; becomes temporarily independent.
   Added to `mw_neutral_list`. Only available in regular mode with realm
   break-up enabled.
3. **Rebel** -- joins the rebel leader's side. Added to
   `mw_rebel_supporter_list` on the rebel's story.
4. **Independence** -- declares independence during the war. Added to
   `mw_independence_rebel_leader_list`. Only available to empire-tier vassals or
   those with a kingdom+ liege already on the independence list.

AI stance selection uses `agot_mw_choose_stance_modifier`, which weighs opinion,
family relations, alliances, historical house loyalties
(`agot_historical_loyalty_targaryen`, `agot_historical_loyalty_blackfyre`), and
personal relations (friends, lovers).

### Temporary Vassalage and Realm Break-Up

During a regular Mega War, the realm physically restructures:

- Loyalists become temporary vassals of the crown (or their `pre_war_liege` if
  already on the same side).
- Rebels become temporary vassals within the rebel faction structure (only if
  `mw_rebel_may_vassalize = flag:yes`; currently disabled by default).
- Neutrals become **temporarily independent** via `agot_mw_become_independent`.

The `pre_war_liege` variable is set on each vassal to record their original
liege for post-war realm reconstruction.

### Story Cycles as Data Stores

The two story cycles are the backbone:

**`story_agot_mw_crown`** (owned by the defending ruler / crown):

- `mw_loyalist_list` -- all loyalist vassals
- `mw_neutral_list` -- all neutral vassals
- `mw_rebel_leader_list` -- all rebel leaders (there can be multiple)
- `mw_independence_rebel_leader_list` -- vassals who declared independence
- `mw_wars` -- list of all war scopes connected to this MW
- `mw_title` -- the primary title being contested
- `mw_mode` -- `flag:mw_regular` or `flag:mw_lite`
- `mw_realm_break_up` -- `flag:yes` or `flag:no`
- `mw_status` -- `flag:initialized` -> `flag:on_going` -> `flag:ending`

**`story_agot_mw_rebel`** (owned by each rebel leader):

- `mw_rebel_supporter_list` -- supporters of this rebel leader
- `mw_wars` -- wars this rebel is part of
- `mw_crown_story_var` -- reference back to the crown's story cycle
- `mw_war_cb` -- the CB type flag (`flag:claim_cb`, `flag:independence_war`,
  `flag:rebellion_war`, `flag:dissolution_war`, `flag:succession_war`)
- `mw_source` -- `flag:mw_internal` or `flag:mw_external`
- `mw_outcome` -- `flag:pending` -> `flag:rebels_won` / `flag:crown_won` /
  `flag:white_peace` / `flag:invalidated`
- `mw_status` -- mirrors the crown story status
- `mw_faction_members_list` -- faction members if war originated from a faction

### Dragon Integration

Mega Wars interact with the dragon system indirectly:

- `dragon_subjugation_cb` is recognized as a valid external war CB that can
  trigger a mega war (see `agot_mw_is_external_war_trigger`).
- Dragonstone gets special handling: the trigger
  `agot_mw_dragonstone_is_loyal_to_crown_trigger` forces child Targaryen rulers
  of Dragonstone to auto-join the crown side via `mw_is_loyal_to` +
  `mw_block_other_stances`.
- Dragon eggs and Valyrian steel are among artifacts that can be seized as
  post-war traitor punishment (`has_variable = dragon_egg` in
  `agot_mw_penalty_artifact_valuable_trigger`).

### Knighthood Integration

The Mega War system does not directly reference knighthood mechanics. However,
the `agot_revolt_war` CB (used for traitor punishment revolt wars) and the
overall war participation system interact with the broader AGOT combat framework
documented in `agot-knighthood.md`.

---

## AGOT Scripted API

### Key Triggers (from `00_agot_mega_wars_triggers.txt`)

| Trigger                                           | Scope                                                                        | Purpose                                                                                                                                 |
| ------------------------------------------------- | ---------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| `agot_mw_start_mw_base_trigger`                   | uses `scope:t_attacker`, `scope:t_defender`                                  | Base validity: not historical war, not blocked governments (ruins, NW, pirates, herder, etc.), at least one side is de jure independent |
| `agot_mw_start_regular_mw_trigger`                | `{ ATTACKER = ... DEFENDER = ... }`                                          | Full MW: empire+ tier major participant, or faction with kingdom+ members, or `agot_allow_mw` variable                                  |
| `agot_mw_start_lite_mw_trigger`                   | `{ ATTACKER = ... DEFENDER = ... }`                                          | Lite MW: attacker is inside defender's realm, defender has kingdom+ tier, realm_size thresholds                                         |
| `agot_mw_any_mw_allowed_trigger`                  | `{ ATTACKER = ... DEFENDER = ... }`                                          | OR of regular and lite triggers                                                                                                         |
| `agot_mw_is_external_war_trigger`                 | war scope                                                                    | Checks if attacker is outside defender's realm + specific CB types                                                                      |
| `agot_mw_crown_trigger`                           | character                                                                    | Character owns a `story_agot_mw_crown`                                                                                                  |
| `agot_mw_rebel_leader_trigger`                    | character                                                                    | Character owns a `story_agot_mw_rebel`                                                                                                  |
| `agot_mw_is_in_loyalist_list_trigger`             | `{ TARGET = ... }`                                                           | TARGET is in any crown's `mw_loyalist_list`                                                                                             |
| `agot_mw_is_in_neutral_list_trigger`              | `{ TARGET = ... }`                                                           | TARGET is in any crown's `mw_neutral_list`                                                                                              |
| `agot_mw_is_in_rebel_list_trigger`                | `{ TARGET = ... }`                                                           | TARGET is in any rebel's `mw_rebel_supporter_list`                                                                                      |
| `agot_mw_in_LIST_of_trigger`                      | `{ STORY_OWNER = ... TYPE = crown/rebel LIST_NAME = ... TARGET = ... }`      | Generic: check if TARGET is in a specific list of a specific story owner                                                                |
| `agot_mw_chars_on_opposite_sides`                 | `{ CHAR_1 = ... CHAR_2 = ... NEUTRAL_CHECK = yes/no LEADER_CHECK = yes/no }` | Are two characters on opposing sides?                                                                                                   |
| `agot_mw_chars_in_same_mw_trigger`                | `{ CHAR_1 = ... CHAR_2 = ... }`                                              | Are two characters participating in the same MW?                                                                                        |
| `agot_mw_show_stance_trigger`                     | `{ CHECK = loyalist/neutral/rebel/independence }`                            | Should this stance option appear in the choice event? Complex logic handling forced stances, imprisonment, faction membership, etc.     |
| `agot_mw_allow_realm_break_up_trigger`            | story scope                                                                  | Is realm break-up enabled for this MW?                                                                                                  |
| `agot_mw_is_torn_between_sides_trigger`           | character                                                                    | Delta between side values is within [-250, 250] and total > 400                                                                         |
| `agot_mw_count_choice_is_unlocked_trigger`        | character                                                                    | County-tier rulers need 12+ leverage or special relations to unlock side choice                                                         |
| `agot_mw_house_has_historical_loyality_to_tigger` | `{ TO_HOUSE = ... }`                                                         | House has `agot_historical_loyalty_targaryen` or `agot_historical_loyalty_blackfyre` modifier                                           |
| `agot_mw_has_claimant_trigger`                    | `{ CLAIMANT = ... HOLDER = ... }`                                            | Does the claimant have a claim on any of the holder's titles?                                                                           |
| `agot_mw_war_valid_during_megawar`                | war scope                                                                    | Should this war remain valid during an active MW?                                                                                       |

### Key Effects (from `00_agot_mega_wars_effects.txt`)

| Effect                                         | Purpose                                                                                                                                                                      |
| ---------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `agot_mw_scenario_crown_setup`                 | Initialize crown story for a scripted scenario. Params: `HELD_TITLE`, `MODE`, `REALM_BREAK_UP`                                                                               |
| `agot_mw_scenario_rebel_setup`                 | Initialize rebel story for a scripted scenario. Params: `HELD_TITLE`, `CASUS_BELLI`, `PRE_WAR_LIEGE`, `SOURCE`, `MODE`, `REALM_BREAK_UP`, `REBEL_MAY_VASSALIZE`, `MW_TARGET` |
| `agot_mw_add_character_to_mw_list`             | Add a character and all sub-vassals to a story's list. Params: `CHARACTER_SCOPE`, `STORY_SCOPE`, `LIST`, `PRE_WAR_LIEGE_SCOPE`                                               |
| `agot_mw_join_loyalists_effect`                | `{ RULER = ... CROWN = ... }` -- Adds ruler to loyalist list, handles temp vassalage                                                                                         |
| `agot_mw_stay_neutral_effect`                  | `{ RULER = ... CROWN = ... }` -- Adds ruler to neutral list, makes temporarily independent                                                                                   |
| `agot_mw_join_rebels_effect`                   | `{ RULER = ... REBEL_LEADER = ... }` -- Adds ruler to rebel supporter list                                                                                                   |
| `agot_mw_start_mid_war_effect`                 | Starts a MW mid-war (for consecutive wars during an ongoing MW)                                                                                                              |
| `agot_assign_temp_vassalage_effect`            | Complex vassalage reshuffling during side-joining                                                                                                                            |
| `agot_mw_become_independent`                   | Makes a character temporarily independent (removes from liege, keeps `pre_war_liege`)                                                                                        |
| `agot_mw_set_pre_war_liege`                    | Records original liege before MW reshuffling                                                                                                                                 |
| `agot_mw_rebuild_realm_effect`                 | `{ REBUILD_MODE = ... TARGET = ... }` -- Post-war realm reconstruction, returns vassals to original lieges                                                                   |
| `agot_mw_set_mw_outcome`                       | `{ SCENARIO = victory/white_peace/invalidated }` -- Sets outcome on the rebel story                                                                                          |
| `agot_mw_fetch_crown_story_from_char_scope`    | `{ CHECK_CHAR = ... }` -- Finds and saves the crown story scope for a given character                                                                                        |
| `agot_mw_fetch_rebel_story_from_char_scope`    | `{ CHECK_CHAR = ... }` -- Finds and saves the rebel story scope for a given character                                                                                        |
| `agot_mw_generate_traitor_list`                | Generates the `mw_traitors_list` for post-war punishment                                                                                                                     |
| `agot_mw_gui_punish_traitor_effect`            | `{ CROWN_TARGET = ... TRAITOR_TARGET = ... }` -- Executes chosen punishments on a traitor                                                                                    |
| `agot_mw_clear_data_effect`                    | Removes MW variables from a character (`pre_war_liege`, etc.)                                                                                                                |
| `agot_mw_faction_war_effect`                   | Converts a faction war into a MW-compatible war                                                                                                                              |
| `agot_mw_faction_war_claimant_effect`          | Converts a claimant faction war into a MW-compatible war                                                                                                                     |
| `agot_mw_cb_new_ruler_effect`                  | Handles title transfer after rebels win                                                                                                                                      |
| `agot_mw_change_iron_throne_holder_effect`     | Special handling for Iron Throne transfer                                                                                                                                    |
| `agot_mw_send_event_to_ruler_or_diarch_effect` | Routes the stance choice event to diarch if ruler has active diarchy and is imprisoned/minor                                                                                 |
| `agot_mw_betray_loyality_var_effect`           | `{ TARGET = ... }` -- If ruler had `mw_is_loyal_to` pointing elsewhere, mark as betrayer                                                                                     |

### Maintenance Triggers (on_action title transfers)

These triggers in the triggers file handle on_action events when titles change
hands during a MW:

| Trigger                              | Purpose                                                                 |
| ------------------------------------ | ----------------------------------------------------------------------- |
| `mw_on_action_crown_trigger`         | Detects when the crown's MW title changes hands                         |
| `mw_on_action_rebel_leader_trigger`  | Detects when a rebel leader loses all land                              |
| `mw_on_action_loyalist_trigger`      | Transfers new holder into loyalist list if previous holder was loyalist |
| `mw_on_action_neutral_trigger`       | Transfers new holder into neutral list                                  |
| `mw_on_action_rebel_trigger`         | Transfers new holder into rebel list                                    |
| `mw_on_action_pre_war_liege_trigger` | Updates `pre_war_liege` when titles transfer                            |
| `mw_action_remove_from_list_trigger` | Removes characters who drop below county tier from lists                |

---

## Casus Belli Types

All defined in `00_agot_casus_belli_mega_wars.txt`:

### `agot_independence_war`

- **Group:** `independence`
- **Purpose:** MW-specific independence CB for vassals who chose independence
  stance.
- **Key logic:** Checks `pre_war_liege` to validate target; defender must be the
  crown. `valid_to_start = { is_ai = no }` -- event-fired only.
- **On victory:** Attacker becomes truly independent
  (`remove_variable = pre_war_liege`), all empire-tier rebel supporters also
  become independent. Crown loses one level of crown authority.
- **War score:** `attacker_wargoal_percentage = 0.8`,
  `max_attacker_score_from_battles = 100`,
  `max_defender_score_from_battles = 50`.

### `agot_reconquest_war`

- **Group:** `vassalization`
- **Purpose:** Iron Throne holder re-subjugates independent empire-tier realms
  in Westeros.
- **Restricted to:** `lp_feudal_government` with
  `primary_title = title:h_the_iron_throne`.
- **Target:** Independent empire-tier rulers whose capital is in
  `world_westeros_seven_kingdoms`.
- **On victory:** Defender becomes vassal of attacker via `swear_fealty`.

### `agot_rebellion_war`

- **Group:** `civil_war`
- **Purpose:** Generic rebellion CB used when rebels win and depose the crown.
- **No white peace.** No target titles.
- **On victory:** Triggers `agot_mega_wars.0500` (the post-war resolution event
  chain). All defenders imprisoned.
- **War score:** `max_attacker_score_from_battles = 200`,
  `max_defender_score_from_battles = 200`.

### `agot_revolt_war`

- **Group:** `civil_war`
- **Purpose:** Revolt war started as aftermath of MW (traitors revolting against
  punishment).
- **`valid_to_start = { always = no }`** -- event-only CB.
- **No white peace.**
- **On defeat:** Each attacker is punished using their stored punishment
  variables via `agot_mw_gui_punish_traitor_effect`.

### `agot_liberty_faction_war`

- **Group:** `civil_war`
- **Purpose:** MW version of the liberty faction war.
- **On victory:** Crown authority reduced by one level. All faction members get
  a favor hook on defender.
- **Should invalidate:** If attacker's liege changes or if the linked crown
  story owner is not the defender.

### `agot_claimant_faction_war`

- **Group:** `civil_war`
- **Purpose:** MW version of the claimant faction war.
- **Target titles:** `claim`
- **On victory:** Calls `on_claimant_faction_war_win_common` to transfer target
  titles to the claimant.

### `agot_bastard_claimant_war`

- **Group:** `civil_war`
- **Purpose:** War where a bastard presses a claim on the throne.
- **Invalidates:** If the claimant dies.
- **On victory:** Claimant gets target titles; attacker gets
  `courtier_installed_on_iron_throne` hook.

### `agot_succession_war`

- **Group:** `claim`
- **Purpose:** Succession crisis war (e.g., disputed succession).
- **`valid_to_start = { always = no }`** -- requires `succession_war_claimant`
  flag.
- **No white peace.**
- **On victory:** All of defender's titles transferred to claimant. Usurper
  artifacts returned.
- **On primary attacker death:** `invalidate` (unlike other MW CBs which use
  `inherit`).

---

## Decisions

### `agot_mega_war_declare_independence_decision`

**File:** `00_agot_mega_wars_decisions.txt`

Allows a **neutral** vassal with an **empire-tier** primary title to declare
independence during an active Mega War.

```pdx
is_shown = {
    NOT = { has_character_flag = mw_declared_independence }
    exists = var:pre_war_liege
    NOT = { is_at_war_with = var:pre_war_liege }
    var:pre_war_liege = {
        any_owned_story = {
            story_type = story_agot_mw_crown
            is_target_in_variable_list = { name = mw_neutral_list target = root }
        }
    }
    primary_title.tier = tier_empire
    NOT = { any_character_war = { using_cb = agot_independence_war } }
    is_ai = no
}
```

**Effect:** Sets `mw_declared_independence` flag (10-day cooldown) and fires
`agot_mega_wars.0010`, which adds the ruler to
`mw_independence_rebel_leader_list` and notifies the crown via
`agot_mega_wars.0011`.

**AI:** `ai_potential = { always = no }` -- AI independence is handled through
the stance choice system, not this decision.

---

## Events & Story Cycles

### Event Flow

#### Initialization (`on_war_started` -> `agot_mega_war_action`)

1. `agot_war_on_actions.txt` fires `agot_mega_war_action` when a war starts and
   `agot_mw_any_mw_allowed_trigger` passes.
2. Crown story (`story_agot_mw_crown`) is created or updated. Rebel story
   (`story_agot_mw_rebel`) is created.
3. Key variables set: `mw_mode`, `mw_realm_break_up`, `mw_source`, `mw_war_cb`,
   `mw_title`, `mw_rebel_may_vassalize`.
4. All eligible vassals are sorted into participants list. Each gets
   `pre_war_liege` set.
5. Vassals become temporarily independent (`agot_mw_become_independent`).
6. Crown receives `agot_mega_wars.0002` ("The Realm is at War").

#### Stance Choice (`agot_mega_wars.0003`)

The main event for each vassal. Fires for all vassals with
`highest_held_title_tier > tier_barony` who are not already on the rebel
supporter list.

Four options:

- **Option A (Loyalist):** Calls `agot_mw_join_loyalists_effect`. In lite mode,
  also auto-joins wars.
- **Option B (Neutral):** Calls `agot_mw_stay_neutral_effect`. Blocked in lite
  mode.
- **Option C (Rebel):** Calls `agot_mw_join_rebels_effect`.
- **Option D (Independence):** Only for empire-tier or those under an
  independence leader. Creates new rebel front.

Special handling for **diarchs**: if a ruler has an active diarchy (imprisoned
or minor), the stance event routes to the diarch via
`agot_mw_send_event_to_ruler_or_diarch_effect`. The actual ruler then gets
`agot_mega_wars.0005` as notification.

Pre-determined stances: Characters with `mw_is_loyal_to` variable pointing to
crown or rebel leader will have other options blocked (combined with
`mw_block_other_stances`). Faction members are forced to join the rebel side.
Characters whose titles are targeted by rebels can only join loyalists.
Imprisoned characters can only stay neutral.

#### War Joining (`agot_mega_wars.0004`)

After choosing a side, kingdom+ tier vassals are prompted to actively join the
wars on their side. This event offers "Join the war" vs. "Don't join the war."

#### Independence Declaration (`agot_mega_wars.0010`, `0011`)

Fired by the independence decision or stance choice. Adds ruler to
`mw_independence_rebel_leader_list`. Crown notified via `agot_mega_wars.0011`.

#### Mid-War Claimant Switch (`agot_mega_wars.0020`, `0021`)

Event `agot_mega_wars.0020` handles when a claimant (the beneficiary of a
claimant war) is asked to choose sides. The claimant cannot join against their
own cause (gets `mw_claimant_had_0020` flag, forcing neutral).

### War Resolution

#### Outcome Setting (`agot_mw_set_mw_outcome`)

Called from `agot_war_on_actions.txt` on war end. Sets `mw_outcome` on the rebel
story to one of:

- `flag:rebels_won`
- `flag:crown_won`
- `flag:white_peace`
- `flag:invalidated`

#### Rebel Victory Chain (`agot_mega_wars.0500`)

The primary post-war event when rebels win. Fired by `agot_rebellion_war`'s
`on_victory`. The rebel leader (now `scope:choosing_ruler`) decides what to do:

- Choose to take the crown title themselves.
- Offer it to a supporting Lord Paramount.
- The event generates `target_titles` from the defender's primary title
  hierarchy.

This branches into `agot_mega_wars.0501`-`0506` for various outcomes (title
transfer, LP offers, Dragonstone handling, etc.).

#### Event `agot_mega_wars.0510`

Handles the case where a Lord Paramount was offered the crown and may accept or
reject.

### Post-War Traitor Punishment

#### Traitor List Generation (`agot_mw_generate_traitor_list`)

After a side wins, the winner gets a `mw_traitors_list` containing all vassals
who fought on the losing side.

#### Punishment Event (`agot_mega_wars.0600`)

Entry point for the winner to punish traitors. Opens the royal court if
available.

#### Court Punishment UI (`agot_mega_wars.0601`)

A **court event** with a custom widget (`agot_mw_punishment_summary`). For each
traitor in `mw_traitors_list`, the winner can choose from:

| Punishment            | Trigger                                    | Variable              |
| --------------------- | ------------------------------------------ | --------------------- |
| Take main titles      | `agot_mw_penalty_main_titles_trigger`      | `take_main_titles`    |
| Take secondary titles | `agot_mw_penalty_secondary_title_trigger`  | N/A (specific titles) |
| Take entire demesne   | `agot_mw_penalty_entire_demesne_trigger`   | `take_entire_demesne` |
| Take half demesne     | `agot_mw_penalty_half_demesne_trigger`     | `take_half_demesne`   |
| Take hostages         | `agot_mw_penalty_hostage_trigger`          | `take_hostage`        |
| Seize artifacts       | `agot_mw_penalty_artifact_trigger`         | `take_artifact`       |
| Execute traitor       | Available always                           | `execution_traitor`   |
| Execute family        | `agot_mw_penalty_execution_family_trigger` | `execution_family`    |
| Execute house members | `agot_mw_penalty_execution_house_trigger`  | `execution_house`     |
| Send to the Wall      | `agot_mw_penalty_wall_trigger`             | `sent_to_wall`        |
| Expel family          | `agot_mw_penalty_expel_family_trigger`     | `expel_family`        |
| Expel house           | `agot_mw_penalty_expel_house_trigger`      | `expel_house`         |
| Delegate to LP        | Hegemon only, traitor not direct vassal    | N/A                   |

An **acceptance indicator** (`acceptance_indicator` variable, 0-100+) grades the
severity:

- 100+ = Mild
- 80-99 = Adequate
- 60-79 = Moderate
- 30-59 = Harsh
- 1-29 = Very Harsh
- 0 or below = Tyrannic

High Septons cannot have titles seized (blocked by `agot_is_high_septon`).

#### AI Punishment (`agot_mega_wars.0605`)

The AI auto-punishes via `agot_mw_aftermath_ai_punishes_effect`, which selects
punishments algorithmically.

#### Revolt Against Punishment (`agot_mega_wars.0602`-`0604`)

Traitors can refuse punishment and start an `agot_revolt_war`. Events handle
assembling the revolt coalition and offering other punished lords the chance to
join.

### Realm Reconstruction

The `agot_mw_rebuild_realm_effect` (called from story cycle `on_end`) returns
all vassals to their `pre_war_liege`, clears MW variables, and restores the
realm hierarchy. Vassal contracts are preserved via
`agot_mw_save_vassal_contract_data` / `agot_mw_reset_vassal_contract`.

### Story Cycle Lifecycle

**`story_agot_mw_crown`:**

- `on_setup`: Sets `mw_status = flag:initialized`.
- Daily `effect_group` (1-day): Transitions `initialized` -> `on_going` (adds
  participants to wars). Checks for fallback end if no rebel leaders remain or
  crown is a dummy character.
- `on_owner_death`: Transfers to `primary_heir`, or `mw_title.holder`, or
  invalidates.
- `on_end`: Calls `agot_mw_rebuild_realm_effect` for each rebel leader,
  rebuilding the realm.
- Ending `effect_group` (17-day): When `mw_status = flag:ending`, calls
  `end_story`.

**`story_agot_mw_rebel`:**

- `on_setup`: Sets `mw_status = flag:initialized`, `mw_outcome = flag:pending`.
- Daily `effect_group` (2-day init): Transitions `initialized` -> `on_going`.
- Daily `effect_group` (1-day): Checks if war no longer exists or rebel is dummy
  -> sets `mw_outcome = flag:invalidated`. When `mw_status = flag:ending`,
  removes self from crown's `mw_rebel_leader_list`, adds to
  `mw_rebel_leader_backup_list`, ends both stories if no rebel leaders remain.
- Punishment fallback `effect_group` (3-day): Handles postponed punishment when
  story couldn't fire it immediately.
- `on_owner_death`: Transfers to `player_heir`, `primary_heir`, or random rebel
  supporter.
- `on_end`: Removes `mw_is_rebel_leader` from story owner.

---

## Sub-Mod Recipes

### Recipe 1: Force a Specific Vassal to Join Crown Side

Use the `mw_is_loyal_to` variable combined with `mw_block_other_stances` before
the MW event fires. The AGOT code checks these during `agot_mega_wars.0003`.

```pdx
# In an on_action or event that fires before agot_mega_wars.0003:
scope:target_vassal = {
    set_variable = {
        name = mw_is_loyal_to
        value = scope:crown_character
    }
    set_variable = {
        name = mw_block_other_stances
        value = yes
    }
}
```

This is exactly how Dragonstone is handled for child Targaryen rulers.

### Recipe 2: Create a Custom Scripted Mega War (Scenario Setup)

For a bookmark or historical event that should start as a Mega War:

```pdx
# Step 1: Set up each rebel leader
agot_mw_scenario_rebel_setup = {
    HELD_TITLE = title:e_the_north
    CASUS_BELLI = agot_independence_war
    PRE_WAR_LIEGE = title:h_the_iron_throne.holder
    SOURCE = flag:mw_internal
    MODE = flag:mw_regular
    REALM_BREAK_UP = flag:yes
    REBEL_MAY_VASSALIZE = flag:no
    MW_TARGET = title:h_the_iron_throne.holder
}

# Step 2: Set up the crown
agot_mw_scenario_crown_setup = {
    HELD_TITLE = title:h_the_iron_throne
    MODE = flag:mw_regular
    REALM_BREAK_UP = flag:yes
}

# Step 3: Add vassals to lists
agot_mw_add_character_to_mw_list = {
    CHARACTER_SCOPE = character:Stark_12
    STORY_SCOPE = scope:mw_rebel_story
    LIST = mw_rebel_supporter_list
    PRE_WAR_LIEGE_SCOPE = title:h_the_iron_throne.holder
}

agot_mw_add_character_to_mw_list = {
    CHARACTER_SCOPE = character:Lannister_5
    STORY_SCOPE = scope:mw_crown_story
    LIST = mw_loyalist_list
    PRE_WAR_LIEGE_SCOPE = title:h_the_iron_throne.holder
}
```

### Recipe 3: Add a New External CB That Triggers Mega Wars

Add your CB to the `agot_mw_is_external_war_trigger` in
`00_agot_mega_wars_triggers.txt`:

```pdx
agot_mw_is_external_war_trigger = {
    # ... existing checks ...
    OR = {
        # ... existing CB checks ...
        scope:war ?= { using_cb = my_custom_invasion_cb }  # Add your CB here
    }
}
```

### Recipe 4: Check if a Character Is in an Active Mega War

```pdx
# Check if root is participating in any MW
trigger = {
    agot_mw_is_in_realm_at_megawar = yes
}

# Check if root is specifically a loyalist
trigger = {
    agot_mw_is_in_loyalist_list_trigger = { TARGET = root }
}

# Check if root is the crown or rebel leader
trigger = {
    OR = {
        agot_mw_crown_trigger = yes
        agot_mw_rebel_leader_trigger = yes
    }
}
```

### Recipe 5: Add Custom Post-War Punishment

To add a new punishment option, you would need to:

1. Create a new trigger in the triggers file (following the pattern of
   `agot_mw_penalty_*_trigger`).
2. Add the punishment variable handling in `agot_mw_gui_punish_traitor_effect`.
3. Add the GUI button in the `agot_mw_punishment_summary` widget.
4. Update `agot_mw_has_any_punishment_variable_trigger` to include your new
   variable.
5. Update the acceptance indicator calculation.

---

## Pitfalls

1. **Do NOT modify `agot_mega_wars.0003` triggers directly.** The event header
   explicitly warns: "Please do NOT modify triggers in this event at all!" Use
   `mw_is_loyal_to` and `mw_block_other_stances` variables instead. Contact the
   system author (TitanRogue) if you need custom behavior.

2. **Historical war blockers.** The `agot_mw_start_mw_base_trigger` has
   hardcoded NOR blocks for specific character/date combinations (e.g.,
   Targaryen_63 on 8129.4.1, Baratheon_2 on 8282.9.15). These prevent MW from
   double-firing during scripted historical scenarios like Robert's Rebellion.
   Your custom scenarios may need similar blocks.

3. **Government exclusions.** The following governments are blocked from
   starting mega wars: `ruins_government`, `nights_watch_government`,
   `silent_sisterhood_government`, `herder_government`, pirate governments, and
   (for defenders only) `nomad_government` and `landless_adventurer_government`.

4. **`pre_war_liege` lifetime.** This variable must persist for the entire MW
   duration. If you remove it prematurely, realm reconstruction will fail
   silently. Only `agot_mw_clear_data_effect` and explicit removal in
   victory/defeat handlers should touch it.

5. **`is_independent_ruler` vs `agot_is_independent_ruler`.** Several places in
   the code explicitly warn "DON'T CHANGE THIS TO `agot*is_independent_ruler`!"
   The vanilla `is_independent_ruler` check is needed because during a MW,
   vassals may be _temporarily_ independent while still logically part of the
   realm.

6. **Multiple rebel leaders.** A single MW can have multiple rebel leaders
   (stored in `mw_rebel_leader_list`). Each has their own `story_agot_mw_rebel`.
   The crown story ends only when ALL rebel stories have ended. If you add a new
   rebel front mid-war, use `agot_mw_start_mid_war_effect`.

7. **Lite mode restrictions.** In `mw_lite` mode, neutral stance is blocked and
   realm break-up is disabled. Do not assume neutral list will be populated in
   lite mode.

8. **Story cycle timing.** The crown story initializes on day 1, the rebel story
   on day 2. Effects that need both stories to be in `on_going` state must
   account for this 1-day offset.

9. **War participant management.** When a character joins a side, they are
   removed from all wars of the opposing side and added to all wars of their
   side. This uses `remove_participant` and `add_attacker`/`add_defender` on
   every war in `mw_wars`. If you manually add wars to `mw_wars`, ensure they
   follow this pattern.

10. **Traitor punishment requires Royal Court.** The court punishment event
    (`agot_mega_wars.0601`) requires `has_royal_court = yes`. Characters without
    Royal Court DLC get the AI auto-punishment path (`agot_mega_wars.0605`)
    instead. If you are creating a sub-mod that should work without Royal Court,
    account for this.

11. **Vassal contract preservation.** The system saves and restores vassal
    contract data via `agot_mw_save_vassal_contract_data` and
    `agot_mw_reset_vassal_contract`. If you modify vassal contracts during a MW,
    the changes may be overwritten during realm reconstruction.

12. **`agot_mw_is_external_war_trigger` is the extension point** for new CBs
    that should trigger mega wars from outside the realm. Adding your CB to this
    trigger's OR block is the intended way to integrate.
