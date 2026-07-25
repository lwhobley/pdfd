"""Office → PDF conversion tool (LibreOffice bridge).

Supported input formats:
  .docx .doc .odt .rtf  — Word-compatible
  .xlsx .xls .ods .csv  — Spreadsheet
  .pptx .ppt .odp       — Presentation
"""
from __future__ import annotations
import os
import shutil
import tempfile
from typing import Any

from pdf_forge.tools.base import BaseTool, ToolMeta
from pdf_forge.workers.job_model import Job, JobResult
from pdf_forge.adapters.libreoffice_adapter import find_soffice, convert_to_pdf

_SUPPORTED = {
    ".docx", ".doc", ".odt", ".rtf",
    ".xlsx", ".xls", ".ods", ".csv",
    ".pptx", ".ppt", ".odp",
    ".html", ".htm", ".txt",
}


class OfficeToPDFJob(Job):
    def __init__(
        self,
        input_paths: list[str],
        output_dir: str,
        libreoffice_path: str = "",
        merge_output: bool = False,
        merged_output_path: str = "",
    ) -> None:
        super().__init__("office_to_pdf", input_paths)
        self.output_dir = output_dir
        self.libreoffice_path = libreoffice_path
        self.merge_output = merge_output
        self.merged_output_path = merged_output_path

    def execute(self) -> JobResult:
        soffice = find_soffice(self.libreoffice_path)
        if not soffice:
            raise RuntimeError(
                "LibreOffice not found. Install it and set the path in Settings."
            )
        self.log(f"Using LibreOffice: {soffice}")

        os.makedirs(self.output_dir, exist_ok=True)
        output_paths: list[str] = []

        with tempfile.TemporaryDirectory() as tmp:
            for i, src in enumerate(self.input_paths):
                if self.cancel_flag:
                    raise Exception("Cancelled")
                ext = os.path.splitext(src)[1].lower()
                if ext not in _SUPPORTED:
                    self.log(f"Skipping unsupported: {src}")
                    continue
                self.log(f"Converting: {os.path.basename(src)}")
                pdf_path = convert_to_pdf(src, tmp, soffice)

                # Move to output_dir with original stem
                stem = os.path.splitext(os.path.basename(src))[0]
                dest = os.path.join(self.output_dir, stem + ".pdf")
                # Avoid overwrite collisions
                if os.path.exists(dest):
                    base, _ = os.path.splitext(dest)
                    dest = f"{base}_{i}.pdf"
                shutil.move(pdf_path, dest)
                output_paths.append(dest)
                self.report_progress(int((i + 1) / len(self.input_paths) * 90))

        if self.merge_output and output_paths and self.merged_output_path:
            import fitz
            dst = fitz.open()
            for p in output_paths:
                src_doc = fitz.open(p)
                dst.insert_pdf(src_doc)
                src_doc.close()
            dst.save(self.merged_output_path, deflate=True)
            dst.close()
            output_paths = [self.merged_output_path]
            self.log(f"Merged into: {self.merged_output_path}")

        self.report_progress(100)
        self.log(f"Converted {len(output_paths)} file(s)")
        return JobResult(output_paths=output_paths)


class OfficeToPDFTool(BaseTool):
    meta = ToolMeta(
        tool_id="office_to_pdf",
        name="Office → PDF",
        description="Convert Word, Excel, PowerPoint, ODT files to PDF via LibreOffice.",
        category="convert",
        icon="office_to_pdf",
        requires=["libreoffice"],
    )

    def create_job(self, params: dict[str, Any]) -> OfficeToPDFJob:
        return OfficeToPDFJob(
            input_paths=params["input_paths"],
            output_dir=params["output_dir"],
            libreoffice_path=params.get("libreoffice_path", ""),
            merge_output=params.get("merge_output", False),
            merged_output_path=params.get("merged_output_path", ""),
        )
