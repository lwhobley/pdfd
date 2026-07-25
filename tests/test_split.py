"""Tests for the split tool."""
import os
from pdf_forge.adapters.pikepdf_adapter import PikePDFAdapter


def test_split_every_1_page(sample_pdf, tmp_dir):
    paths = PikePDFAdapter.split_every_n(sample_pdf, 1, str(tmp_dir), "test")
    assert len(paths) == 3
    for p in paths:
        assert os.path.isfile(p)
        assert PikePDFAdapter.get_page_count(p) == 1


def test_split_every_2_pages(sample_pdf, tmp_dir):
    paths = PikePDFAdapter.split_every_n(sample_pdf, 2, str(tmp_dir), "test")
    assert len(paths) == 2
    assert PikePDFAdapter.get_page_count(paths[0]) == 2
    assert PikePDFAdapter.get_page_count(paths[1]) == 1


def test_split_by_range(sample_pdf, tmp_dir):
    out1 = str(tmp_dir / "out1.pdf")
    out2 = str(tmp_dir / "out2.pdf")
    PikePDFAdapter.split_by_range(
        sample_pdf,
        [(0, 2), (2, 3)],
        [out1, out2],
    )
    assert PikePDFAdapter.get_page_count(out1) == 2
    assert PikePDFAdapter.get_page_count(out2) == 1
