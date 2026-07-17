#!/usr/bin/env python3
"""Generate complete CK3 overrides for the ANT AGOT Vanilla balance patch."""

from __future__ import annotations

import math
import os
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def required_environment_path(name: str) -> Path:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(
            f"{name} is not set; load .env through direnv or run the generator through just"
        )
    return Path(value).expanduser().resolve()


WORKSHOP = required_environment_path("CK3_WORKSHOP_DIR")
ANT = WORKSHOP / "3241130652"
ANT_AGOT = WORKSHOP / "3371298408"
OUT = ROOT / "mods" / "ant_agot_vanilla_balance"


def read(path: Path) -> str:
    if not path.is_file():
        raise SystemExit(f"missing required source: {path}")
    return path.read_text(encoding="utf-8-sig")


def matching_brace(text: str, opening: int) -> int:
    depth = 0
    quoted = False
    escaped = False
    comment = False
    for index in range(opening, len(text)):
        char = text[index]
        if comment:
            if char == "\n":
                comment = False
            continue
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
            continue
        if char == "#":
            comment = True
        elif char == '"':
            quoted = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index
    raise ValueError("unclosed brace")


def extract(text: str, name: str) -> str:
    match = re.search(rf"(?m)^{re.escape(name)}\s*=\s*\{{", text)
    if not match:
        raise ValueError(f"missing definition: {name}")
    opening = text.find("{", match.start())
    closing = matching_brace(text, opening)
    end = closing + 1
    while end < len(text) and text[end] in " \t":
        end += 1
    if end < len(text) and text[end] == "\r":
        end += 1
    if end < len(text) and text[end] == "\n":
        end += 1
    return text[match.start() : end]


def subblock_span(block: str, key: str) -> tuple[int, int] | None:
    match = re.search(rf"(?m)^\s*{re.escape(key)}\s*=\s*\{{", block)
    if not match:
        return None
    opening = block.find("{", match.start())
    closing = matching_brace(block, opening)
    end = closing + 1
    while end < len(block) and block[end] in " \t":
        end += 1
    if end < len(block) and block[end] == "\r":
        end += 1
    if end < len(block) and block[end] == "\n":
        end += 1
    return match.start(), end


def replace_subblock(block: str, key: str, replacement: str | None) -> str:
    span = subblock_span(block, key)
    if span is None:
        if replacement is None:
            return block
        raise ValueError(f"missing nested block {key}")
    start, end = span
    return block[:start] + (replacement or "") + block[end:]


def replace_once(block: str, old: str, new: str) -> str:
    count = block.count(old)
    if count != 1:
        raise ValueError(f"expected one occurrence of {old!r}, found {count}")
    return block.replace(old, new, 1)


def replace_field(block: str, field: str, value: int | float, count: int = 1) -> str:
    pattern = re.compile(rf"(?m)^(\s*{re.escape(field)}\s*=\s*)(-?\d+(?:\.\d+)?)")
    matches = list(pattern.finditer(block))
    if len(matches) != count:
        raise ValueError(f"{field}: expected {count} values, found {len(matches)}")
    return pattern.sub(lambda match: match.group(1) + number(value), block)


def number(value: int | float) -> str:
    if isinstance(value, int) or float(value).is_integer():
        return str(int(value))
    return f"{value:.3f}".rstrip("0").rstrip(".")


def modifier_block(name: str, values: list[tuple[str, int | float | str]]) -> str:
    if not values:
        return ""
    lines = [f"\t{name} = {{"]
    lines.extend(
        f"\t\t{key} = {number(value) if isinstance(value, (int, float)) else value}"
        for key, value in values
    )
    lines.append("\t}\n")
    return "\n".join(lines)


def write(relative: str, content: str) -> None:
    path = OUT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8-sig")


def generate_traditions() -> None:
    base_source = read(ANT_AGOT / "common/culture/traditions/ary_traditions.txt")
    upgrade_source = read(ANT / "common/culture/traditions/ary_traditions_upgrade.txt")
    names = [
        "vv_tradition_more_1",
        "vv_tradition_ice_age1",
        "vv_tradition_true_knight",
        "vv_tradition_cof",
        "vv_tradition_maatg",
        "vv_tradition_tb",
        "vv_tradition_sbl",
        "vv_tradition_supremeblood",
        "vv_tradition_loalamut",
    ]
    blocks = {name: extract(base_source, name) for name in names}

    changes: dict[str, list[tuple[str, str]]] = {
        "vv_tradition_more_1": [
            ("culture_tradition_max_add = 5", "culture_tradition_max_add = 2")
        ],
        "vv_tradition_ice_age1": [
            ("elephant_cavalry_max_size_add = 3", "elephant_cavalry_max_size_add = 1"),
            (
                "elephant_cavalry_damage_mult = 0.2",
                "elephant_cavalry_damage_mult = 0.1",
            ),
            (
                "elephant_cavalry_toughness_mult = 0.2",
                "elephant_cavalry_toughness_mult = 0.1",
            ),
            (
                "elephant_cavalry_pursuit_mult = 0.2",
                "elephant_cavalry_pursuit_mult = 0.1",
            ),
            (
                "elephant_cavalry_screen_mult = 0.2",
                "elephant_cavalry_screen_mult = 0.1",
            ),
            (
                "elephant_cavalry_maintenance_mult = -0.1",
                "elephant_cavalry_maintenance_mult = -0.05",
            ),
        ],
        "vv_tradition_true_knight": [
            ("\t\tactive_accolades = 3\n", ""),
            ("knight_limit = 4", "knight_limit = 2"),
            ("knight_effectiveness_mult = 1.25", "knight_effectiveness_mult = 0.5"),
            ("negate_prowess_penalty_add = 5", "negate_prowess_penalty_add = 2"),
            ("levy_size = -0.5", "levy_size = -0.3"),
            ("levy_maintenance = 1", "levy_maintenance = 0.5"),
        ],
        "vv_tradition_cof": [("\t\tno_limit_to_kingdom_level_holy_wars = yes\n", "")],
        "vv_tradition_maatg": [
            ("men_at_arms_cap = 2", "men_at_arms_cap = 1"),
            ("men_at_arms_limit = 2", "men_at_arms_limit = 1"),
            (
                "men_at_arms_recruitment_cost = -0.2",
                "men_at_arms_recruitment_cost = -0.1",
            ),
        ],
        "vv_tradition_tb": [
            ("additional_fort_level = 4", "additional_fort_level = 2"),
            ("garrison_size = 0.2", "garrison_size = 0.1"),
            ("domain_limit = 2", "domain_limit = 1"),
            ("domicile_build_gold_cost = -0.15", "domicile_build_gold_cost = -0.1"),
            ("build_gold_cost = -0.15", "build_gold_cost = -0.1"),
            ("build_piety_cost = -0.15", "build_piety_cost = -0.1"),
            ("build_prestige_cost = -0.15", "build_prestige_cost = -0.1"),
            ("build_speed = -0.15", "build_speed = -0.1"),
            ("development_growth_factor = 0.1", "development_growth_factor = 0.05"),
        ],
        "vv_tradition_sbl": [
            ("inbreeding_chance = -0.95", "inbreeding_chance = -0.25"),
            (
                "negative_inactive_inheritance_chance = -0.50",
                "negative_inactive_inheritance_chance = -0.15",
            ),
            (
                "genetic_trait_strengthen_chance = 0.40",
                "genetic_trait_strengthen_chance = 0.15",
            ),
            (
                "positive_inactive_inheritance_chance = 0.40",
                "positive_inactive_inheritance_chance = 0.15",
            ),
        ],
        "vv_tradition_supremeblood": [
            ("learning = 5", "learning = 2"),
            ("prowess = 5", "prowess = 2"),
            (
                "monthly_lifestyle_xp_gain_mult = -0.4",
                "monthly_lifestyle_xp_gain_mult = -0.2",
            ),
            ("monthly_piety_gain_mult = -0.4", "monthly_piety_gain_mult = -0.2"),
            ("monthly_prestige_gain_mult = -0.4", "monthly_prestige_gain_mult = -0.2"),
            ("monthly_influence_mult = -0.4", "monthly_influence_mult = -0.2"),
            ("life_expectancy = 300", "life_expectancy = 10"),
            ("years_of_fertility = 260", "years_of_fertility = 3"),
            ("health = 2", "health = 0.5"),
            (
                "negative_inactive_inheritance_chance = -0.25",
                "negative_inactive_inheritance_chance = -0.15",
            ),
            ("levy_attack = 25", "levy_attack = 10"),
            ("levy_toughness = 25", "levy_toughness = 10"),
            ("levy_pursuit = 10", "levy_pursuit = 5"),
            ("levy_screen = 10", "levy_screen = 5"),
            ("levy_size = -0.7", "levy_size = -0.4"),
            ("levy_reinforcement_rate = -0.7", "levy_reinforcement_rate = -0.4"),
            ("hard_casualty_modifier = -0.2", "hard_casualty_modifier = -0.1"),
        ],
        "vv_tradition_loalamut": [
            ("dread_loss_mult = -0.25", "dread_loss_mult = -0.15"),
            (
                "owned_hostile_scheme_success_chance_add = 10",
                "owned_hostile_scheme_success_chance_add = 5",
            ),
            (
                "owned_personal_scheme_success_chance_add = 10",
                "owned_personal_scheme_success_chance_add = 5",
            ),
            (
                "enemy_personal_scheme_success_chance_add = -25",
                "enemy_personal_scheme_success_chance_add = -15",
            ),
            (
                "enemy_hostile_scheme_success_chance_add = -25",
                "enemy_hostile_scheme_success_chance_add = -15",
            ),
            (
                "enemy_hostile_scheme_phase_duration_add = 30",
                "enemy_hostile_scheme_phase_duration_add = 15",
            ),
            (
                "enemy_hostile_scheme_success_chance_growth_add = -10",
                "enemy_hostile_scheme_success_chance_growth_add = -5",
            ),
            (
                "enemy_hostile_scheme_success_chance_max_add = -10",
                "enemy_hostile_scheme_success_chance_max_add = -5",
            ),
            ("skirmishers_siege_value_add = 0.2", "skirmishers_siege_value_add = 0.1"),
            ("skirmishers_damage_mult = 0.2", "skirmishers_damage_mult = 0.1"),
            ("skirmishers_toughness_mult = 0.2", "skirmishers_toughness_mult = 0.1"),
            ("skirmishers_pursuit_mult = 0.2", "skirmishers_pursuit_mult = 0.1"),
            ("skirmishers_screen_mult = 0.2", "skirmishers_screen_mult = 0.1"),
            ("skirmishers_max_size_add = 3", "skirmishers_max_size_add = 1"),
            (
                "heavy_infantry_maintenance_mult = 1",
                "heavy_infantry_maintenance_mult = 0.5",
            ),
            (
                "archer_cavalry_maintenance_mult = 1",
                "archer_cavalry_maintenance_mult = 0.5",
            ),
            (
                "heavy_cavalry_maintenance_mult = 1",
                "heavy_cavalry_maintenance_mult = 0.5",
            ),
            ("movement_speed = 0.1", "movement_speed = 0.05"),
            ("retreat_losses = -0.3", "retreat_losses = -0.15"),
            (
                "enemy_hard_casualty_modifier = 0.3",
                "enemy_hard_casualty_modifier = 0.15",
            ),
            ("hard_casualty_modifier = -0.2", "hard_casualty_modifier = -0.1"),
            (
                "character_travel_safety_mult = 0.1",
                "character_travel_safety_mult = 0.05",
            ),
            (
                "uncontrolled_province_advantage = 10",
                "uncontrolled_province_advantage = 5",
            ),
            (
                "nomad_government_vassal_opinion = -100",
                "nomad_government_vassal_opinion = -50",
            ),
        ],
    }
    for name, replacements in changes.items():
        for old, new in replacements:
            blocks[name] = replace_once(blocks[name], old, new)

    upgrade_names = [
        "vv_tradition_by_lance2",
        "vv_tradition_btsas2",
        "vv_tradition_by_the_arrow2",
        "vv_tradition_ice_age2",
        "vv_tradition_supremeblood2",
        "vv_tradition_true_knight2",
        "vv_tradition_tb2",
    ]
    upgrades = {name: extract(upgrade_source, name) for name in upgrade_names}

    for name in (
        "vv_tradition_by_lance2",
        "vv_tradition_btsas2",
        "vv_tradition_by_the_arrow2",
    ):
        upgrades[name] = re.sub(
            r"(_(?:damage|toughness|pursuit|screen)_mult\s*=\s*)0\.2",
            r"\g<1>0.15",
            upgrades[name],
        )
        upgrades[name] = re.sub(
            r"(_maintenance_mult\s*=\s*)-0\.15", r"\g<1>-0.1", upgrades[name]
        )
        upgrades[name] = re.sub(
            r"(_recruitment_cost_mult\s*=\s*)-0\.2", r"\g<1>-0.1", upgrades[name]
        )
        upgrades[name] = re.sub(r"(_max_size_add\s*=\s*)5", r"\g<1>2", upgrades[name])
    for old, new in [
        ("movement_speed = 0.25", "movement_speed = 0.1"),
        ("enemy_hard_casualty_modifier = 0.25", "enemy_hard_casualty_modifier = 0.1"),
        ("character_travel_speed_mult = 0.25", "character_travel_speed_mult = 0.1"),
    ]:
        upgrades["vv_tradition_by_lance2"] = replace_once(
            upgrades["vv_tradition_by_lance2"], old, new
        )
    upgrades["vv_tradition_by_the_arrow2"] = replace_once(
        upgrades["vv_tradition_by_the_arrow2"],
        "enemy_terrain_advantage = -0.3",
        "enemy_terrain_advantage = -0.1",
    )

    for old, new in [
        ("elephant_cavalry_max_size_add = 5", "elephant_cavalry_max_size_add = 2"),
        ("elephant_cavalry_damage_mult = 0.2", "elephant_cavalry_damage_mult = 0.15"),
        (
            "elephant_cavalry_toughness_mult = 0.2",
            "elephant_cavalry_toughness_mult = 0.15",
        ),
        ("elephant_cavalry_pursuit_mult = 0.2", "elephant_cavalry_pursuit_mult = 0.15"),
        ("elephant_cavalry_screen_mult = 0.2", "elephant_cavalry_screen_mult = 0.15"),
        (
            "elephant_cavalry_maintenance_mult = -0.15",
            "elephant_cavalry_maintenance_mult = -0.1",
        ),
        (
            "elephant_cavalry_recruitment_cost_mult = -0.2",
            "elephant_cavalry_recruitment_cost_mult = -0.1",
        ),
    ]:
        upgrades["vv_tradition_ice_age2"] = replace_once(
            upgrades["vv_tradition_ice_age2"], old, new
        )

    supreme = upgrades["vv_tradition_supremeblood2"]
    for old, new in [
        ("diplomacy = 5", "diplomacy = 2"),
        ("martial = 5", "martial = 2"),
        ("stewardship = 5", "stewardship = 2"),
        ("intrigue = 5", "intrigue = 2"),
        ("learning = 10", "learning = 4"),
        ("prowess = 15", "prowess = 5"),
        ("life_expectancy = 1000", "life_expectancy = 10"),
        ("years_of_fertility = 960", "years_of_fertility = 3"),
        ("health = 2", "health = 1"),
        (
            "negative_inactive_inheritance_chance = -0.5",
            "negative_inactive_inheritance_chance = -0.25",
        ),
        ("levy_attack = 50", "levy_attack = 15"),
        ("levy_toughness = 50", "levy_toughness = 15"),
        ("levy_pursuit = 25", "levy_pursuit = 8"),
        ("levy_screen = 25", "levy_screen = 8"),
        ("levy_size = -0.8", "levy_size = -0.5"),
        ("levy_reinforcement_rate = -0.8", "levy_reinforcement_rate = -0.5"),
        ("hard_casualty_modifier = -0.3", "hard_casualty_modifier = -0.15"),
    ]:
        supreme = replace_once(supreme, old, new)
    supreme = replace_once(
        supreme,
        "\t\tprowess = 5\n",
        "\t\tprowess = 5\n\t\tmonthly_lifestyle_xp_gain_mult = -0.15\n\t\tmonthly_piety_gain_mult = -0.15\n\t\tmonthly_prestige_gain_mult = -0.15\n\t\tmonthly_influence_mult = -0.15\n",
    )
    upgrades["vv_tradition_supremeblood2"] = supreme

    knight = upgrades["vv_tradition_true_knight2"]
    for old, new in [
        ("\t\tactive_accolades = 3\n", ""),
        ("monthly_prestige_gain_mult = 0.2", "monthly_prestige_gain_mult = 0.15"),
        ("knight_limit = 10", "knight_limit = 4"),
        ("knight_effectiveness_mult = 2.25", "knight_effectiveness_mult = 0.75"),
        ("accolade_glory_gain_mult = 0.2", "accolade_glory_gain_mult = 0.15"),
        ("negate_prowess_penalty_add = 10", "negate_prowess_penalty_add = 4"),
        ("prowess_per_prestige_level = 2", "prowess_per_prestige_level = 1"),
        (
            "knight_effectiveness_per_prowess = 0.02",
            "knight_effectiveness_per_prowess = 0.01",
        ),
    ]:
        knight = replace_once(knight, old, new)
    knight = replace_once(
        knight,
        "\t\tknight_effectiveness_per_prowess = 0.01\n",
        "\t\tknight_effectiveness_per_prowess = 0.01\n\t\tlevy_size = -0.4\n\t\tlevy_maintenance = 0.75\n",
    )
    upgrades["vv_tradition_true_knight2"] = knight

    builder = upgrades["vv_tradition_tb2"]
    for old, new in [
        ("additional_fort_level = 8", "additional_fort_level = 4"),
        ("garrison_size = 0.5", "garrison_size = 0.2"),
        ("stewardship_per_prestige_level = 2", "stewardship_per_prestige_level = 1"),
        ("domain_limit = 3", "domain_limit = 2"),
        ("domicile_build_gold_cost = -0.25", "domicile_build_gold_cost = -0.15"),
        ("build_gold_cost = -0.25", "build_gold_cost = -0.15"),
        ("build_piety_cost = -0.25", "build_piety_cost = -0.15"),
        ("build_prestige_cost = -0.25", "build_prestige_cost = -0.15"),
        ("build_speed = -0.35", "build_speed = -0.15"),
        ("development_growth_factor = 0.2", "development_growth_factor = 0.1"),
    ]:
        builder = replace_once(builder, old, new)
    upgrades["vv_tradition_tb2"] = builder

    content = "# Generated by scripts/generate-ant-agot-vanilla-balance.py\n\n"
    content += "\n".join(blocks[name].rstrip() for name in names)
    content += "\n\n" + "\n".join(upgrades[name].rstrip() for name in upgrade_names)
    write(
        "common/culture/traditions/zz_ant_agot_vanilla_balance_traditions.txt", content
    )


def generate_modifiers() -> None:
    content = r"""# Generated by scripts/generate-ant-agot-vanilla-balance.py

ary_traditions_1_modifier = {
	icon = horse_positive
	movement_speed = 0.1
	heavy_cavalry_damage_mult = 0.1
	heavy_cavalry_toughness_mult = 0.1
	heavy_cavalry_pursuit_mult = 0.1
	heavy_cavalry_screen_mult = 0.1
	light_cavalry_damage_mult = 0.1
	light_cavalry_toughness_mult = 0.1
	light_cavalry_pursuit_mult = 0.1
	light_cavalry_screen_mult = 0.1
	archer_cavalry_damage_mult = 0.1
	archer_cavalry_toughness_mult = 0.1
	archer_cavalry_pursuit_mult = 0.1
	archer_cavalry_screen_mult = 0.1
	supply_duration = 0.25
	monthly_dynasty_prestige_mult = 0.05
	accolade_glory_gain_mult = 0.05
	knight_limit = 2
	owned_legend_spread_mult = 0.1
	glory_hound_opinion = 5
}

ary_traditions_2_modifier = {
	icon = tournament_positive
	defender_advantage = 5
	heavy_infantry_damage_mult = 0.1
	heavy_infantry_toughness_mult = 0.1
	heavy_infantry_pursuit_mult = 0.1
	heavy_infantry_screen_mult = 0.1
	pikemen_damage_mult = 0.1
	pikemen_toughness_mult = 0.1
	pikemen_pursuit_mult = 0.1
	pikemen_screen_mult = 0.1
	retreat_losses = -0.1
	monthly_dynasty_prestige_mult = 0.05
	accolade_glory_gain_mult = 0.05
	knight_limit = 2
	owned_legend_spread_mult = 0.1
	glory_hound_opinion = 5
}

ary_traditions_3_modifier = {
	icon = hunt_positive
	county_opinion_add = 10
	skirmishers_damage_mult = 0.1
	skirmishers_toughness_mult = 0.1
	skirmishers_pursuit_mult = 0.1
	skirmishers_screen_mult = 0.1
	archers_damage_mult = 0.1
	archers_toughness_mult = 0.1
	archers_pursuit_mult = 0.1
	archers_screen_mult = 0.1
	enemy_terrain_advantage = -0.1
	monthly_dynasty_prestige_mult = 0.05
	accolade_glory_gain_mult = 0.05
	knight_limit = 2
	owned_legend_spread_mult = 0.1
	glory_hound_opinion = 5
}

ary_traditions_4_modifier = {
	icon = cold_positive
	winter_advantage = 5
	elephant_cavalry_damage_mult = 0.1
	elephant_cavalry_toughness_mult = 0.1
	elephant_cavalry_pursuit_mult = 0.1
	elephant_cavalry_screen_mult = 0.1
	winter_movement_speed = 0.1
	monthly_dynasty_prestige_mult = 0.05
	accolade_glory_gain_mult = 0.05
	knight_limit = 2
	owned_legend_spread_mult = 0.1
	glory_hound_opinion = 5
}

ary_traditions_5_modifier = {
	icon = compass_positive
	advantage = 5
	diplomacy_per_piety_level = 1
	martial_per_piety_level = 1
	stewardship_per_piety_level = 1
	intrigue_per_piety_level = 1
	learning_per_piety_level = 1
	prowess = 5
	negate_health_penalty_add = 0.5
	inbreeding_chance = -0.25
	positive_inactive_inheritance_chance = 0.15
	genetic_trait_strengthen_chance = 0.15
	life_expectancy = 5
	years_of_fertility = 2
	monthly_dynasty_prestige_mult = 0.1
	monthly_piety_gain_mult = 0.1
	monthly_lifestyle_xp_gain_mult = 0.1
	monthly_county_control_growth_add = 0.5
	development_growth_factor = 0.1
	domain_limit = 2
	realm_priest_opinion = 10
	religious_head_opinion = 10
	dynasty_opinion = 10
	no_prowess_loss_from_age = yes
}

ary_traditions_6_modifier = {
	icon = county_modifier_development_positive
	stewardship_per_prestige_level = 1
	negate_stewardship_penalty_add = 1
	domain_limit = 2
	build_speed = -0.15
	domicile_build_gold_cost = -0.05
	build_gold_cost = -0.1
	build_piety_cost = -0.1
	build_prestige_cost = -0.1
	additional_fort_level = 3
	garrison_size = 0.2
}

ary_house_traditions_1_modifier = {
	icon = prowess_positive
	prowess_no_portrait = 5
	knight_effectiveness_mult = 0.5
	knight_effectiveness_per_prowess = 0.01
	knight_effectiveness_per_martial = 0.01
	knight_limit = 3
	tourney_participant_xp_gain_mult = 0.2
	lifestyle_blademaster_xp_gain_mult = 0.25
	accolade_glory_gain_mult = 0.1
	owned_legend_spread_mult = 0.1
	legitimacy_gain_mult = 0.1
	glory_hound_opinion = 5
}
"""
    write("common/modifiers/zz_ant_agot_vanilla_balance_modifiers.txt", content)


MAA_STATS = {
    # stack, damage, toughness, pursuit, screen
    "vv_mammonth2": (25, 180, 160, 10, 20),
    "vv_mammonth3": (10, 500, 400, 20, 20),
    "vv_ary_kotr": (50, 140, 60, 40, 10),
    "vv_ary_black_knights": (25, 280, 160, 50, 25),
    "vv_grail_knights": (50, 140, 65, 35, 15),
    "vv_ary_supremechampions01": (50, 120, 100, 20, 20),
    "vv_ary_valkyrie": (50, 125, 75, 90, 70),
    "vv_ary_mhashashin": (100, 55, 35, 50, 40),
    "vv_knights_horizon": (50, 150, 60, 35, 25),
    "vv_h_archers_h": (100, 55, 25, 45, 35),
    "vv_supreme_maa_pack1": (100, 60, 45, 15, 15),
    "vv_supreme_maa_pack2": (100, 45, 60, 5, 30),
    "vv_supreme_maa_pack3": (100, 65, 25, 10, 20),
    "vv_supreme_maa_pack4": (50, 140, 60, 35, 20),
    "vv_supreme_maa_pack5": (100, 40, 25, 65, 50),
}


def round_away(value: float) -> int:
    return math.floor(value + 0.5) if value >= 0 else math.ceil(value - 0.5)


def scale_environment_bonus(bonus_block: str, new_stats: dict[str, int]) -> str:
    pattern = re.compile(r"\b(damage|toughness|pursuit|screen)\s*=\s*(-?\d+(?:\.\d+)?)")

    def scaled(match: re.Match[str]) -> str:
        stat = match.group(1)
        old_value = float(match.group(2))
        cap = max(10, round_away(new_stats[stat] * 0.5))
        new_value = max(-cap, min(cap, round_away(old_value * 0.25)))
        return f"{stat} = {new_value}"

    return pattern.sub(scaled, bonus_block)


def generate_maa() -> None:
    source = read(ANT_AGOT / "common/men_at_arms_types/vv_ary_maa_types.txt")
    blocks: list[str] = []
    for name, (stack, damage, toughness, pursuit, screen) in MAA_STATS.items():
        block = extract(source, name)
        for field, value in [
            ("damage", damage),
            ("toughness", toughness),
            ("pursuit", pursuit),
            ("screen", screen),
            ("stack", stack),
        ]:
            block = replace_field(block, field, value)
        new_stats = {
            "damage": damage,
            "toughness": toughness,
            "pursuit": pursuit,
            "screen": screen,
        }
        for key in ("terrain_bonus", "winter_bonus"):
            span = subblock_span(block, key)
            if span:
                start, end = span
                block = (
                    block[:start]
                    + scale_environment_bonus(block[start:end], new_stats)
                    + block[end:]
                )
        blocks.append(block.rstrip())
    content = """# Generated by scripts/generate-ant-agot-vanilla-balance.py
@cultural_maa_extra_ai_score = 80
@provisions_cost_infantry_bankrupting = 15
@provisions_cost_cavalry_expensive = 21
@provisions_cost_cavalry_bankrupting = 30

""" + "\n\n".join(blocks)
    write("common/men_at_arms_types/zz_ant_agot_vanilla_balance_maa.txt", content)


COMMON_CHAINS = {
    "ary_mtg": ANT / "common/buildings/ary_common_buildings.txt",
    "ary_ew": ANT / "common/buildings/ary_common_buildings.txt",
    "ary_eto": ANT / "common/buildings/ary_common_buildings.txt",
    "ary_lmc": ANT / "common/buildings/ary_common_buildings.txt",
    "vv_ary_dim": ANT_AGOT / "common/buildings/vv_ary_duchy_and_common_buildings.txt",
    "ary_swt": ANT / "common/buildings/ary_common_buildings.txt",
    "ary_tml": ANT / "common/buildings/ary_common_buildings.txt",
    "ary_dfa": ANT / "common/buildings/ary_common2_buildings.txt",
    "ary_wetm": ANT / "common/buildings/ary_common2_buildings.txt",
    "ary_caryf": ANT / "common/buildings/ary_common2_buildings.txt",
    "ary_swordasa": ANT / "common/buildings/ary_common2_buildings.txt",
    "ary_cameltg": ANT / "common/buildings/ary_common2_buildings.txt",
    "ary_hatg": ANT / "common/buildings/ary_common2_buildings.txt",
    "vv_ary_merchantg": ANT_AGOT
    / "common/buildings/vv_ary_duchy_and_common_buildings.txt",
    "ary_firearmsf": ANT / "common/buildings/ary_common2_buildings.txt",
}

SPECIALIST_CHAINS = {
    "ary_mtg",
    "ary_dfa",
    "ary_wetm",
    "ary_caryf",
    "ary_swordasa",
    "ary_cameltg",
    "ary_hatg",
    "ary_firearmsf",
}


def replace_matching_values(
    block: str, pattern: str, value: float, minimum: int = 1
) -> str:
    regex = re.compile(pattern, re.MULTILINE)
    matches = list(regex.finditer(block))
    if len(matches) < minimum:
        raise ValueError(
            f"expected at least {minimum} matches for {pattern}, found {len(matches)}"
        )
    return regex.sub(lambda match: match.group(1) + number(value), block)


def generate_common_buildings() -> None:
    source_cache = {path: read(path) for path in set(COMMON_CHAINS.values())}
    specialist_curve = [0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45]
    general_curve = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40]
    blocks: list[str] = []

    for chain, path in COMMON_CHAINS.items():
        for level in range(1, 9):
            name = f"{chain}_{level:02d}"
            block = extract(source_cache[path], name)
            block = replace_subblock(block, "character_modifier", None)
            block = re.sub(
                r"(?ms)(\tis_enabled\s*=\s*\{)\s*trigger_if\s*=\s*\{\s*is_county_capital\s*=\s*yes\s*\}\s*(\})",
                r"\1\n\t\tis_county_capital = yes\n\t\2",
                block,
            )

            if chain in SPECIALIST_CHAINS:
                block = replace_matching_values(
                    block,
                    r"(?m)^(\s*stationed_(?!maa_siege_value)[a-z_]+_(?:damage|toughness|pursuit|screen)_mult\s*=\s*)-?\d+(?:\.\d+)?",
                    specialist_curve[level - 1],
                )
                if chain == "ary_firearmsf":
                    block = replace_matching_values(
                        block,
                        r"(?m)^(\s*stationed_maa_siege_value_mult\s*=\s*)-?\d+(?:\.\d+)?",
                        general_curve[level - 1],
                    )
            elif chain == "ary_lmc":
                block = replace_matching_values(
                    block,
                    r"(?m)^(\s*stationed_maa_(?:damage|toughness|pursuit|screen)_mult\s*=\s*)-?\d+(?:\.\d+)?",
                    general_curve[level - 1],
                    minimum=4,
                )
            elif chain == "ary_ew":
                for field, values in {
                    "fort_level": [2, 3, 4, 5, 6, 7, 8, 10],
                    "defender_holding_advantage": [1, 2, 3, 4, 5, 6, 7, 8],
                    "travel_danger": [-1, -2, -3, -4, -5, -6, -7, -8],
                    "monthly_county_control_growth_factor": [
                        0.02,
                        0.04,
                        0.06,
                        0.08,
                        0.10,
                        0.12,
                        0.14,
                        0.16,
                    ],
                }.items():
                    block = replace_field(block, field, values[level - 1])
            elif chain == "ary_eto":
                for field, values in {
                    "monthly_income": [0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4],
                    "tax_mult": [0.03, 0.05, 0.08, 0.10, 0.12, 0.15, 0.18, 0.20],
                    "development_growth": [
                        0.03,
                        0.05,
                        0.08,
                        0.10,
                        0.12,
                        0.15,
                        0.18,
                        0.20,
                    ],
                    "development_growth_factor": [
                        0.03,
                        0.05,
                        0.08,
                        0.10,
                        0.12,
                        0.15,
                        0.18,
                        0.20,
                    ],
                }.items():
                    block = replace_field(block, field, values[level - 1])
            elif chain == "vv_ary_dim":
                block = replace_field(block, "monthly_income", 0.75 * level)
            elif chain == "ary_swt":
                for field, values in {
                    "development_growth": [
                        0.05,
                        0.10,
                        0.15,
                        0.20,
                        0.25,
                        0.30,
                        0.35,
                        0.40,
                    ],
                    "development_growth_factor": [
                        0.05,
                        0.08,
                        0.10,
                        0.12,
                        0.15,
                        0.18,
                        0.20,
                        0.25,
                    ],
                    "defender_holding_advantage": [1, 2, 3, 4, 5, 6, 7, 8],
                }.items():
                    block = replace_field(block, field, values[level - 1])
            elif chain == "ary_tml":
                for field, values in {
                    "monthly_income": [0.3, 0.6, 0.9, 1.2, 1.5, 1.8, 2.1, 2.4],
                    "tax_mult": [0.02, 0.04, 0.06, 0.08, 0.10, 0.12, 0.14, 0.16],
                    "levy_size": [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40],
                }.items():
                    block = replace_field(block, field, values[level - 1])
            elif chain == "vv_ary_merchantg":
                for field, values in {
                    "monthly_income": [0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4],
                    "tax_mult": [0.02, 0.04, 0.06, 0.08, 0.10, 0.12, 0.14, 0.16],
                    "travel_danger": [-2, -4, -6, -8, -10, -12, -14, -16],
                    "development_growth": [
                        0.02,
                        0.04,
                        0.06,
                        0.08,
                        0.10,
                        0.12,
                        0.14,
                        0.16,
                    ],
                    "development_growth_factor": [
                        0.02,
                        0.04,
                        0.06,
                        0.08,
                        0.10,
                        0.12,
                        0.14,
                        0.16,
                    ],
                }.items():
                    block = replace_field(block, field, values[level - 1])
            blocks.append(block.rstrip())

    content = (
        "# Generated by scripts/generate-ant-agot-vanilla-balance.py\n\n"
        + "\n\n".join(blocks)
    )
    write("common/buildings/zz_ant_agot_vanilla_balance_common_buildings.txt", content)


DUCHY_CHAINS = ["woa", "cp", "og", "cote", "knightshof", "squareotf", "highh", "domeol"]


def at(values: list[int | float], tier: int) -> int | float:
    return values[tier - 1]


def slot(tier: int) -> list[tuple[str, int]]:
    return [("building_slot_add", 1)] if tier == 3 else []


def duchy_targets(chain: str, tier: int) -> dict[str, object]:
    if chain == "woa":
        return {
            "max_garrison": at([1000, 1750, 2500], tier),
            "reinforcement": at([0.25, 0.4, 0.55], tier),
            "province_modifier": [
                ("monthly_income", at([1, 2, 3], tier)),
                ("fort_level", at([4, 6, 8], tier)),
                ("defender_holding_advantage", at([5, 8, 12], tier)),
                ("garrison_size", at([0.25, 0.4, 0.6], tier)),
                ("travel_danger", at([-10, -15, -20], tier)),
                ("hostile_raid_time", at([1, 1.5, 2], tier)),
            ],
            "duchy_capital_county_modifier": [
                ("additional_fort_level", tier),
                ("county_opinion_add", at([5, 10, 15], tier)),
            ],
            "county_modifier": [
                ("development_growth", at([0.05, 0.1, 0.15], tier)),
                ("development_growth_factor", at([0.05, 0.1, 0.15], tier)),
                ("levy_size", at([0.05, 0.1, 0.15], tier)),
                ("tax_mult", at([0.05, 0.1, 0.15], tier)),
            ]
            + slot(tier),
        }
    if chain == "cp":
        return {
            "max_garrison": at([500, 750, 1000], tier),
            "reinforcement": at([0.2, 0.3, 0.4], tier),
            "province_modifier": [
                ("monthly_income", at([2, 3.5, 5], tier)),
                ("defender_holding_advantage", at([3, 5, 8], tier)),
                ("tax_mult", at([0.1, 0.15, 0.2], tier)),
                ("development_growth", at([0.1, 0.15, 0.2], tier)),
                ("development_growth_factor", at([0.15, 0.25, 0.35], tier)),
            ],
            "character_modifier": [
                ("monthly_income_mult", at([0.05, 0.1, 0.15], tier)),
                ("tax_mult", at([0.05, 0.1, 0.15], tier)),
                ("diplomatic_range_mult", at([0.05, 0.1, 0.15], tier)),
                ("naval_movement_speed_mult", at([0.05, 0.1, 0.15], tier)),
                ("embarkation_cost_mult", at([-0.05, -0.1, -0.15], tier)),
            ],
            "county_holder_character_modifier": [],
            "county_modifier": slot(tier),
        }
    if chain == "og":
        terrain_keys = [
            "mountains_tax_mult",
            "desert_mountains_tax_mult",
            "hills_tax_mult",
            "majorroad_mountains_tax_mult",
            "minorroad_mountains_tax_mult",
            "majorroad_desert_mountains_tax_mult",
            "minorroad_desert_mountains_tax_mult",
            "majorroad_hills_tax_mult",
            "minorroad_hills_tax_mult",
            "glacier_tax_mult",
            "majorroad_glacier_tax_mult",
            "minorroad_glacier_tax_mult",
            "canyon_tax_mult",
            "majorroad_canyon_tax_mult",
            "minorroad_canyon_tax_mult",
            "highlands_tax_mult",
            "majorroad_highlands_tax_mult",
            "minorroad_highlands_tax_mult",
        ]
        terrain_value = at([0.1, 0.15, 0.2], tier)
        return {
            "max_garrison": at([1250, 2250, 3500], tier),
            "reinforcement": at([0.35, 0.55, 0.75], tier),
            "province_modifier": [
                ("monthly_income", at([0.5, 1, 1.5], tier)),
                ("fort_level", at([8, 12, 16], tier)),
                ("defender_holding_advantage", at([10, 15, 20], tier)),
                ("garrison_size", at([0.5, 0.75, 1], tier)),
                ("hostile_raid_time", at([1, 1.5, 2], tier)),
                ("supply_limit_mult", at([-0.25, -0.15, -0.05], tier)),
                ("levy_size", at([-0.3, -0.2, -0.1], tier)),
                ("levy_reinforcement_rate", at([-0.3, -0.2, -0.1], tier)),
            ],
            "character_modifier": [
                ("defender_advantage", at([2, 3, 5], tier)),
                ("controlled_province_advantage", at([5, 8, 10], tier)),
                ("scheme_discovery_chance_mult", at([0.05, 0.1, 0.15], tier)),
            ],
            "duchy_capital_county_modifier": [
                ("additional_fort_level", at([2, 4, 6], tier)),
                *[(key, terrain_value) for key in terrain_keys],
            ],
            "county_modifier": slot(tier),
        }
    if chain == "cote":
        return {
            "max_garrison": at([1000, 2000, 3000], tier),
            "reinforcement": at([0.3, 0.5, 0.7], tier),
            "province_modifier": [
                ("monthly_income", at([2, 3.5, 5], tier)),
                ("tax_mult", at([0.1, 0.15, 0.2], tier)),
                ("fort_level", at([3, 5, 7], tier)),
                ("defender_holding_advantage", at([5, 8, 12], tier)),
                ("garrison_size", at([0.25, 0.4, 0.6], tier)),
                ("supply_limit_mult", at([0.25, 0.5, 0.75], tier)),
                ("levy_size", at([0.15, 0.25, 0.4], tier)),
                ("development_growth_factor", at([0.05, 0.1, 0.15], tier)),
            ],
            "character_modifier": [
                ("dread_baseline_add", at([5, 10, 15], tier)),
                ("vassal_limit", at([3, 6, 10], tier)),
                ("vassal_tax_contribution_mult", at([0.05, 0.1, 0.15], tier)),
                ("vassal_levy_contribution_mult", at([0.05, 0.1, 0.15], tier)),
                (
                    "character_capital_county_monthly_development_growth_add",
                    at([0.05, 0.1, 0.15], tier),
                ),
                ("vassal_opinion", at([5, 10, 15], tier)),
                ("monthly_dynasty_prestige_mult", at([0.03, 0.05, 0.1], tier)),
            ],
            "county_modifier": slot(tier),
        }
    if chain == "knightshof":
        character = [
            ("monthly_prestige", at([0.5, 1, 1.5], tier)),
            ("monthly_prestige_gain_mult", at([0.05, 0.1, 0.15], tier)),
            ("knight_limit", at([2, 4, 6], tier)),
            ("knight_effectiveness_mult", at([0.25, 0.5, 0.75], tier)),
            ("monthly_legitimacy_add", at([0.1, 0.2, 0.3], tier)),
            ("owned_legend_spread_mult", at([0.03, 0.05, 0.1], tier)),
            ("tourney_participant_xp_gain_mult", at([0.1, 0.2, 0.3], tier)),
            ("accolade_glory_gain_mult", at([0.05, 0.1, 0.15], tier)),
        ]
        if tier == 3:
            character += [
                ("prowess_per_prestige_level", 1),
                ("no_prowess_loss_from_age", "yes"),
            ]
        return {
            "max_garrison": at([350, 700, 1050], tier),
            "reinforcement": at([0.15, 0.3, 0.45], tier),
            "province_modifier": [
                ("fort_level", tier),
                ("defender_holding_advantage", at([3, 5, 8], tier)),
                ("garrison_size", at([0.1, 0.2, 0.3], tier)),
            ],
            "character_modifier": character,
            "county_modifier": [("county_opinion_add", at([5, 10, 15], tier))]
            + slot(tier),
        }
    if chain == "squareotf":
        character = [
            ("monthly_piety", at([0.5, 1, 1.5], tier)),
            ("monthly_piety_gain_mult", at([0.05, 0.1, 0.15], tier)),
            ("tolerance_advantage_mod", at([2, 3, 5], tier)),
            ("opinion_of_same_faith", at([5, 10, 15], tier)),
            ("clergy_opinion", at([5, 10, 15], tier)),
            ("religious_head_opinion", at([5, 10, 15], tier)),
            ("pilgrim_xp_gain_mult", at([0.1, 0.2, 0.3], tier)),
            ("domain_tax_same_faith_mult", at([0.05, 0.1, 0.15], tier)),
            ("levy_reinforcement_rate_same_faith", at([0.05, 0.1, 0.15], tier)),
            ("zealot_levy_contribution_mult", at([0.05, 0.1, 0.15], tier)),
            ("zealot_tax_contribution_mult", at([0.05, 0.1, 0.15], tier)),
        ]
        if tier == 3:
            character.append(("learning_per_piety_level", 1))
        return {
            "max_garrison": at([350, 700, 1050], tier),
            "reinforcement": at([0.15, 0.3, 0.45], tier),
            "province_modifier": [
                ("monthly_income", tier),
                ("fort_level", tier),
                ("defender_holding_advantage", at([3, 5, 8], tier)),
                ("garrison_size", at([0.1, 0.2, 0.3], tier)),
            ],
            "character_modifier": character,
            "county_modifier": [
                ("travel_danger", at([-5, -10, -15], tier)),
                ("monthly_county_control_growth_add", at([0.25, 0.5, 0.75], tier)),
                ("county_opinion_add", at([5, 10, 15], tier)),
            ]
            + slot(tier),
        }
    if chain == "highh":
        character: list[tuple[str, int | float | str]] = []
        if tier >= 2:
            character += [
                (key, 1)
                for key in (
                    "diplomacy",
                    "martial",
                    "stewardship",
                    "intrigue",
                    "learning",
                )
            ]
        character += [
            ("prowess", tier),
            ("monthly_lifestyle_xp_gain_mult", at([0.03, 0.06, 0.1], tier)),
            ("monthly_piety_gain_mult", at([0.03, 0.06, 0.1], tier)),
            ("monthly_prestige_gain_mult", at([0.03, 0.06, 0.1], tier)),
            ("monthly_influence_mult", at([0.03, 0.06, 0.1], tier)),
            ("monthly_dynasty_prestige_mult", at([0.03, 0.06, 0.1], tier)),
            ("monthly_dynasty_prestige", at([0.25, 0.5, 1], tier)),
            ("health", at([0.05, 0.1, 0.15], tier)),
            ("negate_health_penalty_add", at([0.05, 0.1, 0.15], tier)),
        ]
        return {
            "max_garrison": at([1000, 1750, 2500], tier),
            "reinforcement": at([0.25, 0.4, 0.55], tier),
            "province_modifier": [
                ("fort_level", at([5, 8, 12], tier)),
                ("defender_holding_advantage", at([5, 8, 12], tier)),
                ("garrison_size", at([0.25, 0.4, 0.6], tier)),
            ],
            "character_modifier": character,
            "county_modifier": [
                ("tax_mult", at([0.05, 0.1, 0.15], tier)),
                ("hostile_raid_time", at([0.5, 1, 1.5], tier)),
            ]
            + slot(tier),
        }
    if chain == "domeol":
        return {
            "max_garrison": at([350, 700, 1050], tier),
            "reinforcement": at([0.15, 0.3, 0.45], tier),
            "province_modifier": [
                ("monthly_income", tier),
                ("tax_mult", at([0.05, 0.1, 0.15], tier)),
                ("defender_holding_advantage", at([3, 5, 8], tier)),
                ("garrison_size", at([0.1, 0.2, 0.3], tier)),
                ("development_growth_factor", at([0.1, 0.15, 0.2], tier)),
                ("travel_danger", at([-5, -10, -15], tier)),
            ],
            "character_modifier": [
                ("learning", at([2, 3, 5], tier)),
                ("cultural_head_fascination_mult", at([0.05, 0.1, 0.15], tier)),
                ("cultural_head_fascination_add", at([5, 10, 15], tier)),
                ("negate_health_penalty_add", at([0.1, 0.2, 0.3], tier)),
                ("realm_priest_opinion", at([5, 10, 15], tier)),
                ("monthly_lifestyle_xp_gain_mult", at([0.05, 0.1, 0.15], tier)),
            ],
            "county_modifier": [
                ("development_growth_factor", at([0.05, 0.1, 0.15], tier)),
                ("epidemic_resistance", at([5, 10, 15], tier)),
            ]
            + slot(tier),
        }
    raise ValueError(f"unknown duchy chain: {chain}")


def ai_duchy_block() -> str:
    return """\tai_value = {
\t\tbase = 20
\t\tmodifier = {
\t\t\tfactor = 2
\t\t\tscope:holder.capital_province = this
\t\t}
\t\tmodifier = { # Fill all building slots before going for duchy buildings
\t\t\tfactor = 0
\t\t\tfree_building_slots > 0
\t\t}
\t}\n"""


def generate_duchy_buildings() -> None:
    vanilla_source = read(
        ANT_AGOT / "common/buildings/vv_ary_duchy_and_common_buildings.txt"
    )
    fantasy_source = read(ANT_AGOT / "common/buildings/ary_duchy_capital_buildings.txt")
    blocks: list[str] = []

    for chain in DUCHY_CHAINS:
        for tier in range(1, 4):
            name = f"vv_ary_{chain}_{tier:02d}"
            block = extract(vanilla_source, name)
            targets = duchy_targets(chain, tier)
            block = replace_field(block, "max_garrison", targets["max_garrison"])
            block = replace_field(
                block, "garrison_reinforcement_factor", targets["reinforcement"]
            )
            for key in (
                "province_modifier",
                "character_modifier",
                "county_holder_character_modifier",
                "duchy_capital_county_modifier",
                "county_modifier",
            ):
                values = targets.get(key)
                replacement = modifier_block(key, values) if values else None
                block = replace_subblock(block, key, replacement)
            block = replace_subblock(block, "ai_value", ai_duchy_block())
            blocks.append(block.rstrip())

    for chain in DUCHY_CHAINS:
        for tier in range(1, 4):
            name = f"ary_{chain}_{tier:02d}"
            block = extract(fantasy_source, name)
            block = replace_subblock(block, "ai_value", ai_duchy_block())
            blocks.append(block.rstrip())

    content = (
        "# Generated by scripts/generate-ant-agot-vanilla-balance.py\n\n"
        + "\n\n".join(blocks)
    )
    write("common/buildings/zz_ant_agot_vanilla_balance_duchy_buildings.txt", content)


def main() -> None:
    generate_traditions()
    generate_modifiers()
    generate_maa()
    generate_common_buildings()
    generate_duchy_buildings()


if __name__ == "__main__":
    main()
