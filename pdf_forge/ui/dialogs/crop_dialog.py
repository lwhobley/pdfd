"""Crop dialog — set crop margins for PDF pages."""
from __future__ import annotations
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QFormLayout, QGroupBox,
    QSpinBox, QVBoxLayout, QComboBox, QHBoxLayout, QLabel,
)


class CropDialog(QDialog):
    def __init__(self, page_width: float = 595, page_height: float = 842, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Crop Pages")
        self.setMinimumWidth(340)
        self._pw = page_width
        self._ph = page_height
        self._build_ui()

    def _build_ui(self) -> None:
        vbox = QVBoxLayout(self)

        info = QLabel(f"Page size: {self._pw:.0f} × {self._ph:.0f} pt")
        vbox.addWidget(info)

        grp = QGroupBox("Crop margins (points)")
        form = QFormLayout(grp)

        def spin(max_val: int) -> QSpinBox:
            s = QSpinBox()
            s.setRange(0, max_val)
            s.setValue(0)
            s.setSuffix(" pt")
            return s

        self._top    = spin(int(self._ph / 2))
        self._bottom = spin(int(self._ph / 2))
        self._left   = spin(int(self._pw / 2))
        self._right  = spin(int(self._pw / 2))
        form.addRow("Top:",    self._top)
        form.addRow("Bottom:", self._bottom)
        form.addRow("Left:",   self._left)
        form.addRow("Right:",  self._right)
        vbox.addWidget(grp)

        pg_form = QFormLayout()
        self._pages_combo = QComboBox()
        self._pages_combo.addItems(["All pages", "Even pages", "Odd pages"])
        pg_form.addRow("Apply to:", self._pages_combo)
        vbox.addLayout(pg_form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        vbox.addWidget(buttons)

    def get_params(self) -> dict:
        mode_map = {"All pages": "all", "Even pages": "even", "Odd pages": "odd"}
        return {
            "top":    self._top.value(),
            "bottom": self._bottom.value(),
            "left":   self._left.value(),
            "right":  self._right.value(),
            "pages_mode": mode_map[self._pages_combo.currentText()],
        }
