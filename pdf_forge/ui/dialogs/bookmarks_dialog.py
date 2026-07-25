"""Bookmarks (TOC) viewer and editor dialog."""
from __future__ import annotations
import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QTreeWidget,
    QTreeWidgetItem, QDialogButtonBox, QLabel, QFileDialog,
    QSpinBox, QLineEdit, QFormLayout, QGroupBox, QMessageBox,
    QAbstractItemView,
)
from PySide6.QtCore import Qt

from pdf_forge.adapters.pikepdf_adapter import PikePDFAdapter


class BookmarksDialog(QDialog):
    def __init__(self, input_path: str, page_count: int, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit Bookmarks")
        self.setMinimumSize(560, 500)
        self._input_path = input_path
        self._page_count = page_count
        self.result_params: dict | None = None

        # Load TOC: list of [level, title, page_1indexed]
        self._toc = PikePDFAdapter.get_toc(input_path)
        self._setup_ui()
        self._populate_tree()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        file_lbl = QLabel(f"File: {os.path.basename(self._input_path)}")
        file_lbl.setStyleSheet("color: #6c6f85; font-size: 11px;")
        layout.addWidget(file_lbl)

        # Tree
        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(["Title", "Page"])
        self._tree.setColumnWidth(0, 380)
        self._tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._tree.itemDoubleClicked.connect(self._edit_item_inline)
        layout.addWidget(self._tree)

        # Add/Edit/Remove buttons
        btn_row = QHBoxLayout()
        self._btn_add = QPushButton("Add Entry…")
        self._btn_add.clicked.connect(self._add_entry)
        self._btn_remove = QPushButton("Remove")
        self._btn_remove.clicked.connect(self._remove_entry)
        self._btn_up = QPushButton("▲")
        self._btn_up.setFixedWidth(30)
        self._btn_up.clicked.connect(self._move_up)
        self._btn_down = QPushButton("▼")
        self._btn_down.setFixedWidth(30)
        self._btn_down.clicked.connect(self._move_down)
        btn_row.addWidget(self._btn_add)
        btn_row.addWidget(self._btn_remove)
        btn_row.addStretch()
        btn_row.addWidget(self._btn_up)
        btn_row.addWidget(self._btn_down)
        layout.addLayout(btn_row)

        # Output
        out_row = QHBoxLayout()
        self._out_edit = QLineEdit()
        self._out_edit.setPlaceholderText("Leave blank to overwrite input")
        btn_browse = QPushButton("…")
        btn_browse.setFixedWidth(28)
        btn_browse.clicked.connect(self._browse_output)
        out_row.addWidget(QLabel("Output:"))
        out_row.addWidget(self._out_edit, stretch=1)
        out_row.addWidget(btn_browse)
        layout.addLayout(out_row)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _populate_tree(self) -> None:
        self._tree.clear()
        # Flatten the toc into tree items respecting level
        stack: list[QTreeWidgetItem] = []
        for level, title, page in self._toc:
            item = QTreeWidgetItem([title, str(page)])
            item.setFlags(
                item.flags()
                | Qt.ItemFlag.ItemIsEditable
            )
            if level == 1 or not stack:
                self._tree.addTopLevelItem(item)
                stack = [item]
            else:
                depth = min(level - 1, len(stack) - 1)
                parent = stack[depth - 1] if depth > 0 else self._tree.invisibleRootItem()
                parent.addChild(item)
                if len(stack) < level:
                    stack.append(item)
                else:
                    stack[level - 1] = item
                    stack = stack[:level]

        self._tree.expandAll()

    def _get_toc_from_tree(self) -> list[tuple[int, str, int]]:
        toc = []

        def _walk(item: QTreeWidgetItem, level: int) -> None:
            title = item.text(0).strip()
            try:
                page = int(item.text(1))
            except ValueError:
                page = 1
            page = max(1, min(page, self._page_count))
            toc.append((level, title, page))
            for i in range(item.childCount()):
                _walk(item.child(i), level + 1)

        root = self._tree.invisibleRootItem()
        for i in range(root.childCount()):
            _walk(root.child(i), 1)

        return toc

    def _edit_item_inline(self, item: QTreeWidgetItem, col: int) -> None:
        self._tree.editItem(item, col)

    def _add_entry(self) -> None:
        dlg = QDialog(self)
        dlg.setWindowTitle("Add Bookmark")
        layout = QVBoxLayout(dlg)
        form = QFormLayout()
        title_edit = QLineEdit()
        page_spin = QSpinBox()
        page_spin.setRange(1, self._page_count)
        page_spin.setValue(1)
        level_spin = QSpinBox()
        level_spin.setRange(1, 6)
        level_spin.setValue(1)
        form.addRow("Title:", title_edit)
        form.addRow("Page:", page_spin)
        form.addRow("Level:", level_spin)
        layout.addLayout(form)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        layout.addWidget(btns)
        if not dlg.exec():
            return

        title = title_edit.text().strip() or "Untitled"
        page = page_spin.value()
        item = QTreeWidgetItem([title, str(page)])
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
        self._tree.addTopLevelItem(item)

    def _remove_entry(self) -> None:
        item = self._tree.currentItem()
        if item:
            parent = item.parent()
            if parent:
                parent.removeChild(item)
            else:
                idx = self._tree.indexOfTopLevelItem(item)
                self._tree.takeTopLevelItem(idx)

    def _move_up(self) -> None:
        item = self._tree.currentItem()
        if not item:
            return
        parent = item.parent() or self._tree.invisibleRootItem()
        idx = parent.indexOfChild(item)
        if idx > 0:
            parent.takeChild(idx)
            parent.insertChild(idx - 1, item)
            self._tree.setCurrentItem(item)

    def _move_down(self) -> None:
        item = self._tree.currentItem()
        if not item:
            return
        parent = item.parent() or self._tree.invisibleRootItem()
        idx = parent.indexOfChild(item)
        if idx < parent.childCount() - 1:
            parent.takeChild(idx)
            parent.insertChild(idx + 1, item)
            self._tree.setCurrentItem(item)

    def _browse_output(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Save PDF", self._input_path, "PDF Files (*.pdf)"
        )
        if path:
            self._out_edit.setText(path)

    def _on_save(self) -> None:
        toc = self._get_toc_from_tree()
        output_path = self._out_edit.text().strip() or self._input_path
        self.result_params = {
            "input_path": self._input_path,
            "output_path": output_path,
            "toc": toc,
        }
        self.accept()
