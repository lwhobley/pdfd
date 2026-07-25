"""Add page numbers to a PDF."""
from __future__ import annotations
from typing import Any

import fitz

from pdf_forge.tools.base import BaseTool, ToolMeta
from pdf_forge.workers.job_model import Job, JobResult

# (relative_x, relative_y) on page — (0,0) = top-left, (1,1) = bottom-right
_POSITION_MAP = {
    "bottom-center":  (0.5,  0.96),
    "bottom-left":    (0.05, 0.96),
    "bottom-right":   (0.95, 0.96),
    "top-center":     (0.5,  0.03),
    "top-left":       (0.05, 0.03),
    "top-right":      (0.95, 0.03),
}


class PageNumbersJob(Job):
    def __init__(
        self,
        input_path: str,
        output_path: str,
        start_number: int = 1,
        prefix: str = "",
        suffix: str = "",
        include_total: bool = False,
        position: str = "bottom-center",
        font_size: int = 10,
        color: tuple[float, float, float] = (0.0, 0.0, 0.0),
        skip_first: bool = False,
    ) -> None:
        super().__init__("add_page_numbers", [input_path])
        self.output_path = output_path
        self.start_number = start_number
        self.prefix = prefix
        self.suffix = suffix
        self.include_total = include_total
        self.position = position
        self.font_size = font_size
        self.color = color
        self.skip_first = skip_first

    def execute(self) -> JobResult:
        self.log(f"Adding page numbers ({self.position})")
        doc = fitz.open(self.input_paths[0])
        total = doc.page_count

        rel_x, rel_y = _POSITION_MAP.get(self.position, (0.5, 0.96))

        for i in range(total):
            if self.cancel_flag:
                doc.close()
                raise Exception("Cancelled")
            if self.skip_first and i == 0:
                continue

            page = doc[i]
            n = i + self.start_number
            if self.include_total:
                label = f"{self.prefix}{n} / {total + self.start_number - 1}{self.suffix}"
            else:
                label = f"{self.prefix}{n}{self.suffix}"

            w = page.rect.width
            h = page.rect.height
            tw = fitz.get_text_length(label, fontsize=self.font_size)
            x = w * rel_x - tw / 2
            y = h * rel_y

            page.insert_text(
                fitz.Point(x, y),
                label,
                fontsize=self.font_size,
                color=self.color,
            )
            self.report_progress(int((i + 1) / total * 95))

        doc.save(self.output_path, deflate=True)
        doc.close()
        self.report_progress(100)
        return JobResult(output_paths=[self.output_path])


class PageNumbersTool(BaseTool):
    meta = ToolMeta(
        tool_id="add_page_numbers",
        name="Add Page Numbers",
        description="Stamp page numbers at a chosen position on each page.",
        category="edit",
        icon="page_numbers",
    )

    def create_job(self, params: dict[str, Any]) -> PageNumbersJob:
        return PageNumbersJob(
            input_path=params["input_path"],
            output_path=params["output_path"],
            start_number=params.get("start_number", 1),
            prefix=params.get("prefix", ""),
            suffix=params.get("suffix", ""),
            include_total=params.get("include_total", False),
            position=params.get("position", "bottom-center"),
            font_size=params.get("font_size", 10),
            color=params.get("color", (0.0, 0.0, 0.0)),
            skip_first=params.get("skip_first", False),
        )
