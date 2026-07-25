"""Page organizer — drag-and-drop grid for reordering, rotating, and deleting pages."""
from __future__ import annotations
import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QToolBar, QAbstractItemView, QFileDialog,
    QSizePolicy, QFrame, QMessageBox,
)
from PySide6.QtCore import Qt, Signal, QSize, QThreadPool
from PySide6.QtGui import QIcon, QPixmap, QAction

from pdf_forge.adapters.pymupdf_adapter import PyMuPDFAdapter
from pdf_forge.ui.viewer.page_renderer import ThumbnailRenderTask

log = logging.getLogger(__name__)

THUMB_W = 120
THUMB_H = int(THUMB_W * 1.414)
ITEM_W = THUMB_W + 16
ITEM_H = THUMB_H + 28


class PageOrganizerWidget(QWidget):
    """Full-page organizer: thumbnails in a drag-droppable grid.

    Signals:
        apply_requested(list[int]): emitted when user clicks Apply; carries
            the new page order as a list of original 0-based page indices.
        delete_requested(list[int]): emitted for selected page deletion.
        rotate_requested(list[int], int): page indices + degrees.
        extract_requested(list[int]): extract selected to new PDF.
        close_requested(): user closed the organizer.
    """

    apply_requested = Signal(list)          # new_order: list[int]
    delete_requested = Signal(list)         # indices: list[int]
    rotate_requested = Signal(list, int)    # indices, degrees
    extract_requested = Signal(list)        # indices
    close_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._adapter: PyMuPDFAdapter | None = None
        self._pool = QThreadPool.globalInstance()
        self._pixmaps: dict[int, QPixmap] = {}
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Toolbar
        toolbar = QToolBar()
        toolbar.setIconSize(QSize(18, 18))
        toolbar.setStyleSheet("QToolBar { border: none; padding: 4px; background: #181825; }")

        lbl = QLabel("  Page Organizer  ")
        lbl.setStyleSheet("font-weight: bold; color: #89b4fa;")
        toolbar.addWidget(lbl)
        toolbar.addSeparator()

        self._act_rot_left = QAction("↺ Rotate Left", self)
        self._act_rot_left.setToolTip("Rotate selected pages 90° counter-clockwise")
        self._act_rot_left.triggered.connect(lambda: self._rotate(-90))
        toolbar.addAction(self._act_rot_left)

        self._act_rot_right = QAction("↻ Rotate Right", self)
        self._act_rot_right.setToolTip("Rotate selected pages 90° clockwise")
        self._act_rot_right.triggered.connect(lambda: self._rotate(90))
        toolbar.addAction(self._act_rot_right)

        toolbar.addSeparator()

        self._act_delete = QAction("🗑 Delete", self)
        self._act_delete.setToolTip("Delete selected pages")
        self._act_delete.triggered.connect(self._delete_selected)
        toolbar.addAction(self._act_delete)

        self._act_extract = QAction("⬆ Extract", self)
        self._act_extract.setToolTip("Extract selected pages to a new PDF")
        self._act_extract.triggered.connect(self._extract_selected)
        toolbar.addAction(self._act_extract)

        toolbar.addSeparator()

        self._act_select_all = QAction("Select All", self)
        self._act_select_all.setShortcut("Ctrl+A")
        self._act_select_all.triggered.connect(self._select_all)
        toolbar.addAction(self._act_select_all)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(spacer)

        self._lbl_count = QLabel("0 pages")
        self._lbl_count.setStyleSheet("color: #6c6f85; padding-right: 8px;")
        toolbar.addWidget(self._lbl_count)

        self._btn_apply = QPushButton("Apply Order")
        self._btn_apply.setDefault(True)
        self._btn_apply.setToolTip("Save the current page order as a new PDF")
        self._btn_apply.clicked.connect(self._on_apply)
        toolbar.addWidget(self._btn_apply)

        self._btn_close = QPushButton("Close")
        self._btn_close.clicked.connect(self.close_requested.emit)
        toolbar.addWidget(self._btn_close)

        layout.addWidget(toolbar)

        # Help text
        help_lbl = QLabel(
            "Drag pages to reorder  ·  Ctrl+Click to multi-select  ·  Del to delete selected"
        )
        help_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        help_lbl.setStyleSheet(
            "color: #585b70; font-size: 11px; padding: 4px;"
            "background: #1e1e2e; border-bottom: 1px solid #313244;"
        )
        layout.addWidget(help_lbl)

        # Page grid
        self._list = QListWidget()
        self._list.setViewMode(QListWidget.ViewMode.IconMode)
        self._list.setIconSize(QSize(THUMB_W, THUMB_H))
        self._list.setGridSize(QSize(ITEM_W, ITEM_H))
        self._list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self._list.setMovement(QListWidget.Movement.Free)
        self._list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self._list.setDefaultDropAction(Qt.DropAction.MoveAction)
        self._list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._list.setSpacing(8)
        self._list.setStyleSheet(
            "QListWidget { background: #181825; border: none; padding: 8px; }"
            "QListWidget::item { border-radius: 4px; }"
            "QListWidget::item:selected { background: #313244; border: 2px solid #89b4fa; }"
            "QListWidget::item:hover { background: #26273a; }"
        )
        self._list.keyPressEvent = self._list_key_press
        layout.addWidget(self._list, stretch=1)

    # ── Public API ────────────────────────────────────────────────────────────

    def load(self, adapter: PyMuPDFAdapter) -> None:
        self._adapter = adapter
        self._pixmaps.clear()
        self._list.clear()

        count = adapter.page_count
        for i in range(count):
            item = QListWidgetItem(f"  {i + 1}  ")
            item.setData(Qt.ItemDataRole.UserRole, i)  # original index
            item.setData(Qt.ItemDataRole.UserRole + 1, i)  # display label
            item.setSizeHint(QSize(ITEM_W, ITEM_H))
            self._list.addItem(item)
            task = ThumbnailRenderTask(adapter, i, THUMB_W)
            task.signals.ready.connect(self._on_thumb_ready)
            self._pool.start(task)

        self._lbl_count.setText(f"{count} pages")

    def clear(self) -> None:
        self._list.clear()
        self._pixmaps.clear()
        self._adapter = None
        self._lbl_count.setText("0 pages")

    def get_current_order(self) -> list[int]:
        """Return the current page order as original-index list."""
        return [
            self._list.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(self._list.count())
        ]

    def selected_indices_original(self) -> list[int]:
        """Original page indices of selected items."""
        return [
            item.data(Qt.ItemDataRole.UserRole)
            for item in self._list.selectedItems()
        ]

    def selected_positions(self) -> list[int]:
        """Current list positions of selected items (for deletion)."""
        rows = sorted(
            self._list.row(item) for item in self._list.selectedItems()
        )
        return rows

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _on_thumb_ready(self, page_num: int, _zoom: float, pixmap: QPixmap) -> None:
        self._pixmaps[page_num] = pixmap
        for i in range(self._list.count()):
            item = self._list.item(i)
            if item and item.data(Qt.ItemDataRole.UserRole) == page_num:
                item.setIcon(QIcon(pixmap))
                break

    def _on_apply(self) -> None:
        order = self.get_current_order()
        if not order:
            return
        self.apply_requested.emit(order)

    def _rotate(self, degrees: int) -> None:
        indices = self.selected_indices_original()
        if not indices:
            QMessageBox.information(self, "Rotate", "Select pages to rotate first.")
            return
        self.rotate_requested.emit(indices, degrees)

    def _delete_selected(self) -> None:
        rows = sorted(self.selected_positions(), reverse=True)
        if not rows:
            return
        if QMessageBox.question(
            self, "Delete Pages",
            f"Delete {len(rows)} page(s)? This removes them from the organizer view.\n"
            "Click 'Apply Order' to save the result.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        ) != QMessageBox.StandardButton.Yes:
            return
        for row in rows:
            self._list.takeItem(row)
        self._lbl_count.setText(f"{self._list.count()} pages")

    def _extract_selected(self) -> None:
        indices = self.selected_indices_original()
        if not indices:
            QMessageBox.information(self, "Extract", "Select pages to extract first.")
            return
        self.extract_requested.emit(indices)

    def _select_all(self) -> None:
        self._list.selectAll()

    def _list_key_press(self, event) -> None:
        if event.key() == Qt.Key.Key_Delete:
            self._delete_selected()
        else:
            QListWidget.keyPressEvent(self._list, event)
