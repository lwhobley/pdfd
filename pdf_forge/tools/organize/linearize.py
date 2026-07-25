"""Linearize PDF for fast web viewing (optimized for streaming)."""
from __future__ import annotations
from typing import Any

import pikepdf

from pdf_forge.tools.base import BaseTool, ToolMeta
from pdf_forge.workers.job_model import Job, JobResult


class LinearizeJob(Job):
    def __init__(self, input_path: str, output_path: str) -> None:
        super().__init__("linearize_pdf", [input_path])
        self.output_path = output_path

    def execute(self) -> JobResult:
        self.log("Linearizing PDF for fast web open")
        with pikepdf.open(self.input_paths[0]) as pdf:
            pdf.save(
                self.output_path,
                linearize=True,
                compress_streams=True,
            )
        self.report_progress(100)
        self.log("Linearization complete")
        return JobResult(output_paths=[self.output_path])


class LinearizeTool(BaseTool):
    meta = ToolMeta(
        tool_id="linearize_pdf",
        name="Linearize PDF",
        description="Optimize PDF for fast web viewing (byte-range requests).",
        category="organize",
        icon="linearize",
    )

    def create_job(self, params: dict[str, Any]) -> LinearizeJob:
        return LinearizeJob(
            input_path=params["input_path"],
            output_path=params["output_path"],
        )
