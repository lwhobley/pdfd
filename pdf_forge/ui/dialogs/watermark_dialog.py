"""Watermark dialog — add text watermarks to PDF pages."""
from __future__ import annotations
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QFormLayout, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QSlider, QSpinBox,
    QVBoxLayout, QComboBox, QColorDialog, QPushButton,
    QCheckBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor


class WatermarkDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Add Watermark")
        self.setMinimumWidth(380)
        self._color = QColor(128, 128, 128)
        self._build_ui()

    def _build_ui(self) -> None:
        vbox = QVBoxLayout(self)

        form = QFormLayout()

        self._text = QLineEdit("CONFIDENTIAL")
        form.addRow("Text:", self._text)

        self._font_size = QSpinBox()
        self._font_size.setRange(8, 200)
        self._font_size.setValue(48)
        form.addRow("Font size:", self._font_size)

        self._angle = QSpinBox()
        self._angle.setRange(0, 360)
        self._angle.setValue(45)
        form.addRow("Angle °:", self._angle)

        # Opacity slider
        opacity_row = QHBoxLayout()
        self._opacity = QSlider(Qt.Horizontal)
        self._opacity.setRange(5, 100)
        self._opacity.setValue(30)
        self._opacity_label = QLabel("30%")
        self._opacity.valueChanged.connect(lambda v: self._opacity_label.setText(f"{v}%"))
        opacity_row.addWidget(self._opacity)
        opacity_row.addWidget(self._opacity_label)
        form.addRow("Opacity:", opacity_row)

        # Color picker
        color_row = QHBoxLayout()
        self._color_btn = QPushButton()
        self._color_btn.setFixedSize(32, 24)
        self._color_btn.clicked.connect(self._pick_color)
        self._update_color_btn()
        color_row.addWidget(self._color_btn)
        color_row.addStretch()
        form.addRow("Color:", color_row)

        vbox.addLayout(form)

        # Page range group
        pg_grp = QGroupBox("Apply to")
        pg_form = QFormLayout(pg_grp)
        self._pages_combo = QComboBox()
        self._pages_combo.addItems(["All pages", "Odd pages", "Even pages", "Custom range"])
        self._pages_combo.currentIndexChanged.connect(self._on_pages_mode)
        pg_form.addRow("Pages:", self._pages_combo)
        self._pages_edit = QLineEdit()
        self._pages_edit.setPlaceholderText("e.g. 1-3, 5, 7-9")
        self._pages_edit.setEnabled(False)
        pg_form.addRow("Range:", self._pages_edit)
        vbox.addWidget(pg_grp)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        vbox.addWidget(buttons)

    def _pick_color(self) -> None:
        c = QColorDialog.getColor(self._color, self, "Pick Watermark Color")
        if c.isValid():
            self._color = c
            self._update_color_btn()

    def _update_color_btn(self) -> None:
        self._color_btn.setStyleSheet(
            f"background-color: {self._color.name()}; border: 1px solid #555;"
        )

    def _on_pages_mode(self, idx: int) -> None:
        self._pages_edit.setEnabled(idx == 3)

    def get_params(self) -> dict:
        mode = self._pages_combo.currentIndex()
        return {
            "text": self._text.text(),
            "font_size": self._font_size.value(),
            "angle": self._angle.value(),
            "opacity": self._opacity.value() / 100.0,
            "color": (
                self._color.redF(),
                self._color.greenF(),
                self._color.blueF(),
            ),
            "pages_mode": mode,
            "pages_range": self._pages_edit.text() if mode == 3 else "",
        }
