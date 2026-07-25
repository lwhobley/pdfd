"""Tests for shared text search — case sensitivity and whole-word matching.

page.search_for() is always case-insensitive and has no whole-word option,
so these guard the filtering layer on top of it.
"""
from __future__ import annotations
import fitz
import pytest

from pdf_forge.tools.edit.text_search import find_text_rects


def _page(text: str):
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text, fontsize=12)
    return doc, page


@pytest.mark.parametrize("text,needle,case_sensitive,whole_word,expected", [
    ("Foo foo FOO",           "foo", False, False, 3),
    ("Foo foo FOO",           "foo", True,  False, 1),
    ("Foo foo FOO",           "Foo", True,  False, 1),
    ("Foo foo FOO",           "FOO", True,  False, 1),
    ("foo barfoo foobar foo", "foo", False, False, 4),
    ("foo barfoo foobar foo", "foo", False, True,  2),
    ("foo, foo. (foo)",       "foo", False, True,  3),
    ("Foo foo barfoo",        "foo", True,  True,  1),
    ("cat cats concat",       "cat", False, True,  1),
    ("nothing here",          "zzz", False, False, 0),
    ("Hello World",           "",    False, False, 0),
])
def test_find_text_rects(text, needle, case_sensitive, whole_word, expected):
    doc, page = _page(text)
    try:
        hits = find_text_rects(
            page, needle,
            case_sensitive=case_sensitive,
            whole_word=whole_word,
        )
        assert len(hits) == expected
    finally:
        doc.close()


def test_search_for_is_case_insensitive():
    """Documents the PyMuPDF behaviour the filtering layer exists to correct."""
    doc, page = _page("Foo foo FOO")
    try:
        assert len(page.search_for("foo")) == 3
        assert len(page.search_for("FOO")) == 3
    finally:
        doc.close()
