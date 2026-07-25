"""Drag-and-drop zone widget for opening PDFs."""
from __future__ import annotations
from PySide6.QtWidgets import QLabel
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent


class DropZone(QLabel):
    files_dropped = Signal(list)   # list[str]

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setText("Drop PDF files here\nor use File → Open")
        self.setStyleSheet(
            "border: 2px dashed #45475a; border-radius: 8px;"
            "color: #585b70; font-size: 16px; padding: 40px;"
        )

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            pdfs = [
                u.toLocalFile()
                for u in event.mimeData().urls()
                if u.toLocalFile().lower().endswith(".pdf")
            ]
            if pdfs:
                event.acceptProposedAction()
                self.setStyleSheet(
                    "border: 2px dashed #89b4fa; border-radius: 8px;"
                    "color: #89b4fa; font-size: 16px; padding: 40px;"
                )
                return
        event.ignore()

    def dragLeaveEvent(self, event) -> None:
        self._reset_style()

    def dropEvent(self, event: QDropEvent) -> None:
        pdfs = [
            u.toLocalFile()
            for u in event.mimeData().urls()
            if u.toLocalFile().lower().endswith(".pdf")
        ]
        self._reset_style()
        if pdfs:
            self.files_dropped.emit(pdfs)

    def _reset_style(self) -> None:
        self.setStyleSheet(
            "border: 2px dashed #45475a; border-radius: 8px;"
            "color: #585b70; font-size: 16px; padding: 40px;"
        )
