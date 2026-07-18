# AGOT Extension: Story Cycles

> This guide extends
> [references/patterns/story-cycles.md](../patterns/story-cycles.md) with
> AGOT-specific changes.

## What AGOT Changes

AGOT uses story cycles far more extensively than vanilla CK3. The mod defines
**40+ story cycles** covering dragons, maesters, Night's Watch, loans,
scenarios, secret identities, knightly orders, and more. Key differences from
vanilla:

1. **Dragons are characters with story cycles.** The `story_dragon_alive` cycle
   runs daily maintenance on every living dragon — tracking rider location,
   dragonpit status, wild dragon modifiers, wound healing, and growth. Dragons
   are not just items or modifiers; they are full characters managed by stories.
2. **Story cycles as variable storage.** AGOT uses story cycles purely as
   variable containers (e.g., `story_dragon_variable_storage`,
   `agot_knight_tree_teacher`) with empty `on_setup`/`on_end`/`on_owner_death`
   blocks and no effect groups. This is a pattern not seen in vanilla.
3. **Scenario scripting via story cycles.** Historical scenarios like Robert's
   Rebellion (`story_agot_scenario_rr`) use story cycles with dozens of flag
   variables to orchestrate complex multi-phase war narratives, pregnancy
   timelines, and character-specific events.
4. **Global variable lists.** AGOT stories frequently interact with `global_var`
   lists (e.g., `living_dragons`, `known_knight_trees`) using
   `any_in_global_list`, `every_in_global_list`, `add_to_variable_list`, and
   `remove_list_global_variable`.
5. **Aggressive tick rates.** Several AGOT stories tick daily (`days = 1`) for
   maintenance — something vanilla avoids. This is necessary for dragon location
   tracking and war modifiers but is expensive.
6. **Custom AGOT scripted effects inside stories.** Story cycles call
   AGOT-specific scripted effects like
   `agot_remove_from_dragonpit_skip_county_effects`,
   `agot_send_to_dragonpit_no_event`, `dragon_army_modifier_calculation`,
   `agot_citadel_maintenance_effect`, and
   `agot_secret_identity_adventure_effect`.
7. **Character references via `character:ID`.** Scenario story cycles reference
   specific historical characters by ID (e.g., `character:Stark_3`,
   `character:Lannister_1`) in `on_setup` to trigger initial events.
8. **Title-holder scoping for shared state.** AGOT uses `title:c_ruins.holder`
   as a shared variable bus — storing temporary variables on the holder of an
   unused title to pass data into `on_setup` (see `agot_knight_tree_teacher`,
   `story_dragon_variable_storage`).

## AGOT Story Cycle Categories

### Dragon Systems

| Story Cycle                     | Purpose                                                                                                            |
| ------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| `story_dragon_alive`            | Core dragon lifecycle: daily rider/location sync, monthly growth/healing, yearly AI taming and cannibal hunts      |
| `story_dragon_at_war`           | Created when a ridden dragon enters an army; applies siege and combat modifiers daily; ends when rider leaves army |
| `story_dragon_variable_storage` | Pure variable container storing dragon genes, size, age for dead/egg dragons                                       |

### Institutional / Faction

| Story Cycle                  | Purpose                                                                                                                         |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| `story_maester`              | Maester lifecycle: archmaester succession on death, grandmaester replacement, yearly citadel maintenance and novice advancement |
| `nw_ranger_story`            | Night's Watch First Ranger: daily ranger transfers, courtier management, ranging events                                         |
| `agot_knight_tree_structure` | Knight order tree: yearly cleanup check, ends when all members are dead                                                         |
| `agot_knight_tree_teacher`   | Variable container linking a teacher to a knight tree                                                                           |

### Character Narrative

| Story Cycle                 | Purpose                                                                                                                       |
| --------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| `story_agot_widowed`        | Widowed character arc: initial event in 3-7 days, then random events via `on_action = ongoing_widowed_events` every 1-5 years |
| `story_agot_squire_ongoing` | Squire training: AI simulation every 21-32 days, skill progression tracking                                                   |
| `secret_identity_story`     | Secret identity: daily validity check, monthly countdown to reveal/adventure decision                                         |
| `lmf_lover_story_cycle`     | Landless minor family lover: tracks relationship rating 0-5, periodic status checks                                           |

### Economy / Interaction

| Story Cycle                  | Purpose                                                                                                                          |
| ---------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| `story_agot_loan`            | Loan repayment timer: three duplicate effect groups for 3/5/10 year terms (workaround because `years` does not accept variables) |
| `story_hire_faceless`        | Faceless Men assassination: monthly check if victim is dead, then fires completion event                                         |
| `story_wear_face`            | Face-wearing tracking: stores old/new face variables, returns face to Hall of Faces on end                                       |
| `story_divine_plot_assassin` | Divine plot assassin: monthly check if employer changed or has no murder scheme, then assassin vanishes                          |

### Historical Scenarios

| Story Cycle                                  | Purpose                                                                                         |
| -------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| `story_agot_scenario_rr`                     | Robert's Rebellion: dozens of flag variables tracking war phases, pregnancies, duels, marriages |
| `story_agot_scenario_defiance_of_duskendale` | Defiance of Duskendale scenario                                                                 |
| `story_agot_scenario_ninepenny_kings`        | War of the Ninepenny Kings scenario                                                             |
| `story_agot_scenario_rogue_prince`           | Rogue Prince scenario                                                                           |

### Pirate / Trade / Mega-War

| Story Cycle                            | Purpose                       |
| -------------------------------------- | ----------------------------- |
| `agot_landless_pirate_ai_story_cycles` | AI pirate behavior            |
| `agot_story_fund_trade_expedition`     | Trade expedition funding      |
| `agot_story_cycle_mega_wars`           | Large-scale war orchestration |

## AGOT-Specific Template

A typical AGOT story cycle with daily maintenance and periodic narrative events:

```
my_agot_story = {
	on_setup = {
		# Store references from character variables onto the story
		story_owner = {
			if = {
				limit = { has_variable = my_target }
				scope:story = {
					set_variable = {
						name = target
						value = prev.var:my_target
					}
				}
				remove_variable = my_target
			}
		}
		set_variable = {
			name = story_phase
			value = flag:active
		}
	}

	on_end = {
		story_owner = {
			remove_character_flag = has_my_agot_story
			# Clean up any modifiers added during the story
		}
	}

	on_owner_death = {
		# AGOT often just ends on death — transfer is rare
		scope:story = { end_story = yes }
	}

	# Daily maintenance — keep state consistent
	effect_group = {
		days = 1
		triggered_effect = {
			trigger = {
				# Validity check: end if preconditions fail
				OR = {
					NOT = { exists = var:target }
					var:target = { is_alive = no }
				}
			}
			effect = {
				scope:story = { end_story = yes }
			}
		}
	}

	# Periodic narrative events
	effect_group = {
		days = { 90 365 }

		trigger = {
			story_owner = { is_alive = yes }
			var:story_phase = flag:active
		}

		first_valid = {
			triggered_effect = {
				trigger = { always = yes }
				effect = {
					story_owner = {
						trigger_event = {
							on_action = my_agot_story_ongoing_events
						}
					}
				}
			}
		}
	}
}
```

### Variable-storage-only pattern (no effect groups)

Used when you need a persistent container for related variables but no periodic
ticking:

```
my_agot_variable_storage = {
	on_setup = {
		# Pull variables from a shared bus (title holder)
		title:c_ruins.holder = {
			var:transfer_data = { save_scope_as = data_ref }
			remove_variable = transfer_data
		}
		set_variable = {
			name = stored_data
			value = scope:data_ref
		}
	}
	on_end = {}
	on_owner_death = {}
}
```

### Loan-style timer workaround

Since `years` and `days` do not accept variables, duplicate the effect group for
each possible duration:

```
my_agot_timed_story = {
	on_setup = {
		set_variable = {
			name = duration
			value = story_owner.var:chosen_duration
		}
	}
	on_end = {}
	on_owner_death = { scope:story = { end_story = yes } }

	effect_group = {
		years = 3
		trigger = { var:duration = 3 }
		triggered_effect = {
			effect = {
				story_owner = { trigger_event = my_events.0001 }
			}
		}
	}
	effect_group = {
		years = 5
		trigger = { var:duration = 5 }
		triggered_effect = {
			effect = {
				story_owner = { trigger_event = my_events.0001 }
			}
		}
	}
}
```

## Annotated AGOT Example

Below is a simplified version of `story_agot_widowed` showing a clean AGOT
narrative story cycle:

```
# File: common/story_cycles/agot_story_cycle_widowed.txt

story_agot_widowed = {

	on_end = {
		# Debug logging — common in AGOT stories for development
		debug_log = "Widowed story ended on:"
		debug_log_date = yes
	}

	on_owner_death = {
		scope:story = { end_story = yes }
	}

	# Phase 1: Fire the introductory event shortly after creation
	effect_group = {
		days = { 3 7 }          # 3-7 days after story starts
		chance = 100             # Always fires

		triggered_effect = {
			trigger = {
				story_owner = {
					has_trait = widowed
					NOT = { has_character_flag = widow_story_began }
				}
			}
			effect = {
				story_owner = {
					trigger_event = agot_widowed_events.0001
				}
			}
		}
	}

	# Phase 2: Ongoing random events over the years
	effect_group = {
		days = { 365 1825 }     # 1-5 years between events

		trigger = {
			story_owner = {
				has_trait = widowed    # End naturally if trait removed
			}
		}

		first_valid = {
			triggered_effect = {
				trigger = { always = yes }
				effect = {
					story_owner = {
						trigger_event = {
							on_action = ongoing_widowed_events
						}
					}
				}
			}
		}
	}
}
```

The story is created from a hidden death event (`agot_widowed_events.999`),
which checks if the deceased's spouse qualifies:

```
# File: events/agot_story_cycles/agot_story_cycle_widowed_events.txt

agot_widowed_events.999 = {
	hidden = yes
	immediate = {
		save_scope_as = dead_character
		# ... Dosh Khaleen check for Dothraki widows ...
		else_if = {
			limit = {
				exists = primary_spouse
				primary_spouse = {
					OR = {
						has_relation_lover = scope:dead_character
						has_relation_soulmate = scope:dead_character
					}
					NOT = {
						any_spouse = {
							NOT = { this = scope:dead_character }
							is_alive = yes
						}
					}
				}
			}
			primary_spouse = {
				add_trait = widowed
				create_story = story_agot_widowed
				# Store the dead spouse reference on the story
				random_owned_story = {
					limit = { story_type = story_agot_widowed }
					set_variable = {
						name = dead_lover
						value = scope:dead_character
					}
				}
			}
		}
	}
}
```

Key patterns visible here:

- **Setting variables after creation**: The event uses `random_owned_story` +
  `limit = { story_type = ... }` to scope into the just-created story and set
  variables on it. This is necessary because `create_story` does not return a
  scope.
- **Trait as guard**: The `has_trait = widowed` trigger on the ongoing effect
  group ensures the story stops firing events if the trait is ever removed.
- **on_action delegation**: Rather than listing events directly, the story
  delegates to `on_action = ongoing_widowed_events` for cleaner organization.

## Key Differences from Vanilla

| Aspect                          | Vanilla                             | AGOT                                                                                               |
| ------------------------------- | ----------------------------------- | -------------------------------------------------------------------------------------------------- |
| **Story count**                 | ~15 story cycles                    | 40+ story cycles                                                                                   |
| **Daily ticking**               | Rare (avoided for performance)      | Common for dragon/war/ranger maintenance                                                           |
| **Variable storage stories**    | Not used                            | Used frequently — empty stories that just hold variables                                           |
| **Global variable interaction** | Minimal                             | Heavy use of `global_var` lists (`living_dragons`, `known_knight_trees`, etc.)                     |
| **Title as variable bus**       | Not used                            | `title:c_ruins.holder` used to pass data into `on_setup`                                           |
| **Character references**        | Generic — uses scopes               | Scenario stories use `character:ID` for historical figures                                         |
| **Owner is non-human**          | Owner is always a human character   | Owner can be a dragon character (`story_dragon_alive`)                                             |
| **Heir transfer**               | Common pattern (`make_story_owner`) | Rare — most AGOT stories just `end_story = yes` on death                                           |
| **debug_log usage**             | Not present                         | Frequently used for development tracing                                                            |
| **Scripted effects**            | Inline effects                      | Heavy delegation to AGOT scripted effects                                                          |
| **Duration workaround**         | Not needed                          | Duplicate effect groups for variable durations (loan pattern)                                      |
| **on_setup**                    | Usually initializes flags/variables | May also trigger initial events, pull variables from title bus, or reference historical characters |

## AGOT Pitfalls

- **Daily tick performance**: AGOT uses `days = 1` for dragon and ranger stories
  because location sync must be immediate. If your mod does not need
  frame-perfect tracking, use `days = { 7 15 }` or longer. Every daily-tick
  story runs its trigger checks on every single day for every instance.

- **`title:c_ruins.holder` variable bus**: AGOT passes data into `on_setup` by
  storing variables on `title:c_ruins.holder` before calling `create_story`,
  then reading and removing them in `on_setup`. If you use this pattern, always
  `remove_variable` after reading — otherwise the next story creation will pick
  up stale data. Also note that `c_ruins` is an AGOT-specific title; you would
  need your own unused title if creating a sub-mod.

- **`create_story` does not return a scope**: You cannot set variables on a
  story in the same effect block that creates it. Use
  `random_owned_story = { limit = { story_type = my_story } ... }` immediately
  after `create_story` to scope into it and set variables (as shown in the
  widowed example).

- **Duplicate effect groups for variable durations**: The `years` and `days`
  keys in effect groups do not accept variables or scripted values. AGOT works
  around this by creating one effect group per possible duration value, each
  gated by a trigger on a stored variable (see `story_agot_loan`). If you have
  many possible durations, this gets verbose.

- **Dragon stories chain**: `story_dragon_alive` creates `story_dragon_at_war`
  when a ridden dragon enters combat. If you add a new dragon-related story,
  check for existing stories first with `owns_story_of_type` to avoid duplicates
  (AGOT does this:
  `NOT = { story_owner = { owns_story_of_type = story_dragon_at_war } }`).

- **Empty handler blocks still required**: Even if your story does nothing on
  setup, end, or owner death, you must still include the blocks. AGOT stories
  like `agot_knight_tree_teacher` have
  `on_setup = {} on_end = {} on_owner_death = {}` — omitting them can cause
  errors.

- **Scenario stories reference hardcoded characters**: Scenario story cycles
  like `story_agot_scenario_rr` reference characters by ID
  (`character:Stark_3`). If you write a sub-mod that changes history files,
  these references may break if character IDs change. Always check the AGOT
  history files for the correct IDs.

- **Global list cleanup**: If your story adds to a global list in `on_setup`
  (e.g.,
  `add_to_variable_list = { name = my_global_list target = story_owner }`), you
  must remove from that list in `on_end` and `on_owner_death`. AGOT's dragon
  death handler in `story_dragon_alive` removes from `dragons_in_pit` —
  forgetting this leaves orphaned entries that affect `any_in_global_list`
  triggers.

- **AGOT custom triggers in story conditions**: AGOT stories use custom scripted
  triggers like `is_current_dragonrider_warfare`, `agot_can_be_ruler`,
  `agot_valid_ranger_camper`, etc. These are defined in
  `common/scripted_triggers/`. If you reference them in a sub-mod, you depend on
  AGOT's version — they may change between updates.

- **`end_story = yes` vs `scope:story = { end_story = yes }`**: In
  `on_owner_death`, the root scope is the story itself, so `end_story = yes`
  works directly. Inside an effect group's `triggered_effect`, root is also the
  story, but from within a character scope you need
  `scope:story = { end_story = yes }`. AGOT uses both patterns — be consistent
  and explicit.
