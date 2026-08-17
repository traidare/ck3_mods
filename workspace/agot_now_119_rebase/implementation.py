#!/usr/bin/env python3
"""Rebase A Game of Thrones: Now's runtime repairs onto the current release.

Every replacement is counted, so an upstream update fails loudly instead of
silently generating a stale whole-file override.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from gen import GenerationContext
from gen.script import normalize_rebased_source, read_text, write_text
from gen.sources import WorkshopSources
from gen.text import replace_exact


@dataclass(frozen=True, slots=True)
class RunInputs:
    WORKSHOP: WorkshopSources
    NOW_OUTPUT: Path


def generate_now_summerhall_candidate_guards(inputs: RunInputs) -> None:
    relative = "events/agot_events/agot_summerhall_events.txt"
    text = read_text(inputs.WORKSHOP / "3664900993" / relative)
    for candidate, expected in ((1, 23), (2, 13), (3, 3)):
        text = replace_exact(
            text,
            f"NOT = {{ this = scope:candidate_{candidate} }}",
            f"NOT = {{ scope:candidate_{candidate} ?= this }}",
            expected=expected,
            label=f"NOW Summerhall optional candidate {candidate} comparisons",
        )
    write_text(inputs.NOW_OUTPUT, relative, text)


def require_upstream_namespace(inputs: RunInputs, relative: str) -> None:
    """Assert a repair NOW has adopted upstream is still in place.

    The module used to override this file purely to declare its namespace.
    Without a check, a regression upstream would silently reintroduce the
    missing-event bug this module was written to fix.
    """
    namespace = Path(relative).stem
    text = read_text(inputs.WORKSHOP / "3664900993" / relative)
    count = text.count(f"namespace = {namespace}")
    if count != 1:
        raise RuntimeError(
            f"NOW {relative}: expected 1 'namespace = {namespace}', found {count}; "
            "restore the whole-file override that declared it"
        )


def generate_now_core_rebase(inputs: RunInputs) -> None:
    """Regenerate NOW's non-event whole-file runtime repairs."""
    # NOW 1.2.5 fixed the dummy Great Fork title's `capital = c_great_for`
    # typo upstream, so the whole-file titular landed-titles override no longer
    # carries a delta and is not written.
    relative = "common/on_action/agot_now_on_actions.txt"
    text = read_text(inputs.WORKSHOP / "3664900993" / relative)
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
    write_text(inputs.NOW_OUTPUT, relative, normalize_rebased_source(text))

    # NOW declares `namespace = agot_coa_events` in its separate personal-COA
    # event file upstream, so that override is no longer written. Re-adding it
    # would declare the namespace twice.
    require_upstream_namespace(inputs, "events/agot_events/replace/agot_coa_events.txt")


def generate(context: GenerationContext) -> None:

    WORKSHOP = WorkshopSources(context)
    NOW_OUTPUT = context.output_root
    inputs = RunInputs(WORKSHOP=WORKSHOP, NOW_OUTPUT=NOW_OUTPUT)
    generate_now_core_rebase(inputs)
    generate_now_summerhall_candidate_guards(inputs)
