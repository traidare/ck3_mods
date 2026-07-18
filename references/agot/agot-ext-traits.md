# AGOT Extension: Traits

> This guide extends [references/patterns/traits.md](../patterns/traits.md) with
> AGOT-specific changes.

## What AGOT Changes

AGOT massively extends the trait system. Key changes:

1. **Dragons are characters with traits.** AGOT models dragons as CK3
   characters. The `dragon` base trait uses `can_have_children = no`,
   `inheritance_blocker = all`, `flag = can_not_marry`, and has a complete
   personality trait system separate from human personality traits.
2. **Knighthood replaces vanilla knight trait.** The vanilla `knight` trait is
   replaced by a `squire` trait with an XP track (`knight` track at threshold
   100). A character becomes a "knight" when
   `has_trait_xp = { trait = squire track = knight value >= 100 }`. The scripted
   trigger `is_agot_knight_trigger` encapsulates this check.
3. **Night's Watch lifestyle system.** Three NW lifestyle traits
   (`lifestyle_nw_builder`, `lifestyle_nw_ranger`, `lifestyle_nw_steward`) each
   have XP tracks with 3 tiers (Novice/Journeyman/Master at 0/50/100).
4. **Religious order traits.** `septon`, `silent_sister`, `drowned_man`,
   `bearded_priest`, `red_priest`, `most_devout_member`, `kingsguard` -- all
   with `flag = can_not_marry` or `inheritance_blocker = all` as appropriate.
5. **New personality traits.** `authoritative`, `rude`, `inquisitive` -- new
   personality traits with full compatibility blocks.
6. **AGOT-specific health traits.** `greyscale`, `scurvy`, `crippled`, `burned`
   (with XP track for severity), `one_handed`, `half_blind`, `mute`.
7. **Hidden traits for system tracking.** Extensive use of hidden traits
   (`shown_in_ruler_designer = no`, `shown_in_encyclopedia = no`,
   `name = trait_hidden`) for canon dragon identity (`is_dragon_balerion`,
   `is_dragon_vhagar`, etc.), appearance modifications, archmaester specialties,
   and game state tracking.
8. **Vanilla trait overrides.** AGOT ships a modified `00_traits.txt` that
   alters vanilla traits (e.g., `gallowsbait` gets
   `pirate_government_opinion = 20`).
9. **ESR social standing.** A multi-track trait (`esr_social_standing`) with
   tracks `esr_well_connected`, `esr_friends_in_high_places`,
   `esr_social_pariah` using dynamic name/icon based on XP thresholds.

## AGOT Trait Categories

### Dragon Character Traits (00_agot_dragon_traits.txt)

**Base trait:** `dragon` -- applied to all dragon characters.

- `category = health`, `can_have_children = no`, `inheritance_blocker = all`,
  `claim_inheritance_blocker = all`
- Uses `flag = can_not_marry`, `health = 5`, `life_expectancy = 150`
- Dynamic name/desc/icon based on `has_character_flag = owned_dragon` and
  `var:current_rider`

**Rider traits:**

- `dragonrider` -- has dual XP tracks: `dragon_training` (dread bonuses) and
  `dragon_bond` (stat bonuses). Dynamic name shows dragon's name when alive via
  `var:current_dragon`.
- `dragonless_dragonrider` -- former rider whose dragon died but rider survived
- `dragonwidowed` -- rider whose dragon died, with `health = -0.2` penalty

**Dragon personality traits** (8 opposed pairs, all with
`potential = { has_trait = dragon }`): | Pair | Trait A | Trait B |
|------|---------|---------| | Temperament | `dragon_aggressive` |
`dragon_friendly` | | Sociability | `dragon_solitary` | `dragon_cooperative` | |
Authority | `dragon_imperious` | `dragon_supporting` | | Behavior |
`dragon_impulsive` | `dragon_calculating` | | Appetite | `dragon_voracious` |
`dragon_restrained` | | Obedience | `dragon_defiant` | `dragon_accepting` | |
Ferocity | `dragon_bloodthirsty` | `dragon_skittish` | | Special |
`dragon_cannibal` | (no opposite) |

Each dragon personality trait uses `flag` entries to encode numeric modifiers
for custom systems:

```
dragon_aggressive = {
    # ...
    flag = add_draconic_dread_10
    flag = subtract_temperament_12
    flag = subtract_taming_chance_10
    flag = add_combat_effectiveness_modifier_10
}
```

These flags are read by scripted effects/triggers to calculate taming chance,
combat effectiveness, and dread.

**Dragon congenital traits** (leveled groups with `genetic = yes`):

- `dragon_physique_good_1/2/3` and `dragon_physique_bad_1/2/3` -- grouped via
  `group = dragon_physique_good` / `group = dragon_physique_bad`
- `dragon_swift` / `dragon_slow` -- speed pair
- `dragon_majestic` / `dragon_ugly` -- appearance pair
- `dragon_spindly` -- no opposite, combines combat and size flags
- `dragon_fertile` -- only relevant for female dragons
- `dragon_destined` -- early growth flag

**Dragon education traits:** `education_dragon_1` through `education_dragon_5`,
each with temperament/taming flags.

**Dragon health traits:**

- `dragon_wounded_1` through `dragon_wounded_5` (grouped via
  `group = dragon_wounded`, leveled 1-5)
- `dragon_burned`, `dragon_ill`, `dragon_blind`, `dragon_depressed`

**Other:** `dragonslayer` (for humans,
`potential = { NOT = { has_trait = dragon } }`)

### Canon Dragon Identity Traits (00_agot_canon_dragon_traits.txt)

Hidden traits that identify specific dragons: `is_dragon_balerion`,
`is_dragon_vhagar`, `is_dragon_drogon`, `is_dragon_caraxes`, etc. (~50 traits).
All use:

```
is_dragon_balerion = {
    physical = no
    shown_in_ruler_designer = no
    shown_in_encyclopedia = no
    name = trait_hidden
    desc = trait_hidden_desc
    icon = pure_blooded.dds
}
```

Companion scripted triggers in `00_agot_canon_dragons_trait_triggers.txt` check
both the inactive trait and character ID:

```
is_character_dragon_balerion = {
    OR = {
        has_inactive_trait = is_dragon_balerion
        AND = {
            exists = character:dragon_balerion
            this = character:dragon_balerion
        }
    }
}
```

### Knight/Squire System (00_agot_traits.txt)

AGOT replaces vanilla knighthood with an XP-tracked `squire` trait:

```
squire = {
    physical = no
    monthly_prestige = 0.1
    same_opinion = 5
    shown_in_ruler_designer = no

    tracks = {
        knight = {
            100 = {
                attraction_opinion = 5
                monthly_prestige = 0.15
                heavy_cavalry_damage_mult = 0.05
                knight_effectiveness_mult = 0.02
                culture_modifier = {
                    parameter = knight_trait_more_valued
                    general_opinion = 10
                }
            }
        }
    }
}
```

- Name changes dynamically: "Squire" when `is_squire_with_trait_xp = yes`,
  "Knight" when `is_agot_knight_trigger = yes`, "Robber Knight" when also
  `gallowsbait` with bandit XP >= 51.
- Icon changes: `squire.dds` vs `knight.dds` based on same triggers.
- `stripped_knight` is the opposite, with `opposites = { squire }`.

### Night's Watch Traits (00_agot_traits.txt)

**Core trait:** `nightswatch` -- uses `flag = can_not_marry`,
`inheritance_blocker = all`, `claim_inheritance_blocker = all`. Has XP track:

```
nightswatch = {
    track = {
        100 = {
            prowess = 2
            dynasty_opinion = 5
            monthly_piety_gain_mult = 0.02
            ignore_negative_culture_opinion = yes
            ignore_negative_opinion_of_culture = yes
        }
    }
}
```

- Dynamic name: "Flappers" (recruits, XP < 100) vs "Sworn Brother" (XP = 100)
- Dynamic icon: `flappers.dds` vs `nightswatch.dds`

**NW Lifestyles** (all with 3-tier XP tracks at 0/50/100):

- `lifestyle_nw_builder` -- stewardship/building bonuses
- `lifestyle_nw_ranger` -- martial/movement/winter bonuses
- `lifestyle_nw_steward` -- stewardship/development bonuses

**Related:** `nightswatch_temp` (temporary version), `deserter` (opposite of
`nightswatch`)

### Religious Traits (00_agot_traits.txt)

- `septon` -- dynamic name by gender (Septa/Septon) and rank (High
  Septon/Septa), uses `agot_is_high_septon` trigger
- `silent_sister` -- `valid_sex = female`, `flag = can_not_marry`,
  `inheritance_blocker = all`
- `red_priest` -- dynamic name for female ("Red Priestess")
- `drowned_man`, `bearded_priest` -- Ironborn/Norvoshi clergy
- `most_devout_member` -- member of the Most Devout
- `kingsguard` / `former_kingsguard` -- royal bodyguard with
  `flag = can_not_marry`

### System/Utility Traits (00_agot_traits.txt)

"Marker" character traits for non-human entities:

- `ruin` -- for ruins: `immortal = yes`, `health = 100`, `prowess = -100`,
  `domain_limit = 10000`
- `unknown` -- for unknown characters: similar to ruin
- `wilderness` -- for wilderness areas: similar to ruin
- `agot_dummy_trait` -- system placeholder
- `house_customizer`, `vs_customizer`, `heterochromia_customizer` -- ruler
  designer traits

### Hidden Traits (00_agot_hidden_traits.txt)

Tracking traits for game systems: `great_spring_sickness_inactive_trait`,
`had_palatinate_contract`, `agot_was_westerosi_lord`, `not_had_coronation`,
`mw_expelled_trait` (with `inheritance_blocker = all`), archmaester specialty
metals (`archmaester_black_iron`, `archmaester_brass`, `archmaester_bronze`,
`archmaester_copper`, `archmaester_electrum`, `archmaester_yellow_gold`, etc.).

### Appearance Traits (00_agot_appearance_traits.txt)

Hidden traits for portrait modifications: `scripted_appearance`, hair dye traits
(`poppy_hair_dye`, `asshaii_scarlet_hair_dye`, `ghost_rose_hair_dye`, etc.).

### ESR Social Standing (00_agot_esr_traits.txt)

Multi-track trait for social reputation:

```
esr_social_standing = {
    flag = no_message
    shown_in_ruler_designer = no
    tracks = {
        esr_well_connected = { ... }
        esr_friends_in_high_places = { ... }
        esr_social_pariah = { ... }
    }
}
```

Dynamic name changes based on which tracks reach XP >= 60.

## AGOT-Specific Template

### Human trait (AGOT-compatible)

```
# common/traits/my_agot_traits.txt
my_agot_trait = {
    category = fame

    diplomacy = 2
    monthly_prestige = 0.5

    # AGOT-specific opinion modifiers (custom scoped opinions)
    sand_dornish_opinion = 10        # Only Dornish of Sandy type
    high_valyrian_opinion = 5        # Only High Valyrian characters

    # Use culture_modifier for culture-parameter-gated bonuses
    culture_modifier = {
        parameter = some_agot_culture_parameter
        same_culture_opinion = 10
    }

    # Always include dynamic desc with NOT = { exists = this } fallback
    desc = {
        first_valid = {
            triggered_desc = {
                trigger = {
                    NOT = { exists = this }
                }
                desc = trait_my_agot_trait_desc
            }
            desc = trait_my_agot_trait_character_desc
        }
    }

    shown_in_ruler_designer = yes
    ruler_designer_cost = 20
}
```

### Dragon trait (extending the dragon system)

```
# common/traits/my_dragon_traits.txt
my_dragon_personality_trait = {
    category = personality
    desc = {
        first_valid = {
            triggered_desc = {
                trigger = {
                    NOT = { exists = this }
                }
                desc = trait_my_dragon_personality_trait_desc
            }
            desc = trait_my_dragon_personality_trait_character_desc
        }
    }
    opposites = {
        my_dragon_opposite_trait
    }
    # REQUIRED: restrict to dragon characters only
    potential = {
        has_trait = dragon
    }
    # REQUIRED for AGOT dragon traits: prevent random generation
    birth = 0
    random_creation = 0.0
    random_creation_weight = 0
    shown_in_ruler_designer = no

    # AI personality values (used by dragon AI behavior)
    ai_boldness = 30
    ai_compassion = -10

    # Encode modifiers as flags for AGOT's scripted systems
    flag = add_draconic_dread_5
    flag = add_combat_effectiveness_modifier_5
    flag = subtract_taming_chance_10
}
```

### Hidden tracking trait

```
my_agot_tracking_trait = {
    physical = no
    shown_in_ruler_designer = no
    shown_in_encyclopedia = no
    name = trait_hidden
    desc = trait_hidden_desc
    icon = scholar.dds        # Pick any existing icon; it won't display
}
```

## Annotated AGOT Example

The `nightswatch` trait demonstrates AGOT's XP-based progression pattern:

```
nightswatch = {
    # Opposite: deserters can't rejoin
    opposites = {
        deserter
    }

    # Opinion effects -- NW brothers like each other, hate deserters
    same_opinion = 5
    dynasty_opinion = 5
    opposite_opinion = -20

    # NW vows: no marriage, no inheritance
    flag = can_not_marry
    inheritance_blocker = all
    claim_inheritance_blocker = all

    shown_in_ruler_designer = yes

    ai_honor = 10

    # Dynamic name: "Flappers" for recruits, "Sworn Brother" for full members
    name = {
        first_valid = {
            triggered_desc = {
                trigger = {
                    NOT = { exists = this }
                }
                desc = trait_nightswatch              # Fallback for encyclopedia
            }
            triggered_desc = {
                trigger = {
                    has_trait_xp = {
                        trait = nightswatch
                        value < 100                   # Not yet sworn
                    }
                }
                desc = trait_flappers                 # Recruit name
            }
            desc = trait_nightswatch_sworn            # Full member name
        }
    }

    # Dynamic icon follows the same pattern
    icon = {
        first_valid = {
            triggered_desc = {
                trigger = { NOT = { exists = this } }
                desc = nightswatch.dds
            }
            triggered_desc = {
                trigger = {
                    has_trait_xp = {
                        trait = nightswatch
                        value < 100
                    }
                }
                desc = flappers.dds                   # Recruit icon
            }
            desc = nightswatch.dds                    # Sworn brother icon
        }
    }

    # XP track: single threshold at 100 = fully sworn
    track = {
        100 = {
            prowess = 2
            dynasty_opinion = 5
            monthly_piety_gain_mult = 0.02
            ignore_negative_culture_opinion = yes
            ignore_negative_opinion_of_culture = yes
        }
    }
}
```

## Key Differences from Vanilla

| Aspect                | Vanilla                     | AGOT                                                                                                  |
| --------------------- | --------------------------- | ----------------------------------------------------------------------------------------------------- |
| Knight trait          | Simple `knight` trait       | `squire` with XP track; knight = squire at XP 100                                                     |
| Dragon system         | Not applicable              | Dragons are characters; `dragon` base trait + personality/congenital/education/health sub-traits      |
| Religious titles      | Clergy via council mechanic | Explicit traits: `septon`, `silent_sister`, `kingsguard`, `red_priest`, `drowned_man`                 |
| Trait flags           | Occasional use              | Heavy use for encoding numeric values read by scripted effects (e.g., `flag = add_draconic_dread_10`) |
| `potential` block     | Rarely used                 | Widely used to restrict dragon traits to dragon characters                                            |
| Hidden traits         | Rare                        | Extensive: ~50 canon dragon IDs, appearance mods, archmaester specialties, game state trackers        |
| `make_trait_inactive` | Rarely used                 | Core pattern for dragon congenital inheritance (traits can be "carried" but not expressed)            |
| Vanilla overrides     | N/A                         | `00_traits.txt` replaces vanilla file, modifying traits like `gallowsbait`                            |
| Trait-as-XP-container | Rare                        | Common: `nightswatch`, `maester`, `burned`, `esr_social_standing`, `squire` all use tracks            |
| Custom opinion types  | Only standard types         | AGOT-specific: `high_valyrian_opinion`, `sand_dornish_opinion`, `pirate_government_opinion`, etc.     |

## AGOT Pitfalls

- **Never use vanilla `knight` trait directly.** AGOT replaces it with the
  `squire` XP track system. Check knighthood with
  `is_agot_knight_trigger = yes`, not `has_trait = knight`.

- **Dragon traits need `potential = { has_trait = dragon }`.** Without this,
  your dragon personality/congenital trait can appear on human characters. Also
  set `birth = 0`, `random_creation = 0.0`, `random_creation_weight = 0`, and
  `shown_in_ruler_designer = no`.

- **Flag-encoded modifiers are NOT automatic.** Writing
  `flag = add_draconic_dread_10` does nothing by itself. These flags are read by
  AGOT's scripted effects that loop through traits and sum up values. If you add
  new flags, you must also add handling in the relevant scripted effects.

- **Dragon congenital inheritance uses scripted effects, not vanilla
  `genetic = yes`.** While dragon congenital traits do set `genetic = yes`, AGOT
  implements its own inheritance logic via effects like
  `agot_dragon_physique_good_effect` and triggers like
  `agot_dragon_inheritance_both_parents_have_active_trait`. The scripted system
  supports active vs. inactive trait inheritance (`make_trait_inactive` /
  `has_inactive_trait`). If adding new dragon congenital traits, you need to
  write corresponding scripted effects following this pattern.

- **Vanilla `00_traits.txt` is fully replaced.** AGOT ships its own
  `00_traits.txt`. If your submod also needs to modify vanilla traits, you will
  conflict with AGOT's file. Either depend on AGOT's version and patch it, or
  use a separate file for new traits only.

- **Dynamic desc MUST include `NOT = { exists = this }` fallback.** AGOT traits
  consistently include a triggered_desc block for when no character context
  exists (encyclopedia view, tooltips). Without this, the trait shows no
  description in the encyclopedia.

- **`nightswatch` has a temp variant.** `nightswatch_temp` exists as a
  transitional trait. Do not confuse it with the permanent `nightswatch` trait
  when checking conditions.

- **`claim_inheritance_blocker = all` is used alongside
  `inheritance_blocker = all`.** AGOT uses both to fully prevent inheritance.
  Vanilla only uses `inheritance_blocker`. Forgetting
  `claim_inheritance_blocker` means the character can still press claims.

- **Custom scoped opinions.** AGOT defines custom opinion types like
  `high_valyrian_opinion`, `sand_dornish_opinion`, `salt_dornish_opinion`,
  `stone_dornish_opinion`, `the_pact_religion_opinion`, `zealot_opinion`,
  `pirate_government_opinion`. These are defined elsewhere in the mod and can be
  used in traits. Do not invent new opinion types without defining them.

- **`maester` uses XP for rank progression.** The `maester` trait transitions
  through Novice (XP < 34), Acolyte (XP < 100), and Maester (XP = 100) via
  dynamic name blocks. If you interact with maesters, check XP thresholds, not
  separate traits.
