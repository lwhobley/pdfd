"""PDF metadata viewer and editor dialog."""
from __future__ import annotations
import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QDialogButtonBox,
    QGroupBox, QLabel, QPushButton, QHBoxLayout, QFileDialog,
)

from pdf_forge.adapters.pikepdf_adapter import PikePDFAdapter


class MetadataDialog(QDialog):
    def __init__(self, input_path: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit Metadata")
        self.setMinimumWidth(480)
        self._input_path = input_path
        self._metadata = PikePDFAdapter.get_metadata(input_path)
        self.result_params: dict | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        file_lbl = QLabel(f"File: {os.path.basename(self._input_path)}")
        file_lbl.setStyleSheet("color: #6c6f85; font-size: 11px;")
        layout.addWidget(file_lbl)

        group = QGroupBox("Document Information")
        form = QFormLayout(group)

        self._edits: dict[str, QLineEdit] = {}
        fields = [
            ("Title", "Title"),
            ("Author", "Author"),
            ("Subject", "Subject"),
            ("Keywords", "Keywords"),
            ("Creator", "Creator (application)"),
        ]
        for key, label in fields:
            edit = QLineEdit(self._metadata.get(key, ""))
            self._edits[key] = edit
            form.addRow(f"{label}:", edit)

        # Read-only fields
        producer = QLineEdit(self._metadata.get("Producer", ""))
        producer.setReadOnly(True)
        producer.setStyleSheet("color: #6c6f85;")
        form.addRow("Producer:", producer)

        layout.addWidget(group)

        # Output file
        out_row = QHBoxLayout()
        self._out_edit = QLineEdit()
        self._out_edit.setPlaceholderText("Save as (leave blank to overwrite)")
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

    def _browse_output(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Save PDF", self._input_path, "PDF Files (*.pdf)"
        )
        if path:
            self._out_edit.setText(path)

    def _on_save(self) -> None:
        metadata = {
            key: edit.text().strip()
            for key, edit in self._edits.items()
        }
        output_path = self._out_edit.text().strip() or self._input_path
        self.result_params = {
            "input_path": self._input_path,
            "output_path": output_path,
            "metadata": metadata,
        }
        self.accept()
