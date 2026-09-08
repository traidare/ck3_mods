"""Repairs for script faults that dereference unset scopes or undeclared macros.

These run on recurring pulses or during game start, so each fault repeats for as
long as its parent is enabled.
"""

from __future__ import annotations

import re

from gen.script import normalize_rebased_source, read_text, write_text
from gen.text import replace_exact

from .common import (
    assert_source_block_hash,
    extract_top_level_block,
    game_root,
    guard_event_deaths,
)
from .context import RunInputs


def _replace_top_level_block(
    source: str, original: str, repaired: str, *, label: str
) -> str:
    return replace_exact(source, original, repaired, expected=1, label=label)


def guard_appointment_score_calls(block: str) -> str:
    """Gate appointment score triggers on the target title's own succession law."""
    pattern = re.compile(
        r'(?m)^(?P<indent>[ \t]*)"appointment_candidate_accumulated_score'
        r'\(scope:target\)"(?P<operator> >| <=) 0$'
    )

    def replacement(match: re.Match[str]) -> str:
        indent = match.group("indent")
        expression = match.group(0).lstrip()
        return (
            f"{indent}trigger_if = {{\n"
            f"{indent}\tlimit = {{\n"
            f"{indent}\t\tscope:target = {{\n"
            f"{indent}\t\t\thas_title_law_flag = appointment_type_succession\n"
            f"{indent}\t\t}}\n"
            f"{indent}\t}}\n"
            f"{indent}\t{expression}\n"
            f"{indent}}}\n"
            f"{indent}trigger_else = {{ always = no }}"
        )

    repaired, count = pattern.subn(replacement, block)
    if count != 3:
        raise RuntimeError(
            f"support-candidacy repair expected three appointment scores, found {count}"
        )
    target_gate = "\t\t\tscope:target = {\n\t\t\t\tholder = {"
    repaired = replace_exact(
        repaired,
        target_gate,
        (
            "\t\t\tscope:target = {\n"
            "\t\t\t\thas_title_law_flag = appointment_type_succession\n"
            "\t\t\t\tholder = {"
        ),
        expected=2,
        label="support-candidacy title appointment gates",
    )
    return repaired


def strip_unsupported_override_environments(text: str) -> str:
    """Drop the obsolete event environment field rejected by CK3 1.19."""
    repaired, count = re.subn(
        r"(?m)^[ \t]*override_environment\s*=\s*\{[^\n]*\}\s*\n", "", text
    )
    if count != 13:
        raise RuntimeError(
            f"Iron and Salt kraken events expected 13 override_environment fields, found {count}"
        )
    return repaired


def drop_unneeded_title_giver_arguments(text: str) -> str:
    """Remove the TITLE_GIVER argument ``ep3_become_landed_warning_effect`` lacks.

    Every definition of that effect in the playset declares just ``$TITLE$`` and
    ``$TITLE_RECEIVER$``, and passing an undeclared parameter is a documented
    crash cause. The neighbouring ``ep3_landless_invasion_titles_taken_effect``
    call does declare ``$TITLE_GIVER$``, so the removal is anchored to the
    warning effect's block rather than matching the argument anywhere it appears.
    """
    repaired, count = re.subn(
        r"(?ms)(?P<head>^[ \t]*ep3_become_landed_warning_effect = \{\n"
        r"(?:[ \t]*(?!\})[^\n]*\n)*?)"
        r"[ \t]*TITLE_GIVER\s*=\s*scope:defender[ \t]*\n",
        r"\g<head>",
        text,
    )
    if count != 1:
        raise RuntimeError(
            "Adventurer's Beneficiary CB expected 1 unneeded TITLE_GIVER argument, "
            f"found {count}"
        )
    return repaired


def guard_accolade_successor_assignment(block: str) -> str:
    """Assign a generated squire only after revalidating knight eligibility."""
    original = (
        "\t\tif = {\n"
        "\t\t\tlimit = { scope:chosen_knight = { is_courtier_of = scope:owner } }\n"
        "\t\t\tscope:chosen_knight = {\n"
        "\t\t\t\tset_knight_status = force\n"
        "\t\t\t}\n"
        "\t\t}\n"
        "\t\t\n"
        "\t\tscope:accolade_in_need = {\n"
        "\t\t\tset_accolade_successor = scope:chosen_knight\n"
        "\t\t}"
    )
    repaired = """\t\t# Search and recruitment can change state before this effect executes.
\t\t# Fail closed unless the candidate is still a valid knight for this court.
\t\tif = {
\t\t\tlimit = {
\t\t\t\texists = scope:owner
\t\t\t\texists = scope:accolade_in_need
\t\t\t\tscope:chosen_knight = {
\t\t\t\t\tis_alive = yes
\t\t\t\t\tis_ruler = no
\t\t\t\t\tis_courtier_of = scope:owner
\t\t\t\t\tOR = {
\t\t\t\t\t\tis_knight_of = scope:owner
\t\t\t\t\t\tcan_be_knight_trigger = { ARMY_OWNER = scope:owner }
\t\t\t\t\t}
\t\t\t\t}
\t\t\t}
\t\t\tscope:chosen_knight = {
\t\t\t\tif = {
\t\t\t\t\tlimit = { NOT = { is_knight_of = scope:owner } }
\t\t\t\t\tset_knight_status = force
\t\t\t\t}
\t\t\t}
\t\t\tscope:accolade_in_need = {
\t\t\t\tset_accolade_successor = scope:chosen_knight
\t\t\t}
\t\t}"""
    return replace_exact(
        block,
        original,
        repaired,
        expected=1,
        label="LoV generated-squire final eligibility gate",
    )


def defer_accolade_acclaimed_death(block: str) -> str:
    """Move accolade death bookkeeping out of its code-driven transition."""
    worker = replace_exact(
        block,
        "on_accolade_acclaimed_death = {\n\teffect = {",
        """agot_playset_runtime_accolade_acclaimed_death = {
\ttrigger = {
\t\texists = accolade_owner
\t\texists = scope:old_acclaimed_knight
\t}
\teffect = {""",
        expected=1,
        label="deferred accolade acclaimed-death worker",
    )
    dispatcher = """on_accolade_acclaimed_death = {
\ton_actions = {
\t\tdelay = { days = 1 }
\t\tagot_playset_runtime_accolade_acclaimed_death
\t}
}"""
    return f"{dispatcher}\n\n{worker}"


def _repair_dragon_template_block(block: str, variable: str) -> str:
    pattern = re.compile(
        rf"(?P<indent>[ \t]*)every_in_global_list = \{{\n"
        rf"(?P=indent)\tvariable = gl_dragon_variable_storage\n"
        rf"(?P=indent)\tlimit = \{{\n"
        rf"(?P=indent)\t\t(?P<identity>var:dragon_id \?= [^\n]+)\n"
        rf"(?P=indent)\t\}}\n"
        rf"(?P=indent)\tsave_temporary_scope_as = dragon_var_story_val\n"
        rf"(?P=indent)\}}\n"
        rf"(?P=indent)if = \{{\n"
        rf"(?P=indent)\tlimit = \{{\n"
        rf"(?P=indent)\t\texists = scope:dragon_var_story_val\n"
        rf"(?P=indent)\t\tscope:dragon_var_story_val = \{{ has_variable = {variable} \}}\n"
        rf"(?P=indent)\t\}}\n"
        rf"(?P=indent)\tvalue = scope:dragon_var_story_val.var:{variable}\n"
        rf"(?P=indent)\}}"
    )

    def replacement(match: re.Match[str]) -> str:
        indent = match.group("indent")
        return (
            f"{indent}every_in_global_list = {{\n"
            f"{indent}\tvariable = gl_dragon_variable_storage\n"
            f"{indent}\tlimit = {{\n"
            f"{indent}\t\t{match.group('identity')}\n"
            f"{indent}\t\thas_variable = {variable}\n"
            f"{indent}\t}}\n"
            f"{indent}\tvalue = var:{variable}\n"
            f"{indent}}}"
        )

    repaired, count = pattern.subn(replacement, block)
    if count != 2:
        raise RuntimeError(
            f"dragon template repair for {variable} expected two storage lookups, found {count}"
        )
    return repaired


def generate_naval_contact_stability(inputs: RunInputs) -> None:
    effects_relative = "common/scripted_effects/naval_combat_effects.txt"
    source = read_text(inputs.WORKSHOP / "3772178688" / effects_relative)
    block = assert_source_block_hash(
        source,
        "naval_combat_update_contact_effect",
        "740d9bde09b7fb03ed55dde411c51daf13a67be23c376e9bf38852a03dac7175",
        label="Naval Combat automatic-contact effect",
    )
    repaired = replace_exact(
        block,
        """\t\t\t\tscope:naval_combat_contact_enemy = {
\t\t\t\t\tset_variable = { name = naval_combat_contact_target value = root }
\t\t\t\t\tset_variable = { name = naval_combat_contact_value value = 0 }
\t\t\t\t}""",
        """\t\t\t\t# The saved iterator scope is weak. Re-enter through the strong
\t\t\t\t# character variable before writing the reciprocal contact state.
\t\t\t\tvar:naval_combat_contact_target = {
\t\t\t\t\tset_variable = { name = naval_combat_contact_target value = root }
\t\t\t\t\tset_variable = { name = naval_combat_contact_value value = 0 }
\t\t\t\t}""",
        expected=1,
        label="Naval Combat reciprocal contact state",
    )
    source = _replace_top_level_block(
        source, block, repaired, label="Naval Combat contact effect replacement"
    )
    write_text(inputs.OUTPUT, effects_relative, normalize_rebased_source(source))

    events_relative = "events/naval_combat_events.txt"
    event_path = inputs.WORKSHOP / "3781577713" / events_relative
    events = read_text(event_path)
    events = replace_exact(
        events,
        """naval_combat.0100 = {
\ttype = character_event
\thidden = yes

\timmediate = {""",
        """naval_combat.0100 = {
\ttype = character_event
\thidden = yes
\ttrigger = { is_alive = yes }

\timmediate = {""",
        expected=1,
        label="Iron and Salt weekly naval-event living-character gate",
    )
    write_text(inputs.OUTPUT, events_relative, normalize_rebased_source(events))


def generate_appointment_score_guards(inputs: RunInputs) -> None:
    relative = "common/character_interactions/06_ep3_interactions.txt"
    source = read_text(inputs.WORKSHOP / "3788296332" / relative)
    block = assert_source_block_hash(
        source,
        "support_candidacy_interaction",
        "d292185ad9e8e11770beaf32681812065ea7576f2fe1545777b3a1d87b6ac579",
        label="LoV support-candidacy interaction",
    )
    source = _replace_top_level_block(
        source,
        block,
        guard_appointment_score_calls(block),
        label="support-candidacy interaction replacement",
    )
    write_text(inputs.OUTPUT, relative, normalize_rebased_source(source))


def generate_accolade_lifecycle_stability(inputs: RunInputs) -> None:
    """Prevent invalid generated successors and defer death-transition effects.

    The effective LoV squire effect can fail ``set_knight_status`` and then still
    install that character as the accolade successor. Retained native crashes
    subsequently place the faulting worker in the synchronous
    ``on_accolade_acclaimed_death`` callback while CK3 is finalizing accolade
    succession. Revalidate the candidate immediately before both mutations and
    queue the vanilla callback body one day later, preserving its accolade root
    and saved event targets without running an effect chain inside the native
    transition.
    """
    effects_relative = (
        "common/scripted_effects/"
        "zzzz_lv_agot_scripted_effect_runtime_overrides_v0_2_2.txt"
    )
    effects_source = read_text(inputs.WORKSHOP / "3788296332" / effects_relative)
    squire_effect = assert_source_block_hash(
        effects_source,
        "accolade_create_squire_effect",
        "b167eadf88c3a52fadee8bfaeee55e969436d86e65ea6f256d6670a52f501738",
        label="LoV generated-squire effect",
    )
    effects_source = _replace_top_level_block(
        effects_source,
        squire_effect,
        guard_accolade_successor_assignment(squire_effect),
        label="LoV generated-squire effect replacement",
    )
    repaired_squire_effect = extract_top_level_block(
        effects_source, "accolade_create_squire_effect"
    )
    # A dedicated later-named definition keeps the override narrow and avoids
    # making this module the effective owner of every unrelated LoV effect.
    (inputs.OUTPUT / effects_relative).unlink(missing_ok=True)
    write_text(
        inputs.OUTPUT,
        "common/scripted_effects/zzzzz_agot_playset_accolade_stability.txt",
        (
            "# Revalidate generated accolade successors after recruitment.\n\n"
            f"{repaired_squire_effect}\n"
        ),
    )

    on_action_relative = "common/on_action/accolade_on_actions.txt"
    on_action_source = read_text(game_root(inputs) / on_action_relative)
    acclaimed_death = assert_source_block_hash(
        on_action_source,
        "on_accolade_acclaimed_death",
        "d4e7e4884d5742c8f123df4f5706d6a776a83833c3a88cf032d96283fd9976ce",
        label="CK3 acclaimed-knight death on-action",
    )
    on_action_source = _replace_top_level_block(
        on_action_source,
        acclaimed_death,
        defer_accolade_acclaimed_death(acclaimed_death),
        label="deferred acclaimed-knight death on-action",
    )
    write_text(
        inputs.OUTPUT,
        on_action_relative,
        normalize_rebased_source(on_action_source),
    )


def generate_beyond_wall_queued_event_guard(inputs: RunInputs) -> None:
    relative = "events/agot_events/agot_btw_maintenance_events.txt"
    source = read_text(inputs.WORKSHOP / "2962333032" / relative)
    block = assert_source_block_hash(
        source,
        "agot_btw_maintenance.0001",
        "1421b208c7b63cdcc02295670d908bdf8fb7c902e5eb0dfa1c2482f3ef5d1b9f",
        label="AGOT Beyond-the-Wall title-gain maintenance event",
    )
    repaired = replace_exact(
        block,
        """\ttrigger = {
\t\tscope:title = {
\t\t\ttier = tier_county
\t\t\ttitle_province = { geographical_region = world_westeros_beyond_the_wall }
\t\t}
\t}""",
        """\ttrigger = {
\t\ttrigger_if = {
\t\t\tlimit = {
\t\t\t\texists = scope:title
\t\t\t\texists = scope:title.title_province
\t\t\t}
\t\t\tscope:title = {
\t\t\t\ttier = tier_county
\t\t\t\ttitle_province = { geographical_region = world_westeros_beyond_the_wall }
\t\t\t}
\t\t}
\t\ttrigger_else = { always = no }
\t}""",
        expected=1,
        label="Beyond-the-Wall queued title/province gate",
    )
    source = _replace_top_level_block(
        source, block, repaired, label="Beyond-the-Wall maintenance event replacement"
    )
    write_text(inputs.OUTPUT, relative, normalize_rebased_source(source))


def generate_naval_coastal_raid_tooltip(inputs: RunInputs) -> None:
    relative = "common/decisions/naval_combat_decisions.txt"
    source = read_text(inputs.WORKSHOP / "3772178688" / relative)
    block = assert_source_block_hash(
        source,
        "naval_combat_raid_blockaded_coast_decision",
        "8cc8eac8f74dac73ce2ec20405f34a5cb5e475e1e8d2d8199622b3750470bdaa",
        label="Naval Combat coastal-raid decision",
    )
    repaired = replace_exact(
        block,
        """\t\t\t\t\tadd_gold = var:naval_combat_coastal_raid_loot
\t\t\t\t\tscope:naval_combat_raid_target = {
\t\t\t\t\t\tremove_short_term_gold = root.var:naval_combat_coastal_raid_loot
\t\t\t\t\t}""",
        """\t\t\t\t\t# Tooltips do not execute the set_variable above. Repeat the
\t\t\t\t\t# deterministic formula so preview evaluation never reads an unset var.
\t\t\t\t\tadd_gold = {
\t\t\t\t\t\tvalue = scope:naval_combat_raid_target.gold
\t\t\t\t\t\tmultiply = 0.10
\t\t\t\t\t\tmin = 1
\t\t\t\t\t}
\t\t\t\t\tscope:naval_combat_raid_target = {
\t\t\t\t\t\tremove_short_term_gold = {
\t\t\t\t\t\t\tvalue = gold
\t\t\t\t\t\t\tmultiply = 0.10
\t\t\t\t\t\t\tmin = 1
\t\t\t\t\t\t}
\t\t\t\t\t}""",
        expected=1,
        label="Naval Combat coastal-raid tooltip-safe transfer",
    )
    source = _replace_top_level_block(
        source, block, repaired, label="Naval Combat coastal-raid replacement"
    )
    write_text(inputs.OUTPUT, relative, normalize_rebased_source(source))


def generate_dragon_template_storage_guards(inputs: RunInputs) -> None:
    relative = "common/script_values/00_agot_dragon_gene_values.txt"
    source = read_text(inputs.WORKSHOP / "2962333032" / relative)
    repairs = (
        (
            "gene_dragon_fire_color_template_svalue",
            "gene_dragon_fire_color_template",
            "e7ec5b8d5a1cab247688ef16c4f74fffbc67a9384863b3af95875a5777de1727",
        ),
        (
            "gene_dragon_fire_smoke_template_svalue",
            "gene_dragon_fire_smoke_template",
            "f53c5f22a80b5008de5f5c7f18a1db4ec34569cb4af412b101b86d18258ab0ea",
        ),
    )
    for key, variable, expected_hash in repairs:
        block = assert_source_block_hash(
            source, key, expected_hash, label=f"AGOT dragon template value {key}"
        )
        source = _replace_top_level_block(
            source,
            block,
            _repair_dragon_template_block(block, variable),
            label=f"AGOT dragon template replacement {key}",
        )
    write_text(inputs.OUTPUT, relative, normalize_rebased_source(source))


def generate_adventurer_beneficiary_cb_guard(inputs: RunInputs) -> None:
    relative = "common/casus_belli_types/adventurers_beneficiary_conquer.txt"
    source = read_text(inputs.WORKSHOP / "3349316031" / relative)
    block = assert_source_block_hash(
        source,
        "adventurer_beneficiary_independence_war",
        "4f564e64de5fcabb675a07ee69c1ff08b3aaf43afd8aac5f7e8a24b322225601",
        label="Adventurer's Beneficiary independence war",
    )
    repaired = replace_exact(
        block,
        """\tallowed_against_character = {
\t\tscope:attacker.var:val_beneficiary = {
\t\t\tliege = scope:defender
\t\t}
\t}""",
        """\tallowed_against_character = {
\t\ttrigger_if = {
\t\t\tlimit = { scope:attacker = { exists = var:val_beneficiary } }
\t\t\tscope:attacker.var:val_beneficiary = {
\t\t\t\tliege = scope:defender
\t\t\t}
\t\t}
\t\ttrigger_else = { always = no }
\t}""",
        expected=1,
        label="Adventurer's Beneficiary CB variable guard",
    )
    source = _replace_top_level_block(
        source, block, repaired, label="Adventurer's Beneficiary CB replacement"
    )
    # ep3_become_landed_warning_effect declares only $TITLE$ and $TITLE_RECEIVER$.
    source = drop_unneeded_title_giver_arguments(source)
    write_text(inputs.OUTPUT, relative, normalize_rebased_source(source))


def generate_kraken_event_parser_repair(inputs: RunInputs) -> None:
    relative = "events/kraken_events.txt"
    path = inputs.WORKSHOP / "3781577713" / relative
    source = strip_unsupported_override_environments(read_text(path))
    # A kraken taking a traveller is an accident, so protected characters are
    # spared it: the entourage victim in kraken.0100, the travel plan owner
    # when no entourage member is available, and the challenger in kraken.1105.
    source = guard_event_deaths(source, "kraken.0100", expected=2)
    source = guard_event_deaths(source, "kraken.1105", expected=1)
    write_text(inputs.OUTPUT, relative, normalize_rebased_source(source))


def generate_kraken_creation_scope_guard(inputs: RunInputs) -> None:
    """Make the created kraken's follow-up block optional.

    `naval_combat_initialize_decision` starts the kraken population system, and
    that decision stays offered until the naval AI seeding global is set. CK3
    walks a decision's effect tree to build its tooltip, and in that mode
    `create_character` produces nothing, so `save_scope_as = kraken` leaves a
    dead handle. Every statement under `scope:kraken` then dereferences it:
    `untyped trigger [ Scoped object of type 'character' is not valid ]` from
    `kraken_refresh_derived_statistics_effect` and
    `kraken_refresh_presence_danger_effect`, five per evaluation, repeated for
    as long as the decisions panel is drawn.

    The optional-scope operator skips the block when the switch fails and is
    inert once the effect actually runs, because a real `create_character` has
    always populated the scope by then.
    """
    relative = "common/scripted_effects/00_kraken_effects.txt"
    source = read_text(inputs.WORKSHOP / "3781577713" / relative)
    # Eleven blocks in this file enter `scope:kraken`; only the one the creation
    # effect owns can be reached with the scope unset.
    block = extract_top_level_block(source, "kraken_create_at_saved_location_effect")
    repaired = replace_exact(
        block,
        "\tscope:kraken = {\n",
        "\tscope:kraken ?= {\n",
        expected=1,
        label="Iron and Salt kraken creation scope guard",
    )
    source = _replace_top_level_block(
        source, block, repaired, label="Iron and Salt kraken creation effect"
    )
    write_text(inputs.OUTPUT, relative, normalize_rebased_source(source))
