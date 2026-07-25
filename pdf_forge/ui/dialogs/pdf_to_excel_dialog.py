"""PDF → Excel/CSV dialog."""
from __future__ import annotations
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QFormLayout, QLabel,
    QVBoxLayout, QComboBox,
)


class PDFToExcelDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("PDF → Excel / CSV")
        self.setMinimumWidth(340)
        self._build_ui()

    def _build_ui(self) -> None:
        vbox = QVBoxLayout(self)

        vbox.addWidget(QLabel(
            "Detect tables in the PDF and export them.\n"
            "Uses pdfplumber for table detection."
        ))

        form = QFormLayout()
        self._fmt = QComboBox()
        self._fmt.addItems(["Excel (.xlsx)", "CSV (.csv)"])
        form.addRow("Output format:", self._fmt)
        vbox.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        vbox.addWidget(buttons)

    def get_params(self) -> dict:
        return {"fmt": "xlsx" if self._fmt.currentIndex() == 0 else "csv"}
