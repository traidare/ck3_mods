#!/usr/bin/env python3
"""Remove ruler-designer-invalid fields from Long Night special morph genes."""

from __future__ import annotations

import codecs
import hashlib
import re
from pathlib import Path

from gen import GenerationContext, GenerationError
from gen.text import normalize_newlines, strip_trailing_whitespace

RELATIVE_GENES = Path("common/genes/zz_long_night_genes.txt")
SOURCE_SHA256 = "f42025226bfca56fddd95279e9411867f3a60bf915b3bec328749e16425d1502"
EXPECTED_GENES = 18


def read_pinned(context: GenerationContext) -> str:
    path = context.source("long-night-azor-ahai") / RELATIVE_GENES
    if not path.is_file():
        raise GenerationError(f"missing required source: {path}")
    raw = path.read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if actual != SOURCE_SHA256:
        raise GenerationError(
            f"long-night-azor-ahai/{RELATIVE_GENES} changed: "
            f"expected {SOURCE_SHA256}, found {actual}"
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


def generate(context: GenerationContext) -> None:
    payload = codecs.BOM_UTF8 + repaired_genes(read_pinned(context)).encode("utf-8")
    context.write_bytes(RELATIVE_GENES, payload)
