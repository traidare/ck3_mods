#!/usr/bin/env python3
"""Rebase Much Faster Activities onto the AGOT playset's scope expectations.

Every replacement is counted, so an upstream update fails loudly instead of
silently generating a stale whole-file override.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from gen import GenerationContext
from gen.script import balanced_brace_end, guard_event_deaths, read_text, write_text
from gen.sources import WorkshopSources
from gen.text import replace_exact


@dataclass(frozen=True, slots=True)
class RunInputs:
    WORKSHOP: WorkshopSources
    MFA_OUTPUT: Path


def script_brace_delta(line: str) -> int:
    code = line.split("#", 1)[0]
    code = re.sub(r'"(?:\\.|[^"\\])*"', '""', code)
    return code.count("{") - code.count("}")


def scale_fractional_random_list_weights(
    text: str, *, expected_lists: int, expected_fractional_weights: int, label: str
) -> str:
    """Scale affected random-list weights by ten so every weight is integral."""
    replacements: list[tuple[int, int, str]] = []
    affected_lists = 0
    fractional_weights = 0
    random_list_pattern = re.compile(r"(?m)^[ \t]*random_list\s*=\s*\{")
    weight_pattern = re.compile(r"^[ \t]*(\d+(?:\.\d+)?)\s*(?==\s*\{)")

    for match in random_list_pattern.finditer(text):
        open_index = text.find("{", match.start(), match.end())
        end_index = balanced_brace_end(text, open_index)
        cursor = text.find("\n", match.end())
        if cursor < 0 or cursor > end_index:
            continue
        cursor += 1
        depth = 1
        weights: list[tuple[int, int, str]] = []
        list_fractional = 0
        while cursor < end_index:
            newline = text.find("\n", cursor, end_index + 1)
            if newline < 0:
                newline = end_index
            line = text[cursor:newline]
            if depth == 1:
                weight_match = weight_pattern.match(line)
                if weight_match:
                    token = weight_match.group(1)
                    start = cursor + weight_match.start(1)
                    finish = cursor + weight_match.end(1)
                    weights.append((start, finish, token))
                    if "." in token:
                        list_fractional += 1
            depth += script_brace_delta(line)
            cursor = newline + 1

        if list_fractional:
            affected_lists += 1
            fractional_weights += list_fractional
            for start, finish, token in weights:
                scaled = Decimal(token) * 10
                if scaled != scaled.to_integral_value():
                    raise RuntimeError(
                        f"{label}: weight {token} does not become integral "
                        "when scaled by ten"
                    )
                replacements.append((start, finish, str(int(scaled))))

    if affected_lists != expected_lists:
        raise RuntimeError(
            f"{label}: expected {expected_lists} fractional random list(s), "
            f"found {affected_lists}"
        )
    if fractional_weights != expected_fractional_weights:
        raise RuntimeError(
            f"{label}: expected {expected_fractional_weights} fractional "
            f"weight(s), found {fractional_weights}"
        )
    for start, finish, replacement in reversed(replacements):
        text = f"{text[:start]}{replacement}{text[finish:]}"
    return text


def generate_mfa_delayed_pulse_scopes(inputs: RunInputs) -> None:
    prefix = "common/on_action/activities"
    fractional_random_lists = {
        "MFA_agot_coronation_on_actions.txt": (1, 1),
        "MFA_coronation_on_actions.txt": (1, 10),
        "MFA_pilgrimage_on_actions.txt": (1, 3),
        "MFA_tournament_on_actions.txt": (1, 4),
        "MFA_wedding_on_actions.txt": (1, 1),
    }
    province_scope_counts = {
        "MFA_adult_education_on_actions.txt": 19,
        "MFA_agot_coronation_on_actions.txt": 46,
        "MFA_chariot_race_on_actions.txt": 14,
        "MFA_coronation_on_actions.txt": 92,
        "MFA_feast_on_actions.txt": 53,
        "MFA_festival_on_actions.txt": 13,
        "MFA_funeral_on_actions.txt": 45,
        "MFA_gruesome_festival_on_actions.txt": 21,
        "MFA_hunt_on_actions.txt": 4,
        "MFA_pilgrimage_on_actions.txt": 28,
        "MFA_playdate_on_actions.txt": 24,
        "MFA_tour_on_actions.txt": 39,
        "MFA_tournament_on_actions.txt": 37,
        "MFA_wedding_on_actions.txt": 59,
        "MFA_witch_ritual_on_actions.txt": 10,
        "converted_pulse_actions/MFA_agot_coronation_pulse_actions.txt": 10,
        "converted_pulse_actions/MFA_chariot_race_pulse_actions.txt": 2,
        "converted_pulse_actions/MFA_coronation_pulse_actions.txt": 12,
        "converted_pulse_actions/MFA_education_pulse_actions.txt": 1,
        "converted_pulse_actions/MFA_feast_oltner_pulse_actions.txt": 29,
        "converted_pulse_actions/MFA_feast_pulse_actions.txt": 26,
        "converted_pulse_actions/MFA_general_pulse_actions.txt": 4,
        "converted_pulse_actions/MFA_pilgrimage_pulse_actions.txt": 17,
        "converted_pulse_actions/MFA_playdate_pulse_actions.txt": 26,
        "converted_pulse_actions/MFA_tour_pulse_actions.txt": 12,
        "converted_pulse_actions/MFA_tournament_pulse_actions.txt": 22,
        "converted_pulse_actions/MFA_wedding_pulse_actions.txt": 22,
        "converted_pulse_actions/MFA_witch_ritual_pulse_actions.txt": 8,
    }
    for filename, expected in province_scope_counts.items():
        relative = f"{prefix}/{filename}"
        text = read_text(inputs.WORKSHOP / "3723597729" / relative)
        if filename == "MFA_playdate_on_actions.txt":
            text = replace_exact(
                text,
                """			limit = {
				var:MFA_phase_0_remaining >= 1
				scope:activity = { is_current_phase_active = yes }
""",
                """			limit = {
				var:MFA_phase_0_remaining >= 1
				exists = scope:activity
				scope:activity = { is_current_phase_active = yes }
""",
                expected=1,
                label="MFA delayed playdate activity-scope guard",
            )
        text = replace_exact(
            text,
            "scope:province",
            "scope:activity.activity_location",
            expected=expected,
            label=f"MFA delayed pulse activity locations in {filename}",
        )
        if filename == "MFA_hunt_on_actions.txt":
            text = replace_exact(
                text,
                "multiply = hunt_success_chance_roco_amenity_level_value",
                (
                    "multiply = scope:activity."
                    "hunt_success_chance_roco_amenity_level_value"
                ),
                expected=1,
                label="MFA delayed hunt success activity value",
            )
            text = replace_exact(
                text,
                "root.activity_host",
                "scope:activity.activity_host",
                expected=6,
                label="MFA delayed hunt activity-host scopes",
            )
            text = replace_exact(
                text,
                "is_participant_in_activity = root",
                "is_participant_in_activity = scope:activity",
                expected=1,
                label="MFA delayed hunt participant activity scope",
            )
        if filename in fractional_random_lists:
            expected_lists, expected_weights = fractional_random_lists[filename]
            text = scale_fractional_random_list_weights(
                text,
                expected_lists=expected_lists,
                expected_fractional_weights=expected_weights,
                label=f"MFA random-list weights in {filename}",
            )
        write_text(inputs.MFA_OUTPUT, relative, text)


def generate_mfa_tournament_bow_tradition(inputs: RunInputs) -> None:
    """Disable the vanilla archery bonus MFA's whole-file override carries.

    AGOT removes `tradition_land_of_the_bow`, so the block scores a tradition no
    culture in the playset can hold. It is commented rather than deleted, to keep
    the file lining up with MFA's own copy when the next release is diffed.
    """
    relative = "common/activities/activity_types/tournament.txt"
    text = read_text(inputs.WORKSHOP / "3723597729" / relative)
    text = replace_exact(
        text,
        """				if = {
					limit = {
						culture = { has_cultural_tradition = tradition_land_of_the_bow }
					}
					add = {
						value = 50
						desc = tradition_land_of_the_bow_name
					}
				}
""",
        """				# AGOT disables tradition_land_of_the_bow; MFA's generated
				# whole-file override accidentally restored the vanilla block.
				# if = {
				# 	limit = {
				# 		culture = { has_cultural_tradition = tradition_land_of_the_bow }
				# 	}
				# 	add = {
				# 		value = 50
				# 		desc = tradition_land_of_the_bow_name
				# 	}
				# }
""",
        expected=1,
        label="MFA tournament land-of-the-bow tradition bonus",
    )
    # MFA ships these two files CRLF, unlike the on_action files above, so they
    # are written back the way they arrive.
    write_text(inputs.MFA_OUTPUT, relative, text, force_newline="\r\n")


def generate_mfa_tournament_death_guards(inputs: RunInputs) -> None:
    """Let AGOT: Canon Enforcement spare its characters from lethal tournaments.

    These deaths are accidents — a pas d'armes bout, a collapsing stand, a trampled
    peasant — so they are the kind of death canon characters are spared. The
    `show_as_tooltip` copies in 1141 report a death resolved elsewhere in the
    same event and stay unguarded, or the player would be told nothing happened
    to a character who did in fact die.
    """
    relative = "events/activities/tournaments/tournament_events.txt"
    text = read_text(inputs.WORKSHOP / "3723597729" / relative)
    for event_key, expected in {
        "tournament_events.1110": 4,
        "tournament_events.1141": 2,
        "tournament_events.1151": 2,
        "tournament_events.1230": 1,
        "tournament_events.1280": 1,
    }.items():
        text = guard_event_deaths(
            text, event_key, expected=expected, skip_tooltips=True
        )
    write_text(inputs.MFA_OUTPUT, relative, text, force_newline="\r\n")


def generate(context: GenerationContext) -> None:

    WORKSHOP = WorkshopSources(context)
    MFA_OUTPUT = context.output_root
    inputs = RunInputs(WORKSHOP=WORKSHOP, MFA_OUTPUT=MFA_OUTPUT)
    generate_mfa_delayed_pulse_scopes(inputs)
    generate_mfa_tournament_bow_tradition(inputs)
    generate_mfa_tournament_death_guards(inputs)
