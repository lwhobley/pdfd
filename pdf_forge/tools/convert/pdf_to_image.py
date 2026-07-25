"""PDF → Image conversion tool.

Renders each page to PNG/JPEG/TIFF/BMP via fitz.
Returns list of output image paths.
"""
from __future__ import annotations
import os
from typing import Any

import fitz

from pdf_forge.tools.base import BaseTool, ToolMeta
from pdf_forge.workers.job_model import Job, JobResult

_FORMAT_EXT = {
    "png":  ".png",
    "jpeg": ".jpg",
    "jpg":  ".jpg",
    "tiff": ".tiff",
    "bmp":  ".bmp",
}


class PDFToImageJob(Job):
    def __init__(
        self,
        input_path: str,
        output_dir: str,
        fmt: str = "png",
        dpi: int = 150,
        pages: list[int] | None = None,
        prefix: str = "",
    ) -> None:
        super().__init__("pdf_to_image", [input_path])
        self.output_dir = output_dir
        self.fmt = fmt.lower()
        self.dpi = dpi
        self.pages = pages
        self.prefix = prefix or os.path.splitext(os.path.basename(input_path))[0]

    def execute(self) -> JobResult:
        ext = _FORMAT_EXT.get(self.fmt, ".png")
        self.log(f"Rendering to {self.fmt.upper()} at {self.dpi} DPI")

        os.makedirs(self.output_dir, exist_ok=True)
        doc = fitz.open(self.input_paths[0])
        target = self.pages if self.pages is not None else list(range(doc.page_count))
        zoom = self.dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)
        output_paths = []

        for i, pn in enumerate(target):
            if self.cancel_flag:
                doc.close()
                raise Exception("Cancelled")

            page = doc[pn]
            pix = page.get_pixmap(matrix=mat, alpha=False)

            pad = len(str(doc.page_count))
            out_name = f"{self.prefix}_p{str(pn + 1).zfill(pad)}{ext}"
            out_path = os.path.join(self.output_dir, out_name)

            if self.fmt in ("jpeg", "jpg"):
                pix.save(out_path, jpg_quality=85)
            else:
                pix.save(out_path)

            output_paths.append(out_path)
            self.report_progress(int((i + 1) / len(target) * 95))

        doc.close()
        self.report_progress(100)
        self.log(f"Exported {len(output_paths)} image(s) to {self.output_dir}")
        return JobResult(output_paths=output_paths)


class PDFToImageTool(BaseTool):
    meta = ToolMeta(
        tool_id="pdf_to_image",
        name="PDF → Image",
        description="Render PDF pages to PNG, JPEG, TIFF, or BMP image files.",
        category="convert",
        icon="pdf_to_image",
    )

    def create_job(self, params: dict[str, Any]) -> PDFToImageJob:
        return PDFToImageJob(
            input_path=params["input_path"],
            output_dir=params["output_dir"],
            fmt=params.get("fmt", "png"),
            dpi=params.get("dpi", 150),
            pages=params.get("pages"),
            prefix=params.get("prefix", ""),
        )
