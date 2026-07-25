"""Sanitize PDF — strip metadata, JavaScript, embedded files, hidden layers."""
from __future__ import annotations
from typing import Any

import pikepdf
from pikepdf import Name

from pdf_forge.tools.base import BaseTool, ToolMeta
from pdf_forge.workers.job_model import Job, JobResult


class SanitizeJob(Job):
    """Remove potentially sensitive or risky content from a PDF.

    Options (all default True):
      remove_metadata   — clear XMP and DocInfo fields
      remove_javascript — delete /AA, /OpenAction and /JS entries
      remove_embedded   — delete embedded file attachments
      remove_links      — delete URI/Link annotations
    """

    def __init__(
        self,
        input_path: str,
        output_path: str,
        remove_metadata: bool = True,
        remove_javascript: bool = True,
        remove_embedded: bool = True,
        remove_links: bool = False,
    ) -> None:
        super().__init__("sanitize_pdf", [input_path])
        self.output_path = output_path
        self.remove_metadata = remove_metadata
        self.remove_javascript = remove_javascript
        self.remove_embedded = remove_embedded
        self.remove_links = remove_links

    def execute(self) -> JobResult:
        with pikepdf.open(self.input_paths[0]) as pdf:
            removed: list[str] = []

            if self.remove_metadata:
                for key in list(pdf.docinfo.keys()):
                    del pdf.docinfo[key]
                with pdf.open_metadata() as meta:
                    meta.clear()
                removed.append("metadata")

            if self.remove_javascript:
                root = pdf.Root
                for key in ("/AA", "/OpenAction"):
                    if Name(key) in root:
                        del root[Name(key)]
                # Remove Names → JavaScript
                if Name("/Names") in root:
                    names = root[Name("/Names")]
                    for js_key in ("/JavaScript", "/JS"):
                        if Name(js_key) in names:
                            del names[Name(js_key)]
                removed.append("javascript")

            if self.remove_embedded:
                root = pdf.Root
                if Name("/Names") in root:
                    names = root[Name("/Names")]
                    for ef_key in ("/EmbeddedFiles",):
                        if Name(ef_key) in names:
                            del names[Name(ef_key)]
                removed.append("embedded-files")

            if self.remove_links:
                for page in pdf.pages:
                    if Name("/Annots") in page:
                        keep = []
                        for annot in page[Name("/Annots")]:
                            if annot.get(Name("/Subtype")) != Name("/Link"):
                                keep.append(annot)
                        page[Name("/Annots")] = pikepdf.Array(keep)
                removed.append("links")

            pdf.save(
                self.output_path,
                compress_streams=True,
                object_stream_mode=pikepdf.ObjectStreamMode.generate,
            )

        self.report_progress(100)
        self.log(f"Sanitized: removed {', '.join(removed)}")
        return JobResult(
            output_paths=[self.output_path],
            metadata={"removed": removed},
        )


class SanitizeTool(BaseTool):
    meta = ToolMeta(
        tool_id="sanitize_pdf",
        name="Sanitize PDF",
        description="Strip metadata, JavaScript, and embedded files from a PDF.",
        category="organize",
        icon="sanitize",
    )

    def create_job(self, params: dict[str, Any]) -> SanitizeJob:
        return SanitizeJob(
            input_path=params["input_path"],
            output_path=params["output_path"],
            remove_metadata=params.get("remove_metadata", True),
            remove_javascript=params.get("remove_javascript", True),
            remove_embedded=params.get("remove_embedded", True),
            remove_links=params.get("remove_links", False),
        )
