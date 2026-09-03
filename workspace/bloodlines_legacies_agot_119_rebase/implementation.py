#!/usr/bin/env python3
"""Generate the Bloodlines: Legacies of AGOT CK3 1.19 runtime rebase."""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from gen import GenerationContext
from gen.script import read_text, replace_regex
from gen.script import write_text as write_source
from gen.text import line_block_end, matching_brace, replace_exact


@dataclass(frozen=True, slots=True)
class RunInputs:
    BLOODLINES: Path
    AGOT: Path
    OUTPUT: Path


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

# CK3 1.19 rejects each of these tokens outright, so the parser drops the line
# and the surrounding modifier loads without it. The replacements are the current
# tags that carry the same meaning; where the parent's sign encodes a cost rather
# than a bonus, the value is inverted to keep the intended direction.
CROWNLANDS_MODIFIER_TAGS = {
    # The populace's opinion is county opinion, which the same file already uses
    # correctly elsewhere. Valid in the character, province, and county areas, so
    # it suits both the character- and county-applied modifiers.
    "popular_opinion": ("county_opinion_add", False, 29),
    # No plain scheme-resistance tag exists for characters. Resistance is
    # expressed as a reduction of the attacker's success chance.
    "hostile_scheme_resistance_add": (
        "enemy_hostile_scheme_success_chance_add",
        True,
        16,
    ),
    "hostile_scheme_power_add": ("owned_hostile_scheme_success_chance_add", False, 3),
    # Construction time is expressed as build speed, so less time is more speed.
    "building_construction_time": ("holding_build_speed", True, 3),
    "building_construction_cost": ("holding_build_gold_cost", False, 1),
    "county_tax_mult": ("tax_mult", False, 2),
    # Marriage acceptance has no tag. Attraction opinion is the desirability of a
    # match, which is what the "Ambitious Matches" modifier is named for.
    "marriage_acceptance": ("attraction_opinion", False, 1),
}

# These modifiers mix character-only monthly gains with province- or county-valid
# fields, so the whole application is rejected and nothing is applied. Applying
# them to the ruler keeps every field: development growth, build speed, and
# county opinion all have character meanings covering the county in question.
VELARYON_SCOPED_MODIFIERS = (
    ("title:c_driftmark", "county", "agot_velaryon_preserved_old_driftmark_bla"),
    ("scope:hightide_province_bla", "province", "agot_velaryon_hightide_old_glory_bla"),
    (
        "scope:hightide_province_bla",
        "province",
        "agot_velaryon_hightide_legacy_restoration_bla",
    ),
    ("scope:hightide_province_bla", "province", "agot_velaryon_sea_snake_charts_bla"),
)

# create_character blocks that never declare gender data, which CK3 1.19 refuses
# to validate. The pack's one valid block uses gender_female_chance, so the
# repair follows that field: 0 where the event text uses no gendered getters, and
# AGOT's generic 20 where it is written with adaptive pronouns.
MISSING_GENDER_CHARACTERS = {
    "celtigar_tax_collector_bla": 0,
    "velaryon_corrupt_harbormaster_bla": 0,
    "stepstones_pirate_bla": 20,
    "stepstones_sellsail_captain_bla": 20,
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
    "gfx/interface/illustrations/legacy_tracks/ironborn_legacy_track.dds",
)


def write_text(inputs: RunInputs, relative: str, text: str) -> None:
    write_source(inputs.OUTPUT, relative, text, preserve_trailing_whitespace=True)


def extract_named_block(text: str, name: str) -> str:
    lines = text.splitlines(keepends=True)
    pattern = re.compile(rf"^{re.escape(name)}\s*=\s*\{{")
    starts = [index for index, line in enumerate(lines) if pattern.match(line)]
    if len(starts) != 1:
        raise RuntimeError(f"expected one {name} definition, found {len(starts)}")
    start = starts[0]
    offset = sum(map(len, lines[:start]))
    opening = text.index("{", offset)
    end = matching_brace(text, opening) + 1
    if end < len(text) and text[end] == "\n":
        end += 1
    return text[offset:end]


# Wrappers that do not change the scope a nested effect executes in. Anything
# else opens a new scope, so the innermost of these decides whether an effect
# runs on a dynasty.
SCOPE_TRANSPARENT = re.compile(
    r"^(?:if|else|else_if|limit|trigger|trigger_if|trigger_else|trigger_else_if"
    r"|random_list|random|hidden_effect|show_as_tooltip|custom_tooltip"
    r"|custom_description|option|immediate|after|on_trigger_fail|switch"
    r"|first_valid|while|AND|OR|NOT|NOR|NAND|\d+(?:\.\d+)?)$"
)
DYNASTY_SCOPE = re.compile(r"(?:^|\.)dynasty$|^dynasty:\w+$|_dynasty$|dynasty_house$")


def enclosing_scopes(text: str) -> list[list[str]]:
    """Return the open block headers above every line, outermost first."""
    stack: list[str] = []
    per_line: list[list[str]] = []
    for line in text.split("\n"):
        code = line.split("#", 1)[0]
        per_line.append(list(stack))
        position = 0
        while True:
            opening = code.find("{", position)
            closing = code.find("}", position)
            if opening < 0 and closing < 0:
                break
            if opening >= 0 and (closing < 0 or opening < closing):
                header = re.search(r"([A-Za-z_][\w:.$]*)\s*\??=\s*$", code[:opening])
                stack.append(header.group(1) if header else "?")
                position = opening + 1
            else:
                if stack:
                    stack.pop()
                position = closing + 1
    return per_line


def runs_on_dynasty(scopes: list[str]) -> bool:
    for header in reversed(scopes):
        if DYNASTY_SCOPE.search(header):
            return True
        if SCOPE_TRANSPARENT.match(header):
            continue
        return False
    return False


def scope_dynasty_prestige(text: str) -> tuple[str, int]:
    """Enter the dynasty before adding dynasty prestige from a character scope.

    ``add_dynasty_prestige`` and ``add_dynasty_prestige_level`` are dynasty
    effects. Called straight from an event option they raise
    ``Inconsistent effect scopes (character vs. dynasty)`` and grant nothing.
    AGOT's own idiom for the same grant is ``dynasty ?= { ... }``, which is also
    safe for a character without a dynasty.
    """
    lines = text.split("\n")
    scopes = enclosing_scopes(text)
    repaired = 0
    for index, line in enumerate(lines):
        match = re.match(
            r"^(?P<indent>[ \t]*)(?P<effect>add_dynasty_prestige(?:_level)?)"
            r"\s*=\s*(?P<value>[^\s#]+)\s*$",
            line.split("#", 1)[0].rstrip(),
        )
        if not match or runs_on_dynasty(scopes[index]):
            continue
        lines[index] = (
            f"{match.group('indent')}dynasty ?= {{ "
            f"{match.group('effect')} = {match.group('value')} }}"
        )
        repaired += 1
    return "\n".join(lines), repaired


def innermost_scope(scopes: list[str]) -> str:
    for header in reversed(scopes):
        if not SCOPE_TRANSPARENT.match(header):
            return header
    return "<root>"


def identify_iterated_titles(text: str, *, iterator: str) -> tuple[str, int]:
    """Compare an iterated title with itself instead of asking who holds it.

    Inside a title iterator the scope is a landed title, where ``has_title`` is
    a character trigger and raises
    ``Inconsistent trigger scopes (landed_title vs. character)``. The same
    trigger is correct in the character scopes elsewhere in these files, so only
    the uses under the iterator are rewritten.
    """
    lines = text.split("\n")
    scopes = enclosing_scopes(text)
    repaired = 0
    for index, line in enumerate(lines):
        match = re.match(
            r"^(?P<indent>[ \t]*)has_title = (?P<title>title:[\w]+)[ \t]*$",
            line.split("#", 1)[0].rstrip(),
        )
        if not match or innermost_scope(scopes[index]) != iterator:
            continue
        lines[index] = f"{match.group('indent')}this = {match.group('title')}"
        repaired += 1
    return "\n".join(lines), repaired


def repair_crownlands_modifiers(inputs: RunInputs) -> None:
    relative = "common/modifiers/00_agot_crownlands_modifiers_BLA.txt"
    text = read_text(inputs.BLOODLINES / relative)
    for token, (replacement, invert, expected) in CROWNLANDS_MODIFIER_TAGS.items():
        pattern = re.compile(
            rf"(?m)^(?P<indent>[ \t]*){token}(?P<space>\s*=\s*)(?P<value>-?[\d.]+)[ \t]*$"
        )

        def rewrite(match: re.Match[str]) -> str:
            value = match.group("value")
            if invert:
                value = value[1:] if value.startswith("-") else f"-{value}"
            return f"{match.group('indent')}{replacement}{match.group('space')}{value}"

        text, count = pattern.subn(rewrite, text)
        if count != expected:
            raise RuntimeError(
                f"Crownlands modifiers: expected {expected} {token} field(s), "
                f"rewrote {count}"
            )
    for token in CROWNLANDS_MODIFIER_TAGS:
        if re.search(rf"(?m)^[ \t]*{token}\s*=", text):
            raise RuntimeError(f"Crownlands modifiers still declare {token}")
    write_text(inputs, relative, text)


def repair_artifact_effects(inputs: RunInputs) -> None:
    relative = "common/scripted_effects/00_agot_artifact_effects_BLA.txt"
    text = read_text(inputs.BLOODLINES / relative)
    # Every sibling creation effect in the same file spells the rarity effect
    # correctly, so the misspelling is a single typo rather than an old name.
    text = replace_exact(
        text,
        "set_artifact_rairity_illustrious = yes",
        "set_artifact_rarity_illustrious = yes",
        expected=1,
        label="Celtigar artifact rarity effect name",
    )
    # The artifact ownership effect is set_owner; AGOT uses the same scalar form
    # for its own artifact transfers.
    text = replace_exact(
        text,
        "\t\tset_artifact_owner = $OWNER$\n",
        "\t\tset_owner = $OWNER$\n",
        expected=1,
        label="Celtigar artifact owner assignment",
    )
    write_text(inputs, relative, text)


def generate_prison_interaction(inputs: RunInputs) -> None:
    source = read_text(
        inputs.AGOT / "common/character_interactions/00_prison_interactions.txt"
    )
    block = extract_named_block(source, "execute_prisoner_interaction")
    block = replace_exact(
        block,
        "\t\t\t\tdynasty = { has_dynasty_perk = bolton_legacy_1 }\n",
        (
            # AGOT and Bloodlines both enter the dynasty scope unconditionally,
            # so the flaying option raises `dynasty trigger [ Failed context
            # switch ]` for every dynastyless executioner. This override is the
            # effective last writer for the interaction, so the guard lives here.
            "\t\t\t\ttrigger_if = {\n"
            "\t\t\t\t\tlimit = { exists = dynasty }\n"
            "\t\t\t\t\tdynasty = {\n"
            "\t\t\t\t\t\tOR = {\n"
            "\t\t\t\t\t\t\thas_dynasty_perk = bolton_legacy_1\n"
            "\t\t\t\t\t\t\thas_dynasty_perk = bolton_legacy_1_BLA\n"
            "\t\t\t\t\t\t}\n"
            "\t\t\t\t\t}\n"
            "\t\t\t\t}\n"
            "\t\t\t\ttrigger_else = { always = no }\n"
        ),
        expected=1,
        label="Bolton flaying option",
    )
    write_text(
        inputs, "common/character_interactions/00_prison_interactions_BLA.txt", block
    )


def generate_guarded_special_buildings(inputs: RunInputs) -> None:
    relative = "common/on_action/agot_on_actions/agot_game_start_BLA.txt"
    text = read_text(inputs.BLOODLINES / relative)
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
            f"{indent}\t\tlimit = {{ has_holding = yes has_special_building = no }}\n"
            f"{indent}\t\tadd_special_building = {match.group('building')}\n"
            f"{indent}\t}}\n"
            f"{indent}}}"
        )

    text, count = pattern.subn(guard, text)
    # The upstream file retains sixteen historical assignments as comments.
    # Only its 57 active add_special_building effects must be guarded.
    if count != 57:
        raise RuntimeError(
            f"special-building guards: expected 57 active additions, guarded {count}"
        )
    write_text(inputs, relative, text)


def repair_child_birth_on_action(inputs: RunInputs) -> None:
    relative = "common/on_action/child_birth_on_actions_cultures_BLA.txt"
    text = read_text(inputs.BLOODLINES / relative)
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
    text = replace_exact(text, old, new, expected=1, label="Lyseni child-beauty brace")
    write_text(inputs, relative, text)


def repair_common_files(inputs: RunInputs) -> None:
    # Only files with a defect Bloodlines has not fixed itself are overridden.
    # The formable-kingdoms decisions file is correct upstream and is deliberately
    # left to load unmodified, so the repairs below are the whole common/ scope.
    relative = "common/decisions/agot_decisions/00_agot_major_decisions_BLA.txt"
    text = read_text(inputs.BLOODLINES / relative)
    text = replace_exact(
        text,
        "\t\t\t\topinion < 0\n",
        "\t\t\t\topinion = { target = root value < 0 }\n",
        expected=1,
        label="opinion trigger syntax",
    )
    write_text(inputs, relative, text)

    relative = "common/dynasty_legacies/99_agot_cultures_BLA_legacies.txt"
    text = read_text(inputs.BLOODLINES / relative)
    text = replace_exact(
        text,
        "culture:gogossosi",
        "culture:gogossite",
        expected=1,
        label="Gogossos culture id",
    )
    write_text(inputs, relative, text)

    relative = "common/dynasty_perks/00_agot_BLA_perks.txt"
    text = read_text(inputs.BLOODLINES / relative)
    text = replace_regex(
        text,
        r"^(\s*)build_gold_cost\s+(-0\.(?:10|05))\s*$",
        r"\1build_gold_cost = \2",
        expected=2,
        label="build_gold_cost equals signs",
        flags=re.MULTILINE,
    )
    write_text(inputs, relative, text)

    relative = "common/great_projects/types/zz_agot_great_projects_BLA.txt"
    text = read_text(inputs.BLOODLINES / relative)
    if text.count("@msg_completion_effect_generic") != 3:
        raise RuntimeError("expected three generic completion sound references")
    text = (
        "@msg_completion_effect_generic = "
        '"event:/DLC/EP4/SFX/Stingers/China/'
        'tgp_mx_sting_finishing_great_project_generic"\n\n' + text
    )
    write_text(inputs, relative, text)

    relative = "common/modifiers/00_agot_riverlands_modifiers_BLA.txt"
    text = read_text(inputs.BLOODLINES / relative)
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
    write_text(inputs, relative, text)


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
        end = line_block_end(lines, index)
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


def add_missing_gender_data(text: str) -> tuple[str, int]:
    """Declare gender data on the create_character blocks that omit it."""
    repaired = 0
    for scope_name, female_chance in MISSING_GENDER_CHARACTERS.items():
        pattern = re.compile(
            rf"(?m)(?P<head>^(?P<indent>[ \t]*)create_character = \{{\n)"
            # Body lines only, so the match cannot span a sibling create_character.
            rf"(?P<body>(?:(?![ \t]*create_character)[^\n]*\n)*?)"
            rf"(?P=indent)\tsave_scope_as = {scope_name}\n"
        )
        match = pattern.search(text)
        if not match:
            continue
        if re.search(r"(?m)^[ \t]*gender(?:_female_chance)?\s*=", match.group("body")):
            raise RuntimeError(f"{scope_name} already declares gender data")
        indent = match.group("indent")
        text = (
            text[: match.end("head")]
            + f"{indent}\tgender_female_chance = {female_chance}\n"
            + text[match.end("head") :]
        )
        repaired += 1
    return text, repaired


def repair_event(relative: str, text: str) -> tuple[str, dict[str, int]]:
    original = text
    stats = {"opinion_durations": 0, "traits": 0, "dynasty_prestige": 0, "gender": 0}

    text, stats["opinion_durations"] = remove_monthly_opinion_durations(text)
    text, stats["traits"] = replace_script_traits(text)
    text, stats["dynasty_prestige"] = scope_dynasty_prestige(text)
    text, stats["gender"] = add_missing_gender_data(text)

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

    if relative == (
        "events/agot_decision_events/agot_crownlands_velaryon_stepstones_bla.txt"
    ):
        text, identified = identify_iterated_titles(text, iterator="random_held_title")
        if identified != 8:
            raise RuntimeError(
                "Stepstones reward-title identity triggers: expected 8, "
                f"rewrote {identified}"
            )

    if relative == "events/agot_events/agot_crownlands_celtigar_events_bla.txt":
        # create_character rejects location and employer together. The employer
        # already places the courtier in root's court.
        text = replace_exact(
            text,
            "\t\t\temployer = root\n\t\t\tlocation = root.capital_province\n",
            "\t\t\temployer = root\n",
            expected=1,
            label="Celtigar tax collector location",
        )

    if relative == "events/agot_events/agot_crownlands_darklyn_events_bla.txt":
        # Darke, Darkwood, and Dargood are AGOT cadet houses of dynn_Darklyn,
        # not dynasties: the `dynn_*` string these lines name is each house's
        # own name key. Compared as dynasties they resolve to nothing, so every
        # Darklyn-restoration gate is closed for the houses it exists for.
        for house in ("Darke", "Darkwood", "Dargood"):
            text = replace_exact(
                text,
                f"dynasty = dynasty:dynn_{house}\n",
                f"house = house:house_{house}\n",
                expected=4,
                label=f"House {house} identity trigger",
            )
        text = replace_exact(
            text,
            "add_prowess = 1",
            "add_prowess_skill = 1",
            expected=2,
            label="Darklyn white-cloak prowess effect",
        )
        # CK3 1.19 has no has_liege trigger; the event wants a character who is
        # not independent.
        text = replace_exact(
            text,
            "\t\thas_liege = yes\n",
            "\t\texists = liege\n",
            expected=1,
            label="Darklyn Crown's Due liege trigger",
        )
        # An option may declare one trigger. The second block was dropped, so
        # the bought-claim option had no cost requirement at all.
        text = replace_exact(
            text,
            "\t\t\thas_character_flag = agot_darklyn_reclamation_setback_bla\n"
            "\t\t}\n"
            "\n"
            "\t\ttrigger = {\n"
            "\t\t\tgold >= 200\n"
            "\t\t\tprestige_level >= 2\n"
            "\t\t}\n",
            "\t\t\thas_character_flag = agot_darklyn_reclamation_setback_bla\n"
            "\n"
            "\t\t\tgold >= 200\n"
            "\t\t\tprestige_level >= 2\n"
            "\t\t}\n",
            expected=1,
            label="Darklyn bought-claim duplicate trigger block",
        )

    if relative == "events/agot_events/agot_crownlands_velaryon_events_bla.txt":
        for scope, area, modifier in VELARYON_SCOPED_MODIFIERS:
            text = replace_exact(
                text,
                f"\t\t{scope} = {{\n"
                f"\t\t\tadd_{area}_modifier = {{\n"
                f"\t\t\t\tmodifier = {modifier}\n"
                f"\t\t\t\tyears = 10\n"
                f"\t\t\t}}\n"
                f"\t\t}}",
                f"\t\t# Mixed character and {area} fields, so the {area} "
                f"application is rejected\n"
                f"\t\t# whole. Applied to the ruler, every field keeps its "
                f"meaning.\n"
                f"\t\tadd_character_modifier = {{\n"
                f"\t\t\tmodifier = {modifier}\n"
                f"\t\t\tyears = 10\n"
                f"\t\t}}",
                expected=1,
                label=f"{modifier} application scope",
            )

    if relative == "events/agot_events/agot_riverlands_events_bla.txt":
        # CK3 1.19 has no knighthood effect: knights are chosen from eligible
        # courtiers. set_employer above makes the hedge knight one, and the
        # created character already carries the knight trait.
        text = replace_exact(
            text,
            "\t\t\t\t\tset_employer = root\n\t\t\t\t\tadd_knight = yes\n",
            "\t\t\t\t\tset_employer = root\n",
            expected=1,
            label="Crossroads hedge-knight unknown effect",
        )
        # The occupation-modifier triggers and both Quiet Isle county scopes are
        # correct upstream and untouched here.
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
        # The county-control effect name and its capital_county scope are both
        # correct upstream now.
        # The council's own opinion modifiers carry their opinion values in
        # this module's opinion_modifiers file, so no call site needs one.

    if relative == (
        "events/agot_events/agot_riverlands_blackwood_bracken_events_bla.txt"
    ):
        text = replace_exact(
            text,
            "animation = listening",
            "animation = personality_rational",
            expected=1,
            label="Blackwood-Bracken listening animation",
        )

    # The Piper is_at_war trigger and the Lothston dynasty scopes are both
    # correct upstream now.

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
            "        scope:john_mudd = {\n            agot_house_revival_effect = {\n",
            "        scope:john_mudd = {\n"
            "            dynasty:dynn_Mudd.dynasty_founder.house = {\n"
            "                save_scope_as = bastard_house_of\n"
            "            }\n"
            "            agot_house_revival_effect = {\n",
            expected=2,
            label="John Mudd house-revival scope",
        )

    if relative == "events/agot_decision_events/agot_oldstones_bla_events.txt":
        # Upstream names the real barony rather than the undefined
        # title:c_oldstones, but add_county_modifier still needs the county
        # holding it, which the barony scope does not supply.
        text = replace_exact(
            text,
            "\t\ttitle:b_oldstones = {\n\t\t\tadd_county_modifier = {",
            "\t\ttitle:b_oldstones.county = {\n\t\t\tadd_county_modifier = {",
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


EXPECTED_EVENT_REPAIRS = {
    "opinion_durations": 69,
    # Upstream migrated every retired trait id except one melancholic use.
    "traits": 1,
    # Every Crownlands event option that grants dynasty prestige from a
    # character scope. Upstream's on-action and legacy grants already enter the
    # dynasty and must stay untouched.
    "dynasty_prestige": 47,
    "gender": len(MISSING_GENDER_CHARACTERS),
}


def generate_events(inputs: RunInputs) -> None:
    totals = dict.fromkeys(EXPECTED_EVENT_REPAIRS, 0)
    changed_files = 0
    for source in sorted((inputs.BLOODLINES / "events").rglob("*.txt")):
        relative = source.relative_to(inputs.BLOODLINES).as_posix()
        original = read_text(source)
        patched, stats = repair_event(relative, original)
        for key in totals:
            totals[key] += stats[key]
        if patched != original:
            write_text(inputs, relative, patched)
            changed_files += 1
    for key, expected in EXPECTED_EVENT_REPAIRS.items():
        if totals[key] != expected:
            raise RuntimeError(
                f"{key}: expected {expected} repair(s), made {totals[key]}"
            )
    print(
        f"generated {changed_files} patched event files; "
        f"removed {totals['opinion_durations']} invalid opinion durations; "
        f"migrated {totals['traits']} retired trait references; "
        f"scoped {totals['dynasty_prestige']} dynasty-prestige grants; "
        f"declared gender data for {totals['gender']} created characters"
    )


def generate_opinion_compatibility(inputs: RunInputs) -> None:
    write_text(
        inputs,
        "common/opinion_modifiers/zz_bla_119_opinion_compat.txt",
        """# Bloodlines used opinion ids removed from current CK3.
#
# The Trident Council modifiers below are declared upstream in common/modifiers/
# as static modifiers carrying a vassal_opinion field, but they are only ever
# applied with add_opinion, which reads this database. Their call sites pass no
# explicit opinion, so the value has to live here; each one repeats the
# vassal_opinion the upstream static modifier declares.
attended_trident_council_bla = {
\topinion = 10
\tstacking = yes
}

intimidated_by_trident_lord_bla = {
\topinion = 10
\tstacking = yes
}

disappointed_by_trident_lord_bla = {
\topinion = -10
\tstacking = yes
}

insulted_by_trident_lord_bla = {
\topinion = -10
\tstacking = yes
}

# Never declared anywhere upstream. Every call site passes an explicit opinion,
# so these only need to exist as keys.
betrayed_opinion = {
\topinion = 0
\tstacking = yes
}

claimant_opinion = {
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


def generate_localization(inputs: RunInputs) -> None:
    relative = "localization/replace/english/agot_BLA_l_english.yml"
    text = read_text(inputs.BLOODLINES / relative)
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
    write_text(inputs, relative, text)

    write_text(
        inputs,
        "localization/english/bla_119_runtime_rebase_l_english.yml",
        """l_english:
 betrayed_opinion:0 "Betrayed"
 claimant_opinion:0 "Rival Claimant"
 intimidated_by_trident_lord_bla:0 "Intimidated by the Lord of the Trident"
 disappointed_by_trident_lord_bla:0 "Disappointed by the Lord of the Trident"
 insulted_by_trident_lord_bla:0 "Insulted by the Lord of the Trident"
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


def generate_dds_reencodes(inputs: RunInputs) -> None:
    """Re-encode malformed BC7 assets losslessly at their original dimensions."""
    for relative in DDS_REENCODES:
        source = inputs.BLOODLINES / relative
        target = inputs.OUTPUT / relative
        if not source.is_file():
            raise RuntimeError(f"DDS source not found: {source}")
        target.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["magick", str(source), "-define", "dds:compression=none", str(target)],
            check=True,
        )


def main(inputs: RunInputs) -> None:
    if not inputs.BLOODLINES.is_dir():
        raise RuntimeError(f"Bloodlines Workshop source not found: {inputs.BLOODLINES}")
    if not inputs.AGOT.is_dir():
        raise RuntimeError(f"AGOT Workshop source not found: {inputs.AGOT}")
    inputs.OUTPUT.mkdir(parents=True, exist_ok=True)
    for generated_directory in ("common", "events", "gfx", "localization"):
        target = inputs.OUTPUT / generated_directory
        if target.exists():
            shutil.rmtree(target)

    generate_prison_interaction(inputs)
    generate_guarded_special_buildings(inputs)
    repair_child_birth_on_action(inputs)
    repair_common_files(inputs)
    repair_crownlands_modifiers(inputs)
    repair_artifact_effects(inputs)
    generate_events(inputs)
    generate_opinion_compatibility(inputs)
    generate_localization(inputs)
    generate_dds_reencodes(inputs)


def generate(context: GenerationContext) -> None:

    BLOODLINES = context.source("bloodlines-legacies")
    AGOT = context.source("agot")
    OUTPUT = context.output_root
    inputs = RunInputs(BLOODLINES=BLOODLINES, AGOT=AGOT, OUTPUT=OUTPUT)
    main(inputs)
