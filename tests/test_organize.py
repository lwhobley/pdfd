"""Tests for M2 organize tools."""
import os
import pytest
from pdf_forge.adapters.pikepdf_adapter import PikePDFAdapter


def test_reverse_pages(sample_pdf, tmp_dir):
    import fitz
    import pikepdf
    out = str(tmp_dir / "reversed.pdf")
    # Get text from each page of original
    orig = fitz.open(sample_pdf)
    orig_texts = [orig[i].get_text().strip() for i in range(orig.page_count)]
    orig.close()
    with pikepdf.open(sample_pdf) as src:
        with pikepdf.Pdf.new() as dst:
            for page in reversed(src.pages):
                dst.pages.append(page)
            dst.save(out)

    rev = fitz.open(out)
    rev_texts = [rev[i].get_text().strip() for i in range(rev.page_count)]
    rev.close()
    assert rev_texts == list(reversed(orig_texts))


def test_reorder_pages(sample_pdf, tmp_dir):
    out = str(tmp_dir / "reordered.pdf")
    import pikepdf
    with pikepdf.open(sample_pdf) as src:
        n = len(src.pages)
    # Reverse order via reorder
    new_order = list(range(n - 1, -1, -1))
    with pikepdf.open(sample_pdf) as src:
        with pikepdf.Pdf.new() as dst:
            for idx in new_order:
                dst.pages.append(src.pages[idx])
            dst.save(out)
    assert PikePDFAdapter.get_page_count(out) == n


def test_nup_2up(sample_pdf, tmp_dir):
    """2-up should produce ceil(N/2) pages."""
    import math
    import fitz
    out = str(tmp_dir / "nup.pdf")
    src = fitz.open(sample_pdf)
    n = src.page_count
    src.close()

    from pdf_forge.tools.organize.nup import NUpJob
    job = NUpJob(sample_pdf, out, n=2)
    from pdf_forge.workers.job_model import JobStatus
    result = job.execute()
    assert os.path.isfile(out)
    doc = fitz.open(out)
    assert doc.page_count == math.ceil(n / 2)
    doc.close()


def test_add_blank_page(sample_pdf, tmp_dir):
    out = str(tmp_dir / "with_blank.pdf")
    original_count = PikePDFAdapter.get_page_count(sample_pdf)
    from pdf_forge.tools.organize.add_blank_page import AddBlankPageJob
    job = AddBlankPageJob(sample_pdf, out, position=1)
    job.execute()
    assert PikePDFAdapter.get_page_count(out) == original_count + 1


def test_metadata_roundtrip(sample_pdf, tmp_dir):
    out = str(tmp_dir / "meta.pdf")
    PikePDFAdapter.set_metadata(
        sample_pdf, out,
        {"Title": "Test Title", "Author": "Test Author"}
    )
    meta = PikePDFAdapter.get_metadata(out)
    assert meta.get("Title") == "Test Title"
    assert meta.get("Author") == "Test Author"
