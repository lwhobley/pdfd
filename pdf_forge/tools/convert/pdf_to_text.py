"""PDF → Text extraction tool."""
from __future__ import annotations
import os
from typing import Any

import fitz

from pdf_forge.tools.base import BaseTool, ToolMeta
from pdf_forge.workers.job_model import Job, JobResult


class PDFToTextJob(Job):
    """Extract text layer from a PDF.

    mode: "plain" — raw text per page
          "blocks" — text blocks with bounding boxes (JSON)
          "words"  — word-level extraction (JSON)
    """

    def __init__(
        self,
        input_path: str,
        output_path: str,
        mode: str = "plain",
        page_separator: str = "\n\n--- Page {page} ---\n\n",
    ) -> None:
        super().__init__("pdf_to_text", [input_path])
        self.output_path = output_path
        self.mode = mode
        self.page_separator = page_separator

    def execute(self) -> JobResult:
        self.log(f"Extracting text [{self.mode}]")
        doc = fitz.open(self.input_paths[0])

        if self.mode == "plain":
            parts = []
            for i, page in enumerate(doc):
                if self.cancel_flag:
                    doc.close()
                    raise Exception("Cancelled")
                text = page.get_text("text")
                sep = self.page_separator.replace("{page}", str(i + 1))
                parts.append(sep + text)
                self.report_progress(int((i + 1) / doc.page_count * 90))
            doc.close()
            content = "".join(parts)
            with open(self.output_path, "w", encoding="utf-8") as f:
                f.write(content)

        else:  # blocks or words
            import json
            result = []
            key = "blocks" if self.mode == "blocks" else "words"
            for i, page in enumerate(doc):
                if self.cancel_flag:
                    doc.close()
                    raise Exception("Cancelled")
                data = page.get_text(key)
                result.append({"page": i + 1, key: data})
                self.report_progress(int((i + 1) / doc.page_count * 90))
            doc.close()
            with open(self.output_path, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)

        self.report_progress(100)
        return JobResult(output_paths=[self.output_path])


class PDFToTextTool(BaseTool):
    meta = ToolMeta(
        tool_id="pdf_to_text",
        name="PDF → Text",
        description="Extract the text layer from a PDF to a .txt or .json file.",
        category="convert",
        icon="pdf_to_text",
    )

    def create_job(self, params: dict[str, Any]) -> PDFToTextJob:
        return PDFToTextJob(
            input_path=params["input_path"],
            output_path=params["output_path"],
            mode=params.get("mode", "plain"),
            page_separator=params.get("page_separator", "\n\n--- Page {page} ---\n\n"),
        )
