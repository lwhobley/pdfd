"""OCR PDF tool — make scanned PDFs text-searchable.

Strategy (best quality path, Tesseract required):
  For each page → render to PIL image → Tesseract image_to_pdf →
  overlay the resulting searchable layer on the original page.

Fallback (EasyOCR or text-only):
  Extract text strings per page and add as invisible text annotations.
"""
from __future__ import annotations
import io
import os
from typing import Any

import fitz
from PIL import Image

from pdf_forge.tools.base import BaseTool, ToolMeta
from pdf_forge.workers.job_model import Job, JobResult
from pdf_forge.services.ocr_service import OCRService


class OCRJob(Job):
    def __init__(
        self,
        input_path: str,
        output_path: str,
        dpi: int = 200,
        language: str = "eng",
        tesseract_cmd: str = "",
        pages: list[int] | None = None,
        skip_text_pages: bool = True,
    ) -> None:
        super().__init__("ocr_pdf", [input_path])
        self.output_path = output_path
        self.dpi = dpi
        self.language = language
        self.tesseract_cmd = tesseract_cmd
        self.pages = pages
        self.skip_text_pages = skip_text_pages

    def execute(self) -> JobResult:
        ocr = OCRService(tesseract_cmd=self.tesseract_cmd, language=self.language)
        if not ocr.is_available():
            raise Exception(
                "No OCR backend found. Install Tesseract and pytesseract, "
                "or install easyocr."
            )
        self.log(f"OCR backend: {ocr.backend_name}  DPI: {self.dpi}")

        src = fitz.open(self.input_paths[0])
        target = self.pages if self.pages is not None else list(range(src.page_count))
        zoom = self.dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)

        if ocr.backend_name == "tesseract":
            self._ocr_with_tesseract(src, target, mat, ocr)
        else:
            self._ocr_text_overlay(src, target, mat, ocr)

        src.close()
        self.report_progress(100)
        return JobResult(output_paths=[self.output_path])

    def _ocr_with_tesseract(self, src, target, mat, ocr: OCRService) -> None:
        """Render each page to image → Tesseract PDF → merge back."""
        parts: list[bytes] = []

        for i, pn in enumerate(target):
            if self.cancel_flag:
                raise Exception("Cancelled")

            page = src[pn]

            if self.skip_text_pages and page.get_text().strip():
                self.log(f"Page {pn+1}: already has text, copying as-is")
                tmp = fitz.open()
                tmp.insert_pdf(src, from_page=pn, to_page=pn)
                parts.append(tmp.tobytes())
                tmp.close()
            else:
                pix = page.get_pixmap(matrix=mat, alpha=False)
                img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                pdf_bytes = ocr.ocr_page_to_pdf_bytes(img)
                if pdf_bytes:
                    parts.append(pdf_bytes)
                else:
                    # Tesseract returned nothing — copy original
                    tmp = fitz.open()
                    tmp.insert_pdf(src, from_page=pn, to_page=pn)
                    parts.append(tmp.tobytes())
                    tmp.close()

            self.report_progress(int((i + 1) / len(target) * 90))

        # Merge all single-page PDFs
        dst = fitz.open()
        for part in parts:
            tmp = fitz.open("pdf", part)
            dst.insert_pdf(tmp)
            tmp.close()
        dst.save(self.output_path, deflate=True)
        dst.close()

    def _ocr_text_overlay(self, src, target, mat, ocr: OCRService) -> None:
        """Add invisible text overlay using EasyOCR results."""
        for i, pn in enumerate(target):
            if self.cancel_flag:
                raise Exception("Cancelled")
            page = src[pn]
            if self.skip_text_pages and page.get_text().strip():
                continue
            pix = page.get_pixmap(matrix=mat, alpha=False)
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            text = ocr.ocr_page_image(img)
            if text.strip():
                # Add as small invisible text at page top
                page.insert_text(
                    fitz.Point(0, 10),
                    text,
                    fontsize=1,
                    color=(1, 1, 1),  # white = invisible
                    render_mode=3,    # invisible
                )
            self.report_progress(int((i + 1) / len(target) * 90))

        src.save(self.output_path, deflate=True)


class OCRTool(BaseTool):
    meta = ToolMeta(
        tool_id="ocr_pdf",
        name="OCR PDF",
        description="Make scanned PDFs text-searchable using Tesseract or EasyOCR.",
        category="convert",
        icon="ocr",
        requires=["tesseract"],
    )

    def create_job(self, params: dict[str, Any]) -> OCRJob:
        return OCRJob(
            input_path=params["input_path"],
            output_path=params["output_path"],
            dpi=params.get("dpi", 200),
            language=params.get("language", "eng"),
            tesseract_cmd=params.get("tesseract_cmd", ""),
            pages=params.get("pages"),
            skip_text_pages=params.get("skip_text_pages", True),
        )
