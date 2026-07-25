"""Add blank page tool."""
from __future__ import annotations
from typing import Any

import pikepdf
from pikepdf import Pdf, Page, Dictionary, Name, Array

from pdf_forge.tools.base import BaseTool, ToolMeta
from pdf_forge.workers.job_model import Job, JobResult


class AddBlankPageJob(Job):
    """Inserts a blank page at the given position (0-indexed, -1 = end)."""

    def __init__(
        self,
        input_path: str,
        output_path: str,
        position: int,
        width_pt: float = 595.0,
        height_pt: float = 842.0,
    ) -> None:
        super().__init__("add_blank_page", [input_path])
        self.output_path = output_path
        self.position = position
        self.width_pt = width_pt
        self.height_pt = height_pt

    def execute(self) -> JobResult:
        self.log(f"Adding blank page at position {self.position}")
        with pikepdf.open(self.input_paths[0]) as pdf:
            # Build blank page via a temporary Pdf so the page dict is valid
            tmp = pikepdf.Pdf.new()
            tmp.add_blank_page(
                page_size=(self.width_pt, self.height_pt)
            )
            blank_page = pikepdf.Page(pdf.copy_foreign(tmp.pages[0].obj))

            if self.position < 0 or self.position >= len(pdf.pages):
                pdf.pages.append(blank_page)
            else:
                pdf.pages.insert(self.position, blank_page)

            pdf.save(self.output_path)
        self.report_progress(100)
        return JobResult(output_paths=[self.output_path])


class AddBlankPageTool(BaseTool):
    meta = ToolMeta(
        tool_id="add_blank_page",
        name="Add Blank Page",
        description="Insert a blank page at a specified position.",
        category="organize",
        icon="add_page",
    )

    def create_job(self, params: dict[str, Any]) -> AddBlankPageJob:
        return AddBlankPageJob(
            input_path=params["input_path"],
            output_path=params["output_path"],
            position=params.get("position", -1),
            width_pt=params.get("width_pt", 595.0),
            height_pt=params.get("height_pt", 842.0),
        )
