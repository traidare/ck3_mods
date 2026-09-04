#!/usr/bin/env python3
"""Rebuild Build-a-Courtier's lobby buttons on top of AGOT's GUI.

Build-a-Courtier ships a whole-file override of ``gui/multiplayer_types.gui``
and loads after AGOT, so it silently drops both of AGOT's edits to that
file: the ``agot_create_landless_pirate_button`` call site, and the
government-type gate that keeps AGOT's ruins, unknown, and wilderness
characters out of the landless-adventurer designer.

So AGOT owns the file and Build-a-Courtier's delta is replayed onto it,
rather than the other way round.  Build-a-Courtier's own commenting-out of
the three vanilla buttons' ``visible``/``enabled`` gates is deliberately
*not* replayed: those gates are AGOT's, and one of them is AGOT-authored.

``gui/custom_gui/agot_multiplayer_types.gui`` is carried for one reason.
AGOT's pirate button opens the same ``landless_adventurer`` designer mode
Build-a-Courtier hooks, and that path runs
``create_landless_adventurer_title_effect``, so a designed pirate really
does reach ``on_ruler_designer_finished`` holding
``landless_adventurer_government``.  Build-a-Courtier clears its stale
intent flag on the three vanilla designer buttons; AGOT's pirate button is
a fourth one it cannot know about, so the same clear is added there.
"""

from __future__ import annotations

from codecs import BOM_UTF8
from dataclasses import dataclass

from gen import GenerationContext, GenerationError
from gen.text import newline_style, normalize_newlines, replace_exact

MULTIPLAYER_TYPES = "gui/multiplayer_types.gui"
AGOT_MULTIPLAYER_TYPES = "gui/custom_gui/agot_multiplayer_types.gui"

# Full-file pins, vanilla included: this merge is only reviewable when all
# three sides of it are known inputs.  A mismatch is the re-audit trigger.
# Build-a-Courtier's scripted GUI names.  Both live in the parent mod; this
# module only adds call sites, never redefines them.
CLEAR_INTENT = (
    "\"[GetScriptedGui('custom_courtier_clear_intent')"
    '.Execute( GuiScope.SetRoot( Character.MakeScope ).End )]"'
)
SET_INTENT = (
    "\"[GetScriptedGui('custom_courtier_set_intent')"
    '.Execute( GuiScope.SetRoot( Character.MakeScope ).End )]"'
)

# The three vanilla designer buttons Build-a-Courtier guards.  Each opens the
# Ruler Designer, so each must drop a stale intent flag first or a cancelled
# courtier session hijacks the next design.
VANILLA_DESIGNER_MODES = ("noble_family", "landless_adventurer", "default")

CLEAR_COMMENT = (
    "\t\t\t# Build-a-Courtier compatch: clear a possibly stale\n"
    "\t\t\t# courtier-intent flag before this designer session.\n"
)

# Narrow runtime repair.  Build-a-Courtier points both buttons at
# gfx/interface/icons/flat_icons/character.dds, which exists in neither
# vanilla, AGOT, nor Build-a-Courtier itself, so the icon never draws.
# ck3-tiger reports it as missing-file.  add_character.dds is the
# nearest real vanilla icon and matches what the button does.
COURTIER_ICON = "gfx/interface/icons/flat_icons/add_character.dds"
BROKEN_COURTIER_ICON = "gfx/interface/icons/flat_icons/character.dds"

# Build-a-Courtier's two buttons, reindented onto AGOT's file.  The pair is
# mutually exclusive on the Roads to Power feature: the real button, and a
# permanently disabled twin whose tooltip explains the DLC requirement.
# Without that feature 'landless_adventurer' degrades to ruler replacement,
# which would hand the designed character the player's own titles.
COURTIER_BUTTONS = f"""\t\t# ---- Build-a-Courtier button ----
\t\t# Sets the courtier-intent flag via scripted_gui, then opens the
\t\t# editor in landless_adventurer mode.  Build-a-Courtier's
\t\t# custom_courtier.0002 hook reads the flag on
\t\t# on_ruler_designer_finished and converts the new character into a
\t\t# courtier of the player.
\t\tbutton_standard = {{
\t\t\tdatacontext = "[LobbyView.GetSelectedPlayable.GetCharacter]"
\t\t\tvisible = "[HasDlcFeature( 'landless_playable' )]"
\t\t\tsize = {{ 380 45 }}

\t\t\tonclick = {SET_INTENT}
\t\t\tonclick = "[TryStartRulerDesigning( Character.Self, 'landless_adventurer' )]"

\t\t\ttooltip = "custom_courtier_button_tooltip"
\t\t\ttext = "custom_courtier_button_text"

\t\t\tbutton_icon = {{
\t\t\t\tsize = {{ 30 30 }}
\t\t\t\tparentanchor = left|vcenter
\t\t\t\tposition = {{ 5 0 }}
\t\t\t\talwaystransparent = yes
\t\t\t\ttexture = "{COURTIER_ICON}"
\t\t\t}}
\t\t}}

\t\t# Fallback shown without Roads to Power: same button, permanently
\t\t# disabled, tooltip explains the DLC requirement.
\t\tbutton_standard = {{
\t\t\tdatacontext = "[LobbyView.GetSelectedPlayable.GetCharacter]"
\t\t\tvisible = "[Not( HasDlcFeature( 'landless_playable' ) )]"
\t\t\tenabled = no
\t\t\tsize = {{ 380 45 }}

\t\t\ttooltip = "custom_courtier_button_tooltip_no_dlc"
\t\t\ttext = "custom_courtier_button_text"

\t\t\tbutton_icon = {{
\t\t\t\tsize = {{ 30 30 }}
\t\t\t\tparentanchor = left|vcenter
\t\t\t\tposition = {{ 5 0 }}
\t\t\t\talwaystransparent = yes
\t\t\t\ttexture = "{COURTIER_ICON}"
\t\t\t}}
\t\t}}

"""

# Build-a-Courtier places its buttons after the vanilla designer buttons and
# before the selected-character info vbox.  AGOT leaves a whitespace-only
# line there; anchoring on the heir icon keeps the match unique.
BUTTON_ANCHOR = (
    '\t\t\t\ttexture = "gfx/interface/icons/flat_icons/heir.dds"\n'
    "\t\t\t}\n"
    "\t\t}\n"
    "\t\t\n"
    "\t\tvbox = {\n"
)


@dataclass(frozen=True, slots=True)
class ParentSource:
    """One parent's text plus the byte-level shape to write back.

    These GUI files disagree about both BOM and line endings, so each
    output restores what its own parent used rather than a house style.
    """

    text: str
    bom: bool
    newline: str

    def restore(self, merged: str) -> str:
        return normalize_newlines(merged, self.newline)


def parent_source(
    context: GenerationContext, source: str, relative: str
) -> ParentSource:
    """Read one parent file, normalised to LF for rewriting.

    Content drift is not checked here: sources.lock.json pins every file the run
    reads, so a hash repeated in this module would only be a second copy to
    update by hand.
    """
    path = context.source(source) / relative
    if not path.is_file():
        raise GenerationError(f"missing required source: {path}")
    raw = path.read_bytes()
    decoded = raw.decode("utf-8-sig")
    return ParentSource(
        text=decoded.replace("\r\n", "\n").replace("\r", "\n"),
        bom=raw.startswith(BOM_UTF8),
        newline=newline_style(decoded),
    )


def write_like_parent(
    context: GenerationContext, relative: str, parent: ParentSource, merged: str
) -> None:
    """Write a merged file in its parent's own encoding and newlines."""
    context.write_text(
        relative,
        parent.restore(merged),
        encoding="utf-8-sig" if parent.bom else "utf-8",
    )


def assert_parent_delta(courtier: str) -> None:
    """Fail if Build-a-Courtier's delta is no longer what we replay.

    The pins already catch any upstream edit, but these assertions name
    *what* is being replayed, so a pin bump reports the real question:
    whether the parent's own button wiring still looks like this.
    """
    checks = (
        (SET_INTENT, 1, "set-intent call site"),
        (CLEAR_INTENT, 3, "clear-intent call sites"),
        ("visible = \"[HasDlcFeature( 'landless_playable' )]\"", 1, "DLC gate"),
        ('tooltip = "custom_courtier_button_tooltip"', 1, "button tooltip"),
        ('tooltip = "custom_courtier_button_tooltip_no_dlc"', 1, "no-DLC tooltip"),
        # Drop the icon repair once the parent stops shipping the
        # dangling texture reference.
        (BROKEN_COURTIER_ICON, 2, "broken button icon"),
    )
    for needle, expected, label in checks:
        count = courtier.count(needle)
        if count != expected:
            raise GenerationError(
                f"Build-a-Courtier {label}: expected {expected}, found {count}"
            )


def add_clear_before_designer(text: str, mode: str) -> str:
    """Drop a stale courtier-intent flag before one designer button fires."""
    call = f"onclick = \"[TryStartRulerDesigning( Character.Self, '{mode}' )]\""
    return replace_exact(
        text,
        f"\t\t\t{call}",
        f"{CLEAR_COMMENT}\t\t\tonclick = {CLEAR_INTENT}\n\t\t\t{call}",
        label=f"{mode} designer button",
    )


def generate_multiplayer_types(context: GenerationContext) -> None:
    """Replay Build-a-Courtier's additions onto AGOT's lobby GUI."""
    agot = parent_source(context, "agot", MULTIPLAYER_TYPES)
    courtier = parent_source(context, "build-a-courtier", MULTIPLAYER_TYPES)
    assert_parent_delta(courtier.text)

    merged = agot.text
    for mode in VANILLA_DESIGNER_MODES:
        merged = add_clear_before_designer(merged, mode)

    merged = replace_exact(
        merged,
        BUTTON_ANCHOR,
        BUTTON_ANCHOR[: -len("\t\tvbox = {\n")] + COURTIER_BUTTONS + "\t\tvbox = {\n",
        label="Build-a-Courtier button insertion",
    )

    # AGOT's own call site must survive: dropping it is exactly the
    # regression this module exists to undo.
    if "agot_create_landless_pirate_button" not in merged:
        raise GenerationError("merged GUI lost AGOT's pirate designer button")

    write_like_parent(context, MULTIPLAYER_TYPES, agot, merged)


def generate_pirate_button(context: GenerationContext) -> None:
    """Give AGOT's pirate button the same stale-flag clear as the rest."""
    agot = parent_source(context, "agot", AGOT_MULTIPLAYER_TYPES)

    call = "onclick = \"[GetVariableSystem.Set('pirate_designer', 'true')]\""
    merged = replace_exact(
        agot.text,
        f"\t\t{call}",
        "\t\t# Build-a-Courtier compatch: AGOT's pirate button opens the same\n"
        "\t\t# landless_adventurer designer, so it must drop a stale\n"
        "\t\t# courtier-intent flag too or a cancelled courtier session\n"
        "\t\t# converts the designed pirate and destroys their camp.\n"
        f"\t\tonclick = {CLEAR_INTENT}\n"
        f"\t\t{call}",
        label="AGOT pirate designer button",
    )

    write_like_parent(context, AGOT_MULTIPLAYER_TYPES, agot, merged)


def generate(context: GenerationContext) -> None:
    # Read only: the vanilla base is pinned so a three-way review stays
    # possible even though the merge itself is a replay onto AGOT.
    parent_source(context, "game", MULTIPLAYER_TYPES)

    generate_multiplayer_types(context)
    generate_pirate_button(context)

    print(
        "Generated AGOT/Build-a-Courtier compatch: 2 GUI files rebuilt "
        "(4 designer buttons guarded, 2 courtier buttons restored)."
    )
