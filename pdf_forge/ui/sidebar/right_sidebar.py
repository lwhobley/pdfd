"""Right sidebar — document properties, page info, metadata."""
from __future__ import annotations
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QFormLayout, QFrame,
    QScrollArea, QGroupBox,
)
from PySide6.QtCore import Qt


class RightSidebar(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumWidth(180)
        self.setMaximumWidth(260)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        inner = QVBoxLayout(container)
        inner.setContentsMargins(0, 0, 0, 0)
        inner.setSpacing(8)

        # Page info group
        page_group = QGroupBox("Page Info")
        page_form = QFormLayout(page_group)
        self._lbl_page = QLabel("—")
        self._lbl_size = QLabel("—")
        self._lbl_zoom = QLabel("—")
        page_form.addRow("Page:", self._lbl_page)
        page_form.addRow("Size:", self._lbl_size)
        page_form.addRow("Zoom:", self._lbl_zoom)
        inner.addWidget(page_group)

        # Document metadata group
        meta_group = QGroupBox("Document")
        meta_form = QFormLayout(meta_group)
        self._lbl_title = QLabel("—")
        self._lbl_author = QLabel("—")
        self._lbl_pages = QLabel("—")
        self._lbl_file = QLabel("—")
        self._lbl_size_file = QLabel("—")
        self._lbl_title.setWordWrap(True)
        self._lbl_author.setWordWrap(True)
        meta_form.addRow("Title:", self._lbl_title)
        meta_form.addRow("Author:", self._lbl_author)
        meta_form.addRow("Pages:", self._lbl_pages)
        meta_form.addRow("File:", self._lbl_file)
        meta_form.addRow("Size:", self._lbl_size_file)
        inner.addWidget(meta_group)

        inner.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll)

    def update_page_info(
        self, page_num: int, total: int, width_pt: float, height_pt: float, zoom: float
    ) -> None:
        self._lbl_page.setText(f"{page_num + 1} / {total}")
        self._lbl_size.setText(f"{width_pt:.0f} × {height_pt:.0f} pt")
        self._lbl_zoom.setText(f"{zoom * 100:.0f}%")

    def update_document_info(
        self,
        path: str,
        page_count: int,
        metadata: dict,
    ) -> None:
        import os
        self._lbl_title.setText(metadata.get("Title", "—") or "—")
        self._lbl_author.setText(metadata.get("Author", "—") or "—")
        self._lbl_pages.setText(str(page_count))
        self._lbl_file.setText(os.path.basename(path))
        try:
            size_mb = os.path.getsize(path) / 1024 / 1024
            self._lbl_size_file.setText(f"{size_mb:.2f} MB")
        except OSError:
            self._lbl_size_file.setText("—")

    def clear(self) -> None:
        for lbl in [
            self._lbl_page, self._lbl_size, self._lbl_zoom,
            self._lbl_title, self._lbl_author, self._lbl_pages,
            self._lbl_file, self._lbl_size_file,
        ]:
            lbl.setText("—")
