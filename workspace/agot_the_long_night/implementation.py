#!/usr/bin/env python3
"""Build the standalone, fixed AGOT: The Long Night mod from pinned sources."""

from __future__ import annotations

import codecs
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from gen import GenerationContext
from gen.text import (
    assert_count,
    definition_span,
    direct_definition_names,
    matching_brace,
    nested_definition_span,
    newline_style,
    normalize_newlines,
    read_source,
    replace_exact,
    replace_regex,
    strip_trailing_whitespace,
    unique_marker,
)


@dataclass(frozen=True, slots=True)
class RunInputs:
    AGOT: Path
    CORE: Path
    SEASONS: Path
    LONG_NIGHT: Path
    PINNED_HASHES: dict[Path, str]


RELATIVE_ANIMATIONS = Path("gfx/portraits/portrait_animations/animations.txt")

SKIP = {
    "descriptor.mod",
    "common/scripted_rules/00_rules.txt",
    "common/decisions/zz_long_night_plus_native_overrides.txt",
    "common/scripted_triggers/00_long_night_plus_laamp_override.txt",
    "common/scripted_triggers/zz_long_night_plus_capture.txt",
    "common/scripted_triggers/zz_long_night_plus_commander.txt",
    "common/scripted_triggers/zz_long_night_plus_regency.txt",
    "gfx/models/portraits/decals/hair_aging_control.dds",
    "gfx/models/portraits/male_head/male_eyes_normal.dds",
    "gfx/portraits/skin_palette.dds",
}


def text(path: Path) -> str:
    return path.read_bytes().decode("utf-8-sig")


def encoded(value: str) -> bytes:
    return codecs.BOM_UTF8 + value.encode("utf-8")


def replace_definition(value: str, name: str, replacement: str) -> str:
    start, end = definition_span(value, name)
    return value[:start] + replacement + value[end:]


def replace_braced_block_after(
    text: str, marker: str, definition: str, replacement: str, label: str
) -> str:
    marker_at = unique_marker(text, marker, f"{label} marker")
    match = re.search(rf"(?m)^[ \t]*{re.escape(definition)}", text[marker_at:])
    if match is None:
        raise ValueError(f"{label}: definition not found after marker")
    start = marker_at + match.start()
    opening = text.find("{", start)
    end = matching_brace(text, opening) + 1
    return text[:start] + replacement + text[end:]


def wrap_special_genes(
    inputs: RunInputs,
    relative: str,
    category: str,
    *,
    remove_morph_metadata: int = 0,
    remove_draugr_attributes: bool = False,
) -> str:
    text = read_source(inputs.LONG_NIGHT / relative)
    text = replace_exact(
        text,
        f"{category} = {{",
        f"special_genes = {{\n\t{category} = {{",
        f"{relative}: wrap special genes",
    )
    if remove_morph_metadata:
        text = replace_regex(
            text,
            r"(?m)^\s*(?:inheritable|group)\s*=.*\r?\n",
            "",
            f"{relative}: remove persistent-gene metadata",
            remove_morph_metadata * 2,
        )
    if remove_draugr_attributes:
        text = replace_regex(
            text,
            r'(?m)^\s*setting\s*=\s*\{\s*attribute\s*=\s*"bs_draugr_(?:body|head)"[^\n]*\}\s*\r?\n',
            "",
            f"{relative}: removed draugr mesh attributes",
            4,
        )
    stripped = text.rstrip()
    if not stripped.endswith("}"):
        raise ValueError(f"{relative}: expected category closing brace")
    return stripped[:-1] + "\t}\n}\n"


def compat_dna(inputs: RunInputs) -> str:
    relative = "common/dna_data/agot_dna_a_long_night.txt"
    text = read_source(inputs.LONG_NIGHT / relative)
    indent = " \t\t"
    dragon_lines = [
        (
            "gene_dragon_primary_color_hue",
            '"dragon_primary_color_hue" 127 "dragon_primary_color_hue" 127',
        ),
        (
            "gene_dragon_primary_color_value",
            '"dragon_primary_color_value" 127 "dragon_primary_color_value" 127',
        ),
        (
            "gene_dragon_secondary_hue",
            '"dragon_secondary_hue" 127 "dragon_secondary_hue" 127',
        ),
        (
            "gene_dragon_secondary_value",
            '"dragon_secondary_value" 127 "dragon_secondary_value" 127',
        ),
        ("gene_dragon_wounded", '"dragon_scarred" 0 "dragon_scarred" 0'),
        (
            "gene_dragon_tertiary_hue",
            '"dragon_tertiary_hue" 127 "dragon_tertiary_hue" 127',
        ),
        (
            "gene_dragon_tertiary_value",
            '"dragon_tertiary_value" 127 "dragon_tertiary_value" 127',
        ),
        (
            "gene_dragon_body_shading",
            '"dragon_body_shading_lower_black" 0 "dragon_body_shading_lower_black" 0',
        ),
        (
            "gene_dragon_wings_shading",
            '"dragon_wings_shading_back_black" 0 "dragon_wings_shading_back_black" 0',
        ),
        (
            "gene_dragon_eye_color_hue",
            '"dragon_eye_color_hue" 127 "dragon_eye_color_hue" 127',
        ),
        (
            "gene_dragon_eye_color_value",
            '"dragon_eye_color_value" 127 "dragon_eye_color_value" 127',
        ),
        (
            "gene_dragon_horn_color_hue",
            '"dragon_horn_color_hue" 127 "dragon_horn_color_hue" 127',
        ),
        (
            "gene_dragon_horn_color_value",
            '"dragon_horn_color_value" 127 "dragon_horn_color_value" 127',
        ),
        (
            "gene_dragon_metallic_scales_strength",
            '"dragon_scales_metallic" 127 "dragon_scales_metallic" 127',
        ),
    ]
    neutral_shapes = [
        "gene_dragon_brow_width",
        "gene_dragon_cheek_width",
        "gene_dragon_chin_profile",
        "gene_dragon_crest_depth",
        "gene_dragon_head_roundness",
        "gene_dragon_horns_eyebrow_length",
        "gene_dragon_main_horn_shape",
        "gene_dragon_jaw_width",
        "gene_dragon_lower_jaw_height",
        "gene_dragon_lower_jaw_width",
        "gene_dragon_old_neck",
        "gene_dragon_outer_brow_height",
        "gene_dragon_snout_height",
        "gene_dragon_snout_length",
        "gene_dragon_snout_profile",
        "gene_dragon_snout_width",
        "gene_dragon_upper_jaw_width",
        "gene_dragon_back_spike_size",
        "gene_dragon_center_fin_size",
        "gene_dragon_horns_eyebrow",
        "gene_dragon_neck_spike_size",
        "gene_dragon_side_fin_size",
        "gene_dragon_snout_end_width",
        "gene_dragon_neck_length",
        "gene_dragon_tail_length",
    ]
    lines = [f"{indent}{name}={{ {value} }}" for name, value in dragon_lines]
    lines.extend(f'{indent}{name}={{ "" 127 "" 127 }}' for name in neutral_shapes)
    block = "\n".join(lines) + "\n"
    text = replace_regex(
        text,
        r"(?ms)^[ \t]*gene_dragon_skin_hue=.*?^[ \t]*gene_dragon_tail_length=.*?\r?\n",
        block,
        f"{relative}: current dragon DNA schema",
    )
    text = replace_regex(
        text,
        r"(?ms)^[ \t]*skin_color_hue_mhec=.*?^[ \t]*hair_color_value_mhec=.*?\r?\n",
        "",
        f"{relative}: remove obsolete MHEC DNA",
    )
    return text


def compat_maa(inputs: RunInputs) -> str:
    relative = "common/men_at_arms_types/long_night_maa_types.txt"
    text = read_source(inputs.LONG_NIGHT / relative)
    text = replace_exact(
        text,
        "type = Other_infantry",
        "type = heavy_infantry",
        f"{relative}: MAA category",
    )
    text = replace_regex(
        text,
        r"(?ms)^\s*can_recruit\s*=\s*\{.*?^\s*counters\s*=",
        """\tcan_recruit = {
		OR = {
			has_trait = other_trait
			AND = {
				dynasty = dynasty:dynn_Banefort
				any_secret = { secret_type = secret_witch }
			}
		}
	}

	counters =""",
        f"{relative}: recruitment trigger",
    )
    replacements = {
        "other_maa_recruitment_cost": "heavy_infantry_recruitment_cost",
        "other_maa_low_maint_cost": "heavy_infantry_low_maint_cost",
        "other_maa_high_maint_cost": "heavy_infantry_high_maint_cost",
        "ai_quality = { value = @cultural_maa_extra_ai_score }": "ai_quality = { value = 80 }",
        "icon = titan": "icon = heavy_infantry",
    }
    for old, new in replacements.items():
        text = replace_exact(text, old, new, f"{relative}: {old}")
    text = replace_regex(
        text, r"\r?\n\}\s*$", "\n", f"{relative}: obsolete extra closing brace"
    )
    return text


def compat_cb(inputs: RunInputs) -> str:
    relative = "common/casus_belli_types/00_long_night_cbs.txt"
    text = read_source(inputs.LONG_NIGHT / relative)
    for field in (
        "attacker_score_from_battle_scale",
        "defender_score_from_battle_scale",
    ):
        text = replace_regex(
            text, rf"(?m)^\s*{field}\s*=.*\r?\n", "", f"{relative}: remove {field}"
        )
    text = replace_regex(
        text,
        r"add_character_flag\s*=\s*long_night_cooldown\s+years\s*=\s*5",
        "add_character_flag = { flag = long_night_cooldown years = 5 }",
        f"{relative}: timed cooldown flags",
        2,
    )
    text = replace_regex(
        text,
        r"(?ms)^\s*ai_can_target_all_titles\s*=\s*\{.*?^\s*\}\s*\r?\n",
        "",
        f"{relative}: neighbor CB AI targeting",
        2,
    )
    text = replace_regex(
        text,
        r"(every_war_(?:attacker|defender)\s*=\s*\{\s*)(setup_invasion_cb\s*=)",
        r"\1save_temporary_scope_as = ln_war_participant\n\t\t\t\2",
        f"{relative}: name war participant scopes",
        3,
    )
    text = replace_exact(
        text,
        "defender = this",
        "defender = scope:ln_war_participant",
        f"{relative}: participant scope use",
        3,
    )
    text = replace_regex(
        text,
        r"scouring_cb\s*=\s*\{\r?\n\s*group\s*=\s*ambush",
        "scouring_cb = {\n\tgroup = ambush\n\ticon = invasion",
        f"{relative}: Scouring icon",
    )
    text = replace_regex(
        text,
        r"cost\s*=\s*\{\r?\n\}",
        "cost = {\n\t}",
        f"{relative}: empty cost indentation",
    )
    return text


def literal_regiment(type_name: str, size: int, indent: str) -> str:
    return (
        f"{indent}create_maa_regiment = {{ type = {type_name} size = {size} "
        "check_can_recruit = no }"
    )


def compat_scripted_effects(inputs: RunInputs) -> str:
    relative = "common/scripted_effects/agot_long_night_scripted_effects.txt"
    text = read_source(inputs.LONG_NIGHT / relative)
    replacements = {
        "title:c_the_frigid_rise.province": "title:c_the_frigid_rise.title_province",
        "faith = faith:old_gods_south": "faith = faith:old_gods_wnw",
        "culture = culture:dragon": "culture = culture:dragon_culture",
        "faith = faith:valyrian": "faith = faith:valyrian_pan_freehold",
        "set_faith = faith:cold_gods": "set_character_faith = faith:cold_gods",
        "NOT = { dynasty_house = house:house_theothers }": "NOT = { house = house:house_theothers }",
    }
    expected = {"culture = culture:dragon": 3, "faith = faith:valyrian": 3}
    for old, new in replacements.items():
        text = replace_exact(text, old, new, f"{relative}: {old}", expected.get(old, 1))
    text = replace_regex(
        text,
        r"(?m)^\s*make_trait_inactive\s*=\s*is_targaryen_3\s*\r?\n",
        "",
        f"{relative}: removed trait",
    )
    text = replace_regex(
        text,
        r"(?m)^\s*template\s*=\s*other_template\s*\r?\n",
        "",
        f"{relative}: removed empty template",
    )
    marker = "longnight_reform_nightswatch_effect = {"
    marker_at = unique_marker(text, marker, f"{relative}: NW reform")
    create_at = text.find("create_character = {", marker_at)
    insert_at = text.find("\n", create_at) + 1
    text = (
        text[:insert_at]
        + "\n\t\t\t\t\t\t\tlocation = title:c_castle_black.title_province\n"
        + text[insert_at:]
    )
    text = replace_exact(
        text,
        "get_title = title:h_the_others",
        "get_title = title:h_the_others\n\t\t\tchange_government = wight_government",
        f"{relative}: dead-realm government",
    )
    for trait in (
        "goutridden",
        "leper_1",
        "st_anthonys_fire",
        "great_spring_sickness",
        "winter_fever",
        "blood_cough",
        "bloody_flux",
        "shaking_sickness",
        "dancing_plague",
        "lover_pox",
    ):
        text = replace_regex(
            text,
            rf"(?m)^\s*if\s*=\s*\{{\s*limit\s*=\s*\{{\s*has_trait\s*=\s*{trait}\s*\}}\s*remove_trait\s*=\s*{trait}\s*\}}\s*\r?\n",
            "",
            f"{relative}: remove obsolete disease {trait}",
        )
    switch_marker = "trigger = scope:ln_maa_region"
    switch_start = text.rfind(
        "switch = {", 0, unique_marker(text, switch_marker, f"{relative}: regional MAA")
    )
    switch_end = matching_brace(text, text.find("{", switch_start)) + 1
    regions = {
        "north": "frog_spears",
        "riverlands": "river_bows",
        "vale": "finger_scouts",
        "crownlands": "royal_crossbowmen",
        "westerlands": "rain_bringers",
        "reach": "honeywine_quirrels",
        "stormlands": "marcher_longbowmen",
        "dorne": "sun_spears",
        "ironman": "ironborn_reavers",
        "wildling": "clan_raiders",
    }
    region_lines = ["switch = {", "\t\t\ttrigger = scope:ln_maa_region"]
    for region, maa in regions.items():
        region_lines.extend(
            [
                f"\t\t\tflag:{region} = {{",
                f"\t\t\t\tif = {{ limit = {{ scope:ln_camp_level >= 4 }} {literal_regiment(maa, 4, '')} }}",
                f"\t\t\t\telse_if = {{ limit = {{ scope:ln_camp_level >= 3 }} {literal_regiment(maa, 3, '')} }}",
                f"\t\t\t\telse_if = {{ limit = {{ scope:ln_camp_level >= 2 }} {literal_regiment(maa, 2, '')} }}",
                f"\t\t\t\telse = {{ {literal_regiment(maa, 1, '')} }}",
                "\t\t\t}",
            ]
        )
    region_lines.append("\t\t}")
    text = text[:switch_start] + "\n".join(region_lines) + text[switch_end:]
    return text


def compat_decisions(inputs: RunInputs) -> str:
    relative = "common/decisions/00_agot_long_night_decisions.txt"
    text = read_source(inputs.LONG_NIGHT / relative)
    text = replace_exact(
        text,
        "has_faith = faith:old_gods",
        "faith.religion = religion:the_pact_religion",
        f"{relative}: Pact religion",
    )
    text = replace_exact(
        text,
        "has_faith = faith:weirwood_of_the_seven",
        "has_faith = faith:fots_oldnew",
        f"{relative}: mixed faith",
    )
    text = replace_exact(
        text,
        "faith = faith:rhllor",
        "faith.religion = religion:the_rhllor_religion",
        f"{relative}: Rhllor religion",
    )
    text = replace_regex(
        text,
        r"(?ms)^\s*modifier\s*=\s*\{\s*add\s*=\s*50\s*faith\s*=\s*faith:red_god\s*\}\s*",
        "",
        f"{relative}: duplicate Rhllor modifier",
    )
    text = replace_exact(
        text,
        "faith = faith:trios",
        "faith = faith:fc_pan_tyrosh",
        f"{relative}: Trios faith",
    )
    text = replace_exact(
        text,
        "has_government = free_city_government",
        "government_has_flag = government_is_free_city",
        f"{relative}: free city government",
    )
    text = replace_regex(
        text,
        r"any_sub_realm_county\s*=\s*\{\s*geographical_region\s*=\s*([^\s}]+)\s*\}",
        r"any_sub_realm_county = { title_province = { geographical_region = \1 } }",
        f"{relative}: title/province region scopes",
        7,
    )
    text = replace_exact(
        text,
        "effect = {\r\n\t\tflee_noble_south_effect = yes",
        "effect = {\r\n\t\tsave_scope_as = host\r\n\t\tflee_noble_south_effect = yes",
        f"{relative}: refugee host scope",
    )
    return text


def compat_story(inputs: RunInputs) -> str:
    relative = "common/story_cycles/the_long_night.txt"
    text = read_source(inputs.LONG_NIGHT / relative)
    text = replace_exact(
        text,
        "add_culture_tradition = agot_tradition_wildling",
        "add_culture_tradition = tradition_agot_wildling",
        f"{relative}: wildling tradition",
    )
    text = replace_regex(
        text,
        r"(?m)^(\s*)add_trait\s*=\s*other_trait\s*$",
        r"\1add_trait = other_trait\n\1if = { limit = { is_landed = yes } change_government = wight_government }",
        f"{relative}: landed Other government",
        3,
    )
    text = replace_regex(
        text,
        r"effect\s*=\s*\{\r?\n(\s*)agot_long_night_wall_collapse_effect\s*=\s*yes\r?\n\s*\}",
        r"effect = {\n\1story_owner = { agot_long_night_wall_collapse_effect = yes }\n\t\t\t}",
        f"{relative}: Wall collapse character scope",
    )
    new_owner_effect = """effect = {
		story_owner = { save_scope_as = originalnightking }
		if = {
			limit = { title:h_the_others.holder = { has_trait = other_trait } }
			title:h_the_others.holder = {
				save_scope_as = newnightking
				add_trait = nightking
			}
		}
		else = {
			title:h_the_others.holder = { save_scope_as = displacednightking }
			random_ruler = {
				limit = { has_trait = other_trait NOT = { this = scope:originalnightking } }
				save_scope_as = newnightking
				add_trait = nightking
			}
			scope:displacednightking = {
				set_designated_heir = scope:newnightking
				depose = yes
			}
		}
		make_story_owner = scope:newnightking
	}"""
    text = replace_braced_block_after(
        text,
        "#### Fix the Story Owner",
        "effect = {",
        new_owner_effect,
        f"{relative}: story owner transfer",
    )
    return text


def compat_maintenance_events(inputs: RunInputs) -> str:
    relative = "events/others_events/others_maintenance_events.txt"
    text = read_source(inputs.LONG_NIGHT / relative)
    text = replace_regex(
        text,
        r"(?m)^\s*type\s*=\s*empty\s*\r?\n",
        "",
        f"{relative}: empty event type",
        2,
    )
    text = replace_exact(
        text, "faith:old_gods_btw", "faith:old_gods_btw_fnf", f"{relative}: BTW faith"
    )
    final_marker = "game_start_date < 8298.1.1"
    if text.count(final_marker) != 2:
        raise ValueError(f"{relative}: expected two dated scheduler markers")
    marker_at = text.rfind(final_marker)
    final_else_if = text.find("else_if = {", marker_at)
    if final_else_if < 0:
        raise ValueError(f"{relative}: final scheduler else_if not found")
    text = text[:final_else_if] + text[final_else_if:].replace(
        "else_if = {", "else = {", 1
    )
    return text


def compat_occupation_events(inputs: RunInputs) -> str:
    relative = "events/others_events/others_occupation_events.txt"
    text = read_source(inputs.LONG_NIGHT / relative)
    text = replace_exact(
        text,
        "agot_tradition_wildling",
        "tradition_agot_wildling",
        f"{relative}: wildling tradition",
    )
    text = replace_exact(
        text, "faith:old_gods_btw", "faith:old_gods_btw_fnf", f"{relative}: BTW faith"
    )
    text = replace_exact(
        text,
        "faith:old_gods_south",
        "faith:old_gods_wnw",
        f"{relative}: southern Old Gods",
    )
    return text


def compat_aftermath_event(inputs: RunInputs) -> str:
    relative = "events/ln_aftermath_events.txt"
    text = read_source(inputs.LONG_NIGHT / relative)
    old = """create_maa_regiment = {
					type = laamp_settler_maa
					size = ln_refugee_settler_size_value
					check_can_recruit = no
				}"""
    new = """if = { limit = { ln_refugee_settler_size_value >= 4 } create_maa_regiment = { type = laamp_settler_maa size = 4 check_can_recruit = no } }
				else_if = { limit = { ln_refugee_settler_size_value >= 3 } create_maa_regiment = { type = laamp_settler_maa size = 3 check_can_recruit = no } }
				else_if = { limit = { ln_refugee_settler_size_value >= 2 } create_maa_regiment = { type = laamp_settler_maa size = 2 check_can_recruit = no } }
				else = { create_maa_regiment = { type = laamp_settler_maa size = 1 check_can_recruit = no } }"""
    return replace_exact(text, old, new, f"{relative}: literal settler regiment size")


def compat_traits(inputs: RunInputs) -> str:
    relative = "common/traits/invasions_traits.txt"
    text = read_source(inputs.LONG_NIGHT / relative)
    text = replace_regex(
        text,
        r"(?m)^\s*(?:birth|random_creation)\s*=\s*0\s*\r?\n",
        "",
        f"{relative}: non-genetic fields",
        4,
    )
    text = replace_regex(
        text,
        r"(?ms)(^other_trait\s*=\s*\{.*?^\s*)blocks_from_claim_inheritance\s*=\s*yes",
        r"\1inheritance_blocker = all\n\tclaim_inheritance_blocker = all",
        f"{relative}: current inheritance blockers",
    )
    text = replace_regex(
        text,
        r"(?m)^\s*blocks_from_claim_inheritance\s*=\s*yes\s*\r?\n",
        "",
        f"{relative}: redundant wight blocker",
    )
    text = replace_regex(
        text,
        r"(?m)^\s*hostile_scheme_resistance_(?:mult|add)\s*=.*\r?\n",
        "",
        f"{relative}: removed scheme fields",
        2,
    )
    text = replace_exact(
        text,
        "enemy_personal_scheme_success_chance_add = -500",
        "enemy_personal_scheme_success_chance_add = -500\n\tenemy_hostile_scheme_success_chance_add = -200",
        f"{relative}: current hostile scheme defense",
    )
    text = replace_regex(
        text,
        r"(?m)^\s*can_create_activity\s*=\s*no\s*\r?\n",
        "",
        f"{relative}: removed activity modifier",
        2,
    )
    for trait in (
        "goutridden",
        "leper_1",
        "st_anthonys_fire",
        "great_spring_sickness",
        "winter_fever",
        "blood_cough",
        "bloody_flux",
        "shaking_sickness",
        "dancing_plague",
        "lover_pox",
    ):
        text = replace_regex(
            text,
            rf"(?m)^\s*{trait}\s*\r?\n",
            "",
            f"{relative}: obsolete trait {trait}",
            3,
        )
    return text


def compat_government(inputs: RunInputs) -> str:
    relative = "common/governments/zz_wight_government.txt"
    text = read_source(inputs.LONG_NIGHT / relative)
    return replace_exact(
        text,
        "flags = {\n\t\tgovernment_is_tribal",
        "flags = {\n\t\tgovernment_is_uninteractable\n\t\tgovernment_is_tribal",
        f"{relative}: uninteractable flag",
    )


def compat_rules(inputs: RunInputs) -> str:
    relative = "common/scripted_rules/00_rules.txt"
    text = read_source(inputs.AGOT / relative)
    long_night = read_source(inputs.LONG_NIGHT / relative)
    block_start = unique_marker(
        long_night, "\t\t#The Long Night+ Added", f"{relative}: Long Night player block"
    )
    block_end = long_night.index("\t\t#AGOT Added, NW Vassals", block_start)
    player_block = long_night[block_start:block_end]
    marker = "\t\t#AGOT Added, NW Vassals"
    marker_at = unique_marker(text, marker, f"{relative}: AGOT NW marker")
    text = text[:marker_at] + player_block + text[marker_at:]
    text = replace_regex(
        text,
        r"can_be_activity_guest\s*=\s*\{\r?\n",
        "can_be_activity_guest = {\n\tNOT = { has_trait = other_trait }\n",
        f"{relative}: Other activity guests",
    )
    text = replace_regex(
        text,
        r"(any_targeting_faction\s*=\s*\{\r?\n)\s*exists\s*=\s*yes\s*\r?\n",
        r"\1",
        f"{relative}: invalid iterator existence check",
    )
    if "agot_btw_merc_hiring_block" not in text:
        raise ValueError(f"{relative}: current AGOT mercenary guard is missing")
    return text


def compat_culture(inputs: RunInputs) -> str:
    relative = "common/culture/cultures/00_other_culture.txt"
    text = read_source(inputs.LONG_NIGHT / relative)
    return replace_exact(
        text, "0.79500034", "0.79500", f"{relative}: supported decimal precision", 2
    )


def compat_history(inputs: RunInputs) -> str:
    relative = "history/characters/othersinvasion_characters.txt"
    text = read_source(inputs.LONG_NIGHT / relative)
    text = replace_exact(
        text, "name = Other", "name = other_name", f"{relative}: localized name"
    )
    text = replace_exact(
        text,
        "house = house_theothers",
        "dynasty_house = house_theothers",
        f"{relative}: history house field",
    )
    for rank in ("novice", "apprentice", "journeyman"):
        perk = f"necromancy_{rank}_perk"
        text = replace_regex(
            text,
            rf"(?ms)^\s*if\s*=\s*\{{\s*limit\s*=\s*\{{\s*NOT\s*=\s*\{{\s*has_perk\s*=\s*{perk}\s*\}}\s*\}}\s*add_perk\s*=\s*{perk}\s*\}}[ \t]*\r?\n",
            "",
            f"{relative}: undefined {perk} block",
        )
    return text


def compat_armor_asset(inputs: RunInputs) -> str:
    relative = (
        "gfx/models/portraits/m_clothes/other_armor/male_clothes_others_armor.asset"
    )
    text = read_source(inputs.LONG_NIGHT / relative)
    first = 'name = "male_clothes_secular_other_war_02Shape"'
    positions = [match.start() for match in re.finditer(re.escape(first), text)]
    if len(positions) != 2:
        raise ValueError(
            f"{relative}: expected two armor meshsettings, found {len(positions)}"
        )
    second = positions[1]
    text = text[:second] + text[second:].replace(
        first, 'name = "male_clothes_secular_other_war_02Shape-001"', 1
    )
    text = replace_regex(
        text,
        r"(?m)^\s*attribute\s*=\s*\{\s*name\s*=\s*\"bs_body_(?:infant|fat|gaunt|muscular|old|dwarf)_1\".*\r?\n",
        "",
        f"{relative}: absent armor blend shapes",
        6,
    )
    return text


def compat_gui(inputs: RunInputs) -> str:
    relative = "gui/event_windows/ln_topleft_wall_event.gui"
    text = read_source(inputs.LONG_NIGHT / relative)
    text = replace_exact(
        text,
        "Select_CFixedPoint",
        "Select_int32",
        f"{relative}: integer width selectors",
        5,
    )
    text = replace_regex(
        text,
        r"'\(CFixedPoint\)(120|170|200|250|400)'",
        r"'(int32)\1'",
        f"{relative}: integer width casts",
        7,
    )
    types_at = unique_marker(text, "types Events {", f"{relative}: copied global types")
    return text[:types_at].rstrip() + "\n"


def compat_theothers_localization(inputs: RunInputs) -> str:
    relative = "localization/english/theothers_l_english.yml"
    text = read_source(inputs.LONG_NIGHT / relative)
    for key in ("dynn_others", "dynn_Others", "dynn_others_motto"):
        text = replace_regex(
            text, rf"(?m)^\s*{key}:.*\r?\n", "", f"{relative}: canonical {key}"
        )
    motto_matches = list(re.finditer(r"(?m)^\s*dynn_the_others_motto:.*\r?\n", text))
    if len(motto_matches) != 2:
        raise ValueError(
            f"{relative}: expected two dynn_the_others_motto definitions, "
            f"found {len(motto_matches)}"
        )
    duplicate = motto_matches[1]
    text = text[: duplicate.start()] + text[duplicate.end() :]
    for key in (
        "other_barony_male",
        "other_county_male",
        "other_duchy_male",
        "other_kingdom_male",
        "other_barony_female",
        "other_county_female",
        "other_duchy_female",
        "other_kingdom_female",
        "other_empire_male",
        "other_empire_female",
    ):
        matches = list(re.finditer(rf"(?m)^\s*{key}:.*\r?\n", text))
        if len(matches) != 2:
            raise ValueError(
                f"{relative}: expected two {key} definitions, found {len(matches)}"
            )
        text = text[: matches[0].start()] + text[matches[0].end() :]
    text = replace_regex(text, r"fearÃ[^\s]*fear", "fear—fear", f"{relative}: mojibake")
    return text


def compat_localization() -> str:
    return """l_english:
 other_cb_empire:0 "War for the Realm"
 SCOURING_CB:0 "Scouring"
 h_the_others_adj:0 "Other"
 wight_government_adjective:0 "Risen"
 wight_government_realm:0 "Army of the Dead"
 ln_wight_skin:0 "Wight Decay"
 ln_wight_gore:0 "Wight Wounds"
 other_maa_flavor:0 "The dead advance without fear, exhaustion, or mercy."
 others_weak_modifier:0 "Weak Army of the Dead"
 others_weak_modifier_desc:0 "The Army of the Dead has been weakened by the invasion rule."
 others_standard_modifier:0 "Army of the Dead"
 others_standard_modifier_desc:0 "The Army of the Dead has standard invasion strength."
 others_strong_modifier:0 "Strong Army of the Dead"
 others_strong_modifier_desc:0 "The Army of the Dead has increased invasion strength."
 others_insane_modifier:0 "Overwhelming Army of the Dead"
 others_insane_modifier_desc:0 "The Army of the Dead has overwhelming invasion strength."
 others_sword_description:0 "A blade of pale, enchanted ice carried by the Others."
 others_duchy_title:0 "Domain of the Others"
 scouring_army_name:0 "The Scouring Host"
 Skrothmasss:0 "Skrothmasss"
 Skroth:0 "Skroth"
 GAME_OVER_CANNOT_PLAY_WIGHT:0 "Wights are mindless servants of the Night King and cannot be played."
 grand_marshal:0 "Grand Marshal"
 menacing_wooden_sword:0 "Menacing Wooden Sword"
"""


def compat_simple_files(inputs: RunInputs) -> dict[str, str]:
    files: dict[str, str] = {}
    files["common/genes/zz_long_night_genes.txt"] = wrap_special_genes(
        inputs,
        "common/genes/zz_long_night_genes.txt",
        "morph_genes",
        remove_morph_metadata=18,
    )
    files["common/genes/zz_wight_genes.txt"] = wrap_special_genes(
        inputs,
        "common/genes/zz_wight_genes.txt",
        "morph_genes",
        remove_draugr_attributes=True,
    )
    files["common/genes/zz_wight_gore_genes.txt"] = wrap_special_genes(
        inputs, "common/genes/zz_wight_gore_genes.txt", "morph_genes"
    )
    for name in (
        "zz_others_genes_special_accessories_clothes.txt",
        "zz_others_genes_special_accessories_eyes.txt",
    ):
        relative = f"common/genes/{name}"
        files[relative] = wrap_special_genes(inputs, relative, "accessory_genes")
    files["common/dna_data/agot_dna_a_long_night.txt"] = compat_dna(inputs)
    files["common/men_at_arms_types/long_night_maa_types.txt"] = compat_maa(inputs)
    files["common/casus_belli_types/00_long_night_cbs.txt"] = compat_cb(inputs)
    files["common/scripted_effects/agot_long_night_scripted_effects.txt"] = (
        compat_scripted_effects(inputs)
    )
    files["common/decisions/00_agot_long_night_decisions.txt"] = compat_decisions(
        inputs
    )
    files["common/story_cycles/the_long_night.txt"] = compat_story(inputs)
    files["events/others_events/others_maintenance_events.txt"] = (
        compat_maintenance_events(inputs)
    )
    files["events/others_events/others_occupation_events.txt"] = (
        compat_occupation_events(inputs)
    )
    files["events/ln_aftermath_events.txt"] = compat_aftermath_event(inputs)
    other_events = "events/others_events/others_events.txt"
    files[other_events] = replace_regex(
        read_source(inputs.LONG_NIGHT / other_events),
        r"(?m)^\s*type\s*=\s*empty\s*\r?\n",
        "",
        f"{other_events}: empty event type",
    )
    modifier = "common/modifiers/zz_long_night_plus_modifiers.txt"
    files[modifier] = replace_exact(
        read_source(inputs.LONG_NIGHT / modifier),
        "travel_speed = 0.25",
        "character_travel_speed_mult = 0.25",
        f"{modifier}: character travel speed",
    )
    files["common/traits/invasions_traits.txt"] = compat_traits(inputs)
    files["common/governments/zz_wight_government.txt"] = compat_government(inputs)
    files["common/scripted_rules/00_rules.txt"] = compat_rules(inputs)
    files["common/culture/cultures/00_other_culture.txt"] = compat_culture(inputs)
    files["history/characters/othersinvasion_characters.txt"] = compat_history(inputs)
    files[
        "gfx/models/portraits/m_clothes/other_armor/male_clothes_others_armor.asset"
    ] = compat_armor_asset(inputs)
    portrait_modifiers = (
        "gfx/portraits/portrait_modifiers/ln_others_portrait_modifiers.txt"
    )
    files[portrait_modifiers] = read_source(inputs.LONG_NIGHT / portrait_modifiers)
    background_event = "events/others_events/others_events.txt"
    files[background_event] = replace_exact(
        files[background_event],
        "reference = agot_dragon_forest_clearing",
        "reference = wilderness_forest",
        f"{background_event}: current event background",
    )
    files["gui/event_windows/ln_topleft_wall_event.gui"] = compat_gui(inputs)
    coa = "common/coat_of_arms/coat_of_arms/ek2sauron_coa.txt"
    files[coa] = replace_regex(
        read_source(inputs.LONG_NIGHT / coa),
        r"(?m)^\s*custom\s*=\s*yes\s*\r?\n",
        "",
        f"{coa}: removed custom field",
    )
    names = "common/culture/name_lists/00_othernames.txt"
    files[names] = replace_regex(
        read_source(inputs.LONG_NIGHT / names),
        r"(?m)^(\s*)Other\s*$",
        r"\1other_name",
        f"{names}: localized Other names",
        2,
    )
    files["localization/english/theothers_l_english.yml"] = (
        compat_theothers_localization(inputs)
    )
    dynasty_loc = "localization/english/dynasties/otherdynasty_names_l_english.yml"
    files[dynasty_loc] = read_source(inputs.LONG_NIGHT / dynasty_loc)
    wall_loc = "localization/english/long_night_plus_wall_events_l_english.yml"
    files[wall_loc] = read_source(inputs.LONG_NIGHT / wall_loc)
    files["localization/english/agot_long_night_compatch_l_english.yml"] = (
        compat_localization()
    )
    return files


def core_animation(inputs: RunInputs) -> str:
    core = text(inputs.CORE / RELATIVE_ANIMATIONS)
    source = text(inputs.LONG_NIGHT / RELATIVE_ANIMATIONS)
    newline = newline_style(core)
    names = direct_definition_names(source, r"wight_pose_[A-Za-z0-9_]+")
    if len(names) != 5:
        raise ValueError(f"expected five Long Night poses, found {len(names)}")
    poses = "".join(
        source[s:e] for s, e in (nested_definition_span(source, n) for n in names)
    )
    poses = normalize_newlines(poses, newline)
    marker = f"\t\t#AGOT Added{newline}\t\thigh_septon = {{"
    unique_marker(core, marker, "Core high_septon pose")
    merged = core.replace(marker, poses + newline + marker, 1)
    assert_count(merged, r"wight_pose_[A-Za-z0-9_]+", 5, "Core/Long Night poses")
    assert_count(merged, "hold_bow_idle", 1, "Core bow pose")
    assert_count(merged, "hold_long_axe_idle", 1, "AGOT long-axe pose")
    return strip_trailing_whitespace(normalize_newlines(merged, "\n"))


def patch_seasons(inputs: RunInputs) -> str:
    value = text(inputs.SEASONS / "events/season_events.txt")
    start, end = definition_span(value, "season_events.002")
    block = value[start:end]
    immediate = re.search(r"(?m)^\s*immediate\s*=\s*\{", block)
    if immediate is None:
        raise ValueError("Seasons spring event has no immediate block")
    opening = block.find("{", immediate.start())
    closing = matching_brace(block, opening)
    original = block[opening + 1 : closing]
    replacement = (
        "immediate = {\n"
        "\t\tif = {\n"
        "\t\t\tlimit = { is_agot_long_night_active_trigger = yes }\n"
        "\t\t\ttrigger_event = { id = season_events.002 days = 90 }\n"
        "\t\t}\n"
        "\t\telse = {" + original + "\n\t\t}\n\t}"
    )
    block = block[: immediate.start()] + replacement + block[closing + 1 :]
    return value[:start] + block + value[end:]


def game_rules() -> str:
    return """agot_others_invasion_chance = {
\tcategories = { agot }
\tdefault = others_certain_invasion_chance
\tothers_certain_invasion_chance = { }
\tothers_near_certain_invasion_chance = { }
\tothers_even_odds_invasion_chance = { }
\tothers_remote_odds_invasion_chance = { }
\tothers_invasion_wont_happen = { }
}

agot_others_invasion_moment = {
\tcategories = { agot }
\tdefault = others_historical_invasion
\tothers_immediate_invasion = { }
\tothers_invasion_in_50_years = { }
\tothers_invasion_in_100_years = { }
\tothers_invasion_in_150_years = { }
\tothers_historical_invasion = { }
\tothers_full_random_invasion = { }
\tothers_manual_invasion = { }
}

agot_others_invasion_strength = {
\tcategories = { agot }
\tdefault = others_standard_invasion
\tothers_weak_invasion = { }
\tothers_standard_invasion = { }
\tothers_strong_invasion = { }
\tothers_insane_invasion = { }
}

agot_others_resolution = {
\tcategories = { agot }
\tdefault = others_war_resolution
\tothers_war_resolution = { }
}

agot_longnight_iron_throne_reformation = {
\tcategories = { agot }
\tdefault = longnight_iron_throne_reformation_on
\tlongnight_iron_throne_reformation_on = { }
\tlongnight_iron_throne_reformation_off = { }
}

agot_long_night_dragon = {
\tcategories = { agot }
\tdefault = agot_long_night_dragon_off
\tagot_long_night_dragon_off = { }
\tagot_long_night_dragon_on = { }
}

agot_others_cb_tier = {
\tcategories = { agot }
\tdefault = others_cb_kingdom
\tothers_cb_kingdom = { }
\tothers_cb_empire = { }
}
"""


def patch_maintenance(inputs: RunInputs) -> str:
    value = compat_maintenance_events(inputs)
    event = """others_maintenance.1 = {
\tscope = none
\thidden = yes
\timmediate = {
\t\tset_global_variable = { name = agot_long_night_enabled value = yes }
\t\tset_global_variable = { name = agot_long_night_eligible_year value = current_year }
\t\tif = {
\t\t\tlimit = { NOT = { has_dlc_feature = roads_to_power } }
\t\t\tset_global_variable = { name = agot_long_night_dependency_blocked value = yes }
\t\t\tevery_player = { trigger_event = agot_ln.1 }
\t\t}
\t\telse_if = { limit = { has_game_rule = others_invasion_in_50_years } change_global_variable = { name = agot_long_night_eligible_year add = 50 } }
\t\telse_if = { limit = { has_game_rule = others_invasion_in_100_years } change_global_variable = { name = agot_long_night_eligible_year add = 100 } }
\t\telse_if = { limit = { has_game_rule = others_invasion_in_150_years } change_global_variable = { name = agot_long_night_eligible_year add = 150 } }
\t\telse_if = {
\t\t\tlimit = { has_game_rule = others_historical_invasion current_year < 8298 }
\t\t\tset_global_variable = { name = agot_long_night_eligible_year value = 8298 }
\t\t}
\t\telse_if = {
\t\t\tlimit = { has_game_rule = others_full_random_invasion }
\t\t\trandom_list = {
\t\t\t\t20 = { }
\t\t\t\t20 = { change_global_variable = { name = agot_long_night_eligible_year add = 25 } }
\t\t\t\t20 = { change_global_variable = { name = agot_long_night_eligible_year add = 50 } }
\t\t\t\t20 = { change_global_variable = { name = agot_long_night_eligible_year add = 100 } }
\t\t\t\t20 = { change_global_variable = { name = agot_long_night_eligible_year add = 150 } }
\t\t\t}
\t\t}
\t\tif = {
\t\t\tlimit = {
\t\t\t\tNOT = { has_global_variable = agot_long_night_dependency_blocked }
\t\t\t\tNOT = { has_game_rule = others_invasion_wont_happen }
\t\t\t\tNOT = { has_game_rule = others_manual_invasion }
\t\t\t}
\t\t\ttrigger_event = { id = agot_ln.10 days = 1 }
\t\t}
\t}
}"""
    return replace_definition(value, "others_maintenance.1", event)


def army_block(stacks: int) -> str:
    return f"""spawn_army = {{
\t\t\tmen_at_arms = {{ type = other_maa stacks = {stacks} }}
\t\t\tname = wights
\t\t\tuses_supply = no
\t\t\tlocation = capital_province
\t\t}}"""


def patch_effects(inputs: RunInputs) -> str:
    value = compat_scripted_effects(inputs)
    first = value.find("spawn_army = {")
    if first < 0:
        raise ValueError("initial horde army not found")
    end = matching_brace(value, value.find("{", first)) + 1
    replacement = (
        "if = { limit = { has_game_rule = others_weak_invasion } "
        + army_block(100)
        + " }\n\t\telse_if = { limit = { has_game_rule = others_strong_invasion } "
        + army_block(350)
        + " }\n\t\telse_if = { limit = { has_game_rule = others_insane_invasion } "
        + army_block(500)
        + " }\n\t\telse = { "
        + army_block(200)
        + " }"
    )
    value = value[:first] + replacement + value[end:]
    marker = "mutate_into_other_effect = {"
    insertion = """
\tsave_scope_as = host
\t# Centralized horde: conquered rulers do not remain landed undead vassals.
\tif = {
\t\tlimit = { is_landed = yes NOT = { has_trait = other_trait } }
\t\tif = {
\t\t\tlimit = { is_ai = no has_dlc_feature = roads_to_power }
\t\t\tflee_noble_south_effect = yes
\t\t}
\t\telse = {
\t\t\tcreate_title_and_vassal_change = { type = conquest save_scope_as = ln_horde_change }
\t\t\tevery_held_title = {
\t\t\t\tchange_title_holder = { holder = title:h_the_others.holder change = scope:ln_horde_change }
\t\t\t}
\t\t\tresolve_title_and_vassal_change = scope:ln_horde_change
\t\t}
\t}
"""
    value = replace_exact(value, marker, marker + insertion, "central horde conversion")
    value = re.sub(
        r"(?m)^\s*change_government\s*=\s*wight_government\s*\r?\n", "", value
    )
    value = replace_regex(
        value,
        r"(\t\tevery_player\s*=\s*\{\s*trigger_event\s*=\s*\{\s*id\s*=\s*long_night_plus_wall\.1\s*\}\s*\})",
        r"\1\r\n\t\ttrigger_event = { id = agot_ln.39 days = 3 }",
        "coalition call after Wall breach",
    )
    return value


def patch_maa(inputs: RunInputs) -> str:
    value = compat_maa(inputs)
    for old, new in {
        "damage = 38": "damage = 40",
        "toughness = 120": "toughness = 40",
        "pursuit = 70": "pursuit = 15",
        "screen = 0": "screen = 20",
        "stack = 500": "stack = 100",
        "siege_tier = 4": "siege_tier = 1",
        "siege_value = 0.9": "siege_value = 0.15",
    }.items():
        value = replace_exact(value, old, new, f"balanced MAA: {old}")
    value = replace_exact(
        value,
        "type = heavy_infantry",
        "type = heavy_infantry\n\tspecial_recruit_only = yes",
        "event-only MAA",
    )
    return value


def patch_story(inputs: RunInputs) -> str:
    value = compat_story(inputs)
    value = replace_exact(
        value,
        "on_end = {",
        "on_end = {\n\tremove_global_variable = agot_long_night_active\n\tset_global_variable = { name = agot_long_night_completed value = yes }",
        "crisis cleanup state",
    )
    death = """on_owner_death = {
\t\tif = {
\t\t\tlimit = { has_global_variable = war_for_dawn_victory }
\t\t\tend_story = yes
\t\t}
\t\telse = {
\t\t\tchange_global_variable = { name = agot_long_night_threat add = -10 }
\t\t\tif = { limit = { global_var:agot_long_night_threat < 0 } set_global_variable = { name = agot_long_night_threat value = 0 } }
\t\t\tif = {
\t\t\t\tlimit = { exists = title:h_the_others.holder title:h_the_others.holder = { is_alive = yes } }
\t\t\t\tmake_story_owner = title:h_the_others.holder
\t\t\t\tstory_owner = {
\t\t\t\t\tadd_trait = nightking
\t\t\t\t\tadd_character_modifier = { modifier = agot_ln_leaderless_modifier years = 2 }
\t\t\t\t}
\t\t\t}
\t\t}
\t}"""
    value = replace_definition(value, "on_owner_death", death)
    value = replace_regex(
        value,
        r"(exists\s*=\s*title:h_the_others\.holder\s*)(title:c_castle_black\.holder)",
        r"\1has_global_variable = agot_ln_horn_ritual_ready\r\n\t\t\t\t\2",
        "Horn-gated Wall breach",
    )
    return value


def patch_decisions(inputs: RunInputs) -> str:
    value = compat_decisions(inputs)
    start, end = definition_span(value, "others_trigger_invasion")
    block = value[start:end]
    block = replace_regex(
        block,
        r"effect\s*=\s*\{\s*trigger_event\s*=\s*others\.1\s*\}",
        "is_valid = {\n\t\tglobal_var:what_season_is_it = 3\n\t\thas_dlc_feature = roads_to_power\n\t}\n\n\teffect = {\n\t\ttrigger_event = agot_ln.12\n\t}",
        "manual winter gate",
    )
    return value[:start] + block + value[end:]


def patch_other_events(inputs: RunInputs) -> str:
    relative = "events/others_events/others_events.txt"
    value = compat_simple_files(inputs)[relative]
    marker = "\t\tthe_long_night_setup_effect = yes"
    addition = (
        marker
        + "\n\t\tset_global_variable = { name = agot_long_night_active value = yes }\n\t\tset_global_variable = { name = agot_long_night_threat value = 0 }"
    )
    return replace_exact(value, marker, addition, "activate crisis state")


def patch_cb(inputs: RunInputs) -> str:
    value = compat_cb(inputs)
    return replace_regex(
        value,
        r"(war_for_the_dawn_cb\s*=\s*\{.*?on_victory\s*=\s*\{)",
        r"\1\r\n\tagot_war_victory_effects = yes",
        "AGOT war victory hook",
        flags=re.DOTALL,
    )


def api_triggers() -> str:
    return """is_agot_long_night_loaded_trigger = {
\thas_global_variable = agot_long_night_enabled
}

is_agot_long_night_active_trigger = {
\thas_global_variable = agot_long_night_active
\tNOT = { has_global_variable = agot_long_night_completed }
}

is_agot_long_night_start_eligible_trigger = {
\tNOT = { has_global_variable = others_invasion_has_arrived }
\tNOT = { has_global_variable = agot_long_night_dependency_blocked }
\tNOT = { has_game_rule = others_invasion_wont_happen }
\tcurrent_year >= global_var:agot_long_night_eligible_year
\tglobal_var:what_season_is_it = 3
}
"""


def rework_effects() -> str:
    return """agot_ln_spawn_reinforcement_effect = {
\tif = { limit = { has_game_rule = others_weak_invasion } spawn_army = { men_at_arms = { type = other_maa stacks = 25 } name = wights uses_supply = no location = capital_province } }
\telse_if = { limit = { has_game_rule = others_strong_invasion } spawn_army = { men_at_arms = { type = other_maa stacks = 87 } name = wights uses_supply = no location = capital_province } }
\telse_if = { limit = { has_game_rule = others_insane_invasion } spawn_army = { men_at_arms = { type = other_maa stacks = 125 } name = wights uses_supply = no location = capital_province } }
\telse = { spawn_army = { men_at_arms = { type = other_maa stacks = 50 } name = wights uses_supply = no location = capital_province } }
}

agot_ln_add_threat_effect = {
\tchange_global_variable = { name = agot_long_night_threat add = $AMOUNT$ }
\tif = {
\t\tlimit = { global_var:agot_long_night_threat >= 25 NOT = { has_global_variable = agot_ln_threat_25 } }
\t\tset_global_variable = { name = agot_ln_threat_25 value = yes }
\t\tif = { limit = { has_game_rule = agot_long_night_dragon_on } set_global_variable = { name = agot_ln_horn_ritual_ready value = yes } }
\t\telse = { trigger_event = { id = agot_ln.30 days = 30 } }
\t\tagot_ln_spawn_reinforcement_effect = yes
\t}
\tif = { limit = { global_var:agot_long_night_threat >= 50 NOT = { has_global_variable = agot_ln_threat_50 } } set_global_variable = { name = agot_ln_threat_50 value = yes } agot_ln_spawn_reinforcement_effect = yes add_character_modifier = agot_ln_threat_50_modifier }
\tif = { limit = { global_var:agot_long_night_threat >= 75 NOT = { has_global_variable = agot_ln_threat_75 } } set_global_variable = { name = agot_ln_threat_75 value = yes } agot_ln_spawn_reinforcement_effect = yes add_character_modifier = agot_ln_threat_75_modifier }
}

agot_ln_join_war_for_dawn_effect = {
\tif = {
\t\tlimit = { title:h_the_others.holder = { any_character_war = { is_defender = title:h_the_others.holder using_cb = war_for_the_dawn_cb } } }
\t\ttitle:h_the_others.holder = {
\t\t\trandom_character_war = { limit = { is_defender = title:h_the_others.holder using_cb = war_for_the_dawn_cb } add_attacker = root }
\t\t}
\t}
}
"""


def on_actions() -> str:
    return """on_combat_end_winner = { on_actions = { agot_ln_combat_growth } }

agot_ln_combat_growth = {
\ttrigger = { is_agot_long_night_active_trigger = yes side_primary_participant = { has_trait = other_trait } }
\teffect = {
\t\tside_primary_participant = { agot_ln_add_threat_effect = { AMOUNT = 2 } }
\t\tif = { limit = { scope:wipe = yes } side_primary_participant = { agot_ln_add_threat_effect = { AMOUNT = 3 } } }
\t}
}
"""


def rework_events() -> str:
    return """namespace = agot_ln

agot_ln.1 = {
\ttype = character_event
\ttitle = agot_ln.1.t
\tdesc = agot_ln.1.desc
\ttheme = realm
\toption = { name = agot_ln.1.a }
}

agot_ln.10 = {
\tscope = none
\thidden = yes
\timmediate = {
\t\tif = {
\t\t\tlimit = { is_agot_long_night_start_eligible_trigger = yes }
\t\t\tset_global_variable = { name = others_invasion_triggered value = yes }
\t\t\tevery_player = { trigger_event = agot_ln.11 }
\t\t\ttrigger_event = { id = others.1 days = 90 }
\t\t}
\t\telse = { trigger_event = { id = agot_ln.10 days = 90 } }
\t}
}

agot_ln.11 = {
\ttype = character_event
\ttitle = agot_ln.11.t
\tdesc = agot_ln.11.desc
\ttheme = realm
\toption = { name = agot_ln.11.a }
}

agot_ln.12 = {
\tscope = none
\thidden = yes
\ttrigger = { global_var:what_season_is_it = 3 has_dlc_feature = roads_to_power }
\timmediate = {
\t\tset_global_variable = { name = others_invasion_triggered value = yes }
\t\tevery_player = { trigger_event = agot_ln.11 }
\t\ttrigger_event = { id = others.1 days = 90 }
\t}
}

agot_ln.20 = {
\thidden = yes
\ttrigger = { is_agot_long_night_active_trigger = yes has_trait = other_trait }
\timmediate = {
\t\tif = { limit = { scope:county = title:c_castle_black } agot_ln_add_threat_effect = { AMOUNT = 10 } }
\t\telse = { agot_ln_add_threat_effect = { AMOUNT = 5 } }
\t}
}

agot_ln.30 = {
\thidden = yes
\tscope = none
\timmediate = {
\t\tset_global_variable = { name = agot_ln_horn_ritual_ready value = yes }
\t\tevery_player = { trigger_event = agot_ln.31 }
\t}
}

agot_ln.31 = {
\ttype = character_event
\ttitle = agot_ln.31.t
\tdesc = agot_ln.31.desc
\ttheme = realm
\toption = { name = agot_ln.31.a }
}

agot_ln.39 = {
\ttype = character_event
\thidden = yes
\timmediate = {
\t\tif = { limit = { exists = title:h_the_iron_throne.holder title:h_the_iron_throne.holder = { is_alive = yes NOT = { has_faith = faith:cold_gods } } } title:h_the_iron_throne.holder = { save_scope_as = agot_ln_leader } }
\t\telse_if = { limit = { exists = title:e_the_north.holder title:e_the_north.holder = { is_alive = yes NOT = { has_faith = faith:cold_gods } } } title:e_the_north.holder = { save_scope_as = agot_ln_leader } }
\t\telse = { ordered_independent_ruler = { limit = { capital_county.title_province = { geographical_region = world_westeros_seven_kingdoms } NOT = { has_faith = faith:cold_gods } } order_by = max_military_strength position = 0 save_scope_as = agot_ln_leader } }
\t\tif = { limit = { exists = scope:agot_ln_leader } set_global_variable = { name = agot_ln_coalition_leader value = scope:agot_ln_leader } scope:agot_ln_leader = { start_war = { cb = war_for_the_dawn_cb target = title:h_the_others.holder claimant = this } } }
\t\tevery_independent_ruler = { limit = { capital_county.title_province = { geographical_region = world_westeros_seven_kingdoms } NOT = { has_faith = faith:cold_gods } } trigger_event = agot_ln.40 }
\t}
}

agot_ln.40 = {
\ttype = character_event
\ttitle = agot_ln.40.t
\tdesc = agot_ln.40.desc
\ttheme = war
\toption = { name = agot_ln.40.a agot_ln_join_war_for_dawn_effect = yes ai_chance = { base = 40 modifier = { add = 40 capital_county.title_province = { geographical_region = world_westeros_the_north } } modifier = { add = 20 faith.religion = religion:the_pact_religion } } }
\toption = { name = agot_ln.40.b if = { limit = { gold >= 100 } remove_short_term_gold = 100 global_var:agot_ln_coalition_leader = { add_gold = 100 } } ai_chance = { base = 30 } }
\toption = { name = agot_ln.40.c ai_chance = { base = 20 } }
\toption = { name = agot_ln.40.d add_prestige = -100 ai_chance = { base = 10 modifier = { add = 30 has_trait = craven } } }
}
"""


def modifiers() -> str:
    return """agot_ln_leaderless_modifier = {
\tadvantage = -10
\tmonthly_prestige = -1
}
agot_ln_threat_50_modifier = { advantage = 5 siege_phase_time = -0.05 }
agot_ln_threat_75_modifier = { advantage = 10 siege_phase_time = -0.10 }
"""


def localization() -> str:
    return """l_english:
 agot_ln.1.t:0 "Roads to Power Required"
 agot_ln.1.desc:0 "AGOT: The Long Night requires the Roads to Power expansion. The crisis has been disabled for this campaign."
 agot_ln.1.a:0 "The road is closed."
 agot_ln.11.t:0 "The Cold Winds Are Rising"
 agot_ln.11.desc:0 "In the dead of winter, ravens carry impossible reports from beyond the Wall. Pale shapes move beneath the aurora, and the oldest tales are spoken aloud once more."
 agot_ln.11.a:0 "The night gathers."
 agot_ln.31.t:0 "The Horn of Winter"
 agot_ln.31.desc:0 "A terrible note rolls out of the far north. Whether the horn is Joramun's or some older instrument, the wards upon the Wall have begun to crack."
 agot_ln.31.a:0 "The Wall will not hold forever."
 agot_ln.40.t:0 "A War for the Dawn"
 agot_ln.40.desc:0 "The Wall is broken. The chosen leader of the living calls every realm of Westeros to stand against the dead."
 agot_ln.40.a:0 "Join the War for the Dawn."
 agot_ln.40.b:0 "Send gold and supplies."
 agot_ln.40.c:0 "Remain neutral."
 agot_ln.40.d:0 "Refuse the call."
 agot_ln_leaderless_modifier:0 "A Herald Fallen"
 agot_ln_leaderless_modifier_desc:0 "The destruction of the Great Other's herald has temporarily disordered the dead."
 agot_ln_threat_50_modifier:0 "The Dead Gather"
 agot_ln_threat_50_modifier_desc:0 "Every conquest adds fresh bodies to the host."
 agot_ln_threat_75_modifier:0 "The Endless Night"
 agot_ln_threat_75_modifier_desc:0 "The Army of the Dead advances beneath an ever-deepening winter."
 others_standard_invasion:0 "Escalating Crisis"
 others_standard_invasion_desc:0 "The dead begin as a grave regional threat and gain bounded reinforcements through conquest and decisive victories."
 others_weak_invasion:0 "Restrained Crisis"
 others_strong_invasion:0 "Great Winter"
 others_insane_invasion:0 "Apocalyptic Winter"
 others_historical_invasion:0 "Canon Threshold (298 AC)"
 others_immediate_invasion:0 "Next Eligible Winter"
 agot_long_night_dragon_off:0 "Ice Dragon Disabled"
 agot_long_night_dragon_on:0 "Ice Dragon Enabled"
"""


def expected_files(inputs: RunInputs) -> dict[str, bytes]:
    for path, digest in inputs.PINNED_HASHES.items():
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != digest:
            raise ValueError(f"pinned dependency changed: {path} ({actual})")

    files: dict[str, bytes] = {}
    for source in sorted(p for p in inputs.LONG_NIGHT.rglob("*") if p.is_file()):
        relative = source.relative_to(inputs.LONG_NIGHT).as_posix()
        if relative not in SKIP:
            files[relative] = source.read_bytes()

    patched = compat_simple_files(inputs)
    patched.pop("common/scripted_rules/00_rules.txt", None)
    fixed_loc = patched["localization/english/agot_long_night_compatch_l_english.yml"]
    fixed_loc = re.sub(r"(?m)^\s*GAME_OVER_CANNOT_PLAY_WIGHT:.*\n", "", fixed_loc)
    patched["localization/english/agot_long_night_compatch_l_english.yml"] = fixed_loc
    trait_loc = patched["localization/english/theothers_l_english.yml"]
    trait_loc = re.sub(
        r"(?m)^\s*trait_nightking:.*$",
        ' trait_nightking:0 "Herald of the Great Other"',
        trait_loc,
    )
    trait_loc = re.sub(
        r"(?m)^\s*trait_nightking_desc:.*$",
        ' trait_nightking_desc:0 "The transferable war-leader and voice of the power behind the Long Night."',
        trait_loc,
    )
    patched["localization/english/theothers_l_english.yml"] = trait_loc
    patched["common/game_rules/long_night_game_rules.txt"] = game_rules()
    patched["common/men_at_arms_types/long_night_maa_types.txt"] = patch_maa(inputs)
    patched["common/scripted_effects/agot_long_night_scripted_effects.txt"] = (
        patch_effects(inputs)
    )
    patched["common/casus_belli_types/00_long_night_cbs.txt"] = patch_cb(inputs)
    patched["common/decisions/00_agot_long_night_decisions.txt"] = patch_decisions(
        inputs
    )
    patched["common/story_cycles/the_long_night.txt"] = patch_story(inputs)
    patched["events/others_events/others_maintenance_events.txt"] = patch_maintenance(
        inputs
    )
    patched["events/others_events/others_events.txt"] = patch_other_events(inputs)
    patched[str(RELATIVE_ANIMATIONS)] = core_animation(inputs)
    patched["events/season_events.txt"] = patch_seasons(inputs)
    patched["common/scripted_triggers/agot_long_night_public_triggers.txt"] = (
        api_triggers()
    )
    patched["common/scripted_effects/agot_long_night_rework_effects.txt"] = (
        rework_effects()
    )
    patched["common/on_action/agot_long_night_rework_on_actions.txt"] = on_actions()
    patched["common/modifiers/agot_long_night_rework_modifiers.txt"] = modifiers()
    patched["events/agot_long_night_rework_events.txt"] = rework_events()
    patched["localization/english/zz_agot_long_night_rework_l_english.yml"] = (
        localization()
    )

    siege_events = text(
        inputs.LONG_NIGHT / "events/others_events/others_siege_events.txt"
    )
    siege_events = replace_exact(
        siege_events,
        "\t\tsave_scope_as = occupant",
        "\t\tsave_scope_as = occupant\n\t\tsave_scope_as = occupier",
        "siege occupier scope",
    )
    patched["events/others_events/others_siege_events.txt"] = siege_events

    aftermath_effects = text(
        inputs.LONG_NIGHT
        / "common/scripted_effects/zz_long_night_plus_aftermath_effects.txt"
    )
    aftermath_effects = replace_regex(
        aftermath_effects,
        r"(?m)^\s*NOT\s*=\s*\{\s*this\s*\?=\s*scope:ln_unleash_chooser\s*\}\s*\r?\n",
        "",
        "optional aftermath chooser scope",
    )
    patched["common/scripted_effects/zz_long_night_plus_aftermath_effects.txt"] = (
        aftermath_effects
    )

    for relative in (
        "common/on_action/00_others_on_actions.txt",
        "gfx/portraits/trait_portrait_modifiers/whitewalker_trait_modifiers.txt",
    ):
        patched[relative] = text(inputs.LONG_NIGHT / relative)

    siege_path = "common/on_action/AGOT Invasions/invasions_siege.txt"
    siege = text(inputs.LONG_NIGHT / siege_path)
    siege = replace_exact(
        siege,
        "others_siege.0001",
        "others_siege.0001\n        agot_ln.20",
        "threat siege event",
    )
    patched[siege_path] = siege

    for relative, value in patched.items():
        if relative not in SKIP:
            files[relative] = encoded(value)
    return files


def generate(context: GenerationContext) -> None:

    AGOT = context.source("agot")
    CORE = context.source("submod-core")
    SEASONS = context.source("seasons")
    LONG_NIGHT = context.source("long-night")
    PINNED_HASHES = {
        CORE / RELATIVE_ANIMATIONS: (
            "c0b7d8bf00ce21001e28a10ca76cc0c95cf850a0bf5ef3dd81d98b671b1a111a"
        ),
        SEASONS / "events/season_events.txt": (
            "f5f618b90ff2f5697517310b4d3c63f95c44ecf56150a2d1ad4cb3e26b217c04"
        ),
        LONG_NIGHT / RELATIVE_ANIMATIONS: (
            "2d8de11f686ba6772c4607f0d1a8b7938153b589a1c081d5d194dd45c06142bd"
        ),
    }
    inputs = RunInputs(
        AGOT=AGOT,
        CORE=CORE,
        SEASONS=SEASONS,
        LONG_NIGHT=LONG_NIGHT,
        PINNED_HASHES=PINNED_HASHES,
    )
    for relative, content in sorted(expected_files(inputs).items()):
        context.write_bytes(relative, content)
