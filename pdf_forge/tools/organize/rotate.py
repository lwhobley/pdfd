"""Rotate pages tool."""
from __future__ import annotations
from typing import Any

from pdf_forge.tools.base import BaseTool, ToolMeta
from pdf_forge.workers.job_model import Job, JobResult
from pdf_forge.adapters.pikepdf_adapter import PikePDFAdapter


class RotateJob(Job):
    def __init__(
        self,
        input_path: str,
        output_path: str,
        page_indices: list[int],  # empty = all pages
        degrees: int,
    ) -> None:
        super().__init__("rotate_pages", [input_path])
        self.output_path = output_path
        self.page_indices = page_indices
        self.degrees = degrees

    def execute(self) -> JobResult:
        import pikepdf
        if not self.page_indices:
            with pikepdf.open(self.input_paths[0]) as pdf:
                self.page_indices = list(range(len(pdf.pages)))

        self.log(
            f"Rotating {len(self.page_indices)} page(s) by {self.degrees}°"
        )
        PikePDFAdapter.rotate_pages(
            self.input_paths[0],
            self.output_path,
            self.page_indices,
            self.degrees,
            cancel_flag_fn=lambda: self.cancel_flag,
        )
        self.report_progress(100)
        return JobResult(output_paths=[self.output_path])


class RotateTool(BaseTool):
    meta = ToolMeta(
        tool_id="rotate_pages",
        name="Rotate Pages",
        description="Rotate all or selected pages by 90, 180, or 270 degrees.",
        category="organize",
        icon="rotate",
    )

    def create_job(self, params: dict[str, Any]) -> RotateJob:
        return RotateJob(
            input_path=params["input_path"],
            output_path=params["output_path"],
            page_indices=params.get("page_indices", []),
            degrees=params.get("degrees", 90),
        )
