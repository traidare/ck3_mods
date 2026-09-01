"""Runtime repairs for court character."""

from __future__ import annotations

from gen.script import normalize_rebased_source, read_text, replace_regex, write_text
from gen.text import replace_exact

from .common import (
    assert_source_block_hash,
    assert_source_file_hash,
    extract_top_level_block,
    game_root,
    unwrap_unconditional_random_pool_ifs,
)
from .context import RunInputs


def generate_court_events_3020_role_guard(inputs: RunInputs) -> None:
    """Remove optional-scope syntax unsupported by court-scene roles."""
    relative = "events/court_events/01_ep3_court_events_3.txt"
    source = read_text(inputs.WORKSHOP / "2962333032" / relative)
    event = extract_top_level_block(source, "court_events.3020")
    physician_role = (
        "\t\t\tscope:physician ?= {\n"
        "\t\t\t\tgroup = event_group\n"
        "\t\t\t\tanimation = physician\n"
        "\t\t\t}\n"
    )
    repaired_event = replace_exact(
        event,
        physician_role,
        "",
        expected=1,
        label="AGOT court_events.3020 physician role",
    )
    source = replace_exact(
        source,
        event,
        repaired_event,
        expected=1,
        label="AGOT court event 3020 in-place replacement",
    )
    if "namespace = court_events" not in source:
        raise RuntimeError("AGOT court events source lost its namespace during rebase")
    if "court_events.3000 = {" not in source:
        raise RuntimeError(
            "AGOT court events source lost sibling event court_events.3000"
        )
    source = normalize_rebased_source(source)
    write_text(
        inputs.OUTPUT,
        relative,
        "# Runtime rebase: court scene roles require an existing scope.\n\n" + source,
    )


def generate_aurion_title_gain_guard(inputs: RunInputs) -> None:
    """Disable LoV's obsolete title-gain recovery fallback.

    Aurion's recovery event is already attached to travel-plan movement and
    arrival in the LoV base on-actions.  The later RC61 title-gain fallback
    tests every gained county for the expedition building, then attempts to
    grant unique titles to whichever holder happens to gain that county.  The
    latter is the source of repeated title-holder collision errors in normal
    title transfers, so retain its registration but make the fallback inert.
    """
    relative = "common/on_action/cob_on_actions/zz_lv_aurion_lost_expedition_title_gain_rc61.txt"
    source = read_text(inputs.WORKSHOP / "3719888822" / relative)
    handler = extract_top_level_block(
        source, "lv_aurion_lost_expedition_recovery_on_title_gain"
    )
    replacement = (
        "lv_aurion_lost_expedition_recovery_on_title_gain = {\n"
        "    # RC61's title-gain fallback runs in the wrong scope. Recovery\n"
        "    # remains owned by LoV's travel movement/arrival on-actions.\n"
        "    trigger = { always = no }\n"
        "    effect = { }\n"
        "}"
    )
    source = source.replace(handler, replacement, 1)
    write_text(inputs.OUTPUT, relative, source)


def generate_cow_province_setup_rebase(inputs: RunInputs) -> None:
    """Repair COW's stale startup scopes and current AGOT identifiers."""
    relative = "common/on_action/cowagot_province_on_actions.txt"
    source = read_text(inputs.WORKSHOP / "2971198450" / relative)
    lordsport_change = (
        "\t\t\ttitle:b_lordsport = {\n"
        "\t\t\t\tchange_title_holder = {\n"
        "\t\t\t\t  holder = scope:lordsport_holder\n"
        "\t\t\t\t  change = scope:change\n"
        "\t\t\t  }\n"
        "\t\t\t}\n"
    )
    source = replace_exact(
        source,
        lordsport_change,
        "",
        expected=1,
        label="COW Lordsport undefined title-change scope",
    )
    source = replace_exact(
        source,
        "\t\t\t\tadd_building = common_trade_03\n",
        "\t\t\t\tadd_building = common_tradeport_03\n",
        expected=1,
        label="COW stale trade-port building",
    )
    source = replace_exact(
        source,
        "\t\t\t\tremove_building = ironwood_01\n",
        "\t\t\t\tremove_building = agot_ironwood_01\n",
        expected=1,
        label="COW stale ironwood building",
    )
    source = replace_exact(
        source,
        "\t\t\ttitle:b_graced_castle.title_province = {\n"
        "\t\t\t\tadd_building = castle_05\n"
        "\t\t\t}\n\n",
        "",
        expected=1,
        label="COW removed Graced Castle barony",
    )
    source = replace_exact(
        source,
        "title:b_cheesemonger_manse.title_province",
        "title:b_cheesemongers_manse.title_province",
        expected=1,
        label="COW stale Cheesemonger barony",
    )
    source = replace_exact(
        source,
        "\t\t\t\tadd_special_building_slot = bearisland_01\n",
        "\t\t\t\tadd_special_building_slot = agot_rodriks_gift_01\n",
        expected=1,
        label="COW stale Bear Island building slot",
    )
    source = replace_exact(
        source,
        "\t\t\t\tadd_special_building = bearisland_01\n",
        "\t\t\t\tadd_special_building = agot_rodriks_gift_01\n",
        expected=1,
        label="COW stale Bear Island building",
    )
    source = replace_exact(
        source,
        "\t\t\tadd_special_building_slot = harlaw_mines_01\n",
        "\t\t\tadd_building = agot_iron_island_mines_01\n",
        expected=1,
        label="COW stale Harlaw mines building",
    )
    write_text(
        inputs.OUTPUT,
        relative,
        "# Runtime rebase: remove the dead title-change scope and rebase COW's\n"
        "# stale building/barony identifiers onto current AGOT definitions.\n" + source,
    )


def generate_landed_knights(inputs: RunInputs) -> None:
    relative = "common/on_action/on_add_vet_modifer.txt"
    text = read_text(inputs.WORKSHOP / "3361162762" / relative)
    text = replace_exact(
        text,
        """                    NOT = {
                        father = { is_army_owner = root.army_owner }
                    }""",
        """                    # Optional comparison avoids switching through a
                    # missing father and replaces the nonexistent
                    # is_army_owner trigger used by the Workshop source.
                    NOT = { father ?= root.side_primary_participant }""",
        expected=1,
        label="A Landed Knights Mod father/army-owner guard",
    )
    write_text(inputs.OUTPUT, relative, text)


def generate_expanded_court_position_hire_events(inputs: RunInputs) -> None:
    relative = "events/lunarac_00_hire_events.txt"
    text = read_text(inputs.WORKSHOP / "3676293022" / relative)
    text = unwrap_unconditional_random_pool_ifs(
        text, expected=12, label="Expanded Court Position middle-candidate pools"
    )
    text = replace_exact(
        text,
        "grumpy =",
        "irritable =",
        expected=8,
        label="Expanded Court Position grumpy stress impacts",
    )
    text = replace_exact(
        text,
        "depressed = major_stress_impact_loss",
        (
            "depressed_1 = major_stress_impact_loss "
            "depressed_genetic = major_stress_impact_loss"
        ),
        expected=4,
        label="Expanded Court Position depression stress impacts",
    )
    text = replace_exact(
        text,
        "merciful =",
        "compassionate =",
        expected=1,
        label="Expanded Court Position merciful stress impact",
    )
    write_text(inputs.OUTPUT, relative, text)


def generate_legitimacy_over_time_ai(inputs: RunInputs) -> None:
    relative = "events/lot_ai_events.txt"
    text = read_text(inputs.WORKSHOP / "3305687550" / relative)
    text = replace_exact(
        text,
        """                trigger = {
                    OR = {""",
        """                trigger = {
                    # The yearly story-cycle event can outlive the vassal
                    # selected by the scripted effect.
                    scope:recipient ?= { is_alive = yes }
                    OR = {""",
        expected=1,
        label="Legitimacy Over Time sway-recipient guard",
    )
    write_text(inputs.OUTPUT, relative, text)


def generate_red_keep_castellan_guard(inputs: RunInputs) -> None:
    relative = "events/red_keep_title_events.txt"
    text = read_text(inputs.WORKSHOP / "3662281614" / relative)
    event = extract_top_level_block(text, "rk_nw.0002")
    repaired_event = replace_exact(
        event,
        """	immediate = {	
		cp:councillor_castellan = {
			save_scope_as = rk_hand
		}
	}	""",
        """	immediate = {
		if = {
			limit = { exists = cp:councillor_castellan }
			cp:councillor_castellan = {
				save_scope_as = rk_hand
			}
		}
	}""",
        expected=1,
        label="The Red Keep optional castellan scope",
    )
    text = replace_exact(
        text, event, repaired_event, expected=1, label="The Red Keep journey event"
    )
    write_text(inputs.OUTPUT, relative, text)


def assert_red_keep_government_override_is_current(inputs: RunInputs) -> None:
    """Fail when The Red Keep's government override drifts from AGOT again.

    The Red Keep replaces AGOT's whole government database to add one estate
    domicile. When that copy lags behind AGOT it silently drops whichever
    governments AGOT added since, which is how Lorath's three-princes setup lost
    `lorathi_principality_government`. This module ships no file of its own while
    the override stays complete; the check is what makes that safe to rely on.
    """
    relative = "common/governments/00_agot_government_types.txt"
    agot_text = normalize_rebased_source(
        read_text(inputs.WORKSHOP / "2962333032" / relative)
    )
    red_keep_text = normalize_rebased_source(
        read_text(inputs.WORKSHOP / "3662281614" / relative)
    )
    domicile = "\tcourt_generate_commanders = no\n\tdomicile_type = red_keep_estate\n"
    if red_keep_text.count("domicile_type = red_keep_estate") != 1:
        raise RuntimeError("The Red Keep estate government delta changed")
    if (
        red_keep_text.replace(domicile, "\tcourt_generate_commanders = no\n")
        != agot_text
    ):
        raise RuntimeError(
            "The Red Keep government override no longer matches current AGOT "
            "plus the estate domicile; re-audit whether this playset needs a "
            "generated last writer for "
            f"{relative}"
        )


def generate_further_east_startup_government_quarantine(inputs: RunInputs) -> None:
    """Keep Further East setup while suppressing its unsafe government rewrites."""
    relative = "common/on_action/zz_eetlv_gov_dev_on_actions.txt"
    source_path = inputs.WORKSHOP / "3768149491" / relative
    assert_source_file_hash(
        source_path,
        "d33d2f8dd115bd585bb38be87655b708f8f27fe95c1b333f416450a8bc1145e3",
        label="The Further East startup setup",
    )
    text = read_text(source_path)
    text = replace_exact(
        text,
        "\t\tzz_eetlv_gov_dev_effect = yes\n",
        (
            "\t\t# Runtime quarantine: bulk government changes enter CK3's\n"
            "\t\t# theocratic-lease title rewrite with invalid target realms.\n"
        ),
        expected=1,
        label="The Further East bulk government setup",
    )
    text = replace_exact(
        text,
        "\t\tzz_eetlv_cannibal_confederation_effect = yes\n",
        (
            "\t\t# Runtime quarantine: every prerequisite nomad government\n"
            "\t\t# assignment is illegal, so no confederation can be formed.\n"
        ),
        expected=1,
        label="The Further East cannibal government setup",
    )
    if "zz_eetlv_dev_gradient_effect = yes" not in text:
        raise RuntimeError("The Further East rebase lost development setup")
    if "zz_eetlv_buildings_effect = yes" not in text:
        raise RuntimeError("The Further East rebase lost building setup")
    write_text(inputs.OUTPUT, relative, normalize_rebased_source(text))


def generate_automated_squire_training_events(inputs: RunInputs) -> None:
    relative = "events/agot_events/agot_squirehood_ongoing_events.txt"
    text = read_text(inputs.WORKSHOP / "3674548216" / relative)
    event = extract_top_level_block(text, "agot_squirehood_ongoing.0018")
    repaired_event = replace_exact(
        event,
        "right_portrait = scope:second_squire",
        "right_portrait = scope:my_knight",
        expected=1,
        label="AGOT squire downtime portrait scope",
    )
    text = replace_exact(
        text, event, repaired_event, expected=1, label="AGOT squire downtime event"
    )
    text = replace_regex(
        text,
        (
            r"(?m)^([ \t]*)desc = "
            r"(agot_squirehood_ongoing\.0400\.had_a_training_session"
            r"\.desc\.[A-Za-z.]+)[ \t]*$"
        ),
        r"\1text = \2",
        expected=5,
        label="Automated Squire Training interface-message tooltips",
    )
    text = replace_exact(
        text,
        """			ai_chance = {
				base = 115
			}
""",
        "",
        expected=1,
        label="Automated Squire Training nested AI chance",
    )
    write_text(inputs.OUTPUT, relative, text)


def generate_knighting_ceremony_event(inputs: RunInputs) -> None:
    relative = "events/zz_agot_squire_automation_events.txt"
    text = read_text(inputs.WORKSHOP / "3673468355" / relative)
    text = replace_exact(
        text,
        "\tis_triggered_only = yes\n",
        "",
        expected=1,
        label="Knighting Ceremony obsolete event field",
    )
    write_text(inputs.OUTPUT, relative, text)


def generate_house_founders(inputs: RunInputs) -> None:
    relative = "common/character_interactions/00_agot_hf_revealbastards.txt"
    text = read_text(inputs.WORKSHOP / "2967263410" / relative)
    text = replace_exact(
        text,
        "\t\t\t\tprimary_title = {",
        "\t\t\t\tprimary_title ?= {",
        expected=2,
        label="House Founders optional primary-title guards",
    )
    text = replace_exact(
        text,
        "\t\tscope:recipient.top_liege = {",
        "\t\tscope:recipient.top_liege ?= {",
        expected=2,
        label="House Founders optional top-liege guards",
    )
    write_text(inputs.OUTPUT, relative, text)


def generate_house_founders_title_gain_capital_guards(inputs: RunInputs) -> None:
    """Keep title-gain house-head checks safe for landless new rulers."""
    relative = "common/scripted_effects/00_agot_hf_effects.txt"
    source = read_text(inputs.WORKSHOP / "2967263410" / relative)
    effect = assert_source_block_hash(
        source,
        "agot_hf_force_house_head",
        "45044132166b6b31262e2b5be243501067e122d48304ca19a02adc4a20fbe35e",
        label="House Founders force-house-head effect",
    )
    guarded = replace_exact(
        effect,
        "scope:new_ruler.capital_province = {",
        "scope:new_ruler.capital_province ?= {",
        expected=9,
        label="House Founders optional new-ruler capital switches",
    )
    source = replace_exact(
        source,
        effect,
        guarded,
        expected=1,
        label="House Founders force-house-head in-place rebase",
    )
    write_text(inputs.OUTPUT, relative, source)


def generate_house_founders_dynasty_on_action_rebase(inputs: RunInputs) -> None:
    """Preserve House Founders naming and defer dynasty-head trait cleanup.

    Retained crash dumps repeatedly place the faulting worker in
    ``on_became_dynasty_head`` from House Founders' effective same-path
    override.  Its two synchronous trait removals mutate character and
    succession state while CK3 is still changing the dynasty head.  Making the
    effect block empty was insufficient: three subsequent dumps retained the
    same instruction-offset stack and pointed directly at that empty effect.
    Keep House Founders' human dynasty-name event, but move the vanilla/AGOT
    cleanup into a hidden event delayed by one day so no effect chain runs
    inside the code-driven callback.
    """
    relative = "common/on_action/dynasty_on_actions.txt"
    agot_source = read_text(inputs.WORKSHOP / "2962333032" / relative)
    house_founders_source = read_text(inputs.WORKSHOP / "2967263410" / relative)

    agot_created = assert_source_block_hash(
        agot_source,
        "on_dynasty_created",
        "292660b2f69b32a436ac717fa415d9be1cee4ec2ecac01e9db8338bc84218981",
        label="AGOT dynasty-created on-action",
    )
    house_founders_created = assert_source_block_hash(
        house_founders_source,
        "on_dynasty_created",
        "ca580ac534acc0bed07107b92b4f937b2f592274afbee213d503b5da1c8052a0",
        label="House Founders dynasty-created on-action",
    )
    expected_house_founders_source = replace_exact(
        agot_source,
        agot_created,
        house_founders_created,
        expected=1,
        label="House Founders sole dynasty on-action delta",
    )
    if expected_house_founders_source != house_founders_source:
        raise RuntimeError(
            "House Founders dynasty_on_actions.txt now differs from AGOT "
            "outside on_dynasty_created"
        )

    agot_naming_branch = """\t\telse_if = {
\t\t\tlimit = {
\t\t\t\tdynast = {
\t\t\t\t\tculture = {
\t\t\t\t\t\tOR = {
\t\t\t\t\t\t\thas_cultural_pillar = heritage_andal
\t\t\t\t\t\t\thas_cultural_pillar = heritage_first_man
\t\t\t\t\t\t\thas_cultural_pillar = heritage_ironman
\t\t\t\t\t\t\thas_cultural_pillar = heritage_rhoynar
\t\t\t\t\t\t}
\t\t\t\t\t\tagot_is_wildling_culture = no
\t\t\t\t\t}
\t\t\t\t\ttrigger_if = {
\t\t\t\t\t\tlimit = { is_landed = yes }
\t\t\t\t\t\tcapital_province ?= { geographical_region = world_westeros_seven_kingdoms }
\t\t\t\t\t}
\t\t\t\t\ttrigger_else_if = {
\t\t\t\t\t\tlimit = {
\t\t\t\t\t\t\texists = liege_or_court_owner
\t\t\t\t\t\t\tliege_or_court_owner.capital_province ?= { geographical_region = world_westeros_seven_kingdoms }
\t\t\t\t\t\t}
\t\t\t\t\t}
\t\t\t\t\ttrigger_else = {
\t\t\t\t\t\tlimit = {
\t\t\t\t\t\t\tlocation ?= { geographical_region = world_westeros_seven_kingdoms }
\t\t\t\t\t\t}
\t\t\t\t\t}
\t\t\t\t}
\t\t\t}
\t\t\tdynast = { agot_generate_westerosi_dynasty_name_effect = yes }
\t\t}
"""
    house_founders_naming_branch = """\t\telse_if = {
\t\t\tlimit = {
\t\t\t\tdynast = {
\t\t\t\t\tis_human = yes
\t\t\t\t}
\t\t\t}
\t\t\tdynast = { trigger_event = agot_hf_new_house_name_generation_events.0002 }
\t\t}
"""
    rebased = replace_exact(
        agot_source,
        agot_naming_branch,
        house_founders_naming_branch,
        expected=1,
        label="House Founders human dynasty-name event",
    )

    dynasty_head = assert_source_block_hash(
        rebased,
        "on_became_dynasty_head",
        "b61538aa1cb1d1bf7f8ec3a8ed19913fbcbd0f485e9f40cb70e24b7d3c50ce04",
        label="AGOT dynasty-head on-action",
    )
    deferred_dynasty_head = """on_became_dynasty_head = {
\tevents = {
\t\tdelay = { days = 1 }
\t\tagot_playset_runtime.0001
\t}
}"""
    rebased = replace_exact(
        rebased,
        dynasty_head,
        deferred_dynasty_head,
        expected=1,
        label="deferred dynasty-head trait cleanup",
    )
    write_text(
        inputs.OUTPUT,
        relative,
        "# Runtime rebase: preserve House Founders naming and avoid dynasty-head "
        "re-entrancy.\n\n" + rebased,
    )
    write_text(
        inputs.OUTPUT,
        "events/agot_playset_runtime_events.txt",
        """namespace = agot_playset_runtime

# Run outside the code-driven dynasty-head transition. The synchronous effect
# chain, including an empty effect block, produces a repeatable CK3 1.19 SIGSEGV.
agot_playset_runtime.0001 = {
\thidden = yes
\ttrigger = {
\t\tOR = {
\t\t\thas_trait = denounced
\t\t\thas_trait = disinherited
\t\t}
\t}
\timmediate = {
\t\tif = {
\t\t\tlimit = { has_trait = denounced }
\t\t\tremove_trait = denounced
\t\t}
\t\tif = {
\t\t\tlimit = { has_trait = disinherited }
\t\t\tremove_trait = disinherited
\t\t}
\t}
}
""",
    )


def generate_suggest_dragon_bonding(inputs: RunInputs) -> None:
    relative = (
        "common/character_interactions/00_agot_suggest_dragon_bonding_interaction.txt"
    )
    text = read_text(inputs.WORKSHOP / "3324579171" / relative)

    marker = "        # Check if the recipient meets all conditions"
    before, separator, after = text.partition(marker)
    if not separator:
        raise RuntimeError(
            "AGOT Suggest Dragon Bonding: recipient-condition marker missing"
        )
    before = replace_exact(
        before,
        """every_courtier = {
                                    limit = {
                                        has_trait = dragon
                                        is_alive = yes
                                        any_relation = {
                                            type = agot_dragon
                                            count = 0
                                        }
                                    }
                                }""",
        """any_courtier = {
                                    has_trait = dragon
                                    is_alive = yes
                                    any_relation = {
                                        type = agot_dragon
                                        count = 0
                                    }
                                }""",
        expected=1,
        label="Suggest Dragon Bonding trigger-context courtier iterator",
    )
    before = replace_exact(
        before,
        "every_vassal = {",
        "any_vassal = {",
        expected=10,
        label="Suggest Dragon Bonding trigger-context vassal iterators",
    )
    text = before + separator + after

    text = replace_exact(
        text,
        "            is_busy_in_events_localised = yes",
        "            is_available = yes",
        expected=1,
        label="Suggest Dragon Bonding current availability trigger",
    )
    text = replace_exact(
        text,
        """			target = actor
			value = scope:actor.diplomacy""",
        """			target = scope:actor
			value = diplomacy""",
        expected=1,
        label="Suggest Dragon Bonding diplomacy compare modifier",
    )
    text = replace_exact(
        text,
        """			add = intimidated_external_reason_value
            multiplier = 0.1""",
        """			add = {
				value = intimidated_external_reason_value
				multiply = 0.1
			}""",
        expected=1,
        label="Suggest Dragon Bonding intimidated-value scaling",
    )
    text = replace_exact(
        text,
        """			add = cowed_external_reason_value
            multiplier = 0.1""",
        """			add = {
				value = cowed_external_reason_value
				multiply = 0.1
			}""",
        expected=1,
        label="Suggest Dragon Bonding cowed-value scaling",
    )
    write_text(inputs.OUTPUT, relative, text)


def generate_agot_tour_events(inputs: RunInputs) -> None:
    relative = "events/activities/tour_activity/tour_phase_host_a_dinner.txt"
    text = read_text(inputs.WORKSHOP / "2962333032" / relative)
    text = replace_exact(
        text,
        """host_dinner_events.3050 = {
\ttype = activity_event
\ttitle = host_dinner_events.3050.title
\tdesc = host_dinner_events.3050.desc

\ttheme = host_dinner
\tleft_portrait = {
\t\tcharacter = root
\t\tanimation = rage
\t}
\tright_portrait = {
\t\tcharacter = scope:non_eater_scope
\t\tanimation = personality_zealous
\t}
\tcooldown = { years = 5 }
\ttrigger = {
\t\tinvolved_activity = {
\t\t\tany_attending_character = {
\t\t\t\tthis != scope:stop_host_scope
\t\t\t\tthis != scope:visiting_liege""",
        """host_dinner_events.3050 = {
\ttype = activity_event
\ttitle = host_dinner_events.3050.title
\tdesc = host_dinner_events.3050.desc

\ttheme = host_dinner
\tleft_portrait = {
\t\tcharacter = root
\t\tanimation = rage
\t}
\tright_portrait = {
\t\tcharacter = scope:non_eater_scope
\t\tanimation = personality_zealous
\t}
\tcooldown = { years = 5 }
\ttrigger = {
\t\texists = scope:stop_host_scope
\t\texists = scope:visiting_liege
\t\tinvolved_activity = {
\t\t\tany_attending_character = {
\t\t\t\tNOT = { scope:stop_host_scope ?= this }
\t\t\t\tNOT = { scope:visiting_liege ?= this }""",
        expected=1,
        label="AGOT host dinner 3050 saved-scope guard",
    )
    text = replace_exact(
        text,
        """host_dinner_events.3080 = {
\ttype = activity_event
\ttitle = host_dinner_events.3080.title
\tdesc = host_dinner_events.3080.desc

\ttheme = host_dinner
\tleft_portrait = {
\t\tcharacter = root
\t\tanimation = shock
\t}
\tright_portrait = {
\t\tcharacter = scope:choking_character_scope
\t\tanimation = sick
\t}
\t#cooldown = { years = 5 }

\ttrigger = {
\t\tlocation = {
\t\t\tany_character_in_location = {
\t\t\t\tis_available_ai_adult = yes
\t\t\t\tany_memory = {
\t\t\t\t\thas_memory_category = positive
\t\t\t\t}
\t\t\t\tthis != scope:stop_host_scope
\t\t\t\tthis != scope:visiting_liege""",
        """host_dinner_events.3080 = {
\ttype = activity_event
\ttitle = host_dinner_events.3080.title
\tdesc = host_dinner_events.3080.desc

\ttheme = host_dinner
\tleft_portrait = {
\t\tcharacter = root
\t\tanimation = shock
\t}
\tright_portrait = {
\t\tcharacter = scope:choking_character_scope
\t\tanimation = sick
\t}
\t#cooldown = { years = 5 }

\ttrigger = {
\t\texists = scope:stop_host_scope
\t\texists = scope:visiting_liege
\t\tlocation = {
\t\t\tany_character_in_location = {
\t\t\t\tis_available_ai_adult = yes
\t\t\t\tany_memory = {
\t\t\t\t\thas_memory_category = positive
\t\t\t\t}
\t\t\t\tNOT = { scope:stop_host_scope ?= this }
\t\t\t\tNOT = { scope:visiting_liege ?= this }""",
        expected=1,
        label="AGOT host dinner 3080 saved-scope guard",
    )
    write_text(inputs.OUTPUT, relative, text)

    relative = "events/activities/tour_activity/tour_general_events.txt"
    text = read_text(inputs.WORKSHOP / "3719888822" / relative)
    text = replace_exact(
        text,
        """	trigger = {
		is_available_travelling_adult = yes
		scope:stop_host_scope = { this != root }
		exists = scope:stop_host_scope
""",
        """	trigger = {
		exists = scope:stop_host_scope
		is_available_travelling_adult = yes
		scope:stop_host_scope = { this != root }
""",
        expected=1,
        label="LoV tour-general 3001 stop-host guard ordering",
    )
    write_text(inputs.OUTPUT, relative, text)

    relative = "events/activities/tour_activity/az_tour_events.txt"
    text = read_text(inputs.WORKSHOP / "2962333032" / relative)
    for event_id in ("az_tour.0002", "az_tour.0003", "az_tour.0004"):
        block = extract_top_level_block(text, event_id)
        guarded = replace_regex(
            block,
            (
                r"(?m)^    trigger = \{\n"
                r"(?=[ \t]*scope:stop_host_scope = \{)"
            ),
            ("    trigger = {\n        exists = scope:stop_host_scope\n"),
            expected=1,
            label=f"{event_id} stop-host trigger guard",
        )
        text = text.replace(block, guarded, 1)

    block = extract_top_level_block(text, "az_tour.0005")
    guarded = replace_exact(
        block,
        """    immediate = {
""",
        """    trigger = {
        exists = scope:stop_host_scope
    }

    immediate = {
""",
        expected=1,
        label="az_tour.0005 stop-host event gate",
    )
    text = text.replace(block, guarded, 1)
    write_text(inputs.OUTPUT, relative, text)


def generate_adventurers_beneficiary(inputs: RunInputs) -> None:
    relative = "common/character_interactions/adventurers_beneficiary_unselect.txt"
    text = read_text(inputs.WORKSHOP / "3349316031" / relative)
    text = replace_exact(
        text,
        """			NOT = { scope:recipient = scope:actor }
			scope:recipient = var:val_beneficiary""",
        """			NOT = { scope:recipient = scope:actor }
			has_variable = val_beneficiary
			scope:recipient = var:val_beneficiary""",
        expected=1,
        label="Adventurer's Beneficiary selected-character variable guard",
    )
    write_text(inputs.OUTPUT, relative, text)


def generate_all_men_must_serve(inputs: RunInputs) -> None:
    relative = "common/scripted_effects/00_ame_effects.txt"
    source = read_text(inputs.WORKSHOP / "3761342990" / relative)
    block = extract_top_level_block(source, "ame_charge_service_cost_effect")
    block = replace_exact(
        block,
        "add_gold = -75",
        "remove_short_term_gold = 75",
        expected=1,
        label="All Men Must Serve positive-value service-cost deduction",
    )
    write_text(
        inputs.OUTPUT,
        "common/scripted_effects/zz_ame_runtime_cost_effect.txt",
        (
            "# CK3 1.19 rejects negative add_gold values. Preserve the "
            "Workshop mod's 75-gold fee with the current deduction effect.\n"
            f"{block}\n"
        ),
    )


def generate_agot_citadel(inputs: RunInputs) -> None:
    relative = "common/scripted_effects/00_agot_citadel_effects.txt"
    source = read_text(inputs.WORKSHOP / "2962333032" / relative)
    block = extract_top_level_block(source, "agot_seed_maesters_effect")
    block = replace_exact(
        block,
        """		limit = {
			capital_county.title_province = { geographical_region = world_westeros_seven_kingdoms }""",
        """		limit = {
			exists = capital_county
			capital_county.title_province = { geographical_region = world_westeros_seven_kingdoms }""",
        expected=1,
        label="AGOT seed-maesters capital-county guard",
    )
    (inputs.OUTPUT / relative).unlink(missing_ok=True)
    write_text(
        inputs.OUTPUT,
        "common/scripted_effects/zz_agot_runtime_citadel_effects.txt",
        f"{block}\n",
    )


def generate_agot_starting_legitimacy(inputs: RunInputs) -> None:
    relative = (
        "common/on_action/agot_on_actions/agot_starting_legitimacy_on_actions.txt"
    )
    text = read_text(inputs.WORKSHOP / "2962333032" / relative)
    text = replace_exact(
        text,
        """					limit = {
						capital_province = { geographical_region = world_westeros_seven_kingdoms }""",
        """					limit = {
						exists = capital_province
						capital_province = { geographical_region = world_westeros_seven_kingdoms }""",
        expected=1,
        label="AGOT starting-legitimacy capital-province guard",
    )
    write_text(inputs.OUTPUT, relative, text)


def generate_vanilla_tour_pulse(inputs: RunInputs) -> None:
    relative = "common/scripted_effects/04_dlc_ep2_tour_effects.txt"
    source = read_text(game_root(inputs) / relative)
    block = extract_top_level_block(source, "tour_monthly_pulse_effect")
    marker = "\tscope:activity.var:stop_host = {"
    marker_index = block.find(marker)
    if marker_index < 0:
        raise RuntimeError("vanilla tour pulse: stop_host scope marker not found")
    if not block.endswith("\n}"):
        raise RuntimeError("vanilla tour pulse: unexpected block ending")
    head = block[:marker_index]
    guarded = block[marker_index:-2]
    indented = "".join(
        f"\t{line}" if line.strip() else line
        for line in guarded.splitlines(keepends=True)
    )
    block = (
        f"{head}\tif = {{\n"
        "\t\tlimit = { scope:activity = { exists = var:stop_host } }\n"
        f"{indented}\t}}\n"
        "}"
    )
    write_text(
        inputs.OUTPUT,
        "common/scripted_effects/zz_agot_runtime_tour_pulse_effect.txt",
        (
            "# Guard the vanilla tour pulse when MFA relays it before an "
            "itinerary stop exists.\n"
            f"{block}\n"
        ),
    )

    relative = "events/activities/tour_activity/tour_phase_cultural_festival.txt"
    text = read_text(inputs.WORKSHOP / "2962333032" / relative)
    text = replace_exact(
        text,
        """cultural_festival.4100 = { #Your courtier made a cultural faux pas
\ttype = activity_event
\ttitle = cultural_festival.4100.t
\tdesc = cultural_festival.4100.desc\t

\ttheme = cultural_festival

\tleft_portrait = {
\t\tcharacter = root
\t\tanimation = worry
\t}
\tright_portrait = {
\t\tcharacter = scope:offended_character_scope
\t\tanimation = shock
\t}
\tcenter_portrait = {
\t\tcharacter = scope:inconsiderate_character_scope
\t\tanimation = fear
\t}

\tcooldown = { years = 5 }

\ttrigger = {
\t\tOR = {""",
        """cultural_festival.4100 = { #Your courtier made a cultural faux pas
\ttype = activity_event
\ttitle = cultural_festival.4100.t
\tdesc = cultural_festival.4100.desc\t

\ttheme = cultural_festival

\tleft_portrait = {
\t\tcharacter = root
\t\tanimation = worry
\t}
\tright_portrait = {
\t\tcharacter = scope:offended_character_scope
\t\tanimation = shock
\t}
\tcenter_portrait = {
\t\tcharacter = scope:inconsiderate_character_scope
\t\tanimation = fear
\t}

\tcooldown = { years = 5 }

\ttrigger = {
\t\texists = scope:stop_host_scope
\t\texists = scope:visiting_liege
\t\tOR = {""",
        expected=1,
        label="AGOT cultural festival 4100 saved-scope gate",
    )
    text = replace_exact(
        text,
        "culture != scope:stop_host_scope.culture",
        "scope:stop_host_scope ?= { culture != prev.culture }",
        expected=1,
        label="AGOT cultural festival optional stop-host culture",
    )
    text = replace_exact(
        text,
        "culture != scope:visiting_liege.culture",
        "scope:visiting_liege ?= { culture != prev.culture }",
        expected=1,
        label="AGOT cultural festival optional visiting-liege culture",
    )
    write_text(inputs.OUTPUT, relative, text)
