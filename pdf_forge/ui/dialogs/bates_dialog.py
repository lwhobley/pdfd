"""Bates number dialog."""
from __future__ import annotations
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout, QLabel,
    QLineEdit, QSpinBox, QVBoxLayout, QComboBox,
)

_POSITIONS = [
    "Bottom Right", "Bottom Left", "Bottom Center",
    "Top Right",    "Top Left",    "Top Center",
]


class BatesDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Add Bates Numbers")
        self.setMinimumWidth(360)
        self._build_ui()

    def _build_ui(self) -> None:
        vbox = QVBoxLayout(self)
        form = QFormLayout()

        self._prefix = QLineEdit()
        self._prefix.setPlaceholderText("e.g. CASE-")
        form.addRow("Prefix:", self._prefix)

        self._suffix = QLineEdit()
        form.addRow("Suffix:", self._suffix)

        self._start = QSpinBox()
        self._start.setRange(0, 9_999_999)
        self._start.setValue(1)
        form.addRow("Start number:", self._start)

        self._pad = QSpinBox()
        self._pad.setRange(1, 10)
        self._pad.setValue(6)
        form.addRow("Zero-pad width:", self._pad)

        self._position = QComboBox()
        self._position.addItems(_POSITIONS)
        form.addRow("Position:", self._position)

        self._font_size = QSpinBox()
        self._font_size.setRange(6, 72)
        self._font_size.setValue(9)
        form.addRow("Font size:", self._font_size)

        vbox.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        vbox.addWidget(buttons)

    def get_params(self) -> dict:
        pos_map = {
            "Bottom Right":  "bottom_right",
            "Bottom Left":   "bottom_left",
            "Bottom Center": "bottom_center",
            "Top Right":     "top_right",
            "Top Left":      "top_left",
            "Top Center":    "top_center",
        }
        return {
            "prefix": self._prefix.text(),
            "suffix": self._suffix.text(),
            "start_number": self._start.value(),
            "pad_width": self._pad.value(),
            "position": pos_map[self._position.currentText()],
            "font_size": self._font_size.value(),
        }
