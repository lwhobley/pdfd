"""Left thumbnail strip — scrollable list of page thumbnails."""
from __future__ import annotations
import logging
from PySide6.QtWidgets import (
    QWidget, QListWidget, QListWidgetItem, QVBoxLayout, QLabel,
    QSizePolicy,
)
from PySide6.QtCore import Qt, QThreadPool, Signal, QSize
from PySide6.QtGui import QPixmap, QIcon

from pdf_forge.adapters.pymupdf_adapter import PyMuPDFAdapter
from pdf_forge.ui.viewer.page_renderer import ThumbnailRenderTask

log = logging.getLogger(__name__)

THUMB_W = 140


class ThumbnailPanel(QWidget):
    page_clicked = Signal(int)    # 0-indexed page number

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._adapter: PyMuPDFAdapter | None = None
        self._pool = QThreadPool.globalInstance()
        self._pixmaps: dict[int, QPixmap] = {}
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._list = QListWidget()
        self._list.setViewMode(QListWidget.ViewMode.IconMode)
        self._list.setIconSize(QSize(THUMB_W, int(THUMB_W * 1.414)))
        self._list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self._list.setSpacing(6)
        self._list.setMovement(QListWidget.Movement.Static)
        self._list.setUniformItemSizes(False)
        self._list.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self._list.currentRowChanged.connect(self._on_row_changed)
        layout.addWidget(self._list)

    def load(self, adapter: PyMuPDFAdapter) -> None:
        self._adapter = adapter
        self._pixmaps.clear()
        self._list.clear()

        for i in range(adapter.page_count):
            item = QListWidgetItem(f"Page {i + 1}")
            item.setData(Qt.ItemDataRole.UserRole, i)
            item.setSizeHint(QSize(THUMB_W + 10, int(THUMB_W * 1.414) + 24))
            self._list.addItem(item)

        # Render thumbnails in background
        for i in range(adapter.page_count):
            task = ThumbnailRenderTask(adapter, i, THUMB_W)
            task.signals.ready.connect(self._on_thumb_ready)
            self._pool.start(task)

    def clear(self) -> None:
        self._list.clear()
        self._pixmaps.clear()
        self._adapter = None

    def set_current_page(self, page_num: int) -> None:
        self._list.blockSignals(True)
        self._list.setCurrentRow(page_num)
        self._list.blockSignals(False)

    def _on_thumb_ready(self, page_num: int, _zoom: float, pixmap: QPixmap) -> None:
        self._pixmaps[page_num] = pixmap
        item = self._list.item(page_num)
        if item:
            item.setIcon(QIcon(pixmap))

    def _on_row_changed(self, row: int) -> None:
        if row >= 0:
            self.page_clicked.emit(row)
