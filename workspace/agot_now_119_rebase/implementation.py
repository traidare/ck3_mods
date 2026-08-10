#!/usr/bin/env python3
"""Rebase A Game of Thrones: Now's runtime repairs onto the current release.

Every replacement is counted, so an upstream update fails loudly instead of
silently generating a stale whole-file override.
"""

from __future__ import annotations

from pathlib import Path

from ck3mm.generation import GenerationContext
from ck3mm.generators.script import normalize_rebased_source, read_text, write_text
from ck3mm.generators.sources import WorkshopSources
from ck3mm.generators.text import replace_exact

WORKSHOP: WorkshopSources | None = None
NOW_OUTPUT: Path | None = None


def generate_now_summerhall_candidate_guards() -> None:
    relative = "events/agot_events/agot_summerhall_events.txt"
    text = read_text(WORKSHOP / "3664900993" / relative)
    for candidate, expected in ((1, 23), (2, 13), (3, 3)):
        text = replace_exact(
            text,
            f"NOT = {{ this = scope:candidate_{candidate} }}",
            f"NOT = {{ scope:candidate_{candidate} ?= this }}",
            expected=expected,
            label=f"NOW Summerhall optional candidate {candidate} comparisons",
        )
    write_text(NOW_OUTPUT, relative, text)


def generate_now_core_rebase() -> None:
    """Regenerate NOW's non-event whole-file runtime repairs."""
    # NOW 1.2.5 fixed the dummy Great Fork title's `capital = c_great_for`
    # typo upstream, so the whole-file titular landed-titles override no longer
    # carries a delta and is not written.
    relative = "common/on_action/agot_now_on_actions.txt"
    text = read_text(WORKSHOP / "3664900993" / relative)
    # NOW 1.2.5 resolved the rest of this file's repairs upstream: the
    # command-government mechanism now runs through the game-start grey-cloaks
    # court-position appointment (which applies `change_government` itself), the
    # permanent `duration = -1` population modifiers are gone, and the invalid
    # `set_government`/`set_de_jure_liege` effects were replaced. Only the
    # unsaved Great Fork title-change scope still needs repair.
    text = replace_exact(
        text,
        "change = scope:great_fork_change",
        "change = scope:blackwater_change",
        expected=1,
        label="NOW Great Fork title-change scope",
    )
    write_text(NOW_OUTPUT, relative, normalize_rebased_source(text))

    relative = "events/agot_events/replace/agot_coa_events.txt"
    text = read_text(WORKSHOP / "3664900993" / relative)
    text = replace_exact(
        text,
        "agot_coa_events.0003 = {",
        "namespace = agot_coa_events\n\nagot_coa_events.0003 = {",
        expected=1,
        label="NOW personal-COA event namespace",
    )
    write_text(NOW_OUTPUT, relative, text)


def generate(context: GenerationContext) -> None:
    global WORKSHOP, NOW_OUTPUT
    WORKSHOP = WorkshopSources(context)
    NOW_OUTPUT = context.output_root
    generate_now_core_rebase()
    generate_now_summerhall_candidate_guards()
