"""Digital signature dialog."""
from __future__ import annotations
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
    QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QSpinBox, QVBoxLayout, QPushButton,
)


class SignDialog(QDialog):
    def __init__(self, total_pages: int = 1, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Sign PDF")
        self.setMinimumWidth(420)
        self._total_pages = total_pages
        self._build_ui()

    def _build_ui(self) -> None:
        vbox = QVBoxLayout(self)

        # Certificate
        cert_grp = QGroupBox("Certificate (PFX / P12)")
        cert_form = QFormLayout(cert_grp)

        pfx_row = QHBoxLayout()
        self._pfx = QLineEdit()
        self._pfx.setPlaceholderText("Path to .pfx or .p12 file")
        browse = QPushButton("Browse…")
        browse.clicked.connect(self._browse_pfx)
        pfx_row.addWidget(self._pfx, 1)
        pfx_row.addWidget(browse)
        cert_form.addRow("Certificate:", pfx_row)

        self._password = QLineEdit()
        self._password.setEchoMode(QLineEdit.Password)
        self._password.setPlaceholderText("Leave blank if no password")
        cert_form.addRow("Password:", self._password)
        vbox.addWidget(cert_grp)

        # Signature metadata
        meta_grp = QGroupBox("Signature Details")
        meta_form = QFormLayout(meta_grp)

        self._name = QLineEdit()
        meta_form.addRow("Signer name:", self._name)

        self._reason = QLineEdit()
        self._reason.setPlaceholderText("e.g. Approved")
        meta_form.addRow("Reason:", self._reason)

        self._location = QLineEdit()
        self._location.setPlaceholderText("e.g. New York")
        meta_form.addRow("Location:", self._location)

        self._contact = QLineEdit()
        self._contact.setPlaceholderText("e.g. email@example.com")
        meta_form.addRow("Contact:", self._contact)
        vbox.addWidget(meta_grp)

        # Placement
        place_grp = QGroupBox("Signature Box Placement")
        place_form = QFormLayout(place_grp)

        self._page = QSpinBox()
        self._page.setRange(1, max(1, self._total_pages))
        self._page.setValue(self._total_pages)
        self._page.setSpecialValueText("Last page")
        place_form.addRow("Page:", self._page)

        def coord_spin(val: int) -> QSpinBox:
            s = QSpinBox()
            s.setRange(0, 9999)
            s.setValue(val)
            s.setSuffix(" pt")
            return s

        self._x0 = coord_spin(50)
        self._y0 = coord_spin(50)
        self._x1 = coord_spin(250)
        self._y1 = coord_spin(100)

        box_row = QHBoxLayout()
        for lbl, spin in [("x0", self._x0), ("y0", self._y0), ("x1", self._x1), ("y1", self._y1)]:
            box_row.addWidget(QLabel(lbl))
            box_row.addWidget(spin)
        place_form.addRow("Box (x0,y0,x1,y1):", box_row)
        vbox.addWidget(place_grp)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        vbox.addWidget(buttons)

    def _browse_pfx(self) -> None:
        p, _ = QFileDialog.getOpenFileName(
            self, "Open Certificate", "",
            "PKCS#12 Certificates (*.pfx *.p12);;All Files (*)"
        )
        if p:
            self._pfx.setText(p)

    def _on_accept(self) -> None:
        if not self._pfx.text():
            self._pfx.setFocus()
            return
        self.accept()

    def get_params(self) -> dict:
        return {
            "pfx_path":     self._pfx.text(),
            "pfx_password": self._password.text(),
            "name":         self._name.text(),
            "reason":       self._reason.text(),
            "location":     self._location.text(),
            "contact_info": self._contact.text(),
            "page":         self._page.value() - 1,
            "rect":         (
                self._x0.value(), self._y0.value(),
                self._x1.value(), self._y1.value(),
            ),
        }
