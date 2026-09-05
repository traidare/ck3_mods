"""Runtime repairs for integrations."""

from __future__ import annotations

from gen.script import normalize_rebased_source, read_text, write_text
from gen.text import replace_exact

from .common import (
    assert_source_block_hash,
    game_root,
    guard_event_deaths,
    remove_enclosing_block,
)
from .context import RunInputs


def generate_baie_rebases(inputs: RunInputs) -> None:
    """Replay BAIE's compatible deltas on AGOT's current parent definitions."""
    baie = inputs.WORKSHOP / "3732116186"

    nickname_relative = "common/scripted_effects/00_nickname_effects.txt"
    vanilla_nickname = read_text(game_root(inputs) / nickname_relative)
    agot_nickname = read_text(inputs.WORKSHOP / "2962333032" / nickname_relative)
    baie_nickname = read_text(
        baie / "common/scripted_effects/baie_wl_nickname_effects.txt"
    )
    assert_source_block_hash(
        vanilla_nickname,
        "assign_random_nickname_effect",
        "44ef022098a7a965cfe73d33758d8ae0f2d03ea9c6fb0e0f4871a80c4d26e41c",
        label="CK3 nickname effect used by BAIE",
    )
    assert_source_block_hash(
        baie_nickname,
        "assign_random_nickname_effect",
        "d13ce7361dc64a4d662e4f2d1ba1f5c99959e78a3bbcc82b6c9f86810bc3de90",
        label="BAIE nickname effect",
    )
    nickname = assert_source_block_hash(
        agot_nickname,
        "assign_random_nickname_effect",
        "bc1777d7a3ded27d6adac2e700013f03db447b29f47e8b7ee9cefefd4c03f3da",
        label="AGOT nickname effect",
    )
    nickname = replace_exact(
        nickname,
        """\t\t\t\t\thas_personality_submissive_trigger = yes
\t\t\t\t\tlearning >= 16
\t\t\t\t\tnum_of_relation_ward >= 2
""",
        """\t\t\t\t\thas_personality_submissive_trigger = yes
\t\t\t\t\tlearning >= 14
\t\t\t\t\tnum_of_relation_ward >= wlbol_ward_limit
""",
        expected=1,
        label="BAIE sage nickname threshold",
    )
    write_text(
        inputs.OUTPUT,
        "common/scripted_effects/baie_wl_nickname_effects.txt",
        f"# Generated BAIE rebase onto AGOT's current nickname effect.\n\n{nickname}\n",
    )

    travel_relative = "events/travel_events/travel_events_james.txt"
    vanilla_travel = read_text(game_root(inputs) / travel_relative)
    agot_travel = read_text(inputs.WORKSHOP / "2962333032" / travel_relative)
    baie_travel = read_text(baie / travel_relative)
    assert_source_block_hash(
        vanilla_travel,
        "travel_events.4012",
        "21d34fbc1cb00105d46ac03c9cb4d337dfb464e5a73dce6a555840fd89267f41",
        label="CK3 feral-child travel event used by BAIE",
    )
    assert_source_block_hash(
        baie_travel,
        "travel_events.4012",
        "c3b463691047d7f48161e4b3417cbce3b7a425ed59b8c0835efe16c8e4121d6b",
        label="BAIE feral-child travel event",
    )
    travel_event = assert_source_block_hash(
        agot_travel,
        "travel_events.4012",
        "cb587d9c45944726f1c0d01c54476dd158489335986b21674de264f77b0c80c9",
        label="AGOT feral-child travel event",
    )
    repaired_travel_event = replace_exact(
        travel_event,
        "\t\t\tnum_of_relation_ward < 2\n",
        "\t\t\tnum_of_relation_ward < wlbol_ward_limit\n",
        expected=1,
        label="BAIE feral-child ward limit",
    )
    agot_travel = replace_exact(
        agot_travel,
        travel_event,
        repaired_travel_event,
        expected=1,
        label="BAIE feral-child travel-event rebase",
    )
    # Canon-enforcement guards for the accidental deaths in this file: the viking
    # fight, drowning in a storm at sea, and the wild-animal attack.
    for event_key, deaths in (
        ("travel_events.4003", 3),
        ("travel_events.4007", 4),
        ("travel_events.4032", 3),
    ):
        agot_travel = guard_event_deaths(agot_travel, event_key, expected=deaths)
    write_text(inputs.OUTPUT, travel_relative, normalize_rebased_source(agot_travel))

    interaction_relative = "common/character_interactions/00_education_interactions.txt"
    vanilla_interactions = read_text(game_root(inputs) / interaction_relative)
    agot_interactions = read_text(inputs.WORKSHOP / "2962333032" / interaction_relative)
    baie_interactions = read_text(
        baie / "common/character_interactions/xx_baie_wl_education_interactions.txt"
    )
    interaction_hashes = {
        "educate_child_interaction": (
            "13907affc8938f6365637de4672ef829fc1951addc4273b341a0ceebb23f8300",
            "99eb76caec96d18f35e75efb8e75be81f247a72ed09d3bb03edb5298c81e9215",
            "0e15b7bcba08d4c06b27d855c8fc8d57814b529c8c454d6e41add6f1db58d235",
        ),
        "offer_ward_interaction": (
            "d3e2f59e15b1194198585aa08a29de62e67ead0577c2b71986e3d9279cad90b9",
            "dab8a522bf995a3a6f83c80769aed93f0bae37f7d03107afabd935c2ec7843a4",
            "a4bb5fff16940ade73455a216225c927922a2c563b840d1daafdcb2a474f62ae",
        ),
        "offer_guardianship_interaction": (
            "f17869255ecc24861fd9f2b88d918377162e3da53d0944f7fc72df9d1a59d340",
            "0bef17a73deb873196857f99bd96029b2cbd0266c174e98461427ef8f4bc7b61",
            "bd53e3282efe7ead1ed64a7d65fa4820c7f3a1f16fe4bf6bd63eae793befe366",
        ),
        "make_child_learn_language_interaction": (
            "7def391af3c492589f7fba8a2d2622ee9999609a425a8a0a020d2b6e09345040",
            "9eec35d37535a7a7e35e9d9adf3fe3ccbb75578bb8323de721ff480e417c19aa",
            "124132cf55fba87278600f6140365b7585582f7299fde0bff32f82018f9ae2e5",
        ),
    }
    rebased: dict[str, str] = {}
    for interaction, (vanilla_hash, baie_hash, agot_hash) in interaction_hashes.items():
        assert_source_block_hash(
            vanilla_interactions,
            interaction,
            vanilla_hash,
            label=f"CK3 {interaction} used by BAIE",
        )
        assert_source_block_hash(
            baie_interactions, interaction, baie_hash, label=f"BAIE {interaction}"
        )
        rebased[interaction] = assert_source_block_hash(
            agot_interactions, interaction, agot_hash, label=f"AGOT {interaction}"
        )

    educate = rebased["educate_child_interaction"]
    educate = replace_exact(
        educate,
        """\t\t\tevery_courtier = {
\t\t\t\tlimit = {
\t\t\t\t\tis_physically_able_adult = yes
\t\t\t\t\tnum_of_relation_ward < 2
\t\t\t\t}
\t\t\t\tadd_to_list = characters
\t\t\t}
""",
        """\t\t\tevery_courtier = {
\t\t\t\tlimit = {
\t\t\t\t\tis_physically_able_adult = yes
\t\t\t\t\tnum_of_relation_ward < 2
\t\t\t\t}
\t\t\t\tadd_to_list = characters
\t\t\t}
\t\t\tevery_vassal = {
\t\t\t\tlimit = {
\t\t\t\t\tis_physically_able_adult = yes
\t\t\t\t\tnum_of_relation_ward < wlbol_ward_limit
\t\t\t\t}
\t\t\t\tadd_to_list = characters
\t\t\t}
""",
        expected=1,
        label="BAIE vassal guardian candidates",
    )
    for old, new, expected in (
        ("num_of_relation_ward < 2", "num_of_relation_ward < wlbol_ward_limit", 8),
        ("num_of_relation_ward <= 2", "num_of_relation_ward <= wlbol_ward_limit", 1),
        ("num_of_relation_ward <= 1", "num_of_relation_ward <= wlbol_ward_limit", 1),
        (
            "scope:secondary_actor.num_of_relation_ward >= 1",
            "scope:secondary_actor.num_of_relation_ward >= wlbol_ward_limit",
            1,
        ),
    ):
        educate = replace_exact(
            educate,
            old,
            new,
            expected=expected,
            label=f"BAIE {old} in educate-child interaction",
        )
    older_heir_modifier = """\t\tmodifier = { # Slight preference for older heirs
\t\t\tadd = scope:secondary_recipient.age
\t\t}
"""
    education_ai_modifiers = """
\t\t# Better AI Education: favour skilled, intellectually gifted guardians.
\t\tmodifier = {
\t\t\tadd = 2000
\t\t\tscope:secondary_actor = { has_trait = intellect_good_3 }
\t\t}
\t\tmodifier = {
\t\t\tadd = 1000
\t\t\tscope:secondary_actor = { has_trait = intellect_good_2 }
\t\t}
\t\tmodifier = {
\t\t\tadd = 500
\t\t\tscope:secondary_actor = {
\t\t\t\tOR = {
\t\t\t\t\thas_trait = intellect_good_1
\t\t\t\t\thas_trait = shrewd
\t\t\t\t}
\t\t\t}
\t\t}
\t\tmodifier = {
\t\t\tscope:secondary_recipient = {
\t\t\t\tNOT = { has_focus = education_learning }
\t\t\t}
\t\t\tadd = {
\t\t\t\tvalue = scope:secondary_actor.learning
\t\t\t\tmultiply = 5
\t\t\t}
\t\t}
\t\tmodifier = {
\t\t\tscope:secondary_recipient = { has_focus = education_diplomacy }
\t\t\tadd = { value = scope:secondary_actor.diplomacy multiply = 30 }
\t\t}
\t\tmodifier = {
\t\t\tscope:secondary_recipient = { has_focus = education_martial }
\t\t\tadd = { value = scope:secondary_actor.martial multiply = 30 }
\t\t}
\t\tmodifier = {
\t\t\tscope:secondary_recipient = { has_focus = education_stewardship }
\t\t\tadd = { value = scope:secondary_actor.stewardship multiply = 30 }
\t\t}
\t\tmodifier = {
\t\t\tscope:secondary_recipient = { has_focus = education_intrigue }
\t\t\tadd = { value = scope:secondary_actor.intrigue multiply = 30 }
\t\t}
\t\tmodifier = {
\t\t\tscope:secondary_recipient = { has_focus = education_learning }
\t\t\tadd = { value = scope:secondary_actor.learning multiply = 30 }
\t\t}
"""
    educate = replace_exact(
        educate,
        older_heir_modifier,
        older_heir_modifier + education_ai_modifiers,
        expected=1,
        label="BAIE education AI weights",
    )
    educate = replace_exact(
        educate,
        "\t\tmodifier = { # Prefer to educate your own heirs\n\t\t\tadd = 900\n",
        "\t\tmodifier = { # Prefer to educate your own heirs\n\t\t\tadd = 50\n",
        expected=1,
        label="BAIE own-heir guardian weighting",
    )
    educate = replace_exact(
        educate,
        """\t\tmodifier = { # Otherwise, find a good educator for them
\t\t\tadd = 200
\t\t\tscope:secondary_actor = {
\t\t\t\tOR = {
\t\t\t\t\thas_education_rank_4_trigger = yes
\t\t\t\t\thas_education_rank_3_trigger = yes
\t\t\t\t}
""",
        """\t\tmodifier = { # Otherwise, find a good educator for them
\t\t\tadd = 200
\t\t\tscope:secondary_actor = {
\t\t\t\tOR = {
\t\t\t\t\thas_education_rank_4_trigger = yes
\t\t\t\t\thas_education_rank_3_trigger = yes
\t\t\t\t\thas_education_rank_2_trigger = yes
\t\t\t\t}
""",
        expected=1,
        label="BAIE rank-two guardian preference",
    )
    educate = remove_enclosing_block(
        educate,
        marker="Random peasants can only dream about educating noble children!",
        block_name="modifier",
        label="BAIE lowborn guardian restriction",
    )
    educate = remove_enclosing_block(
        educate,
        marker="Don't care about random children",
        block_name="modifier",
        label="BAIE unrelated-child restriction",
    )
    if "has_focus != education_learning" in educate:
        raise RuntimeError("BAIE rebase retained invalid has_focus comparison syntax")
    rebased["educate_child_interaction"] = educate

    for interaction, expected in (
        ("offer_ward_interaction", 6),
        ("offer_guardianship_interaction", 5),
    ):
        rebased[interaction] = replace_exact(
            rebased[interaction],
            "num_of_relation_ward < 2",
            "num_of_relation_ward < wlbol_ward_limit",
            expected=expected,
            label=f"BAIE ward limit in {interaction}",
        )

    language = rebased["make_child_learn_language_interaction"]
    for aptitude in range(4, -1, -1):
        for position in ("court_tutor_court_position", "court_guru_court_position"):
            language = replace_exact(
                language,
                f"aptitude:{position} = {aptitude}",
                f"aptitude:{position} = {aptitude + 1}",
                expected=1,
                label=f"BAIE {position} aptitude tier {aptitude}",
            )
    rebased["make_child_learn_language_interaction"] = language

    write_text(
        inputs.OUTPUT,
        "common/character_interactions/xx_baie_wl_education_interactions.txt",
        "# Generated BAIE rebase onto AGOT's current education interactions.\n\n"
        + "\n\n".join(rebased.values())
        + "\n",
    )


def generate_any_new_traditions(inputs: RunInputs) -> None:
    relative = "common/on_action/any_new_traditions_on_action.txt"
    text = read_text(inputs.WORKSHOP / "3241130652" / relative)
    text = replace_exact(
        text,
        "dynasty = { has_dynasty_modifier = ary_traditions_5_modifier }",
        "dynasty ?= { has_dynasty_modifier = ary_traditions_5_modifier }",
        expected=2,
        label="Any New Traditions optional dynasty scopes",
    )
    write_text(inputs.OUTPUT, relative, text)

    for filename in (
        "any_new_traditions_decisions.txt",
        "any_vanilla_traditions_decisions.txt",
    ):
        relative = f"common/decisions/{filename}"
        text = read_text(inputs.WORKSHOP / "3241130652" / relative)
        text = replace_exact(
            text,
            "\t\tOR - {",
            "\t\tOR = {",
            expected=1,
            label=f"Any New Traditions malformed OR in {filename}",
        )
        text = replace_exact(
            text,
            "add_dynasty_prestige >= 10000",
            "add_dynasty_prestige = 10000",
            expected=2,
            label=f"Any New Traditions prestige effect in {filename}",
        )
        write_text(inputs.OUTPUT, relative, text)


def generate_health_event_death_guards(inputs: RunInputs) -> None:
    relative = "events/health_events.txt"
    source = read_text(inputs.WORKSHOP / "2962333032" / relative)
    # Canon-enforcement guards for the deaths this file inflicts without the character
    # choosing them: a treatment that goes wrong, and the mysterious death of
    # an incapacitated character.
    for event_key, deaths in (
        ("health.3107", 1),
        ("health.3200", 1),
        ("health.4105", 1),
        ("health.6200", 2),
        ("health.6203", 1),
        ("health.6204", 1),
        ("health.6207", 1),
        ("health.6208", 1),
    ):
        source = guard_event_deaths(source, event_key, expected=deaths)
    source = normalize_rebased_source(source)
    write_text(inputs.OUTPUT, relative, source)
