"""Edit Text dialog — find and replace text in a PDF."""
from __future__ import annotations
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QFormLayout, QGroupBox,
    QLabel, QLineEdit, QVBoxLayout, QCheckBox, QPushButton,
)
from PySide6.QtCore import Qt


class EditTextDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit Text")
        self.setMinimumWidth(400)
        self._build_ui()

    def _build_ui(self) -> None:
        vbox = QVBoxLayout(self)

        grp = QGroupBox("Find and Replace")
        form = QFormLayout(grp)

        self._find = QLineEdit()
        self._find.setPlaceholderText("Text to find")
        form.addRow("Find:", self._find)

        self._replace = QLineEdit()
        self._replace.setPlaceholderText("Replacement text (leave blank to delete)")
        form.addRow("Replace with:", self._replace)

        self._case_sensitive = QCheckBox("Case sensitive")
        self._case_sensitive.setChecked(True)
        form.addRow("", self._case_sensitive)

        vbox.addWidget(grp)

        note = QLabel(
            "All matches across all pages will be replaced. "
            "The original text is permanently removed — save to a new file to preserve the original."
        )
        note.setWordWrap(True)
        vbox.addWidget(note)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self._ok_btn = buttons.button(QDialogButtonBox.Ok)
        self._ok_btn.setEnabled(False)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        vbox.addWidget(buttons)

        self._find.textChanged.connect(self._update_ok)

    def _update_ok(self, text: str) -> None:
        self._ok_btn.setEnabled(bool(text.strip()))

    def get_params(self) -> dict:
        return {
            "find_text":      self._find.text(),
            "replace_text":   self._replace.text(),
            "case_sensitive": self._case_sensitive.isChecked(),
        }
