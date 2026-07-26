"""Permanent redaction tool.

Strategy: search for text strings, add redaction annotations, then apply.
Applying redaction in fitz removes the underlying content permanently and
paints a black (or custom-colored) rectangle over the area.
"""
from __future__ import annotations
from typing import Any

import fitz

from pdf_forge.tools.base import BaseTool, ToolMeta
from pdf_forge.tools.edit.text_search import find_text_rects
from pdf_forge.workers.job_model import Job, JobResult


class RedactJob(Job):
    """Search for terms and permanently redact them.

    search_terms: list of strings to find and redact
    fill_color: RGB tuple for the redaction rectangle (default black)
    """

    def __init__(
        self,
        input_path: str,
        output_path: str,
        search_terms: list[str],
        fill_color: tuple[float, float, float] = (0.0, 0.0, 0.0),
        whole_word: bool = False,
        case_sensitive: bool = False,
    ) -> None:
        super().__init__("redact", [input_path])
        self.output_path = output_path
        self.search_terms = search_terms
        self.fill_color = fill_color
        self.whole_word = whole_word
        self.case_sensitive = case_sensitive

    def execute(self) -> JobResult:
        self.log(f"Redacting {len(self.search_terms)} term(s)")
        doc = fitz.open(self.input_paths[0])
        total_redactions = 0

        for i, page in enumerate(doc):
            if self.cancel_flag:
                doc.close()
                raise Exception("Cancelled")

            for term in self.search_terms:
                hits = find_text_rects(
                    page, term,
                    case_sensitive=self.case_sensitive,
                    whole_word=self.whole_word,
                )
                for rect in hits:
                    page.add_redact_annot(rect, fill=self.fill_color)
                    total_redactions += 1

            # Apply all redactions on this page — this removes underlying content
            page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)
            self.report_progress(int((i + 1) / doc.page_count * 95))

        doc.save(self.output_path, deflate=True, garbage=4, clean=True)
        doc.close()
        self.report_progress(100)
        self.log(f"Applied {total_redactions} redaction(s)")
        return JobResult(
            output_paths=[self.output_path],
            metadata={"redaction_count": total_redactions},
        )


class RedactTool(BaseTool):
    meta = ToolMeta(
        tool_id="redact",
        name="Redact Content",
        description="Search for text and permanently remove it with black rectangles.",
        category="edit",
        icon="redact",
    )

    def create_job(self, params: dict[str, Any]) -> RedactJob:
        return RedactJob(
            input_path=params["input_path"],
            output_path=params["output_path"],
            search_terms=params.get("search_terms", []),
            fill_color=tuple(params.get("fill_color", (0.0, 0.0, 0.0))),
            whole_word=params.get("whole_word", False),
            case_sensitive=params.get("case_sensitive", False),
        )

    def apply_to_doc(self, doc: fitz.Document, params: dict[str, Any]) -> fitz.Document:
        """Search and redact terms in-place."""
        search_terms = params.get("search_terms", [])
        fill_color = tuple(params.get("fill_color", (0.0, 0.0, 0.0)))
        whole_word = params.get("whole_word", False)
        case_sensitive = params.get("case_sensitive", False)

        for page in doc:
            for term in search_terms:
                hits = find_text_rects(
                    page, term,
                    case_sensitive=case_sensitive,
                    whole_word=whole_word,
                )
                for rect in hits:
                    page.add_redact_annot(rect, fill=fill_color)

            page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)

        return doc
