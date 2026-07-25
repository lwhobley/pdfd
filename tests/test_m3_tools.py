"""M3 tool tests — edit, secure, convert."""
from __future__ import annotations
import os
import json
import pytest


# ── Watermark ─────────────────────────────────────────────────────────────────

def test_watermark_creates_output(sample_pdf, tmp_path):
    from pdf_forge.tools.edit.watermark import WatermarkJob

    out = str(tmp_path / "wm.pdf")
    job = WatermarkJob(
        input_path=sample_pdf,
        output_path=out,
        text="DRAFT",
        font_size=48,
        angle=45,
        opacity=0.3,
        color=(0.5, 0.5, 0.5),
    )
    result = job.execute()
    assert os.path.exists(out)
    assert out in result.output_paths


def test_watermark_all_pages(sample_pdf, tmp_path):
    import fitz
    from pdf_forge.tools.edit.watermark import WatermarkJob

    out = str(tmp_path / "wm.pdf")
    WatermarkJob(
        input_path=sample_pdf,
        output_path=out,
        text="TEST",
    ).execute()
    doc = fitz.open(out)
    # Watermark adds text; check page count preserved
    src = fitz.open(sample_pdf)
    assert doc.page_count == src.page_count


# ── Page Numbers ──────────────────────────────────────────────────────────────

def test_page_numbers(sample_pdf, tmp_path):
    from pdf_forge.tools.edit.page_numbers import PageNumbersJob
    import fitz

    out = str(tmp_path / "numbered.pdf")
    PageNumbersJob(
        input_path=sample_pdf,
        output_path=out,
        position="bottom_center",
        start_number=1,
        font_size=10,
    ).execute()
    assert os.path.exists(out)
    doc = fitz.open(out)
    src = fitz.open(sample_pdf)
    assert doc.page_count == src.page_count


# ── Bates Numbers ─────────────────────────────────────────────────────────────

def test_bates_number(sample_pdf, tmp_path):
    from pdf_forge.tools.edit.bates_number import BatesNumberJob

    out = str(tmp_path / "bates.pdf")
    result = BatesNumberJob(
        input_path=sample_pdf,
        output_path=out,
        prefix="CASE-",
        start_number=1,
        pad_width=6,
        position="bottom_right",
        font_size=9,
    ).execute()
    assert os.path.exists(out)
    assert result.metadata.get("end_number") == 3  # 3-page sample


# ── Header / Footer ───────────────────────────────────────────────────────────

def test_header_footer(sample_pdf, tmp_path):
    from pdf_forge.tools.edit.header_footer import HeaderFooterJob
    import fitz

    out = str(tmp_path / "hf.pdf")
    HeaderFooterJob(
        input_path=sample_pdf,
        output_path=out,
        header_center="My Document",
        footer_center="{page} / {total}",
        font_size=9,
    ).execute()
    assert os.path.exists(out)
    doc = fitz.open(out)
    # Check footer text appears on first page
    text = doc[0].get_text()
    assert "1" in text


# ── Crop ──────────────────────────────────────────────────────────────────────

def test_crop_reduces_cropbox(sample_pdf, tmp_path):
    import fitz
    from pdf_forge.tools.edit.crop import CropJob

    src = fitz.open(sample_pdf)
    orig_rect = src[0].mediabox
    src.close()

    out = str(tmp_path / "cropped.pdf")
    CropJob(
        input_path=sample_pdf,
        output_path=out,
        margin_top=20,
        margin_right=20,
        margin_bottom=20,
        margin_left=20,
    ).execute()
    doc = fitz.open(out)
    new_rect = doc[0].cropbox
    assert new_rect.width < orig_rect.width
    assert new_rect.height < orig_rect.height


# ── Redact ────────────────────────────────────────────────────────────────────

def test_redact_removes_text(tmp_path):
    """Create a PDF with known text, redact it, verify it's gone."""
    import fitz

    # Create test PDF with known text
    src_path = str(tmp_path / "src.pdf")
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(fitz.Point(100, 100), "SECRET12345")
    doc.save(src_path)
    doc.close()

    from pdf_forge.tools.edit.redact import RedactJob

    out = str(tmp_path / "redacted.pdf")
    RedactJob(
        input_path=src_path,
        output_path=out,
        search_terms=["SECRET12345"],
    ).execute()

    doc2 = fitz.open(out)
    text = doc2[0].get_text()
    assert "SECRET12345" not in text


# ── Flatten ───────────────────────────────────────────────────────────────────

def test_flatten_produces_raster_pdf(sample_pdf, tmp_path):
    import fitz
    from pdf_forge.tools.edit.flatten import FlattenJob

    out = str(tmp_path / "flat.pdf")
    FlattenJob(
        input_path=sample_pdf,
        output_path=out,
        render_dpi=72,
    ).execute()
    assert os.path.exists(out)
    doc = fitz.open(out)
    src = fitz.open(sample_pdf)
    assert doc.page_count == src.page_count


# ── Remove Annotations ────────────────────────────────────────────────────────

def test_remove_annotations(tmp_path):
    import fitz
    from pdf_forge.tools.edit.remove_annotations import RemoveAnnotationsJob

    src_path = str(tmp_path / "ann.pdf")
    doc = fitz.open()
    page = doc.new_page()
    page.add_text_annot(fitz.Point(100, 100), "Hello")
    doc.save(src_path)
    doc.close()

    out = str(tmp_path / "clean.pdf")
    RemoveAnnotationsJob(
        input_path=src_path,
        output_path=out,
    ).execute()
    doc2 = fitz.open(out)
    assert list(doc2[0].annots()) == []


# ── Compress ──────────────────────────────────────────────────────────────────

def test_compress_low(sample_pdf, tmp_path):
    from pdf_forge.tools.secure.compress import CompressJob

    out = str(tmp_path / "comp.pdf")
    CompressJob(
        input_path=sample_pdf,
        output_path=out,
        level="low",
    ).execute()
    assert os.path.exists(out)
    # Output should exist and be a valid PDF
    import fitz
    doc = fitz.open(out)
    assert doc.page_count > 0


# ── Encrypt / Decrypt ─────────────────────────────────────────────────────────

def test_encrypt_decrypt_roundtrip(sample_pdf, tmp_path):
    import pikepdf
    from pdf_forge.tools.secure.encrypt import EncryptJob, DecryptJob

    enc_out = str(tmp_path / "enc.pdf")
    EncryptJob(
        input_path=sample_pdf,
        output_path=enc_out,
        user_password="hunter2",
        owner_password="owner999",
    ).execute()
    assert os.path.exists(enc_out)

    # Decrypt with correct password
    dec_out = str(tmp_path / "dec.pdf")
    DecryptJob(
        input_path=enc_out,
        output_path=dec_out,
        password="hunter2",
    ).execute()
    doc = pikepdf.open(dec_out)
    assert len(doc.pages) == 3


# ── Image → PDF ───────────────────────────────────────────────────────────────

def test_image_to_pdf(tmp_path):
    from PIL import Image
    from pdf_forge.tools.convert.image_to_pdf import ImageToPDFJob
    import fitz

    # Create a small test PNG
    img_path = str(tmp_path / "test.png")
    img = Image.new("RGB", (100, 100), color=(255, 0, 0))
    img.save(img_path)

    out = str(tmp_path / "from_image.pdf")
    result = ImageToPDFJob(
        input_paths=[img_path],
        output_path=out,
    ).execute()
    assert os.path.exists(out)
    doc = fitz.open(out)
    assert doc.page_count == 1


# ── PDF → Image ───────────────────────────────────────────────────────────────

def test_pdf_to_image(sample_pdf, tmp_path):
    from pdf_forge.tools.convert.pdf_to_image import PDFToImageJob

    out_dir = str(tmp_path / "images")
    result = PDFToImageJob(
        input_path=sample_pdf,
        output_dir=out_dir,
        fmt="png",
        dpi=72,
    ).execute()
    assert len(result.output_paths) == 3  # 3-page PDF
    for p in result.output_paths:
        assert os.path.exists(p)


# ── PDF → Text ────────────────────────────────────────────────────────────────

def test_pdf_to_text_plain(sample_pdf, tmp_path):
    from pdf_forge.tools.convert.pdf_to_text import PDFToTextJob

    out = str(tmp_path / "text.txt")
    PDFToTextJob(
        input_path=sample_pdf,
        output_path=out,
        mode="plain",
    ).execute()
    assert os.path.exists(out)
    content = open(out, encoding="utf-8").read()
    assert len(content) > 0


def test_pdf_to_text_json(sample_pdf, tmp_path):
    from pdf_forge.tools.convert.pdf_to_text import PDFToTextJob

    out = str(tmp_path / "blocks.json")
    PDFToTextJob(
        input_path=sample_pdf,
        output_path=out,
        mode="blocks",
    ).execute()
    data = json.loads(open(out).read())
    assert isinstance(data, list)
    assert len(data) == 3
