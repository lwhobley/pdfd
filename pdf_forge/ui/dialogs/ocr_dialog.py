"""OCR dialog — make scanned PDF text-searchable."""
from __future__ import annotations
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QFormLayout, QLabel,
    QSpinBox, QVBoxLayout, QComboBox, QCheckBox,
)

_COMMON_LANGS = [
    ("English", "eng"),
    ("French", "fra"),
    ("German", "deu"),
    ("Spanish", "spa"),
    ("Italian", "ita"),
    ("Portuguese", "por"),
    ("Dutch", "nld"),
    ("Chinese (Simplified)", "chi_sim"),
    ("Chinese (Traditional)", "chi_tra"),
    ("Japanese", "jpn"),
    ("Korean", "kor"),
    ("Arabic", "ara"),
    ("Russian", "rus"),
]


class OCRDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("OCR — Make Searchable")
        self.setMinimumWidth(380)
        self._build_ui()

    def _build_ui(self) -> None:
        vbox = QVBoxLayout(self)

        info = QLabel(
            "Renders each page to an image and runs OCR to produce a "
            "text-searchable PDF. Requires Tesseract (preferred) or EasyOCR."
        )
        info.setWordWrap(True)
        vbox.addWidget(info)

        form = QFormLayout()

        self._lang = QComboBox()
        for label, code in _COMMON_LANGS:
            self._lang.addItem(label, code)
        form.addRow("Language:", self._lang)

        self._dpi = QSpinBox()
        self._dpi.setRange(100, 400)
        self._dpi.setValue(200)
        self._dpi.setSuffix(" DPI")
        form.addRow("Render DPI:", self._dpi)

        self._skip_text = QCheckBox("Skip pages that already contain text")
        self._skip_text.setChecked(True)
        form.addRow("", self._skip_text)

        vbox.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        vbox.addWidget(buttons)

    def get_params(self) -> dict:
        return {
            "language":        self._lang.currentData(),
            "dpi":             self._dpi.value(),
            "skip_text_pages": self._skip_text.isChecked(),
        }
