#!/usr/bin/env python3
"""Regenerate the Long Night+, Submod Core, and DFP compatibility patch."""

from __future__ import annotations

import argparse
import codecs
import hashlib
import os
import re
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def required_environment_path(name: str) -> Path:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"{name} is not set")
    return Path(value).expanduser().resolve()


WORKSHOP = required_environment_path("CK3_WORKSHOP_DIR")
AGOT = WORKSHOP / "2962333032"
SUBMOD_CORE = WORKSHOP / "3034473189"
DFP_AGOT = WORKSHOP / "3609763696"
LONG_NIGHT = WORKSHOP / "3766462389"
STANDALONE_LONG_NIGHT = ROOT / "mods" / "agot_the_long_night"

RELATIVE_ANIMATIONS = Path("gfx/portraits/portrait_animations/animations.txt")
MOD_OUTPUT_ROOT = ROOT / "mods" / "agot_longnight_submodcore_dfp_compatch"

EXPECTED_DFP_POSES = 197
EXPECTED_MERGED_POSES = 196
EXPECTED_WIGHT_POSES = 5
EXPECTED_DFP_ANIMATIONS_SHA256 = (
    "8ddcb0ba720c236d6913779d924203d5105897c63251224b64e931e272f6a65c"
)


def read(path: Path) -> str:
    if not path.is_file():
        raise SystemExit(f"missing required source: {path}")
    raw = path.read_bytes()
    if not raw.startswith(codecs.BOM_UTF8):
        raise SystemExit(f"required source is missing its UTF-8 BOM: {path}")
    return raw.decode("utf-8-sig")


def read_source(path: Path) -> str:
    if not path.is_file():
        raise ValueError(f"missing required source: {path}")
    return path.read_bytes().decode("utf-8-sig")


def replace_exact(
    text: str, old: str, new: str, label: str, expected: int = 1
) -> str:
    count = text.count(old)
    if count != expected:
        raise ValueError(f"{label}: expected {expected} matches, found {count}")
    return text.replace(old, new)


def replace_regex(
    text: str,
    pattern: str,
    replacement: str,
    label: str,
    expected: int = 1,
    flags: int = 0,
) -> str:
    result, count = re.subn(pattern, replacement, text, flags=flags)
    if count != expected:
        raise ValueError(f"{label}: expected {expected} matches, found {count}")
    return result


def replace_braced_block_after(
    text: str, marker: str, definition: str, replacement: str, label: str
) -> str:
    marker_at = unique_marker(text, marker, f"{label} marker")
    match = re.search(
        rf"(?m)^[ \t]*{re.escape(definition)}", text[marker_at:]
    )
    if match is None:
        raise ValueError(f"{label}: definition not found after marker")
    start = marker_at + match.start()
    opening = text.find("{", start)
    end = matching_brace(text, opening) + 1
    return text[:start] + replacement + text[end:]


def newline_style(text: str) -> str:
    return "\r\n" if "\r\n" in text else "\n"


def normalize_newlines(text: str, newline: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n").replace("\n", newline)


def strip_trailing_whitespace(text: str) -> str:
    return re.sub(r"[ \t]+(?=\r?$)", "", text, flags=re.MULTILINE)


def matching_brace(text: str, opening: int) -> int:
    depth = 0
    quoted = False
    escaped = False
    comment = False
    for index in range(opening, len(text)):
        char = text[index]
        if comment:
            if char == "\n":
                comment = False
            continue
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
            continue
        if char == "#":
            comment = True
        elif char == '"':
            quoted = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index
    raise ValueError("unclosed brace")


def definition_matches(text: str, name_pattern: str) -> list[re.Match[str]]:
    return list(
        re.finditer(
            rf"(?m)^\t\t(?P<name>{name_pattern})\s*=\s*\{{",
            text,
        )
    )


def definition_span(text: str, name: str) -> tuple[int, int]:
    matches = definition_matches(text, re.escape(name))
    if len(matches) != 1:
        raise ValueError(f"{name}: expected one definition, found {len(matches)}")
    start = matches[0].start()
    opening = text.find("{", start)
    end = matching_brace(text, opening) + 1
    while end < len(text) and text[end] in " \t":
        end += 1
    if text.startswith("\r\n", end):
        end += 2
    elif end < len(text) and text[end] == "\n":
        end += 1
    return start, end


def unique_marker(text: str, marker: str, label: str) -> int:
    count = text.count(marker)
    if count != 1:
        raise ValueError(f"{label}: expected one insertion marker, found {count}")
    return text.index(marker)


def direct_definition_names(text: str, name_pattern: str) -> list[str]:
    return [match.group("name") for match in definition_matches(text, name_pattern)]


def assert_count(text: str, name_pattern: str, expected: int, label: str) -> None:
    count = len(definition_matches(text, name_pattern))
    if count != expected:
        raise ValueError(f"{label}: expected {expected}, found {count}")


def extract_dfp_poses(dfp: str, newline: str) -> tuple[str, set[str]]:
    pose_names = direct_definition_names(dfp, r"CIP_[A-Za-z0-9_]+")
    if len(pose_names) != EXPECTED_DFP_POSES:
        raise ValueError(
            f"DFP poses: expected {EXPECTED_DFP_POSES}, found {len(pose_names)}"
        )
    if len(set(pose_names)) != len(pose_names):
        raise ValueError("DFP poses contain duplicate definition names")

    first_pose = unique_marker(dfp, "\t\tCIP_toast = {", "first DFP pose")
    dfp_newline = newline_style(dfp)
    high_septon_marker = f"\t\t#AGOT Added{dfp_newline}\t\thigh_septon = {{"
    high_septon = unique_marker(dfp, high_septon_marker, "DFP high_septon")
    if first_pose >= high_septon:
        raise ValueError("DFP pose region is not before high_septon")
    poses = dfp[first_pose:high_septon]

    obsolete_start, obsolete_end = definition_span(poses, "CIP_agressive_longsword")
    poses_newline = newline_style(poses)
    removal_start = obsolete_start
    if poses[:obsolete_start].endswith(poses_newline):
        removal_start -= len(poses_newline)
    poses = poses[:removal_start] + poses_newline + poses[obsolete_end:]

    trigger = re.compile(
        r"(?m)^[ \t]*use_longsword_default_trigger\s*=\s*no[ \t]*(?:\r?\n)"
    )
    poses, replacements = trigger.subn("", poses)
    if replacements != 1:
        raise ValueError(
            "generic DFP aggressive pose: expected one obsolete trigger, "
            f"found {replacements}"
        )

    expected_names = set(pose_names) - {"CIP_agressive_longsword"}
    actual_names = set(direct_definition_names(poses, r"CIP_[A-Za-z0-9_]+"))
    if actual_names != expected_names:
        raise ValueError(
            "DFP pose extraction did not preserve the expected definitions"
        )
    return normalize_newlines(poses, newline), expected_names


def extract_core_bow(core: str, newline: str) -> str:
    bow_start, bow_end = definition_span(core, "hold_bow_idle")
    comment = "\t\t##TGC Added"
    comment_start = core.rfind(comment, 0, bow_start)
    if comment_start < 0 or core[comment_start:bow_start].count("\n") > 2:
        raise ValueError("Submod Core bow pose is missing its expected TGC comment")
    return normalize_newlines(core[comment_start:bow_end], newline)


def generate() -> str:
    long_night = read(STANDALONE_LONG_NIGHT / RELATIVE_ANIMATIONS)
    dfp_path = DFP_AGOT / RELATIVE_ANIMATIONS
    if not dfp_path.is_file():
        raise ValueError(f"missing required DFP AGOT source: {dfp_path}")
    dfp_bytes = dfp_path.read_bytes()
    actual_hash = hashlib.sha256(dfp_bytes).hexdigest()
    if actual_hash != EXPECTED_DFP_ANIMATIONS_SHA256:
        raise ValueError(
            "DFP AGOT animations changed upstream: expected "
            f"{EXPECTED_DFP_ANIMATIONS_SHA256}, found {actual_hash}"
        )
    dfp = read(dfp_path)
    newline = newline_style(long_night)

    assert_count(
        long_night,
        r"wight_pose_[A-Za-z0-9_]+",
        EXPECTED_WIGHT_POSES,
        "Long Night+ wight poses",
    )
    assert_count(long_night, r"CIP_[A-Za-z0-9_]+", 0, "Long Night+ DFP poses")
    assert_count(long_night, "hold_long_axe_idle", 1, "AGOT long-axe pose")
    assert_count(long_night, "hold_bow_idle", 1, "Submod Core bow pose")

    poses, expected_pose_names = extract_dfp_poses(dfp, newline)

    high_septon_marker = f"\t\t#AGOT Added{newline}\t\thigh_septon = {{"
    unique_marker(long_night, high_septon_marker, "Long Night+ high_septon")

    merged = long_night.replace(high_septon_marker, poses + high_septon_marker, 1)

    merged_pose_names = set(direct_definition_names(merged, r"CIP_[A-Za-z0-9_]+"))
    if merged_pose_names != expected_pose_names:
        raise ValueError("merged file does not contain the expected DFP pose set")
    assert_count(
        merged,
        r"CIP_[A-Za-z0-9_]+",
        EXPECTED_MERGED_POSES,
        "merged DFP poses",
    )
    assert_count(
        merged,
        r"wight_pose_[A-Za-z0-9_]+",
        EXPECTED_WIGHT_POSES,
        "merged wight poses",
    )
    assert_count(merged, "hold_bow_idle", 1, "merged bow pose")
    assert_count(merged, "hold_long_axe_idle", 1, "merged long-axe pose")
    assert_count(
        merged,
        "CIP_agressive_longsword",
        0,
        "obsolete DFP longsword pose",
    )
    active_removed_trigger = re.findall(
        r"(?m)^[ \t]*use_longsword_default_trigger\s*=", merged
    )
    if active_removed_trigger:
        raise ValueError("merged file still has an active removed longsword trigger")
    return strip_trailing_whitespace(normalize_newlines(merged, "\n"))


def wrap_special_genes(
    relative: str,
    category: str,
    *,
    remove_morph_metadata: int = 0,
    remove_draugr_attributes: bool = False,
) -> str:
    text = read_source(LONG_NIGHT / relative)
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


def patch_dna() -> str:
    relative = "common/dna_data/agot_dna_a_long_night.txt"
    text = read_source(LONG_NIGHT / relative)
    indent = " \t\t"
    dragon_lines = [
        ('gene_dragon_primary_color_hue', '"dragon_primary_color_hue" 127 "dragon_primary_color_hue" 127'),
        ('gene_dragon_primary_color_value', '"dragon_primary_color_value" 127 "dragon_primary_color_value" 127'),
        ('gene_dragon_secondary_hue', '"dragon_secondary_hue" 127 "dragon_secondary_hue" 127'),
        ('gene_dragon_secondary_value', '"dragon_secondary_value" 127 "dragon_secondary_value" 127'),
        ('gene_dragon_wounded', '"dragon_scarred" 0 "dragon_scarred" 0'),
        ('gene_dragon_tertiary_hue', '"dragon_tertiary_hue" 127 "dragon_tertiary_hue" 127'),
        ('gene_dragon_tertiary_value', '"dragon_tertiary_value" 127 "dragon_tertiary_value" 127'),
        ('gene_dragon_body_shading', '"dragon_body_shading_lower_black" 0 "dragon_body_shading_lower_black" 0'),
        ('gene_dragon_wings_shading', '"dragon_wings_shading_back_black" 0 "dragon_wings_shading_back_black" 0'),
        ('gene_dragon_eye_color_hue', '"dragon_eye_color_hue" 127 "dragon_eye_color_hue" 127'),
        ('gene_dragon_eye_color_value', '"dragon_eye_color_value" 127 "dragon_eye_color_value" 127'),
        ('gene_dragon_horn_color_hue', '"dragon_horn_color_hue" 127 "dragon_horn_color_hue" 127'),
        ('gene_dragon_horn_color_value', '"dragon_horn_color_value" 127 "dragon_horn_color_value" 127'),
        ('gene_dragon_metallic_scales_strength', '"dragon_scales_metallic" 127 "dragon_scales_metallic" 127'),
    ]
    neutral_shapes = [
        "gene_dragon_brow_width", "gene_dragon_cheek_width",
        "gene_dragon_chin_profile", "gene_dragon_crest_depth",
        "gene_dragon_head_roundness", "gene_dragon_horns_eyebrow_length",
        "gene_dragon_main_horn_shape", "gene_dragon_jaw_width",
        "gene_dragon_lower_jaw_height", "gene_dragon_lower_jaw_width",
        "gene_dragon_old_neck", "gene_dragon_outer_brow_height",
        "gene_dragon_snout_height", "gene_dragon_snout_length",
        "gene_dragon_snout_profile", "gene_dragon_snout_width",
        "gene_dragon_upper_jaw_width", "gene_dragon_back_spike_size",
        "gene_dragon_center_fin_size", "gene_dragon_horns_eyebrow",
        "gene_dragon_neck_spike_size", "gene_dragon_side_fin_size",
        "gene_dragon_snout_end_width", "gene_dragon_neck_length",
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


def patch_maa() -> str:
    relative = "common/men_at_arms_types/long_night_maa_types.txt"
    text = read_source(LONG_NIGHT / relative)
    text = replace_exact(text, "type = Other_infantry", "type = heavy_infantry", f"{relative}: MAA category")
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
        text,
        r"\r?\n\}\s*$",
        "\n",
        f"{relative}: obsolete extra closing brace",
    )
    return text


def patch_cb() -> str:
    relative = "common/casus_belli_types/00_long_night_cbs.txt"
    text = read_source(LONG_NIGHT / relative)
    for field in ("attacker_score_from_battle_scale", "defender_score_from_battle_scale"):
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


def patch_scripted_effects() -> str:
    relative = "common/scripted_effects/agot_long_night_scripted_effects.txt"
    text = read_source(LONG_NIGHT / relative)
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
    text = replace_regex(text, r"(?m)^\s*make_trait_inactive\s*=\s*is_targaryen_3\s*\r?\n", "", f"{relative}: removed trait")
    text = replace_regex(text, r"(?m)^\s*template\s*=\s*other_template\s*\r?\n", "", f"{relative}: removed empty template")
    marker = "longnight_reform_nightswatch_effect = {"
    marker_at = unique_marker(text, marker, f"{relative}: NW reform")
    create_at = text.find("create_character = {", marker_at)
    insert_at = text.find("\n", create_at) + 1
    text = text[:insert_at] + "\n\t\t\t\t\t\t\tlocation = title:c_castle_black.title_province\n" + text[insert_at:]
    text = replace_exact(
        text,
        "get_title = title:h_the_others",
        "get_title = title:h_the_others\n\t\t\tchange_government = wight_government",
        f"{relative}: dead-realm government",
    )
    for trait in (
        "goutridden", "leper_1", "st_anthonys_fire", "great_spring_sickness",
        "winter_fever", "blood_cough", "bloody_flux", "shaking_sickness",
        "dancing_plague", "lover_pox",
    ):
        text = replace_regex(
            text,
            rf"(?m)^\s*if\s*=\s*\{{\s*limit\s*=\s*\{{\s*has_trait\s*=\s*{trait}\s*\}}\s*remove_trait\s*=\s*{trait}\s*\}}\s*\r?\n",
            "",
            f"{relative}: remove obsolete disease {trait}",
        )
    switch_marker = "trigger = scope:ln_maa_region"
    switch_start = text.rfind("switch = {", 0, unique_marker(text, switch_marker, f"{relative}: regional MAA"))
    switch_end = matching_brace(text, text.find("{", switch_start)) + 1
    regions = {
        "north": "frog_spears", "riverlands": "river_bows", "vale": "finger_scouts",
        "crownlands": "royal_crossbowmen", "westerlands": "rain_bringers",
        "reach": "honeywine_quirrels", "stormlands": "marcher_longbowmen",
        "dorne": "sun_spears", "ironman": "ironborn_reavers", "wildling": "clan_raiders",
    }
    region_lines = ["switch = {", "\t\t\ttrigger = scope:ln_maa_region"]
    for region, maa in regions.items():
        region_lines.extend([
            f"\t\t\tflag:{region} = {{",
            f"\t\t\t\tif = {{ limit = {{ scope:ln_camp_level >= 4 }} {literal_regiment(maa, 4, '')} }}",
            f"\t\t\t\telse_if = {{ limit = {{ scope:ln_camp_level >= 3 }} {literal_regiment(maa, 3, '')} }}",
            f"\t\t\t\telse_if = {{ limit = {{ scope:ln_camp_level >= 2 }} {literal_regiment(maa, 2, '')} }}",
            f"\t\t\t\telse = {{ {literal_regiment(maa, 1, '')} }}",
            "\t\t\t}",
        ])
    region_lines.append("\t\t}")
    text = text[:switch_start] + "\n".join(region_lines) + text[switch_end:]
    return text


def patch_decisions() -> str:
    relative = "common/decisions/00_agot_long_night_decisions.txt"
    text = read_source(LONG_NIGHT / relative)
    text = replace_exact(text, "has_faith = faith:old_gods", "faith.religion = religion:the_pact_religion", f"{relative}: Pact religion")
    text = replace_exact(text, "has_faith = faith:weirwood_of_the_seven", "has_faith = faith:fots_oldnew", f"{relative}: mixed faith")
    text = replace_exact(text, "faith = faith:rhllor", "faith.religion = religion:the_rhllor_religion", f"{relative}: Rhllor religion")
    text = replace_regex(
        text,
        r"(?ms)^\s*modifier\s*=\s*\{\s*add\s*=\s*50\s*faith\s*=\s*faith:red_god\s*\}\s*",
        "",
        f"{relative}: duplicate Rhllor modifier",
    )
    text = replace_exact(text, "faith = faith:trios", "faith = faith:fc_pan_tyrosh", f"{relative}: Trios faith")
    text = replace_exact(text, "has_government = free_city_government", "government_has_flag = government_is_free_city", f"{relative}: free city government")
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


def patch_story() -> str:
    relative = "common/story_cycles/the_long_night.txt"
    text = read_source(LONG_NIGHT / relative)
    text = replace_exact(text, "add_culture_tradition = agot_tradition_wildling", "add_culture_tradition = tradition_agot_wildling", f"{relative}: wildling tradition")
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


def patch_maintenance_events() -> str:
    relative = "events/others_events/others_maintenance_events.txt"
    text = read_source(LONG_NIGHT / relative)
    text = replace_regex(text, r"(?m)^\s*type\s*=\s*empty\s*\r?\n", "", f"{relative}: empty event type", 2)
    text = replace_exact(text, "faith:old_gods_btw", "faith:old_gods_btw_fnf", f"{relative}: BTW faith")
    final_marker = "game_start_date < 8298.1.1"
    if text.count(final_marker) != 2:
        raise ValueError(f"{relative}: expected two dated scheduler markers")
    marker_at = text.rfind(final_marker)
    final_else_if = text.find("else_if = {", marker_at)
    if final_else_if < 0:
        raise ValueError(f"{relative}: final scheduler else_if not found")
    text = text[:final_else_if] + text[final_else_if:].replace("else_if = {", "else = {", 1)
    return text


def patch_occupation_events() -> str:
    relative = "events/others_events/others_occupation_events.txt"
    text = read_source(LONG_NIGHT / relative)
    text = replace_exact(text, "agot_tradition_wildling", "tradition_agot_wildling", f"{relative}: wildling tradition")
    text = replace_exact(text, "faith:old_gods_btw", "faith:old_gods_btw_fnf", f"{relative}: BTW faith")
    text = replace_exact(text, "faith:old_gods_south", "faith:old_gods_wnw", f"{relative}: southern Old Gods")
    return text


def patch_aftermath_event() -> str:
    relative = "events/ln_aftermath_events.txt"
    text = read_source(LONG_NIGHT / relative)
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


def patch_traits() -> str:
    relative = "common/traits/invasions_traits.txt"
    text = read_source(LONG_NIGHT / relative)
    text = replace_regex(text, r"(?m)^\s*(?:birth|random_creation)\s*=\s*0\s*\r?\n", "", f"{relative}: non-genetic fields", 4)
    text = replace_regex(
        text,
        r"(?ms)(^other_trait\s*=\s*\{.*?^\s*)blocks_from_claim_inheritance\s*=\s*yes",
        r"\1inheritance_blocker = all\n\tclaim_inheritance_blocker = all",
        f"{relative}: current inheritance blockers",
    )
    text = replace_regex(text, r"(?m)^\s*blocks_from_claim_inheritance\s*=\s*yes\s*\r?\n", "", f"{relative}: redundant wight blocker")
    text = replace_regex(text, r"(?m)^\s*hostile_scheme_resistance_(?:mult|add)\s*=.*\r?\n", "", f"{relative}: removed scheme fields", 2)
    text = replace_exact(text, "enemy_personal_scheme_success_chance_add = -500", "enemy_personal_scheme_success_chance_add = -500\n\tenemy_hostile_scheme_success_chance_add = -200", f"{relative}: current hostile scheme defense")
    text = replace_regex(text, r"(?m)^\s*can_create_activity\s*=\s*no\s*\r?\n", "", f"{relative}: removed activity modifier", 2)
    for trait in (
        "goutridden", "leper_1", "st_anthonys_fire", "great_spring_sickness",
        "winter_fever", "blood_cough", "bloody_flux", "shaking_sickness",
        "dancing_plague", "lover_pox",
    ):
        text = replace_regex(text, rf"(?m)^\s*{trait}\s*\r?\n", "", f"{relative}: obsolete trait {trait}", 3)
    return text


def patch_government() -> str:
    relative = "common/governments/zz_wight_government.txt"
    text = read_source(LONG_NIGHT / relative)
    return replace_exact(
        text,
        "flags = {\n\t\tgovernment_is_tribal",
        "flags = {\n\t\tgovernment_is_uninteractable\n\t\tgovernment_is_tribal",
        f"{relative}: uninteractable flag",
    )


def patch_rules() -> str:
    relative = "common/scripted_rules/00_rules.txt"
    text = read_source(AGOT / relative)
    long_night = read_source(LONG_NIGHT / relative)
    block_start = unique_marker(long_night, "\t\t#The Long Night+ Added", f"{relative}: Long Night player block")
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


def patch_culture() -> str:
    relative = "common/culture/cultures/00_other_culture.txt"
    text = read_source(LONG_NIGHT / relative)
    return replace_exact(text, "0.79500034", "0.79500", f"{relative}: supported decimal precision", 2)


def patch_history() -> str:
    relative = "history/characters/othersinvasion_characters.txt"
    text = read_source(LONG_NIGHT / relative)
    text = replace_exact(text, "name = Other", "name = other_name", f"{relative}: localized name")
    text = replace_exact(text, "house = house_theothers", "dynasty_house = house_theothers", f"{relative}: history house field")
    for rank in ("novice", "apprentice", "journeyman"):
        perk = f"necromancy_{rank}_perk"
        text = replace_regex(
            text,
            rf"(?ms)^\s*if\s*=\s*\{{\s*limit\s*=\s*\{{\s*NOT\s*=\s*\{{\s*has_perk\s*=\s*{perk}\s*\}}\s*\}}\s*add_perk\s*=\s*{perk}\s*\}}[ \t]*\r?\n",
            "",
            f"{relative}: undefined {perk} block",
        )
    return text


def patch_armor_asset() -> str:
    relative = "gfx/models/portraits/m_clothes/other_armor/male_clothes_others_armor.asset"
    text = read_source(LONG_NIGHT / relative)
    first = 'name = "male_clothes_secular_other_war_02Shape"'
    positions = [match.start() for match in re.finditer(re.escape(first), text)]
    if len(positions) != 2:
        raise ValueError(f"{relative}: expected two armor meshsettings, found {len(positions)}")
    second = positions[1]
    text = text[:second] + text[second:].replace(first, 'name = "male_clothes_secular_other_war_02Shape-001"', 1)
    text = replace_regex(
        text,
        r"(?m)^\s*attribute\s*=\s*\{\s*name\s*=\s*\"bs_body_(?:infant|fat|gaunt|muscular|old|dwarf)_1\".*\r?\n",
        "",
        f"{relative}: absent armor blend shapes",
        6,
    )
    return text


def patch_gui() -> str:
    relative = "gui/event_windows/ln_topleft_wall_event.gui"
    text = read_source(LONG_NIGHT / relative)
    text = replace_exact(text, "Select_CFixedPoint", "Select_int32", f"{relative}: integer width selectors", 5)
    text = replace_regex(text, r"'\(CFixedPoint\)(120|170|200|250|400)'", r"'(int32)\1'", f"{relative}: integer width casts", 7)
    types_at = unique_marker(text, "types Events {", f"{relative}: copied global types")
    return text[:types_at].rstrip() + "\n"


def patch_theothers_localization() -> str:
    relative = "localization/english/theothers_l_english.yml"
    text = read_source(LONG_NIGHT / relative)
    for key in ("dynn_others", "dynn_Others", "dynn_others_motto"):
        text = replace_regex(text, rf"(?m)^\s*{key}:.*\r?\n", "", f"{relative}: canonical {key}")
    motto_matches = list(re.finditer(r"(?m)^\s*dynn_the_others_motto:.*\r?\n", text))
    if len(motto_matches) != 2:
        raise ValueError(
            f"{relative}: expected two dynn_the_others_motto definitions, "
            f"found {len(motto_matches)}"
        )
    duplicate = motto_matches[1]
    text = text[:duplicate.start()] + text[duplicate.end():]
    for key in (
        "other_barony_male", "other_county_male", "other_duchy_male", "other_kingdom_male",
        "other_barony_female", "other_county_female", "other_duchy_female", "other_kingdom_female",
        "other_empire_male", "other_empire_female",
    ):
        matches = list(re.finditer(rf"(?m)^\s*{key}:.*\r?\n", text))
        if len(matches) != 2:
            raise ValueError(f"{relative}: expected two {key} definitions, found {len(matches)}")
        text = text[:matches[0].start()] + text[matches[0].end():]
    text = replace_regex(text, r"fearÃ[^\s]*fear", "fear—fear", f"{relative}: mojibake")
    return text


def compatch_localization() -> str:
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


def patch_simple_files() -> dict[str, str]:
    files: dict[str, str] = {}
    files["common/genes/zz_long_night_genes.txt"] = wrap_special_genes(
        "common/genes/zz_long_night_genes.txt",
        "morph_genes",
        remove_morph_metadata=18,
    )
    files["common/genes/zz_wight_genes.txt"] = wrap_special_genes(
        "common/genes/zz_wight_genes.txt",
        "morph_genes",
        remove_draugr_attributes=True,
    )
    files["common/genes/zz_wight_gore_genes.txt"] = wrap_special_genes(
        "common/genes/zz_wight_gore_genes.txt", "morph_genes"
    )
    for name in (
        "zz_others_genes_special_accessories_clothes.txt",
        "zz_others_genes_special_accessories_eyes.txt",
    ):
        relative = f"common/genes/{name}"
        files[relative] = wrap_special_genes(relative, "accessory_genes")
    files["common/dna_data/agot_dna_a_long_night.txt"] = patch_dna()
    files["common/men_at_arms_types/long_night_maa_types.txt"] = patch_maa()
    files["common/casus_belli_types/00_long_night_cbs.txt"] = patch_cb()
    files["common/scripted_effects/agot_long_night_scripted_effects.txt"] = patch_scripted_effects()
    files["common/decisions/00_agot_long_night_decisions.txt"] = patch_decisions()
    files["common/story_cycles/the_long_night.txt"] = patch_story()
    files["events/others_events/others_maintenance_events.txt"] = patch_maintenance_events()
    files["events/others_events/others_occupation_events.txt"] = patch_occupation_events()
    files["events/ln_aftermath_events.txt"] = patch_aftermath_event()
    other_events = "events/others_events/others_events.txt"
    files[other_events] = replace_regex(
        read_source(LONG_NIGHT / other_events),
        r"(?m)^\s*type\s*=\s*empty\s*\r?\n",
        "",
        f"{other_events}: empty event type",
    )
    modifier = "common/modifiers/zz_long_night_plus_modifiers.txt"
    files[modifier] = replace_exact(
        read_source(LONG_NIGHT / modifier),
        "travel_speed = 0.25",
        "character_travel_speed_mult = 0.25",
        f"{modifier}: character travel speed",
    )
    files["common/traits/invasions_traits.txt"] = patch_traits()
    files["common/governments/zz_wight_government.txt"] = patch_government()
    files["common/scripted_rules/00_rules.txt"] = patch_rules()
    files["common/culture/cultures/00_other_culture.txt"] = patch_culture()
    files["history/characters/othersinvasion_characters.txt"] = patch_history()
    files["gfx/models/portraits/m_clothes/other_armor/male_clothes_others_armor.asset"] = patch_armor_asset()
    portrait_modifiers = "gfx/portraits/portrait_modifiers/ln_others_portrait_modifiers.txt"
    files[portrait_modifiers] = read_source(LONG_NIGHT / portrait_modifiers)
    background_event = "events/others_events/others_events.txt"
    files[background_event] = replace_exact(
        files[background_event],
        "reference = agot_dragon_forest_clearing",
        "reference = wilderness_forest",
        f"{background_event}: current event background",
    )
    files["gui/event_windows/ln_topleft_wall_event.gui"] = patch_gui()
    coa = "common/coat_of_arms/coat_of_arms/ek2sauron_coa.txt"
    files[coa] = replace_regex(
        read_source(LONG_NIGHT / coa),
        r"(?m)^\s*custom\s*=\s*yes\s*\r?\n",
        "",
        f"{coa}: removed custom field",
    )
    names = "common/culture/name_lists/00_othernames.txt"
    files[names] = replace_regex(
        read_source(LONG_NIGHT / names),
        r"(?m)^(\s*)Other\s*$",
        r"\1other_name",
        f"{names}: localized Other names",
        2,
    )
    files["localization/english/theothers_l_english.yml"] = patch_theothers_localization()
    dynasty_loc = "localization/english/dynasties/otherdynasty_names_l_english.yml"
    files[dynasty_loc] = read_source(LONG_NIGHT / dynasty_loc)
    wall_loc = "localization/english/long_night_plus_wall_events_l_english.yml"
    files[wall_loc] = read_source(LONG_NIGHT / wall_loc)
    files["localization/english/agot_long_night_compatch_l_english.yml"] = compatch_localization()
    return files


def write_atomic(path: Path, content: str) -> bool:
    encoded = codecs.BOM_UTF8 + content.encode("utf-8")
    if path.is_file() and path.read_bytes() == encoded:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", prefix=f".{path.name}.", dir=path.parent, delete=False
        ) as handle:
            handle.write(encoded)
            temporary = Path(handle.name)
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
    return True


def write_bytes_atomic(path: Path, content: bytes) -> bool:
    if path.is_file() and path.read_bytes() == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", prefix=f".{path.name}.", dir=path.parent, delete=False
        ) as handle:
            handle.write(content)
            temporary = Path(handle.name)
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail when the generated animation payload is not current",
    )
    arguments = parser.parse_args()

    if not (AGOT / "descriptor.mod").is_file():
        raise SystemExit(f"missing required AGOT dependency: {AGOT}")
    if not (STANDALONE_LONG_NIGHT / "descriptor.mod").is_file():
        raise SystemExit(
            f"missing generated standalone Long Night: {STANDALONE_LONG_NIGHT}"
        )
    destination = MOD_OUTPUT_ROOT / RELATIVE_ANIMATIONS
    generated = codecs.BOM_UTF8 + generate().encode("utf-8")
    current = destination.read_bytes() if destination.is_file() else None
    changed = current != generated
    if arguments.check:
        if changed:
            raise SystemExit(f"generated payload is stale: {destination}")
    else:
        write_bytes_atomic(destination, generated)

    print(
        f"{'checked' if arguments.check else 'generated'} the animation-only "
        f"DFP compatibility payload in "
        f"{MOD_OUTPUT_ROOT.relative_to(ROOT)}; changed {int(changed)} file "
        f"({EXPECTED_MERGED_POSES} DFP poses, {EXPECTED_WIGHT_POSES} wight "
        "poses, 1 Submod Core bow pose)"
    )


if __name__ == "__main__":
    try:
        main()
    except ValueError as error:
        raise SystemExit(f"cannot regenerate compatch: {error}") from error
