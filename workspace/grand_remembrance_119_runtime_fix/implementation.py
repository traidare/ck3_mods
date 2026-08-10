#!/usr/bin/env python3
"""Repair Grand Remembrance's NPC obituary data for the AGOT playset.

Every replacement is counted, so an upstream update fails loudly instead of
silently generating a stale whole-file override.
"""

from __future__ import annotations

from pathlib import Path

from ck3mm.generation import GenerationContext
from ck3mm.generators.script import read_text, write_text
from ck3mm.generators.sources import WorkshopSources
from ck3mm.generators.text import replace_exact

WORKSHOP: WorkshopSources | None = None
GR_OUTPUT: Path | None = None


def generate_grand_remembrance_agot_obituary() -> None:
    relative = "common/on_action/gr_on_actions.txt"
    text = read_text(WORKSHOP / "3678529052" / relative)
    rice_revalidation = "# RICE COMPATIBILITY REVALIDATION"
    npc_obituary = "# NPC Obituary Processing"
    section_k = "\t\t\t\t# SECTION K: FAME / EVENT TRAITS"
    section_l = "\t\t\t\t# SECTION L: HEALTH & INFAMY"
    section_m2b = "\t\t\t\t# SECTION M2b: ELECTIVE SUCCESSION DETECTION"
    section_m3 = "\t\t\t\t# SECTION M3: SUCCESSION CRISIS MOD DETECTION"
    for marker in (
        rice_revalidation,
        npc_obituary,
        section_k,
        section_l,
        section_m2b,
        section_m3,
    ):
        if text.count(marker) != 1:
            raise RuntimeError(
                "Grand Remembrance obituary rebase: expected one marker "
                f"{marker.strip()!r}, found {text.count(marker)}"
            )

    start = text.index(rice_revalidation)
    end = text.index(npc_obituary)
    text = (
        text[:start]
        + (
            "# RICE COMPATIBILITY: disabled for this AGOT playset\n"
            "# The RICE-only placeholder faith cannot be queried safely when "
            "RICE is absent.\n\n"
        )
        + text[end:]
    )

    start = text.index(section_k)
    end = text.index(section_l)
    text = (
        text[:start]
        + (
            "\t\t\t\t# SECTION K: AGOT compatibility\n"
            "\t\t\t\t# Vanilla/RICE fame traits and vanilla religion/"
            "heritage crossings are\n"
            "\t\t\t\t# unavailable in AGOT. Its compatibility submod "
            "supplies AGOT obituary data.\n"
            "\t\t\t\t\n"
        )
        + text[end:]
    )

    start = text.index(section_m2b)
    end = text.index(section_m3)
    text = (
        text[:start]
        + (
            "\t\t\t\t# SECTION M2b: AGOT compatibility\n"
            "\t\t\t\t# Vanilla elective title laws are removed by AGOT; "
            "skip this flavor classifier.\n"
            "\t\t\t\t\n"
        )
        + text[end:]
    )
    text = replace_exact(
        text,
        (
            "\t\t\t\tif = { limit = { root = { has_trait = "
            "born_in_the_purple } } set_variable = { name = "
            "gr_dynasty_purple value = yes } }\n"
        ),
        ("\t\t\t\t# AGOT removes the vanilla born_in_the_purple trait.\n"),
        expected=1,
        label="Grand Remembrance AGOT born-in-the-purple classifier",
    )
    write_text(GR_OUTPUT, relative, text)

    relative = "common/scripted_effects/gr_npc_obituary_data_effect.txt"
    text = read_text(WORKSHOP / "3678529052" / relative)
    text = replace_exact(
        text,
        """		# Player's opinion of the dead NPC. opinion:X targets a saved event
		# scope by its bare name (no "scope:" prefix — gotcha #9), and it
		# is evaluated relative to the CURRENT scope, so this must run with
		# scope:gr_iter_player (the player) as the acting scope.
		scope:gr_iter_player = {
			save_temporary_scope_as = gr_opinion_holder
		}
		scope:dead_npc = {
			set_variable = { name = gr_opinion value = scope:gr_opinion_holder.opinion:dead_npc }
		}""",
        """		# Capture the player's opinion while both character scopes are valid.
		# save_temporary_opinion_value_as is the CK3 1.19 interface for
		# materializing an opinion as a numeric temporary scope.
		scope:gr_iter_player = {
			save_temporary_opinion_value_as = {
				name = gr_opinion_of_dead_npc
				target = scope:dead_npc
			}
			scope:dead_npc = {
				set_variable = {
					name = gr_opinion
					value = scope:gr_opinion_of_dead_npc
				}
			}
		}""",
        expected=1,
        label="Grand Remembrance NPC obituary opinion value",
    )
    section_k = "\t\t# SECTION K: FAME / EVENT TRAITS"
    section_l = "\t\t# SECTION L: HEALTH & INFAMY"
    section_n = "\t\t# SECTION N: LEGACY SCORE CALCULATION"
    elective = "\t\t\t# Elective"
    for marker in (section_k, section_l, elective, section_n):
        if text.count(marker) != 1:
            raise RuntimeError(
                "Grand Remembrance NPC obituary rebase: expected one marker "
                f"{marker.strip()!r}, found {text.count(marker)}"
            )

    start = text.index(section_k)
    end = text.index(section_l)
    text = (
        text[:start]
        + (
            "\t\t# SECTION K: AGOT compatibility\n"
            "\t\t# Vanilla/RICE fame classifiers are unavailable in AGOT; "
            "the AGOT\n"
            "\t\t# compatibility submod supplies its setting-specific "
            "obituary data.\n"
            "\t\t\n"
        )
        + text[end:]
    )
    text = replace_exact(
        text,
        (
            "\t\t\tif = { limit = { has_trait = born_in_the_purple } "
            "set_variable = { name = gr_dynasty_purple value = yes } }\n"
        ),
        "\t\t\t# AGOT removes the vanilla born_in_the_purple trait.\n",
        expected=1,
        label="Grand Remembrance NPC born-in-the-purple classifier",
    )

    start = text.index(elective)
    scope_end = text.index("\n\t\t}\n", start)
    section_n_start = text.index(section_n)
    if scope_end >= section_n_start:
        raise RuntimeError(
            "Grand Remembrance NPC elective classifier did not end before Section N"
        )
    text = (
        text[:start]
        + (
            "\t\t\t# AGOT removes the vanilla elective title laws; skip "
            "this flavor classifier.\n"
        )
        + text[scope_end:]
    )
    write_text(GR_OUTPUT, relative, text)


def generate(context: GenerationContext) -> None:
    global WORKSHOP, GR_OUTPUT
    WORKSHOP = WorkshopSources(context)
    GR_OUTPUT = context.output_root
    generate_grand_remembrance_agot_obituary()
