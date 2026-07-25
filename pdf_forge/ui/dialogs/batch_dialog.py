"""Batch processing dialog — run one tool against many PDFs."""
from __future__ import annotations
import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget,
    QListWidgetItem, QLabel, QFileDialog, QDialogButtonBox,
    QGroupBox, QFormLayout, QComboBox, QSpinBox, QCheckBox,
    QLineEdit, QAbstractItemView, QProgressBar, QWidget,
    QStackedWidget, QMessageBox, QTabWidget,
)
from PySide6.QtCore import Qt, Signal, Slot


class BatchDialog(QDialog):
    """Submit the same operation against multiple PDFs.

    Supported batch ops: split, rotate, extract-pages, nup.
    Merge is excluded (different paradigm — many-to-one).
    """

    batch_submitted = Signal(list)  # list of (tool_id, params) tuples

    _OPS = [
        ("split_pdf",    "Split (every N pages)"),
        ("rotate_pages", "Rotate All Pages"),
        ("nup_pdf",      "N-Up Layout"),
    ]

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Batch Processing")
        self.setMinimumSize(600, 500)
        self.result_jobs: list[tuple[str, dict]] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        # === File list ===
        files_group = QGroupBox("Input Files")
        files_layout = QVBoxLayout(files_group)

        self._file_list = QListWidget()
        self._file_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._file_list.setAcceptDrops(True)
        files_layout.addWidget(self._file_list)

        file_btns = QHBoxLayout()
        btn_add = QPushButton("Add Files…")
        btn_add.clicked.connect(self._add_files)
        btn_add_dir = QPushButton("Add Folder…")
        btn_add_dir.clicked.connect(self._add_folder)
        btn_remove = QPushButton("Remove Selected")
        btn_remove.clicked.connect(self._remove_files)
        file_btns.addWidget(btn_add)
        file_btns.addWidget(btn_add_dir)
        file_btns.addWidget(btn_remove)
        file_btns.addStretch()
        self._lbl_count = QLabel("0 files")
        file_btns.addWidget(self._lbl_count)
        files_layout.addLayout(file_btns)
        layout.addWidget(files_group)

        # === Operation ===
        op_group = QGroupBox("Operation")
        op_layout = QVBoxLayout(op_group)

        op_row = QHBoxLayout()
        op_row.addWidget(QLabel("Tool:"))
        self._op_combo = QComboBox()
        for tool_id, label in self._OPS:
            self._op_combo.addItem(label, tool_id)
        self._op_combo.currentIndexChanged.connect(self._on_op_changed)
        op_row.addWidget(self._op_combo)
        op_row.addStretch()
        op_layout.addLayout(op_row)

        # Stacked params widget
        self._params_stack = QStackedWidget()

        # Split params
        split_widget = QWidget()
        split_form = QFormLayout(split_widget)
        self._split_n = QSpinBox()
        self._split_n.setRange(1, 9999)
        self._split_n.setValue(1)
        split_form.addRow("Split every N pages:", self._split_n)
        self._params_stack.addWidget(split_widget)

        # Rotate params
        rotate_widget = QWidget()
        rotate_form = QFormLayout(rotate_widget)
        self._rotate_combo = QComboBox()
        self._rotate_combo.addItems(["90° clockwise", "180°", "90° counter-clockwise"])
        rotate_form.addRow("Rotation:", self._rotate_combo)
        self._params_stack.addWidget(rotate_widget)

        # N-Up params
        nup_widget = QWidget()
        nup_form = QFormLayout(nup_widget)
        self._nup_combo = QComboBox()
        for n, lbl in [(2, "2-up"), (4, "4-up"), (6, "6-up"), (9, "9-up")]:
            self._nup_combo.addItem(lbl, n)
        nup_form.addRow("Layout:", self._nup_combo)
        self._params_stack.addWidget(nup_widget)

        op_layout.addWidget(self._params_stack)
        layout.addWidget(op_group)

        # === Output ===
        out_group = QGroupBox("Output")
        out_layout = QFormLayout(out_group)
        out_dir_row = QHBoxLayout()
        self._out_dir_edit = QLineEdit()
        self._out_dir_edit.setPlaceholderText("Same folder as input (default)")
        btn_out = QPushButton("…")
        btn_out.setFixedWidth(28)
        btn_out.clicked.connect(self._browse_output)
        out_dir_row.addWidget(self._out_dir_edit)
        out_dir_row.addWidget(btn_out)
        out_layout.addRow("Output folder:", out_dir_row)

        self._suffix_edit = QLineEdit("_batch")
        out_layout.addRow("Filename suffix:", self._suffix_edit)
        layout.addWidget(out_group)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Submit Batch")
        buttons.accepted.connect(self._on_submit)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _add_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Add PDFs", "", "PDF Files (*.pdf)"
        )
        for path in paths:
            self._add_path(path)

    def _add_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if not folder:
            return
        import glob
        for path in sorted(glob.glob(os.path.join(folder, "*.pdf"))):
            self._add_path(path)

    def _add_path(self, path: str) -> None:
        # Avoid duplicates
        for i in range(self._file_list.count()):
            if self._file_list.item(i).data(Qt.ItemDataRole.UserRole) == path:
                return
        item = QListWidgetItem(os.path.basename(path))
        item.setData(Qt.ItemDataRole.UserRole, path)
        item.setToolTip(path)
        self._file_list.addItem(item)
        self._lbl_count.setText(f"{self._file_list.count()} files")

    def _remove_files(self) -> None:
        for item in self._file_list.selectedItems():
            self._file_list.takeItem(self._file_list.row(item))
        self._lbl_count.setText(f"{self._file_list.count()} files")

    def _browse_output(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if path:
            self._out_dir_edit.setText(path)

    def _on_op_changed(self, index: int) -> None:
        self._params_stack.setCurrentIndex(index)

    def _on_submit(self) -> None:
        count = self._file_list.count()
        if count == 0:
            QMessageBox.warning(self, "Batch", "Add at least one PDF file.")
            return

        paths = [
            self._file_list.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(count)
        ]
        tool_id = self._op_combo.currentData()
        suffix = self._suffix_edit.text().strip() or "_batch"
        out_dir = self._out_dir_edit.text().strip()

        jobs: list[tuple[str, dict]] = []
        deg_map = {"90° clockwise": 90, "180°": 180, "90° counter-clockwise": 270}

        for path in paths:
            base, ext = os.path.splitext(path)
            file_out_dir = out_dir or os.path.dirname(path)
            out_name = os.path.basename(base) + suffix + ext
            out_path = os.path.join(file_out_dir, out_name)

            if tool_id == "split_pdf":
                params = {
                    "input_path": path,
                    "output_dir": file_out_dir,
                    "mode": "every_n",
                    "every_n": self._split_n.value(),
                }
            elif tool_id == "rotate_pages":
                params = {
                    "input_path": path,
                    "output_path": out_path,
                    "page_indices": [],
                    "degrees": deg_map[self._rotate_combo.currentText()],
                }
            elif tool_id == "nup_pdf":
                params = {
                    "input_path": path,
                    "output_path": out_path,
                    "n": self._nup_combo.currentData(),
                    "landscape": True,
                }
            else:
                continue
            jobs.append((tool_id, params))

        self.result_jobs = jobs
        self.accept()
