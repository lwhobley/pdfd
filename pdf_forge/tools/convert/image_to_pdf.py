"""Image → PDF conversion tool.

Supports: PNG, JPG, JPEG, BMP, TIFF, WEBP, GIF (first frame), HEIC.
Each image becomes one page; page size matches image dimensions at 72 DPI.
"""
from __future__ import annotations
import os
from typing import Any

import fitz
from PIL import Image

from pdf_forge.tools.base import BaseTool, ToolMeta
from pdf_forge.workers.job_model import Job, JobResult

_SUPPORTED_EXT = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".webp", ".gif"}


class ImageToPDFJob(Job):
    """Convert one or more image files into a single PDF."""

    def __init__(
        self,
        input_paths: list[str],
        output_path: str,
        page_size: str = "image",  # "image" | "a4" | "letter"
        fit_to_page: bool = False,
        dpi: int = 72,
    ) -> None:
        super().__init__("image_to_pdf", input_paths)
        self.output_path = output_path
        self.page_size = page_size
        self.fit_to_page = fit_to_page
        self.dpi = dpi

    def execute(self) -> JobResult:
        self.log(f"Converting {len(self.input_paths)} image(s) to PDF")
        _PAGE_SIZES = {
            "a4":     (595, 842),
            "letter": (612, 792),
        }

        dst = fitz.open()
        total = len(self.input_paths)

        for i, img_path in enumerate(self.input_paths):
            if self.cancel_flag:
                dst.close()
                raise Exception("Cancelled")

            ext = os.path.splitext(img_path)[1].lower()
            if ext not in _SUPPORTED_EXT:
                self.log(f"Skipping unsupported file: {img_path}")
                continue

            # Get image dimensions via PIL
            with Image.open(img_path) as im:
                iw, ih = im.size
                mode = im.mode

            pt_w = iw * 72 / self.dpi
            pt_h = ih * 72 / self.dpi

            if self.page_size in _PAGE_SIZES:
                page_w, page_h = _PAGE_SIZES[self.page_size]
            else:
                page_w, page_h = pt_w, pt_h

            page = dst.new_page(width=page_w, height=page_h)

            if self.fit_to_page and self.page_size in _PAGE_SIZES:
                # Scale image to fit page with margin
                margin = 20
                avail_w = page_w - 2 * margin
                avail_h = page_h - 2 * margin
                scale = min(avail_w / pt_w, avail_h / pt_h, 1.0)
                iw_pt = pt_w * scale
                ih_pt = pt_h * scale
                x0 = (page_w - iw_pt) / 2
                y0 = (page_h - ih_pt) / 2
                rect = fitz.Rect(x0, y0, x0 + iw_pt, y0 + ih_pt)
            else:
                rect = fitz.Rect(0, 0, page_w, page_h)

            page.insert_image(rect, filename=img_path)
            self.report_progress(int((i + 1) / total * 95))

        dst.save(self.output_path, deflate=True)
        dst.close()
        self.report_progress(100)
        self.log(f"Saved → {self.output_path}")
        return JobResult(output_paths=[self.output_path])


class ImageToPDFTool(BaseTool):
    meta = ToolMeta(
        tool_id="image_to_pdf",
        name="Image → PDF",
        description="Convert images (PNG, JPG, TIFF, BMP, WEBP) to a PDF.",
        category="convert",
        icon="image_to_pdf",
    )

    def create_job(self, params: dict[str, Any]) -> ImageToPDFJob:
        return ImageToPDFJob(
            input_paths=params["input_paths"],
            output_path=params["output_path"],
            page_size=params.get("page_size", "image"),
            fit_to_page=params.get("fit_to_page", False),
            dpi=params.get("dpi", 72),
        )
