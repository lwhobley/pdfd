"""Edit bookmarks (TOC) tool."""
from __future__ import annotations
from typing import Any

from pdf_forge.tools.base import BaseTool, ToolMeta
from pdf_forge.workers.job_model import Job, JobResult
from pdf_forge.adapters.pikepdf_adapter import PikePDFAdapter


class EditBookmarksJob(Job):
    def __init__(
        self,
        input_path: str,
        output_path: str,
        toc: list[tuple[int, str, int]],
    ) -> None:
        super().__init__("edit_bookmarks", [input_path])
        self.output_path = output_path
        self.toc = toc

    def execute(self) -> JobResult:
        self.log(f"Writing {len(self.toc)} bookmark entries")
        PikePDFAdapter.set_toc(self.input_paths[0], self.output_path, self.toc)
        self.report_progress(100)
        return JobResult(output_paths=[self.output_path])


class EditBookmarksTool(BaseTool):
    meta = ToolMeta(
        tool_id="edit_bookmarks",
        name="Edit Bookmarks",
        description="Add, edit, or remove bookmarks (table of contents) in a PDF.",
        category="organize",
        icon="bookmarks",
    )

    def create_job(self, params: dict[str, Any]) -> EditBookmarksJob:
        return EditBookmarksJob(
            input_path=params["input_path"],
            output_path=params["output_path"],
            toc=params["toc"],
        )
