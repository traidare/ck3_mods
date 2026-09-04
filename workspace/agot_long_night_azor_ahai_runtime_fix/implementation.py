#!/usr/bin/env python3
"""Narrow runtime repairs for AGOT: The Long Night & Azor Ahai on CK3 1.19."""

from __future__ import annotations

import codecs
import re
from pathlib import Path

from gen import GenerationContext, GenerationError
from gen.text import normalize_newlines, read_source, strip_trailing_whitespace

SOURCE = "long-night-azor-ahai"

RELATIVE_GENES = Path("common/genes/zz_long_night_genes.txt")
EXPECTED_GENES = 18

RELATIVE_SERVICE_TRIGGERS = Path("common/scripted_triggers/zz_ln_service_triggers.txt")
SERVICE_GATE = "ln_may_serve_trigger"
SERVICE_TRIGGER_CALL_SITES = (
    "can_be_knight_trigger",
    "base_court_position_validity_trigger",
    "can_be_councillor_basics_trigger",
)


def read_upstream(context: GenerationContext, relative: Path) -> str:
    """Read one upstream file, asserting the encoding this generator assumes.

    Content drift is not checked here: sources.lock.json pins every file the run
    reads, so a hash repeated in this module would only be a second copy to
    update by hand.
    """
    return read_source(
        context.source(SOURCE) / relative, require_bom=True, normalize_newlines=True
    )


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


def assert_service_gate_terminated(context: GenerationContext) -> None:
    """Fail generation if the parent's service gate loses its chain terminator.

    ``ln_may_serve_trigger`` gates knights, court positions, councillors, and
    commanders. A ``trigger_if``/``trigger_else_if`` chain with no
    ``trigger_else`` fails PostValidate on CK3 1.19, which makes the whole gate
    return false and refuses every candidate rather than only the dead. The
    parent terminates the chain itself, so this module owns no override of the
    file; the check exists so a regression is caught here instead of in a log.
    """
    path = context.source(SOURCE) / RELATIVE_SERVICE_TRIGGERS
    if not path.is_file():
        raise GenerationError(f"missing required source: {path}")
    source = path.read_bytes().decode("utf-8-sig").replace("\r\n", "\n")

    gate = re.search(
        rf"(?ms)^{re.escape(SERVICE_GATE)}\s*=\s*\{{\n(?P<body>.*?)^\}}$", source
    )
    if gate is None:
        raise GenerationError(f"service gate {SERVICE_GATE} is no longer defined")
    body = gate.group("body")

    if not re.search(r"(?m)^\ttrigger_else_if\s*=", body):
        raise GenerationError(
            f"{SERVICE_GATE} no longer branches on trigger_else_if; recheck whether "
            "the chain still needs a terminator at all"
        )
    if not re.search(r"(?m)^\ttrigger_else\s*=", body):
        raise GenerationError(
            f"{SERVICE_GATE} lost its trigger_else terminator; CK3 1.19 fails "
            "PostValidate on the chain and the gate refuses every candidate"
        )

    for call_site in SERVICE_TRIGGER_CALL_SITES:
        if not re.search(rf"(?m)^{re.escape(call_site)}\s*=\s*\{{", source):
            raise GenerationError(f"service gate no longer overrides {call_site}")


def generate(context: GenerationContext) -> None:
    genes = read_upstream(context, RELATIVE_GENES)
    context.write_bytes(
        RELATIVE_GENES, codecs.BOM_UTF8 + repaired_genes(genes).encode("utf-8")
    )

    assert_service_gate_terminated(context)
