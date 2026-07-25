"""Split PDF dialog."""
from __future__ import annotations
import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFileDialog, QDialogButtonBox, QRadioButton, QSpinBox,
    QLineEdit, QGroupBox, QFormLayout,
)
from PySide6.QtCore import Qt


class SplitDialog(QDialog):
    def __init__(self, input_path: str = "", parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Split PDF")
        self.setMinimumWidth(440)
        self._input_path = input_path
        self._setup_ui()
        self.result_params: dict | None = None

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Input file
        file_row = QHBoxLayout()
        self._input_edit = QLineEdit(self._input_path)
        self._input_edit.setPlaceholderText("Select input PDF…")
        btn_browse = QPushButton("Browse…")
        btn_browse.clicked.connect(self._browse_input)
        file_row.addWidget(QLabel("Input PDF:"))
        file_row.addWidget(self._input_edit, stretch=1)
        file_row.addWidget(btn_browse)
        layout.addLayout(file_row)

        # Split mode
        mode_group = QGroupBox("Split Mode")
        mode_layout = QVBoxLayout(mode_group)

        self._radio_every_n = QRadioButton("Split every N pages")
        self._radio_every_n.setChecked(True)
        self._spin_n = QSpinBox()
        self._spin_n.setMinimum(1)
        self._spin_n.setMaximum(9999)
        self._spin_n.setValue(1)
        n_row = QHBoxLayout()
        n_row.addWidget(self._radio_every_n)
        n_row.addWidget(self._spin_n)
        n_row.addWidget(QLabel("pages"))
        n_row.addStretch()
        mode_layout.addLayout(n_row)

        self._radio_ranges = QRadioButton("Custom ranges (e.g. 1-3,4-6,7)")
        self._ranges_edit = QLineEdit()
        self._ranges_edit.setPlaceholderText("1-3, 4-6, 7")
        self._ranges_edit.setEnabled(False)
        self._radio_ranges.toggled.connect(
            lambda checked: self._ranges_edit.setEnabled(checked)
        )
        mode_layout.addWidget(self._radio_ranges)
        mode_layout.addWidget(self._ranges_edit)
        layout.addWidget(mode_group)

        # Output directory
        out_row = QHBoxLayout()
        self._out_edit = QLineEdit()
        self._out_edit.setPlaceholderText("Output folder…")
        btn_out = QPushButton("Browse…")
        btn_out.clicked.connect(self._browse_output)
        out_row.addWidget(QLabel("Output folder:"))
        out_row.addWidget(self._out_edit, stretch=1)
        out_row.addWidget(btn_out)
        layout.addLayout(out_row)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Split")
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _browse_input(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select PDF", "", "PDF Files (*.pdf)"
        )
        if path:
            self._input_path = path
            self._input_edit.setText(path)
            if not self._out_edit.text():
                self._out_edit.setText(os.path.dirname(path))

    def _browse_output(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if path:
            self._out_edit.setText(path)

    def _on_accept(self) -> None:
        input_path = self._input_edit.text().strip()
        output_dir = self._out_edit.text().strip()
        if not input_path or not os.path.isfile(input_path):
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Split PDF", "Please select a valid input PDF.")
            return
        if not output_dir:
            output_dir = os.path.dirname(input_path)

        if self._radio_every_n.isChecked():
            self.result_params = {
                "input_path": input_path,
                "output_dir": output_dir,
                "mode": "every_n",
                "every_n": self._spin_n.value(),
            }
        else:
            ranges = self._parse_ranges(self._ranges_edit.text())
            if ranges is None:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Split PDF", "Invalid range format. Use e.g. 1-3,4-6,7")
                return
            self.result_params = {
                "input_path": input_path,
                "output_dir": output_dir,
                "mode": "ranges",
                "ranges": ranges,
            }
        self.accept()

    def _parse_ranges(self, text: str) -> list[tuple[int, int]] | None:
        ranges = []
        for part in text.split(","):
            part = part.strip()
            if not part:
                continue
            if "-" in part:
                parts = part.split("-", 1)
                try:
                    start = int(parts[0].strip()) - 1
                    end = int(parts[1].strip())
                    ranges.append((start, end))
                except ValueError:
                    return None
            else:
                try:
                    n = int(part) - 1
                    ranges.append((n, n + 1))
                except ValueError:
                    return None
        return ranges if ranges else None
