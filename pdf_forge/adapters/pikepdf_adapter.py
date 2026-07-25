"""Thin adapter around pikepdf for structural PDF operations."""
from __future__ import annotations
import logging
from typing import Optional

import pikepdf

log = logging.getLogger(__name__)

_META_FIELDS = ["/Title", "/Author", "/Subject", "/Keywords", "/Creator", "/Producer"]


class PikePDFAdapter:
    """Wraps pikepdf for structural operations: merge, split, encrypt, etc."""

    @staticmethod
    def merge(
        input_paths: list[str],
        output_path: str,
        preserve_bookmarks: bool = True,
        cancel_flag_fn=None,
    ) -> None:
        with pikepdf.Pdf.new() as output:
            for i, path in enumerate(input_paths):
                if cancel_flag_fn and cancel_flag_fn():
                    raise Exception("Cancelled")
                with pikepdf.open(path) as src:
                    output.pages.extend(src.pages)
                log.debug("Merged %s", path)
            output.save(output_path)
        log.info("Merge complete → %s", output_path)

    @staticmethod
    def split_by_range(
        input_path: str,
        ranges: list[tuple[int, int]],
        output_paths: list[str],
        cancel_flag_fn=None,
    ) -> None:
        """Split input PDF into multiple outputs, one per (start, end) page range.

        Ranges are 0-indexed, end is exclusive.
        """
        with pikepdf.open(input_path) as src:
            for (start, end), out_path in zip(ranges, output_paths):
                if cancel_flag_fn and cancel_flag_fn():
                    raise Exception("Cancelled")
                with pikepdf.Pdf.new() as dst:
                    dst.pages.extend(src.pages[start:end])
                    dst.save(out_path)
                log.debug("Split pages %d-%d → %s", start, end - 1, out_path)

    @staticmethod
    def split_every_n(
        input_path: str,
        n: int,
        output_dir: str,
        base_name: str,
        cancel_flag_fn=None,
    ) -> list[str]:
        """Split into chunks of n pages. Returns list of created paths."""
        import os
        output_paths = []
        with pikepdf.open(input_path) as src:
            total = len(src.pages)
            chunk = 0
            for start in range(0, total, n):
                if cancel_flag_fn and cancel_flag_fn():
                    raise Exception("Cancelled")
                end = min(start + n, total)
                out_path = os.path.join(
                    output_dir, f"{base_name}_part{chunk + 1:03d}.pdf"
                )
                with pikepdf.Pdf.new() as dst:
                    dst.pages.extend(src.pages[start:end])
                    dst.save(out_path)
                output_paths.append(out_path)
                chunk += 1
        return output_paths

    @staticmethod
    def rotate_pages(
        input_path: str,
        output_path: str,
        page_indices: list[int],
        degrees: int,
        cancel_flag_fn=None,
    ) -> None:
        with pikepdf.open(input_path) as pdf:
            for idx in page_indices:
                if cancel_flag_fn and cancel_flag_fn():
                    raise Exception("Cancelled")
                page = pdf.pages[idx]
                current = int(page.get("/Rotate", 0))
                page["/Rotate"] = (current + degrees) % 360
            pdf.save(output_path)

    @staticmethod
    def delete_pages(
        input_path: str,
        output_path: str,
        page_indices: list[int],
        cancel_flag_fn=None,
    ) -> None:
        indices_set = set(page_indices)
        with pikepdf.open(input_path) as pdf:
            with pikepdf.Pdf.new() as dst:
                for i in range(len(pdf.pages)):
                    if cancel_flag_fn and cancel_flag_fn():
                        raise Exception("Cancelled")
                    if i not in indices_set:
                        dst.pages.append(pdf.pages[i])
                dst.save(output_path)

    @staticmethod
    def extract_pages(
        input_path: str,
        output_path: str,
        page_indices: list[int],
        cancel_flag_fn=None,
    ) -> None:
        with pikepdf.open(input_path) as pdf:
            with pikepdf.Pdf.new() as dst:
                for idx in page_indices:
                    if cancel_flag_fn and cancel_flag_fn():
                        raise Exception("Cancelled")
                    dst.pages.append(pdf.pages[idx])
                dst.save(output_path)

    @staticmethod
    def get_page_count(path: str) -> int:
        with pikepdf.open(path) as pdf:
            return len(pdf.pages)

    @staticmethod
    def get_metadata(path: str) -> dict:
        with pikepdf.open(path) as pdf:
            meta = {}
            info = pdf.docinfo
            for key in _META_FIELDS:
                val = info.get(key, "")
                if val:
                    meta[key.lstrip("/")] = str(val)
            return meta

    @staticmethod
    def set_metadata(input_path: str, output_path: str, metadata: dict) -> None:
        """Write metadata dict to PDF. Keys are plain strings (no leading slash)."""
        with pikepdf.open(input_path) as pdf:
            with pdf.open_metadata() as xmp:
                # Update XMP where possible
                if "Title" in metadata:
                    xmp["dc:title"] = metadata["Title"]
                if "Author" in metadata:
                    xmp["dc:creator"] = [metadata["Author"]]
                if "Subject" in metadata:
                    xmp["dc:description"] = metadata["Subject"]
                if "Keywords" in metadata:
                    xmp["pdf:Keywords"] = metadata["Keywords"]

            # Also write legacy docinfo
            info = pdf.docinfo
            for key, val in metadata.items():
                info[f"/{key}"] = val

            pdf.save(output_path)

    @staticmethod
    def get_toc(path: str) -> list[tuple[int, str, int]]:
        """Returns list of (level, title, page_num_1indexed) tuples."""
        import fitz
        doc = fitz.open(path)
        toc = doc.get_toc()
        doc.close()
        return toc  # already [(level, title, page), ...]

    @staticmethod
    def set_toc(
        input_path: str,
        output_path: str,
        toc: list[tuple[int, str, int]],
    ) -> None:
        import fitz
        doc = fitz.open(input_path)
        doc.set_toc(toc)
        doc.save(output_path)
        doc.close()

    @staticmethod
    def remove_blank_pages(
        input_path: str,
        output_path: str,
        threshold: float = 0.001,
        cancel_flag_fn=None,
    ) -> int:
        """Remove pages whose content stream is nearly empty.

        Returns the number of pages removed.
        """
        import fitz
        src = fitz.open(input_path)
        keep_indices = []
        for i, page in enumerate(src):
            if cancel_flag_fn and cancel_flag_fn():
                src.close()
                raise Exception("Cancelled")
            text = page.get_text().strip()
            images = page.get_images()
            if text or images:
                keep_indices.append(i)
        src.close()

        removed = src.page_count - len(keep_indices) if hasattr(src, 'page_count') else 0

        with pikepdf.open(input_path) as pdf:
            total = len(pdf.pages)
            removed = total - len(keep_indices)
            with pikepdf.Pdf.new() as dst:
                for i in keep_indices:
                    dst.pages.append(pdf.pages[i])
                dst.save(output_path)

        return removed
