"""Node palette — sidebar listing all available node types."""
from __future__ import annotations
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QListWidget, QListWidgetItem, QFrame,
)
from PySide6.QtCore import Qt, QMimeData
from PySide6.QtGui import QDrag, QFont

from pdf_forge.workflow.node_registry import specs_by_category


class PaletteItem(QListWidgetItem):
    def __init__(self, node_type: str, title: str) -> None:
        super().__init__(title)
        self.node_type = node_type
        self.setToolTip(f"Drag onto canvas to add a '{title}' node")


class NodePalette(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumWidth(170)
        self.setMaximumWidth(220)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 8, 4, 4)
        layout.setSpacing(2)

        label = QLabel("  NODES")
        label.setStyleSheet(
            "color: #6c6f85; font-size: 10px; font-weight: bold;"
            "padding-bottom: 4px;"
        )
        layout.addWidget(label)

        by_cat = specs_by_category()
        for cat, specs in by_cat.items():
            # Category header
            header = QLabel(f"  {cat.upper()}")
            f = QFont()
            f.setPointSize(8)
            f.setBold(True)
            header.setFont(f)
            header.setStyleSheet("color: #7f849c; padding: 6px 0 2px 0;")
            layout.addWidget(header)

            lst = _DraggableList()
            for spec in specs:
                lst.addItem(PaletteItem(spec.node_type, spec.title))
            layout.addWidget(lst)

        layout.addStretch()


class _DraggableList(QListWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setStyleSheet(
            "QListWidget { border: none; background: transparent; }"
            "QListWidget::item { padding: 5px 10px; border-radius: 3px; }"
            "QListWidget::item:hover { background: #313244; }"
        )
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setDragEnabled(True)

    def startDrag(self, actions) -> None:
        item = self.currentItem()
        if not isinstance(item, PaletteItem):
            return
        mime = QMimeData()
        mime.setText(item.node_type)
        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.exec(Qt.CopyAction)
