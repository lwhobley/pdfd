"""Remove all annotations from a PDF."""
from __future__ import annotations
from typing import Any

import fitz

from pdf_forge.tools.base import BaseTool, ToolMeta
from pdf_forge.workers.job_model import Job, JobResult


class RemoveAnnotationsJob(Job):
    """Delete every annotation from every page (or specified pages).

    annotation_types: if None, remove all types.
    Valid fitz type names: Text, FreeText, Line, Square, Circle, Polygon,
    PolyLine, Highlight, Underline, Squiggly, StrikeOut, Stamp, Caret,
    Ink, Popup, FileAttachment, Sound, Movie, Widget, Link, PrinterMark,
    TrapNet, Watermark, 3D, Redact
    """

    def __init__(
        self,
        input_path: str,
        output_path: str,
        annotation_types: list[str] | None = None,
        pages: list[int] | None = None,
    ) -> None:
        super().__init__("remove_annotations", [input_path])
        self.output_path = output_path
        self.annotation_types = annotation_types
        self.pages = pages

    def execute(self) -> JobResult:
        self.log("Removing annotations")
        doc = fitz.open(self.input_paths[0])
        target = self.pages if self.pages is not None else list(range(doc.page_count))
        removed = 0

        for pn in target:
            if self.cancel_flag:
                doc.close()
                raise Exception("Cancelled")
            page = doc[pn]
            annots_to_delete = []
            for annot in page.annots():
                if self.annotation_types is None:
                    annots_to_delete.append(annot)
                elif annot.type[1] in self.annotation_types:
                    annots_to_delete.append(annot)
            for annot in annots_to_delete:
                page.delete_annot(annot)
                removed += 1

        doc.save(self.output_path, deflate=True)
        doc.close()
        self.report_progress(100)
        self.log(f"Removed {removed} annotation(s)")
        return JobResult(
            output_paths=[self.output_path],
            metadata={"removed": removed},
        )


class RemoveAnnotationsTool(BaseTool):
    meta = ToolMeta(
        tool_id="remove_annotations",
        name="Remove Annotations",
        description="Strip all or selected annotation types from a PDF.",
        category="edit",
        icon="remove_annots",
    )

    def create_job(self, params: dict[str, Any]) -> RemoveAnnotationsJob:
        return RemoveAnnotationsJob(
            input_path=params["input_path"],
            output_path=params["output_path"],
            annotation_types=params.get("annotation_types"),
            pages=params.get("pages"),
        )
