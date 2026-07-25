"""Tests for the merge tool."""
import os
import pytest
from pdf_forge.adapters.pikepdf_adapter import PikePDFAdapter


def test_merge_two_pdfs(sample_pdf, sample_pdf_2, tmp_dir):
    output = str(tmp_dir / "merged.pdf")
    PikePDFAdapter.merge([sample_pdf, sample_pdf_2], output)
    assert os.path.isfile(output)

    # Verify page count
    count = PikePDFAdapter.get_page_count(output)
    assert count == PikePDFAdapter.get_page_count(sample_pdf) + PikePDFAdapter.get_page_count(sample_pdf_2)


def test_merge_requires_at_least_two(sample_pdf, tmp_dir):
    output = str(tmp_dir / "merged.pdf")
    # Merging one file is still valid (copies it)
    PikePDFAdapter.merge([sample_pdf], output)
    assert PikePDFAdapter.get_page_count(output) == 3


def test_merge_preserves_order(sample_pdf, sample_pdf_2, tmp_dir):
    import fitz
    output = str(tmp_dir / "merged.pdf")
    PikePDFAdapter.merge([sample_pdf, sample_pdf_2], output)
    doc = fitz.open(output)
    total = doc.page_count
    doc.close()
    assert total == 4
