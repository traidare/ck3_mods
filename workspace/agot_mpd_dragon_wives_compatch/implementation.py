#!/usr/bin/env python3
"""Carry More Personality Depth's character-window deltas onto Dragon Wives'."""

from __future__ import annotations

from gen import GenerationContext
from gen.script import read_text, write_text
from gen.text import replace_exact

WINDOW_RELATIVE = "gui/window_character.gui"

# Dragon Wives and More Personality Depth both fork AGOT's character window at
# the same two places, so each delta is lifted out of MPD's file by its
# surrounding anchors rather than restated here.
HUD_ANCHOR = (
    "\t\ton_start = \"[GetVariableSystem.Clear( 'hide_bottom_left_HUD' )]\"\n\t}\n\n"
)
MAIN_CONTENT_ANCHOR = '\tvbox = {\n\t\tname = "main_content"\n'
PERSONALITY_ANCHOR = '\t\t\t\tname = "ai_personality"\n'
PERSONALITY_END = '\n\t\t\t\traw_text = " • #L [Character.GetAIPersonalityNoTooltip]#!"'
STALE_FAKE_DEATH_WIDGET = "\tagot_fake_death_character_view = {}\n"

# Replacing these is the whole point of Dragon Wives, so they are the only lines
# of AGOT's window it is allowed to be missing.
DRAGON_WIVES_REPLACED = frozenset(
    {
        "visible = \"[GreaterThan_int32( Character.GetMaxSpouses, '(int32)1' )]\"",
        'visible = "[Not(Or(GreaterThan_int32( Character.GetMaxSpouses, '
        "'(int32)1' ), GreaterThan_int32( Character.GetMaxConsorts, "
        "'(int32)0' )))]\"",
        'visible = "[Or(GreaterThan_int32( Character.GetMaxSpouses, '
        "'(int32)1' ), GreaterThan_int32( Character.GetMaxConsorts, "
        "'(int32)0' ))]\"",
    }
)


def span_between(text: str, start: str, end: str, *, label: str) -> str:
    """Return the text an upstream file holds between two unique anchors."""
    for anchor in (start, end):
        if text.count(anchor) != 1:
            raise RuntimeError(
                f"{label}: expected one occurrence of {anchor.strip()!r}, "
                f"found {text.count(anchor)}"
            )
    opening = text.index(start) + len(start)
    closing = text.index(end)
    if closing <= opening:
        raise RuntimeError(f"{label}: anchors are out of order")
    return text[opening:closing]


def require_dragon_wives_current(agot: str, dragon_wives: str) -> None:
    """Fail when Dragon Wives no longer carries AGOT's GUI statements."""

    def statements(text: str) -> set[str]:
        return {
            line.strip()
            for line in text.split("\n")
            if line.strip() and not line.lstrip().startswith("#")
        }

    missing = statements(agot) - statements(dragon_wives) - DRAGON_WIVES_REPLACED
    if missing:
        raise RuntimeError(
            "Dragon Wives' character window is missing "
            f"{len(missing)} AGOT line(s) beyond the spouse-slot tests it "
            f"replaces, starting with {sorted(missing)[0]!r}"
        )


def generate_window_character(agot: str, dragon_wives: str, mpd: str) -> str:
    """Show Dragon Wives' spouse rows with MPD's personality roller and display."""
    require_dragon_wives_current(agot, dragon_wives)
    dragon_wives = replace_exact(
        dragon_wives,
        STALE_FAKE_DEATH_WIDGET,
        "",
        "Dragon Wives stale fake-death widget",
    )

    view_hook = span_between(
        mpd, HUD_ANCHOR, MAIN_CONTENT_ANCHOR, label="MPD view-hook widget"
    )
    if 'name = "mpd_view_hook"' not in view_hook:
        raise RuntimeError("MPD no longer places its view-hook widget on the window")
    text = replace_exact(
        dragon_wives,
        HUD_ANCHOR + MAIN_CONTENT_ANCHOR,
        HUD_ANCHOR + view_hook + MAIN_CONTENT_ANCHOR,
        "Dragon Wives character window view-hook",
    )

    personality = "MPD personality visibility"
    return replace_exact(
        text,
        PERSONALITY_ANCHOR
        + span_between(
            dragon_wives, PERSONALITY_ANCHOR, PERSONALITY_END, label=personality
        ),
        PERSONALITY_ANCHOR
        + span_between(mpd, PERSONALITY_ANCHOR, PERSONALITY_END, label=personality),
        "Dragon Wives character window personality display",
    )


def generate(context: GenerationContext) -> None:
    write_text(
        context.output_root,
        WINDOW_RELATIVE,
        generate_window_character(
            read_text(context.source("agot") / WINDOW_RELATIVE),
            read_text(context.source("dragon-wives") / WINDOW_RELATIVE),
            read_text(context.source("more-personality-depth") / WINDOW_RELATIVE),
        ),
        with_bom=False,
    )
