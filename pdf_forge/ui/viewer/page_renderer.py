"""Background page renderer — renders PDF pages off the main thread."""
from __future__ import annotations
import logging
from PySide6.QtCore import QRunnable, QThreadPool, Signal, QObject
from PySide6.QtGui import QPixmap

from pdf_forge.adapters.pymupdf_adapter import PyMuPDFAdapter

log = logging.getLogger(__name__)


class _RenderSignals(QObject):
    ready = Signal(int, float, QPixmap)   # page_num, zoom, pixmap
    error = Signal(int, str)


class PageRenderTask(QRunnable):
    def __init__(
        self, adapter: PyMuPDFAdapter, page_num: int, zoom: float
    ) -> None:
        super().__init__()
        self.setAutoDelete(True)
        self._adapter = adapter
        self._page_num = page_num
        self._zoom = zoom
        self.signals = _RenderSignals()

    def run(self) -> None:
        try:
            pixmap = self._adapter.render_page(self._page_num, self._zoom)
            self.signals.ready.emit(self._page_num, self._zoom, pixmap)
        except Exception as e:
            log.warning("Render failed page %d: %s", self._page_num, e)
            self.signals.error.emit(self._page_num, str(e))


class ThumbnailRenderTask(QRunnable):
    def __init__(
        self, adapter: PyMuPDFAdapter, page_num: int, width: int
    ) -> None:
        super().__init__()
        self.setAutoDelete(True)
        self._adapter = adapter
        self._page_num = page_num
        self._width = width
        self.signals = _RenderSignals()

    def run(self) -> None:
        try:
            pixmap = self._adapter.render_thumbnail(self._page_num, self._width)
            self.signals.ready.emit(self._page_num, 0.0, pixmap)
        except Exception as e:
            log.warning("Thumbnail failed page %d: %s", self._page_num, e)
            self.signals.error.emit(self._page_num, str(e))
