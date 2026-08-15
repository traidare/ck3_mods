#!/usr/bin/env python3
"""Rebase RC71's intentional LoV startup hooks onto current AGOT 0.5."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from gen import GenerationContext
from gen.script import normalize_rebased_source, read_text, write_text
from gen.sources import WorkshopSources
from gen.text import definition_span, replace_exact

GAME_START = "common/on_action/agot_on_actions/agot_game_start.txt"
AGOT_SOURCE_HASH = "7a74d4ef6644caec08fd72c30bea3a499f8582d4a472c0eb5a8370f717c53577"
RC71_SOURCE_HASH = "8d1ac6d5399d6b3499434135b63d173c754a17ac7a4282f366dbad79e8e2f7e3"
AGOT_PIRATE_BLOCK_HASH = (
    "d885afd7771d3701f21fec7ee8ab80d3fd3b07199d1381bfa00c5b6b09f8e1ce"
)

ESTATE_DYNASTIES = {
    6: ("Maegyr", "Vhassar", "Paenymion", "Qhaedar", "Vaelaros"),
    5: ("Staegone", "Tagaros", "Nogarys", "Votar", "Loraq", "Galare", "Uruzarys"),
    4: (
        "Reznak",
        "Pahl",
        "Rhazdar",
        "Yherizan",
        "Kandaq",
        "Ghazeen",
        "Quazzar",
        "Hazkar",
        "Merreq",
        "Naqqan",
        "Dhazak",
        "Yunzak",
        "Zherzyn",
        "Nakloz",
        "Grazdhan",
        "Paenohrin",
    ),
    3: ("Qaggaz", "Myraq", "Ahlaq", "Ullhor", "Grazlar", "Xhore", "Ennyrion"),
    2: ("Eraz", "Rhaezn", "Faez", "Mazlaq"),
}

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


def pinned_source(inputs: RunInputs, item: str, expected_hash: str) -> str:
    text = read_text(inputs.workshop / item / GAME_START)
    actual = hashlib.sha256(text.encode()).hexdigest()
    if actual != expected_hash:
        raise RuntimeError(
            f"{item} game-start source changed: expected {expected_hash}, found {actual}"
        )
    return text


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


def rebase_game_start(inputs: RunInputs) -> None:
    agot = pinned_source(inputs, "2962333032", AGOT_SOURCE_HASH)
    rc71 = pinned_source(inputs, "3719888822", RC71_SOURCE_HASH)
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
    rc_admin = block(rc71, "agot_administrative_setup")
    for tier, next_tier in ((6, 5), (5, 4), (4, 3), (3, 2)):
        admin = replace_exact(
            admin,
            estate_body(admin, tier, next_tier),
            estate_body(rc_admin, tier, next_tier),
            expected=1,
            label=f"LoV estate tier {tier} innovation and capacity guards",
        )
    for tier, dynasties in ESTATE_DYNASTIES.items():
        anchor = ESTATE_ANCHORS[tier]
        additions = "".join(
            f"\t\t\t\t\t\towner.dynasty = dynasty:dynn_{dynasty}\n"
            for dynasty in dynasties
        )
        for dynasty in dynasties:
            reference = f"owner.dynasty = dynasty:dynn_{dynasty}"
            if reference in admin or reference not in rc_admin:
                raise RuntimeError(f"LoV estate dynasty boundary changed: {dynasty}")
        admin = replace_exact(
            admin,
            anchor,
            anchor + additions,
            expected=1,
            label=f"LoV estate tier {tier} dynasties",
        )
    text = replace_exact(
        text,
        block(text, "agot_administrative_setup"),
        admin,
        expected=1,
        label="LoV administrative setup rebase",
    )

    pirate = block(text, "agot_pirate_domiciles_setup")
    pirate_hash = hashlib.sha256(pirate.encode()).hexdigest()
    if pirate_hash != AGOT_PIRATE_BLOCK_HASH:
        raise RuntimeError(f"AGOT pirate setup was not preserved: {pirate_hash}")
    if "agot_realm_narrow_sea_enabled = yes" not in pirate:
        raise RuntimeError("AGOT Narrow Sea pirate guard is missing")
    if "random_direct_de_jure_vassal_title" in text:
        raise RuntimeError("stale random-barony supersiren selection survived")

    write_text(inputs.output, GAME_START, normalize_rebased_source(text))


def generate(context: GenerationContext) -> None:
    rebase_game_start(
        RunInputs(workshop=WorkshopSources(context), output=context.output_root)
    )
