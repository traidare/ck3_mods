#!/usr/bin/env python3
"""Generate the VIET 1.3.0 + AGOT runtime rebase from Workshop sources."""

from __future__ import annotations

import re
from pathlib import Path

from ck3mm.generation import GenerationContext
from ck3mm.generators.text import read_source

ROOT: Path | None = None
SOURCE: Path | None = None
OUTPUT: Path | None = None
DISABLED_EVENTS_FILE: Path | None = None

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

DUPLICATE_WIDGET_EVENTS = {
    "VIETmisc.2080",
    "VIETmisc.2081",
}

TOAST_RANDOM_LIST_EVENTS = {
    "VIETmisc.0033",
    "VIETmisc.0088",
}

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


def read_text(path: Path) -> str:
    return read_source(path, normalize_newlines=True)


def write_text(relative: str, text: str) -> None:
    target = OUTPUT / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8-sig", newline="")


def disabled_events() -> set[str]:
    events = {
        line.strip()
        for line in read_text(DISABLED_EVENTS_FILE).splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    if len(events) != 151:
        raise RuntimeError(f"expected 151 disabled VIET events, found {len(events)}")
    return events


def brace_delta(line: str) -> int:
    """Count structural braces, ignoring comments and quoted strings."""
    delta = 0
    quoted = False
    escaped = False
    for char in line:
        if escaped:
            escaped = False
            continue
        if char == "\\" and quoted:
            escaped = True
            continue
        if char == '"':
            quoted = not quoted
            continue
        if char == "#" and not quoted:
            break
        if quoted:
            continue
        if char == "{":
            delta += 1
        elif char == "}":
            delta -= 1
    return delta


def block_end(lines: list[str], start: int) -> int:
    depth = 0
    for index in range(start, len(lines)):
        depth += brace_delta(lines[index])
        if depth == 0:
            return index + 1
    raise RuntimeError(f"unterminated block beginning at line {start + 1}")


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
        end = block_end(lines, index)
        toast = lines[index:end]
        depth = brace_delta(toast[0])
        random_start = None
        for toast_index in range(1, len(toast)):
            if depth == 1 and random_pattern.match(toast[toast_index]):
                random_start = toast_index
                break
            depth += brace_delta(toast[toast_index])
        if random_start is None:
            output.extend(toast)
            index = end
            continue
        random_end = block_end(toast, random_start)
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
    relative: str, disabled: set[str], found: set[str]
) -> tuple[int, int, int, int, int, int, int]:
    lines = read_text(SOURCE / relative).splitlines(keepends=True)
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
        end = block_end(lines, index)
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
        write_text(relative, output_text)
    return (
        replaced,
        owner_patches,
        animation_patches,
        character_scope_patches,
        widget_patches,
        else_patches,
        toast_random_list_patches,
    )


def remove_disabled_on_action_entries(relative: str, disabled: set[str]) -> int:
    text = read_text(SOURCE / relative)
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
        write_text(relative, "".join(output))
    return removed


def replace_named_blocks(source_relative: str, replacements: dict[str, str]) -> int:
    lines = read_text(SOURCE / source_relative).splitlines(keepends=True)
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
        end = block_end(lines, index)
        output.append(replacements[key])
        found.add(key)
        index = end
    missing = set(replacements) - found
    if missing:
        raise RuntimeError(
            f"{source_relative}: missing replacement blocks: {sorted(missing)}"
        )
    write_text(source_relative, "".join(output))
    return len(found)


def main() -> None:
    if not SOURCE.is_dir():
        raise RuntimeError(f"VIET Workshop source is unavailable: {SOURCE}")

    disabled = disabled_events()
    found: set[str] = set()
    event_results = {
        relative: replace_disabled_events(relative, disabled, found)
        for relative in EVENT_FILES
    }
    missing = disabled - found
    if missing:
        raise RuntimeError(f"disabled event definitions not found: {sorted(missing)}")

    on_action_counts = {
        relative: remove_disabled_on_action_entries(relative, disabled)
        for relative in ON_ACTION_FILES
    }
    custom_count = replace_named_blocks(
        "common/customizable_localization/VIET_customizable_localization_misc.txt",
        CUSTOM_LOC_REPLACEMENTS,
    )
    background_count = replace_named_blocks(
        "common/event_backgrounds/VIET_event_backgrounds.txt",
        BACKGROUND_REPLACEMENTS,
    )

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


def generate(context: GenerationContext) -> None:
    global SOURCE, OUTPUT, DISABLED_EVENTS_FILE
    SOURCE = context.source("viet")
    OUTPUT = context.output_root
    DISABLED_EVENTS_FILE = context.assets_dir / "disabled-events.txt"
    main()
