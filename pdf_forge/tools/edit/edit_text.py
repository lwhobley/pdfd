"""Find-and-replace text in PDF pages using redaction + reinsertion."""
from __future__ import annotations
from typing import Any

import fitz

from pdf_forge.tools.base import BaseTool, ToolMeta
from pdf_forge.tools.edit.text_search import find_text_rects
from pdf_forge.workers.job_model import Job, JobResult


def _font_size_at(page: fitz.Page, rect: fitz.Rect) -> float:
    """Return the font size of the first text span overlapping rect."""
    try:
        for block in page.get_text("dict", clip=rect)["blocks"]:
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    size = span.get("size")
                    if size:
                        return float(size)
    except Exception:
        pass
    return 11.0


class EditTextJob(Job):
    """Find text and replace it, or delete it if replace_text is empty.

    Strategy: white-fill redaction annotation removes the original content,
    then insert_text writes the replacement at the same baseline position.
    """

    def __init__(
        self,
        input_path: str,
        output_path: str,
        find_text: str,
        replace_text: str = "",
        case_sensitive: bool = True,
    ) -> None:
        super().__init__("edit_text", [input_path])
        self.output_path = output_path
        self.find_text = find_text
        self.replace_text = replace_text
        self.case_sensitive = case_sensitive

    def execute(self) -> JobResult:
        self.log(f"Edit text: find={self.find_text!r} replace={self.replace_text!r}")
        doc = fitz.open(self.input_paths[0])
        total = 0

        for i, page in enumerate(doc):
            if self.cancel_flag:
                doc.close()
                raise Exception("Cancelled")

            rects = self._find_rects(page)
            if not rects:
                self.report_progress(int((i + 1) / doc.page_count * 95))
                continue

            # Collect font sizes before redaction changes the page
            replacements: list[tuple[fitz.Point, float]] = []
            for rect in rects:
                font_size = _font_size_at(page, rect)
                page.add_redact_annot(rect, fill=(1.0, 1.0, 1.0))
                replacements.append((fitz.Point(rect.x0, rect.y1), font_size))

            page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)

            if self.replace_text:
                for pt, fs in replacements:
                    page.insert_text(pt, self.replace_text, fontsize=fs, color=(0.0, 0.0, 0.0))

            total += len(rects)
            self.report_progress(int((i + 1) / doc.page_count * 95))

        doc.save(self.output_path, deflate=True, garbage=4, clean=True)
        doc.close()
        self.report_progress(100)
        self.log(f"Processed {total} occurrence(s)")
        return JobResult(
            output_paths=[self.output_path],
            metadata={"replacements": total},
        )

    def _find_rects(self, page: fitz.Page) -> list[fitz.Rect]:
        return find_text_rects(page, self.find_text, case_sensitive=self.case_sensitive)


class EditTextTool(BaseTool):
    meta = ToolMeta(
        tool_id="edit_text",
        name="Edit Text",
        description="Find text in a PDF and replace or delete it.",
        category="edit",
        icon="edit_text",
    )

    def create_job(self, params: dict[str, Any]) -> EditTextJob:
        return EditTextJob(
            input_path=params["input_path"],
            output_path=params["output_path"],
            find_text=params["find_text"],
            replace_text=params.get("replace_text", ""),
            case_sensitive=params.get("case_sensitive", True),
        )
