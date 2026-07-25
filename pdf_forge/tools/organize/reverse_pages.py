"""Reverse pages tool."""
from __future__ import annotations
from typing import Any

import pikepdf

from pdf_forge.tools.base import BaseTool, ToolMeta
from pdf_forge.workers.job_model import Job, JobResult


class ReversePagesJob(Job):
    def __init__(self, input_path: str, output_path: str) -> None:
        super().__init__("reverse_pages", [input_path])
        self.output_path = output_path

    def execute(self) -> JobResult:
        self.log("Reversing page order")
        with pikepdf.open(self.input_paths[0]) as pdf:
            with pikepdf.Pdf.new() as dst:
                for page in reversed(pdf.pages):
                    if self.cancel_flag:
                        raise Exception("Cancelled")
                    dst.pages.append(page)
                dst.save(self.output_path)
        self.report_progress(100)
        return JobResult(output_paths=[self.output_path])


class ReversePagesTool(BaseTool):
    meta = ToolMeta(
        tool_id="reverse_pages",
        name="Reverse Pages",
        description="Reverse the order of all pages in a PDF.",
        category="organize",
        icon="reverse",
    )

    def create_job(self, params: dict[str, Any]) -> ReversePagesJob:
        return ReversePagesJob(
            input_path=params["input_path"],
            output_path=params["output_path"],
        )
