"""Remove blank pages tool."""
from __future__ import annotations
from typing import Any

import fitz

from pdf_forge.tools.base import BaseTool, ToolMeta
from pdf_forge.workers.job_model import Job, JobResult
from pdf_forge.adapters.pikepdf_adapter import PikePDFAdapter


class RemoveBlankPagesJob(Job):
    def __init__(self, input_path: str, output_path: str) -> None:
        super().__init__("remove_blank_pages", [input_path])
        self.output_path = output_path

    def execute(self) -> JobResult:
        self.log("Scanning for blank pages…")
        removed = PikePDFAdapter.remove_blank_pages(
            self.input_paths[0],
            self.output_path,
            cancel_flag_fn=lambda: self.cancel_flag,
        )
        self.log(f"Removed {removed} blank page(s)")
        self.report_progress(100)
        return JobResult(output_paths=[self.output_path], metadata={"removed": removed})


class RemoveBlankPagesTool(BaseTool):
    meta = ToolMeta(
        tool_id="remove_blank_pages",
        name="Remove Blank Pages",
        description="Automatically detect and remove blank pages from a PDF.",
        category="organize",
        icon="remove_blank",
    )

    def create_job(self, params: dict[str, Any]) -> RemoveBlankPagesJob:
        return RemoveBlankPagesJob(
            input_path=params["input_path"],
            output_path=params["output_path"],
        )

    def apply_to_doc(self, doc: fitz.Document, params: dict[str, Any]) -> fitz.Document:
        """Detect and remove blank pages in-place."""
        removed = 0
        indices_to_delete = []

        for i in range(len(doc)):
            page = doc[i]
            # A page is blank if it has no text and no images
            text = page.get_text().strip()
            images = page.get_images()
            if not text and not images:
                indices_to_delete.append(i)
                removed += 1

        # Delete in reverse order to preserve indices
        for idx in sorted(indices_to_delete, reverse=True):
            doc.delete_page(idx)

        return doc
