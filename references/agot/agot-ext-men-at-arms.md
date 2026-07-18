# AGOT Extension: Men-at-Arms

> This guide extends
> [references/patterns/men-at-arms.md](../patterns/men-at-arms.md) with
> AGOT-specific changes.

## What AGOT Changes

AGOT overhauls the Men-at-Arms system in several major ways:

1. **Replaces vanilla terrain bonuses entirely.** Every MaA type (including
   vanilla ones in `00_maa_types.txt`) has its terrain bonuses rewritten. AGOT
   uses a comprehensive system where every terrain is listed with bonuses or
   penalties, instead of vanilla's sparse approach.
2. **Adds new terrain types.** AGOT introduces terrain keys not present in
   vanilla: `the_bog`, `cloudforest`, `glacier`, `frozen_flats`, `taiga_bog`,
   `urban`, `highlands`. Each terrain also has `majorroad_` and `minorroad_`
   variants (e.g., `majorroad_the_bog`, `minorroad_glacier`).
3. **Adds the `anti_dragon` archetype.** A new MaA `type` value for units that
   counter dragons.
4. **Adds `chariot_cavalry` counters.** Some AGOT units counter
   `chariot_cavalry`, a new archetype added by AGOT.
5. **Night's Watch exclusion.** Almost all non-NW MaA types include
   `NOT = { government_has_flag = government_is_nw }` in `can_recruit`. Night's
   Watch characters have their own dedicated MaA in
   `00_agot_nights_watch_maa_types.txt`.
6. **Pirate-exclusive units.** The pirate government gets its own MaA gated by
   `government_has_flag = government_is_pirate`.
7. **Title-gated MaA.** Some units require holding a specific title (e.g.,
   `goldcloaks` requires `has_title = title:c_kings_landing`) plus a global
   variable check.
8. **AGOT cost script values.** Costs use AGOT-specific script value names like
   `heavy_cavalry_recruitment_cost_very_cheap`,
   `skirmisher_low_maint_cost_normal`, etc., instead of vanilla's simpler
   values.
9. **Provision cost variables.** Every MaA file redeclares the same block of
   `@provisions_cost_*` local variables, which must be synced across files.
10. **Massive regional cultural MaA library.** AGOT adds ~28 cultural MaA files,
    one per region (North, Dorne, Ironborn, Reach, etc.) plus Essos regions.

## AGOT MaA Types

### File Categories

| File pattern                              | Gate mechanism                                             | Examples                                         |
| ----------------------------------------- | ---------------------------------------------------------- | ------------------------------------------------ |
| `00_agot_cultural_<region>_maa_types.txt` | `valid_for_maa_trigger = { PARAMETER = unlock_maa_<key> }` | `barrow_knights`, `winter_wolves`, `sand_steeds` |
| `00_agot_innovation_maa_types.txt`        | `culture = { has_innovation = innovation_agot_* }`         | `knights_of_the_dragon`                          |
| `00_agot_title_maa_types.txt`             | `has_title = title:<key>` + global variable                | `goldcloaks`                                     |
| `00_agot_dragon_maa_types.txt`            | Innovation or faith doctrine                               | `scorpions`, `water_wizards`                     |
| `00_agot_nights_watch_maa_types.txt`      | `government_has_flag = government_is_nw`                   | `nw_rangers`                                     |
| `00_agot_pirate_maa_types.txt`            | `government_has_flag = government_is_pirate`               | `pirate_archers`                                 |
| `00_agot_holy_order_maa_types.txt`        | Faith + conditional title checks                           | `shrikes`                                        |
| `00_agot_legacy_maa_types.txt`            | Dynasty perk                                               | `sarsfield_horse_archers`                        |
| `00_agot_special_maa_types.txt`           | Domicile parameter                                         | `laamp_settler_maa`                              |
| `00_maa_types.txt`                        | _(vanilla overwrite)_                                      | `light_footmen`, `bowmen`, etc.                  |

### New Archetypes

- **`anti_dragon`** -- Used by `scorpions` and `water_wizards`. These have
  `fights_in_main_phase = no` and counter the dummy `dragons_regiment` type.
- **`chariot_cavalry`** -- Appears in counter blocks of many AGOT units (e.g.,
  Dornish `sun_spears` counters `chariot_cavalry = 1`).

### Notable Units

- **`dragons_regiment`** -- A dummy MaA type (`can_recruit = { always = no }`)
  that exists solely so scorpions can declare a counter against it. Do NOT
  modify this.
- **`water_wizards`** -- Faith-gated anti-dragon unit that only appears when
  `agot_dragon_population_alive = yes` (a scripted trigger).
- **`goldcloaks`** -- Title-gated to `c_kings_landing` holder, plus requires a
  global variable flag `agot_goldcloaks_founded`.
- **`shrikes`** -- Holy order MaA with a complex trigger: requires
  `faith:drowned_god` and checks whether Iron Islands title holders are
  non-Drowned-God faith. Also uses `max_regiments = 4`.

## AGOT-Specific Template

### common/men_at_arms_types/00_agot_cultural_myregion_maa_types.txt

```
# standard costs
@maa_buy_cost = 150
@maa_low_maintenance_cost = 1.0
@maa_high_maintenance_cost = 5.0
@cultural_maa_extra_ai_score = 80

# Must be synced between files with the values located at "# Provisions Costs #".
@provisions_cost_infantry_cheap = 3
@provisions_cost_infantry_moderate = 7
@provisions_cost_infantry_expensive = 12
@provisions_cost_infantry_bankrupting = 15

@provisions_cost_cavalry_cheap = 7
@provisions_cost_cavalry_moderate = 15
@provisions_cost_cavalry_expensive = 21
@provisions_cost_cavalry_bankrupting = 30

@provisions_cost_special_cheap = 6
@provisions_cost_special_moderate = 12
@provisions_cost_special_expensive = 18
@provisions_cost_special_bankrupting = 24

my_regional_warriors = {
	type = heavy_infantry

	buy_cost = { gold = heavy_infantry_recruitment_cost_normal }
	low_maintenance_cost = { gold = heavy_infantry_low_maint_cost_normal }
	high_maintenance_cost = { gold = heavy_infantry_high_maint_cost_normal }
	provision_cost = @provisions_cost_infantry_expensive
	stack = 100

	damage = 30
	toughness = 30
	pursuit = 0
	screen = 0

	counters = {
		skirmishers = 1
		pikemen = 1
	}

	can_recruit = {
		valid_for_maa_trigger = { PARAMETER = unlock_maa_my_regional_warriors }
		NOT = { government_has_flag = government_is_nw }
		NOT = {
			culture = { has_cultural_parameter = strength_in_numbers_heavy_maa_ban }
		}
	}

	ai_quality = { value = @cultural_maa_extra_ai_score }
	icon = heavy_infantry

	terrain_bonus = {
		# Home terrains: strong bonus
		taiga = { damage = 10  toughness = 10  pursuit = 10 screen = 10 }
		hills = { damage = 10  toughness = 10  pursuit = 10 screen = 10 }
		steppe = { damage = 10  toughness = 10  pursuit = 10 screen = 10 }
		# Familiar terrains: moderate bonus
		forest = { damage = 5  toughness = 5  pursuit = 5 screen = 5 }
		mountains = { damage = 5  toughness = 5  pursuit = 5 screen = 5 }
		wetlands = { damage = 5  toughness = 5  pursuit = 5 screen = 5 }
		taiga_bog = { damage = 5  toughness = 5  pursuit = 5 screen = 5 }
		glacier = { damage = 5  toughness = 5  pursuit = 5 screen = 5 }
		# Neutral: no entry needed, or 0
		# Unfamiliar terrains: moderate penalty
		plains = { damage = -5  toughness = -5  pursuit = -5 screen = -5 }
		farmlands = { damage = -5  toughness = -5  pursuit = -5 screen = -5 }
		oasis = { damage = -5  toughness = -5  pursuit = -5 screen = -5 }
		cloudforest = { damage = -5  toughness = -5  pursuit = -5 screen = -5 }
		floodplains = { damage = -5  toughness = -5  pursuit = -5 screen = -5 }
		# Hostile terrains: strong penalty
		desert = { damage = -10  toughness = -10  pursuit = -10 screen = -10 }
		desert_mountains = { damage = -10  toughness = -10  pursuit = -10 screen = -10 }
		jungle = { damage = -10  toughness = -10  pursuit = -10 screen = -10 }
		drylands = { damage = -10  toughness = -10  pursuit = -10 screen = -10 }
		urban = { damage = -10  toughness = -10  pursuit = -10 screen = -10 }
		highlands = { damage = -10  toughness = -10  pursuit = -10 screen = -10 }
		frozen_flats = { damage = -10  toughness = -10  pursuit = -10 screen = -10 }
		# Extreme penalty
		the_bog = { damage = -30  toughness = -30  pursuit = -30 screen = -30 }

		# Road variants: must mirror the base terrain values
		majorroad_taiga = { damage = 10  toughness = 10  pursuit = 10 screen = 10 }
		majorroad_hills = { damage = 10  toughness = 10  pursuit = 10 screen = 10 }
		majorroad_steppe = { damage = 10  toughness = 10  pursuit = 10 screen = 10 }
		majorroad_forest = { damage = 5  toughness = 5  pursuit = 5 screen = 5 }
		majorroad_mountains = { damage = 5  toughness = 5  pursuit = 5 screen = 5 }
		majorroad_wetlands = { damage = 5  toughness = 5  pursuit = 5 screen = 5 }
		majorroad_taiga_bog = { damage = 5  toughness = 5  pursuit = 5 screen = 5 }
		majorroad_glacier = { damage = 5  toughness = 5  pursuit = 5 screen = 5 }
		majorroad_plains = { damage = -5  toughness = -5  pursuit = -5 screen = -5 }
		majorroad_farmlands = { damage = -5  toughness = -5  pursuit = -5 screen = -5 }
		majorroad_oasis = { damage = -5  toughness = -5  pursuit = -5 screen = -5 }
		majorroad_cloudforest = { damage = -5  toughness = -5  pursuit = -5 screen = -5 }
		majorroad_floodplains = { damage = -5  toughness = -5  pursuit = -5 screen = -5 }
		majorroad_desert = { damage = -10  toughness = -10  pursuit = -10 screen = -10 }
		majorroad_desert_mountains = { damage = -10  toughness = -10  pursuit = -10 screen = -10 }
		majorroad_jungle = { damage = -10  toughness = -10  pursuit = -10 screen = -10 }
		majorroad_drylands = { damage = -10  toughness = -10  pursuit = -10 screen = -10 }
		majorroad_urban = { damage = -10  toughness = -10  pursuit = -10 screen = -10 }
		majorroad_highlands = { damage = -10  toughness = -10  pursuit = -10 screen = -10 }
		majorroad_frozen_flats = { damage = -10  toughness = -10  pursuit = -10 screen = -10 }
		majorroad_the_bog = { damage = -30  toughness = -30  pursuit = -30 screen = -30 }
		minorroad_taiga = { damage = 10  toughness = 10  pursuit = 10 screen = 10 }
		minorroad_hills = { damage = 10  toughness = 10  pursuit = 10 screen = 10 }
		minorroad_steppe = { damage = 10  toughness = 10  pursuit = 10 screen = 10 }
		minorroad_forest = { damage = 5  toughness = 5  pursuit = 5 screen = 5 }
		minorroad_mountains = { damage = 5  toughness = 5  pursuit = 5 screen = 5 }
		minorroad_wetlands = { damage = 5  toughness = 5  pursuit = 5 screen = 5 }
		minorroad_taiga_bog = { damage = 5  toughness = 5  pursuit = 5 screen = 5 }
		minorroad_glacier = { damage = 5  toughness = 5  pursuit = 5 screen = 5 }
		minorroad_plains = { damage = -5  toughness = -5  pursuit = -5 screen = -5 }
		minorroad_farmlands = { damage = -5  toughness = -5  pursuit = -5 screen = -5 }
		minorroad_oasis = { damage = -5  toughness = -5  pursuit = -5 screen = -5 }
		minorroad_cloudforest = { damage = -5  toughness = -5  pursuit = -5 screen = -5 }
		minorroad_floodplains = { damage = -5  toughness = -5  pursuit = -5 screen = -5 }
		minorroad_desert = { damage = -10  toughness = -10  pursuit = -10 screen = -10 }
		minorroad_desert_mountains = { damage = -10  toughness = -10  pursuit = -10 screen = -10 }
		minorroad_jungle = { damage = -10  toughness = -10  pursuit = -10 screen = -10 }
		minorroad_drylands = { damage = -10  toughness = -10  pursuit = -10 screen = -10 }
		minorroad_urban = { damage = -10  toughness = -10  pursuit = -10 screen = -10 }
		minorroad_highlands = { damage = -10  toughness = -10  pursuit = -10 screen = -10 }
		minorroad_frozen_flats = { damage = -10  toughness = -10  pursuit = -10 screen = -10 }
		minorroad_the_bog = { damage = -30  toughness = -30  pursuit = -30 screen = -30 }
	}

	winter_bonus = {
		normal_winter = { damage = 5  toughness = 5  pursuit = 5 screen = 5 }
		harsh_winter = { damage = 5  toughness = 5  pursuit = 5 screen = 5 }
	}
}
```

### Localization (localization/english/my_maa_l_english.yml)

```
l_english:
 my_regional_warriors: "Regional Warriors"
 my_regional_warriors_flavor: "#F Battle-hardened fighters from the region.#!"
```

## Annotated AGOT Example

This is `frog_spears` from `00_agot_cultural_north_maa_types.txt` (Crannogmen
skirmishers), with annotations.

```
frog_spears = {
	type = skirmishers                          # Standard vanilla archetype

	# AGOT uses named script values for costs, not literal numbers
	buy_cost = { gold = skirmisher_recruitment_cost_expensive }
	low_maintenance_cost = { gold = skirmisher_low_maint_cost_normal }
	high_maintenance_cost = { gold = skirmisher_high_maint_cost_normal }
	provision_cost = @provisions_cost_infantry_cheap  # File-local variable
	stack = 80                                  # Slightly below standard 100

	damage = 10
	toughness = 15
	pursuit = 15
	screen = 20

	counters = {
		light_cavalry = 2                       # Strong counter
		camel_cavalry = 2
		pikemen = 1
		heavy_cavalry = 1
		heavy_infantry = 1
	}

	can_recruit = {
		# Cultural parameter set by a tradition
		valid_for_maa_trigger = { PARAMETER = unlock_maa_frog_spears }
		# Night's Watch cannot recruit this
		NOT = { government_has_flag = government_is_nw }
		# No strength_in_numbers ban needed (skirmishers, not heavy)
	}

	ai_quality = { value = @cultural_maa_extra_ai_score }  # 80 = strong AI preference
	icon = marsh_walkers                        # Reuses an existing icon

	terrain_bonus = {
		# Crannogmen thrive in swamps and northern terrain
		the_bog = { damage = 20  toughness = 20  pursuit = 20 screen = 20 }  # Extreme home bonus
		taiga = { damage = 10  toughness = 10  pursuit = 10 screen = 10 }
		taiga_bog = { damage = 10  toughness = 10  pursuit = 10 screen = 10 }
		# ... moderate bonuses, penalties ...
		desert = { damage = -30  toughness = -30  pursuit = -30 screen = -30 }  # Extreme penalty

		# AGOT REQUIREMENT: road variants must mirror base terrain values
		majorroad_the_bog = { damage = 20  toughness = 20  pursuit = 20 screen = 20 }
		majorroad_taiga = { damage = 10  toughness = 10  pursuit = 10 screen = 10 }
		# ... all majorroad_ and minorroad_ variants ...
		minorroad_the_bog = { damage = 20  toughness = 20  pursuit = 20 screen = 20 }
		minorroad_taiga = { damage = 10  toughness = 10  pursuit = 10 screen = 10 }
		# ... etc.
	}

	winter_bonus = {
		normal_winter = { damage = 5  toughness = 5  pursuit = 5 screen = 5 }
		harsh_winter = { damage = 5  toughness = 5  pursuit = 5 screen = 5 }
	}
}
```

## Key Differences from Vanilla

| Aspect                   | Vanilla                                             | AGOT                                                                                                                                                                                                                            |
| ------------------------ | --------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Terrain coverage**     | Sparse: only terrains where unit has bonuses        | Exhaustive: every terrain listed with a value; road variants included                                                                                                                                                           |
| **AGOT terrain keys**    | N/A                                                 | `the_bog`, `cloudforest`, `glacier`, `frozen_flats`, `taiga_bog`, `urban`, `highlands`                                                                                                                                          |
| **Road variants**        | N/A                                                 | `majorroad_<terrain>` and `minorroad_<terrain>` for every terrain -- must mirror base values                                                                                                                                    |
| **Cost format**          | Literal numbers or vanilla script values            | Named AGOT script values: `<archetype>_recruitment_cost_<tier>`, `<archetype>_low_maint_cost_<tier>`, `<archetype>_high_maint_cost_<tier>`. Tiers: `very_cheap`, `cheap`, `normal`, `expensive`, `very_expensive`, `indentured` |
| **Provision cost**       | Optional                                            | Required. Uses file-local `@provisions_cost_<category>_<tier>` variables                                                                                                                                                        |
| **File-level variables** | Optional                                            | Mandatory. Every AGOT MaA file redeclares the full block of `@maa_buy_cost`, `@provisions_cost_*`, `@cultural_maa_extra_ai_score` at the top                                                                                    |
| **NW exclusion**         | N/A                                                 | `NOT = { government_has_flag = government_is_nw }` required on all non-NW units                                                                                                                                                 |
| **Heavy MaA ban**        | Optional                                            | Required on `heavy_infantry` and `heavy_cavalry`: `NOT = { culture = { has_cultural_parameter = strength_in_numbers_heavy_maa_ban } }`                                                                                          |
| **New archetypes**       | N/A                                                 | `anti_dragon`, `chariot_cavalry` (for counters)                                                                                                                                                                                 |
| **Terrain bonus values** | Per-stat bonuses (e.g., `damage = 8 toughness = 6`) | Uniform 4-stat bonuses in tiers: `+10/+5/-5/-10/-30` applied to all of `damage`, `toughness`, `pursuit`, `screen`                                                                                                               |
| **`ai_quality`**         | Varies                                              | Cultural MaA use `@cultural_maa_extra_ai_score` (60-80)                                                                                                                                                                         |

## AGOT Pitfalls

- **Missing road variants.** Every terrain entry must be tripled: base,
  `majorroad_`, `minorroad_`. If you define `taiga = { damage = 10 ... }` but
  forget `majorroad_taiga` and `minorroad_taiga`, your unit will have no bonus
  on roads through taiga. AGOT expects all three.
- **Missing AGOT terrains.** If you only list vanilla terrains, your unit will
  have no modifiers on `the_bog`, `cloudforest`, `glacier`, `frozen_flats`,
  `taiga_bog`, `urban`, or `highlands`. Copy the full terrain block from an
  existing AGOT unit as a starting point.
- **Forgetting `NOT = { government_has_flag = government_is_nw }`.** Without
  this, Night's Watch characters can recruit your unit, breaking AGOT's design
  where NW has its own dedicated roster.
- **Forgetting `strength_in_numbers_heavy_maa_ban`.** If your unit is
  `heavy_infantry` or `heavy_cavalry`, you must include
  `NOT = { culture = { has_cultural_parameter = strength_in_numbers_heavy_maa_ban } }`
  in `can_recruit`. This allows the Strength in Numbers tradition to work
  correctly.
- **Redeclaring `@provisions_cost_*` with wrong values.** These file-local
  variables are copied identically across all AGOT MaA files. If you change a
  value, it only affects your file -- but if you get it wrong, your unit's
  provision cost will be inconsistent. Copy the exact variable block from an
  existing AGOT file.
- **Using literal cost numbers instead of AGOT script values.** While literal
  numbers work, they bypass AGOT's cost balancing system. Use the named script
  values (e.g., `heavy_infantry_recruitment_cost_normal`) to stay consistent
  with AGOT's economy.
- **Countering `dragons_regiment` without `type = anti_dragon`.** If you want to
  make a unit that counters dragons, it must use `type = anti_dragon` like
  `scorpions` does. Do not add `dragons_regiment` to the counters of a regular
  infantry unit.
- **Using vanilla terrain bonus style.** Vanilla allows per-stat bonuses like
  `forest = { damage = 8 toughness = 6 }`. AGOT uses uniform 4-stat values like
  `forest = { damage = 5  toughness = 5  pursuit = 5 screen = 5 }`. Mixing
  styles works mechanically but breaks AGOT's design conventions.
- **Forgetting `provision_cost`.** AGOT expects every MaA to have a
  `provision_cost` field. Omitting it defaults to 0, which is inconsistent with
  the rest of the mod.
- **Not setting `the_bog` penalty.** Every AGOT MaA type has
  `the_bog = { damage = -30  toughness = -30  pursuit = -30 screen = -30 }` as
  an extreme penalty. Forgetting this makes your unit unrealistically effective
  in the Neck.
