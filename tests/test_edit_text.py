"""Tests for the edit_text (find and replace) tool."""
from __future__ import annotations
import fitz
import pytest

from pdf_forge.tools.edit.edit_text import EditTextTool


def _make_pdf(path: str, lines: list[str], pages: int = 1) -> None:
    doc = fitz.open()
    for _ in range(pages):
        page = doc.new_page()
        y = 72
        for line in lines:
            page.insert_text((72, y), line, fontsize=12)
            y += 24
    doc.save(path)
    doc.close()


def _run(tmp_path, lines, pages=1, **params):
    src = str(tmp_path / "in.pdf")
    out = str(tmp_path / "out.pdf")
    _make_pdf(src, lines, pages)
    job = EditTextTool().create_job(
        {"input_path": src, "output_path": out, **params}
    )
    result = job.execute()
    doc = fitz.open(out)
    text = "\n".join(page.get_text() for page in doc)
    doc.close()
    return result, text


def test_replaces_text(tmp_path):
    result, text = _run(
        tmp_path, ["Hello World"],
        find_text="World", replace_text="Planet",
    )
    assert result.metadata["replacements"] == 1
    assert "Planet" in text
    assert "World" not in text


def test_deletes_text_when_replacement_empty(tmp_path):
    result, text = _run(
        tmp_path, ["Delete ME please"],
        find_text="ME ", replace_text="",
    )
    assert result.metadata["replacements"] == 1
    assert "ME" not in text


def test_case_sensitive_matches_exact_case_only(tmp_path):
    result, text = _run(
        tmp_path, ["Foo foo FOO"],
        find_text="foo", replace_text="bar", case_sensitive=True,
    )
    assert result.metadata["replacements"] == 1
    assert "Foo" in text and "FOO" in text


def test_case_insensitive_matches_all_cases(tmp_path):
    result, text = _run(
        tmp_path, ["Foo foo FOO"],
        find_text="foo", replace_text="bar", case_sensitive=False,
    )
    assert result.metadata["replacements"] == 3
    # no leftover fragments from the original words
    assert "Foo" not in text and "FOO" not in text


def test_no_match_is_a_noop(tmp_path):
    result, _ = _run(
        tmp_path, ["nothing here"],
        find_text="zzz", replace_text="x",
    )
    assert result.metadata["replacements"] == 0


def test_replaces_across_all_pages(tmp_path):
    result, text = _run(
        tmp_path, ["TARGET here"], pages=3,
        find_text="TARGET", replace_text="HIT",
    )
    assert result.metadata["replacements"] == 3
    assert "TARGET" not in text
    assert text.count("HIT") == 3
