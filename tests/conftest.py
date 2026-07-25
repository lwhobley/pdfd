"""pytest configuration and shared fixtures."""
import os
import pytest
import tempfile
from pathlib import Path


@pytest.fixture
def tmp_dir(tmp_path):
    return tmp_path


@pytest.fixture
def sample_pdf(tmp_path) -> str:
    """Create a minimal valid PDF for testing."""
    import reportlab.pdfgen.canvas as canvas_mod
    path = str(tmp_path / "sample.pdf")
    c = canvas_mod.Canvas(path)
    c.drawString(100, 750, "Test page 1")
    c.showPage()
    c.drawString(100, 750, "Test page 2")
    c.showPage()
    c.drawString(100, 750, "Test page 3")
    c.showPage()
    c.save()
    return path


@pytest.fixture
def sample_pdf_2(tmp_path) -> str:
    import reportlab.pdfgen.canvas as canvas_mod
    path = str(tmp_path / "sample2.pdf")
    c = canvas_mod.Canvas(path)
    c.drawString(100, 750, "Second PDF page 1")
    c.showPage()
    c.save()
    return path
