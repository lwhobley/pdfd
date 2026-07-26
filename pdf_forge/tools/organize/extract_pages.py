"""Extract pages tool."""
from __future__ import annotations
from typing import Any

import fitz

from pdf_forge.tools.base import BaseTool, ToolMeta
from pdf_forge.workers.job_model import Job, JobResult
from pdf_forge.adapters.pikepdf_adapter import PikePDFAdapter


class ExtractPagesJob(Job):
    def __init__(
        self, input_path: str, output_path: str, page_indices: list[int]
    ) -> None:
        super().__init__("extract_pages", [input_path])
        self.output_path = output_path
        self.page_indices = page_indices

    def execute(self) -> JobResult:
        self.log(f"Extracting {len(self.page_indices)} page(s)")
        PikePDFAdapter.extract_pages(
            self.input_paths[0],
            self.output_path,
            self.page_indices,
            cancel_flag_fn=lambda: self.cancel_flag,
        )
        self.report_progress(100)
        return JobResult(output_paths=[self.output_path])


class ExtractPagesTool(BaseTool):
    meta = ToolMeta(
        tool_id="extract_pages",
        name="Extract Pages",
        description="Extract selected pages into a new PDF file.",
        category="organize",
        icon="extract",
    )

    def create_job(self, params: dict[str, Any]) -> ExtractPagesJob:
        return ExtractPagesJob(
            input_path=params["input_path"],
            output_path=params["output_path"],
            page_indices=params["page_indices"],
        )

    def apply_to_doc(self, doc: fitz.Document, params: dict[str, Any]) -> fitz.Document:
        """Extract pages: keep only the specified pages in-place."""
        page_indices = set(params["page_indices"])
        # Delete pages not in the extract list, in reverse order
        for idx in range(len(doc) - 1, -1, -1):
            if idx not in page_indices:
                doc.delete_page(idx)
        return doc
