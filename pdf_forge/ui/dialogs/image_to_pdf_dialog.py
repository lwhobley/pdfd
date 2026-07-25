"""Image → PDF dialog."""
from __future__ import annotations
import os
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
    QGroupBox, QHBoxLayout, QLabel, QListWidget, QPushButton,
    QVBoxLayout, QComboBox, QCheckBox, QSpinBox,
)


class ImageToPDFDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Images → PDF")
        self.setMinimumSize(440, 420)
        self._build_ui()

    def _build_ui(self) -> None:
        vbox = QVBoxLayout(self)

        # File list
        vbox.addWidget(QLabel("Images to include (drag to reorder):"))
        self._file_list = QListWidget()
        self._file_list.setDragDropMode(QListWidget.InternalMove)
        vbox.addWidget(self._file_list)

        btn_row = QHBoxLayout()
        add_btn = QPushButton("Add Files…")
        add_btn.clicked.connect(self._add_files)
        remove_btn = QPushButton("Remove")
        remove_btn.clicked.connect(self._remove_selected)
        btn_row.addWidget(add_btn)
        btn_row.addWidget(remove_btn)
        btn_row.addStretch()
        vbox.addLayout(btn_row)

        # Options
        grp = QGroupBox("Page options")
        form = QFormLayout(grp)

        self._page_size = QComboBox()
        self._page_size.addItems(["Match image size", "A4 (595 × 842 pt)", "Letter (612 × 792 pt)"])
        form.addRow("Page size:", self._page_size)

        self._fit = QCheckBox("Fit image to page (with margins)")
        form.addRow("", self._fit)

        self._dpi = QSpinBox()
        self._dpi.setRange(72, 600)
        self._dpi.setValue(72)
        self._dpi.setSuffix(" DPI")
        form.addRow("Source DPI:", self._dpi)

        vbox.addWidget(grp)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        vbox.addWidget(buttons)

    def _add_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Add Images", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.tiff *.tif *.webp *.gif)"
        )
        for p in paths:
            self._file_list.addItem(p)

    def _remove_selected(self) -> None:
        for item in self._file_list.selectedItems():
            self._file_list.takeItem(self._file_list.row(item))

    def _on_accept(self) -> None:
        if self._file_list.count() == 0:
            return
        self.accept()

    def get_params(self) -> dict:
        size_map = {0: "image", 1: "a4", 2: "letter"}
        return {
            "input_paths": [
                self._file_list.item(i).text()
                for i in range(self._file_list.count())
            ],
            "page_size":   size_map[self._page_size.currentIndex()],
            "fit_to_page": self._fit.isChecked(),
            "dpi":         self._dpi.value(),
        }
