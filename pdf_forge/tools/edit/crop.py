"""Crop PDF pages by setting CropBox."""
from __future__ import annotations
from typing import Any

import fitz

from pdf_forge.tools.base import BaseTool, ToolMeta
from pdf_forge.workers.job_model import Job, JobResult


class CropJob(Job):
    """Set CropBox on all (or specified) pages.

    Margins are in points (1/72 inch) from each edge.
    A positive margin trims content; negative expands (adds white space).
    """

    def __init__(
        self,
        input_path: str,
        output_path: str,
        margin_top: float,
        margin_right: float,
        margin_bottom: float,
        margin_left: float,
        pages: list[int] | None = None,
    ) -> None:
        super().__init__("crop_pdf", [input_path])
        self.output_path = output_path
        self.margin_top = margin_top
        self.margin_right = margin_right
        self.margin_bottom = margin_bottom
        self.margin_left = margin_left
        self.pages = pages

    def execute(self) -> JobResult:
        self.log(
            f"Cropping margins: T={self.margin_top} R={self.margin_right} "
            f"B={self.margin_bottom} L={self.margin_left}"
        )
        doc = fitz.open(self.input_paths[0])
        target = self.pages if self.pages is not None else list(range(doc.page_count))

        for i, pn in enumerate(target):
            if self.cancel_flag:
                doc.close()
                raise Exception("Cancelled")
            page = doc[pn]
            mb = page.mediabox
            crop = fitz.Rect(
                mb.x0 + self.margin_left,
                mb.y0 + self.margin_top,
                mb.x1 - self.margin_right,
                mb.y1 - self.margin_bottom,
            )
            # Clamp to mediabox
            crop = crop & mb
            page.set_cropbox(crop)
            self.report_progress(int((i + 1) / len(target) * 95))

        doc.save(self.output_path, deflate=True)
        doc.close()
        self.report_progress(100)
        return JobResult(output_paths=[self.output_path])


class CropTool(BaseTool):
    meta = ToolMeta(
        tool_id="crop_pdf",
        name="Crop PDF",
        description="Set crop margins on all or selected pages.",
        category="edit",
        icon="crop",
    )

    def create_job(self, params: dict[str, Any]) -> CropJob:
        return CropJob(
            input_path=params["input_path"],
            output_path=params["output_path"],
            margin_top=float(params.get("margin_top", 0)),
            margin_right=float(params.get("margin_right", 0)),
            margin_bottom=float(params.get("margin_bottom", 0)),
            margin_left=float(params.get("margin_left", 0)),
            pages=params.get("pages"),
        )
