"""Repair/recover a corrupt or non-conformant PDF via pikepdf + fitz fallback."""
from __future__ import annotations
from typing import Any

import pikepdf
import fitz

from pdf_forge.tools.base import BaseTool, ToolMeta
from pdf_forge.workers.job_model import Job, JobResult


class RepairJob(Job):
    def __init__(self, input_path: str, output_path: str) -> None:
        super().__init__("repair_pdf", [input_path])
        self.output_path = output_path

    def execute(self) -> JobResult:
        self.log("Attempting PDF repair")
        # Strategy 1: pikepdf with suppress_warnings
        try:
            with pikepdf.open(
                self.input_paths[0],
                suppress_warnings=True,
                attempt_recovery=True,
            ) as pdf:
                pdf.save(self.output_path, compress_streams=True, garbage=3)
            self.log("Repaired via pikepdf")
            self.report_progress(100)
            return JobResult(output_paths=[self.output_path])
        except Exception as e1:
            self.log(f"pikepdf repair failed ({e1}), trying fitz…")

        # Strategy 2: fitz page-by-page reconstruction
        try:
            src = fitz.open(self.input_paths[0])
            dst = fitz.open()
            for i, page in enumerate(src):
                dst.insert_pdf(src, from_page=i, to_page=i)
                self.report_progress(int((i + 1) / src.page_count * 90))
            dst.save(self.output_path, deflate=True, garbage=4, clean=True)
            dst.close()
            src.close()
            self.log("Repaired via fitz reconstruction")
            self.report_progress(100)
            return JobResult(output_paths=[self.output_path])
        except Exception as e2:
            raise Exception(f"Could not repair PDF: {e1}; {e2}") from e2


class RepairTool(BaseTool):
    meta = ToolMeta(
        tool_id="repair_pdf",
        name="Repair PDF",
        description="Attempt to recover and repair a corrupt or malformed PDF.",
        category="secure",
        icon="repair",
    )

    def create_job(self, params: dict[str, Any]) -> RepairJob:
        return RepairJob(
            input_path=params["input_path"],
            output_path=params["output_path"],
        )

    def apply_to_doc(self, doc: fitz.Document, params: dict[str, Any]) -> fitz.Document:
        """Repair via fitz page-by-page reconstruction in-place."""
        # Create a new clean doc by copying pages from the original
        dst = fitz.open()
        for i in range(len(doc)):
            dst.insert_pdf(doc, from_page=i, to_page=i)
        # Close original and return the reconstructed doc
        doc.close()
        return dst
