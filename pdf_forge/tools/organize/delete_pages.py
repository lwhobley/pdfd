"""Delete pages tool."""
from __future__ import annotations
from typing import Any

from pdf_forge.tools.base import BaseTool, ToolMeta
from pdf_forge.workers.job_model import Job, JobResult
from pdf_forge.adapters.pikepdf_adapter import PikePDFAdapter


class DeletePagesJob(Job):
    def __init__(
        self, input_path: str, output_path: str, page_indices: list[int]
    ) -> None:
        super().__init__("delete_pages", [input_path])
        self.output_path = output_path
        self.page_indices = page_indices

    def execute(self) -> JobResult:
        self.log(f"Deleting {len(self.page_indices)} page(s)")
        PikePDFAdapter.delete_pages(
            self.input_paths[0],
            self.output_path,
            self.page_indices,
            cancel_flag_fn=lambda: self.cancel_flag,
        )
        self.report_progress(100)
        return JobResult(output_paths=[self.output_path])


class DeletePagesTool(BaseTool):
    meta = ToolMeta(
        tool_id="delete_pages",
        name="Delete Pages",
        description="Remove one or more pages from a PDF.",
        category="organize",
        icon="delete_page",
    )

    def create_job(self, params: dict[str, Any]) -> DeletePagesJob:
        return DeletePagesJob(
            input_path=params["input_path"],
            output_path=params["output_path"],
            page_indices=params["page_indices"],
        )
