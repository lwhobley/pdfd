"""N-Up layout dialog."""
from __future__ import annotations
import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QComboBox, QCheckBox,
    QDialogButtonBox, QLabel, QFileDialog, QHBoxLayout, QLineEdit,
    QPushButton,
)


class NUpDialog(QDialog):
    def __init__(self, input_path: str = "", parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("N-Up PDF")
        self.setMinimumWidth(400)
        self._input_path = input_path
        self.result_params: dict | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Input
        in_row = QHBoxLayout()
        self._in_edit = QLineEdit(self._input_path)
        self._in_edit.setPlaceholderText("Select input PDF…")
        btn_in = QPushButton("…")
        btn_in.setFixedWidth(28)
        btn_in.clicked.connect(self._browse_input)
        in_row.addWidget(QLabel("Input:"))
        in_row.addWidget(self._in_edit, stretch=1)
        in_row.addWidget(btn_in)
        layout.addLayout(in_row)

        form = QFormLayout()

        self._n_combo = QComboBox()
        for n, label in [(2, "2-up (2×1)"), (4, "4-up (2×2)"),
                          (6, "6-up (3×2)"), (9, "9-up (3×3)")]:
            self._n_combo.addItem(label, n)
        form.addRow("Layout:", self._n_combo)

        self._landscape_check = QCheckBox("Landscape output pages")
        self._landscape_check.setChecked(True)
        form.addRow("", self._landscape_check)

        layout.addLayout(form)

        # Output
        out_row = QHBoxLayout()
        self._out_edit = QLineEdit()
        self._out_edit.setPlaceholderText("Output file…")
        btn_out = QPushButton("…")
        btn_out.setFixedWidth(28)
        btn_out.clicked.connect(self._browse_output)
        out_row.addWidget(QLabel("Output:"))
        out_row.addWidget(self._out_edit, stretch=1)
        out_row.addWidget(btn_out)
        layout.addLayout(out_row)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Create N-Up")
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _browse_input(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select PDF", "", "PDF Files (*.pdf)"
        )
        if path:
            self._input_path = path
            self._in_edit.setText(path)

    def _browse_output(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Save N-Up PDF", "", "PDF Files (*.pdf)"
        )
        if path:
            self._out_edit.setText(path)

    def _on_accept(self) -> None:
        input_path = self._in_edit.text().strip()
        if not input_path or not os.path.isfile(input_path):
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "N-Up PDF", "Select a valid input PDF.")
            return
        output_path = self._out_edit.text().strip()
        if not output_path:
            base, ext = os.path.splitext(input_path)
            n = self._n_combo.currentData()
            output_path = f"{base}_{n}up{ext}"

        self.result_params = {
            "input_path": input_path,
            "output_path": output_path,
            "n": self._n_combo.currentData(),
            "landscape": self._landscape_check.isChecked(),
        }
        self.accept()
