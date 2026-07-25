"""Remove Annotations dialog."""
from __future__ import annotations
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QVBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QCheckBox,
)
from PySide6.QtCore import Qt

_ANNOTATION_TYPES = [
    ("Text (sticky notes)", "Text"),
    ("Highlights", "Highlight"),
    ("Underlines", "Underline"),
    ("Strike-throughs", "StrikeOut"),
    ("Ink / freehand", "Ink"),
    ("Links", "Link"),
    ("Form fields", "Widget"),
    ("Stamps", "Stamp"),
    ("Free text", "FreeText"),
    ("Squares & circles", "Square"),
    ("Lines & arrows", "Line"),
]


class RemoveAnnotationsDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Remove Annotations")
        self.setMinimumWidth(320)
        self._build_ui()

    def _build_ui(self) -> None:
        vbox = QVBoxLayout(self)
        vbox.addWidget(QLabel("Select annotation types to remove:"))

        self._all_check = QCheckBox("Remove ALL annotation types")
        self._all_check.setChecked(True)
        self._all_check.toggled.connect(self._on_all_toggled)
        vbox.addWidget(self._all_check)

        self._list = QListWidget()
        self._list.setEnabled(False)
        for label, code in _ANNOTATION_TYPES:
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, code)
            item.setCheckState(Qt.Checked)
            self._list.addItem(item)
        vbox.addWidget(self._list)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        vbox.addWidget(buttons)

    def _on_all_toggled(self, checked: bool) -> None:
        self._list.setEnabled(not checked)

    def get_params(self) -> dict:
        if self._all_check.isChecked():
            return {"type_filter": None}
        types = []
        for i in range(self._list.count()):
            item = self._list.item(i)
            if item.checkState() == Qt.Checked:
                types.append(item.data(Qt.UserRole))
        return {"type_filter": types if types else None}
