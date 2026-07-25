"""Encrypt / Decrypt dialogs."""
from __future__ import annotations
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QFormLayout, QGroupBox,
    QLabel, QLineEdit, QVBoxLayout, QCheckBox, QHBoxLayout,
    QPushButton,
)
from PySide6.QtCore import Qt


class EncryptDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Encrypt PDF")
        self.setMinimumWidth(400)
        self._build_ui()

    def _build_ui(self) -> None:
        vbox = QVBoxLayout(self)

        # Passwords
        pw_grp = QGroupBox("Passwords")
        pw_form = QFormLayout(pw_grp)

        self._user_pw = QLineEdit()
        self._user_pw.setEchoMode(QLineEdit.Password)
        self._user_pw.setPlaceholderText("Required to open the document")
        pw_form.addRow("User password:", self._user_pw)

        self._owner_pw = QLineEdit()
        self._owner_pw.setEchoMode(QLineEdit.Password)
        self._owner_pw.setPlaceholderText("Required to change permissions (optional)")
        pw_form.addRow("Owner password:", self._owner_pw)
        vbox.addWidget(pw_grp)

        # Permissions
        perm_grp = QGroupBox("Permissions (for users who open with user password)")
        perm_vbox = QVBoxLayout(perm_grp)

        self._perm_print      = QCheckBox("Allow printing")
        self._perm_print.setChecked(True)
        self._perm_copy       = QCheckBox("Allow copying text/images")
        self._perm_copy.setChecked(True)
        self._perm_modify     = QCheckBox("Allow modifying document")
        self._perm_annot      = QCheckBox("Allow adding/modifying annotations")
        self._perm_annot.setChecked(True)
        self._perm_forms      = QCheckBox("Allow filling form fields")
        self._perm_forms.setChecked(True)
        self._perm_print_hq   = QCheckBox("Allow high-quality printing")
        self._perm_print_hq.setChecked(True)

        for cb in (self._perm_print, self._perm_print_hq, self._perm_copy,
                   self._perm_modify, self._perm_annot, self._perm_forms):
            perm_vbox.addWidget(cb)
        vbox.addWidget(perm_grp)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        vbox.addWidget(buttons)

    def _on_accept(self) -> None:
        if not self._user_pw.text():
            self._user_pw.setFocus()
            return
        self.accept()

    def get_params(self) -> dict:
        return {
            "user_password":  self._user_pw.text(),
            "owner_password": self._owner_pw.text() or None,
            "allow_print":    self._perm_print.isChecked(),
            "allow_print_hq": self._perm_print_hq.isChecked(),
            "allow_copy":     self._perm_copy.isChecked(),
            "allow_modify":   self._perm_modify.isChecked(),
            "allow_annot":    self._perm_annot.isChecked(),
            "allow_forms":    self._perm_forms.isChecked(),
        }


class DecryptDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Decrypt PDF")
        self.setMinimumWidth(320)
        self._build_ui()

    def _build_ui(self) -> None:
        vbox = QVBoxLayout(self)
        vbox.addWidget(QLabel("Enter the password to decrypt and save an unencrypted copy:"))

        form = QFormLayout()
        self._password = QLineEdit()
        self._password.setEchoMode(QLineEdit.Password)
        form.addRow("Password:", self._password)
        vbox.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        vbox.addWidget(buttons)

    def get_params(self) -> dict:
        return {"password": self._password.text()}
