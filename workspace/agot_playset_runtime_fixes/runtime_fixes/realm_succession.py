"""Runtime repairs for realm succession."""

from __future__ import annotations

import hashlib
import re
import textwrap

from gen.script import normalize_rebased_source, read_text, replace_regex, write_text
from gen.text import replace_exact

from .common import assert_source_block_hash, extract_top_level_block, game_root
from .context import RunInputs


def generate_kurultai_succession_scope_repairs(inputs: RunInputs) -> None:
    """Repair the two invalid scopes reached by chaotic Kurultai succession."""
    source_relative = "common/scripted_effects/09_dlc_mpo_scripted_effects.txt"
    parent_sources = {
        "AGOT": read_text(inputs.WORKSHOP / "2962333032" / source_relative),
        "CK3": read_text(game_root(inputs) / source_relative),
    }
    expected_hashes = {
        "nomadic_heir_cleanup_realm_effect": (
            "5833144559ca644280803314b5874e04e397b6705bcc2af2539b201562d563bf"
        ),
        "nomadic_realm_split_effect": (
            "3dbe761f4557589422c44a5ef276549550a22a7d168bc736f20dee27b51423b6"
        ),
    }
    blocks: dict[str, str] = {}
    for effect, expected_hash in expected_hashes.items():
        for parent, source in parent_sources.items():
            block = extract_top_level_block(source, effect)
            actual_hash = hashlib.sha256(block.encode()).hexdigest()
            if actual_hash != expected_hash:
                raise RuntimeError(
                    f"{parent} Kurultai source changed: {effect} expected "
                    f"{expected_hash}, found {actual_hash}"
                )
            if parent == "AGOT":
                blocks[effect] = block

    cleanup = replace_exact(
        blocks["nomadic_heir_cleanup_realm_effect"],
        "\t\t\t\tscope:recipient = {\n\t\t\t\t\tchange_liege = {",
        "\t\t\t\tscope:inheritor_char = {\n\t\t\t\t\tchange_liege = {",
        expected=1,
        label="Kurultai inheritor liege scope",
    )
    if "scope:recipient = {" in cleanup:
        raise RuntimeError("Kurultai cleanup retained the missing recipient scope")

    realm_split = replace_exact(
        blocks["nomadic_realm_split_effect"],
        "\t\t\tif = {\n"
        "\t\t\t\tlimit = {\n"
        "\t\t\t\t\tNOT = {\n"
        "\t\t\t\t\t\tthis = scope:new_ruler_scope\n"
        "\t\t\t\t\t}\n"
        "\t\t\t\t\tholder = {\n",
        "\t\t\tif = {\n"
        "\t\t\t\tlimit = {\n"
        "\t\t\t\t\tNOT = {\n"
        "\t\t\t\t\t\tholder = scope:new_ruler_scope\n"
        "\t\t\t\t\t}\n"
        "\t\t\t\t\tholder = {\n",
        expected=1,
        label="Kurultai county-holder comparison scope",
    )
    repaired_holder_guard = (
        "\t\t\t\t\tNOT = {\n"
        "\t\t\t\t\t\tholder = scope:new_ruler_scope\n"
        "\t\t\t\t\t}\n"
        "\t\t\t\t\tholder = {\n"
    )
    if realm_split.count(repaired_holder_guard) != 1:
        raise RuntimeError("Kurultai split holder comparison repair changed")
    if realm_split.count("this = scope:new_ruler_scope") != 1:
        raise RuntimeError("Kurultai split valid holder-scope comparison changed")

    write_text(
        inputs.OUTPUT,
        "common/scripted_effects/zz_agot_playset_kurultai_succession_fixes.txt",
        (
            "# Generated narrow repairs for CK3 1.19 chaotic Kurultai succession.\n"
            "# Source: AGOT 0.4.40 / common/scripted_effects/"
            "09_dlc_mpo_scripted_effects.txt\n\n"
            f"{cleanup}\n\n{realm_split}\n"
        ),
    )


def generate_chaotic_kurultai_event_guard(inputs: RunInputs) -> None:
    """Avoid resolving the optional prior holder of a new nomadic title."""
    relative = "events/mpo_chaotic_kurultai_succession.txt"
    source = read_text(inputs.WORKSHOP / "2962333032" / relative)
    if source.count("namespace = mpo_chaotic_kurultai_succession") != 1:
        raise RuntimeError("AGOT chaotic Kurultai event namespace changed")
    assert_source_block_hash(
        source,
        "mpo_chaotic_kurultai_succession.0005",
        "a3c0e7f8f88cdd38164dfe3d919803b6001bd5b84a963c81fc7f9d1fa4d51615",
        label="AGOT chaotic Kurultai introduction event",
    )
    prior_holder_pattern = re.compile(
        r"(?m)^(?P<indent>\t+)primary_title\.previous_holder = \{\n"
        r"(?P=indent)\tif = \{\n"
        r"(?P=indent)\t\tlimit = \{\n"
        r"(?P=indent)\t\t\tis_alive = no\n"
        r"(?P=indent)\t\t\}\n"
        r"(?P=indent)\t\tsave_scope_as = dead_parent\n"
        r"(?P=indent)\t\}\n"
        r"(?P=indent)\}"
    )

    def guard_prior_holder(match: re.Match[str]) -> str:
        indent = match.group("indent")
        return (
            f"{indent}primary_title = {{\n"
            f"{indent}\tif = {{\n"
            f"{indent}\t\tlimit = {{ exists = previous_holder }}\n"
            f"{indent}\t\tprevious_holder = {{\n"
            f"{indent}\t\t\tif = {{\n"
            f"{indent}\t\t\t\tlimit = {{\n"
            f"{indent}\t\t\t\t\tis_alive = no\n"
            f"{indent}\t\t\t\t}}\n"
            f"{indent}\t\t\t\tsave_scope_as = dead_parent\n"
            f"{indent}\t\t\t}}\n"
            f"{indent}\t\t}}\n"
            f"{indent}\t}}\n"
            f"{indent}}}"
        )

    source, guards = prior_holder_pattern.subn(guard_prior_holder, source)
    if guards != 17:
        raise RuntimeError(
            "chaotic Kurultai prior-holder guard: expected 17 unsafe accesses, "
            f"repaired {guards}"
        )
    if "primary_title.previous_holder = {" in source:
        raise RuntimeError("chaotic Kurultai source retained an unguarded prior holder")
    repaired_event = extract_top_level_block(
        source, "mpo_chaotic_kurultai_succession.0005"
    )
    if "limit = { exists = previous_holder }" not in repaired_event:
        raise RuntimeError("chaotic Kurultai introduction event was not guarded")
    write_text(inputs.OUTPUT, relative, normalize_rebased_source(source))


def generate_essos_disabled_realm_cleanup(inputs: RunInputs) -> None:
    """Initialize disabled Essos Expanded realms directly as LoV wilderness."""
    realms = (
        "bloodless_men",
        "cannibal_sands",
        "hidden_sea",
        "ibben",
        "ifequevron",
        "lesser_moraq",
        "lorath",
        "mossovy",
        "naath",
        "norvos",
        "omber",
        "qohor",
        "sarnor",
        "sothoryos",
        "summer_isles",
        "thousand_islands",
        "ulthos",
        "upper_sarne_dothraki",
        "lower_sarne_dothraki",
        "great_grass_sea_dothraki",
        "bone_mountain_dothraki",
        "lhazar",
        "qarth",
        "golden_yi_ti",
        "jogos_nhai",
        "great_moraq",
        "leng",
    )
    game_rules = read_text(
        inputs.WORKSHOP / "3682802751/common/game_rules/01_essos_empire_game_rules.txt"
    )
    on_action = read_text(
        inputs.WORKSHOP / "3682802751/common/on_action/essos_game_start.txt"
    )
    family_effects = read_text(
        inputs.WORKSHOP / "3682802751/common/scripted_effects/essos_family_effects.txt"
    )
    agot_remove_realms = read_text(
        inputs.WORKSHOP
        / "2962333032/common/scripted_effects/00_agot_remove_realms_effects.txt"
    )
    lov_colonization = read_text(
        inputs.WORKSHOP
        / "3719888822/common/scripted_effects/00_agot_colonization_effects.txt"
    )
    assert_source_block_hash(
        on_action,
        "essos_generate_families",
        "b94b4bc55ecdf1890ec6667fe4366b38a5b6a6af8f9d4d941b5b9726df14d3f7",
        label="Essos Expanded startup family dispatcher",
    )
    assert_source_block_hash(
        family_effects,
        "essos_give_family_effect",
        "465c1415a8987439f6ce4d1ca9009710793299f5b2bf30301f6b5d34915e8345",
        label="Essos Expanded family effect",
    )
    assert_source_block_hash(
        agot_remove_realms,
        "agot_remove_realm_effect",
        "9168fb5f64500cb04f28a321ddec8c6f658cc459dca4cfb62c3217a361a67b3b",
        label="AGOT realm-removal effect",
    )
    assert_source_block_hash(
        lov_colonization,
        "make_settlement_county_wilderness",
        "4bac248019f401289eac2f39e1e10c5bcd7bd7142db32ef5744af82a9066580b",
        label="LoV wilderness conversion",
    )
    if on_action.count("essos_remove_realms = {") != 1:
        raise RuntimeError("Essos Expanded startup dispatcher changed")

    # Further East ships the last landed-titles file, so it defines which Essos
    # Expanded empires still exist. AGOT covers Lorath, Norvos, and Qohor
    # natively, and Further East drops their empires accordingly; keeping their
    # removal actions would dispatch game-start effects at undefined titles.
    landed_titles = read_text(
        inputs.WORKSHOP / "3768149491/common/landed_titles/01_landed_titles.txt"
    )
    retired = [
        realm
        for realm in realms
        if not re.search(rf"(?m)^\s*e_{re.escape(realm)}\s*=\s*{{", landed_titles)
    ]
    if len(retired) > len(realms) // 2:
        raise RuntimeError(
            "Further East defines almost no Essos Expanded empire; re-audit "
            "whether it still ships the effective landed titles"
        )
    for realm in retired:
        on_action = replace_exact(
            on_action,
            f"\t\tessos_remove_realm_{realm}\n",
            "",
            expected=1,
            label=f"retired Essos empire dispatch for {realm}",
        )
        on_action = replace_exact(
            on_action,
            extract_top_level_block(on_action, f"essos_remove_realm_{realm}") + "\n\n",
            "",
            expected=1,
            label=f"retired Essos empire removal action for {realm}",
        )
        on_action = replace_exact(
            on_action,
            f"\t\t\t\t\t\tprimary_title = title:e_{realm}\n",
            "",
            expected=1,
            label=f"retired Essos empire family filter for {realm}",
        )

    for realm in (realm for realm in realms if realm not in retired):
        rule = f"essos_empire_{realm}_disabled"
        root_title = f"title:e_{realm}"
        old_removal = f"agot_remove_realm_effect = {{ REALM = {root_title} }}"
        if game_rules.count(f"{rule} = {{") != 1:
            raise RuntimeError(f"Essos Expanded game rule changed: {rule}")
        if on_action.count(f"essos_remove_realm_{realm} = {{") != 1:
            raise RuntimeError(f"Essos Expanded removal action changed: {realm}")
        on_action = replace_exact(
            on_action,
            old_removal,
            (
                "agot_playset_make_disabled_essos_realm_wilderness = "
                f"{{ REALM = {root_title} }}"
            ),
            expected=1,
            label=f"Essos Expanded {realm} wilderness replacement",
        )

    on_action = replace_exact(
        on_action,
        "on_game_start = {\n\ton_actions = {\n\t\tessos_remove_realms\n"
        "\t\tessos_generate_families\n\t}\n}",
        "on_game_start = {\n\ton_actions = {\n\t\tessos_remove_realms\n\t}\n}\n"
        "\n# Families need final ruler capitals and LoV's wilderness state.\n"
        "on_game_start_after_lobby = {\n\ton_actions = {\n"
        "\t\tessos_generate_families\n\t}\n}",
        expected=1,
        label="Essos Expanded family-generation timing",
    )
    on_action = replace_exact(
        on_action,
        "# Each empire checks its game rule; if disabled, calls agot_remove_realm_effect.",
        "# Each empire checks its game rule; if disabled, initializes LoV wilderness.",
        expected=1,
        label="Essos Expanded direct-wilderness startup description",
    )
    on_action = replace_exact(
        on_action,
        "\t\t\t\tis_ruler = yes\n\t\t\t\tage >= 30",
        "\t\t\t\tis_ruler = yes\n\t\t\t\tis_landed = yes\n"
        "\t\t\t\texists = capital_province\n\t\t\t\texists = top_liege\n"
        "\t\t\t\tage >= 30",
        expected=1,
        label="Essos Expanded family-ruler location guards",
    )

    for descendant in ("essos_child_1", "essos_child_2", "essos_child_3"):
        family_effects = replace_exact(
            family_effects,
            f"LOCATION  = scope:{descendant}",
            "LOCATION  = scope:essos_gen_char",
            expected=1,
            label=f"Essos family {descendant} location",
        )
    family_block = extract_top_level_block(family_effects, "essos_give_family_effect")
    family_open = family_block.index("{")
    guarded_family_block = (
        "essos_give_family_effect = {\n"
        "\t# The dispatcher filters this too; the AGOT helper dereferences\n"
        "\t# $LOCATION$.location, so direct callers must satisfy this invariant.\n"
        "\tif = {\n\t\tlimit = {\n\t\t\tis_landed = yes\n"
        "\t\t\texists = capital_province\n\t\t}\n"
        + textwrap.indent(family_block[family_open + 1 : -1].strip(), "\t\t")
        + "\n\t}\n}"
    )
    family_effects = replace_exact(
        family_effects,
        family_block,
        guarded_family_block,
        expected=1,
        label="Essos family location guard wrapper",
    )

    effect_text = textwrap.dedent(
        """\
        # Disabled Essos realms must not be staged through AGOT's c_unknown or
        # Local_Rulers. Preserve AGOT's removal semantics while converting every
        # county through the effective LoV wilderness operation.
        agot_playset_make_disabled_essos_realm_wilderness = {
        \t$REALM$ = {
        \t\tsave_scope_as = agot_playset_disabled_essos_realm
        \t\t# Remove noble-family titles before the landed hierarchy disappears.
        \t\tevery_in_de_jure_hierarchy = {
        \t\t\tlimit = { exists = holder tier >= tier_duchy }
        \t\t\tholder = {
        \t\t\t\tevery_held_title = {
        \t\t\t\t\tlimit = { is_noble_family_title = yes }
        \t\t\t\t\tholder = {
        \t\t\t\t\t\tif = {
        \t\t\t\t\t\t\tlimit = { is_landed = no }
        \t\t\t\t\t\t\tevery_courtier_or_guest = {
        \t\t\t\t\t\t\t\tdeath = { death_reason = death_vanished }
        \t\t\t\t\t\t\t}
        \t\t\t\t\t\t}
        \t\t\t\t\t\tdestroy_title = prev
        \t\t\t\t\t}
        \t\t\t\t}
        \t\t\t\tevery_vassal = {
        \t\t\t\t\tevery_held_title = {
        \t\t\t\t\t\tlimit = { is_noble_family_title = yes }
        \t\t\t\t\t\tholder = {
        \t\t\t\t\t\t\tif = {
        \t\t\t\t\t\t\t\tlimit = { is_landed = no }
        \t\t\t\t\t\t\t\tevery_courtier_or_guest = {
        \t\t\t\t\t\t\t\t\tdeath = { death_reason = death_vanished }
        \t\t\t\t\t\t\t\t}
        \t\t\t\t\t\t\t}
        \t\t\t\t\t\t\tdestroy_title = prev
        \t\t\t\t\t\t}
        \t\t\t\t\t}
        \t\t\t\t}
        \t\t\t}
        \t\t}
        \t\t# Remove de-jure duchy-and-higher titles before county conversion.
        \t\tevery_in_de_jure_hierarchy = {
        \t\t\tlimit = { exists = holder tier >= tier_duchy }
        \t\t\tholder = { destroy_title = prev }
        \t\t}
        \t\t# Clean landless companies whose capital remains inside this realm.
        \t\tevery_ruler = {
        \t\t\tlimit = {
        \t\t\t\tOR = {
        \t\t\t\t\tis_landless_adventurer = yes
        \t\t\t\t\tprimary_title = { is_mercenary_company = yes }
        \t\t\t\t}
        \t\t\t\texists = capital_province
        \t\t\t\tcapital_province.county = {
        \t\t\t\t\tscope:agot_playset_disabled_essos_realm = {
        \t\t\t\t\t\tis_de_jure_liege_or_above_target = prev
        \t\t\t\t\t}
        \t\t\t\t}
        \t\t\t}
        \t\t\tevery_courtier_or_guest = {
        \t\t\t\tdeath = { death_reason = death_vanished }
        \t\t\t}
        \t\t\tdestroy_title = primary_title
        \t\t\tdeath = { death_reason = death_vanished }
        \t\t}
        \t\tevery_in_de_jure_hierarchy = {
        \t\t\tlimit = { tier = tier_county }
        \t\t\tevery_county_province = {
        \t\t\t\tagot_remove_realms_remove_special_buildings_effect = yes
        \t\t\t\tsave_scope_as = agot_playset_disabled_essos_pool_province
        \t\t\t\tevery_pool_character = {
        \t\t\t\t\tprovince = scope:agot_playset_disabled_essos_pool_province
        \t\t\t\t\tdeath = { death_reason = death_vanished }
        \t\t\t\t}
        \t\t\t}
        \t\t\tif = {
        \t\t\t\tlimit = { exists = holder }
        \t\t\t\tholder = {
        \t\t\t\t\tsave_scope_as = agot_playset_disabled_essos_old_holder
        \t\t\t\t\tevery_courtier_or_guest = {
        \t\t\t\t\t\tdeath = { death_reason = death_vanished }
        \t\t\t\t\t}
        \t\t\t\t}
        \t\t\t\tmake_settlement_county_wilderness = { COUNTY = this }
        \t\t\t\tscope:agot_playset_disabled_essos_old_holder = {
        \t\t\t\t\tif = {
        \t\t\t\t\t\tlimit = { is_ruler = no }
        \t\t\t\t\t\tdeath = { death_reason = death_vanished }
        \t\t\t\t\t}
        \t\t\t\t}
        \t\t\t}
        \t\t\telse = {
        \t\t\t\tmake_settlement_county_wilderness = { COUNTY = this }
        \t\t\t}
        \t\t}
        \t\t# The de-jure iterator excludes the root empire title itself.
        \t\tif = {
        \t\t\tlimit = { exists = holder }
        \t\t\tholder = {
        \t\t\t\tdestroy_title = prev
        \t\t\t\tif = {
        \t\t\t\t\tlimit = { is_ruler = no }
        \t\t\t\t\tdeath = { death_reason = death_vanished }
        \t\t\t\t}
        \t\t\t}
        \t\t}
        \t}
        }
        """
    )
    write_text(
        inputs.OUTPUT,
        "common/on_action/essos_game_start.txt",
        normalize_rebased_source(on_action),
    )
    write_text(
        inputs.OUTPUT,
        "common/scripted_effects/essos_family_effects.txt",
        normalize_rebased_source(family_effects),
    )
    write_text(
        inputs.OUTPUT,
        "common/scripted_effects/zz_essos_disabled_realm_cleanup_effect.txt",
        effect_text,
    )
    for relative in (
        "common/decisions/zz_agot_playset_essos_migration_decision.txt",
        "common/scripted_triggers/zz_agot_playset_essos_migration_triggers.txt",
        "events/zz_agot_playset_essos_migration_events.txt",
        "localization/english/agot_playset_runtime_fixes_l_english.yml",
    ):
        (inputs.OUTPUT / relative).unlink(missing_ok=True)
    (inputs.OUTPUT / "common/on_action/zz_essos_disabled_realm_cleanup.txt").unlink(
        missing_ok=True
    )


def generate_lov_title_on_action_repairs(inputs: RunInputs) -> None:
    """Repair LoV title on-actions: yurt setup and noble-family title churn."""
    relative = "common/on_action/title_on_actions.txt"
    source = read_text(inputs.WORKSHOP / "3719888822" / relative)

    def yurt_main_block(external_count: int) -> str:
        external = (
            "\n".join(
                "\t\t\t\t\tadd_random_yurt_external_building_effect = yes"
                for _ in range(external_count)
            )
            + "\n"
            + "\n".join(
                "\t\t\t\t\tupgrade_random_yurt_external_building_effect = yes"
                for _ in range(external_count)
            )
        )
        return textwrap.indent(
            (
                "\t\t\t\ttitle_domicile = {\n"
                "\t\t\t\t\tif = {\n"
                "\t\t\t\t\t\tlimit = {\n"
                "\t\t\t\t\t\t\tNOT = { has_domicile_building = yurt_main_02 }\n"
                "\t\t\t\t\t\t}\n"
                "\t\t\t\t\t\tadd_domicile_building = yurt_main_02\n"
                "\t\t\t\t\t}\n"
                "\t\t\t\t\tif = {\n"
                "\t\t\t\t\t\tlimit = {\n"
                "\t\t\t\t\t\t\thas_domicile_building = yurt_main_02\n"
                "\t\t\t\t\t\t\towner ?= {\n"
                "\t\t\t\t\t\t\t\tOR = {\n"
                "\t\t\t\t\t\t\t\t\thas_realm_law = nomadic_authority_2\n"
                "\t\t\t\t\t\t\t\t\thas_realm_law = nomadic_authority_3\n"
                "\t\t\t\t\t\t\t\t\thas_realm_law = nomadic_authority_4\n"
                "\t\t\t\t\t\t\t\t\thas_realm_law = nomadic_authority_5\n"
                "\t\t\t\t\t\t\t\t}\n"
                "\t\t\t\t\t\t\t}\n"
                "\t\t\t\t\t\t\tNOT = { has_domicile_building = yurt_main_03 }\n"
                "\t\t\t\t\t\t}\n"
                "\t\t\t\t\t\tadd_domicile_building = yurt_main_03\n"
                "\t\t\t\t\t}\n"
                "\t\t\t\t\tif = {\n"
                "\t\t\t\t\t\tlimit = {\n"
                "\t\t\t\t\t\t\thas_domicile_building = yurt_main_03\n"
                "\t\t\t\t\t\t\towner ?= {\n"
                "\t\t\t\t\t\t\t\tOR = {\n"
                "\t\t\t\t\t\t\t\t\thas_realm_law = nomadic_authority_3\n"
                "\t\t\t\t\t\t\t\t\thas_realm_law = nomadic_authority_4\n"
                "\t\t\t\t\t\t\t\t\thas_realm_law = nomadic_authority_5\n"
                "\t\t\t\t\t\t\t\t}\n"
                "\t\t\t\t\t\t\t}\n"
                "\t\t\t\t\t\t\tNOT = { has_domicile_building = yurt_main_04 }\n"
                "\t\t\t\t\t\t}\n"
                "\t\t\t\t\t\tadd_domicile_building = yurt_main_04\n"
                "\t\t\t\t\t}\n"
                f"{external}\n"
                "\t\t\t\t}"
            ),
            "\t\t\t",
        )

    old_1300 = (
        "\t\t\t\ttitle_domicile = {\n"
        "\t\t\t\t\tadd_domicile_building = yurt_main_02\n"
        "\t\t\t\t\tadd_domicile_building = yurt_main_03\n"
        "\t\t\t\t\tadd_domicile_building = yurt_main_04\n"
        "\t\t\t\t\tadd_random_yurt_external_building_effect = yes\n"
        "\t\t\t\t\tadd_random_yurt_external_building_effect = yes\n"
        "\t\t\t\t\tadd_random_yurt_external_building_effect = yes\n"
        "\t\t\t\t\tadd_random_yurt_external_building_effect = yes\n"
        "\t\t\t\t\tupgrade_random_yurt_external_building_effect = yes\n"
        "\t\t\t\t\tupgrade_random_yurt_external_building_effect = yes\n"
        "\t\t\t\t\tupgrade_random_yurt_external_building_effect = yes\n"
        "\t\t\t\t\tupgrade_random_yurt_external_building_effect = yes\n"
        "\t\t\t\t}"
    )
    old_1300 = textwrap.indent(old_1300, "\t\t\t")
    old_1200 = (
        "\t\t\t\ttitle_domicile = {\n"
        "\t\t\t\t\tadd_domicile_building = yurt_main_02\n"
        "\t\t\t\t\tadd_domicile_building = yurt_main_03\n"
        "\t\t\t\t\tadd_domicile_building = yurt_main_04\n"
        "\t\t\t\t\tadd_random_yurt_external_building_effect = yes\n"
        "\t\t\t\t\tadd_random_yurt_external_building_effect = yes\n"
        "\t\t\t\t\tadd_random_yurt_external_building_effect = yes\n"
        "\t\t\t\t\tupgrade_random_yurt_external_building_effect = yes\n"
        "\t\t\t\t\tupgrade_random_yurt_external_building_effect = yes\n"
        "\t\t\t\t\tupgrade_random_yurt_external_building_effect = yes\n"
        "\t\t\t\t}"
    )
    old_1200 = textwrap.indent(old_1200, "\t\t\t")
    source = replace_exact(
        source,
        old_1300,
        yurt_main_block(4),
        expected=1,
        label="LoV nomad 1300 yurt setup",
    )
    source = replace_exact(
        source,
        old_1200,
        yurt_main_block(3),
        expected=1,
        label="LoV nomad 1200 yurt setup",
    )

    old_1100 = (
        "\t\t\t\ttitle_domicile = {\n"
        "\t\t\t\t\tadd_domicile_building = yurt_main_02\n"
        "\t\t\t\t\tif = {\n"
        "\t\t\t\t\t\tlimit = {\n"
        "\t\t\t\t\t\t\thas_domicile_building = yurt_main_02\n"
        "\t\t\t\t\t\t\towner ?= {\n"
        "\t\t\t\t\t\t\t\tOR = {\n"
        "\t\t\t\t\t\t\t\t\thas_realm_law = nomadic_authority_2\n"
        "\t\t\t\t\t\t\t\t\thas_realm_law = nomadic_authority_3\n"
        "\t\t\t\t\t\t\t\t\thas_realm_law = nomadic_authority_4\n"
        "\t\t\t\t\t\t\t\t\thas_realm_law = nomadic_authority_5\n"
        "\t\t\t\t\t\t\t\t}\n"
        "\t\t\t\t\t\t\t}\n"
        "\t\t\t\t\t\t}\n"
        "\t\t\t\t\t\tadd_domicile_building = yurt_main_03\n"
        "\t\t\t\t\t}\n"
        "\t\t\t\t\tadd_random_yurt_external_building_effect = yes\n"
        "\t\t\t\t\tadd_random_yurt_external_building_effect = yes\n"
        "\t\t\t\t\tupgrade_random_yurt_external_building_effect = yes\n"
        "\t\t\t\t\tupgrade_random_yurt_external_building_effect = yes\n"
        "\t\t\t\t}"
    )
    new_1100 = old_1100.replace(
        "\t\t\t\t\tadd_domicile_building = yurt_main_02\n",
        "\t\t\t\t\tif = {\n"
        "\t\t\t\t\t\tlimit = { NOT = { has_domicile_building = yurt_main_02 } }\n"
        "\t\t\t\t\t\tadd_domicile_building = yurt_main_02\n"
        "\t\t\t\t\t}\n",
        1,
    )
    new_1100 = new_1100.replace(
        "\t\t\t\t\t\t\t}\n"
        "\t\t\t\t\t\t}\n"
        "\t\t\t\t\t\tadd_domicile_building = yurt_main_03\n",
        "\t\t\t\t\t\t\t}\n"
        "\t\t\t\t\t\t\tNOT = { has_domicile_building = yurt_main_03 }\n"
        "\t\t\t\t\t\t}\n"
        "\t\t\t\t\t\tadd_domicile_building = yurt_main_03\n",
        1,
    )
    old_1100 = textwrap.indent(old_1100, "\t\t\t")
    new_1100 = textwrap.indent(new_1100, "\t\t\t")
    source = replace_exact(
        source, old_1100, new_1100, expected=1, label="LoV nomad 1100 yurt setup"
    )
    old_900 = (
        "\t\t\t\ttitle_domicile = {\n"
        "\t\t\t\t\tadd_domicile_building = yurt_main_02\n"
        "\t\t\t\t\tadd_random_yurt_external_building_effect = yes\n"
        "\t\t\t\t\tupgrade_random_yurt_external_building_effect = yes\n"
        "\t\t\t\t}"
    )
    new_900 = old_900.replace(
        "\t\t\t\t\tadd_domicile_building = yurt_main_02\n",
        "\t\t\t\t\tif = {\n"
        "\t\t\t\t\t\tlimit = { NOT = { has_domicile_building = yurt_main_02 } }\n"
        "\t\t\t\t\t\tadd_domicile_building = yurt_main_02\n"
        "\t\t\t\t\t}\n",
        1,
    )
    old_900 = textwrap.indent(old_900, "\t\t\t")
    new_900 = textwrap.indent(new_900, "\t\t\t")
    source = replace_exact(
        source, old_900, new_900, expected=1, label="LoV nomad 900 yurt setup"
    )

    # on_vassal_change creates noble-family titles synchronously. That call is
    # reached from inside an in-flight title/vassal change batch, and an AI
    # appointment cascade re-enters on_vassal_change many times per tick for the
    # same character, so each cascade nests an unbounded number of x_nf_* title
    # creations inside the batch that triggered them. Signature:
    #   "Executing change nested in 1 other change(s), originating from file:
    #    CreateNobleFamilyTitle line: 297"
    # Route both call sites through a request effect that rate-limits per
    # character and performs the creation on its own tick.
    source = replace_exact(
        source,
        "\t\t\tcreate_noble_family_effect = { GOVERNMENT_GIVER = this }\n"
        "\t\t\tdomicile ?= { set_up_domicile_estate_effect = yes }\n",
        "\t\t\tagot_playset_request_noble_family_title_effect = {\n"
        "\t\t\t\tEVENT = agot_playset_noble_family.1\n"
        "\t\t\t}\n",
        expected=1,
        label="LoV noble-family creation deferral (top-liege vassal)",
    )
    source = replace_exact(
        source,
        "\t\t\t\t\tcreate_noble_family_effect = { GOVERNMENT_GIVER = this }\n"
        "\t\t\t\t\tdomicile ?= { set_up_domicile_estate_effect = yes }\n",
        "\t\t\t\t\tagot_playset_request_noble_family_title_effect = {\n"
        "\t\t\t\t\t\tEVENT = agot_playset_noble_family.2\n"
        "\t\t\t\t\t}\n",
        expected=1,
        label="LoV noble-family creation deferral (independent ruler)",
    )
    write_text(inputs.OUTPUT, relative, source)

    request_effect = textwrap.dedent(
        """\
        # Deferred noble-family title creation.
        #
        # on_vassal_change fires inside an in-flight title/vassal change batch,
        # and an AI appointment cascade re-enters it repeatedly for the same
        # character within one tick. Creating the x_nf_* title there nests
        # landed-title creation inside that batch; if the created title does not
        # satisfy is_noble_family_title the caller's guard also never closes, so
        # every later vassal change creates another one.
        #
        # Record the request instead. The flag rate-limits a character to one
        # request per month no matter how large the cascade is, and the event
        # re-checks the caller's own guard on a later tick, outside the batch.
        agot_playset_request_noble_family_title_effect = {
        \tif = {
        \t\tlimit = {
        \t\t\tNOT = { has_character_flag = agot_playset_nf_title_requested }
        \t\t}
        \t\tadd_character_flag = {
        \t\t\tflag = agot_playset_nf_title_requested
        \t\t\tdays = 30
        \t\t}
        \t\ttrigger_event = {
        \t\t\tid = $EVENT$
        \t\t\tdays = 1
        \t\t}
        \t}
        }
        """
    )
    write_text(
        inputs.OUTPUT,
        "common/scripted_effects/zz_agot_playset_noble_family_effect.txt",
        request_effect,
    )

    events = textwrap.dedent(
        """\
        namespace = agot_playset_noble_family

        # Top-liege direct vassal. The trigger mirrors the on_vassal_change guard
        # this was deferred from, re-checked because a tick has passed.
        agot_playset_noble_family.1 = {
        \ttype = character_event
        \thidden = yes

        \ttrigger = {
        \t\tis_alive = yes
        \t\tgovernment_allows = administrative
        \t\tis_house_head = yes
        \t\ttrigger_if = {
        \t\t\tlimit = {
        \t\t\t\tgovernment_has_flag = government_has_county_tier_noble_families
        \t\t\t}
        \t\t\thighest_held_title_tier >= tier_county
        \t\t}
        \t\ttrigger_else = { highest_held_title_tier >= tier_duchy }
        \t\tliege = {
        \t\t\ttop_liege = this
        \t\t\tgovernment_allows = administrative
        \t\t}
        \t\tNOR = {
        \t\t\tany_held_title = { is_noble_family_title = yes }
        \t\t\thouse = {
        \t\t\t\tany_house_member = {
        \t\t\t\t\tany_held_title = { is_noble_family_title = yes }
        \t\t\t\t}
        \t\t\t}
        \t\t}
        \t}

        \timmediate = {
        \t\tremove_character_flag = agot_playset_nf_title_requested
        \t\tcreate_noble_family_effect = { GOVERNMENT_GIVER = this }
        \t\tdomicile ?= { set_up_domicile_estate_effect = yes }
        \t}
        }

        # Independent administrative ruler.
        agot_playset_noble_family.2 = {
        \ttype = character_event
        \thidden = yes

        \ttrigger = {
        \t\tis_alive = yes
        \t\tgovernment_has_flag = government_is_administrative
        \t\tliege = this
        \t\tadministrative_tier_allows_independence = yes
        \t\tNOT = { any_held_title = { is_noble_family_title = yes } }
        \t}

        \timmediate = {
        \t\tremove_character_flag = agot_playset_nf_title_requested
        \t\tcreate_noble_family_effect = { GOVERNMENT_GIVER = this }
        \t\tdomicile ?= { set_up_domicile_estate_effect = yes }
        \t}
        }
        """
    )
    write_text(
        inputs.OUTPUT,
        "events/zz_agot_playset_noble_family_events.txt",
        events,
    )


def generate_faction_legitimate_house_guards(inputs: RunInputs) -> None:
    """Guard AGOT claimant-faction legitimate-house comparisons."""
    relative = "common/scripted_modifiers/00_faction_modifiers.txt"
    source = read_text(inputs.WORKSHOP / "2962333032" / relative)
    source = replace_exact(
        source,
        "\t\t$FACTION_TITLE$ = {\n"
        "\t\t\ttitle_uses_legitimate_house_mechanic = yes\n"
        "\t\t\tNOT = { var:legitimate_house = $FACTION_TARGET$.house } # Not held by the legitimate house\n"
        "\t\t}",
        "\t\t$FACTION_TITLE$ = {\n"
        "\t\t\ttitle_uses_legitimate_house_mechanic = yes\n"
        "\t\t\ttitle_is_not_held_by_legitimate_house = yes\n"
        "\t\t}",
        expected=1,
        label="AGOT claimant faction illegitimate-house guard",
    )
    source = replace_exact(
        source,
        "\t\t$FACTION_TITLE$ = {\n"
        "\t\t\ttitle_uses_legitimate_house_mechanic = yes\n"
        "\t\t\tvar:legitimate_house = $FACTION_TARGET$.house # The title is held by the legitimate house\n"
        "\t\t}",
        "\t\t$FACTION_TITLE$ = {\n"
        "\t\t\ttitle_uses_legitimate_house_mechanic = yes\n"
        "\t\t\ttitle_is_held_by_legitimate_house = yes\n"
        "\t\t}",
        expected=1,
        label="AGOT claimant faction legitimate-house guard",
    )
    write_text(inputs.OUTPUT, relative, source)


def generate_dragon_wives_legitimate_house_guards(inputs: RunInputs) -> None:
    """Use AGOT's guarded legitimate-house trigger in Dragon Wives modifiers."""
    relative = "common/scripted_modifiers/00_marriage_scripted_modifiers.txt"
    source = read_text(inputs.WORKSHOP / "3541596590" / relative)
    source = replace_exact(
        source,
        "\t\t\tNOT = { var:legitimate_house = var:current_house }\n",
        "\t\t\ttitle_is_not_held_by_legitimate_house = yes\n",
        expected=2,
        label="Dragon Wives legitimate-house comparison",
    )
    write_text(inputs.OUTPUT, relative, source)


def generate_succession_crisis(inputs: RunInputs) -> None:
    relative = "events/sc_power_consolidation_event.txt"
    text = read_text(inputs.WORKSHOP / "3713902872" / relative)
    text = replace_exact(
        text,
        "NOT = { this = scope:crisis_special_character }",
        "NOT = { scope:crisis_special_character ?= this }",
        expected=1,
        label="Succession Crisis event optional special-character comparison",
    )
    write_text(inputs.OUTPUT, relative, text)

    relative = "common/casus_belli_types/succession_crisis_cb.txt"
    text = read_text(inputs.WORKSHOP / "3713902872" / relative)
    assert_source_block_hash(
        text,
        "succession_crisis_cb",
        "251ae06b03e802a3f496f7fb4015a165df73c3bbf468834a4b90c36c3ec970b6",
        label="Succession Crisis casus belli",
    )
    text = replace_exact(
        text,
        "scope:war = {",
        "scope:war ?= {",
        expected=5,
        label="Succession Crisis optional war scopes",
    )
    write_text(inputs.OUTPUT, relative, normalize_rebased_source(text))

    relative = "events/succession_crisis_misc.txt"
    source = read_text(inputs.WORKSHOP / "3713902872" / relative)
    event = assert_source_block_hash(
        source,
        "succession_crisis_misc.0012",
        "ee9e75518be8a4e8f2504f6fa100a6739cce1b02ae5f0957cfc77889cf18173c",
        label="Succession Crisis participant fixer",
    )
    repaired_event = replace_exact(
        event,
        "\t\t\t\tevery_vassal_or_below = {\n\t\t\t\t\tif = {",
        "\t\t\t\tevery_vassal_or_below = {\n"
        "\t\t\t\t\tsave_temporary_scope_as = succession_crisis_candidate\n"
        "\t\t\t\t\tif = {",
        expected=1,
        label="Succession Crisis participant candidate scope",
    )
    for side, opposite, add_effect in (
        ("defender", "attacker", "add_defender"),
        ("attacker", "defender", "add_attacker"),
    ):
        old = (
            "\t\t\t\t\t\t\tNOT = {\n"
            "\t\t\t\t\t\t\t\tscope:crisis_war = {\n"
            f"\t\t\t\t\t\t\t\t\tis_{side} = prev\n"
            "\t\t\t\t\t\t\t\t}\n"
            "\t\t\t\t\t\t\t}\n"
            "\t\t\t\t\t\t}\n"
            "\t\t\t\t\t\tif = {\n"
            "\t\t\t\t\t\t\tlimit = {\n"
            "\t\t\t\t\t\t\t\tscope:crisis_war = {\n"
            f"\t\t\t\t\t\t\t\t\tis_{opposite} = prev\n"
            "\t\t\t\t\t\t\t\t}\n"
            "\t\t\t\t\t\t\t}\n"
            "\t\t\t\t\t\t\tscope:crisis_war = {\n"
            "\t\t\t\t\t\t\t\tremove_participant = prev\n"
            "\t\t\t\t\t\t\t}\n"
            "\t\t\t\t\t\t}\n"
            "\t\t\t\t\t\tscope:crisis_war = {\n"
            f"\t\t\t\t\t\t\t{add_effect} = prev\n"
            "\t\t\t\t\t\t}\n"
        )
        replacement = (
            "\t\t\t\t\t\t\tNOT = {\n"
            "\t\t\t\t\t\t\t\tscope:crisis_war = {\n"
            f"\t\t\t\t\t\t\t\t\tis_{side} = scope:succession_crisis_candidate\n"
            "\t\t\t\t\t\t\t\t}\n"
            "\t\t\t\t\t\t\t}\n"
            "\t\t\t\t\t\t}\n"
            "\t\t\t\t\t\tif = {\n"
            "\t\t\t\t\t\t\tlimit = {\n"
            "\t\t\t\t\t\t\t\tscope:crisis_war = {\n"
            f"\t\t\t\t\t\t\t\t\tis_{opposite} = scope:succession_crisis_candidate\n"
            "\t\t\t\t\t\t\t\t}\n"
            "\t\t\t\t\t\t\t}\n"
            "\t\t\t\t\t\t\tscope:crisis_war = {\n"
            "\t\t\t\t\t\t\t\tremove_participant = scope:succession_crisis_candidate\n"
            "\t\t\t\t\t\t\t}\n"
            "\t\t\t\t\t\t}\n"
            "\t\t\t\t\t\tif = {\n"
            "\t\t\t\t\t\t\tlimit = {\n"
            "\t\t\t\t\t\t\t\tscope:crisis_war = {\n"
            "\t\t\t\t\t\t\t\t\tNOT = {\n"
            "\t\t\t\t\t\t\t\t\t\tany_war_participant = {\n"
            "\t\t\t\t\t\t\t\t\t\t\tthis = scope:succession_crisis_candidate\n"
            "\t\t\t\t\t\t\t\t\t\t}\n"
            "\t\t\t\t\t\t\t\t\t}\n"
            "\t\t\t\t\t\t\t\t\tNOT = {\n"
            "\t\t\t\t\t\t\t\t\t\tany_war_participant = {\n"
            "\t\t\t\t\t\t\t\t\t\t\tis_at_war_with = scope:succession_crisis_candidate\n"
            "\t\t\t\t\t\t\t\t\t\t}\n"
            "\t\t\t\t\t\t\t\t\t}\n"
            "\t\t\t\t\t\t\t\t}\n"
            "\t\t\t\t\t\t\t}\n"
            "\t\t\t\t\t\t\tscope:crisis_war = {\n"
            f"\t\t\t\t\t\t\t\t{add_effect} = scope:succession_crisis_candidate\n"
            "\t\t\t\t\t\t\t}\n"
            "\t\t\t\t\t\t}\n"
        )
        repaired_event = replace_exact(
            repaired_event,
            old,
            replacement,
            expected=1,
            label=f"Succession Crisis {add_effect} participant guard",
        )
    if (
        "add_defender = prev" in repaired_event
        or "add_attacker = prev" in repaired_event
    ):
        raise RuntimeError("Succession Crisis retained an unguarded participant join")
    source = replace_exact(
        source,
        event,
        repaired_event,
        expected=1,
        label="Succession Crisis participant event rebase",
    )
    write_text(inputs.OUTPUT, relative, normalize_rebased_source(source))


def generate_more_interactive_vassals_war_join_guards(inputs: RunInputs) -> None:
    """Refuse MIV war joins that conflict with any current participant."""
    relative = "events/interactive_events/interactive_events.txt"
    text = read_text(inputs.WORKSHOP / "2712590542" / relative)
    assert_source_block_hash(
        text,
        "interactive.0007",
        "9135f5b9aac37842b6e71281041130606bb9a348786e7b4fe6bccb90ad236ddb",
        label="More Interactive Vassals interactive.0007",
    )
    for joiner in ("scope:vassal", "scope:vassals_vassal"):
        pattern = (
            r"(?m)^(?P<indent>\t+)limit = \{\n"
            r"(?P=indent)\tprimary_attacker = \{\n"
            r"(?P=indent)\t\tNOT = \{\n"
            rf"(?P=indent)\t\t\tis_at_war_with = {re.escape(joiner)}\n"
            r"(?P=indent)\t\t\}\n"
            r"(?P=indent)\t\}\n"
            r"(?P=indent)\tprimary_defender = \{\n"
            r"(?P=indent)\t\tNOT = \{\n"
            rf"(?P=indent)\t\t\tis_at_war_with = {re.escape(joiner)}\n"
            r"(?P=indent)\t\t\}\n"
            r"(?P=indent)\t\}\n"
            r"(?P=indent)\}"
        )
        replacement = (
            "\\g<indent>limit = {\n"
            f"\\g<indent>\tNOT = {{ any_war_participant = {{ this = {joiner} }} }}\n"
            f"\\g<indent>\tNOT = {{\n"
            f"\\g<indent>\t\tany_war_participant = {{\n"
            f"\\g<indent>\t\t\tis_at_war_with = {joiner}\n"
            f"\\g<indent>\t\t}}\n"
            f"\\g<indent>\t}}\n"
            "\\g<indent>}"
        )
        text = replace_regex(
            text,
            pattern,
            replacement,
            expected=2,
            label=f"MIV all-participant war guard for {joiner}",
        )
    text = replace_exact(
        text,
        "vassal_contract_has_flag = has_warden_contract",
        "always = no # CK3 1.19 has no has_warden_contract definition",
        expected=3,
        label="MIV unavailable warden-contract branches",
    )
    write_text(inputs.OUTPUT, relative, normalize_rebased_source(text))


def generate_agot_war_value_guards(inputs: RunInputs) -> None:
    """Make AGOT's house-relation AI score tolerate house-less participants."""
    relative = "common/script_values/00_war_values.txt"
    source = read_text(inputs.WORKSHOP / "2962333032" / relative)
    assert_source_block_hash(
        source,
        "house_relation_ai_score_value",
        "5725a0fe1abb147a729742c45c6b164499cc519bff31eb3711cfe87754edce5d",
        label="AGOT house-relation AI score",
    )
    repaired = """house_relation_ai_score_value = {
\tvalue = 0
\tif = {
\t\tlimit = {
\t\t\texists = scope:attacker.house
\t\t\texists = scope:defender.house
\t\t}
\t\tscope:attacker.house = {
\t\t\tif = {
\t\t\t\tlimit = {
\t\t\t\t\tscope:defender.house = {
\t\t\t\t\t\tNOT = { this = scope:attacker.house }
\t\t\t\t\t\thas_house_relation_with = scope:attacker.house
\t\t\t\t\t}
\t\t\t\t}
\t\t\t\tevery_house_relation = {
\t\t\t\t\tlimit = {
\t\t\t\t\t\tany_relation_house = { this = scope:defender.house }
\t\t\t\t\t}
\t\t\t\t\tif = {
\t\t\t\t\t\tlimit = { has_house_relation_parameter = less_likely_war_target }
\t\t\t\t\t\tadd = house_relation_less_likely_war_target_value
\t\t\t\t\t}
\t\t\t\t\telse_if = {
\t\t\t\t\t\tlimit = { has_house_relation_parameter = more_likely_war_target }
\t\t\t\t\t\tadd = house_relation_more_likely_war_target_value
\t\t\t\t\t}
\t\t\t\t}
\t\t\t}
\t\t}
\t}
}
"""
    write_text(
        inputs.OUTPUT,
        "common/script_values/zz_agot_playset_war_value_guards.txt",
        repaired,
    )

    relative = "common/scripted_effects/sc_create_landless_adventurer_title_effect.txt"
    text = read_text(inputs.WORKSHOP / "3713902872" / relative)
    text = replace_exact(
        text,
        "\t\ttrigger_event = { id = misc.0001 days = 1 }\n",
        (
            "\t\t# AGOT disables misc.0001 and removes this vanilla "
            "rags-to-riches call.\n"
        ),
        expected=1,
        label="Succession Crisis AGOT-disabled misc.0001 call",
    )
    text = replace_exact(
        text,
        """				trigger = {
					NOT = {
						scope:new_landless_adventurer.culture = culture:kurdish
					}
				}
""",
        """				# AGOT has no Kurdish culture, so keep this title-name option
				# available exactly as AGOT does in the parent effect.
""",
        expected=1,
        label="Succession Crisis AGOT-disabled Kurdish culture gate",
    )
    write_text(inputs.OUTPUT, relative, text)

    relative = "common/on_action/sc_power_consolidation.txt"
    text = read_text(inputs.WORKSHOP / "3713902872" / relative)
    text = replace_exact(
        text,
        "NOT = { this = scope:crisis_special_character }",
        "NOT = { scope:crisis_special_character ?= this }",
        expected=1,
        label="Succession Crisis on-action optional comparisons",
    )
    write_text(inputs.OUTPUT, relative, text)


def generate_great_councils(inputs: RunInputs) -> None:
    relative = "events/zzz_Great_Councils_events.txt"
    text = read_text(inputs.WORKSHOP / "3621472324" / relative)
    text = replace_regex(
        text,
        r"(\bTRAIT\s*=\s*)([A-Za-z_][A-Za-z0-9_]*)",
        r"\1trait:\2",
        expected=56,
        label="AGOT Great Councils typed scripted-trigger trait parameters",
    )
    text = replace_exact(
        text,
        "has_trait = high_septon",
        "agot_is_high_septon = yes",
        expected=2,
        label="AGOT Great Councils current High Septon trigger",
    )
    write_text(inputs.OUTPUT, relative, text)


def generate_mpo_nomad_event_guards(inputs: RunInputs) -> None:
    """Guard MPO nomad events against AGOT's disabled Great Steppe situation."""
    relative = "events/dlc/mpo/mpo_nomads_flavour_events.txt"
    source = read_text(inputs.WORKSHOP / "2962333032" / relative)
    source = replace_exact(
        source,
        """\t\tmodifier = {
\t\t\tadd = 3
\t\t\tsituation:the_great_steppe = {
""",
        """\t\tmodifier = {
\t\t\tadd = 3
\t\t\tsituation:the_great_steppe ?= {
""",
        expected=1,
        label="AGOT MPO snow-wolf event optional Great Steppe situation",
    )
    source = replace_exact(
        source,
        """\t\tsituation:the_great_steppe = {
\t\t\tNOR = {
\t\t\t    any_situation_sub_region = {
""",
        """\t\tsituation:the_great_steppe ?= {
\t\t\tNOR = {
\t\t\t    any_situation_sub_region = {
""",
        expected=1,
        label="AGOT MPO low-herd event optional Great Steppe situation",
    )
    write_text(inputs.OUTPUT, relative, normalize_rebased_source(source))


def generate_voluntary_laamp_repairs(inputs: RunInputs) -> None:
    """Rebase the voluntary-adventurer decision and More Dragon Eggs event."""
    flag = "unlock_voluntary_laampdom_trait"

    trait_sources = (
        (
            "AGOT Nomadic Philosophy",
            inputs.WORKSHOP / "2962333032/common/traits/00_traits.txt",
            "nomadic_philosophy",
        ),
        (
            "Immersive Personalities gpt_tiger",
            inputs.WORKSHOP / "3596393244/common/traits/zz_gptev_traits.txt",
            "gpt_tiger",
        ),
        (
            "Immersive Personalities gpt_wolf",
            inputs.WORKSHOP / "3596393244/common/traits/zz_gptev_traits.txt",
            "gpt_wolf",
        ),
    )
    for label, path, trait in trait_sources:
        block = extract_top_level_block(read_text(path), trait)
        if f"flag = {flag}" not in block:
            raise RuntimeError(f"{label} no longer declares {flag}")

    decision_relative = "common/decisions/zz_agot_voluntary_laamp_decision.txt"
    decision_source = read_text(
        inputs.WORKSHOP
        / "2962333032/common/decisions/dlc_decisions/ep_3/06_ep3_laamp_decisions.txt"
    )
    decision = assert_source_block_hash(
        decision_source,
        "become_landless_adventurer_decision",
        "8028398f821a2de509efbd414a3e5a5c51f52888c5a1a86ddc7299b550df2436",
        label="AGOT voluntary-adventurer decision",
    )
    decision = replace_exact(
        decision,
        "has_trait = nomadic_philosophy",
        f"has_trait_with_flag = {flag}",
        expected=2,
        label="AGOT hard-coded voluntary-adventurer trait unlocks",
    )
    decision = replace_exact(
        decision,
        """\t\t\thas_character_modifier = tgp_gave_up_modifier
\t\t\tAND = {
""",
        """\t\t\thas_character_modifier = tgp_gave_up_modifier
\t\t\tagot_is_landless_pirate_character = yes
\t\t\tAND = {
""",
        expected=1,
        label="AGOT voluntary-adventurer visibility pirate unlock",
    )
    decision = replace_exact(
        decision,
        """\t\t\t\thas_character_modifier = tgp_gave_up_modifier
\t\t\t}
""",
        """\t\t\t\thas_character_modifier = tgp_gave_up_modifier
\t\t\t\tagot_is_landless_pirate_character = yes
\t\t\t}
""",
        expected=1,
        label="AGOT voluntary-adventurer validity pirate unlock",
    )
    write_text(
        inputs.OUTPUT,
        decision_relative,
        "# Runtime rebase: consume the generic trait flag and let stranded "
        "landless pirates choose the voluntary-adventurer route.\n" + decision,
    )

    event_relative = "events/dlc/ep3/ep3_laamp_events.txt"
    event_source = read_text(inputs.WORKSHOP / "3388366564" / event_relative)
    event = assert_source_block_hash(
        event_source,
        "ep3_laamps.0030",
        "6ae8981457953c35f6951818ab3041e9c9abbc78bcb301e75f537b76a88f0e24",
        label="More Dragon Eggs voluntary-adventurer event",
    )
    old_event_trigger = (
        "\ttrigger = { # MDE Modified\n"
        "\t\texists = scope:laamp_inheritor \n"
        "\t\tOR = {\n"
        "\t\t\thas_game_rule = can_children_be_landless_default\n"
        "\t\t\tAND = {\n"
        "\t\t\t\thas_game_rule = can_children_be_landless_not_dragonrider\n"
        "\t\t\t\troot = {\n"
        "\t\t\t\t\tNOT = { has_trait = dragonrider }\n"
        "\t\t\t\t}\n"
        "\t\t\t}\n"
        "\t\t\tAND = {\n"
        "\t\t\t\thas_game_rule = can_children_be_landless_not_targaryen\n"
        "\t\t\t\troot = {\n"
        "\t\t\t\t\tNOT = { dynasty = dynasty:dynn_Targaryen }\n"
        "\t\t\t\t}\n"
        "\t\t\t}\n"
        "\t\t}\n"
        "\t}\n"
    )
    repaired_event = replace_exact(
        event,
        old_event_trigger,
        """\ttrigger = { exists = scope:laamp_inheritor }
""",
        expected=1,
        label="More Dragon Eggs misplaced voluntary-event game-rule gate",
    )
    event_source = replace_exact(
        event_source,
        event,
        repaired_event,
        expected=1,
        label="More Dragon Eggs voluntary-adventurer event replacement",
    )
    write_text(
        inputs.OUTPUT,
        event_relative,
        event_source,
        preserve_trailing_whitespace=True,
        force_newline="\r\n",
    )
