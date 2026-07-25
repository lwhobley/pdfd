"""Split PDF tool — supports range-based and every-N-pages modes."""
from __future__ import annotations
import os
from typing import Any

from pdf_forge.tools.base import BaseTool, ToolMeta
from pdf_forge.workers.job_model import Job, JobResult
from pdf_forge.adapters.pikepdf_adapter import PikePDFAdapter


class SplitJob(Job):
    def __init__(
        self,
        input_path: str,
        output_dir: str,
        mode: str,         # "every_n" | "ranges"
        every_n: int = 1,
        ranges: list[tuple[int, int]] | None = None,
    ) -> None:
        super().__init__("split_pdf", [input_path])
        self.output_dir = output_dir
        self.mode = mode
        self.every_n = every_n
        self.ranges = ranges or []

    def execute(self) -> JobResult:
        input_path = self.input_paths[0]
        base = os.path.splitext(os.path.basename(input_path))[0]
        os.makedirs(self.output_dir, exist_ok=True)

        if self.mode == "every_n":
            self.log(f"Splitting every {self.every_n} pages")
            output_paths = PikePDFAdapter.split_every_n(
                input_path,
                n=self.every_n,
                output_dir=self.output_dir,
                base_name=base,
                cancel_flag_fn=lambda: self.cancel_flag,
            )
        else:
            output_paths = [
                os.path.join(self.output_dir, f"{base}_part{i + 1:03d}.pdf")
                for i in range(len(self.ranges))
            ]
            self.log(f"Splitting into {len(self.ranges)} ranges")
            PikePDFAdapter.split_by_range(
                input_path,
                self.ranges,
                output_paths,
                cancel_flag_fn=lambda: self.cancel_flag,
            )

        self.report_progress(100)
        self.log(f"Created {len(output_paths)} files in {self.output_dir}")
        return JobResult(output_paths=output_paths)


class SplitTool(BaseTool):
    meta = ToolMeta(
        tool_id="split_pdf",
        name="Split PDF",
        description="Split a PDF into multiple files by page range or every N pages.",
        category="organize",
        icon="split",
    )

    def create_job(self, params: dict[str, Any]) -> SplitJob:
        return SplitJob(
            input_path=params["input_path"],
            output_dir=params["output_dir"],
            mode=params.get("mode", "every_n"),
            every_n=params.get("every_n", 1),
            ranges=params.get("ranges"),
        )
