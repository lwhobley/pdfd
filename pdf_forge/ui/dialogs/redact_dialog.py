"""Redact dialog — search for text to permanently black out."""
from __future__ import annotations
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QFormLayout, QLabel,
    QLineEdit, QVBoxLayout, QCheckBox, QGroupBox,
)


class RedactDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Redact Text")
        self.setMinimumWidth(380)
        self._build_ui()

    def _build_ui(self) -> None:
        vbox = QVBoxLayout(self)

        warn = QLabel(
            "<b>Warning:</b> Redaction is permanent and cannot be undone.\n"
            "Save to a new file to preserve the original."
        )
        warn.setWordWrap(True)
        vbox.addWidget(warn)

        grp = QGroupBox("Search")
        form = QFormLayout(grp)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Text to redact (one term per line)")
        form.addRow("Search term:", self._search)

        self._case_sensitive = QCheckBox("Case sensitive")
        form.addRow("", self._case_sensitive)

        self._whole_word = QCheckBox("Whole word only")
        form.addRow("", self._whole_word)

        vbox.addWidget(grp)

        note = QLabel(
            "All matches across all pages will be filled with a black rectangle "
            "and the underlying text will be permanently removed."
        )
        note.setWordWrap(True)
        vbox.addWidget(note)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        vbox.addWidget(buttons)

    def get_params(self) -> dict:
        return {
            "search_term":      self._search.text(),
            "case_sensitive":   self._case_sensitive.isChecked(),
            "whole_word":       self._whole_word.isChecked(),
        }
