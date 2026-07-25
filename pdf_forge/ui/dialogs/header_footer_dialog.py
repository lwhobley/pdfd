"""Header/Footer dialog — 6 slots: header/footer × left/center/right."""
from __future__ import annotations
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QFormLayout, QGroupBox,
    QLabel, QLineEdit, QSpinBox, QVBoxLayout, QGridLayout,
)


class HeaderFooterDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Add Header / Footer")
        self.setMinimumWidth(460)
        self._build_ui()

    def _build_ui(self) -> None:
        vbox = QVBoxLayout(self)

        hint = QLabel(
            "Tokens: <b>{page}</b> &nbsp; <b>{total}</b> &nbsp; "
            "<b>{filename}</b> &nbsp; <b>{date}</b>"
        )
        hint.setWordWrap(True)
        vbox.addWidget(hint)

        for section, label in (("header", "Header"), ("footer", "Footer")):
            grp = QGroupBox(label)
            grid = QGridLayout(grp)
            grid.addWidget(QLabel("Left"), 0, 1)
            grid.addWidget(QLabel("Center"), 0, 2)
            grid.addWidget(QLabel("Right"), 0, 3)

            for row, side in enumerate(("left", "center", "right"), start=1):
                edit = QLineEdit()
                edit.setPlaceholderText(f"{section} {side}")
                setattr(self, f"_{section}_{side}", edit)
                grid.addWidget(edit, row, row)

            # redo layout as single row
            grp2 = QGroupBox(label)
            form = QFormLayout(grp2)
            for side in ("left", "center", "right"):
                form.addRow(side.capitalize() + ":", getattr(self, f"_{section}_{side}"))
            vbox.addWidget(grp2)

        form2 = QFormLayout()
        self._font_size = QSpinBox()
        self._font_size.setRange(6, 36)
        self._font_size.setValue(9)
        form2.addRow("Font size:", self._font_size)

        self._margin = QSpinBox()
        self._margin.setRange(5, 100)
        self._margin.setValue(30)
        self._margin.setSuffix(" pt")
        form2.addRow("Margin:", self._margin)
        vbox.addLayout(form2)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        vbox.addWidget(buttons)

    def get_params(self) -> dict:
        return {
            "header_left":    self._header_left.text(),
            "header_center":  self._header_center.text(),
            "header_right":   self._header_right.text(),
            "footer_left":    self._footer_left.text(),
            "footer_center":  self._footer_center.text(),
            "footer_right":   self._footer_right.text(),
            "font_size":      self._font_size.value(),
            "margin":         self._margin.value(),
        }
