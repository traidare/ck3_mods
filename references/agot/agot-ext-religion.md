# AGOT Extension: Religion

> This guide extends the religion section of
> [references/patterns/culture-religion.md](../patterns/culture-religion.md)
> with AGOT-specific changes.

## What AGOT Changes

AGOT replaces **all** vanilla religions with an entirely new set of religions
for Planetos. The vanilla religion families (`rf_pagan`, `rf_christian`, etc.)
are replaced by six AGOT-specific families. Every vanilla hostility doctrine,
pantheon doctrine, and syncretism doctrine is replaced with AGOT equivalents.

Key structural changes:

- **6 custom religion families** instead of vanilla's families
- **22 religion files** in `common/religion/religions/`, each containing a
  religion with multiple faiths
- **Custom pantheon doctrines** per religion (e.g.,
  `doctrine_pantheon_the_seven`, `doctrine_pantheon_old_gods`,
  `doctrine_pantheon_rhllor`)
- **AGOT syncretism doctrines** that control which religions can syncretize with
  each other (e.g., `doctrine_syncretism_the_faith`,
  `doctrine_syncretism_the_pact`)
- **Special invisible doctrines** used to tag faiths for scripted triggers
  (`special_doctrine_agot_is_seven_faith`,
  `special_doctrine_agot_is_pact_faith`, etc.)
- **Custom tenets** specific to Planetos lore (e.g., `tenet_weirwoods`,
  `tenet_heart_of_fire`, `tenet_greensight`, `tenet_shadowbinding`)
- **`special_doctrine_agot_uncreated`** on certain faiths to prevent players
  from creating them in the faith editor

## AGOT Religion Families

Defined in `common/religion/religion_families/`. Each family sets the graphical
style, piety icon group, hostility doctrine, and background icon.

| Family             | File                           | Key Properties                                                                                                                    |
| ------------------ | ------------------------------ | --------------------------------------------------------------------------------------------------------------------------------- |
| `rf_sunset`        | `00_agot_rf_sunset.txt`        | `graphical_faith = fots_god_gfx`, `piety_icon_group = "christian"`, `hostility_doctrine = sunset_hostility_doctrine`              |
| `rf_azorian`       | `00_agot_rf_azor.txt`          | `graphical_faith = dawnbringer_god_gfx`, `piety_icon_group = "christian"`, `hostility_doctrine = azorian_hostility_doctrine`      |
| `rf_dawn`          | `00_agot_rf_dawn.txt`          | `graphical_faith = yitish_god_gfx`, `piety_icon_group = "pagan"`, `hostility_doctrine = dawn_hostility_doctrine`                  |
| `rf_western_essos` | `00_agot_rf_western_essos.txt` | `graphical_faith = free_cities_god_gfx`, `piety_icon_group = "eastern"`, `hostility_doctrine = western_essosi_hostility_doctrine` |
| `rf_grasslands`    | `00_agot_rf_grasslands.txt`    | `graphical_faith = free_cities_god_gfx`, `piety_icon_group = "islam"`, `is_pagan = yes`                                           |
| `rf_southseas`     | `00_agot_rf_southsea.txt`      | `graphical_faith = summer_god_gfx`, `piety_icon_group = "pagan"`, `is_pagan = yes`                                                |

**Religion-to-family mapping (selected):**

| Religion                                        | Family          | File                         |
| ----------------------------------------------- | --------------- | ---------------------------- |
| `the_seven_religion` (Faith of the Seven)       | `rf_sunset`     | `00_agot_the_seven.txt`      |
| `the_pact_religion` (Old Gods)                  | `rf_sunset`     | `00_agot_the_pact.txt`       |
| `the_rhllor_religion` (R'hllor)                 | `rf_azorian`    | `00_agot_the_rhllor.txt`     |
| `the_shanties_religion` (Drowned God, etc.)     | `rf_southseas`  | `00_agot_the_shanties.txt`   |
| `the_houses_religion` (Qartheen Warlocks, etc.) | `rf_grasslands` | `00_agot_the_houses.txt`     |
| `the_first_gods_religion`                       | varies          | `00_agot_the_first_gods.txt` |
| `the_others_religion`                           | varies          | `00_agot_the_others.txt`     |

Full list of religion files: `the_chosen`, `the_churches`, `the_counsels`,
`the_courts`, `the_cults`, `the_first_gods`, `the_flames`, `the_flocks`,
`the_graces`, `the_houses`, `the_liturgies`, `the_mother`, `the_orders`,
`the_others`, `the_pact`, `the_rhllor`, `the_seven`, `the_shanties`,
`the_songs`, `the_temples`, `the_venerations`, `the_ways`.

## Holy Sites in Planetos

Holy sites are defined in `common/religion/holy_sites/00_agot_holy_sites.txt`
(plus `00_holy_sites.txt` for additional entries). Each holy site references an
AGOT county and barony.

Example holy site definitions:

```
# Faith of the Seven holy sites
starry_sept = {
    county = c_oldtown
    barony = b_the_starry_sept
    character_modifier = {
        religious_vassal_opinion = 10
    }
}

sept_great = {
    county = c_kings_landing
    barony = b_visenyas_hill
    character_modifier = {
        religious_head_opinion = 10
    }
}

# Old Gods holy sites
winterfell = {
    county = c_winterfell
    barony = b_winterfell
    character_modifier = {
        garrison_size = 0.1
    }
}

gods_eye = {
    county = c_harrenhal
    barony = b_harrenhal
    character_modifier = {
        monthly_piety_gain_mult = 0.05
    }
}

# R'hllor holy sites
dragonstone = {
    county = c_dragonstone
    barony = b_dragonstone
    character_modifier = {
        same_faith_opinion = 10
    }
}
```

Holy sites are assigned **at the faith level**, not the religion level. Some
faiths share holy sites (e.g., `dragonstone` is used by both `rhllor_fc` and
`rhllor_fots`). AGOT faiths typically have 5-7 holy sites each.

## AGOT-Specific Patterns

### Special Invisible Doctrines

AGOT uses invisible doctrines to tag religions for scripted logic. Defined in
`common/religion/doctrines/00_agot_doctrines_special.txt`:

```
# Prevents faith from being created in the faith editor
agot_uncreated = {
    group = special_invisible
    is_available_on_create = { always = no }
    special_doctrine_agot_uncreated = {
        visible = no
    }
}

# Tags a faith as belonging to a specific religion group
agot_is_seven_faith = {
    group = special_invisible
    is_available_on_create = {
        has_doctrine = special_doctrine_agot_is_seven_faith
    }
    special_doctrine_agot_is_seven_faith = {
        visible = no
    }
}
```

Every religion applies `special_doctrine_agot_is_any_faith` plus a
religion-specific tag at the religion level:

```
the_seven_religion = {
    # ...
    doctrine = special_doctrine_agot_is_any_faith
    doctrine = special_doctrine_agot_is_seven_faith
    # ...
}
```

### Custom Pantheon Doctrines

AGOT defines custom pantheon doctrines in
`common/religion/doctrines/00_agot_doctrines.txt`. These are religion-locked via
`can_pick`:

```
doctrine_pantheon_the_seven = {
    icon = doctrine_syncretism_the_faith
    can_pick = {
        religion_tag = the_seven_religion
    }
    piety_cost = {
        value = faith_doctrine_cost_high
        if = {
            limit = { has_doctrine = doctrine_pantheon_the_seven }
            multiply = faith_unchanged_doctrine_cost_mult
        }
    }
    parameters = {
        faith_of_the_seven_patrons = yes
    }
}
```

Variants exist for syncretic pantheons: `doctrine_pantheon_the_seven_old_gods`
(can be picked by both `the_seven_religion` and `the_pact_religion`),
`doctrine_pantheon_the_seven_qarlon`, `doctrine_pantheon_the_seven_baelor`.

### AGOT Syncretism Doctrines

Faiths use AGOT-specific syncretism doctrines instead of vanilla ones. These
control inter-religion tolerance:

```
# In a faith definition:
doctrine = doctrine_syncretism_the_faith    # Syncretic with Faith of the Seven
doctrine = doctrine_syncretism_the_pact     # Syncretic with Old Gods
doctrine = doctrine_syncretism_the_cults    # Syncretic with cult religions
doctrine = doctrine_syncretism_the_churches # Syncretic with church religions
```

### Scripted Triggers for Religion Checks

AGOT provides scripted triggers in
`common/scripted_triggers/00_agot_religious_triggers.txt` for checking religion
membership:

```
# Check if a character believes in some form of the Seven
agot_believes_in_the_seven = {
    faith = {
        OR = {
            has_doctrine = doctrine_pantheon_the_seven
            has_doctrine = doctrine_pantheon_the_seven_old_gods
            has_doctrine = doctrine_pantheon_the_seven_qarlon
            has_doctrine = doctrine_pantheon_the_seven_baelor
            has_doctrine = doctrine_pantheon_the_seven_drowned_god
            has_doctrine = doctrine_pantheon_the_seven_valyrian
        }
    }
}

# Check if a faith supports patron god selection
agot_faith_has_patron_gods = {
    OR = {
        has_doctrine_parameter = faith_of_the_seven_patrons
        has_doctrine_parameter = faith_of_eight_patrons
        has_doctrine_parameter = summer_gods_patrons
        has_doctrine_parameter = yiti_imperial_patrons
        has_doctrine_parameter = braavosi_patrons
        # ... many more
    }
}

# Check if character is High Septon
agot_is_high_septon = {
    trigger_if = {
        limit = { is_alive = yes }
        has_title = title:k_the_most_devout
    }
    trigger_else = {
        primary_title = title:k_the_most_devout
    }
}
```

### Scripted Effects for Religion

AGOT provides effects in `common/scripted_effects/00_agot_religion_effects.txt`,
including:

- `agot_upgrade_blasphemous_sacrifice_effect` -- stacking modifier for
  sacrifices
- `agot_grab_spouses_and_family_to_convert_effect` -- handles family conversion
  cascades

## AGOT-Specific Template

### Adding a new faith to an existing AGOT religion

```
# common/religion/religions/zz_my_submod_faith.txt
the_seven_religion = {
    faiths = {
        my_new_seven_faith = {
            icon = fots  # Must use an existing AGOT icon or define your own

            # Tenets (pick from AGOT custom tenets + vanilla tenets)
            doctrine = tenet_knighthood
            doctrine = tenet_monasticism
            doctrine = tenet_communal_identity
            doctrine = tenet_the_most_devout  # AGOT-specific tenet
            doctrine = tenet_adaptive

            # Main Doctrines
            doctrine = doctrine_gender_male_dominated
            doctrine = doctrine_pluralism_pluralistic
            doctrine = doctrine_theocracy_temporal
            doctrine = doctrine_spiritual_head
            doctrine = doctrine_pantheon_the_seven        # AGOT pantheon doctrine
            doctrine = doctrine_pilgrimage_encouraged
            doctrine = doctrine_syncretism_the_pact       # AGOT syncretism doctrine

            # Marriage Doctrines
            doctrine = doctrine_monogamy
            doctrine = doctrine_divorce_approval
            doctrine = doctrine_bastardry_legitimization
            doctrine = doctrine_consanguinity_cousins

            # Criminology Doctrines
            doctrine = doctrine_homosexuality_shunned
            doctrine = doctrine_deviancy_crime
            doctrine = doctrine_adultery_men_shunned
            doctrine = doctrine_adultery_women_crime
            doctrine = doctrine_kinslaying_close_kin_crime
            doctrine = doctrine_witchcraft_crime
            doctrine = doctrine_slavery_crime

            # Clerical Doctrines
            doctrine = doctrine_clerical_function_alms_and_pacification
            doctrine = doctrine_clerical_gender_male_only
            doctrine = doctrine_clerical_marriage_disallowed
            doctrine = doctrine_clerical_succession_spiritual_fixed_appointment
            doctrine = doctrine_anointment_permitted

            # Optional: prevent creation in faith editor
            # doctrine = special_doctrine_agot_uncreated

            color = { 200 180 120 }

            # Holy sites -- use AGOT holy site keys
            holy_site = starry_sept
            holy_site = sept_great
            holy_site = highgarden
            holy_site = seven_stars
            holy_site = stoney_sept

            # Optional: set a religious head
            # religious_head = k_the_most_devout

            # Faith-level localization overrides (optional)
            localization = {
                HighGodName = my_faith_high_god_name
                HighGodName2 = my_faith_high_god_name_2
                # ... full localization block if different from religion defaults
            }
        }
    }
}
```

### Adding a new AGOT religion (new religion + family)

```
# common/religion/religion_families/zz_my_family.txt
rf_my_family = {
    graphical_faith = fots_god_gfx          # Reuse an AGOT graphical faith
    piety_icon_group = "pagan"
    hostility_doctrine = my_hostility_doctrine  # Must define this doctrine
    doctrine_background_icon = core_tenet_banner_pagan.dds
    # is_pagan = yes  # Optional
}
```

```
# common/religion/religions/zz_my_religion.txt
my_planetos_religion = {
    family = rf_my_family
    doctrine = my_hostility_doctrine
    graphical_faith = fots_god_gfx

    # Tag for scripted logic
    doctrine = special_doctrine_agot_is_any_faith

    traits = {
        virtues = { brave generous just }
        sins = { craven greedy arbitrary }
    }

    custom_faith_icons = {
        fots_extra_1
        fots_extra_2
        # ... reuse AGOT icons
    }

    localization = {
        HighGodName = my_religion_high_god_name
        # ... full localization block (see Annotated Example below)
    }

    faiths = {
        my_faith = {
            icon = fots_extra_1
            # ... full faith definition
        }
    }
}
```

## Annotated AGOT Example

The Faith of the Seven (`fots_seven`) from `00_agot_the_seven.txt`:

```
the_seven_religion = {
    family = rf_sunset                       # Uses Westeros religion family
    doctrine = sunset_hostility_doctrine     # Hostility toward other rf_sunset religions
    graphical_faith = fots_god_gfx           # AGOT visual style for the Seven

    traits = {
        virtues = {
            just = 0.5          # Weighted virtues (0.5 = half weight for AI)
            compassionate = 0.5
            chaste = 0.5
            diligent = 0.5
            brave = 0.5
            patient = 0.5
            humble = 0.5
        }
        sins = {
            arbitrary           # Default weight (1.0)
            sadistic
            lazy
            lustful
            craven
            impatient
            arrogant
        }
    }

    # Invisible tagging doctrines
    doctrine = special_doctrine_agot_is_any_faith
    doctrine = special_doctrine_agot_is_seven_faith

    localization = {
        HighGodName = fots_seven_high_god_name           # "The Seven"
        HighGodNameSheHe = CHARACTER_SHEHE_HE
        # ... 70+ localization keys for god names, pronouns, terms
        HouseOfWorship = fots_seven_house_of_worship     # "Sept"
        PriestMale = fots_seven_priest_male              # "Septon"
        PriestFemale = fots_seven_priest_female           # "Septa"
        BishopMale = fots_seven_bishop_male              # "Most Devout"
        DevoteeMale = fots_seven_devotee_male            # "Pious"
        ReligiousText = fots_seven_religious_text        # "The Seven-Pointed Star"
    }

    faiths = {
        fots_seven = {                                   # Main Faith of the Seven
            icon = fots
            religious_head = k_the_most_devout           # High Septon title

            # Tenets
            doctrine = tenet_knighthood                  # AGOT custom tenet
            doctrine = tenet_the_most_devout             # AGOT custom tenet
            doctrine = tenet_monasticism
            doctrine = tenet_communal_identity
            doctrine = tenet_adaptive

            # Main Doctrines
            doctrine = doctrine_gender_male_dominated
            doctrine = doctrine_pluralism_pluralistic
            doctrine = doctrine_theocracy_temporal
            doctrine = doctrine_spiritual_head
            doctrine = doctrine_pantheon_the_seven       # AGOT custom pantheon
            doctrine = doctrine_pilgrimage_encouraged
            doctrine = doctrine_syncretism_the_pact      # Syncretic with Old Gods

            # Marriage
            doctrine = doctrine_monogamy
            doctrine = doctrine_divorce_approval
            doctrine = doctrine_bastardry_legitimization
            doctrine = doctrine_consanguinity_cousins

            # Crimes
            doctrine = doctrine_homosexuality_shunned
            doctrine = doctrine_deviancy_crime
            doctrine = doctrine_adultery_men_shunned
            doctrine = doctrine_adultery_women_crime
            doctrine = doctrine_kinslaying_close_kin_crime
            doctrine = doctrine_witchcraft_crime
            doctrine = doctrine_slavery_crime

            # Clergy
            doctrine = doctrine_clerical_function_alms_and_pacification
            doctrine = doctrine_clerical_gender_male_only
            doctrine = doctrine_clerical_marriage_disallowed
            doctrine = doctrine_clerical_succession_spiritual_fixed_appointment
            doctrine = doctrine_anointment_permitted

            color = { 224 211 140 }

            # 7 holy sites across Westeros
            holy_site = starry_sept
            holy_site = sept_great
            holy_site = highgarden
            holy_site = seven_stars
            holy_site = sept_snows
            holy_site = stoney_sept
            holy_site = hugors_hill
        }
    }
}
```

## Key Differences from Vanilla

| Aspect               | Vanilla                                                          | AGOT                                                                                                                                               |
| -------------------- | ---------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| Religion families    | `rf_pagan`, `rf_christian`, `rf_islamic`, etc.                   | `rf_sunset`, `rf_azorian`, `rf_dawn`, `rf_western_essos`, `rf_grasslands`, `rf_southseas`                                                          |
| Hostility doctrines  | `abrahamic_hostility_doctrine`, `pagan_hostility_doctrine`, etc. | `sunset_hostility_doctrine`, `azorian_hostility_doctrine`, `dawn_hostility_doctrine`, etc.                                                         |
| Pantheon doctrines   | None (vanilla uses generic doctrines)                            | Custom per religion: `doctrine_pantheon_the_seven`, `doctrine_pantheon_old_gods`, `doctrine_pantheon_rhllor`, etc.                                 |
| Syncretism doctrines | `doctrine_is_christian_syncretism`, etc.                         | `doctrine_syncretism_the_faith`, `doctrine_syncretism_the_pact`, `doctrine_syncretism_the_cults`, etc.                                             |
| Special doctrines    | None                                                             | `special_doctrine_agot_is_any_faith`, `special_doctrine_agot_is_seven_faith`, `special_doctrine_agot_uncreated`, etc.                              |
| Holy site locations  | Historical Earth baronies                                        | Planetos baronies (`b_the_starry_sept`, `b_winterfell`, `b_dragonstone`, etc.)                                                                     |
| Virtue weights       | All 1.0                                                          | Some religions use weighted virtues (e.g., `just = 0.5` in the Seven)                                                                              |
| Faith-level loc      | Rare overrides                                                   | Very common -- most faiths override the full localization block                                                                                    |
| `pagan_roots`        | On pagan religions                                               | Used selectively (e.g., `the_pact_religion` has `pagan_roots = yes`)                                                                               |
| Graphical faiths     | Vanilla GFX                                                      | AGOT-specific: `fots_god_gfx`, `old_gods_gfx`, `drowned_god_gfx`, `dawnbringer_god_gfx`, `yitish_god_gfx`, `free_cities_god_gfx`, `summer_god_gfx` |
| Scripted triggers    | `is_christian_trigger` etc.                                      | `agot_believes_in_the_seven`, `agot_faith_has_patron_gods`, `agot_is_high_septon`                                                                  |

## AGOT Pitfalls

- **Do not reference vanilla religion families.** Families like `rf_pagan` or
  `rf_christian` do not exist in AGOT. Use the six AGOT families listed above.
- **Do not reference vanilla holy sites.** Sites like `jerusalem`, `rome`,
  `mecca` do not exist. All holy sites use AGOT Planetos locations.
- **Pantheon doctrines are religion-locked.** `doctrine_pantheon_the_seven` has
  `can_pick = { religion_tag = the_seven_religion }`. You cannot assign it to a
  faith in a different religion. Define a new pantheon doctrine if needed.
- **Every faith needs a syncretism doctrine.** AGOT faiths almost always include
  one `doctrine_syncretism_*` doctrine. Without it, the faith may behave
  unexpectedly with inter-faith relations.
- **Localization is massive.** AGOT religions define 70+ localization keys at
  the religion level (god names, pronouns, terms for priests, worship places,
  afterlife, etc.). Faiths that differ from the religion defaults must override
  the entire block.
- **`special_doctrine_agot_uncreated` blocks faith creation.** If you add this
  to your faith, players cannot create or reform it. This is intentional for
  lore-locked faiths.
- **Use `special_doctrine_agot_is_any_faith`** on new religions. AGOT scripted
  triggers check for this doctrine to identify AGOT faiths. If your religion
  lacks it, AGOT events and decisions may not fire correctly.
- **Custom tenets exist.** AGOT adds tenets like `tenet_weirwoods`,
  `tenet_heart_of_fire`, `tenet_greensight`, `tenet_shadowbinding`,
  `tenet_the_most_devout`, `tenet_knighthood`. Check existing religion files for
  available AGOT tenets before creating new ones.
- **Faith-level `holy_site` overrides.** In AGOT, holy sites are commonly
  declared per-faith (inside the faith block) rather than relying on
  religion-level defaults. Some faiths within the same religion have completely
  different holy sites.
- **Conversion is restricted.** The `agot_can_convert` trigger limits AI
  conversion to R'hllor faiths only. If you add a new proselytizing faith, be
  aware AI may not convert to it without modifying this trigger.
