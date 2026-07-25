"""Shared text search for the redact and edit_text tools.

page.search_for() is always case-insensitive and has no whole-word option,
so its hits are treated as candidates and filtered against the text actually
present at each rect.
"""
from __future__ import annotations

import fitz


def find_text_rects(
    page: fitz.Page,
    needle: str,
    case_sensitive: bool = False,
    whole_word: bool = False,
) -> list[fitz.Rect]:
    """Return rects of every occurrence of needle on page."""
    if not needle:
        return []
    rects = page.search_for(needle)
    if not (case_sensitive or whole_word):
        return rects
    return [r for r in rects if _keep(page, r, needle, case_sensitive, whole_word)]


def _keep(
    page: fitz.Page,
    rect: fitz.Rect,
    needle: str,
    case_sensitive: bool,
    whole_word: bool,
) -> bool:
    if case_sensitive and needle not in page.get_text("text", clip=rect):
        return False
    if whole_word and not _is_whole_word(page, rect, needle, case_sensitive):
        return False
    return True


def _is_whole_word(
    page: fitz.Page,
    rect: fitz.Rect,
    needle: str,
    case_sensitive: bool,
) -> bool:
    """True if the match is not embedded in a longer alphanumeric run."""
    word = _word_at(page, rect)
    if word is None:
        return False
    haystack = word if case_sensitive else word.lower()
    target = needle if case_sensitive else needle.lower()

    idx = haystack.find(target)
    while idx != -1:
        before = word[idx - 1] if idx > 0 else ""
        end = idx + len(target)
        after = word[end] if end < len(word) else ""
        if not before.isalnum() and not after.isalnum():
            return True
        idx = haystack.find(target, idx + 1)
    return False


def _word_at(page: fitz.Page, rect: fitz.Rect) -> str | None:
    """Text of the word overlapping rect the most."""
    best: str | None = None
    best_area = 0.0
    for x0, y0, x1, y1, word, *_ in page.get_text("words"):
        overlap = fitz.Rect(x0, y0, x1, y1) & rect
        if overlap.is_empty:
            continue
        area = abs(overlap)
        if area > best_area:
            best, best_area = word, area
    return best
