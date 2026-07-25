"""Reorder pages tool — applies a custom page order to a PDF."""
from __future__ import annotations
from typing import Any

import pikepdf

from pdf_forge.tools.base import BaseTool, ToolMeta
from pdf_forge.workers.job_model import Job, JobResult


class ReorderPagesJob(Job):
    """Reorders pages according to a provided index list.

    page_order: list of original 0-based page indices in the desired output order.
    E.g. [2, 0, 1] moves page 3 first, then 1, then 2.
    """

    def __init__(
        self,
        input_path: str,
        output_path: str,
        page_order: list[int],
    ) -> None:
        super().__init__("reorder_pages", [input_path])
        self.output_path = output_path
        self.page_order = page_order

    def execute(self) -> JobResult:
        self.log(f"Reordering {len(self.page_order)} pages")
        with pikepdf.open(self.input_paths[0]) as src:
            with pikepdf.Pdf.new() as dst:
                for i, idx in enumerate(self.page_order):
                    if self.cancel_flag:
                        raise Exception("Cancelled")
                    dst.pages.append(src.pages[idx])
                    self.report_progress(int((i + 1) / len(self.page_order) * 95))
                dst.save(self.output_path)
        self.report_progress(100)
        return JobResult(output_paths=[self.output_path])


class ReorderPagesTool(BaseTool):
    meta = ToolMeta(
        tool_id="reorder_pages",
        name="Reorder Pages",
        description="Apply a custom page order to a PDF.",
        category="organize",
        icon="reorder",
    )

    def create_job(self, params: dict[str, Any]) -> ReorderPagesJob:
        return ReorderPagesJob(
            input_path=params["input_path"],
            output_path=params["output_path"],
            page_order=params["page_order"],
        )
