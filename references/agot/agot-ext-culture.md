# AGOT Extension: Culture

> This guide extends the culture section of
> [references/patterns/culture-religion.md](../patterns/culture-religion.md)
> with AGOT-specific changes.

## What AGOT Changes

AGOT replaces **all** vanilla cultures with lore-accurate Planetos cultures. The
structure uses the same CK3 engine (pillars, traditions, name lists, GFX), but
every identifier is custom.

Key changes:

- **No culture groups.** Vanilla wraps cultures inside a `my_group = { ... }`
  block with `graphical_cultures`. AGOT defines each culture as a **top-level
  block** (no parent group wrapper). Shared heritage replaces the grouping
  concept.
- **22 custom heritages** replace vanilla heritages (`heritage_andal`,
  `heritage_first_man`, `heritage_valyrian`, `heritage_wildling`,
  `heritage_ironman`, `heritage_freecities`, `heritage_ghiscari`,
  `heritage_rhoynar`, `heritage_grasslands`, `heritage_elder_races`,
  `heritage_hyrkoonan`, `heritage_jadeislands`, `heritage_mennight`,
  `heritage_moraqi`, `heritage_nghai`, `heritage_qaathi`, `heritage_sarnori`,
  `heritage_shadowlanders`, `heritage_sothoryi`, `heritage_summer`,
  `heritage_yitish`, `heritage_hairyman`).
- **28+ custom languages** (`language_agot_westeros`, `language_agot_andal`,
  `language_agot_valyrian`, `language_agot_free_cities`,
  `language_agot_first_men`, `language_agot_dothraki`, `language_agot_ghis`,
  `language_agot_rhoyne`, `language_agot_hyrkoon`, `language_agot_yiti`, etc.).
- **5 custom ethos types** added alongside vanilla (`ethos_festive`,
  `ethos_mystic`, `ethos_methodical`, `ethos_assertive`, `ethos_fervent`).
- **`head_determination`** pillar is present on every culture (usually
  `head_determination_domain`, nomads use `head_determination_herd`).
- **`parents` and `created`** fields track culture divergence history and are
  used extensively.
- **`dlc_tradition`** blocks conditionally load DLC traditions with fallbacks.
- **`ethnicities`** are weighted lists of AGOT-custom ethnicity presets for
  character appearance.
- **Custom house CoA frames** (`house_coa_frame`, `house_coa_mask_offset`,
  `house_coa_mask_scale`) vary by heritage.
- **AGOT-specific traditions** (prefixed `tradition_agot_`) provide
  region-locked MaA, modifiers, and parameters.
- **Culture-related scripted triggers** like `agot_is_dornish_culture`,
  `agot_is_wildling_culture`, `agot_is_raiding_culture` are used in events and
  decisions.

## AGOT Culture Groups & Pillars

AGOT cultures are organized by heritage (defined in
`common/culture/pillars/00_agot_heritage.txt`). Each heritage maps to one of the
22 culture files in `common/culture/cultures/`.

| Heritage              | File                         | Example cultures                                                                                                           | Audio param |
| --------------------- | ---------------------------- | -------------------------------------------------------------------------------------------------------------------------- | ----------- |
| `heritage_andal`      | `00_agot_cul_andal.txt`      | `andal`, `crownlander`, `reachman`, `stormlander_main`, `westerman_main`, `riverman_main`, `valeman_main`, `stone_dornish` | `european`  |
| `heritage_first_man`  | `00_agot_cul_first_man.txt`  | `first_man`, `northman`, `skagosi`, `crannog`                                                                              | `european`  |
| `heritage_valyrian`   | `00_agot_cul_valyrian.txt`   | `valyrian_original`, `high_valyrian`, `westerosi_valyrian`, `essosi_valyrian`                                              | `byzantine` |
| `heritage_wildling`   | `00_agot_cul_wildling.txt`   | `first_clan`, `thenn`, `fangman`, `forestman`, `hornfoot`, `frozen_shoreman`, `moon_clan`                                  | `european`  |
| `heritage_ironman`    | `00_agot_cul_ironman.txt`    | `ironborn`, `greenborn`                                                                                                    | `european`  |
| `heritage_freecities` | `00_agot_cul_freecities.txt` | `braavosi`, `volantene`, `lyseni`, `pentoshi`, `tyroshi`, `myrish`                                                         | `byzantine` |
| `heritage_ghiscari`   | `00_agot_cul_ghiscari.txt`   | `meereenese`, `astapori`, `yunkish`                                                                                        | `mena`      |
| `heritage_rhoynar`    | `00_agot_cul_rhoynar.txt`    | `salt_dornish`, `sand_dornish`, `greenblood`, `orphan_rhoynar`                                                             | `mena`      |
| `heritage_grasslands` | `00_agot_cul_grasslands.txt` | `dothraki`, `jogos_nhai`                                                                                                   | `mena`      |
| `heritage_yitish`     | `00_agot_cul_yitish.txt`     | Yi Ti cultures                                                                                                             | `european`  |

Languages are in `common/culture/pillars/00_agot_language.txt`. Each includes
`ai_will_do` weighting and a `color` for the map. Note that many Westerosi
Andal-heritage cultures use `language_agot_westeros` (Common Tongue), not
`language_agot_andal`.

Custom ethos definitions are in `common/culture/pillars/00_agot_ethos.txt`:

- `ethos_festive` -- +1 diplomacy, +1 intrigue, +5 direct vassal opinion, +5
  county opinion
- `ethos_mystic` -- +1 intrigue, +10% monthly piety, -10% build speed
- `ethos_methodical` -- +1 prowess, -10% hard casualties, +10% development
  growth
- `ethos_assertive` -- -10% MaA maintenance, +10% hard casualties, cheaper
  truce-breaking
- `ethos_fervent` -- clergy can fight, cheaper piety CBs, +1 prowess

## AGOT-Specific Template

AGOT cultures are **flat** (no group wrapper). Here is the minimal structure:

### common/culture/cultures/my_agot_submod_cultures.txt

```
my_new_culture = {
	color = { 0.5 0.3 0.7 }

	ethos = ethos_bellicose
	heritage = heritage_andal
	language = language_agot_westeros
	martial_custom = martial_custom_male_only
	head_determination = head_determination_domain

	coa_gfx = {
		andal_coa_gfx
	}
	building_gfx = {
		western_building_gfx
	}
	clothing_gfx = {
		western_clothing_gfx
		andal_clothing_gfx
	}
	unit_gfx = {
		western_unit_gfx
	}
	house_coa_frame = house_frame_andal1
	house_coa_mask_offset = { 0.0 0.0 }
	house_coa_mask_scale = { 0.79500034 0.79500034 }

	traditions = {
		tradition_agot_vale            # Regional AGOT tradition
		tradition_chivalry             # Vanilla tradition (can be mixed)
		tradition_stalwart_defenders
	}

	ethnicities = {
		10 = Northmen_1
		10 = Northmen_2
		10 = Northmen_3
	}

	name_list = name_list_valeman

	# Culture divergence history (optional but recommended)
	parents = {
		valeman_main
	}
	created = 8300.1.1
}
```

### DLC-conditional traditions

AGOT cultures use `dlc_tradition` blocks to include DLC-dependent traditions
with fallbacks:

```
	dlc_tradition = {
		trait = tradition_fp2_state_ransoming
		requires_dlc_flag = the_fate_of_iberia
		fallback = tradition_sorcerous_metallurgy
	}
```

## Annotated AGOT Example

From `00_agot_cul_valyrian.txt` -- the Westerosi Valyrian culture (House
Targaryen's adopted culture):

```
westerosi_valyrian = {
	color = { 0.78 0.29 0.46 }

	# Pillars -- all 5 are required
	ethos = ethos_courtly                       # Vanilla ethos, used as-is
	heritage = heritage_valyrian                # AGOT heritage from 00_agot_heritage.txt
	language = language_agot_westeros           # Common Tongue, not Valyrian
	martial_custom = martial_custom_male_only   # Vanilla pillar
	head_determination = head_determination_domain  # AGOT pillar

	traditions = {
		tradition_agot_blackwater_bay           # AGOT regional tradition
		tradition_agot_western_valyrian         # AGOT unique tradition
		tradition_family_entrepreneurship       # Vanilla tradition
		tradition_maritime_mercantilism         # Vanilla tradition
		tradition_seafaring                     # Vanilla tradition
		tradition_fishermen                     # Vanilla tradition
	}

	name_list = name_list_westerosi_valyrian    # Custom AGOT name list

	# GFX -- uses andal CoA (culturally integrated) but valyrian clothing
	coa_gfx = { andal_coa_gfx }
	building_gfx = {
		crownlands_building_gfx                 # AGOT custom building GFX
		mediterranean_building_gfx              # Vanilla fallback
	}
	clothing_gfx = {
		westerosi_valyrian_clothing_gfx         # AGOT custom
		valyrian_clothing_gfx                   # AGOT custom
		western_clothing_gfx                    # Vanilla fallback
	}
	unit_gfx = {
		westerosi_valyrian_unit_gfx             # AGOT custom
		eastern_unit_gfx                        # Vanilla fallback
	}
	house_coa_frame = house_frame_andal1        # Andal-style frame (blended identity)
	house_coa_mask_offset = { 0.0 0.0 }
	house_coa_mask_scale = { 0.79500034 0.79500034 }

	ethnicities = {
		10 = Westerosi_valyrian_1               # Custom ethnicity presets
		10 = Westerosi_valyrian_2
		...
	}

	# Diverged from valyrian_original and andal
	parents = {
		valyrian_original
		andal
	}
	created = 7700.1.1                          # AGOT timeline date
}
```

## Key Differences from Vanilla

| Aspect                    | Vanilla                                                        | AGOT                                                                    |
| ------------------------- | -------------------------------------------------------------- | ----------------------------------------------------------------------- |
| **Culture grouping**      | Cultures nested inside a group block with `graphical_cultures` | Cultures are top-level; no group wrapper                                |
| **Heritage keys**         | `heritage_west_germanic`, `heritage_byzantine`, etc.           | `heritage_andal`, `heritage_valyrian`, `heritage_wildling`, etc.        |
| **Language keys**         | `language_germanic`, `language_latin`, etc.                    | `language_agot_westeros`, `language_agot_valyrian`, etc.                |
| **Ethos**                 | 7 vanilla types                                                | 7 vanilla + 5 AGOT-custom (`ethos_festive`, `ethos_mystic`, etc.)       |
| **`head_determination`**  | Not always present                                             | Present on every AGOT culture                                           |
| **`parents` / `created`** | Rarely used                                                    | Used extensively for divergence trees                                   |
| **`house_coa_frame`**     | Optional                                                       | Present on every AGOT culture                                           |
| **Traditions**            | All vanilla                                                    | Mix of vanilla + `tradition_agot_*` customs                             |
| **`dlc_tradition`**       | Optional                                                       | Used frequently with `requires_dlc_flag` + `fallback`                   |
| **Name lists**            | `name_list_german`, etc.                                       | `name_list_valeman`, `name_list_high_valyrian`, etc.                    |
| **Ethnicities**           | Vanilla presets                                                | AGOT custom ethnicity presets per culture                               |
| **`graphical_cultures`**  | Required in group block                                        | Does not exist; GFX set per-culture via `coa_gfx`, `clothing_gfx`, etc. |

## AGOT Pitfalls

- **Do not wrap cultures in a group block.** AGOT cultures are defined at the
  top level. Adding a group wrapper will cause load errors or create an
  unintended culture group that conflicts with AGOT's flat structure.
- **Use AGOT heritage keys.** Vanilla heritages like `heritage_west_germanic` do
  not exist. You must use one of the 22 AGOT heritages defined in
  `00_agot_heritage.txt`.
- **Use AGOT language keys.** Vanilla languages are removed. Use keys from
  `00_agot_language.txt` (e.g., `language_agot_westeros` for Common Tongue).
- **Include `head_determination`.** Every AGOT culture sets this pillar.
  Omitting it may cause fallback behavior or inconsistency.
- **Include `house_coa_frame` and mask fields.** AGOT relies on these for
  correct house CoA rendering. Copy values from a culture with the same
  heritage.
- **AGOT traditions have `is_shown` guards.** Many `tradition_agot_*` traditions
  are restricted to specific cultures or regions (e.g., `tradition_agot_vale`
  checks `world_westeros_the_vale`). Adding them to a culture outside that
  region may hide them from the UI or cause AI issues.
- **Use matching GFX keys.** AGOT defines many custom `_coa_gfx`,
  `_building_gfx`, `_clothing_gfx`, and `_unit_gfx` entries. Using vanilla GFX
  keys as fallback is fine, but primary entries should match your culture's
  visual identity in AGOT.
- **High Valyrian conversion rules.** AGOT has game rules
  (`agot_hv_conversion_disallowed`, `agot_hv_conversion_unrestricted`) and
  triggers (`agot_is_westerosi_high_valyrian`, `agot_is_essosi_high_valyrian`)
  that restrict culture conversion to/from `high_valyrian`. Be aware of these if
  your submod interacts with Valyrian culture.
- **Wildling culture detection uses a variable.** The trigger
  `agot_is_wildling_culture` checks `has_variable = wildling_culture`, not
  heritage. If you create a new wildling culture, you may need to set this
  variable for AGOT events to recognize it.
- **`parents` and `created` are not cosmetic.** AGOT scripted triggers like
  `agot_is_dornish_culture` check `any_parent_culture_or_above` to match culture
  families. If your culture descends from an AGOT culture, set `parents`
  correctly or these triggers will miss it.
- **Provide localization.** You need `l_english` keys for: the culture name,
  `_desc`, and the name list. AGOT also expects localization for any custom
  traditions you create.
