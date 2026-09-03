#!/usr/bin/env python3
"""Narrow runtime repairs for AGOT: The Long Night & Azor Ahai on CK3 1.19."""

from __future__ import annotations

import codecs
import hashlib
import re
from pathlib import Path

from gen import GenerationContext, GenerationError
from gen.text import normalize_newlines, replace_exact, strip_trailing_whitespace

SOURCE = "long-night-azor-ahai"

RELATIVE_GENES = Path("common/genes/zz_long_night_genes.txt")
GENES_SHA256 = "f42025226bfca56fddd95279e9411867f3a60bf915b3bec328749e16425d1502"
EXPECTED_GENES = 18

RELATIVE_SERVICE_TRIGGERS = Path("common/scripted_triggers/zz_ln_service_triggers.txt")
SERVICE_TRIGGERS_SHA256 = (
    "25eec74b1ac72d8e2f25325d6beb26960d090666c9f4f348c7b2e58d1cd65550"
)
SERVICE_TRIGGER_CALL_SITES = (
    "can_be_knight_trigger",
    "base_court_position_validity_trigger",
    "can_be_councillor_basics_trigger",
)


def read_pinned(context: GenerationContext, relative: Path, expected: str) -> str:
    path = context.source(SOURCE) / relative
    if not path.is_file():
        raise GenerationError(f"missing required source: {path}")
    raw = path.read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if actual != expected:
        raise GenerationError(
            f"{SOURCE}/{relative} changed: expected {expected}, found {actual}"
        )
    if not raw.startswith(codecs.BOM_UTF8):
        raise GenerationError(f"required source is missing its UTF-8 BOM: {path}")
    return raw.decode("utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")


def repaired_genes(source: str) -> str:
    gene_names = re.findall(r"(?m)^\t\t\t(?P<name>[a-z0-9_]+)\s*=\s*\{$", source)
    if len(gene_names) != EXPECTED_GENES or len(set(gene_names)) != EXPECTED_GENES:
        raise GenerationError(
            f"special morph genes: expected {EXPECTED_GENES} unique definitions, "
            f"found {len(gene_names)} ({len(set(gene_names))} unique)"
        )

    repaired, inheritable_count = re.subn(
        r"(?m)^[ \t]*inheritable\s*=\s*yes[ \t]*\n", "", source
    )
    repaired, group_count = re.subn(
        r"(?m)^[ \t]*group\s*=\s*(?:body|hair|eyes)[ \t]*\n", "", repaired
    )
    if inheritable_count != EXPECTED_GENES:
        raise GenerationError(
            f"inheritable fields: expected {EXPECTED_GENES}, found {inheritable_count}"
        )
    if group_count != EXPECTED_GENES:
        raise GenerationError(
            f"group fields: expected {EXPECTED_GENES}, found {group_count}"
        )
    if re.search(r"(?m)^[ \t]*(?:inheritable|group)\s*=", repaired):
        raise GenerationError("repaired special morph genes retain a forbidden field")

    repaired_names = re.findall(r"(?m)^\t\t\t(?P<name>[a-z0-9_]+)\s*=\s*\{$", repaired)
    if repaired_names != gene_names:
        raise GenerationError("gene definitions changed while removing invalid fields")
    return strip_trailing_whitespace(normalize_newlines(repaired, "\n"))


def repaired_service_triggers(source: str) -> str:
    """Terminate the service gate's trigger_if chain so CK3 1.19 validates it.

    ``ln_may_serve_trigger`` pairs a ``trigger_if`` with a ``trigger_else_if``
    and no ``trigger_else``, which fails PostValidate and makes the whole gate
    return false for every caller. The living-under-a-living-lord case is the
    one the parent documents as silently permitted, so the terminator is
    ``always = yes``.
    """
    calls = len(re.findall(r"(?m)^\tln_may_serve_trigger = \{ LORD = ", source))
    if calls != len(SERVICE_TRIGGER_CALL_SITES):
        raise GenerationError(
            f"service gate: expected {len(SERVICE_TRIGGER_CALL_SITES)} in-file call "
            f"sites, found {calls}"
        )
    for call_site in SERVICE_TRIGGER_CALL_SITES:
        if not re.search(rf"(?m)^{re.escape(call_site)}\s*=\s*\{{", source):
            raise GenerationError(f"service gate no longer overrides {call_site}")

    if re.search(r"(?m)^\ttrigger_else\s*=", source):
        raise GenerationError(
            "service gate already terminates its chain; the repair is obsolete"
        )

    chain_end = """\ttrigger_else_if = {
\t\tlimit = { $LORD$ ?= { ln_is_one_of_them_trigger = yes } }
\t\tcustom_tooltip = {
\t\t\ttext = ln_may_not_serve_the_dead_tt
\t\t\tln_is_one_of_them_trigger = yes
\t\t}
\t}
}"""
    if source.count(chain_end) != 1:
        raise GenerationError(
            "service gate no longer ends on the unterminated trigger_else_if chain"
        )

    repaired = replace_exact(
        source,
        """\ttrigger_else_if = {
\t\tlimit = { $LORD$ ?= { ln_is_one_of_them_trigger = yes } }
\t\tcustom_tooltip = {
\t\t\ttext = ln_may_not_serve_the_dead_tt
\t\t\tln_is_one_of_them_trigger = yes
\t\t}
\t}
}""",
        """\ttrigger_else_if = {
\t\tlimit = { $LORD$ ?= { ln_is_one_of_them_trigger = yes } }
\t\tcustom_tooltip = {
\t\t\ttext = ln_may_not_serve_the_dead_tt
\t\t\tln_is_one_of_them_trigger = yes
\t\t}
\t}
\t# CK3 1.19 fails PostValidate on a trigger_else_if with no trigger_else, and
\t# the whole gate then returns false for all four call sites. Both parties are
\t# living here, which the gate is meant to permit without a tooltip.
\ttrigger_else = { always = yes }
}""",
        expected=1,
        label="Long Night service gate trigger_else terminator",
    )
    return strip_trailing_whitespace(normalize_newlines(repaired, "\n"))


def generate(context: GenerationContext) -> None:
    genes = read_pinned(context, RELATIVE_GENES, GENES_SHA256)
    context.write_bytes(
        RELATIVE_GENES, codecs.BOM_UTF8 + repaired_genes(genes).encode("utf-8")
    )

    triggers = read_pinned(context, RELATIVE_SERVICE_TRIGGERS, SERVICE_TRIGGERS_SHA256)
    context.write_bytes(
        RELATIVE_SERVICE_TRIGGERS,
        codecs.BOM_UTF8 + repaired_service_triggers(triggers).encode("utf-8"),
    )
