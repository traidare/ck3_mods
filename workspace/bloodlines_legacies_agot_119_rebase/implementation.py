#!/usr/bin/env python3
"""Generate the Bloodlines: Legacies of AGOT CK3 1.19 runtime rebase."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

from ck3mm.generation import GenerationContext
from ck3mm.generators.text import (
    read_source,
    replace_exact,
)
from ck3mm.generators.text import (
    replace_regex as shared_replace_regex,
)

ROOT: Path | None = None
BLOODLINES: Path | None = None
AGOT: Path | None = None
OUTPUT: Path | None = None

MONTHLY_OPINION_MODIFIERS = {
    "disappointed_opinion",
    "grateful_opinion",
    "hate_opinion",
    "impressed_opinion",
    "pious_opinion",
    "respect_opinion",
    "scared_opinion",
    "suspicion_opinion",
    "suspicious_opinion",
}

TRAIT_REPLACEMENTS = {
    "blademaster": "lifestyle_blademaster",
    "blademaster_1": "lifestyle_blademaster",
    "eager_reveler": "lifestyle_reveler",
    "elusive_shadow": "education_intrigue_4",
    "melancholic": "depressed_1",
    "mystic": "lifestyle_mystic",
    "mystic_1": "lifestyle_mystic",
    "mystic_2": "lifestyle_mystic",
    "mystic_3": "lifestyle_mystic",
    "poet": "lifestyle_poet",
    "wise_man": "lifestyle_mystic",
}

DDS_REENCODES = (
    "gfx/interface/icons/building_types/icon_amberly_watch.dds",
    "gfx/interface/icons/building_types/icon_butterwell_whitewalls.dds",
    "gfx/interface/icons/building_types/icon_manwoody_kingsgrave.dds",
    "gfx/interface/icons/building_types/icon_red_dunes.dds",
    "gfx/interface/icons/building_types/icon_wylde_rainhouse.dds",
    "gfx/interface/icons/dynasty/westerling_legacy_track.dds",
    "gfx/interface/illustrations/men_at_arms_small/costayne_chalice_wardens.dds",
    "gfx/interface/illustrations/men_at_arms_small/fisher_kings_bowmen.dds",
    "gfx/interface/illustrations/men_at_arms_small/payne_silent_guard.dds",
    "gfx/interface/illustrations/men_at_arms_small/tarbeck_starforged_retainers.dds",
)


def read_text(path: Path) -> str:
    return read_source(path, normalize_newlines=True)


def write_text(relative: str, text: str) -> None:
    target = OUTPUT / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8-sig", newline="")


def replace_regex(
    text: str,
    pattern: str,
    replacement: str,
    *,
    expected: int,
    label: str,
    flags: int = 0,
) -> str:
    return shared_replace_regex(
        text,
        pattern,
        replacement,
        label,
        expected,
        flags,
        error_type=RuntimeError,
    )


def brace_delta(line: str) -> int:
    """Count structural braces while ignoring comments and quoted strings."""
    depth = 0
    quoted = False
    escaped = False
    for char in line:
        if escaped:
            escaped = False
            continue
        if char == "\\" and quoted:
            escaped = True
            continue
        if char == '"':
            quoted = not quoted
            continue
        if char == "#" and not quoted:
            break
        if quoted:
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
    return depth


def block_end(lines: list[str], start: int) -> int:
    depth = 0
    for index in range(start, len(lines)):
        depth += brace_delta(lines[index])
        if depth == 0:
            return index + 1
    raise RuntimeError(f"unterminated block beginning at line {start + 1}")


def extract_named_block(text: str, name: str) -> str:
    lines = text.splitlines(keepends=True)
    pattern = re.compile(rf"^{re.escape(name)}\s*=\s*\{{")
    starts = [index for index, line in enumerate(lines) if pattern.match(line)]
    if len(starts) != 1:
        raise RuntimeError(f"expected one {name} definition, found {len(starts)}")
    start = starts[0]
    return "".join(lines[start : block_end(lines, start)])


def generate_prison_interaction() -> None:
    source = read_text(
        AGOT / "common/character_interactions/00_prison_interactions.txt"
    )
    block = extract_named_block(source, "execute_prisoner_interaction")
    block = replace_exact(
        block,
        "\t\t\t\tdynasty = { has_dynasty_perk = bolton_legacy_1 }\n",
        (
            "\t\t\t\tdynasty = {\n"
            "\t\t\t\t\tOR = {\n"
            "\t\t\t\t\t\thas_dynasty_perk = bolton_legacy_1\n"
            "\t\t\t\t\t\thas_dynasty_perk = bolton_legacy_1_BLA\n"
            "\t\t\t\t\t}\n"
            "\t\t\t\t}\n"
        ),
        expected=1,
        label="Bolton flaying option",
    )
    write_text(
        "common/character_interactions/00_prison_interactions_BLA.txt",
        block,
    )


def generate_guarded_special_buildings() -> None:
    relative = "common/on_action/agot_on_actions/agot_game_start_BLA.txt"
    text = read_text(BLOODLINES / relative)
    pattern = re.compile(
        r"^(?P<indent>[ \t]*)province:(?P<province>\d+) = "
        r"\{ add_special_building = (?P<building>[A-Za-z0-9_]+) \}$",
        re.MULTILINE,
    )

    def guard(match: re.Match[str]) -> str:
        indent = match.group("indent")
        return (
            f"{indent}province:{match.group('province')} = {{\n"
            f"{indent}\tif = {{\n"
            f"{indent}\t\tlimit = {{ has_special_building = no }}\n"
            f"{indent}\t\tadd_special_building = {match.group('building')}\n"
            f"{indent}\t}}\n"
            f"{indent}}}"
        )

    text, count = pattern.subn(guard, text)
    if count != 73:
        raise RuntimeError(
            f"special-building guards: expected 73 additions, guarded {count}"
        )
    write_text(relative, text)


def repair_child_birth_on_action() -> None:
    relative = "common/on_action/child_birth_on_actions_cultures_BLA.txt"
    text = read_text(BLOODLINES / relative)
    old = (
        "\t\t\t\t\t  random_list = {\n"
        "        \t\t\t\t\t1 = { add_trait = beauty_good_1 }\n"
        "       \t\t\t\t\t\t1 = { add_trait = beauty_good_2 }\n"
        "        \t\t\t\t\t1 = { add_trait = beauty_good_3 }\n"
        "\t\t\t\t}\n"
        "\t\t\t}\n"
        "\t\t\tif = {\n"
    )
    new = (
        "\t\t\t\t\t  random_list = {\n"
        "        \t\t\t\t\t1 = { add_trait = beauty_good_1 }\n"
        "       \t\t\t\t\t\t1 = { add_trait = beauty_good_2 }\n"
        "        \t\t\t\t\t1 = { add_trait = beauty_good_3 }\n"
        "\t\t\t\t}\n"
        "\t\t\t\t}\n"
        "\t\t\t}\n"
        "\t\t\tif = {\n"
    )
    text = replace_exact(
        text,
        old,
        new,
        expected=1,
        label="Lyseni child-beauty brace",
    )
    write_text(relative, text)


def repair_common_files() -> None:
    relative = (
        "common/decisions/agot_decisions/00_agot_formable_kingdoms_decisions_BLA.txt"
    )
    text = read_text(BLOODLINES / relative)
    text = replace_exact(
        text,
        "title:e_the_iron_throne",
        "title:h_the_iron_throne",
        expected=6,
        label="Iron Throne title rank",
    )
    text = replace_exact(
        text,
        "title:k_duskendale",
        "title:k_dusklands_bla",
        expected=2,
        label="Dusklands kingdom title",
    )
    write_text(relative, text)

    relative = "common/decisions/agot_decisions/00_agot_major_decisions_BLA.txt"
    text = read_text(BLOODLINES / relative)
    text = replace_exact(
        text,
        "world_westeros_riverlands",
        "world_westeros_the_riverlands",
        expected=2,
        label="Riverlands geographical region",
    )
    text = replace_exact(
        text,
        "\t\t\t\topinion < 0\n",
        "\t\t\t\topinion = { target = root value < 0 }\n",
        expected=1,
        label="opinion trigger syntax",
    )
    text = replace_exact(
        text,
        "\tconfirm = fashion_blackwood_weirwood_bow_decision_confirm\n",
        "\tconfirm_text = fashion_blackwood_weirwood_bow_decision_confirm\n",
        expected=1,
        label="decision confirm_text field",
    )
    write_text(relative, text)

    relative = "common/dynasty_legacies/99_agot_cultures_BLA_legacies.txt"
    text = read_text(BLOODLINES / relative)
    text = replace_exact(
        text,
        "has_dynasty_perk = northman_legacy_1",
        "has_dynasty_perk = north_legacy_1",
        expected=1,
        label="North legacy perk id",
    )
    text = replace_exact(
        text,
        "culture:gogossosi",
        "culture:gogossite",
        expected=1,
        label="Gogossos culture id",
    )
    text = replace_exact(
        text,
        "culture:yunkish",
        "culture:yunkaii",
        expected=1,
        label="Yunkai culture id",
    )
    write_text(relative, text)

    relative = "common/dynasty_perks/00_agot_BLA_perks.txt"
    text = read_text(BLOODLINES / relative)
    text = replace_regex(
        text,
        r"^(\s*)build_gold_cost\s+(-0\.(?:10|05))\s*$",
        r"\1build_gold_cost = \2",
        expected=2,
        label="build_gold_cost equals signs",
        flags=re.MULTILINE,
    )
    write_text(relative, text)

    relative = "common/great_projects/types/zz_agot_great_projects_BLA.txt"
    text = read_text(BLOODLINES / relative)
    if text.count("@msg_completion_effect_generic") != 3:
        raise RuntimeError("expected three generic completion sound references")
    text = (
        "@msg_completion_effect_generic = "
        '"event:/DLC/EP4/SFX/Stingers/China/'
        'tgp_mx_sting_finishing_great_project_generic"\n\n' + text
    )
    write_text(relative, text)

    relative = "common/modifiers/00_agot_riverlands_modifiers_BLA.txt"
    text = read_text(BLOODLINES / relative)
    text = replace_exact(
        text,
        "\tmonthly_piety = 0.20\n"
        "\tcounty_opinion_add = 5\n"
        "\tmonthly_county_control_growth_add = 0.20\n",
        "\tcounty_opinion_add = 5\n\tmonthly_county_control_growth_add = 0.20\n",
        expected=1,
        label="Oldstones county modifier scope",
    )
    text = replace_exact(
        text,
        "\ticon = icon_positive\n",
        "\ticon = piety_positive\n",
        expected=1,
        label="Vance piety modifier icon",
    )
    write_text(relative, text)


def remove_monthly_opinion_durations(text: str) -> tuple[str, int]:
    lines = text.splitlines(keepends=True)
    output: list[str] = []
    removed = 0
    index = 0
    start_re = re.compile(r"^\s*add_opinion\s*=\s*\{")
    modifier_re = re.compile(r"\bmodifier\s*=\s*([A-Za-z0-9_]+)")
    duration_re = re.compile(r"^\s*(?:years|months|days)\s*=")
    while index < len(lines):
        if not start_re.match(lines[index]):
            output.append(lines[index])
            index += 1
            continue
        end = block_end(lines, index)
        block = lines[index:end]
        modifier = None
        for line in block:
            match = modifier_re.search(line)
            if match:
                modifier = match.group(1)
                break
        if modifier in MONTHLY_OPINION_MODIFIERS:
            retained = []
            for line in block:
                if duration_re.match(line):
                    removed += 1
                else:
                    retained.append(line)
            block = retained
        output.extend(block)
        index = end
    return "".join(output), removed


def replace_script_traits(text: str) -> tuple[str, int]:
    total = 0
    field_pattern = r"(has_trait|add_trait|remove_trait|trait)"
    for old, new in TRAIT_REPLACEMENTS.items():
        pattern = re.compile(rf"\b{field_pattern}(\s*=\s*){re.escape(old)}\b")
        text, count = pattern.subn(rf"\1\2{new}", text)
        total += count
    return text, total


def repair_event(relative: str, text: str) -> tuple[str, dict[str, int]]:
    original = text
    stats = {"opinion_durations": 0, "traits": 0}

    text, stats["opinion_durations"] = remove_monthly_opinion_durations(text)
    text, stats["traits"] = replace_script_traits(text)

    text = re.sub(
        r"^[ \t]*(?:has_trait\s*=\s*romantic|add_trait\s*=\s*gambler)\s*$\n?",
        "",
        text,
        flags=re.MULTILINE,
    )
    text = re.sub(r"\btype\s*=\s*weak_hook\b", "type = favor_hook", text)
    text = text.replace("title:b_crossroads_inn", "title:b_inn_at_the_crossroads")
    text = text.replace(
        "geographical_region = world_westeros_riverlands",
        "geographical_region = world_westeros_the_riverlands",
    )
    text = text.replace(
        "has_cultural_pillar = heritage_first_men",
        "has_cultural_pillar = heritage_first_man",
    )

    if relative == "events/agot_events/agot_riverlands_events_bla.txt":
        text = replace_exact(
            text,
            "any_realm_county = { has_county_modifier = county_recently_conquered }\n"
            "\t\t\tany_realm_county = { has_county_modifier = county_occupied }",
            "any_realm_county = { has_county_modifier = occupation_modifier }",
            expected=1,
            label="obsolete county occupation modifiers",
        )
        text = replace_exact(
            text,
            "this = title:c_quiet_isle",
            "this = title:b_quiet_isle.county",
            expected=1,
            label="Quiet Isle held county",
        )
        text = replace_exact(
            text,
            "\t\t\t\t\ttitle:c_quiet_isle\n",
            "\t\t\t\t\tthis = title:b_quiet_isle.county\n",
            expected=1,
            label="Quiet Isle neighboring county",
        )
        text = replace_exact(
            text,
            "\t\t\ttemplate = knight_template\n",
            "\t\t\ttemplate = agot_hedgeknight_character\n"
            "\t\t\tlocation = root.location\n",
            expected=1,
            label="Crossroads hedge-knight template",
        )
        text = replace_exact(
            text,
            "\t\t\t\t\tset_employer = root\n\t\t\t\t\tis_knight = yes\n",
            "\t\t\t\t\tset_employer = root\n\t\t\t\t\tset_knight_status = force\n",
            expected=1,
            label="Crossroads knight-status effect",
        )
        text = replace_exact(
            text,
            "\t\ttitle:c_harrenhal = {\n"
            "\t\t\tadd_county_modifier = {\n"
            "\t\t\t\tmodifier = riverlands_searched_black_towers_bla\n"
            "\t\t\t\tyears = 5\n"
            "\t\t\t}\n"
            "\t\t}\n",
            "\t\tadd_character_modifier = {\n"
            "\t\t\tmodifier = riverlands_searched_black_towers_bla\n"
            "\t\t\tyears = 5\n"
            "\t\t}\n",
            expected=1,
            label="searched Black Towers modifier scope",
        )

    if relative == "events/agot_events/agot_riverlands_bracken_events_bla.txt":
        text = replace_exact(
            text,
            "\t\t\ttemplate = knight_template\n",
            "\t\t\ttemplate = agot_hedgeknight_character\n"
            "\t\t\tlocation = root.location\n",
            expected=1,
            label="Bracken hedge-knight template",
        )

    if relative == (
        "events/agot_decision_events/"
        "agot_riverlands_trident_council_decision_events.txt"
    ):
        text = replace_exact(
            text,
            "animation = personality_thoughtful",
            "animation = personality_rational",
            expected=2,
            label="Trident Council thoughtful animation",
        )
        text = replace_exact(
            text,
            "change_control = -10",
            "change_county_control = -10",
            expected=3,
            label="Trident Council county control",
        )
        text = replace_exact(
            text,
            "change_county_opinion = -10",
            "change_county_control = -10",
            expected=1,
            label="Trident Council obsolete county-opinion effect",
        )
        text = replace_regex(
            text,
            r"capital_province = \{\n(?P<indent>\s*)change_county_control = -10",
            r"capital_county = {\n\g<indent>change_county_control = -10",
            expected=4,
            label="Trident Council control effect scope",
        )
        for modifier, opinion, expected in (
            ("intimidated_opinion", "-15", 1),
            ("attended_trident_council_bla", "10", 2),
            ("disappointed_opinion", "-10", 4),
        ):
            pattern = (
                rf"(?P<indent>^[ \t]*)modifier = {modifier}\s*$"
                rf"(?!\n(?P=indent)opinion\s*=)"
            )
            text = replace_regex(
                text,
                pattern,
                rf"\g<indent>modifier = {modifier}\n"
                rf"\g<indent>opinion = {opinion}",
                expected=expected,
                label=f"{modifier} explicit opinion",
                flags=re.MULTILINE,
            )

    if relative == (
        "events/agot_events/agot_riverlands_blackwood_bracken_events_bla.txt"
    ):
        text = replace_exact(
            text,
            "\t\tadd prestige = -50\n",
            "\t\tadd_prestige = -50\n",
            expected=1,
            label="Blackwood-Bracken prestige effect",
        )
        text = replace_exact(
            text,
            "animation = listening",
            "animation = personality_rational",
            expected=1,
            label="Blackwood-Bracken listening animation",
        )

    if relative == "events/agot_events/agot_riverlands_piper_events_bla.txt":
        text = replace_exact(
            text,
            "\t\tat_war = yes\n",
            "\t\tis_at_war = yes\n",
            expected=1,
            label="Piper war trigger",
        )

    if relative == "events/agot_events/agot_lothston_returns_events.txt":
        text = replace_regex(
            text,
            r"\bdynasty = (dynn_(?:Lothston|Strong|Mudd))\b",
            r"dynasty = dynasty:\1",
            expected=3,
            label="Lothston dynasty scopes",
        )

    if relative == "events/agot_events/agot_john_mudd_claim_hammerford_events.txt":
        text = replace_exact(
            text,
            "        NOT = {\n"
            "            any_player = {\n"
            "                dynasty = dynasty:dynn_Mudd\n"
            "                primary_title = title:c_hammerford\n"
            "            }\n"
            "        }\n",
            "        NOT = {\n"
            "            any_player = {\n"
            "                dynasty = dynasty:dynn_Mudd\n"
            "                primary_title = title:c_hammerford\n"
            "            }\n"
            "        }\n"
            "        OR = {\n"
            "            AND = {\n"
            "                current_date < 8290.1.1\n"
            "                exists = character:Mudd_54\n"
            "            }\n"
            "            exists = character:Mudd_2\n"
            "        }\n",
            expected=1,
            label="John Mudd existence trigger",
        )
        text = replace_exact(
            text,
            "        else = {\n"
            "            hidden_effect = { end_event_chain = yes }\n"
            "        }\n\n",
            "",
            expected=1,
            label="obsolete end_event_chain effect",
        )
        text = replace_exact(
            text,
            "        scope:john_mudd = {\n            agot_house_revival_effect = {\n",
            "        scope:john_mudd = {\n"
            "            dynasty:dynn_Mudd.dynasty_founder.house = {\n"
            "                save_scope_as = bastard_house_of\n"
            "            }\n"
            "            agot_house_revival_effect = {\n",
            expected=2,
            label="John Mudd house-revival scope",
        )

    if relative == "events/bla_custom_house_legacy_events.txt":
        text = replace_regex(
            text,
            r"^\s*is_triggered_only\s*=\s*yes\s*$\n?",
            "",
            expected=7,
            label="obsolete is_triggered_only fields",
            flags=re.MULTILINE,
        )

    if relative == "events/agot_decision_events/agot_oldstones_bla_events.txt":
        text = replace_exact(
            text,
            "title:c_oldstones",
            "title:b_oldstones.county",
            expected=1,
            label="Oldstones county title",
        )

    if relative == "events/agot_events/agot_riverlands_vance_events_bla.txt":
        text = replace_exact(
            text,
            "modifier = vance_vanguard_readiness_bla",
            "modifier = vance_gathered_river_support_bla",
            expected=1,
            label="undefined Vance readiness modifier",
        )
        text = replace_exact(
            text,
            "reference = war_room",
            "reference = throne_room",
            expected=1,
            label="Vance event background",
        )
        text = replace_exact(
            text,
            "animation = personality_disapproval",
            "animation = disapproval",
            expected=2,
            label="Vance disapproval animation",
        )
        text = replace_exact(
            text,
            "\tadd_character_flag = {\n"
            "\t\tflag = vance_secured_co_conspirator_bla\n"
            "\t\tyears = 5\n"
            "\t}\n"
            "}\n"
            "}\n\n"
            "agot_riverlands_bla.0814",
            "\tadd_character_flag = {\n"
            "\t\tflag = vance_secured_co_conspirator_bla\n"
            "\t\tyears = 5\n"
            "\t}\n"
            "\t}\n"
            "}\n\n"
            "agot_riverlands_bla.0814",
            expected=1,
            label="Vance option closing-brace indentation",
        )

    if relative == "events/agot_events/agot_riverlands_harrenhal_events_bla.txt":
        text = replace_exact(
            text,
            "reference = agot_weirwood",
            "reference = agot_weirwood_event",
            expected=1,
            label="Harrenhal weirwood background",
        )
        text = replace_exact(
            text,
            "reference = amsb_harrenhal",
            "reference = agot_weirwood_event_night_harrenhal",
            expected=7,
            label="Harrenhal event backgrounds",
        )
        text = replace_exact(
            text,
            "animation = personality_thinking",
            "animation = personality_rational",
            expected=1,
            label="Harrenhal thinking animation",
        )

    if relative == "events/agot_events/agot_riverlands_justman_events_bla.txt":
        text = replace_exact(
            text,
            "reference = burning_village",
            "reference = burning_building",
            expected=1,
            label="Justman burning-village background",
        )

    if relative == "events/agot_events/agot_riverlands_frey_events_bla.txt":
        text = replace_exact(
            text,
            "has_dynasty = dynasty:dynn_Frey",
            "dynasty = dynasty:dynn_Frey",
            expected=1,
            label="Frey dynasty trigger",
        )
        text = replace_exact(
            text,
            "animation = personality_gregarious",
            "animation = personality_compassionate",
            expected=1,
            label="Frey gregarious animation",
        )
        pattern = (
            r"(?P<indent>^[ \t]*)modifier = offended_opinion\s*$"
            r"(?!\n(?P=indent)opinion\s*=)"
        )
        text = replace_regex(
            text,
            pattern,
            r"\g<indent>modifier = offended_opinion\n"
            r"\g<indent>opinion = -15",
            expected=1,
            label="offended_opinion explicit opinion",
            flags=re.MULTILINE,
        )

    if relative == "events/agot_events/agot_reforge_red_rain_events.txt":
        text = replace_exact(
            text,
            "\tright_portrait = scope:smith\n",
            "",
            expected=1,
            label="unsaved Red Rain smith portrait scope",
        )
        text = replace_exact(
            text,
            "\t}\n}\n\toption = {\n",
            "\t}\n\t}\n\toption = {\n",
            expected=1,
            label="Red Rain immediate closing-brace indentation",
        )

    if relative == "events/agot_events/agot_riverlands_mallister_events_bla.txt":
        text = replace_exact(
            text,
            "has_dynasty = dynasty:dynn_Mallister",
            "dynasty = dynasty:dynn_Mallister",
            expected=5,
            label="Mallister dynasty triggers",
        )

    if relative == "events/agot_events/agot_riverlands_events_bla.txt":
        text = replace_exact(
            text,
            "animation = personality_gregarious",
            "animation = personality_compassionate",
            expected=1,
            label="Riverlands gregarious animation",
        )

    if text == original:
        return text, stats
    return text, stats


def generate_events() -> None:
    opinion_durations = 0
    trait_replacements = 0
    changed_files = 0
    for source in sorted((BLOODLINES / "events").rglob("*.txt")):
        relative = source.relative_to(BLOODLINES).as_posix()
        original = read_text(source)
        patched, stats = repair_event(relative, original)
        opinion_durations += stats["opinion_durations"]
        trait_replacements += stats["traits"]
        if patched != original:
            write_text(relative, patched)
            changed_files += 1
    if opinion_durations != 69:
        raise RuntimeError(
            f"monthly opinion durations: expected 69 removals, made {opinion_durations}"
        )
    if trait_replacements != 32:
        raise RuntimeError(
            f"retired trait ids: expected 32 replacements, made {trait_replacements}"
        )
    print(
        f"generated {changed_files} patched event files; "
        f"removed {opinion_durations} invalid opinion durations; "
        f"migrated {trait_replacements} retired trait references"
    )


def generate_opinion_compatibility() -> None:
    write_text(
        "common/opinion_modifiers/zz_bla_119_opinion_compat.txt",
        """# Bloodlines used opinion ids removed from current CK3.
attended_trident_council_bla = {
\topinion = 0
\tstacking = yes
}

intimidated_opinion = {
\topinion = 0
\tstacking = yes
}

fear_opinion = {
\topinion = 0
\tstacking = yes
}

uneasy_court_opinion = {
\topinion = 0
\tstacking = yes
}

exposed_criminal_opinion = {
\topinion = 0
\tstacking = yes
}

rival_opinion = {
\topinion = 0
\tstacking = yes
}

cultural_disapproval_opinion = {
\topinion = 0
\tstacking = yes
}

offended_opinion = {
\topinion = 0
\tstacking = yes
}
""",
    )


def generate_localization() -> None:
    relative = "localization/replace/english/agot_BLA_l_english.yml"
    text = read_text(BLOODLINES / relative)
    text = replace_exact(
        text,
        "kingdom_of_duskendale_decision",
        "kingdom_of_dusklands_decision",
        expected=1,
        label="Dusklands decision localization reference",
    )
    text = replace_exact(
        text,
        "GetTrait('poet')",
        "GetTrait('lifestyle_poet')",
        expected=1,
        label="poet localization reference",
    )
    text = replace_exact(
        text,
        "GetTrait('mystic_2')",
        "GetTrait('lifestyle_mystic')",
        expected=1,
        label="mystic localization reference",
    )
    text = replace_exact(
        text,
        "Major Rivers#.",
        "Major Rivers#!.",
        expected=1,
        label="Manderly high-markup terminator",
    )
    text = replace_exact(
        text,
        "[men_at-arms|E]",
        "[men_at_arms|E]",
        expected=1,
        label="men-at-arms concept id",
    )
    text = replace_exact(
        text,
        "as surely as ink holds parchment.\n\n"
        "building_type_agot_jordayne_tor_library_01",
        'as surely as ink holds parchment."\n\n'
        "building_type_agot_jordayne_tor_library_01",
        expected=1,
        label="Jordayne unit localization quote",
    )
    write_text(relative, text)

    write_text(
        "localization/english/bla_119_runtime_rebase_l_english.yml",
        """l_english:
 intimidated_opinion:0 "Intimidated"
 fear_opinion:0 "Fear"
 uneasy_court_opinion:0 "Uneasy at Court"
 exposed_criminal_opinion:0 "Exposed My Crime"
 rival_opinion:0 "Rivalry"
 cultural_disapproval_opinion:0 "Cultural Disapproval"
 offended_opinion:0 "Offended"
 agot_riverlands_bla.0803.a.paranoid_existing_tt:0 "Your existing paranoia sharpens into an unsettling insight."
 weakened_defenses_bla:0 "Weakened Defenses"
 barrowman_legacy_track_name:0 "Barrowman"
 barrowman_legacy_track_desc:0 "Kings Beneath the Mounds"
 great_project_type_tooltip_construct_great_fleet_01:0 "$great_project_type_construct_great_fleet_01_desc$"
 great_project_type_tooltip_construct_great_fleet_02:0 "$great_project_type_construct_great_fleet_02_desc$"
 great_project_type_tooltip_construct_great_fleet_03:0 "$great_project_type_construct_great_fleet_03_desc$"
""",
    )


def generate_dds_reencodes() -> None:
    """Re-encode malformed BC7 assets losslessly at their original dimensions."""
    for relative in DDS_REENCODES:
        source = BLOODLINES / relative
        target = OUTPUT / relative
        if not source.is_file():
            raise RuntimeError(f"DDS source not found: {source}")
        target.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                "magick",
                str(source),
                "-define",
                "dds:compression=none",
                str(target),
            ],
            check=True,
        )


def main() -> None:
    if not BLOODLINES.is_dir():
        raise RuntimeError(f"Bloodlines Workshop source not found: {BLOODLINES}")
    if not AGOT.is_dir():
        raise RuntimeError(f"AGOT Workshop source not found: {AGOT}")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for generated_directory in ("common", "events", "gfx", "localization"):
        target = OUTPUT / generated_directory
        if target.exists():
            shutil.rmtree(target)

    generate_prison_interaction()
    generate_guarded_special_buildings()
    repair_child_birth_on_action()
    repair_common_files()
    generate_events()
    generate_opinion_compatibility()
    generate_localization()
    generate_dds_reencodes()


def generate(context: GenerationContext) -> None:
    global BLOODLINES, AGOT, OUTPUT
    BLOODLINES = context.source("bloodlines-legacies")
    AGOT = context.source("agot")
    OUTPUT = context.output_root
    main()
