"""Add text watermark to all pages."""
from __future__ import annotations
import math
from typing import Any

import fitz

from pdf_forge.tools.base import BaseTool, ToolMeta
from pdf_forge.workers.job_model import Job, JobResult


class WatermarkJob(Job):
    """Stamp diagonal text watermark on every page using fitz."""

    def __init__(
        self,
        input_path: str,
        output_path: str,
        text: str,
        font_size: int = 60,
        opacity: float = 0.15,
        angle: float = 45.0,
        color: tuple[float, float, float] = (0.5, 0.5, 0.5),
        pages: list[int] | None = None,
    ) -> None:
        super().__init__("watermark", [input_path])
        self.output_path = output_path
        self.text = text
        self.font_size = font_size
        self.opacity = opacity
        self.angle = angle
        self.color = color
        self.pages = pages  # None = all pages

    def execute(self) -> JobResult:
        self.log(f"Adding watermark: '{self.text}'")
        doc = fitz.open(self.input_paths[0])
        target_pages = self.pages if self.pages is not None else list(range(doc.page_count))

        for i, pn in enumerate(target_pages):
            if self.cancel_flag:
                doc.close()
                raise Exception("Cancelled")

            page = doc[pn]
            rect = page.rect
            center = fitz.Point(rect.width / 2, rect.height / 2)

            # Measure text width to centre it
            tw = fitz.get_text_length(self.text, fontsize=self.font_size)
            th = self.font_size

            # Insert rotated text via a text writer for opacity support
            writer = fitz.TextWriter(rect, opacity=self.opacity, color=self.color)
            # Rotate insertion point around page centre
            rad = math.radians(self.angle)
            start = fitz.Point(
                center.x - math.cos(rad) * tw / 2,
                center.y + math.sin(rad) * tw / 2,
            )
            writer.append(start, self.text, fontsize=self.font_size)
            writer.write_text(page, morph=(center, fitz.Matrix(self.angle)))

            self.report_progress(int((i + 1) / len(target_pages) * 95))

        doc.save(self.output_path, deflate=True)
        doc.close()
        self.report_progress(100)
        return JobResult(output_paths=[self.output_path])


class WatermarkTool(BaseTool):
    meta = ToolMeta(
        tool_id="watermark",
        name="Add Watermark",
        description="Stamp a diagonal text watermark on all or selected pages.",
        category="edit",
        icon="watermark",
    )

    def create_job(self, params: dict[str, Any]) -> WatermarkJob:
        return WatermarkJob(
            input_path=params["input_path"],
            output_path=params["output_path"],
            text=params.get("text", "CONFIDENTIAL"),
            font_size=params.get("font_size", 60),
            opacity=params.get("opacity", 0.15),
            angle=params.get("angle", 45.0),
            color=params.get("color", (0.5, 0.5, 0.5)),
            pages=params.get("pages"),
        )
