"""Application settings dialog."""
from __future__ import annotations
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QPushButton,
    QHBoxLayout, QComboBox, QLabel, QFileDialog, QDialogButtonBox,
    QGroupBox, QTabWidget, QWidget,
)

from pdf_forge.persistence.settings import AppSettings


class SettingsDialog(QDialog):
    def __init__(self, settings: AppSettings, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(480)
        self._settings = settings
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        tabs = QTabWidget()

        # General tab
        general = QWidget()
        gen_layout = QVBoxLayout(general)
        gen_form = QFormLayout()

        self._theme_combo = QComboBox()
        self._theme_combo.addItems(["dark", "light"])
        self._theme_combo.setCurrentText(self._settings.theme)
        gen_form.addRow("Theme:", self._theme_combo)

        self._output_dir_edit = QLineEdit(self._settings.default_output_dir)
        btn_output = QPushButton("Browse…")
        btn_output.clicked.connect(self._browse_output)
        output_row = QHBoxLayout()
        output_row.addWidget(self._output_dir_edit)
        output_row.addWidget(btn_output)
        gen_form.addRow("Default output dir:", output_row)

        gen_layout.addLayout(gen_form)
        gen_layout.addStretch()
        tabs.addTab(general, "General")

        # External tools tab
        tools = QWidget()
        tools_layout = QVBoxLayout(tools)
        tools_form = QFormLayout()

        self._tesseract_edit = QLineEdit(self._settings.tesseract_path)
        self._tesseract_edit.setPlaceholderText("Auto-detect from PATH")
        btn_tess = QPushButton("Browse…")
        btn_tess.clicked.connect(lambda: self._browse_exe(self._tesseract_edit))
        tess_row = QHBoxLayout()
        tess_row.addWidget(self._tesseract_edit)
        tess_row.addWidget(btn_tess)
        tools_form.addRow("Tesseract OCR:", tess_row)

        self._lo_edit = QLineEdit(self._settings.libreoffice_path)
        self._lo_edit.setPlaceholderText("Auto-detect (soffice)")
        btn_lo = QPushButton("Browse…")
        btn_lo.clicked.connect(lambda: self._browse_exe(self._lo_edit))
        lo_row = QHBoxLayout()
        lo_row.addWidget(self._lo_edit)
        lo_row.addWidget(btn_lo)
        tools_form.addRow("LibreOffice:", lo_row)

        tools_layout.addLayout(tools_form)
        tools_layout.addStretch()
        tabs.addTab(tools, "External Tools")

        layout.addWidget(tabs)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _browse_output(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select Default Output Folder")
        if path:
            self._output_dir_edit.setText(path)

    def _browse_exe(self, edit: QLineEdit) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Executable", "", "Executables (*.exe);;All Files (*)"
        )
        if path:
            edit.setText(path)

    def _save(self) -> None:
        self._settings.theme = self._theme_combo.currentText()
        self._settings.default_output_dir = self._output_dir_edit.text()
        self._settings.tesseract_path = self._tesseract_edit.text()
        self._settings.libreoffice_path = self._lo_edit.text()
        self._settings.sync()
        self.accept()
