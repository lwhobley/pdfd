"""Merge PDFs dialog."""
from __future__ import annotations
import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget,
    QListWidgetItem, QLabel, QFileDialog, QDialogButtonBox,
    QAbstractItemView,
)
from PySide6.QtCore import Qt


class MergeDialog(QDialog):
    def __init__(self, initial_paths: list[str] | None = None, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Merge PDFs")
        self.setMinimumSize(520, 400)
        self._setup_ui()
        for path in (initial_paths or []):
            self._add_file(path)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Add PDFs to merge (drag to reorder):"))

        self._list = QListWidget()
        self._list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self._list.setDefaultDropAction(Qt.DropAction.MoveAction)
        self._list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        layout.addWidget(self._list)

        btn_row = QHBoxLayout()
        self._btn_add = QPushButton("Add Files…")
        self._btn_add.clicked.connect(self._browse_add)
        self._btn_remove = QPushButton("Remove")
        self._btn_remove.clicked.connect(self._remove_selected)
        self._btn_up = QPushButton("▲")
        self._btn_up.setFixedWidth(32)
        self._btn_up.clicked.connect(self._move_up)
        self._btn_down = QPushButton("▼")
        self._btn_down.setFixedWidth(32)
        self._btn_down.clicked.connect(self._move_down)
        btn_row.addWidget(self._btn_add)
        btn_row.addWidget(self._btn_remove)
        btn_row.addStretch()
        btn_row.addWidget(self._btn_up)
        btn_row.addWidget(self._btn_down)
        layout.addLayout(btn_row)

        self._buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self._buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Merge…")
        self._buttons.accepted.connect(self._on_accept)
        self._buttons.rejected.connect(self.reject)
        layout.addWidget(self._buttons)

        self.result_params: dict | None = None

    def _add_file(self, path: str) -> None:
        item = QListWidgetItem(os.path.basename(path))
        item.setData(Qt.ItemDataRole.UserRole, path)
        item.setToolTip(path)
        self._list.addItem(item)

    def _browse_add(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Select PDFs", "", "PDF Files (*.pdf)"
        )
        for p in paths:
            self._add_file(p)

    def _remove_selected(self) -> None:
        for item in self._list.selectedItems():
            self._list.takeItem(self._list.row(item))

    def _move_up(self) -> None:
        row = self._list.currentRow()
        if row > 0:
            item = self._list.takeItem(row)
            self._list.insertItem(row - 1, item)
            self._list.setCurrentRow(row - 1)

    def _move_down(self) -> None:
        row = self._list.currentRow()
        if row < self._list.count() - 1:
            item = self._list.takeItem(row)
            self._list.insertItem(row + 1, item)
            self._list.setCurrentRow(row + 1)

    def _on_accept(self) -> None:
        if self._list.count() < 2:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Merge PDFs", "Add at least 2 PDF files to merge.")
            return

        input_paths = [
            self._list.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(self._list.count())
        ]
        first_dir = os.path.dirname(input_paths[0])
        output_path, _ = QFileDialog.getSaveFileName(
            self, "Save Merged PDF", os.path.join(first_dir, "merged.pdf"),
            "PDF Files (*.pdf)"
        )
        if not output_path:
            return

        self.result_params = {
            "input_paths": input_paths,
            "output_path": output_path,
        }
        self.accept()
