"""PDF page viewer — scrollable single-page view with zoom and navigation."""
from __future__ import annotations
import logging
from PySide6.QtWidgets import (
    QWidget, QScrollArea, QLabel, QVBoxLayout, QHBoxLayout,
    QSizePolicy, QFrame, QLineEdit,
)
from PySide6.QtCore import Qt, Signal, QThreadPool, QSize, QPoint, QRect
from PySide6.QtGui import QPixmap, QWheelEvent, QKeyEvent, QFont

from pdf_forge.adapters.pymupdf_adapter import PyMuPDFAdapter
from pdf_forge.ui.viewer.page_renderer import PageRenderTask

log = logging.getLogger(__name__)

MIN_ZOOM = 0.2
MAX_ZOOM = 5.0
ZOOM_STEP = 0.15


class PageLabel(QLabel):
    """Label that displays one rendered PDF page."""

    text_edit_clicked = Signal(QPoint)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.setMinimumSize(100, 100)
        self.setText("Open a PDF to start")
        self.setStyleSheet("color: #585b70; font-size: 18px;")
        self._text_edit_mode = False

    def set_text_edit_mode(self, enabled: bool) -> None:
        self._text_edit_mode = enabled
        self.setCursor(
            Qt.CursorShape.IBeamCursor if enabled else Qt.CursorShape.ArrowCursor
        )

    def mousePressEvent(self, event) -> None:
        if self._text_edit_mode and event.button() == Qt.MouseButton.LeftButton:
            self.text_edit_clicked.emit(event.position().toPoint())
            event.accept()
            return
        super().mousePressEvent(event)


class InlineTextEditor(QLineEdit):
    """Single-line editor displayed over text on the rendered page."""

    accepted = Signal()
    cancelled = Signal()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.cancelled.emit()
            event.accept()
            return
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.accepted.emit()
            event.accept()
            return
        super().keyPressEvent(event)


class PDFViewer(QWidget):
    """Main page viewer widget.

    Owns the PyMuPDFAdapter for the currently displayed document.
    Renders pages on QThreadPool, never blocks the UI thread.
    """

    page_changed = Signal(int)       # current page (0-indexed)
    zoom_changed = Signal(float)     # current zoom
    text_edit_committed = Signal(dict)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._adapter: PyMuPDFAdapter | None = None
        self._current_page: int = 0
        self._zoom: float = 1.0
        self._is_dirty: bool = False
        self._source_file_path: str | None = None
        self._pool = QThreadPool.globalInstance()
        self._pool.setMaxThreadCount(max(2, self._pool.maxThreadCount()))
        self._pending_render: int = -1
        self._text_edit_mode = False
        self._inline_editor: InlineTextEditor | None = None
        self._editing_text: dict | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )

        self._page_label = PageLabel()
        self._page_label.text_edit_clicked.connect(self._begin_text_edit)
        self._scroll.setWidget(self._page_label)
        layout.addWidget(self._scroll)

    # ── Public API ────────────────────────────────────────────────────────────

    def load(self, adapter: PyMuPDFAdapter) -> None:
        self._adapter = adapter
        self._current_page = 0
        self._zoom = 1.0
        self._is_dirty = False
        self._source_file_path = adapter.path
        self._render_current()

    def close_document(self) -> None:
        self._close_inline_editor()
        self._adapter = None
        self._is_dirty = False
        self._source_file_path = None
        self._page_label.setPixmap(QPixmap())
        self._page_label.setText("Open a PDF to start")
        self._page_label.setStyleSheet("color: #585b70; font-size: 18px;")

    def go_to_page(self, page_num: int) -> None:
        if not self._adapter:
            return
        page_num = max(0, min(page_num, self._adapter.page_count - 1))
        if page_num != self._current_page:
            self._close_inline_editor()
            self._current_page = page_num
            self._render_current()
            self.page_changed.emit(page_num)

    def next_page(self) -> None:
        self.go_to_page(self._current_page + 1)

    def prev_page(self) -> None:
        self.go_to_page(self._current_page - 1)

    def set_zoom(self, zoom: float) -> None:
        zoom = max(MIN_ZOOM, min(MAX_ZOOM, zoom))
        if abs(zoom - self._zoom) > 0.001:
            self._close_inline_editor()
            self._zoom = zoom
            self._render_current()
            self.zoom_changed.emit(zoom)

    def zoom_in(self) -> None:
        self.set_zoom(self._zoom + ZOOM_STEP)

    def zoom_out(self) -> None:
        self.set_zoom(self._zoom - ZOOM_STEP)

    def zoom_fit_width(self) -> None:
        if not self._adapter:
            return
        rect = self._adapter.get_page_rect(self._current_page)
        available = self._scroll.viewport().width() - 20
        zoom = available / rect.width
        self.set_zoom(zoom)

    def zoom_fit_page(self) -> None:
        if not self._adapter:
            return
        rect = self._adapter.get_page_rect(self._current_page)
        vp = self._scroll.viewport()
        zoom_w = (vp.width() - 20) / rect.width
        zoom_h = (vp.height() - 20) / rect.height
        self.set_zoom(min(zoom_w, zoom_h))

    @property
    def current_page(self) -> int:
        return self._current_page

    @property
    def zoom(self) -> float:
        return self._zoom

    @property
    def page_count(self) -> int:
        return self._adapter.page_count if self._adapter else 0

    # ── In-place editing support ───────────────────────────────────────────────

    def current_doc(self) -> object | None:
        """Return the underlying fitz.Document, or None if no PDF open."""
        return self._adapter.doc if self._adapter else None

    def is_dirty(self) -> bool:
        """Check if the document has unsaved changes."""
        return self._is_dirty

    def set_dirty(self, dirty: bool) -> None:
        """Mark the document as modified or clean."""
        self._is_dirty = dirty

    def source_file_path(self) -> str | None:
        """Return the path of the currently open PDF file."""
        return self._source_file_path

    def reload_from_memory(self) -> None:
        """Refresh the display after the in-memory document was modified.

        Call this after applying a tool to update the rendered view.
        """
        if self._adapter:
            self._close_inline_editor()
            self._render_current()

    def set_text_edit_mode(self, enabled: bool) -> None:
        """Enable click-to-edit text lines on the currently displayed page."""
        self._text_edit_mode = enabled
        self._page_label.set_text_edit_mode(enabled)
        if not enabled:
            self._close_inline_editor()

    def text_edit_mode(self) -> bool:
        return self._text_edit_mode

    # ── Rendering ─────────────────────────────────────────────────────────────

    def _render_current(self) -> None:
        if not self._adapter:
            return
        self._pending_render = self._current_page
        task = PageRenderTask(self._adapter, self._current_page, self._zoom)
        task.signals.ready.connect(self._on_page_ready)
        task.signals.error.connect(self._on_render_error)
        self._pool.start(task)

    def _on_page_ready(self, page_num: int, zoom: float, pixmap: QPixmap) -> None:
        if page_num == self._current_page and abs(zoom - self._zoom) < 0.001:
            self._page_label.setPixmap(pixmap)
            self._page_label.setText("")
            self._page_label.adjustSize()

    def _begin_text_edit(self, point: QPoint) -> None:
        if not self._adapter or self._inline_editor:
            return
        pixmap = self._page_label.pixmap()
        if pixmap.isNull():
            return
        page = self._adapter.doc[self._current_page]
        page_rect = page.rect
        offset_x = (self._page_label.width() - pixmap.width()) / 2
        offset_y = (self._page_label.height() - pixmap.height()) / 2
        pixel_x, pixel_y = point.x() - offset_x, point.y() - offset_y
        if not (0 <= pixel_x <= pixmap.width() and 0 <= pixel_y <= pixmap.height()):
            return

        scale_x = pixmap.width() / page_rect.width
        scale_y = pixmap.height() / page_rect.height
        pdf_x = page_rect.x0 + pixel_x / scale_x
        pdf_y = page_rect.y0 + pixel_y / scale_y
        target = self._find_text_line(page, pdf_x, pdf_y)
        if target is None:
            target = {
                "page_num": self._current_page,
                "rect": (pdf_x, pdf_y - 12, pdf_x + 180, pdf_y + 4),
                "original_text": "",
                "font_size": 12.0,
                "color": (0.0, 0.0, 0.0),
            }

        rect = target["rect"]
        left = int(offset_x + (rect[0] - page_rect.x0) * scale_x)
        top = int(offset_y + (rect[1] - page_rect.y0) * scale_y)
        width = max(120, int((rect[2] - rect[0]) * scale_x) + 18)
        height = max(24, int((rect[3] - rect[1]) * scale_y) + 10)
        editor = InlineTextEditor(self._page_label)
        editor.setGeometry(QRect(left, top, width, height))
        editor.setText(target["original_text"])
        font = QFont()
        font.setPointSizeF(max(8.0, target["font_size"] * self._zoom))
        editor.setFont(font)
        editor.setStyleSheet("background: white; color: black; border: 2px solid #3b82f6;")
        editor.accepted.connect(self._commit_inline_text)
        editor.cancelled.connect(self._close_inline_editor)
        editor.show()
        editor.setFocus()
        editor.selectAll()
        self._inline_editor = editor
        self._editing_text = target

    def _find_text_line(self, page, x: float, y: float) -> dict | None:
        """Find the nearest extracted text line under the pointer."""
        closest: tuple[float, dict] | None = None
        for block in page.get_text("dict").get("blocks", []):
            for line in block.get("lines", []):
                rect = line.get("bbox")
                spans = line.get("spans", [])
                text = "".join(span.get("text", "") for span in spans)
                if not rect or not spans or not text:
                    continue
                distance = max(rect[0] - x, 0, x - rect[2], rect[1] - y, 0, y - rect[3])
                if distance > 8 / self._zoom:
                    continue
                if closest is None or distance < closest[0]:
                    span = spans[0]
                    packed_color = span.get("color", 0)
                    closest = (distance, {
                        "page_num": self._current_page,
                        "rect": tuple(rect),
                        "original_text": text,
                        "font_size": span.get("size", 12.0),
                        "color": (
                            ((packed_color >> 16) & 255) / 255,
                            ((packed_color >> 8) & 255) / 255,
                            (packed_color & 255) / 255,
                        ),
                    })
        return closest[1] if closest else None

    def _commit_inline_text(self) -> None:
        if self._inline_editor and self._editing_text:
            edit = dict(self._editing_text)
            edit["text"] = self._inline_editor.text()
            self.text_edit_committed.emit(edit)
        self._close_inline_editor()

    def _close_inline_editor(self) -> None:
        if self._inline_editor:
            self._inline_editor.deleteLater()
        self._inline_editor = None
        self._editing_text = None

    def _on_render_error(self, page_num: int, error: str) -> None:
        log.warning("Render error page %d: %s", page_num, error)
        if page_num == self._current_page:
            self._page_label.setText(f"Render error: {error}")

    # ── Input handling ────────────────────────────────────────────────────────

    def wheelEvent(self, event: QWheelEvent) -> None:
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self.zoom_in()
            elif delta < 0:
                self.zoom_out()
            event.accept()
        else:
            super().wheelEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        key = event.key()
        if key in (Qt.Key.Key_Right, Qt.Key.Key_Down, Qt.Key.Key_PageDown):
            self.next_page()
        elif key in (Qt.Key.Key_Left, Qt.Key.Key_Up, Qt.Key.Key_PageUp):
            self.prev_page()
        elif key == Qt.Key.Key_Home:
            self.go_to_page(0)
        elif key == Qt.Key.Key_End:
            self.go_to_page(self.page_count - 1)
        elif key == Qt.Key.Key_Plus and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.zoom_in()
        elif key == Qt.Key.Key_Minus and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.zoom_out()
        else:
            super().keyPressEvent(event)
