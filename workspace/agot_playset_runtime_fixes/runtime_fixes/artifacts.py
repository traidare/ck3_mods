"""Runtime repairs for artifacts."""

from __future__ import annotations

import re

from gen.script import (
    balanced_brace_end,
    normalize_rebased_source,
    read_text,
    replace_regex,
    write_text,
)
from gen.text import replace_exact

from .common import extract_top_level_block, remove_if_block_for_artifact_modifier
from .context import RunInputs


def generate_artifact_manager_distribution_event(inputs: RunInputs) -> None:
    relative = "events/distribute_artifacts.txt"
    text = read_text(inputs.WORKSHOP / "2886417277" / relative)
    text = replace_exact(
        text,
        "small_stress_impact_loss",
        "minor_stress_impact_loss",
        expected=2,
        label="Artifact Manager current stress-impact values",
    )
    text = replace_exact(
        text,
        "highlight_portrait = r_dyny",
        "highlight_portrait = scope:r_dyny",
        expected=1,
        label="Artifact Manager family portrait scope",
    )
    write_text(inputs.OUTPUT, relative, text)


def generate_artifact_manager_scripted_guis(inputs: RunInputs) -> None:
    relative = "common/scripted_guis/am_status_events.txt"
    text = read_text(inputs.WORKSHOP / "2886417277" / relative)
    text = replace_exact(
        text,
        """AM_combine_artifacts_available = {
    AND = {
        has_game_rule = amx_direct_upgrade_artifacts_enabled
        employs_court_position = antiquarian_court_position
        court_position:antiquarian_court_position = { aptitude:antiquarian_court_position >= 4  }
    }
}

""",
        "",
        expected=1,
        label="Artifact Manager bare trigger in scripted-GUI file",
    )
    text = replace_exact(
        text,
        "	saved_scope = { target }",
        "	saved_scopes = { target }",
        expected=4,
        label="Artifact Manager scripted-GUI saved scopes",
    )
    text = replace_exact(
        text,
        "            AM_combine_artifacts_available = yes",
        """            has_game_rule = amx_direct_upgrade_artifacts_enabled
            employs_court_position = antiquarian_court_position
            court_position:antiquarian_court_position = {
                aptitude:antiquarian_court_position >= 4
            }""",
        expected=1,
        label="Artifact Manager direct-upgrade availability trigger",
    )
    text = replace_exact(
        text,
        "        global_var:exists = at_artifact_trade_loaded",
        "        exists = global_var:at_artifact_trade_loaded",
        expected=1,
        label="Artifact Manager optional integration variable",
    )
    unavailable_agot_modifiers = (
        *(f"artifact_prowess_{level}_modifier" for level in range(6, 11)),
        *(f"artifact_minor_prestige_{level}_modifier" for level in range(1, 8)),
        *(f"artifact_prestige_{level}_modifier" for level in range(1, 8)),
        *(f"artifact_monthly_merit_add_{level}_modifier" for level in range(1, 8)),
        *(f"artifact_montly_lifestyle_xp_{level}_modifier" for level in range(1, 4)),
        *(
            f"artifact_montly_{skill}_lifestyle_xp_{level}_modifier"
            for skill in ("diplomacy", "martial", "stewardship", "intrigue", "learning")
            for level in range(1, 4)
        ),
        *(
            "artifact_study_confucian_classics_scheme_phase_duration_add_"
            f"{level}_modifier"
            for level in range(1, 4)
        ),
        *(
            f"artifact_monthly_confucian_education_xp_{level}_modifier"
            for level in range(1, 3)
        ),
    )
    if len(unavailable_agot_modifiers) != 49:
        raise RuntimeError(
            "Artifact Manager AGOT modifier filter: expected 49 identifiers, "
            f"constructed {len(unavailable_agot_modifiers)}"
        )
    for modifier in unavailable_agot_modifiers:
        text = replace_regex(
            text,
            rf"(?m)^[ \t]*has_artifact_modifier = {modifier}\n",
            "",
            expected=1,
            label=f"Artifact Manager unavailable AGOT modifier {modifier}",
        )
    write_text(inputs.OUTPUT, relative, text)


def generate_artifact_manager_upgrade_guis(inputs: RunInputs) -> None:
    relative = "common/scripted_guis/am_upgrade_ops.txt"
    text = read_text(inputs.WORKSHOP / "2886417277" / relative)
    text = replace_exact(
        text,
        "remove_variable = var:AM_upgrade_op_selected_artifact",
        "remove_variable = AM_upgrade_op_selected_artifact",
        expected=1,
        label="Artifact Manager selected-upgrade variable removal",
    )
    text = replace_exact(
        text,
        "remove_variable = var:AM_upgrade_op_gold_cost",
        "remove_variable = AM_upgrade_op_gold_cost",
        expected=1,
        label="Artifact Manager upgrade-cost variable removal",
    )
    text = replace_exact(
        text,
        "add_artifact_modifier = artifact_prowess_11_modifier",
        "add_artifact_modifier = artifact_prowess_5_modifier",
        expected=12,
        label="Artifact Manager AGOT maximum prowess modifier",
    )
    unavailable_upgrade_sources = (
        *(f"artifact_prowess_{level}_modifier" for level in range(6, 11)),
        *(f"artifact_monthly_merit_add_{level}_modifier" for level in range(1, 8)),
        *(
            "artifact_study_confucian_classics_scheme_phase_duration_add_"
            f"{level}_modifier"
            for level in range(1, 4)
        ),
        *(
            f"artifact_monthly_confucian_education_xp_{level}_modifier"
            for level in range(1, 3)
        ),
    )
    for modifier in unavailable_upgrade_sources:
        text = remove_if_block_for_artifact_modifier(
            text, modifier, label="Artifact Manager unavailable AGOT artifact upgrade"
        )
    write_text(inputs.OUTPUT, relative, text)

    relative = "common/scripted_guis/am_artifacts_batch_ops.txt"
    text = read_text(inputs.WORKSHOP / "2886417277" / relative)
    text = replace_exact(
        text,
        "scope:artifact",
        "scope:this_artifact",
        expected=4,
        label="Artifact Manager batch-sale saved artifact scope",
    )
    text = replace_exact(
        text,
        """                    faith = {
                        has_doctrine = tenet_aniconism
                    }""",
        """                    root = {
                        faith = {
                            has_doctrine = tenet_aniconism
                        }
                    }""",
        expected=2,
        label="Artifact Manager batch-sale owner faith scope",
    )
    for scripted_gui in ("AM_repair_all_artifacts", "AM_repair_selected_artifacts"):
        block = extract_top_level_block(text, scripted_gui)
        repaired_block = replace_exact(
            block,
            "save_scope_as = this_artifact",
            "save_scope_as = this_artifact\n\t\t\tsave_scope_as = artifact",
            expected=1,
            label=(f"Artifact Manager {scripted_gui} repair-cost artifact scope"),
        )
        text = replace_exact(
            text,
            block,
            repaired_block,
            expected=1,
            label=f"Artifact Manager {scripted_gui} scripted GUI",
        )
    text = replace_exact(
        text,
        """            if = {
                exists = scope:gift_recipient
""",
        """            if = {
                limit = { exists = scope:gift_recipient }
""",
        expected=2,
        label="Artifact Manager optional giveaway recipient guard",
    )
    text = replace_exact(
        text,
        "                } else {",
        "                }\n                else = {",
        expected=1,
        label="Artifact Manager batch-combination else effect",
    )
    write_text(inputs.OUTPUT, relative, text)

    relative = "common/scripted_guis/distribute_artifacts.txt"
    text = read_text(inputs.WORKSHOP / "2886417277" / relative)
    text = replace_exact(
        text,
        "  saved_scope = {",
        "  saved_scopes = {",
        expected=1,
        label="Artifact Manager distribution saved scopes",
    )
    write_text(inputs.OUTPUT, relative, text)


def generate_agot_artifact_succession(inputs: RunInputs) -> None:
    relative = "events/artifacts/artifact_events.txt"
    source = read_text(inputs.WORKSHOP / "2962333032" / relative)
    block = extract_top_level_block(source, "artifact.0031")
    repaired_block = replace_exact(
        block,
        """				var:artifact_succession_title = { is_title_created = yes } #Does the title the artifact should follow exist?
				scope:old_owner = var:artifact_succession_title.previous_holder #Is the old owner of the artifact also the holder of the title the artifact should follow?""",
        """				var:artifact_succession_title = { is_title_created = yes } #Does the title the artifact should follow exist?
				exists = var:artifact_succession_title.previous_holder
				scope:old_owner = var:artifact_succession_title.previous_holder #Is the old owner of the artifact also the holder of the title the artifact should follow?""",
        expected=1,
        label="AGOT artifact succession previous-holder guard",
    )
    source = replace_exact(
        source,
        block,
        repaired_block,
        expected=1,
        label="AGOT artifact succession in-place replacement",
    )
    source = normalize_rebased_source(source)
    (inputs.OUTPUT / "events/artifacts/zz_agot_runtime_artifact_events.txt").unlink(
        missing_ok=True
    )
    write_text(inputs.OUTPUT, relative, source)


def generate_agot_artifact_feature_owner_guards(inputs: RunInputs) -> None:
    relative = "common/scripted_triggers/00_artifact_triggers.txt"
    source = read_text(inputs.WORKSHOP / "2962333032" / relative)
    trigger_names = (
        "artifact_feature_pattern_wolf_trigger",
        "artifact_feature_pattern_animals_trigger",
        "artifact_feature_pattern_local_animal_trigger",
        "artifact_feature_pattern_beasts_trigger",
        "artifact_feature_pattern_bird_trigger",
        "artifact_feature_pattern_war_god_trigger",
        "artifact_feature_pattern_religion_trigger",
        "artifact_feature_pattern_eschatology_trigger",
        "artifact_feature_pattern_religious_symbol_trigger",
        "artifact_feature_pattern_gibberish_trigger",
        "artifact_feature_pattern_culture_symbol_trigger",
        "artifact_feature_pattern_culture_style_trigger",
    )
    repaired_blocks: list[str] = []
    for trigger_name in trigger_names:
        block = extract_top_level_block(source, trigger_name)
        owner_match = re.search(r"(?m)^\tscope:owner\s*=\s*\{", block)
        if not owner_match:
            raise RuntimeError(f"{trigger_name}: expected direct owner-scope condition")
        owner_open = block.index("{", owner_match.start())
        owner_end = balanced_brace_end(block, owner_open)
        owner_block = block[owner_match.start() : owner_end + 1]
        indented_owner = "\n".join(f"\t{line}" for line in owner_block.splitlines())
        guarded_owner = (
            "\t# Artifact generation can evaluate feature triggers before an "
            "owner is assigned.\n"
            "\ttrigger_if = {\n"
            "\t\tlimit = { exists = scope:owner }\n"
            f"{indented_owner}\n"
            "\t}"
        )
        block = block[: owner_match.start()] + guarded_owner + block[owner_end + 1 :]
        repaired_blocks.append(block)

    write_text(
        inputs.OUTPUT,
        ("common/scripted_triggers/zz_agot_runtime_artifact_owner_triggers.txt"),
        (
            "# Current AGOT pattern triggers assume an artifact owner already "
            "exists.\n"
            "# These narrow later definitions preserve their logic while "
            "making that scope optional.\n\n" + "\n\n".join(repaired_blocks) + "\n"
        ),
    )


def generate_agot_wall_banner_capital_fallback(inputs: RunInputs) -> None:
    relative = "common/scripted_effects/01_ep1_court_artifact_creation_effects.txt"
    source = read_text(inputs.WORKSHOP / "2962333032" / relative)
    block = extract_top_level_block(source, "create_artifact_wall_banner_effect")
    block = replace_exact(
        block,
        """\t$OWNER$ = { save_scope_as = owner }
\t$CREATOR$ = { save_scope_as = creator }
\t$TARGET$ = { save_scope_as = target } #Can be a title, a house or a dynasty

\t#This effect can be used to generate banners""",
        """\t$OWNER$ = { save_scope_as = owner }
\t$CREATOR$ = { save_scope_as = creator }
\t$TARGET$ = { save_scope_as = target } #Can be a title, a house or a dynasty

\t# Startup banner history requires a capital province. If a malformed or
\t# titular royal-court owner has none, use the existing created-banner branch
\t# instead; it still creates and grants the banner without an invalid location.
\t$OWNER$ = {
\t\tif = {
\t\t\tlimit = {
\t\t\t\thas_variable = startup_banner
\t\t\t\tNOT = { exists = capital_province }
\t\t\t}
\t\t\tremove_variable = startup_banner
\t\t}
\t}

\t#This effect can be used to generate banners""",
        expected=1,
        label="AGOT wall-banner missing-capital startup fallback",
    )
    write_text(
        inputs.OUTPUT,
        "common/scripted_effects/zz_agot_runtime_wall_banner_effect.txt",
        f"{block}\n",
    )
