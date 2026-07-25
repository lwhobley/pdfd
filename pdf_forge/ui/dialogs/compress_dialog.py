"""Compress dialog — choose compression level."""
from __future__ import annotations
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QLabel, QVBoxLayout,
    QRadioButton, QButtonGroup, QGroupBox, QSpinBox, QFormLayout,
)


class CompressDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Compress PDF")
        self.setMinimumWidth(360)
        self._build_ui()

    def _build_ui(self) -> None:
        vbox = QVBoxLayout(self)

        grp = QGroupBox("Compression level")
        grp_vbox = QVBoxLayout(grp)

        self._btn_group = QButtonGroup(self)

        self._low = QRadioButton(
            "Low — stream compression only\n"
            "(fast, minimal size reduction)"
        )
        self._med = QRadioButton(
            "Medium — streams + linearize\n"
            "(good for web/fast open)"
        )
        self._high = QRadioButton(
            "High — downsample images + aggressive repack\n"
            "(max reduction, may reduce image quality)"
        )
        self._med.setChecked(True)

        for btn in (self._low, self._med, self._high):
            self._btn_group.addButton(btn)
            grp_vbox.addWidget(btn)

        vbox.addWidget(grp)

        # Image DPI setting for high mode
        self._dpi_form = QFormLayout()
        self._img_dpi = QSpinBox()
        self._img_dpi.setRange(72, 300)
        self._img_dpi.setValue(150)
        self._img_dpi.setSuffix(" DPI")
        self._dpi_form.addRow("Image DPI (high only):", self._img_dpi)
        vbox.addLayout(self._dpi_form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        vbox.addWidget(buttons)

    def get_params(self) -> dict:
        if self._low.isChecked():
            level = "low"
        elif self._high.isChecked():
            level = "high"
        else:
            level = "med"
        return {"level": level, "image_dpi": self._img_dpi.value()}
