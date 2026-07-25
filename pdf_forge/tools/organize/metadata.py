"""Edit PDF metadata tool."""
from __future__ import annotations
from typing import Any

from pdf_forge.tools.base import BaseTool, ToolMeta
from pdf_forge.workers.job_model import Job, JobResult
from pdf_forge.adapters.pikepdf_adapter import PikePDFAdapter


class EditMetadataJob(Job):
    def __init__(
        self,
        input_path: str,
        output_path: str,
        metadata: dict[str, str],
    ) -> None:
        super().__init__("edit_metadata", [input_path])
        self.output_path = output_path
        self.metadata = metadata

    def execute(self) -> JobResult:
        self.log(f"Writing metadata to {self.output_path}")
        PikePDFAdapter.set_metadata(self.input_paths[0], self.output_path, self.metadata)
        self.report_progress(100)
        return JobResult(output_paths=[self.output_path])


class EditMetadataTool(BaseTool):
    meta = ToolMeta(
        tool_id="edit_metadata",
        name="Edit Metadata",
        description="View and edit PDF document metadata (title, author, subject, etc.).",
        category="organize",
        icon="metadata",
    )

    def create_job(self, params: dict[str, Any]) -> EditMetadataJob:
        return EditMetadataJob(
            input_path=params["input_path"],
            output_path=params["output_path"],
            metadata=params["metadata"],
        )
