"""Thin adapter around PyMuPDF (fitz) for rendering and extraction."""
from __future__ import annotations
import logging
from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtCore import QByteArray

log = logging.getLogger(__name__)


class PyMuPDFAdapter:
    """Wraps fitz.Document with convenience methods used by the viewer and tools."""

    def __init__(self, path: str) -> None:
        self._path = path
        self._doc: fitz.Document = fitz.open(path)

    @property
    def page_count(self) -> int:
        return self._doc.page_count

    @property
    def path(self) -> str:
        return self._path

    def render_page(self, page_num: int, zoom: float = 1.0) -> QPixmap:
        """Render a page to a QPixmap at the given zoom level."""
        page = self._doc[page_num]
        mat = fitz.Matrix(zoom, zoom)
        clip = page.rect
        pix = page.get_pixmap(matrix=mat, clip=clip, alpha=False)

        img = QImage(
            pix.samples,
            pix.width,
            pix.height,
            pix.stride,
            QImage.Format.Format_RGB888,
        )
        return QPixmap.fromImage(img)

    def render_thumbnail(self, page_num: int, width: int = 140) -> QPixmap:
        page = self._doc[page_num]
        scale = width / page.rect.width
        return self.render_page(page_num, zoom=scale)

    def get_page_rect(self, page_num: int) -> fitz.Rect:
        return self._doc[page_num].rect

    def extract_text(self, page_num: int) -> str:
        return self._doc[page_num].get_text()

    def get_metadata(self) -> dict:
        return self._doc.metadata

    def get_toc(self) -> list:
        return self._doc.get_toc()

    def close(self) -> None:
        if not self._doc.is_closed:
            self._doc.close()

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass
