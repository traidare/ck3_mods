#!/usr/bin/env python3
"""Generate the VIET 1.3.0 + AGOT runtime rebase from Workshop sources."""

from __future__ import annotations

import hashlib
import re

from gen import GenerationContext
from gen.script import read_text, write_text
from gen.text import direct_child_block_start, line_block_end

EVENT_KEY_RE = re.compile(r"^(VIET[A-Za-z]*\.\d+)\s*=\s*\{")
EVENT_TYPE_RE = re.compile(r"^\s*type\s*=\s*([a-z0-9_]+)\s*(?:#.*)?$", re.MULTILINE)
EVENT_SCOPE_RE = re.compile(r"^\s*scope\s*=\s*([a-z0-9_]+)\s*(?:#.*)?$", re.MULTILINE)

OWNER_SCOPE_EVENTS = {
    "VIETmisc.5030",
    "VIETmisc.5032",
    "VIETmisc.5039",
    "VIETmisc.5059",
}

CHARACTER_PING_EVENTS = {
    "VIETmisc.2032",
    "VIETmisc.2035",
    "VIETmonogatari.0002",
    "VIETmonogatari.0004",
}

DUPLICATE_WIDGET_EVENTS = {"VIETmisc.2080", "VIETmisc.2081"}

TOAST_RANDOM_LIST_EVENTS = {"VIETmisc.0033", "VIETmisc.0088"}

ANIMATION_REPLACEMENTS = {
    "worried": "worry",
    "schaudenfreude": "schadenfreude",
    "throne_room_conversation": "throne_room_conversation_1",
    "personality_charitable": "personality_compassionate",
    "peresonality_zealous": "personality_zealous",
}

EVENT_FILES = (
    "events/VIET_events_artifacts.txt",
    "events/VIET_events_basic.txt",
    "events/VIET_events_basic_2.txt",
    "events/VIET_events_chains.txt",
    "events/VIET_events_county.txt",
    "events/VIET_events_county_old.txt",
    "events/VIET_events_court.txt",
    "events/VIET_events_decisions.txt",
    "events/VIET_events_old.txt",
    "events/VIET_events_older.txt",
    "events/VIET_events_oldest.txt",
    "events/VIET_events_qi_ma.txt",
    "events/VIET_events_setup.txt",
    "events/VIET_events_travel.txt",
)

ON_ACTION_FILES = (
    "common/on_action/VIET_court_events_on_actions.txt",
    "common/on_action/VIET_on_actions.txt",
    "common/on_action/VIET_travel_on_actions.txt",
)

CUSTOM_LOC_REPLACEMENTS = {
    "VIET_old_cactus_name": """VIET_old_cactus_name = {
\ttype = character
\ttext = {
\t\tlocalization_key = VIET_old_world_cactus_name_sri_lanka
\t\tfallback = yes
\t}
}
""",
    "VIET_dumpling_name": """VIET_dumpling_name = {
\ttype = character
\ttext = {
\t\tlocalization_key = VIET_dumpling_name_generic
\t\tfallback = yes
\t}
}
""",
    "VIET_random_fruit": """VIET_random_fruit = {
\ttype = character
\ttext = {
\t\tlocalization_key = VIET_cherry
\t\tfallback = yes
\t}
}
""",
}

BACKGROUND_REPLACEMENTS = {
    "VIET_background_tuscan_country": """VIET_background_tuscan_country = {
\tbackground = {
\t\treference = "gfx/interface/illustrations/event_scenes/VIET_tuscan_country.dds"
\t\tenvironment = "environment_event_garden"
\t\tambience = "event:/SFX/Events/Backgrounds/castle_garden_day"
\t}
}
""",
    "VIET_background_ancient_cairn": """VIET_background_ancient_cairn = {
\tbackground = {
\t\treference = "gfx/interface/illustrations/event_scenes/VIET_ancient_cairn.dds"
\t\tenvironment = "environment_event_forest"
\t\tambience = "event:/SFX/Events/Backgrounds/deciduous_forest_day"
\t}
}
""",
    "VIET_background_small_town": """VIET_background_small_town = {
\tbackground = {
\t\treference = "gfx/interface/illustrations/event_scenes/VIET_small_town.dds"
\t\tenvironment = "environment_event_garden"
\t\tambience = "event:/SFX/Events/Backgrounds/townmarket_western_day"
\t}
}
""",
    "VIET_background_skyrim_forest": """VIET_background_skyrim_forest = {
\tbackground = {
\t\treference = "gfx/interface/illustrations/event_scenes/VIET_skyrim_forest.dds"
\t\tenvironment = "environment_event_forest_pine"
\t\tambience = "event:/SFX/Events/Backgrounds/coniferous_forest_day"
\t}
}
""",
}


DATABASE_TRIGGER_HASHES = {
    "VIET_is_baklava_culture_trigger": "8127ca4b2bd49a31ce71cf69aba2d1427d2e95fb7c8212d6740ebe4357b39f6b",
    "VIET_norse_localization_trigger": "aa14f3e03d959c2aacf4d72f0918764c348c9cc1deb559e3c5ddce53765f875f",
    "VIET_is_sinosphere_trigger": "72639b18b05c9590fc13b5bf2bc602c27f53bd78c54425966013f9d35be90b62",
    "VIET_is_lesser_sinosphere_culture_trigger": "39407a442fdbc346aa6c91ed4b87d3615144d8434d221615edfdfe3bb99ff46b",
    "VIET_is_in_broccoli_region_trigger": "f895ea67f3ddd0401bdec8854eb78d3fad287969001bbde2357254077396c0b3",
    "VIET_is_hummus_culture_trigger": "6d7fc2f65d293a24ce2699ad0af55c11877374247f2e793a86884282c11215c5",
    "VIET_indian_or_in_india_trigger": "3697f5fa06aaaec7cc56f32c93612600daf6af7a06a6584316bd5098e8229bb5",
    "VIET_is_henna_culture_trigger": "cbd5daa918762dddfed0c399073c311fa01311918c59d5cd64f249a83ed10ab3",
    "VIET_is_redhead_or_blonde_area_or_culture": "f530ff3739d3b42b0a3158918f5a74a817b8244baf2d8b208cf64650897bde37",
    "VIET_is_redhead_or_blonde_area_capital": "d47fddf800686312276f264553554edf9297542d3218c8a57683832b88eb8480",
    "VIET_is_in_coconut_region_trigger": "5e68c55d6bd10256014bdbcdb8965ad32713dc671671204b24ac7bd7610a0bb1",
    "VIET_is_in_coconut_octopus_region_trigger": "dad12579ea35854ca42128d67862b320220b7085809ef634de69451fe670be0d",
    "VIET_is_in_wild_strawberry_region_trigger": "ad5b29d3831a746e14da67efec86e3da3fc57362f8b3ae035004ae493b34d255",
    "VIET_is_sinosphere_religion_trigger": "bcad07d712edb9fc3c525d80f704fce9ed38c72004804a57387a5bfa7e6f6c89",
    "VIET_fish_sauce_culture": "d3b6674bd6177c28d8b01717201e58e9bb9fe6f2af04751d2da083fba6c67010",
    "VIET_is_byzantine_or_roman_trigger": "8e192d07fa2b9bfd1462619dc7af2ffec9a6c6a97e3d98657f5bd7bbcdcce062",
    "VIET_anatolian_or_near_east_turkish": "ebcca090c04abc57abaf306bf9e31b33110ee7571099005eb9db0f7f897eacd2",
}

DATABASE_TRIGGER_REPLACEMENTS = {
    "VIET_is_baklava_culture_trigger": """VIET_is_baklava_culture_trigger = {
\tculture_has_west_asian_heritage_pillar_trigger = yes
}
""",
    "VIET_norse_localization_trigger": """VIET_norse_localization_trigger = {
\tculture = { has_cultural_pillar = heritage_ironman }
}
""",
    "VIET_is_sinosphere_trigger": """VIET_is_sinosphere_trigger = {
\tOR = {
\t\tculture_has_east_asian_heritage_pillar_trigger = yes
\t\tculture_has_southeast_asian_heritage_pillar_trigger = yes
\t\tculture_has_central_asian_heritage_pillar_trigger = yes
\t}
}
""",
    "VIET_is_lesser_sinosphere_culture_trigger": """VIET_is_lesser_sinosphere_culture_trigger = {
\tOR = {
\t\tculture_has_east_asian_heritage_pillar_trigger = yes
\t\tculture_has_southeast_asian_heritage_pillar_trigger = yes
\t}
}
""",
    "VIET_is_in_broccoli_region_trigger": """VIET_is_in_broccoli_region_trigger = {
\talways = no
}
""",
    "VIET_is_hummus_culture_trigger": """VIET_is_hummus_culture_trigger = {
\tculture_has_west_asian_heritage_pillar_trigger = yes
}
""",
    "VIET_indian_or_in_india_trigger": """VIET_indian_or_in_india_trigger = {
\talways = no
}
""",
    "VIET_is_henna_culture_trigger": """VIET_is_henna_culture_trigger = {
\tOR = {
\t\tculture_has_west_asian_heritage_pillar_trigger = yes
\t\tculture_has_mena_heritage_pillar_trigger = yes
\t\tculture_has_east_african_heritage_pillar_trigger = yes
\t}
}
""",
    "VIET_is_redhead_or_blonde_area_or_culture": """VIET_is_redhead_or_blonde_area_or_culture = {
\talways = no
}
""",
    "VIET_is_redhead_or_blonde_area_capital": """VIET_is_redhead_or_blonde_area_capital = {
\talways = no
}
""",
    "VIET_is_in_coconut_region_trigger": """VIET_is_in_coconut_region_trigger = {
\talways = no
}
""",
    "VIET_is_in_coconut_octopus_region_trigger": """VIET_is_in_coconut_octopus_region_trigger = {
\talways = no
}
""",
    "VIET_is_in_wild_strawberry_region_trigger": """VIET_is_in_wild_strawberry_region_trigger = {
\talways = no
}
""",
    "VIET_is_sinosphere_religion_trigger": """VIET_is_sinosphere_religion_trigger = {
\talways = no
}
""",
    "VIET_fish_sauce_culture": """VIET_fish_sauce_culture = {
\tOR = {
\t\tculture_has_east_asian_heritage_pillar_trigger = yes
\t\tculture_has_southeast_asian_heritage_pillar_trigger = yes
\t}
}
""",
    "VIET_is_byzantine_or_roman_trigger": """VIET_is_byzantine_or_roman_trigger = {
\talways = no
}
""",
    "VIET_anatolian_or_near_east_turkish": """VIET_anatolian_or_near_east_turkish = {
\talways = no
}
""",
}

DATABASE_DECISION_HASHES = {
    "VIET_decision_venerate_a_mummified_hermit": "b2d8a8806330b08a79f086cbb448880c9a9a0111c6215d05d93805fbde3e9200",
    "VIET_decision_drink_shadowbanish_wine": "2831e3198b9761039eacaff95c515474009573e0f0e061b79dc9a08eaa168753",
    "VIET_decision_destroy_shadowbanish_wine": "906c2056298c4c134595c70790d1add74ec7212bc7983959b4f951dfec0ca700",
}

DATABASE_DECISION_REPLACEMENTS = {
    "VIET_decision_venerate_a_mummified_hermit": """VIET_decision_venerate_a_mummified_hermit = {
\tpicture = { reference = "gfx/interface/illustrations/decisions/decision_viet_buddhist_monk.dds" }
\tdecision_group_type = VIET_everyday
\tdesc = VIET_decision_venerate_a_mummified_hermit_desc
\tis_shown = { always = no }
}
""",
    "VIET_decision_drink_shadowbanish_wine": """VIET_decision_drink_shadowbanish_wine = {
\tpicture = { reference = "gfx/interface/illustrations/decisions/decision_viet_wine.dds" }
\tdecision_group_type = VIET_rare
\tdesc = VIET_decision_drink_shadowbanish_wine_desc
\tis_shown = { always = no }
}
""",
    "VIET_decision_destroy_shadowbanish_wine": """VIET_decision_destroy_shadowbanish_wine = {
\tpicture = { reference = "gfx/interface/illustrations/decisions/decision_viet_wine.dds" }
\tdecision_group_type = VIET_rare
\tdesc = VIET_decision_destroy_shadowbanish_wine_desc
\tis_shown = { always = no }
}
""",
}

AGOT_HERITAGE_TRIGGERS = """# Generated AGOT compatibility helpers for VIET's broad culture categories.

culture_has_asian_heritage_pillar_trigger = {
\tOR = {
\t\tculture_has_east_asian_heritage_pillar_trigger = yes
\t\tculture_has_west_asian_heritage_pillar_trigger = yes
\t\tculture_has_southeast_asian_heritage_pillar_trigger = yes
\t\tculture_has_central_asian_heritage_pillar_trigger = yes
\t}
}

culture_has_east_asian_heritage_pillar_trigger = {
\tculture = {
\t\tOR = {
\t\t\thas_cultural_pillar = heritage_yitish
\t\t\thas_cultural_pillar = heritage_nghai
\t\t}
\t}
}

culture_has_west_asian_heritage_pillar_trigger = {
\tculture = {
\t\tOR = {
\t\t\thas_cultural_pillar = heritage_grasslands
\t\t\thas_cultural_pillar = heritage_hyrkoonan
\t\t\thas_cultural_pillar = heritage_qaathi
\t\t\thas_cultural_pillar = heritage_sarnori
\t\t\thas_cultural_pillar = heritage_shadowlanders
\t\t}
\t}
}

culture_has_southeast_asian_heritage_pillar_trigger = {
\tculture = { has_cultural_pillar = heritage_jadeislands }
}

culture_has_central_asian_heritage_pillar_trigger = {
\tculture = {
\t\tOR = {
\t\t\thas_cultural_pillar = heritage_grasslands
\t\t\thas_cultural_pillar = heritage_hyrkoonan
\t\t\thas_cultural_pillar = heritage_nghai
\t\t\thas_cultural_pillar = heritage_sarnori
\t\t}
\t}
}

culture_has_central_african_heritage_pillar_trigger = {
\tculture = { has_cultural_pillar = heritage_sothoryi }
}

culture_has_east_african_heritage_pillar_trigger = {
\tculture = {
\t\tOR = {
\t\t\thas_cultural_pillar = heritage_moraqi
\t\t\thas_cultural_pillar = heritage_sothoryi
\t\t\thas_cultural_pillar = heritage_summer
\t\t}
\t}
}

culture_has_north_african_heritage_pillar_trigger = {
\tculture = {
\t\tOR = {
\t\t\thas_cultural_pillar = heritage_ghiscari
\t\t\thas_cultural_pillar = heritage_moraqi
\t\t}
\t}
}

culture_has_mena_heritage_pillar_trigger = {
\tculture = {
\t\tOR = {
\t\t\thas_cultural_pillar = heritage_freecities
\t\t\thas_cultural_pillar = heritage_ghiscari
\t\t\thas_cultural_pillar = heritage_qaathi
\t\t\thas_cultural_pillar = heritage_rhoynar
\t\t\thas_cultural_pillar = heritage_shadowlanders
\t\t\thas_cultural_pillar = heritage_valyrian
\t\t}
\t}
}

culture_has_european_heritage_pillar_trigger = {
\tculture = {
\t\tOR = {
\t\t\thas_cultural_pillar = heritage_andal
\t\t\thas_cultural_pillar = heritage_first_man
\t\t\thas_cultural_pillar = heritage_ironman
\t\t\thas_cultural_pillar = heritage_wildling
\t\t}
\t}
}

culture_has_east_european_heritage_pillar_trigger = {
\talways = no
}

culture_has_central_european_heritage_pillar_trigger = {
\tculture = { has_cultural_pillar = heritage_andal }
}

culture_has_south_european_heritage_pillar_trigger = {
\tculture = {
\t\tOR = {
\t\t\thas_cultural_pillar = heritage_andal
\t\t\thas_cultural_pillar = heritage_freecities
\t\t\thas_cultural_pillar = heritage_rhoynar
\t\t\thas_cultural_pillar = heritage_valyrian
\t\t}
\t}
}

culture_has_north_european_heritage_pillar_trigger = {
\tculture = {
\t\tOR = {
\t\t\thas_cultural_pillar = heritage_first_man
\t\t\thas_cultural_pillar = heritage_ironman
\t\t\thas_cultural_pillar = heritage_wildling
\t\t}
\t}
}

# Christianity does not exist in AGOT. Incompatible VIET events are stubbed.
is_christian_trigger = {
\talways = no
}
"""

OPTIONAL_ETHNICITIES_EFFECT = """# Optional VIET compatibility hook for Ethnicities & Portraits Expanded.
# That mod is absent from this playset; keep the symbol valid and inert.
ek_character_setup_effect = {
\tif = {
\t\tlimit = { always = no }
\t\tadd_prestige = 0
\t}
}
"""


def disabled_events(context: GenerationContext) -> set[str]:
    events = {
        line.strip()
        for line in read_text(context.assets_dir / "disabled-events.txt").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    if len(events) != 151:
        raise RuntimeError(f"expected 151 disabled VIET events, found {len(events)}")
    return events


def event_stub(event_id: str, block: str) -> str:
    event_type = EVENT_TYPE_RE.search(block)
    event_scope = EVENT_SCOPE_RE.search(block)
    if event_type:
        scope_line = f"\ttype = {event_type.group(1)}"
    elif event_scope:
        scope_line = f"\tscope = {event_scope.group(1)}"
    else:
        raise RuntimeError(f"cannot determine event type/scope for {event_id}")
    return (
        f"{event_id} = {{\n"
        f"{scope_line}\n"
        "\thidden = yes\n"
        "\ttrigger = { always = no }\n"
        "}\n"
    )


def add_artifact_owner_scope(event_id: str, block: str) -> str:
    pattern = re.compile(r"^(\s*)immediate\s*=\s*\{\s*$", re.MULTILINE)
    match = pattern.search(block)
    if not match:
        raise RuntimeError(f"{event_id}: immediate block not found")
    indent = match.group(1) + "\t"
    insertion = match.group(0) + f"\n{indent}root = {{ save_scope_as = owner }}"
    patched = block[: match.start()] + insertion + block[match.end() :]
    if "get_artifact_feature_references_effect = yes" not in patched:
        raise RuntimeError(f"{event_id}: artifact feature-reference call not found")
    return patched


def repair_character_ping_scope(event_id: str, block: str) -> str:
    pattern = re.compile(r"^(\s*)scope\s*=\s*none\s*(?:#.*)?$", re.MULTILINE)
    patched, replacements = pattern.subn(r"\1type = character_event", block, count=1)
    if replacements != 1:
        raise RuntimeError(
            f"{event_id}: expected one 'scope = none' declaration, "
            f"replaced {replacements}"
        )
    return patched


def remove_duplicate_widget(event_id: str, block: str) -> str:
    pattern = re.compile(
        r"^[ \t]*widget\s*=\s*\{\s*"
        r"gui\s*=\s*event_window_widget_vfx_snow\s+"
        r"container\s*=\s*foreground_shader_vfx_container\s*"
        r"\}\s*\r?\n",
        re.MULTILINE,
    )
    patched, replacements = pattern.subn("", block, count=1)
    if replacements != 1:
        raise RuntimeError(
            f"{event_id}: expected one redundant inline widget, removed {replacements}"
        )
    if len(re.findall(r"^[ \t]*widget\s*=", patched, re.MULTILINE)) != 1:
        raise RuntimeError(f"{event_id}: expected one structured widget after repair")
    return patched


def move_random_lists_out_of_toasts(event_id: str, block: str) -> tuple[str, int]:
    lines = block.splitlines(keepends=True)
    output: list[str] = []
    index = 0
    moved = 0
    toast_pattern = re.compile(r"^[ \t]*send_interface_toast\s*=\s*\{")
    random_pattern = re.compile(r"^[ \t]*random_list\s*=\s*\{")
    while index < len(lines):
        if not toast_pattern.match(lines[index]):
            output.append(lines[index])
            index += 1
            continue
        end = line_block_end(lines, index)
        toast = lines[index:end]
        random_start = direct_child_block_start(toast, 0, random_pattern)
        if random_start is None:
            output.extend(toast)
            index = end
            continue
        random_end = line_block_end(toast, random_start)
        random_block = toast[random_start:random_end]
        output.extend(toast[:random_start])
        output.extend(toast[random_end:])
        for line in random_block:
            if not line.startswith("\t"):
                raise RuntimeError(
                    f"{event_id}: cannot dedent toast random_list line: {line!r}"
                )
            output.append(line[1:])
        moved += 1
        index = end
    return "".join(output), moved


def repair_missing_limit_else(relative: str, text: str) -> tuple[str, int]:
    if relative != "events/VIET_events_oldest.txt":
        return text, 0
    pattern = re.compile(
        r"^(?P<indent>[ \t]*)else_if(?P<suffix>[ \t]*=[ \t]*\{\r?\n"
        r"[ \t]*VIET_(?:small|medium|large|huge|massive)_piety_gain_effect"
        r"[ \t]*=[ \t]*yes)",
        re.MULTILINE,
    )
    patched, replacements = pattern.subn(r"\g<indent>else\g<suffix>", text)
    if replacements != 6:
        raise RuntimeError(
            f"{relative}: expected six limit-less else_if fallbacks, "
            f"repaired {replacements}"
        )
    return patched, replacements


def repair_animation_names(text: str) -> tuple[str, int]:
    count = 0
    for old, new in ANIMATION_REPLACEMENTS.items():
        pattern = re.compile(rf"(\banimation\s*=\s*){re.escape(old)}\b")
        text, replacements = pattern.subn(rf"\g<1>{new}", text)
        count += replacements
    return text, count


def replace_disabled_events(
    context: GenerationContext, relative: str, disabled: set[str], found: set[str]
) -> tuple[int, int, int, int, int, int, int]:
    lines = read_text(context.source("viet") / relative).splitlines(keepends=True)
    output: list[str] = []
    index = 0
    replaced = 0
    owner_patches = 0
    character_scope_patches = 0
    widget_patches = 0
    toast_random_list_patches = 0
    while index < len(lines):
        match = EVENT_KEY_RE.match(lines[index])
        if not match:
            output.append(lines[index])
            index += 1
            continue
        event_id = match.group(1)
        if (
            event_id not in disabled
            and event_id not in OWNER_SCOPE_EVENTS
            and event_id not in CHARACTER_PING_EVENTS
            and event_id not in DUPLICATE_WIDGET_EVENTS
            and event_id not in TOAST_RANDOM_LIST_EVENTS
        ):
            output.append(lines[index])
            index += 1
            continue
        end = line_block_end(lines, index)
        block = "".join(lines[index:end])
        if event_id in disabled:
            output.append(event_stub(event_id, block))
            found.add(event_id)
            replaced += 1
        else:
            if event_id in OWNER_SCOPE_EVENTS:
                block = add_artifact_owner_scope(event_id, block)
                owner_patches += 1
            if event_id in CHARACTER_PING_EVENTS:
                block = repair_character_ping_scope(event_id, block)
                character_scope_patches += 1
            if event_id in DUPLICATE_WIDGET_EVENTS:
                block = remove_duplicate_widget(event_id, block)
                widget_patches += 1
            if event_id in TOAST_RANDOM_LIST_EVENTS:
                block, moved = move_random_lists_out_of_toasts(event_id, block)
                toast_random_list_patches += moved
            output.append(block)
        index = end
    output_text, else_patches = repair_missing_limit_else(relative, "".join(output))
    output_text, animation_patches = repair_animation_names(output_text)
    if (
        replaced
        or owner_patches
        or character_scope_patches
        or widget_patches
        or toast_random_list_patches
        or else_patches
        or animation_patches
    ):
        write_text(
            context.output_root,
            relative,
            output_text,
            preserve_trailing_whitespace=True,
        )
    return (
        replaced,
        owner_patches,
        animation_patches,
        character_scope_patches,
        widget_patches,
        else_patches,
        toast_random_list_patches,
    )


def remove_disabled_on_action_entries(
    context: GenerationContext, relative: str, disabled: set[str]
) -> int:
    text = read_text(context.source("viet") / relative)
    lines = text.splitlines(keepends=True)
    event_pattern = re.compile(r"^\s*\d+\s*=\s*(VIET[A-Za-z]*\.\d+)\s*(?:#.*)?$")
    output: list[str] = []
    removed = 0
    for line in lines:
        match = event_pattern.match(line.rstrip("\r\n"))
        if match and match.group(1) in disabled:
            removed += 1
            continue
        output.append(line)
    if removed:
        write_text(
            context.output_root,
            relative,
            "".join(output),
            preserve_trailing_whitespace=True,
        )
    return removed


def replace_named_blocks(
    context: GenerationContext, source_relative: str, replacements: dict[str, str]
) -> int:
    lines = read_text(context.source("viet") / source_relative).splitlines(
        keepends=True
    )
    key_pattern = re.compile(
        rf"^({'|'.join(re.escape(key) for key in replacements)})\s*=\s*\{{"
    )
    output: list[str] = []
    found: set[str] = set()
    index = 0
    while index < len(lines):
        match = key_pattern.match(lines[index])
        if not match:
            output.append(lines[index])
            index += 1
            continue
        key = match.group(1)
        end = line_block_end(lines, index)
        output.append(replacements[key])
        found.add(key)
        index = end
    missing = set(replacements) - found
    if missing:
        raise RuntimeError(
            f"{source_relative}: missing replacement blocks: {sorted(missing)}"
        )
    write_text(
        context.output_root,
        source_relative,
        "".join(output),
        preserve_trailing_whitespace=True,
    )
    return len(found)


def replace_pinned_named_blocks(
    context: GenerationContext,
    source_relative: str,
    replacements: dict[str, str],
    expected_hashes: dict[str, str],
) -> int:
    """Replace top-level blocks only after verifying their Workshop revisions."""
    if set(replacements) != set(expected_hashes):
        raise RuntimeError(
            f"{source_relative}: replacement and source-hash keys do not match"
        )

    lines = read_text(context.source("viet") / source_relative).splitlines(
        keepends=True
    )
    key_pattern = re.compile(
        rf"^({'|'.join(re.escape(key) for key in replacements)})\s*=\s*\{{"
    )
    output: list[str] = []
    found: set[str] = set()
    index = 0
    while index < len(lines):
        match = key_pattern.match(lines[index])
        if not match:
            output.append(lines[index])
            index += 1
            continue

        key = match.group(1)
        if key in found:
            raise RuntimeError(f"{source_relative}: duplicate block for {key}")
        end = line_block_end(lines, index)
        source_block = "".join(lines[index:end]).rstrip("\r\n")
        actual_hash = hashlib.sha256(source_block.encode("utf-8")).hexdigest()
        expected_hash = expected_hashes[key]
        if actual_hash != expected_hash:
            raise RuntimeError(
                f"{source_relative}: {key} source changed "
                f"(expected {expected_hash}, got {actual_hash})"
            )
        output.append(replacements[key])
        found.add(key)
        index = end

    missing = set(replacements) - found
    if missing:
        raise RuntimeError(
            f"{source_relative}: missing replacement blocks: {sorted(missing)}"
        )
    write_text(
        context.output_root,
        source_relative,
        "".join(output),
        preserve_trailing_whitespace=True,
    )
    return len(found)


def generate_database_compatibility(
    context: GenerationContext,
) -> tuple[int, int]:
    trigger_count = replace_pinned_named_blocks(
        context,
        "common/scripted_triggers/VIET_scripted_triggers.txt",
        DATABASE_TRIGGER_REPLACEMENTS,
        DATABASE_TRIGGER_HASHES,
    )
    county_decision_key = "VIET_decision_venerate_a_mummified_hermit"
    county_decision_count = replace_pinned_named_blocks(
        context,
        "common/decisions/VIET_county_decisions.txt",
        {county_decision_key: DATABASE_DECISION_REPLACEMENTS[county_decision_key]},
        {county_decision_key: DATABASE_DECISION_HASHES[county_decision_key]},
    )
    misc_decision_keys = (
        "VIET_decision_drink_shadowbanish_wine",
        "VIET_decision_destroy_shadowbanish_wine",
    )
    misc_decision_count = replace_pinned_named_blocks(
        context,
        "common/decisions/VIET_misc_decisions.txt",
        {key: DATABASE_DECISION_REPLACEMENTS[key] for key in misc_decision_keys},
        {key: DATABASE_DECISION_HASHES[key] for key in misc_decision_keys},
    )
    write_text(
        context.output_root,
        "common/scripted_triggers/zzz_viet_agot_heritage_triggers.txt",
        AGOT_HERITAGE_TRIGGERS,
        preserve_trailing_whitespace=True,
    )
    write_text(
        context.output_root,
        "common/scripted_effects/zzz_viet_agot_optional_effects.txt",
        OPTIONAL_ETHNICITIES_EFFECT,
        preserve_trailing_whitespace=True,
    )

    stale_database_tokens = (
        "heritage_byzantine",
        "heritage_turkic",
        "heritage_north_germanic",
        "heritage_chinese",
        "heritage_indo_aryan",
        "faith:",
        "religion = religion:",
        "culture = culture:",
        "geographical_region =",
        "title:e_byzantium",
        "title:h_roman_empire",
    )
    for relative in (
        "common/scripted_triggers/VIET_scripted_triggers.txt",
        "common/decisions/VIET_county_decisions.txt",
        "common/decisions/VIET_misc_decisions.txt",
    ):
        text = read_text(context.output_root / relative)
        stale = [token for token in stale_database_tokens if token in text]
        if stale:
            raise RuntimeError(
                f"{relative}: stale vanilla database references remain: {stale}"
            )

    return trigger_count, county_decision_count + misc_decision_count


def generate(context: GenerationContext) -> None:
    source = context.source("viet")
    if not source.is_dir():
        raise RuntimeError(f"VIET Workshop source is unavailable: {source}")

    disabled = disabled_events(context)
    found: set[str] = set()
    event_results = {
        relative: replace_disabled_events(context, relative, disabled, found)
        for relative in EVENT_FILES
    }
    missing = disabled - found
    if missing:
        raise RuntimeError(f"disabled event definitions not found: {sorted(missing)}")

    on_action_counts = {
        relative: remove_disabled_on_action_entries(context, relative, disabled)
        for relative in ON_ACTION_FILES
    }
    custom_count = replace_named_blocks(
        context,
        "common/customizable_localization/VIET_customizable_localization_misc.txt",
        CUSTOM_LOC_REPLACEMENTS,
    )
    background_count = replace_named_blocks(
        context,
        "common/event_backgrounds/VIET_event_backgrounds.txt",
        BACKGROUND_REPLACEMENTS,
    )
    trigger_count, decision_count = generate_database_compatibility(context)

    print(
        f"Stubbed {sum(result[0] for result in event_results.values())} "
        "incompatible VIET events"
    )
    for relative, result in event_results.items():
        count = result[0]
        if count:
            print(f"  {count:3d}  {relative}")
    print(
        f"Repaired {sum(result[1] for result in event_results.values())} "
        "artifact owner scopes"
    )
    print(
        f"Repaired {sum(result[2] for result in event_results.values())} "
        "invalid portrait-animation names"
    )
    print(
        f"Repaired {sum(result[3] for result in event_results.values())} "
        "character ping-event scopes"
    )
    print(
        f"Removed {sum(result[4] for result in event_results.values())} "
        "duplicate event widgets"
    )
    print(
        f"Repaired {sum(result[5] for result in event_results.values())} "
        "limit-less else_if fallbacks"
    )
    toast_random_list_count = sum(result[6] for result in event_results.values())
    if toast_random_list_count != 7:
        raise RuntimeError(
            "expected seven toast-nested random_list blocks, "
            f"repaired {toast_random_list_count}"
        )
    print(f"Moved {toast_random_list_count} random_list blocks out of interface toasts")
    print(f"Removed {sum(on_action_counts.values())} pulse entries")
    for relative, count in on_action_counts.items():
        if count:
            print(f"  {count:3d}  {relative}")
    print(f"Replaced {custom_count} customizable-localization selectors")
    print(f"Replaced {background_count} event-background selectors")
    print(f"Rebased {trigger_count} scripted triggers and {decision_count} decisions")
