"""PDF → Image dialog."""
from __future__ import annotations
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
    QLabel, QLineEdit, QSpinBox, QVBoxLayout, QComboBox,
    QHBoxLayout, QPushButton,
)

_FORMATS = ["PNG", "JPEG", "TIFF", "BMP"]


class PDFToImageDialog(QDialog):
    def __init__(self, default_dir: str = "", parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("PDF → Images")
        self.setMinimumWidth(400)
        self._default_dir = default_dir
        self._build_ui()

    def _build_ui(self) -> None:
        vbox = QVBoxLayout(self)
        form = QFormLayout()

        self._fmt = QComboBox()
        self._fmt.addItems(_FORMATS)
        form.addRow("Output format:", self._fmt)

        self._dpi = QSpinBox()
        self._dpi.setRange(72, 600)
        self._dpi.setValue(150)
        self._dpi.setSuffix(" DPI")
        form.addRow("DPI:", self._dpi)

        # Output directory
        dir_row = QHBoxLayout()
        self._out_dir = QLineEdit(self._default_dir)
        browse_btn = QPushButton("Browse…")
        browse_btn.clicked.connect(self._browse)
        dir_row.addWidget(self._out_dir, 1)
        dir_row.addWidget(browse_btn)
        form.addRow("Output folder:", dir_row)

        vbox.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        vbox.addWidget(buttons)

    def _browse(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "Output Folder", self._out_dir.text())
        if d:
            self._out_dir.setText(d)

    def get_params(self) -> dict:
        return {
            "fmt":        self._fmt.currentText().lower(),
            "dpi":        self._dpi.value(),
            "output_dir": self._out_dir.text(),
        }
