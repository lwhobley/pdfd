"""Compress PDF — reduce file size via pikepdf stream compression + image downsampling."""
from __future__ import annotations
import os
from typing import Any

import pikepdf
import fitz

from pdf_forge.tools.base import BaseTool, ToolMeta
from pdf_forge.workers.job_model import Job, JobResult


class CompressJob(Job):
    """Two-level compression strategy:

    level "low"  — pikepdf stream compression only (lossless, fast)
    level "med"  — above + remove duplicate objects + linearize
    level "high" — above + downsample images to target_dpi via fitz
    """

    def __init__(
        self,
        input_path: str,
        output_path: str,
        level: str = "med",
        image_dpi: int = 96,
    ) -> None:
        super().__init__("compress_pdf", [input_path])
        self.output_path = output_path
        self.level = level
        self.image_dpi = image_dpi

    def execute(self) -> JobResult:
        input_size = os.path.getsize(self.input_paths[0])
        self.log(f"Compressing [{self.level}] — input: {input_size / 1024:.0f} KB")

        if self.level == "high":
            self._compress_high()
        else:
            self._compress_pikepdf()

        self.report_progress(100)
        output_size = os.path.getsize(self.output_path)
        ratio = (1 - output_size / input_size) * 100 if input_size else 0
        self.log(f"Output: {output_size / 1024:.0f} KB  (saved {ratio:.1f}%)")
        return JobResult(
            output_paths=[self.output_path],
            metadata={"input_bytes": input_size, "output_bytes": output_size},
        )

    def _compress_pikepdf(self) -> None:
        import pikepdf
        linearize = self.level in ("med", "high")
        with pikepdf.open(self.input_paths[0]) as pdf:
            pdf.save(
                self.output_path,
                compress_streams=True,
                object_stream_mode=pikepdf.ObjectStreamMode.generate,
                recompress_flate=True,
                linearize=linearize,
            )

    def _compress_high(self) -> None:
        """Re-render images at target_dpi to reduce size, then compress streams."""
        import io
        from PIL import Image

        doc = fitz.open(self.input_paths[0])
        target_zoom = self.image_dpi / 72.0

        for i, page in enumerate(doc):
            if self.cancel_flag:
                doc.close()
                raise Exception("Cancelled")
            # Replace all page images with downsampled versions
            for img_info in page.get_images(full=True):
                xref = img_info[0]
                try:
                    base_image = doc.extract_image(xref)
                    img_bytes = base_image["image"]
                    img = Image.open(io.BytesIO(img_bytes))
                    # Only downsample if larger than target
                    if img.width > 800 or img.height > 800:
                        scale = min(self.image_dpi / max(img.width, img.height) * 11.11, 1.0)
                        new_w = max(1, int(img.width * scale))
                        new_h = max(1, int(img.height * scale))
                        img = img.resize((new_w, new_h), Image.LANCZOS)
                    buf = io.BytesIO()
                    fmt = "JPEG" if img.mode == "RGB" else "PNG"
                    img.save(buf, format=fmt, quality=75, optimize=True)
                    doc.update_stream(xref, buf.getvalue())
                except Exception:
                    pass  # skip images we can't process
            self.report_progress(int((i + 1) / doc.page_count * 80))

        tmp_path = self.output_path + ".tmp"
        doc.save(tmp_path, deflate=True, garbage=4, clean=True)
        doc.close()

        # Final pikepdf pass for stream compression
        with pikepdf.open(tmp_path) as pdf:
            pdf.save(
                self.output_path,
                compress_streams=True,
                object_stream_mode=pikepdf.ObjectStreamMode.generate,
                recompress_flate=True,
            )
        os.remove(tmp_path)


class CompressTool(BaseTool):
    meta = ToolMeta(
        tool_id="compress_pdf",
        name="Compress PDF",
        description="Reduce PDF file size with three compression levels.",
        category="secure",
        icon="compress",
    )

    def create_job(self, params: dict[str, Any]) -> CompressJob:
        return CompressJob(
            input_path=params["input_path"],
            output_path=params["output_path"],
            level=params.get("level", "med"),
            image_dpi=params.get("image_dpi", 96),
        )
