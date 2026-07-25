"""Bates numbering tool."""
from __future__ import annotations
from typing import Any

import fitz

from pdf_forge.tools.base import BaseTool, ToolMeta
from pdf_forge.workers.job_model import Job, JobResult


class BatesNumberJob(Job):
    """Add zero-padded Bates numbers to each page.

    Format: {prefix}{zero_padded_number}{suffix}
    Example: ACME-000001 through ACME-000042
    """

    def __init__(
        self,
        input_path: str,
        output_path: str,
        prefix: str = "",
        suffix: str = "",
        start_number: int = 1,
        pad_width: int = 6,
        position: str = "bottom-right",
        font_size: int = 9,
    ) -> None:
        super().__init__("bates_number", [input_path])
        self.output_path = output_path
        self.prefix = prefix
        self.suffix = suffix
        self.start_number = start_number
        self.pad_width = pad_width
        self.position = position
        self.font_size = font_size

    def execute(self) -> JobResult:
        from pdf_forge.tools.edit.page_numbers import _POSITION_MAP
        self.log(f"Applying Bates numbering: {self.prefix}{'0' * self.pad_width}{self.suffix}")
        doc = fitz.open(self.input_paths[0])
        total = doc.page_count
        rel_x, rel_y = _POSITION_MAP.get(self.position, (0.95, 0.96))

        for i in range(total):
            if self.cancel_flag:
                doc.close()
                raise Exception("Cancelled")

            page = doc[i]
            n = self.start_number + i
            label = f"{self.prefix}{str(n).zfill(self.pad_width)}{self.suffix}"
            w = page.rect.width
            h = page.rect.height
            tw = fitz.get_text_length(label, fontsize=self.font_size)

            # Right-align or centre depending on position
            rel_x_val, _ = _POSITION_MAP.get(self.position, (0.95, 0.96))
            x = w * rel_x_val - (tw if rel_x_val > 0.8 else tw / 2)
            y = h * rel_y

            page.insert_text(
                fitz.Point(x, y),
                label,
                fontsize=self.font_size,
                color=(0.0, 0.0, 0.0),
            )
            self.report_progress(int((i + 1) / total * 95))

        doc.save(self.output_path, deflate=True)
        doc.close()
        self.report_progress(100)
        end_number = self.start_number + total - 1
        self.log(f"Bates range: {self.prefix}{str(self.start_number).zfill(self.pad_width)} – "
                 f"{self.prefix}{str(end_number).zfill(self.pad_width)}")
        return JobResult(
            output_paths=[self.output_path],
            metadata={"end_number": end_number},
        )


class BatesNumberTool(BaseTool):
    meta = ToolMeta(
        tool_id="bates_number",
        name="Bates Numbering",
        description="Apply sequential Bates numbers to each page for legal/discovery workflows.",
        category="edit",
        icon="bates",
    )

    def create_job(self, params: dict[str, Any]) -> BatesNumberJob:
        return BatesNumberJob(
            input_path=params["input_path"],
            output_path=params["output_path"],
            prefix=params.get("prefix", ""),
            suffix=params.get("suffix", ""),
            start_number=params.get("start_number", 1),
            pad_width=params.get("pad_width", 6),
            position=params.get("position", "bottom-right"),
            font_size=params.get("font_size", 9),
        )
