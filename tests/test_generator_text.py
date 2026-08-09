from __future__ import annotations

from codecs import BOM_UTF8

import pytest

from ck3mm.generators.text import matching_brace, read_source, replace_regex


def test_matching_brace_ignores_strings_comments_and_escapes() -> None:
    text = '{ quoted = "}" escaped = "\\"" # }\n nested = { value = yes } }'

    assert matching_brace(text, 0) == len(text) - 1


def test_read_source_optionally_requires_utf8_bom(tmp_path) -> None:
    source = tmp_path / "source.txt"
    source.write_bytes(BOM_UTF8 + b"value = yes\n")

    assert read_source(source, require_bom=True) == "value = yes\n"

    source.write_bytes(b"value = no\r\nnext = value\r")
    assert read_source(source) == "value = no\r\nnext = value\r"
    assert read_source(source, normalize_newlines=True) == "value = no\nnext = value\n"

    with pytest.raises(ValueError, match="missing its UTF-8 BOM"):
        read_source(source, require_bom=True)


def test_replace_regex_checks_match_count_and_error_type() -> None:
    assert replace_regex("a=1", r"1", "2", "value") == "a=2"

    with pytest.raises(RuntimeError, match="expected 2 regex match"):
        replace_regex("a=1", r"1", "2", "value", expected=2, error_type=RuntimeError)
