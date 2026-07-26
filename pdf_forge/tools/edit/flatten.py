"""Flatten PDF — bake annotations and form fields into page content."""
from __future__ import annotations
from typing import Any

import fitz

from pdf_forge.tools.base import BaseTool, ToolMeta
from pdf_forge.workers.job_model import Job, JobResult


class FlattenJob(Job):
    """Render each page to a pixmap and rebuild the PDF.

    This permanently bakes all annotations, form fields, and overlays
    into the page content, removing all interactive elements.
    render_dpi controls output quality (150 dpi is a good balance).
    """

    def __init__(
        self,
        input_path: str,
        output_path: str,
        render_dpi: int = 150,
    ) -> None:
        super().__init__("flatten_pdf", [input_path])
        self.output_path = output_path
        self.render_dpi = render_dpi

    def execute(self) -> JobResult:
        self.log(f"Flattening PDF at {self.render_dpi} DPI")
        src = fitz.open(self.input_paths[0])
        dst = fitz.open()
        zoom = self.render_dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)

        for i, page in enumerate(src):
            if self.cancel_flag:
                src.close()
                dst.close()
                raise Exception("Cancelled")

            pix = page.get_pixmap(matrix=mat, alpha=False)
            # Create new page same dimensions as original
            new_page = dst.new_page(width=page.rect.width, height=page.rect.height)
            # Insert the rasterized image
            new_page.insert_image(new_page.rect, pixmap=pix)
            self.report_progress(int((i + 1) / src.page_count * 95))

        dst.save(self.output_path, deflate=True)
        dst.close()
        src.close()
        self.report_progress(100)
        return JobResult(output_paths=[self.output_path])


class FlattenTool(BaseTool):
    meta = ToolMeta(
        tool_id="flatten_pdf",
        name="Flatten PDF",
        description="Bake annotations and form fields permanently into page content.",
        category="edit",
        icon="flatten",
    )

    def create_job(self, params: dict[str, Any]) -> FlattenJob:
        return FlattenJob(
            input_path=params["input_path"],
            output_path=params["output_path"],
            render_dpi=params.get("render_dpi", 150),
        )

    def apply_to_doc(self, doc: fitz.Document, params: dict[str, Any]) -> fitz.Document:
        """Flatten annotations in-place by rasterizing to new doc, then swapping pages."""
        render_dpi = params.get("render_dpi", 150)
        zoom = render_dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)

        # Create temporary doc for rasterized pages
        dst = fitz.open()
        for page in doc:
            pix = page.get_pixmap(matrix=mat, alpha=False)
            new_page = dst.new_page(width=page.rect.width, height=page.rect.height)
            new_page.insert_image(new_page.rect, pixmap=pix)

        # Swap pages: delete all original pages and replace with flattened
        for i in range(len(doc) - 1, -1, -1):
            doc.delete_page(i)
        for page in dst:
            doc.insert_pdf(dst, from_page=page.number, to_page=page.number)

        dst.close()
        return doc
