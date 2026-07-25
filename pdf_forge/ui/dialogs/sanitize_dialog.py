"""Sanitize PDF dialog."""
from __future__ import annotations
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QLabel, QVBoxLayout, QCheckBox, QGroupBox,
)


class SanitizeDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Sanitize PDF")
        self.setMinimumWidth(360)
        self._build_ui()

    def _build_ui(self) -> None:
        vbox = QVBoxLayout(self)

        vbox.addWidget(QLabel(
            "Remove potentially sensitive or risky content from the PDF."
        ))

        grp = QGroupBox("Remove")
        grp_vbox = QVBoxLayout(grp)

        self._metadata   = QCheckBox("Metadata (author, creation date, software info)")
        self._javascript = QCheckBox("JavaScript (actions, open-action scripts)")
        self._embedded   = QCheckBox("Embedded files and attachments")
        self._links      = QCheckBox("Hyperlinks (URL annotations)")

        self._metadata.setChecked(True)
        self._javascript.setChecked(True)
        self._embedded.setChecked(True)

        for cb in (self._metadata, self._javascript, self._embedded, self._links):
            grp_vbox.addWidget(cb)

        vbox.addWidget(grp)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        vbox.addWidget(buttons)

    def get_params(self) -> dict:
        return {
            "remove_metadata":   self._metadata.isChecked(),
            "remove_javascript": self._javascript.isChecked(),
            "remove_embedded":   self._embedded.isChecked(),
            "remove_links":      self._links.isChecked(),
        }
