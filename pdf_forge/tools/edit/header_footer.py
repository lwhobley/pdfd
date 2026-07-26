"""Add header and/or footer text to a PDF."""
from __future__ import annotations
from typing import Any

import fitz

from pdf_forge.tools.base import BaseTool, ToolMeta
from pdf_forge.workers.job_model import Job, JobResult

# Supported tokens: {page}, {total}, {filename}, {date}
_MARGIN = 24  # points from edge


class HeaderFooterJob(Job):
    def __init__(
        self,
        input_path: str,
        output_path: str,
        header_left: str = "",
        header_center: str = "",
        header_right: str = "",
        footer_left: str = "",
        footer_center: str = "",
        footer_right: str = "",
        font_size: int = 9,
        color: tuple[float, float, float] = (0.3, 0.3, 0.3),
        skip_first: bool = False,
    ) -> None:
        super().__init__("header_footer", [input_path])
        self.output_path = output_path
        self.header_left = header_left
        self.header_center = header_center
        self.header_right = header_right
        self.footer_left = footer_left
        self.footer_center = footer_center
        self.footer_right = footer_right
        self.font_size = font_size
        self.color = color
        self.skip_first = skip_first

    def execute(self) -> JobResult:
        import os
        from datetime import date

        self.log("Adding header/footer")
        doc = fitz.open(self.input_paths[0])
        total = doc.page_count
        filename = os.path.basename(self.input_paths[0])
        today = date.today().strftime("%Y-%m-%d")

        def _resolve(template: str, page_num: int) -> str:
            return (
                template
                .replace("{page}", str(page_num))
                .replace("{total}", str(total))
                .replace("{filename}", filename)
                .replace("{date}", today)
            )

        for i in range(total):
            if self.cancel_flag:
                doc.close()
                raise Exception("Cancelled")
            if self.skip_first and i == 0:
                continue

            page = doc[i]
            w = page.rect.width
            h = page.rect.height
            n = i + 1
            fs = self.font_size

            def _insert(text: str, x: float, y: float, align_right: bool = False) -> None:
                if not text:
                    return
                t = _resolve(text, n)
                tw = fitz.get_text_length(t, fontsize=fs)
                px = (x - tw) if align_right else x
                page.insert_text(fitz.Point(px, y), t, fontsize=fs, color=self.color)

            header_y = _MARGIN
            footer_y = h - _MARGIN + fs

            _insert(self.header_left,   _MARGIN,         header_y)
            _insert(self.header_center, w / 2 - fitz.get_text_length(_resolve(self.header_center, n), fontsize=fs) / 2, header_y)
            _insert(self.header_right,  w - _MARGIN,     header_y, align_right=True)

            _insert(self.footer_left,   _MARGIN,         footer_y)
            _insert(self.footer_center, w / 2 - fitz.get_text_length(_resolve(self.footer_center, n), fontsize=fs) / 2, footer_y)
            _insert(self.footer_right,  w - _MARGIN,     footer_y, align_right=True)

            self.report_progress(int((i + 1) / total * 95))

        doc.save(self.output_path, deflate=True)
        doc.close()
        self.report_progress(100)
        return JobResult(output_paths=[self.output_path])


class HeaderFooterTool(BaseTool):
    meta = ToolMeta(
        tool_id="header_footer",
        name="Header & Footer",
        description="Add custom header and footer text with {page}, {total}, {date} tokens.",
        category="edit",
        icon="header_footer",
    )

    def create_job(self, params: dict[str, Any]) -> HeaderFooterJob:
        return HeaderFooterJob(
            input_path=params["input_path"],
            output_path=params["output_path"],
            header_left=params.get("header_left", ""),
            header_center=params.get("header_center", ""),
            header_right=params.get("header_right", ""),
            footer_left=params.get("footer_left", ""),
            footer_center=params.get("footer_center", ""),
            footer_right=params.get("footer_right", ""),
            font_size=params.get("font_size", 9),
            color=params.get("color", (0.3, 0.3, 0.3)),
            skip_first=params.get("skip_first", False),
        )

    def apply_to_doc(self, doc: fitz.Document, params: dict[str, Any]) -> fitz.Document:
        """Add header/footer text to pages in-place."""
        import os
        from datetime import date

        header_left = params.get("header_left", "")
        header_center = params.get("header_center", "")
        header_right = params.get("header_right", "")
        footer_left = params.get("footer_left", "")
        footer_center = params.get("footer_center", "")
        footer_right = params.get("footer_right", "")
        font_size = params.get("font_size", 9)
        color = params.get("color", (0.3, 0.3, 0.3))
        skip_first = params.get("skip_first", False)

        total = len(doc)
        filename = "document"  # No input_path in apply_to_doc context
        today = date.today().strftime("%Y-%m-%d")

        def _resolve(template: str, page_num: int) -> str:
            return (
                template
                .replace("{page}", str(page_num))
                .replace("{total}", str(total))
                .replace("{filename}", filename)
                .replace("{date}", today)
            )

        for i in range(total):
            if skip_first and i == 0:
                continue

            page = doc[i]
            w = page.rect.width
            h = page.rect.height
            n = i + 1
            fs = font_size

            def _insert(text: str, x: float, y: float, align_right: bool = False) -> None:
                if not text:
                    return
                t = _resolve(text, n)
                tw = fitz.get_text_length(t, fontsize=fs)
                px = (x - tw) if align_right else x
                page.insert_text(fitz.Point(px, y), t, fontsize=fs, color=color)

            header_y = _MARGIN
            footer_y = h - _MARGIN + fs

            _insert(header_left, _MARGIN, header_y)
            _insert(header_center, w / 2 - fitz.get_text_length(_resolve(header_center, n), fontsize=fs) / 2, header_y)
            _insert(header_right, w - _MARGIN, header_y, align_right=True)

            _insert(footer_left, _MARGIN, footer_y)
            _insert(footer_center, w / 2 - fitz.get_text_length(_resolve(footer_center, n), fontsize=fs) / 2, footer_y)
            _insert(footer_right, w - _MARGIN, footer_y, align_right=True)

        return doc
