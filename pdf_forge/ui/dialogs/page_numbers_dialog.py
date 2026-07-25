"""Page numbers dialog."""
from __future__ import annotations
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QFormLayout, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QSpinBox,
    QVBoxLayout, QComboBox, QCheckBox,
)

_POSITIONS = [
    "Bottom Center",
    "Bottom Left",
    "Bottom Right",
    "Top Center",
    "Top Left",
    "Top Right",
]


class PageNumbersDialog(QDialog):
    def __init__(self, total_pages: int = 1, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Add Page Numbers")
        self.setMinimumWidth(380)
        self._total = total_pages
        self._build_ui()

    def _build_ui(self) -> None:
        vbox = QVBoxLayout(self)

        form = QFormLayout()

        self._position = QComboBox()
        self._position.addItems(_POSITIONS)
        form.addRow("Position:", self._position)

        self._start = QSpinBox()
        self._start.setRange(1, 9999)
        self._start.setValue(1)
        form.addRow("Start number:", self._start)

        self._prefix = QLineEdit()
        self._prefix.setPlaceholderText("e.g. Page ")
        form.addRow("Prefix:", self._prefix)

        self._suffix = QLineEdit()
        form.addRow("Suffix:", self._suffix)

        self._show_total = QCheckBox("Show total  (e.g. 1 / 10)")
        form.addRow("", self._show_total)

        self._font_size = QSpinBox()
        self._font_size.setRange(6, 72)
        self._font_size.setValue(10)
        form.addRow("Font size:", self._font_size)

        self._margin = QSpinBox()
        self._margin.setRange(5, 100)
        self._margin.setValue(30)
        self._margin.setSuffix(" pt")
        form.addRow("Margin:", self._margin)

        vbox.addLayout(form)

        # Page range
        pg_grp = QGroupBox("Apply to")
        pg_form = QFormLayout(pg_grp)
        self._first_page = QSpinBox()
        self._first_page.setRange(1, max(1, self._total))
        self._first_page.setValue(1)
        self._last_page = QSpinBox()
        self._last_page.setRange(1, max(1, self._total))
        self._last_page.setValue(self._total)
        rng = QHBoxLayout()
        rng.addWidget(self._first_page)
        rng.addWidget(QLabel("—"))
        rng.addWidget(self._last_page)
        rng.addStretch()
        pg_form.addRow("Pages:", rng)
        vbox.addWidget(pg_grp)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        vbox.addWidget(buttons)

    def get_params(self) -> dict:
        pos_map = {
            "Bottom Center": "bottom_center",
            "Bottom Left":   "bottom_left",
            "Bottom Right":  "bottom_right",
            "Top Center":    "top_center",
            "Top Left":      "top_left",
            "Top Right":     "top_right",
        }
        return {
            "position": pos_map[self._position.currentText()],
            "start_number": self._start.value(),
            "prefix": self._prefix.text(),
            "suffix": self._suffix.text(),
            "show_total": self._show_total.isChecked(),
            "font_size": self._font_size.value(),
            "margin": self._margin.value(),
            "first_page": self._first_page.value() - 1,
            "last_page": self._last_page.value() - 1,
        }
