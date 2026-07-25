"""Office → PDF dialog."""
from __future__ import annotations
import os
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
    QGroupBox, QHBoxLayout, QLabel, QListWidget, QPushButton,
    QVBoxLayout, QCheckBox, QLineEdit,
)


class OfficeToPDFDialog(QDialog):
    def __init__(self, libreoffice_path: str = "", parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Office → PDF")
        self.setMinimumSize(480, 420)
        self._lo_path = libreoffice_path
        self._build_ui()

    def _build_ui(self) -> None:
        vbox = QVBoxLayout(self)

        vbox.addWidget(QLabel(
            "Convert Word, Excel, PowerPoint, or ODT files to PDF\n"
            "(requires LibreOffice)."
        ))

        self._file_list = QListWidget()
        self._file_list.setDragDropMode(QListWidget.InternalMove)
        vbox.addWidget(self._file_list)

        btn_row = QHBoxLayout()
        add_btn = QPushButton("Add Files…")
        add_btn.clicked.connect(self._add_files)
        rm_btn = QPushButton("Remove")
        rm_btn.clicked.connect(self._remove_selected)
        btn_row.addWidget(add_btn)
        btn_row.addWidget(rm_btn)
        btn_row.addStretch()
        vbox.addLayout(btn_row)

        # Output dir
        out_grp = QGroupBox("Output")
        out_form = QFormLayout(out_grp)

        dir_row = QHBoxLayout()
        self._out_dir = QLineEdit()
        browse = QPushButton("Browse…")
        browse.clicked.connect(self._browse_dir)
        dir_row.addWidget(self._out_dir, 1)
        dir_row.addWidget(browse)
        out_form.addRow("Output folder:", dir_row)

        self._merge = QCheckBox("Merge all outputs into one PDF")
        out_form.addRow("", self._merge)
        self._merge.toggled.connect(self._on_merge_toggled)

        self._merged_path = QLineEdit()
        self._merged_path.setPlaceholderText("merged.pdf path")
        self._merged_path.setEnabled(False)
        merged_row = QHBoxLayout()
        merged_row.addWidget(self._merged_path, 1)
        merged_browse = QPushButton("…")
        merged_browse.setFixedWidth(28)
        merged_browse.clicked.connect(self._browse_merged)
        merged_row.addWidget(merged_browse)
        out_form.addRow("Merged file:", merged_row)

        vbox.addWidget(out_grp)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        vbox.addWidget(buttons)

    def _add_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Add Office Files", "",
            "Office Files (*.docx *.doc *.odt *.rtf "
            "*.xlsx *.xls *.ods *.csv "
            "*.pptx *.ppt *.odp *.html *.htm *.txt)"
        )
        for p in paths:
            self._file_list.addItem(p)

    def _remove_selected(self) -> None:
        for item in self._file_list.selectedItems():
            self._file_list.takeItem(self._file_list.row(item))

    def _browse_dir(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "Output Folder")
        if d:
            self._out_dir.setText(d)

    def _on_merge_toggled(self, checked: bool) -> None:
        self._merged_path.setEnabled(checked)

    def _browse_merged(self) -> None:
        p, _ = QFileDialog.getSaveFileName(self, "Merged PDF", "", "PDF (*.pdf)")
        if p:
            self._merged_path.setText(p)

    def _on_accept(self) -> None:
        if self._file_list.count() == 0:
            return
        self.accept()

    def get_params(self) -> dict:
        out_dir = self._out_dir.text() or os.path.dirname(
            self._file_list.item(0).text()
        )
        return {
            "input_paths": [
                self._file_list.item(i).text()
                for i in range(self._file_list.count())
            ],
            "output_dir":         out_dir,
            "merge_output":       self._merge.isChecked(),
            "merged_output_path": self._merged_path.text(),
            "libreoffice_path":   self._lo_path,
        }
