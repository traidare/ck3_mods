# AGOT Extension: Governments & Laws

> This guide extends
> [references/patterns/governments.md](../patterns/governments.md) with
> AGOT-specific changes.

## What AGOT Changes

AGOT replaces the vanilla political landscape with Westeros/Essos-themed
governments. The key changes are:

1. **New government types** -- Lord Paramount feudal (`lp_feudal_government`),
   Night's Watch (`nights_watch_government`), pirates (`pirate_government`), The
   Citadel (`the_citadel_government`), Kingsguard (`kingsguard_government`),
   Silent Sisterhood (`silent_sisterhood_government`), ruins/wilderness/unknown
   placeholder governments, First Ranger (`first_ranger_government`), and a
   Command government (`command_government`).
2. **Vanilla governments heavily modified** -- `feudal_government`,
   `clan_government`, `tribal_government`, `administrative_government`,
   `republic_government`, and `theocracy_government` are all overwritten in
   `00_government_types.txt` with AGOT-specific tweaks (new holdings like
   `ruin_holding`, `settlement_holding`; removed `required_county_holdings`;
   disabled `primary_heritages`; added `government_is_default` flag).
3. **Free Cities use administrative_government** -- Rather than a separate
   government, Free Cities reuse `administrative_government` with the flag
   `government_is_free_city` and a custom `free_city_election_succession_law`.
4. **New custom law groups** -- Slavery laws, Dragonpit laws, Night's Watch
   centralization, pirate port tax rates, Free City term length/franchise/policy
   laws.
5. **Paramountcy system** -- A scripted trigger
   (`agot_is_part_of_paramountcy_realm`) governs whether a character qualifies
   for `lp_feudal_government`, which replaces standard feudal in paramountcy
   realms (e.g., the Seven Kingdoms under the Iron Throne).
6. **Government-specific events** -- `events/agot_government_events/` contains
   event files for Free Cities, Night's Watch maintenance, Citadel maintenance,
   and pirates.

## AGOT Government Types

### Landed, playable governments

| Government key              | Lore equivalent                                    | Primary holding      | Key flags                                                                          | Notes                                                                                                                                                                                                                    |
| --------------------------- | -------------------------------------------------- | -------------------- | ---------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `feudal_government`         | Standard feudal lords (NOT in a paramountcy realm) | `castle_holding`     | `government_is_feudal`, `government_is_default`                                    | Vanilla override. `can_get_government` excludes paramountcy realm members.                                                                                                                                               |
| `lp_feudal_government`      | Lord Paramount feudal (Seven Kingdoms, etc.)       | `castle_holding`     | `government_is_feudal`, `government_is_lp_feudal`, `government_is_default`         | Requires `agot_is_valid_lp_feudal_government_target` or a liege passing that check. Excludes Night's Watch lieges. Uses `lp_feudal_vassal` contract group.                                                               |
| `clan_government`           | Dothraki, Essosi clans                             | `castle_holding`     | `government_is_clan`, `government_is_default`                                      | `dynasty_named_realms` disabled, `always_use_patronym` kept.                                                                                                                                                             |
| `tribal_government`         | Wildlings, First Men remnants                      | `tribal_holding`     | `government_is_tribal`, `government_is_default`, `government_can_raid_rule`        | Mostly vanilla. Adds `republic_government_tax_contribution_add = -0.15` to character_modifier.                                                                                                                           |
| `administrative_government` | Free Cities (Braavos, Volantis, etc.)              | `castle_holding`     | `government_is_administrative`, `government_is_free_city`, `government_is_default` | Reuses vanilla admin framework. Legitimacy and state_faith disabled. Heavier levy/MaA penalties (`levy_size = -0.7`, `men_at_arms_limit = -5`).                                                                          |
| `nights_watch_government`   | The Night's Watch                                  | `castle_holding`     | `government_is_nw`, `government_is_default`                                        | Requires holding `title:k_the_wall` (or being a vassal of that holder) AND having trait `nightswatch`/`nightswatch_temp`/`nightswatch_historical`. Strong military modifiers. Uses `nights_watch_vassal` contract group. |
| `pirate_government`         | Stepstones pirates (with Landless Playable DLC)    | `pirate_den_holding` | `government_is_pirate`, `government_can_raid_rule`, `agot_unlocks_conquest_cb`     | Uses `domicile_type = agot_pirate_ship`. Landless playable. Has `pirate_vassal` contract group.                                                                                                                          |
| `pirate_no_dlc_government`  | Stepstones pirates (without DLC)                   | `pirate_den_holding` | `government_is_pirate_without_landless_dlc`, `government_can_raid_rule`            | Fallback for players without Roads to Power. No domicile.                                                                                                                                                                |
| `first_ranger_government`   | Night's Watch First Ranger                         | `castle_holding`     | `government_is_first_ranger`, `government_is_nw`, `government_is_custom_landless`  | Landless playable. Requires `title:d_nw_landless_first_ranger` + NW trait + `lifestyle_nw_ranger` trait. Uses `domicile_type = agot_ranger_camp`.                                                                        |
| `command_government`        | Golden Company command?                            | `castle_holding`     | `government_is_command`, `government_is_default`                                   | Requires `primary_title = title:b_goldguard_heights`. Uses `command_vassal` contract group.                                                                                                                              |

### Non-playable / placeholder governments

| Government key                 | Purpose                                 | Key flags                                                  |
| ------------------------------ | --------------------------------------- | ---------------------------------------------------------- |
| `the_citadel_government`       | The Citadel (Archmaesters)              | `government_is_the_citadel`                                |
| `kingsguard_government`        | Kingsguard order                        | `government_is_kg`                                         |
| `silent_sisterhood_government` | Silent Sisters                          | `government_is_silent_sisters`                             |
| `ruins_government`             | Ruined holdings                         | `government_is_ruins`, `government_is_uninteractable`      |
| `unknown_government`           | Unknown/unmapped regions                | `government_is_unknown`, `government_is_uninteractable`    |
| `wilderness_government`        | Wilderness areas                        | `government_is_wilderness`, `government_is_uninteractable` |
| `host_government`              | Temporary host realms                   | `government_is_host`                                       |
| `republic_government`          | City republics (non-Free-City)          | `government_is_republic`                                   |
| `theocracy_government`         | Religious rulers (Faith Militant, etc.) | `government_is_theocracy`                                  |

### The `government_is_default` flag

AGOT adds `government_is_default` to nearly every playable government. This flag
groups governments that should use regular lifestyle perks. When writing
triggers that should apply to "normal" governments (but not
ruins/wilderness/uninteractable), use:

```
government_has_flag = government_is_default
```

### The paramountcy system and `lp_feudal_government`

The `lp_feudal_government` (Lord Paramount feudal) is a parallel feudal
government for realms under a paramountcy title (e.g., the Iron Throne
hegemony). The eligibility is controlled by two scripted triggers in
`common/scripted_triggers/00_agot_government_triggers.txt`:

- `agot_is_valid_lp_feudal_government_target` -- character must NOT be
  theocracy/republic/kingsguard/admin/uninteractable, must have a castle
  capital, and must be part of a paramountcy realm.
- `agot_is_part_of_paramountcy_realm` -- checks up to 6 liege levels deep for a
  title with `has_variable = agot_is_paramountcy_realm`.

Standard `feudal_government` has a `can_get_government` that explicitly EXCLUDES
characters qualifying for lp_feudal, so the two are mutually exclusive.

## AGOT Law Changes

### AGOT-specific law groups

**File: `common/laws/01_agot_realm_laws.txt`**

| Law group        | Laws                                                                                                             | Scope                                                                                                   |
| ---------------- | ---------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| `slavery_laws`   | `slavery_disallowed_law` (default), `slavery_allowed_law`                                                        | All realm types + admin. Gated by faith doctrines (`doctrine_slavery_thralls`, etc.) and cooldown.      |
| `dragonpit_laws` | `dragonpit_close_family_law` (default), `dragonpit_house_law`, `dragonpit_dynasty_law`, `dragonpit_everyone_law` | Requires a held title with `has_variable = has_dragonkeeper_order`. Controls who can use the dragonpit. |

**File: `common/laws/02_agot_nw_laws.txt`**

| Law group                    | Laws                                                                  | Scope                                                                                                                                                                                                                                                  |
| ---------------------------- | --------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `night_watch_centralization` | `night_watch_centralization_0` through `night_watch_centralization_3` | Night's Watch only (`realm_law_use_night_watch_centralization` trigger). Cumulative, like crown authority. Controls domain limit, knight limit, build costs, and wall maintenance level (`wall_maintenance_low` through `wall_maintenance_very_high`). |

**File: `common/laws/00_agot_pirate_laws.txt`**

| Law group                | Laws                                              | Scope                                                                                                                                                                                                                     |
| ------------------------ | ------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `pirate_haven_port_laws` | `pirate_tax_rate_01` through `pirate_tax_rate_04` | Pirates only (`government_has_flag = government_is_pirate`). Requires `pirate_den_01` building. Non-cumulative. Controls raid speed, MaA costs, travel speed, sea danger. Notifies pirate ship domicile owners on change. |

**File: `common/laws/02_agot_free_cities_laws.txt`**

| Law group          | Laws                                                                                                                                                     | Scope                                                                                                                            |
| ------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| `term_length_laws` | `term_length_short`, `term_length_long` (default), `term_length_life`                                                                                    | Admin governments with `free_city_election_succession_law`. Historical Free Cities are locked via `term_length_historical_laws`. |
| `franchise_laws`   | `franchise_democratic_full`, `franchise_lean_democratic` (default), `franchise_lean_aristocratic`, `franchise_aristocratic_full`, `franchise_theocratic` | Admin governments. Controls tyranny, vassal opinion, county opinion, control growth. Vassals must match liege's law.             |
| `policy_laws`      | `policy_mercantile_full`, `policy_lean_mercantile` (default), `policy_lean_militaristic`, `policy_militaristic_full`                                     | Admin governments. Controls development growth, MaA maintenance, faction opinions. Uses influence as pass cost.                  |

### Vanilla succession law modifications

AGOT modifies vanilla succession laws in `common/laws/00_succession_laws.txt`:

- Confederate partition references AGOT innovations
  (`innovation_agot_gavelkind`, `innovation_agot_heraldry`) instead of vanilla
  ones.
- A `free_city_election_succession_law` is added for administrative/Free City
  governments.
- A `pirate_succession_law` is defined in
  `common/laws/01_title_succession_laws.txt`.

## AGOT-Specific Template

### Adding a new government under the AGOT paramountcy system

```
# common/governments/my_agot_government_types.txt
my_agot_custom_government = {
    government_rules = {
        create_cadet_branches = yes
        rulers_should_have_dynasty = yes
        dynasty_named_realms = yes
        legitimacy = yes
        court_generate_spouses = no   # AGOT disables this on most governments
    }

    royal_court = any
    court_generate_commanders = no    # AGOT disables this on most governments

    primary_holding = castle_holding
    valid_holdings = { ruin_holding settlement_holding }  # AGOT custom holding types
    required_county_holdings = { castle_holding }

    can_get_government = {
        # Your custom eligibility logic
        # Example: requires a specific title or region
        has_title = title:k_my_custom_kingdom
        NOT = {
            any_liege_or_above = { has_trait = nightswatch }
        }
    }

    vassal_contract_group = feudal_vassal  # Or a custom one

    ai = {
        use_legends = yes
    }

    # IMPORTANT: Include government_is_default for lifestyle perk compatibility
    flags = {
        government_is_my_custom
        government_is_settled
        government_uses_crown_authority
        government_uses_domain_limit
        government_is_default   # Required for AGOT lifestyle perk compatibility
    }

    color = rgb{ 150 80 200 }
}
```

### Adding a new AGOT-specific law group

```
# common/laws/my_agot_laws.txt
@my_law_cooldown_years = 10

my_custom_laws = {
    default = my_law_level_1
    cumulative = no
    flag = all_realm_law        # Makes it show up under realm laws
    flag = agot_realm_law       # AGOT-specific grouping
    flag = admin_law            # Include if it should apply to admin governments too

    my_law_level_1 = {
        flag = my_law_basic

        can_have = {
            # Government restriction -- use flags, not has_government
            government_has_flag = government_is_my_custom
        }

        can_pass = {
            custom_description = {
                subject = root
                text = "has_my_law_cooldown"
                NOT = { has_variable = my_law_cooldown }
            }
        }

        pass_cost = {
            prestige = increase_crown_authority_prestige_cost
        }

        on_pass = {
            set_variable = {
                name = my_law_cooldown
                years = @my_law_cooldown_years
            }
        }

        modifier = {
            # Stat effects for this law level
            domain_limit = 1
        }

        ai_will_do = {
            value = 1
        }
    }

    my_law_level_2 = {
        # ... same structure, higher effects
    }
}
```

## Annotated AGOT Example

The Night's Watch government is a good example of a fully custom AGOT government
with its own law group.

### Government definition (from `common/governments/00_agot_government_types.txt`)

```
nights_watch_government = {
    government_rules = {
        create_cadet_branches = no          # NW members renounce family
        rulers_should_have_dynasty = no     # Lord Commander has no dynasty
        dynasty_named_realms = no
        court_generate_spouses = no         # No marriages on the Wall
    }

    court_generate_commanders = no

    primary_holding = castle_holding
    required_county_holdings = { castle_holding }
    valid_holdings = { ruin_holding }        # Can hold ruins (e.g., abandoned castles)

    can_get_government = {
        OR = {
            has_title = title:k_the_wall
            any_liege_or_above = {
                has_title = title:k_the_wall
            }
        }
        OR = {
            has_trait = nightswatch          # Permanent NW member
            has_trait = nightswatch_temp     # Temporary (event-driven)
            has_trait = nightswatch_historical  # Historical setup
        }
    }

    character_modifier = {
        monthly_dread = 0.5
        army_maintenance_mult = -0.6        # NW doesn't pay soldiers
        men_at_arms_maintenance = -0.7
        martial_per_prestige_level = 2
        prowess_per_prestige_level = 2
        holy_order_hire_cost_mult = 1000    # Effectively blocks holy order hiring
        ai_war_chance = 2                   # Aggressive against wildlings
        ai_war_cooldown = -0.5
    }

    vassal_contract_group = nights_watch_vassal

    flags = {
        government_is_nw                    # Primary NW flag for trigger checks
        government_is_settled
        government_is_default               # Enables standard lifestyle perks
    }

    color = hsv{ 0.9 0.0 0.22 }            # Very dark (black of the Night's Watch)
}
```

### Paired law group (from `common/laws/02_agot_nw_laws.txt`)

```
night_watch_centralization = {
    default = night_watch_centralization_1
    cumulative = yes                        # Works like crown authority tiers
    flag = realm_law
    flag = all_realm_law

    night_watch_centralization_0 = {
        modifier = {
            build_speed = 0.1               # Slower building
            build_gold_cost = 0.1           # More expensive
            knight_limit = -2
            domain_limit = -1               # Reduced domain
        }
        flag = title_revocation_allowed
        flag = wall_maintenance_low         # AGOT custom flag for wall events

        can_keep = {
            realm_law_use_night_watch_centralization = yes
        }
    }

    night_watch_centralization_1 = {        # Default level
        modifier = {
            build_speed = -0.15             # Faster building
            build_gold_cost = -0.15
            knight_limit = 4
            domain_limit = 2
        }
        flag = title_revocation_allowed
        flag = can_change_succession_laws
        flag = wall_maintenance_normal

        can_keep = {
            realm_law_use_night_watch_centralization = yes
        }

        can_pass = {
            # Standard crown-authority-style cooldown
            trigger_if = {
                limit = { has_realm_law = night_watch_centralization_0 }
                custom_description = {
                    subject = root
                    text = "has_crown_authority_cooldown"
                    NAND = {
                        has_variable = crown_authority_cooldown
                        NOT = {
                            culture = { has_innovation = innovation_all_things }
                        }
                    }
                }
            }
        }

        pass_cost = {
            prestige = {
                if = {
                    limit = {
                        NOR = {
                            has_realm_law = night_watch_centralization_2
                            has_realm_law = night_watch_centralization_3
                        }
                    }
                    add = increase_crown_authority_prestige_cost
                }
            }
        }

        on_pass = {
            calculate_authority_cooldown_break_effect = yes
            set_variable = {
                name = crown_authority_cooldown
                years = 20
            }
        }
    }

    # ... levels 2 and 3 continue the pattern with higher bonuses
    # Level 2 adds: vassal_retraction_allowed, wall_maintenance_high
    # Level 3 adds: wall_maintenance_very_high
}
```

### Supporting events (from `events/agot_government_events/`)

The Night's Watch has maintenance events in
`agot_nightswatch_maintenance_events.txt` that:

- Remove all women from court (`agot_nightswatch_maintenance.0001`)
- Enforce NW-specific court/courtier rules via
  `agot_nightswatch_ruler_on_start_effect` and
  `agot_nightswatch_courtier_on_start_effect`
- Reassign courtiers who have the `nightswatch` trait but are not properly
  attached

## Key Differences from Vanilla

| Aspect                         | Vanilla                                                  | AGOT                                                                                                                                                                                                                  |
| ------------------------------ | -------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Feudal split**               | Single `feudal_government`                               | Split into `feudal_government` (non-paramountcy) and `lp_feudal_government` (paramountcy realms). Mutually exclusive via `can_get_government`.                                                                        |
| **Free Cities**                | No equivalent                                            | Uses `administrative_government` with `government_is_free_city` flag. Has custom election, franchise, and policy laws.                                                                                                |
| **Holdings**                   | Standard set                                             | Adds `ruin_holding`, `settlement_holding`, `pirate_den_holding`, `wilderness_holding`, `unknown_holding`. Most governments add these to `valid_holdings`.                                                             |
| **`required_county_holdings`** | Usually `{ castle_holding city_holding church_holding }` | Often reduced or removed entirely (e.g., feudal only requires `castle_holding`, admin requires `castle_holding city_holding`).                                                                                        |
| **Court generation**           | Default enabled                                          | Most AGOT governments set `court_generate_spouses = no` and `court_generate_commanders = no`.                                                                                                                         |
| **Uninteractable governments** | None                                                     | `ruins_government`, `unknown_government`, `wilderness_government` use `government_is_uninteractable` flag, disable all AI, and apply extreme negative modifiers (`knight_limit = -100`, `monthly_income_mult = -10`). |
| **DLC handling**               | Single government per type                               | Pirates have two variants: `pirate_government` (with DLC, landless playable + domicile) and `pirate_no_dlc_government` (without DLC).                                                                                 |
| **Succession**                 | Vanilla innovations                                      | AGOT innovations (`innovation_agot_gavelkind`, `innovation_agot_heraldry`) replace vanilla ones in succession law triggers.                                                                                           |
| **Law cooldowns**              | Crown authority only                                     | Each AGOT law group has its own cooldown variable (e.g., `slavery_law_cooldown`, `pirate_port_law_cooldown`, `dragonpit_law_cooldown`).                                                                               |

## AGOT Pitfalls

### "My custom government conflicts with lp_feudal_government"

The paramountcy check in `feudal_government.can_get_government` and
`lp_feudal_government.can_get_government` use scripted triggers that check
multiple liege levels. If your government should work within a paramountcy
realm, you need to either:

- Add exclusion logic in your `can_get_government` (like NW does with
  `NOT = { any_liege_or_above = { has_trait = nightswatch } }`)
- OR modify the `agot_is_valid_lp_feudal_government_target` trigger to exclude
  your government

### "My government gets overwritten to feudal/lp_feudal on game start"

AGOT runs government reassignment logic in
`common/on_action/agot_on_actions/agot_game_start.txt` and
`agot_title_on_actions.txt`. Characters may be force-switched to the "correct"
government. Check these files for interference with your custom government.

### "Characters in ruins/wilderness/unknown governments are interactable"

These placeholder governments are designed to be invisible. They use
`government_is_uninteractable` flag and extreme negative modifiers. If you need
to interact with these holdings, check for the flag first:

```
NOT = { government_has_flag = government_is_uninteractable }
```

### "My law doesn't appear for Free City rulers"

Free City laws use `government_allows = administrative` (not a flag check)
combined with `has_realm_law = free_city_election_succession_law`. Both
conditions must be true. Also check if `agot_is_historical_free_city` is
blocking your law (historical Free Cities have locked term lengths).

### "Night's Watch centralization doesn't show up"

NW centralization requires `realm_law_use_night_watch_centralization = yes` in
`can_keep`. This is a scripted trigger -- make sure your character is actually
under the NW government and holds `title:k_the_wall` or is a vassal of that
holder.

### "Pirate laws require a building"

Pirate port laws gate `can_have` on `has_building_or_higher = pirate_den_01` in
the capital county. If the pirate den building doesn't exist, the law group
won't appear at all.

### "Missing `government_is_default` flag causes lifestyle perk issues"

AGOT uses `government_has_flag = government_is_default` to gate standard
lifestyle perks. If you create a new playable government and forget this flag,
rulers may lose access to lifestyle perk trees.

### "Slavery law can_keep fails silently"

`slavery_allowed_law` has a `can_keep` that checks both liege law AND faith
doctrines. If a character changes faith to one with `doctrine_slavery_thralls`,
`doctrine_slavery_indentured`, or `doctrine_slavery_crime`, the law is
automatically revoked. The `agot_pentos_braavos_treaty_character_trigger` also
blocks it for specific characters.

### "Free City franchise/policy laws cost influence, not prestige"

Unlike most AGOT laws that cost prestige, `policy_laws` use `influence` as the
pass cost currency. Make sure the character actually has influence (admin
governments only).

### "Admin government changes from vanilla are significant"

AGOT's `administrative_government` disables `legitimacy` and `state_faith`,
increases MaA penalties (`men_at_arms_limit = -5` vs vanilla `-2`), and adds
`government_is_free_city` flag directly. If your submod expects vanilla admin
behavior, these differences will affect it.
