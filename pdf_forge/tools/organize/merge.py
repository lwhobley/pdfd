"""Merge PDFs tool."""
from __future__ import annotations
import os
from typing import Any

from pdf_forge.tools.base import BaseTool, ToolMeta
from pdf_forge.workers.job_model import Job, JobResult
from pdf_forge.adapters.pikepdf_adapter import PikePDFAdapter
from pdf_forge.core.exceptions import JobCancelledError


class MergeJob(Job):
    def __init__(self, input_paths: list[str], output_path: str) -> None:
        super().__init__("merge_pdfs", input_paths)
        self.output_path = output_path

    def execute(self) -> JobResult:
        self.log(f"Merging {len(self.input_paths)} files → {self.output_path}")
        total = len(self.input_paths)

        def cancel_check():
            if self.cancel_flag:
                raise JobCancelledError()

        for i, path in enumerate(self.input_paths):
            cancel_check()
            self.report_progress(int(i / total * 80))

        PikePDFAdapter.merge(
            self.input_paths,
            self.output_path,
            preserve_bookmarks=True,
            cancel_flag_fn=lambda: self.cancel_flag,
        )
        self.report_progress(100)
        return JobResult(output_paths=[self.output_path])


class MergeTool(BaseTool):
    meta = ToolMeta(
        tool_id="merge_pdfs",
        name="Merge PDFs",
        description="Combine multiple PDF files into one, preserving bookmarks.",
        category="organize",
        icon="merge",
    )

    def create_job(self, params: dict[str, Any]) -> MergeJob:
        return MergeJob(
            input_paths=params["input_paths"],
            output_path=params["output_path"],
        )
