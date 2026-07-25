"""Flatten dialog — rasterize PDF to remove form fields / annotations."""
from __future__ import annotations
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QFormLayout, QLabel,
    QSpinBox, QVBoxLayout, QComboBox,
)


class FlattenDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Flatten PDF")
        self.setMinimumWidth(340)
        self._build_ui()

    def _build_ui(self) -> None:
        vbox = QVBoxLayout(self)

        info = QLabel(
            "Flattening renders each page to a raster image, removing all "
            "interactive elements (forms, annotations, layers)."
        )
        info.setWordWrap(True)
        vbox.addWidget(info)

        form = QFormLayout()

        self._dpi = QSpinBox()
        self._dpi.setRange(72, 600)
        self._dpi.setValue(150)
        self._dpi.setSuffix(" DPI")
        form.addRow("Render DPI:", self._dpi)

        self._fmt = QComboBox()
        self._fmt.addItems(["PNG (lossless)", "JPEG (smaller file)"])
        form.addRow("Image format:", self._fmt)

        vbox.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        vbox.addWidget(buttons)

    def get_params(self) -> dict:
        return {
            "render_dpi": self._dpi.value(),
            "image_format": "jpeg" if self._fmt.currentIndex() == 1 else "png",
        }
