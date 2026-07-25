"""N-Up PDF tool — lay N source pages onto each output page.

Uses PyMuPDF (fitz) which has first-class support for page imposition
via Document.new_page() + page.show_pdf_page().
"""
from __future__ import annotations
import math
from typing import Any

import fitz

from pdf_forge.tools.base import BaseTool, ToolMeta
from pdf_forge.workers.job_model import Job, JobResult


# Layout grid (cols, rows) for common N-Up values
_LAYOUTS: dict[int, tuple[int, int]] = {
    2: (2, 1),
    4: (2, 2),
    6: (3, 2),
    8: (4, 2),
    9: (3, 3),
}


class NUpJob(Job):
    """Compose N source pages onto each output page.

    n: number of source pages per output page (2, 4, 6, 8, or 9)
    landscape: force landscape orientation on output pages
    """

    def __init__(
        self,
        input_path: str,
        output_path: str,
        n: int = 2,
        landscape: bool = True,
    ) -> None:
        super().__init__("nup_pdf", [input_path])
        self.output_path = output_path
        self.n = n
        self.landscape = landscape

    def execute(self) -> JobResult:
        cols, rows = _LAYOUTS.get(self.n, (2, 1))
        self.log(f"{self.n}-up layout ({cols}×{rows})")

        src = fitz.open(self.input_paths[0])
        total = src.page_count

        # Determine output page size from first source page
        sp = src[0].rect
        cell_w = sp.width
        cell_h = sp.height
        if self.landscape:
            out_w = cell_w * cols
            out_h = cell_h * rows
        else:
            out_w = cell_w * rows
            out_h = cell_h * cols

        dst = fitz.open()
        out_page_num = 0

        for start in range(0, total, self.n):
            if self.cancel_flag:
                src.close()
                dst.close()
                raise Exception("Cancelled")

            out_page = dst.new_page(width=out_w, height=out_h)

            for slot in range(self.n):
                src_idx = start + slot
                if src_idx >= total:
                    break
                col = slot % cols
                row = slot // cols
                x0 = col * cell_w
                y0 = row * cell_h
                rect = fitz.Rect(x0, y0, x0 + cell_w, y0 + cell_h)
                out_page.show_pdf_page(rect, src, src_idx)

            out_page_num += 1
            self.report_progress(int(out_page_num / math.ceil(total / self.n) * 95))

        dst.save(self.output_path)
        dst.close()
        src.close()
        self.report_progress(100)
        self.log(f"Created {out_page_num} output pages → {self.output_path}")
        return JobResult(output_paths=[self.output_path])


class NUpTool(BaseTool):
    meta = ToolMeta(
        tool_id="nup_pdf",
        name="N-Up PDF",
        description="Lay multiple source pages onto each output page (2-up, 4-up, etc.).",
        category="organize",
        icon="nup",
    )

    def create_job(self, params: dict[str, Any]) -> NUpJob:
        return NUpJob(
            input_path=params["input_path"],
            output_path=params["output_path"],
            n=params.get("n", 2),
            landscape=params.get("landscape", True),
        )
