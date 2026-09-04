#!/usr/bin/env python3
"""Rebase the LoV AGOT bridge's intentional startup hooks onto current AGOT."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from gen import GenerationContext
from gen.script import normalize_rebased_source, read_text, write_text
from gen.sources import WorkshopSources
from gen.text import definition_span, replace_exact

GAME_START = "common/on_action/agot_on_actions/agot_game_start.txt"

ESTATE_ANCHORS = {
    6: "\t\t\t\t\t\towner.dynasty = dynasty:dynn_Sonaryen\n",
    5: "\t\t\t\t\t\towner.dynasty = dynasty:dynn_Haratis\n",
    4: "\t\t\t\t\t\towner.dynasty = dynasty:dynn_Enrosaena\n",
    3: "\t\t\t\t\t\towner.dynasty = dynasty:dynn_Talraen\n",
    2: "\t\t\t\t\t\towner.dynasty = dynasty:dynn_Erygon\n",
}

SUPERSIREN_REBASE = """\t\t### Enhanced Siren on Steroids System
\t\tevery_ruler = {
\t\t\tlimit = { has_character_flag = supersiren_flag }
\t\t\tremove_variable = siren_distribution_failed
\t\t\tsave_scope_as = siren_source_ruler
\t\t\tevery_held_title = {
\t\t\t\tlimit = { tier > tier_county }
\t\t\t\tprev = { destroy_title = prev }
\t\t\t}
\t\t\tevery_held_county = {
\t\t\t\tsave_scope_as = siren_distribution_title
\t\t\t\ttitle_province ?= { save_scope_as = siren_distribution_province }
\t\t\t\tif = {
\t\t\t\t\tlimit = {
\t\t\t\t\t\tscope:siren_distribution_province ?= {
\t\t\t\t\t\t\texists = culture
\t\t\t\t\t\t\texists = faith
\t\t\t\t\t\t}
\t\t\t\t\t}
\t\t\t\t\tif = {
\t\t\t\t\t\tlimit = { scope:siren_distribution_province.culture = culture:lakefolk }
\t\t\t\t\t\tcreate_character = {
\t\t\t\t\t\t\tlocation = scope:siren_distribution_province
\t\t\t\t\t\t\trandom_traits = yes
\t\t\t\t\t\t\tculture = scope:siren_distribution_province.culture
\t\t\t\t\t\t\tfaith = scope:siren_distribution_province.faith
\t\t\t\t\t\t\tage = { 16 55 }
\t\t\t\t\t\t\tgender = female
\t\t\t\t\t\t\tdynasty = generate
\t\t\t\t\t\t\tafter_creation = {
\t\t\t\t\t\t\t\tget_title = scope:siren_distribution_title
\t\t\t\t\t\t\t\tadd_gold = { minor_gold_value_check medium_gold_value_check }
\t\t\t\t\t\t\t\tadd_prestige = { minor_prestige_gain medium_prestige_gain }
\t\t\t\t\t\t\t\tadd_piety = { minor_piety_gain medium_piety_gain }
\t\t\t\t\t\t\t}
\t\t\t\t\t\t}
\t\t\t\t\t}
\t\t\t\t\telse = {
\t\t\t\t\t\tcreate_character = {
\t\t\t\t\t\t\tlocation = scope:siren_distribution_province
\t\t\t\t\t\t\trandom_traits = yes
\t\t\t\t\t\t\tculture = scope:siren_distribution_province.culture
\t\t\t\t\t\t\tfaith = scope:siren_distribution_province.faith
\t\t\t\t\t\t\tage = { 16 55 }
\t\t\t\t\t\t\tgender = male
\t\t\t\t\t\t\tdynasty = generate
\t\t\t\t\t\t\tafter_creation = {
\t\t\t\t\t\t\t\tget_title = scope:siren_distribution_title
\t\t\t\t\t\t\t\tadd_gold = { minor_gold_value_check medium_gold_value_check }
\t\t\t\t\t\t\t\tadd_prestige = { minor_prestige_gain medium_prestige_gain }
\t\t\t\t\t\t\t\tadd_piety = { minor_piety_gain medium_piety_gain }
\t\t\t\t\t\t\t}
\t\t\t\t\t\t}
\t\t\t\t\t}
\t\t\t\t}
\t\t\t\telse = {
\t\t\t\t\tscope:siren_source_ruler = { set_variable = siren_distribution_failed }
\t\t\t\t}
\t\t\t}
\t\t\tif = {
\t\t\t\tlimit = {
\t\t\t\t\tNOT = { has_variable = siren_distribution_failed }
\t\t\t\t\tis_landed = no
\t\t\t\t}
\t\t\t\tdeath = natural
\t\t\t}
\t\t\tremove_variable = siren_distribution_failed
\t\t}

"""


@dataclass(frozen=True, slots=True)
class RunInputs:
    workshop: WorkshopSources
    output: Path


def block(text: str, name: str) -> str:
    start, end = definition_span(text, name)
    return text[start:end]


def estate_body(text: str, tier: int, next_tier: int) -> str:
    start_marker = f"\t\t\t### {tier}"
    end_marker = f"\t\t\t### {next_tier}"
    start = text.index(start_marker)
    end = text.index(end_marker, start)
    section = text[start:end]
    body_start = section.index("\t\t\t\t# Game screams")
    body_end = section.rfind("\n\t\t\t}")
    if body_end <= body_start:
        raise RuntimeError(f"estate tier {tier} body could not be isolated")
    return section[body_start:body_end]


def estate_guard_span(text: str, tier: int, next_tier: int) -> tuple[int, int]:
    """Return the span of the tier's estate-slot setup that LoV guards.

    The rest of AGOT's tier body changes independently, so copying the bridge's
    whole tier would restore stale parent behaviour.  The guarded setup ends
    immediately before the shared random-building loop.

    Several tiers hold byte-identical setups in AGOT, so callers splice by
    span; matching on the text itself would be ambiguous.
    """
    section_start = text.index(f"\t\t\t### {tier}")
    section_end = text.index(f"\t\t\t### {next_tier}", section_start)
    start = text.index("\t\t\t\t# Game screams", section_start)
    end = text.index("\n\t\t\t\twhile = {", start)
    if not section_start < start < end < section_end:
        raise RuntimeError(f"estate tier {tier} setup could not be isolated")
    return start, end


def rebase_game_start(inputs: RunInputs) -> None:
    # sources.lock.json pins both game-start files by content, so a hash
    # repeated here would only be a second copy to update by hand.
    agot = read_text(inputs.workshop / "2962333032" / GAME_START)
    bridge = read_text(inputs.workshop / "3719888822" / GAME_START)
    text = agot

    on_start = block(text, "agot_on_game_start")
    supersiren_start = on_start.index("\t\t### Enhanced Siren on Steroids System")
    supersiren_end = on_start.index("\t\t### Beyond the Wall setup", supersiren_start)
    on_start = (
        on_start[:supersiren_start] + SUPERSIREN_REBASE + on_start[supersiren_end:]
    )
    text = replace_exact(
        text,
        block(text, "agot_on_game_start"),
        on_start,
        expected=1,
        label="AGOT supersiren capital-safe rebase",
    )

    dummy = block(text, "agot_dummy_rulers")
    tail = "\n\t}\n}"
    if not dummy.endswith(tail):
        raise RuntimeError("AGOT dummy-ruler block tail changed")
    dummy = (
        dummy[: -len(tail)] + "\n\n\t\tlv_rehome_all_dummy_rulers_effect = yes" + tail
    )
    text = replace_exact(
        text,
        block(text, "agot_dummy_rulers"),
        dummy,
        expected=1,
        label="LoV dummy-ruler rehome hook",
    )

    after_lobby = block(text, "on_game_start_after_lobby")
    after_lobby = replace_exact(
        after_lobby,
        "\t\tagot_laamp_camp_locations\n",
        "\t\tagot_laamp_camp_locations\n\t\tagot_mantaryans_traits\n",
        expected=1,
        label="LoV Mantaryan startup hook",
    )
    text = replace_exact(
        text,
        block(text, "on_game_start_after_lobby"),
        after_lobby,
        expected=1,
        label="LoV after-lobby hook rebase",
    )

    admin = block(text, "agot_administrative_setup")
    bridge_admin = block(bridge, "agot_administrative_setup")
    for tier, next_tier in ((6, 5), (5, 4), (4, 3), (3, 2)):
        start, end = estate_guard_span(admin, tier, next_tier)
        bridge_start, bridge_end = estate_guard_span(bridge_admin, tier, next_tier)
        guarded = bridge_admin[bridge_start:bridge_end]
        if guarded == admin[start:end]:
            raise RuntimeError(
                f"LoV estate tier {tier} innovation-slot guards are no longer needed"
            )
        if "### " in guarded:
            raise RuntimeError(f"LoV estate tier {tier} guard span crossed a tier")
        admin = admin[:start] + guarded + admin[end:]
    # LoV drives noble family estates from its own title_on_actions.txt, and its
    # game-start estate-owner lists match AGOT's exactly, so none are ported.
    # The checks below fail if it starts widening them here again.
    for anchor in ESTATE_ANCHORS.values():
        if admin.count(anchor) != 1 or bridge_admin.count(anchor) != 1:
            raise RuntimeError(f"estate owner anchor changed: {anchor.strip()}")
    for tier, anchor in ESTATE_ANCHORS.items():
        agot_list = admin[
            admin.rfind("limit", 0, admin.index(anchor)) : admin.index(anchor)
        ]
        bridge_list = bridge_admin[
            bridge_admin.rfind(
                "limit", 0, bridge_admin.index(anchor)
            ) : bridge_admin.index(anchor)
        ]
        if agot_list != bridge_list:
            raise RuntimeError(f"LoV estate tier {tier} owner list diverged again")
    text = replace_exact(
        text,
        block(text, "agot_administrative_setup"),
        admin,
        expected=1,
        label="LoV administrative setup rebase",
    )

    if "random_direct_de_jure_vassal_title" in text:
        raise RuntimeError("stale random-barony supersiren selection survived")

    write_text(inputs.output, GAME_START, normalize_rebased_source(text))


def generate(context: GenerationContext) -> None:
    rebase_game_start(
        RunInputs(workshop=WorkshopSources(context), output=context.output_root)
    )
