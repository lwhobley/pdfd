"""PDF'D — main window."""
from __future__ import annotations
import logging
import os
import fitz
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QSplitter,
    QTabWidget, QFileDialog, QMessageBox, QLabel, QStatusBar,
    QToolBar, QApplication, QDockWidget, QSpinBox, QComboBox,
    QSizePolicy,
)
from PySide6.QtCore import Qt, Slot, QSize, Signal
from PySide6.QtGui import QAction, QKeySequence, QIcon, QCloseEvent

from pdf_forge import APP_NAME, __version__
from pdf_forge.persistence.settings import AppSettings
from pdf_forge.persistence.recent_files import RecentFiles
from pdf_forge.persistence.job_history import JobHistory
from pdf_forge.services.pdf_service import PDFService, DocumentHandle
from pdf_forge.workers.job_queue import JobQueue
from pdf_forge.tools.registry import registry
from pdf_forge.adapters.capability import Capabilities

from pdf_forge.ui.viewer.pdf_viewer import PDFViewer
from pdf_forge.ui.viewer.thumbnail_panel import ThumbnailPanel
from pdf_forge.ui.sidebar.left_sidebar import LeftSidebar
from pdf_forge.ui.sidebar.right_sidebar import RightSidebar
from pdf_forge.ui.panels.jobs_panel import JobsPanel
from pdf_forge.ui.widgets.drop_zone import DropZone
from pdf_forge.ui.dialogs.merge_dialog import MergeDialog
from pdf_forge.ui.dialogs.split_dialog import SplitDialog
from pdf_forge.ui.dialogs.settings_dialog import SettingsDialog
from pdf_forge.ui.dialogs.metadata_dialog import MetadataDialog
from pdf_forge.ui.dialogs.bookmarks_dialog import BookmarksDialog
from pdf_forge.ui.dialogs.nup_dialog import NUpDialog
from pdf_forge.ui.dialogs.batch_dialog import BatchDialog
from pdf_forge.ui.dialogs.watermark_dialog import WatermarkDialog
from pdf_forge.ui.dialogs.page_numbers_dialog import PageNumbersDialog
from pdf_forge.ui.dialogs.bates_dialog import BatesDialog
from pdf_forge.ui.dialogs.header_footer_dialog import HeaderFooterDialog
from pdf_forge.ui.dialogs.crop_dialog import CropDialog
from pdf_forge.ui.dialogs.redact_dialog import RedactDialog
from pdf_forge.ui.dialogs.edit_text_dialog import EditTextDialog
from pdf_forge.ui.dialogs.flatten_dialog import FlattenDialog
from pdf_forge.ui.dialogs.remove_annotations_dialog import RemoveAnnotationsDialog
from pdf_forge.ui.dialogs.compress_dialog import CompressDialog
from pdf_forge.ui.dialogs.encrypt_dialog import EncryptDialog, DecryptDialog
from pdf_forge.ui.dialogs.image_to_pdf_dialog import ImageToPDFDialog
from pdf_forge.ui.dialogs.pdf_to_image_dialog import PDFToImageDialog
from pdf_forge.ui.dialogs.ocr_dialog import OCRDialog
from pdf_forge.ui.dialogs.office_to_pdf_dialog import OfficeToPDFDialog
from pdf_forge.ui.dialogs.sign_dialog import SignDialog
from pdf_forge.ui.dialogs.pdf_to_excel_dialog import PDFToExcelDialog
from pdf_forge.ui.dialogs.sanitize_dialog import SanitizeDialog
from pdf_forge.ui.organizer.page_organizer import PageOrganizerWidget
from pdf_forge.ui.workflow.workflow_window import WorkflowWindow
from pdf_forge.ui.undo_stack import UndoStack

log = logging.getLogger(__name__)


class DocumentTab(QWidget):
    """One tab in the multi-document interface.

    Hosts two modes, switched via a stacked widget:
      0 = Viewer mode  (thumbnail strip + page viewer)
      1 = Organizer mode (full-screen drag-drop grid)
    """

    organizer_apply = Signal(list)        # new page order
    organizer_delete = Signal(list)       # page indices to delete
    organizer_rotate = Signal(list, int)  # page indices, degrees
    organizer_extract = Signal(list)      # page indices to extract

    def __init__(self, handle: DocumentHandle, parent=None) -> None:
        super().__init__(parent)
        self.handle = handle
        self._undo_stack = UndoStack()

        from PySide6.QtWidgets import QStackedWidget
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self._stack = QStackedWidget()

        # ── Mode 0: Viewer ─────────────────────────────────────
        viewer_widget = QWidget()
        viewer_layout = QHBoxLayout(viewer_widget)
        viewer_layout.setContentsMargins(0, 0, 0, 0)
        viewer_layout.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.thumbnails = ThumbnailPanel()
        self.thumbnails.setMinimumWidth(130)
        self.thumbnails.setMaximumWidth(180)
        splitter.addWidget(self.thumbnails)

        self.viewer = PDFViewer()
        splitter.addWidget(self.viewer)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([160, 800])
        viewer_layout.addWidget(splitter)
        self._stack.addWidget(viewer_widget)

        # ── Mode 1: Organizer ──────────────────────────────────
        self.organizer = PageOrganizerWidget()
        self.organizer.apply_requested.connect(self.organizer_apply)
        self.organizer.delete_requested.connect(self.organizer_delete)
        self.organizer.rotate_requested.connect(self.organizer_rotate)
        self.organizer.extract_requested.connect(self.organizer_extract)
        self.organizer.close_requested.connect(self._exit_organizer)
        self._stack.addWidget(self.organizer)

        main_layout.addWidget(self._stack)

        # Load document
        if handle.adapter:
            self.viewer.load(handle.adapter)
            self.thumbnails.load(handle.adapter)
            self.thumbnails.page_clicked.connect(self.viewer.go_to_page)
            self.viewer.page_changed.connect(self.thumbnails.set_current_page)

    def enter_organizer(self) -> None:
        if self.handle.adapter:
            self.organizer.load(self.handle.adapter)
        self._stack.setCurrentIndex(1)

    def _exit_organizer(self) -> None:
        self.organizer.clear()
        self._stack.setCurrentIndex(0)

    def is_organizer_mode(self) -> bool:
        return self._stack.currentIndex() == 1


class MainWindow(QMainWindow):
    def __init__(self, settings: AppSettings, parent=None) -> None:
        super().__init__(parent)
        self._settings = settings
        self._recent = RecentFiles()
        self._history = JobHistory()
        self._pdf_service = PDFService(self._recent)
        self._job_queue = JobQueue(self._history, parent=self)
        self._current_file_path: str | None = None

        Capabilities.detect(settings)
        registry.discover()

        self.setWindowTitle(APP_NAME)
        self.resize(1280, 820)
        self.setAcceptDrops(True)

        self._build_ui()
        self._build_menu()
        self._build_toolbar()
        self._connect_events()
        self._restore_geometry()

        self._status_bar.showMessage("Ready")
        log.info("MainWindow initialized")

    # ── UI Construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Outer horizontal splitter: left sidebar | content | right sidebar
        h_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left sidebar
        self._left_sidebar = LeftSidebar(self._recent)
        self._left_sidebar.tool_requested.connect(self._on_tool_requested)
        self._left_sidebar.recent_file_clicked.connect(self.open_file)
        h_splitter.addWidget(self._left_sidebar)

        # Center: tab widget (documents) + welcome screen
        center = QWidget()
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(0)

        self._tab_widget = QTabWidget()
        self._tab_widget.setTabsClosable(True)
        self._tab_widget.setMovable(True)
        self._tab_widget.tabCloseRequested.connect(self._close_tab)
        self._tab_widget.currentChanged.connect(self._on_tab_changed)

        self._drop_zone = DropZone()
        self._drop_zone.files_dropped.connect(self._open_files)

        self._tab_widget.hide()
        center_layout.addWidget(self._drop_zone, stretch=1)
        center_layout.addWidget(self._tab_widget, stretch=1)
        h_splitter.addWidget(center)

        # Right sidebar
        self._right_sidebar = RightSidebar()
        h_splitter.addWidget(self._right_sidebar)

        h_splitter.setStretchFactor(0, 0)
        h_splitter.setStretchFactor(1, 1)
        h_splitter.setStretchFactor(2, 0)
        h_splitter.setSizes([200, 900, 210])

        # Vertical splitter: content | jobs panel
        v_splitter = QSplitter(Qt.Orientation.Vertical)
        v_splitter.addWidget(h_splitter)

        self._jobs_panel = JobsPanel(self._job_queue)
        self._jobs_panel.setMinimumHeight(80)
        self._jobs_panel.setMaximumHeight(220)
        v_splitter.addWidget(self._jobs_panel)
        v_splitter.setSizes([700, 120])
        v_splitter.setStretchFactor(0, 1)
        v_splitter.setStretchFactor(1, 0)

        main_layout.addWidget(v_splitter)

        # Status bar
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._lbl_page_info = QLabel()
        self._status_bar.addPermanentWidget(self._lbl_page_info)

    def _build_menu(self) -> None:
        mb = self.menuBar()

        # File menu
        file_menu = mb.addMenu("&File")
        act_open = file_menu.addAction("&Open…")
        act_open.setShortcut(QKeySequence.StandardKey.Open)
        act_open.triggered.connect(self._browse_open)

        self._act_save = file_menu.addAction("&Save")
        self._act_save.setShortcut(QKeySequence.StandardKey.Save)
        self._act_save.triggered.connect(self._save)
        self._act_save.setEnabled(False)

        file_menu.addSeparator()

        act_close = file_menu.addAction("Close Tab")
        act_close.setShortcut(QKeySequence("Ctrl+W"))
        act_close.triggered.connect(self._close_current_tab)

        file_menu.addSeparator()

        act_settings = file_menu.addAction("&Settings…")
        act_settings.triggered.connect(self._open_settings)

        file_menu.addSeparator()

        act_quit = file_menu.addAction("&Quit")
        act_quit.setShortcut(QKeySequence.StandardKey.Quit)
        act_quit.triggered.connect(self.close)

        # Edit menu
        edit_menu = mb.addMenu("&Edit")
        self._act_undo = edit_menu.addAction("&Undo")
        self._act_undo.setShortcut(QKeySequence.StandardKey.Undo)
        self._act_undo.triggered.connect(self._undo)
        self._act_undo.setEnabled(False)

        self._act_redo = edit_menu.addAction("&Redo")
        self._act_redo.setShortcut(QKeySequence.StandardKey.Redo)
        self._act_redo.triggered.connect(self._redo)
        self._act_redo.setEnabled(False)

        # Tools menu
        tools_menu = mb.addMenu("&Tools")

        organize_menu = tools_menu.addMenu("Organize")
        act_merge = organize_menu.addAction("Merge PDFs…")
        act_merge.setShortcut(QKeySequence("Ctrl+M"))
        act_merge.triggered.connect(lambda: self._on_tool_requested("merge_pdfs"))

        act_split = organize_menu.addAction("Split PDF…")
        act_split.triggered.connect(lambda: self._on_tool_requested("split_pdf"))

        act_rotate = organize_menu.addAction("Rotate Pages…")
        act_rotate.triggered.connect(lambda: self._on_tool_requested("rotate_pages"))

        act_delete = organize_menu.addAction("Delete Pages…")
        act_delete.triggered.connect(lambda: self._on_tool_requested("delete_pages"))

        act_extract = organize_menu.addAction("Extract Pages…")
        act_extract.triggered.connect(lambda: self._on_tool_requested("extract_pages"))

        organize_menu.addSeparator()

        act_reverse = organize_menu.addAction("Reverse Pages")
        act_reverse.triggered.connect(lambda: self._on_tool_requested("reverse_pages"))

        act_blank = organize_menu.addAction("Add Blank Page…")
        act_blank.triggered.connect(lambda: self._on_tool_requested("add_blank_page"))

        act_remove_blank = organize_menu.addAction("Remove Blank Pages")
        act_remove_blank.triggered.connect(lambda: self._on_tool_requested("remove_blank_pages"))

        act_nup = organize_menu.addAction("N-Up PDF…")
        act_nup.triggered.connect(lambda: self._on_tool_requested("nup_pdf"))

        organize_menu.addSeparator()

        act_organizer = organize_menu.addAction("Page Organizer")
        act_organizer.setShortcut(QKeySequence("Ctrl+Shift+O"))
        act_organizer.triggered.connect(self._toggle_organizer)

        act_metadata = organize_menu.addAction("Edit Metadata…")
        act_metadata.triggered.connect(lambda: self._on_tool_requested("edit_metadata"))

        act_bookmarks = organize_menu.addAction("Edit Bookmarks…")
        act_bookmarks.triggered.connect(lambda: self._on_tool_requested("edit_bookmarks"))

        # Edit submenu (M3)
        edit_menu = tools_menu.addMenu("Edit")
        for label, tool_id in [
            ("Watermark…",           "watermark"),
            ("Page Numbers…",        "add_page_numbers"),
            ("Bates Numbers…",       "bates_number"),
            ("Header / Footer…",     "header_footer"),
            ("Crop Pages…",          "crop_pdf"),
            ("Redact Content…",      "redact"),
            ("Flatten PDF…",         "flatten_pdf"),
            ("Remove Annotations…",  "remove_annotations"),
            ("Sign PDF…",            "sign_pdf"),
        ]:
            act = edit_menu.addAction(label)
            act.triggered.connect(
                (lambda tid: lambda: self._on_tool_requested(tid))(tool_id)
            )

        # Convert submenu (M3)
        convert_menu = tools_menu.addMenu("Convert")
        for label, tool_id in [
            ("Images → PDF…",          "image_to_pdf"),
            ("PDF → Images…",          "pdf_to_image"),
            ("PDF → Text…",            "pdf_to_text"),
            ("OCR (Make Searchable)…", "ocr_pdf"),
            ("Office → PDF…",          "office_to_pdf"),
            ("PDF → Excel/CSV…",       "pdf_to_excel"),
        ]:
            act = convert_menu.addAction(label)
            act.triggered.connect(
                (lambda tid: lambda: self._on_tool_requested(tid))(tool_id)
            )

        # Secure submenu (M3)
        secure_menu = tools_menu.addMenu("Secure")
        for label, tool_id in [
            ("Encrypt PDF…",   "encrypt_pdf"),
            ("Decrypt PDF…",   "decrypt_pdf"),
            ("Compress PDF…",  "compress_pdf"),
            ("Linearize…",     "linearize_pdf"),
            ("Sanitize PDF…",  "sanitize_pdf"),
        ]:
            act = secure_menu.addAction(label)
            act.triggered.connect(
                (lambda tid: lambda: self._on_tool_requested(tid))(tool_id)
            )

        tools_menu.addSeparator()
        act_workflow = tools_menu.addAction("Workflow Editor…")
        act_workflow.setShortcut(QKeySequence("Ctrl+W"))
        act_workflow.triggered.connect(self._open_workflow_editor)

        tools_menu.addSeparator()
        act_batch = tools_menu.addAction("Batch Processing…")
        act_batch.setShortcut(QKeySequence("Ctrl+B"))
        act_batch.triggered.connect(self._run_batch)

        # View menu
        view_menu = mb.addMenu("&View")
        act_zoom_in = view_menu.addAction("Zoom In")
        act_zoom_in.setShortcut(QKeySequence.StandardKey.ZoomIn)
        act_zoom_in.triggered.connect(self._zoom_in)

        act_zoom_out = view_menu.addAction("Zoom Out")
        act_zoom_out.setShortcut(QKeySequence.StandardKey.ZoomOut)
        act_zoom_out.triggered.connect(self._zoom_out)

        act_fit_w = view_menu.addAction("Fit Width")
        act_fit_w.setShortcut(QKeySequence("Ctrl+Shift+W"))
        act_fit_w.triggered.connect(self._fit_width)

        act_fit_p = view_menu.addAction("Fit Page")
        act_fit_p.setShortcut(QKeySequence("Ctrl+Shift+F"))
        act_fit_p.triggered.connect(self._fit_page)

        # Help menu
        help_menu = mb.addMenu("&Help")
        act_about = help_menu.addAction("About PDF'D")
        act_about.triggered.connect(self._show_about)

    def _build_toolbar(self) -> None:
        tb = QToolBar("Main Toolbar")
        tb.setIconSize(QSize(20, 20))
        tb.setMovable(False)
        self.addToolBar(tb)

        act_open = QAction("Open", self)
        act_open.setShortcut(QKeySequence.StandardKey.Open)
        act_open.triggered.connect(self._browse_open)
        tb.addAction(act_open)

        tb.addSeparator()

        # Page navigation
        self._spin_page = QSpinBox()
        self._spin_page.setMinimum(1)
        self._spin_page.setMaximum(1)
        self._spin_page.setEnabled(False)
        self._spin_page.setFixedWidth(60)
        self._spin_page.valueChanged.connect(self._on_page_spinbox)
        tb.addWidget(self._spin_page)
        self._lbl_of = QLabel(" / — ")
        tb.addWidget(self._lbl_of)

        tb.addSeparator()

        # Zoom
        act_zoom_out = QAction("−", self)
        act_zoom_out.triggered.connect(self._zoom_out)
        tb.addAction(act_zoom_out)

        self._zoom_combo = QComboBox()
        self._zoom_combo.addItems(["50%", "75%", "100%", "125%", "150%", "200%"])
        self._zoom_combo.setCurrentText("100%")
        self._zoom_combo.setEditable(True)
        self._zoom_combo.setFixedWidth(72)
        self._zoom_combo.currentTextChanged.connect(self._on_zoom_combo)
        tb.addWidget(self._zoom_combo)

        act_zoom_in = QAction("+", self)
        act_zoom_in.triggered.connect(self._zoom_in)
        tb.addAction(act_zoom_in)

        act_fit_w = QAction("Fit W", self)
        act_fit_w.triggered.connect(self._fit_width)
        tb.addAction(act_fit_w)

        tb.addSeparator()

        self._act_organizer = QAction("Organize", self)
        self._act_organizer.setToolTip("Page Organizer (Ctrl+Shift+O)")
        self._act_organizer.setCheckable(True)
        self._act_organizer.triggered.connect(self._toggle_organizer)
        tb.addAction(self._act_organizer)

    def _connect_events(self) -> None:
        from pdf_forge.core.events import events
        events.status_message.connect(self._status_bar.showMessage)

    # ── Document Management ───────────────────────────────────────────────────

    def open_file(self, path: str) -> None:
        path = os.path.normpath(path)
        # If already open, switch to its tab
        for i in range(self._tab_widget.count()):
            tab: DocumentTab = self._tab_widget.widget(i)
            if tab.handle.path == path:
                self._tab_widget.setCurrentIndex(i)
                return

        try:
            handle = self._pdf_service.open(path)
        except Exception as e:
            QMessageBox.critical(self, "Open Failed", str(e))
            log.error("Open failed: %s", e)
            return

        tab = DocumentTab(handle)
        tab.viewer.page_changed.connect(self._on_viewer_page_changed)
        tab.viewer.zoom_changed.connect(self._on_viewer_zoom_changed)

        idx = self._tab_widget.addTab(tab, handle.title)
        self._tab_widget.setCurrentIndex(idx)

        self._drop_zone.hide()
        self._tab_widget.show()

        self._left_sidebar.refresh_recent()
        self._right_sidebar.update_document_info(
            path,
            handle.page_count,
            handle.adapter.get_metadata() if handle.adapter else {},
        )
        self._update_page_controls(tab)
        self._status_bar.showMessage(f"Opened: {os.path.basename(path)}")

    def _open_files(self, paths: list[str]) -> None:
        for path in paths:
            self.open_file(path)

    def _browse_open(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Open PDF", "", "PDF Files (*.pdf);;All Files (*)"
        )
        self._open_files(paths)

    def _close_tab(self, index: int) -> None:
        tab: DocumentTab = self._tab_widget.widget(index)
        if tab.viewer.is_dirty():
            # Prompt to save before closing
            reply = QMessageBox.question(
                self, "Unsaved Changes",
                f"Save changes to {self._tab_widget.tabText(index)} before closing?",
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Save
            )
            if reply == QMessageBox.StandardButton.Cancel:
                return
            elif reply == QMessageBox.StandardButton.Save:
                self._save()

        self._pdf_service.close(tab.handle.path)
        self._tab_widget.removeTab(index)
        if self._tab_widget.count() == 0:
            self._tab_widget.hide()
            self._drop_zone.show()
            self._right_sidebar.clear()
            self._update_page_controls(None)
            self._update_undo_redo_buttons()
        else:
            self._update_undo_redo_buttons()

    def _close_current_tab(self) -> None:
        idx = self._tab_widget.currentIndex()
        if idx >= 0:
            self._close_tab(idx)

    def _current_tab(self) -> DocumentTab | None:
        widget = self._tab_widget.currentWidget()
        return widget if isinstance(widget, DocumentTab) else None

    def _current_input_path(self) -> str | None:
        tab = self._current_tab()
        return tab.handle.path if tab else None

    # ── Tool Dispatch ─────────────────────────────────────────────────────────

    @Slot(str)
    def _on_tool_requested(self, tool_id: str) -> None:
        dispatch = {
            # Organize (M1/M2)
            "merge_pdfs":         self._run_merge,
            "split_pdf":          self._run_split,
            "rotate_pages":       self._run_rotate,
            "delete_pages":       self._run_delete_pages,
            "extract_pages":      self._run_extract_pages,
            "reverse_pages":      self._run_reverse_pages,
            "add_blank_page":     self._run_add_blank_page,
            "remove_blank_pages": self._run_remove_blank_pages,
            "nup_pdf":            self._run_nup,
            "edit_metadata":      self._run_edit_metadata,
            "edit_bookmarks":     self._run_edit_bookmarks,
            # Edit (M3)
            "watermark":            self._run_watermark,
            "add_page_numbers":     self._run_page_numbers,
            "bates_number":         self._run_bates,
            "header_footer":        self._run_header_footer,
            "crop_pdf":             self._run_crop,
            "redact":               self._run_redact,
            "edit_text":            self._run_edit_text,
            "flatten_pdf":          self._run_flatten,
            "remove_annotations":   self._run_remove_annotations,
            # Convert (M3)
            "image_to_pdf":  self._run_image_to_pdf,
            "pdf_to_image":  self._run_pdf_to_image,
            "pdf_to_text":   self._run_pdf_to_text,
            "ocr_pdf":       self._run_ocr,
            # Secure (M3)
            "compress_pdf": self._run_compress,
            "encrypt_pdf":  self._run_encrypt,
            "decrypt_pdf":  self._run_decrypt,
            # M4 — Edit
            "sign_pdf":     self._run_sign,
            # M4 — Convert
            "office_to_pdf": self._run_office_to_pdf,
            "pdf_to_excel":  self._run_pdf_to_excel,
            # M4 — Organize/Secure
            "linearize_pdf": self._run_linearize,
            "sanitize_pdf":  self._run_sanitize,
            "repair_pdf":    self._run_repair,
        }
        fn = dispatch.get(tool_id)
        if fn:
            fn()
        else:
            self._status_bar.showMessage(f"Tool '{tool_id}' not yet implemented.")

    def _run_merge(self) -> None:
        paths = [h.path for h in self._pdf_service.open_documents()]
        dlg = MergeDialog(initial_paths=paths, parent=self)
        if dlg.exec() and dlg.result_params:
            tool = registry.get("merge_pdfs")
            job = tool.create_job(dlg.result_params)
            self._job_queue.submit(job)
            self._status_bar.showMessage(f"Merge job submitted [{job.job_id}]")

    def _run_split(self) -> None:
        input_path = self._current_input_path() or ""
        dlg = SplitDialog(input_path=input_path, parent=self)
        if dlg.exec() and dlg.result_params:
            tool = registry.get("split_pdf")
            job = tool.create_job(dlg.result_params)
            self._job_queue.submit(job)
            self._status_bar.showMessage(f"Split job submitted [{job.job_id}]")

    def _apply_inplace_edit(self, tool_id: str, params: dict, description: str) -> bool:
        """Apply an edit to the open document and record it for undo/redo."""
        tab = self._current_tab()
        doc = self._viewer.current_doc() if tab else None
        if not tab or not doc:
            return False

        before_bytes = doc.tobytes()
        modified = registry.get(tool_id).apply_to_doc(doc, params)
        assert modified is doc, (
            f"{tool_id}.apply_to_doc() returned a different document object; "
            "in-place edits must mutate the open document."
        )
        from pdf_forge.ui.undo_stack import SnapshotCommand
        tab._undo_stack.push(SnapshotCommand(description, before_bytes), before_bytes)
        self._viewer.reload_from_memory()
        self._mark_dirty()
        self._update_undo_redo_buttons()
        self._status_bar.showMessage(description)
        return True

    def _run_rotate(self) -> None:
        doc = self._viewer.current_doc()
        if doc:
            # In-place editing mode
            self._run_rotate_inplace(doc)
            return

        # Legacy: file-based mode (no doc open)
        input_path = self._current_input_path()
        if not input_path:
            QMessageBox.information(self, "Rotate Pages", "Open a PDF first.")
            return
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QComboBox, QDialogButtonBox, QFormLayout
        dlg = QDialog(self)
        dlg.setWindowTitle("Rotate Pages")
        layout = QVBoxLayout(dlg)
        form = QFormLayout()
        combo_deg = QComboBox()
        combo_deg.addItems(["90° clockwise", "180°", "90° counter-clockwise"])
        form.addRow("Rotation:", combo_deg)
        layout.addLayout(form)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        layout.addWidget(btns)

        if not dlg.exec():
            return

        deg_map = {"90° clockwise": 90, "180°": 180, "90° counter-clockwise": 270}
        degrees = deg_map[combo_deg.currentText()]

        out_path, _ = QFileDialog.getSaveFileName(
            self, "Save Rotated PDF",
            self._suggest_output(input_path, "_rotated"),
            "PDF Files (*.pdf)"
        )
        if not out_path:
            return

        tool = registry.get("rotate_pages")
        job = tool.create_job({
            "input_path": input_path,
            "output_path": out_path,
            "page_indices": [],
            "degrees": degrees,
        })
        self._job_queue.submit(job)

    def _run_rotate_inplace(self, doc) -> None:
        """Rotate pages in the open document (in-place mode)."""
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QComboBox, QDialogButtonBox, QFormLayout
        dlg = QDialog(self)
        dlg.setWindowTitle("Rotate Pages")
        layout = QVBoxLayout(dlg)
        form = QFormLayout()
        combo_deg = QComboBox()
        combo_deg.addItems(["90° clockwise", "180°", "90° counter-clockwise"])
        form.addRow("Rotation:", combo_deg)
        layout.addLayout(form)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        layout.addWidget(btns)

        if not dlg.exec():
            return

        deg_map = {"90° clockwise": 90, "180°": 180, "90° counter-clockwise": 270}
        degrees = deg_map[combo_deg.currentText()]

        self._apply_inplace_edit(
            "rotate_pages", {"page_indices": [], "degrees": degrees},
            f"Rotate {degrees} degrees",
        )
        return


    def _run_delete_pages(self) -> None:
        input_path = self._current_input_path()
        if not input_path:
            QMessageBox.information(self, "Delete Pages", "Open a PDF first.")
            return
        tab = self._current_tab()
        if not tab:
            return
        current = tab.viewer.current_page
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QDialogButtonBox, QLineEdit, QLabel, QFormLayout
        dlg = QDialog(self)
        dlg.setWindowTitle("Delete Pages")
        layout = QVBoxLayout(dlg)
        form = QFormLayout()
        edit = QLineEdit(str(current + 1))
        edit.setPlaceholderText("e.g. 1,3,5-7")
        form.addRow("Pages to delete:", edit)
        layout.addLayout(form)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        layout.addWidget(btns)
        if not dlg.exec():
            return

        indices = self._parse_page_spec(edit.text(), tab.handle.page_count)
        if indices is None:
            QMessageBox.warning(self, "Delete Pages", "Invalid page specification.")
            return

        if self._apply_inplace_edit("delete_pages", {"page_indices": indices}, "Delete Pages"):
            return

        out_path, _ = QFileDialog.getSaveFileName(
            self, "Save PDF",
            self._suggest_output(input_path, "_deleted"),
            "PDF Files (*.pdf)"
        )
        if not out_path:
            return

        tool = registry.get("delete_pages")
        job = tool.create_job({
            "input_path": input_path,
            "output_path": out_path,
            "page_indices": indices,
        })
        self._job_queue.submit(job)

    def _run_extract_pages(self) -> None:
        input_path = self._current_input_path()
        if not input_path:
            QMessageBox.information(self, "Extract Pages", "Open a PDF first.")
            return
        tab = self._current_tab()
        if not tab:
            return
        current = tab.viewer.current_page
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QDialogButtonBox, QLineEdit, QFormLayout
        dlg = QDialog(self)
        dlg.setWindowTitle("Extract Pages")
        layout = QVBoxLayout(dlg)
        form = QFormLayout()
        edit = QLineEdit(str(current + 1))
        edit.setPlaceholderText("e.g. 1-3,5,7-9")
        form.addRow("Pages to extract:", edit)
        layout.addLayout(form)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        layout.addWidget(btns)
        if not dlg.exec():
            return

        indices = self._parse_page_spec(edit.text(), tab.handle.page_count)
        if indices is None:
            QMessageBox.warning(self, "Extract Pages", "Invalid page specification.")
            return

        if self._apply_inplace_edit("extract_pages", {"page_indices": indices}, "Extract Pages"):
            return

        out_path, _ = QFileDialog.getSaveFileName(
            self, "Save Extracted Pages",
            self._suggest_output(input_path, "_extracted"),
            "PDF Files (*.pdf)"
        )
        if not out_path:
            return

        tool = registry.get("extract_pages")
        job = tool.create_job({
            "input_path": input_path,
            "output_path": out_path,
            "page_indices": indices,
        })
        self._job_queue.submit(job)

    # ── M2 Tool Handlers ──────────────────────────────────────────────────────

    def _run_reverse_pages(self) -> None:
        input_path = self._current_input_path()
        if not input_path:
            QMessageBox.information(self, "Reverse Pages", "Open a PDF first.")
            return
        if self._apply_inplace_edit("reverse_pages", {}, "Reverse Pages"):
            return
        out_path, _ = QFileDialog.getSaveFileName(
            self, "Save Reversed PDF",
            self._suggest_output(input_path, "_reversed"), "PDF Files (*.pdf)"
        )
        if not out_path:
            return
        tool = registry.get("reverse_pages")
        self._job_queue.submit(tool.create_job({
            "input_path": input_path, "output_path": out_path
        }))

    def _run_add_blank_page(self) -> None:
        input_path = self._current_input_path()
        if not input_path:
            QMessageBox.information(self, "Add Blank Page", "Open a PDF first.")
            return
        tab = self._current_tab()
        current = tab.viewer.current_page if tab else 0

        from PySide6.QtWidgets import QDialog, QVBoxLayout, QDialogButtonBox, QSpinBox, QFormLayout
        dlg = QDialog(self)
        dlg.setWindowTitle("Add Blank Page")
        layout = QVBoxLayout(dlg)
        form = QFormLayout()
        spin = QSpinBox()
        spin.setRange(1, (tab.handle.page_count + 1) if tab else 9999)
        spin.setValue(current + 2)
        form.addRow("Insert at position:", spin)
        layout.addLayout(form)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        layout.addWidget(btns)
        if not dlg.exec():
            return

        if self._apply_inplace_edit(
            "add_blank_page", {"position": spin.value() - 1}, "Add Blank Page"
        ):
            return

        out_path, _ = QFileDialog.getSaveFileName(
            self, "Save PDF",
            self._suggest_output(input_path, "_blank"), "PDF Files (*.pdf)"
        )
        if not out_path:
            return
        tool = registry.get("add_blank_page")
        self._job_queue.submit(tool.create_job({
            "input_path": input_path,
            "output_path": out_path,
            "position": spin.value() - 1,
        }))

    def _run_remove_blank_pages(self) -> None:
        input_path = self._current_input_path()
        if not input_path:
            QMessageBox.information(self, "Remove Blank Pages", "Open a PDF first.")
            return
        if self._apply_inplace_edit("remove_blank_pages", {}, "Remove Blank Pages"):
            return
        out_path, _ = QFileDialog.getSaveFileName(
            self, "Save PDF",
            self._suggest_output(input_path, "_cleaned"), "PDF Files (*.pdf)"
        )
        if not out_path:
            return
        tool = registry.get("remove_blank_pages")
        self._job_queue.submit(tool.create_job({
            "input_path": input_path, "output_path": out_path
        }))

    def _run_nup(self) -> None:
        input_path = self._current_input_path() or ""
        dlg = NUpDialog(input_path=input_path, parent=self)
        if dlg.exec() and dlg.result_params:
            tool = registry.get("nup_pdf")
            self._job_queue.submit(tool.create_job(dlg.result_params))

    def _run_edit_metadata(self) -> None:
        input_path = self._current_input_path()
        if not input_path:
            QMessageBox.information(self, "Edit Metadata", "Open a PDF first.")
            return
        dlg = MetadataDialog(input_path, parent=self)
        if dlg.exec() and dlg.result_params:
            tool = registry.get("edit_metadata")
            self._job_queue.submit(tool.create_job(dlg.result_params))

    def _run_edit_bookmarks(self) -> None:
        input_path = self._current_input_path()
        if not input_path:
            QMessageBox.information(self, "Edit Bookmarks", "Open a PDF first.")
            return
        tab = self._current_tab()
        page_count = tab.handle.page_count if tab else 1
        dlg = BookmarksDialog(input_path, page_count, parent=self)
        if dlg.exec() and dlg.result_params:
            tool = registry.get("edit_bookmarks")
            self._job_queue.submit(tool.create_job(dlg.result_params))

    def _open_workflow_editor(self) -> None:
        if not hasattr(self, "_workflow_window") or self._workflow_window is None:
            self._workflow_window = WorkflowWindow(parent=self)
        self._workflow_window.show()
        self._workflow_window.raise_()
        self._workflow_window.activateWindow()

    def _run_batch(self) -> None:
        dlg = BatchDialog(parent=self)
        if not dlg.exec() or not dlg.result_jobs:
            return
        for tool_id, params in dlg.result_jobs:
            tool = registry.get(tool_id)
            if tool:
                self._job_queue.submit(tool.create_job(params))
        self._status_bar.showMessage(
            f"Batch: {len(dlg.result_jobs)} job(s) submitted"
        )

    def _toggle_organizer(self) -> None:
        tab = self._current_tab()
        if not tab:
            QMessageBox.information(self, "Page Organizer", "Open a PDF first.")
            if hasattr(self, "_act_organizer"):
                self._act_organizer.setChecked(False)
            return
        if tab.is_organizer_mode():
            tab._exit_organizer()
            if hasattr(self, "_act_organizer"):
                self._act_organizer.setChecked(False)
            self._status_bar.showMessage("Viewer mode")
        else:
            tab.enter_organizer()
            # Wire organizer actions to job submissions
            tab.organizer_apply.connect(
                lambda order, t=tab: self._organizer_apply(t, order)
            )
            tab.organizer_delete.connect(
                lambda indices, t=tab: self._organizer_delete(t, indices)
            )
            tab.organizer_rotate.connect(
                lambda indices, deg, t=tab: self._organizer_rotate(t, indices, deg)
            )
            tab.organizer_extract.connect(
                lambda indices, t=tab: self._organizer_extract(t, indices)
            )
            if hasattr(self, "_act_organizer"):
                self._act_organizer.setChecked(True)
            self._status_bar.showMessage("Page Organizer — drag pages to reorder")

    def _organizer_apply(self, tab: "DocumentTab", order: list[int]) -> None:
        if tab is self._current_tab() and self._apply_inplace_edit(
            "reorder_pages", {"page_order": order}, "Reorder Pages"
        ):
            return
        out_path, _ = QFileDialog.getSaveFileName(
            self, "Save Reordered PDF",
            self._suggest_output(tab.handle.path, "_reordered"),
            "PDF Files (*.pdf)"
        )
        if not out_path:
            return
        tool = registry.get("reorder_pages")
        self._job_queue.submit(tool.create_job({
            "input_path": tab.handle.path,
            "output_path": out_path,
            "page_order": order,
        }))

    def _organizer_delete(self, tab: "DocumentTab", indices: list[int]) -> None:
        out_path, _ = QFileDialog.getSaveFileName(
            self, "Save PDF",
            self._suggest_output(tab.handle.path, "_edited"),
            "PDF Files (*.pdf)"
        )
        if not out_path:
            return
        tool = registry.get("delete_pages")
        self._job_queue.submit(tool.create_job({
            "input_path": tab.handle.path,
            "output_path": out_path,
            "page_indices": indices,
        }))

    def _organizer_rotate(self, tab: "DocumentTab", indices: list[int], degrees: int) -> None:
        out_path, _ = QFileDialog.getSaveFileName(
            self, "Save Rotated PDF",
            self._suggest_output(tab.handle.path, "_rotated"),
            "PDF Files (*.pdf)"
        )
        if not out_path:
            return
        tool = registry.get("rotate_pages")
        self._job_queue.submit(tool.create_job({
            "input_path": tab.handle.path,
            "output_path": out_path,
            "page_indices": indices,
            "degrees": degrees,
        }))

    def _organizer_extract(self, tab: "DocumentTab", indices: list[int]) -> None:
        out_path, _ = QFileDialog.getSaveFileName(
            self, "Save Extracted Pages",
            self._suggest_output(tab.handle.path, "_extracted"),
            "PDF Files (*.pdf)"
        )
        if not out_path:
            return
        tool = registry.get("extract_pages")
        self._job_queue.submit(tool.create_job({
            "input_path": tab.handle.path,
            "output_path": out_path,
            "page_indices": indices,
        }))

    # ── Viewer Controls ───────────────────────────────────────────────────────

    def _zoom_in(self) -> None:
        tab = self._current_tab()
        if tab:
            tab.viewer.zoom_in()

    def _zoom_out(self) -> None:
        tab = self._current_tab()
        if tab:
            tab.viewer.zoom_out()

    def _fit_width(self) -> None:
        tab = self._current_tab()
        if tab:
            tab.viewer.zoom_fit_width()

    def _fit_page(self) -> None:
        tab = self._current_tab()
        if tab:
            tab.viewer.zoom_fit_page()

    def _on_page_spinbox(self, value: int) -> None:
        tab = self._current_tab()
        if tab:
            tab.viewer.go_to_page(value - 1)

    def _on_zoom_combo(self, text: str) -> None:
        try:
            pct = float(text.rstrip("%"))
            tab = self._current_tab()
            if tab:
                tab.viewer.set_zoom(pct / 100.0)
        except ValueError:
            pass

    @Slot(int)
    def _on_viewer_page_changed(self, page_num: int) -> None:
        tab = self._current_tab()
        if not tab:
            return
        self._spin_page.blockSignals(True)
        self._spin_page.setValue(page_num + 1)
        self._spin_page.blockSignals(False)
        self._lbl_page_info.setText(
            f"Page {page_num + 1} / {tab.handle.page_count}"
        )
        if tab.handle.adapter:
            rect = tab.handle.adapter.get_page_rect(page_num)
            self._right_sidebar.update_page_info(
                page_num, tab.handle.page_count,
                rect.width, rect.height, tab.viewer.zoom
            )

    @Slot(float)
    def _on_viewer_zoom_changed(self, zoom: float) -> None:
        pct = f"{zoom * 100:.0f}%"
        self._zoom_combo.blockSignals(True)
        self._zoom_combo.setCurrentText(pct)
        self._zoom_combo.blockSignals(False)

    @Slot(int)
    def _on_tab_changed(self, index: int) -> None:
        tab = self._current_tab()
        if not tab:
            return
        self._update_page_controls(tab)
        self._update_undo_redo_buttons()
        self._right_sidebar.update_document_info(
            tab.handle.path,
            tab.handle.page_count,
            tab.handle.adapter.get_metadata() if tab.handle.adapter else {},
        )
        # Update status bar with current tab info
        status = f"Tab: {tab.handle.title}"
        if tab.viewer.is_dirty():
            status += " (modified)"
        self._status_bar.showMessage(status)

    def _update_page_controls(self, tab: DocumentTab | None) -> None:
        if tab and tab.handle.page_count > 0:
            self._spin_page.setEnabled(True)
            self._spin_page.setMaximum(tab.handle.page_count)
            self._spin_page.setValue(tab.viewer.current_page + 1)
            self._lbl_of.setText(f" / {tab.handle.page_count} ")
        else:
            self._spin_page.setEnabled(False)
            self._spin_page.setMaximum(1)
            self._spin_page.setValue(1)
            self._lbl_of.setText(" / — ")

    # ── Drag and Drop ─────────────────────────────────────────────────────────

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            pdfs = [
                u.toLocalFile()
                for u in event.mimeData().urls()
                if u.toLocalFile().lower().endswith(".pdf")
            ]
            if pdfs:
                event.acceptProposedAction()
                return
        event.ignore()

    def dropEvent(self, event) -> None:
        pdfs = [
            u.toLocalFile()
            for u in event.mimeData().urls()
            if u.toLocalFile().lower().endswith(".pdf")
        ]
        self._open_files(pdfs)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _suggest_output(self, input_path: str, suffix: str) -> str:
        base, ext = os.path.splitext(input_path)
        return f"{base}{suffix}{ext}"

    def _parse_page_spec(
        self, text: str, total: int
    ) -> list[int] | None:
        """Parse '1,3,5-7' into 0-indexed page list."""
        indices = set()
        for part in text.split(","):
            part = part.strip()
            if not part:
                continue
            if "-" in part:
                parts = part.split("-", 1)
                try:
                    start = int(parts[0].strip())
                    end = int(parts[1].strip())
                    for n in range(start, end + 1):
                        if 1 <= n <= total:
                            indices.add(n - 1)
                except ValueError:
                    return None
            else:
                try:
                    n = int(part)
                    if 1 <= n <= total:
                        indices.add(n - 1)
                except ValueError:
                    return None
        return sorted(indices) if indices else None

    # ── M3 Edit Tool Handlers ─────────────────────────────────────────────────

    def _require_open(self, title: str) -> str | None:
        path = self._current_input_path()
        if not path:
            QMessageBox.information(self, title, "Open a PDF first.")
        return path

    def _save_as(self, title: str, input_path: str, suffix: str) -> str | None:
        out, _ = QFileDialog.getSaveFileName(
            self, title,
            self._suggest_output(input_path, suffix),
            "PDF Files (*.pdf)"
        )
        return out or None

    def _run_watermark(self) -> None:
        input_path = self._require_open("Watermark")
        if not input_path:
            return
        dlg = WatermarkDialog(parent=self)
        if not dlg.exec():
            return
        params = dlg.get_params()
        if self._apply_inplace_edit("watermark", params, "Watermark"):
            return
        out = self._save_as("Save Watermarked PDF", input_path, "_watermarked")
        if not out:
            return
        params.update({"input_path": input_path, "output_path": out})
        tool = registry.get("watermark")
        self._job_queue.submit(tool.create_job(params))

    def _run_page_numbers(self) -> None:
        input_path = self._require_open("Page Numbers")
        if not input_path:
            return
        tab = self._current_tab()
        total = tab.handle.page_count if tab else 1
        dlg = PageNumbersDialog(total_pages=total, parent=self)
        if not dlg.exec():
            return
        params = dlg.get_params()
        if self._apply_inplace_edit("add_page_numbers", params, "Add Page Numbers"):
            return
        out = self._save_as("Save PDF with Page Numbers", input_path, "_numbered")
        if not out:
            return
        params.update({"input_path": input_path, "output_path": out})
        tool = registry.get("add_page_numbers")
        self._job_queue.submit(tool.create_job(params))

    def _run_bates(self) -> None:
        input_path = self._require_open("Bates Numbers")
        if not input_path:
            return
        dlg = BatesDialog(parent=self)
        if not dlg.exec():
            return
        params = dlg.get_params()
        if self._apply_inplace_edit("bates_number", params, "Add Bates Numbers"):
            return
        out = self._save_as("Save Bates-Numbered PDF", input_path, "_bates")
        if not out:
            return
        params.update({"input_path": input_path, "output_path": out})
        tool = registry.get("bates_number")
        self._job_queue.submit(tool.create_job(params))

    def _run_header_footer(self) -> None:
        input_path = self._require_open("Header / Footer")
        if not input_path:
            return
        dlg = HeaderFooterDialog(parent=self)
        if not dlg.exec():
            return
        params = dlg.get_params()
        if self._apply_inplace_edit("header_footer", params, "Add Header / Footer"):
            return
        out = self._save_as("Save PDF with Header/Footer", input_path, "_hf")
        if not out:
            return
        params.update({"input_path": input_path, "output_path": out})
        tool = registry.get("header_footer")
        self._job_queue.submit(tool.create_job(params))

    def _run_crop(self) -> None:
        input_path = self._require_open("Crop Pages")
        if not input_path:
            return
        tab = self._current_tab()
        pw, ph = 595.0, 842.0
        if tab and tab.handle.adapter:
            r = tab.handle.adapter.get_page_rect(tab.viewer.current_page)
            pw, ph = r.width, r.height
        dlg = CropDialog(page_width=pw, page_height=ph, parent=self)
        if not dlg.exec():
            return
        p = dlg.get_params()
        # Build optional pages list from pages_mode
        pages = None
        if p["pages_mode"] != "all" and tab:
            total = tab.handle.page_count
            if p["pages_mode"] == "even":
                pages = [i for i in range(total) if (i + 1) % 2 == 0]
            elif p["pages_mode"] == "odd":
                pages = [i for i in range(total) if (i + 1) % 2 == 1]
        params = {
            "margin_top": p["top"], "margin_bottom": p["bottom"],
            "margin_left": p["left"], "margin_right": p["right"], "pages": pages,
        }
        if self._apply_inplace_edit("crop_pdf", params, "Crop Pages"):
            return
        out = self._save_as("Save Cropped PDF", input_path, "_cropped")
        if not out:
            return
        tool = registry.get("crop_pdf")
        self._job_queue.submit(tool.create_job({
            "input_path":    input_path,
            "output_path":   out,
            "margin_top":    p["top"],
            "margin_bottom": p["bottom"],
            "margin_left":   p["left"],
            "margin_right":  p["right"],
            "pages":         pages,
        }))

    def _run_redact(self) -> None:
        input_path = self._require_open("Redact")
        if not input_path:
            return
        dlg = RedactDialog(parent=self)
        if not dlg.exec():
            return
        p = dlg.get_params()
        params = {
            "search_terms": [t.strip() for t in p["search_term"].splitlines() if t.strip()],
            "whole_word": p["whole_word"], "case_sensitive": p["case_sensitive"],
        }
        if self._apply_inplace_edit("redact", params, "Redact"):
            return
        out = self._save_as("Save Redacted PDF", input_path, "_redacted")
        if not out:
            return
        tool = registry.get("redact")
        self._job_queue.submit(tool.create_job({
            "input_path":   input_path,
            "output_path":  out,
            "search_terms": [t.strip() for t in p["search_term"].splitlines() if t.strip()],
            "whole_word":   p["whole_word"],
            "case_sensitive": p["case_sensitive"],
        }))

    def _run_edit_text(self) -> None:
        input_path = self._require_open("Edit Text")
        if not input_path:
            return
        dlg = EditTextDialog(parent=self)
        if not dlg.exec():
            return
        p = dlg.get_params()
        params = {"find_text": p["find_text"], "replace_text": p["replace_text"], "case_sensitive": p["case_sensitive"]}
        if self._apply_inplace_edit("edit_text", params, "Edit Text"):
            return
        out = self._save_as("Save Edited PDF", input_path, "_edited")
        if not out:
            return
        tool = registry.get("edit_text")
        self._job_queue.submit(tool.create_job({
            "input_path":     input_path,
            "output_path":    out,
            "find_text":      p["find_text"],
            "replace_text":   p["replace_text"],
            "case_sensitive": p["case_sensitive"],
        }))

    def _run_flatten(self) -> None:
        input_path = self._require_open("Flatten PDF")
        if not input_path:
            return
        dlg = FlattenDialog(parent=self)
        if not dlg.exec():
            return
        params = dlg.get_params()
        if self._apply_inplace_edit("flatten_pdf", params, "Flatten PDF"):
            return
        out = self._save_as("Save Flattened PDF", input_path, "_flat")
        if not out:
            return
        params.update({"input_path": input_path, "output_path": out})
        tool = registry.get("flatten_pdf")
        self._job_queue.submit(tool.create_job(params))

    def _run_remove_annotations(self) -> None:
        input_path = self._require_open("Remove Annotations")
        if not input_path:
            return
        dlg = RemoveAnnotationsDialog(parent=self)
        if not dlg.exec():
            return
        params = dlg.get_params()
        if self._apply_inplace_edit("remove_annotations", params, "Remove Annotations"):
            return
        out = self._save_as("Save PDF", input_path, "_clean")
        if not out:
            return
        params.update({"input_path": input_path, "output_path": out})
        tool = registry.get("remove_annotations")
        self._job_queue.submit(tool.create_job(params))

    # ── M3 Convert Tool Handlers ──────────────────────────────────────────────

    def _run_image_to_pdf(self) -> None:
        dlg = ImageToPDFDialog(parent=self)
        if not dlg.exec():
            return
        params = dlg.get_params()
        out, _ = QFileDialog.getSaveFileName(
            self, "Save PDF",
            os.path.join(self._settings.default_output_dir, "images.pdf"),
            "PDF Files (*.pdf)"
        )
        if not out:
            return
        params["output_path"] = out
        tool = registry.get("image_to_pdf")
        self._job_queue.submit(tool.create_job(params))

    def _run_pdf_to_image(self) -> None:
        input_path = self._require_open("PDF → Image")
        if not input_path:
            return
        dlg = PDFToImageDialog(
            default_dir=os.path.dirname(input_path),
            parent=self,
        )
        if not dlg.exec():
            return
        params = dlg.get_params()
        params["input_path"] = input_path
        tool = registry.get("pdf_to_image")
        self._job_queue.submit(tool.create_job(params))

    def _run_pdf_to_text(self) -> None:
        input_path = self._require_open("PDF → Text")
        if not input_path:
            return
        out, _ = QFileDialog.getSaveFileName(
            self, "Save Text File",
            self._suggest_output(input_path, "_text").replace(".pdf", ".txt"),
            "Text Files (*.txt);;JSON (*.json);;All Files (*)"
        )
        if not out:
            return
        mode = "plain"
        if out.endswith(".json"):
            from PySide6.QtWidgets import QInputDialog
            choice, ok = QInputDialog.getItem(
                self, "Export mode", "Mode:", ["blocks (JSON)", "words (JSON)"], 0, False
            )
            if ok:
                mode = "blocks" if "blocks" in choice else "words"
        tool = registry.get("pdf_to_text")
        self._job_queue.submit(tool.create_job({
            "input_path": input_path,
            "output_path": out,
            "mode": mode,
        }))

    def _run_ocr(self) -> None:
        input_path = self._require_open("OCR")
        if not input_path:
            return
        dlg = OCRDialog(parent=self)
        if not dlg.exec():
            return
        out = self._save_as("Save Searchable PDF", input_path, "_ocr")
        if not out:
            return
        params = dlg.get_params()
        params.update({
            "input_path":    input_path,
            "output_path":   out,
            "tesseract_cmd": self._settings.tesseract_path,
        })
        tool = registry.get("ocr_pdf")
        self._job_queue.submit(tool.create_job(params))

    # ── M4 Tool Handlers ──────────────────────────────────────────────────────

    def _run_sign(self) -> None:
        input_path = self._require_open("Sign PDF")
        if not input_path:
            return
        tab = self._current_tab()
        total = tab.handle.page_count if tab else 1
        dlg = SignDialog(total_pages=total, parent=self)
        if not dlg.exec():
            return
        out = self._save_as("Save Signed PDF", input_path, "_signed")
        if not out:
            return
        params = dlg.get_params()
        params.update({"input_path": input_path, "output_path": out})
        tool = registry.get("sign_pdf")
        self._job_queue.submit(tool.create_job(params))

    def _run_office_to_pdf(self) -> None:
        dlg = OfficeToPDFDialog(
            libreoffice_path=self._settings.libreoffice_path,
            parent=self,
        )
        if not dlg.exec():
            return
        params = dlg.get_params()
        tool = registry.get("office_to_pdf")
        self._job_queue.submit(tool.create_job(params))

    def _run_pdf_to_excel(self) -> None:
        input_path = self._require_open("PDF → Excel/CSV")
        if not input_path:
            return
        dlg = PDFToExcelDialog(parent=self)
        if not dlg.exec():
            return
        fmt = dlg.get_params()["fmt"]
        ext = ".xlsx" if fmt == "xlsx" else ".csv"
        out, _ = QFileDialog.getSaveFileName(
            self, "Save Table Export",
            self._suggest_output(input_path, "_tables").replace(".pdf", ext),
            f"{'Excel (*.xlsx)' if fmt == 'xlsx' else 'CSV (*.csv)'};;All Files (*)"
        )
        if not out:
            return
        tool = registry.get("pdf_to_excel")
        self._job_queue.submit(tool.create_job({
            "input_path":  input_path,
            "output_path": out,
            "fmt":         fmt,
        }))

    def _run_linearize(self) -> None:
        input_path = self._require_open("Linearize PDF")
        if not input_path:
            return
        out = self._save_as("Save Linearized PDF", input_path, "_web")
        if not out:
            return
        tool = registry.get("linearize_pdf")
        self._job_queue.submit(tool.create_job({
            "input_path": input_path,
            "output_path": out,
        }))

    def _run_sanitize(self) -> None:
        input_path = self._require_open("Sanitize PDF")
        if not input_path:
            return
        dlg = SanitizeDialog(parent=self)
        if not dlg.exec():
            return
        out = self._save_as("Save Sanitized PDF", input_path, "_sanitized")
        if not out:
            return
        params = dlg.get_params()
        params.update({"input_path": input_path, "output_path": out})
        tool = registry.get("sanitize_pdf")
        self._job_queue.submit(tool.create_job(params))

    # ── M3 Secure Tool Handlers ───────────────────────────────────────────────

    def _run_compress(self) -> None:
        input_path = self._require_open("Compress PDF")
        if not input_path:
            return
        dlg = CompressDialog(parent=self)
        if not dlg.exec():
            return
        out = self._save_as("Save Compressed PDF", input_path, "_compressed")
        if not out:
            return
        params = dlg.get_params()
        params.update({"input_path": input_path, "output_path": out})
        tool = registry.get("compress_pdf")
        self._job_queue.submit(tool.create_job(params))

    def _run_encrypt(self) -> None:
        input_path = self._require_open("Encrypt PDF")
        if not input_path:
            return
        dlg = EncryptDialog(parent=self)
        if not dlg.exec():
            return
        out = self._save_as("Save Encrypted PDF", input_path, "_encrypted")
        if not out:
            return
        params = dlg.get_params()
        params.update({"input_path": input_path, "output_path": out})
        tool = registry.get("encrypt_pdf")
        self._job_queue.submit(tool.create_job(params))

    def _run_decrypt(self) -> None:
        input_path = self._require_open("Decrypt PDF")
        if not input_path:
            return
        dlg = DecryptDialog(parent=self)
        if not dlg.exec():
            return
        out = self._save_as("Save Decrypted PDF", input_path, "_decrypted")
        if not out:
            return
        params = dlg.get_params()
        params.update({"input_path": input_path, "output_path": out})
        tool = registry.get("decrypt_pdf")
        self._job_queue.submit(tool.create_job(params))

    def _run_repair(self) -> None:
        input_path = self._require_open("Repair PDF")
        if not input_path:
            return
        if self._apply_inplace_edit("repair_pdf", {}, "Repair PDF"):
            return
        out = self._save_as("Save Repaired PDF", input_path, "_repaired")
        if not out:
            return
        tool = registry.get("repair_pdf")
        self._job_queue.submit(tool.create_job({
            "input_path": input_path,
            "output_path": out,
        }))

    # ── Settings ──────────────────────────────────────────────────────────────

    def _open_settings(self) -> None:
        dlg = SettingsDialog(self._settings, parent=self)
        dlg.exec()

    def _show_about(self) -> None:
        QMessageBox.about(
            self, "About PDF'D",
            f"PDF'D v{__version__}\n\n"
            "A production-grade PDF workstation.\n\n"
            "Built with Python + PySide6 + PyMuPDF + pikepdf."
        )

    # ── Undo/Redo/Save (In-Place Editing) ──────────────────────────────────────

    def _undo(self) -> None:
        """Undo the last operation in current tab."""
        tab = self._current_tab()
        if not tab or not hasattr(tab, '_undo_stack'):
            self._status_bar.showMessage("Nothing to undo")
            return

        doc = self._viewer.current_doc()
        result = tab._undo_stack.undo(doc.tobytes()) if doc else None
        if result:
            cmd, before_state = result
            if doc:
                restored = fitz.open(stream=before_state, filetype="pdf")
                if doc.page_count:
                    doc.delete_pages(0, doc.page_count - 1)
                doc.insert_pdf(restored)
                restored.close()
                self._viewer.set_dirty(True)
                self._viewer.reload_from_memory()
                self._status_bar.showMessage(f"Undone: {cmd.description()}")
                self._update_undo_redo_buttons()
        else:
            self._status_bar.showMessage("Nothing to undo")

    def _redo(self) -> None:
        """Redo the last undone operation in current tab."""
        tab = self._current_tab()
        if not tab or not hasattr(tab, '_undo_stack'):
            self._status_bar.showMessage("Nothing to redo")
            return

        doc = self._viewer.current_doc()
        result = tab._undo_stack.redo(doc.tobytes()) if doc else None
        if result:
            cmd, before_state = result
            if doc:
                restored = fitz.open(stream=before_state, filetype="pdf")
                if doc.page_count:
                    doc.delete_pages(0, doc.page_count - 1)
                doc.insert_pdf(restored)
                restored.close()
                self._viewer.set_dirty(True)
                self._viewer.reload_from_memory()
                self._status_bar.showMessage(f"Redone: {cmd.description()}")
                self._update_undo_redo_buttons()
        else:
            self._status_bar.showMessage("Nothing to redo")

    def _save(self) -> None:
        """Save the current document (in-place or save-as on first save)."""
        doc = self._viewer.current_doc()
        if not doc:
            self._status_bar.showMessage("No PDF open to save")
            return

        if not self._current_file_path:
            # First save: show save-as dialog, defaulting to the source path
            default_path = self._viewer.source_file_path() or ""
            out, _ = QFileDialog.getSaveFileName(
                self, "Save PDF", default_path, "PDF Files (*.pdf)"
            )
            if not out:
                return
            self._current_file_path = out

        try:
            # fitz keeps the file it was opened from locked/open, so writing
            # a full rebuilt copy back to that exact path fails (and on
            # Windows, even a temp-file-and-replace swap fails because the
            # OS won't replace a file that's still held open). Saving back
            # to the original path must go through an incremental save;
            # saving to any other (save-as) path can use a normal full save.
            same_as_source = doc.name and os.path.normcase(
                os.path.normpath(self._current_file_path)
            ) == os.path.normcase(os.path.normpath(doc.name))

            if same_as_source:
                doc.saveIncr()
            else:
                doc.save(self._current_file_path, deflate=True, garbage=4, clean=True)

            self._viewer.set_dirty(False)
            self._mark_clean()
            self._status_bar.showMessage(f"Saved: {self._current_file_path}")
        except Exception as e:
            log.error("Save failed: %s", e)
            self._status_bar.showMessage(f"Save failed: {e}")

    def _mark_dirty(self) -> None:
        """Mark document as modified and update UI."""
        self._viewer.set_dirty(True)
        self._act_save.setEnabled(self._viewer.current_doc() is not None)
        # Update window title to show unsaved indicator
        title = APP_NAME
        if self._current_file_path:
            title += f" - {os.path.basename(self._current_file_path)}"
        if self._viewer.is_dirty():
            title += " *"
        self.setWindowTitle(title)

    def _mark_clean(self) -> None:
        """Mark document as clean (no unsaved changes)."""
        self._viewer.set_dirty(False)
        # Update window title to remove unsaved indicator
        title = APP_NAME
        if self._current_file_path:
            title += f" - {os.path.basename(self._current_file_path)}"
        self.setWindowTitle(title)

    def _update_undo_redo_buttons(self) -> None:
        """Enable/disable undo/redo buttons based on stack state."""
        tab = self._current_tab()
        if tab and hasattr(tab, '_undo_stack'):
            self._act_undo.setEnabled(tab._undo_stack.can_undo())
            self._act_redo.setEnabled(tab._undo_stack.can_redo())
        else:
            self._act_undo.setEnabled(False)
            self._act_redo.setEnabled(False)

    @property
    def _viewer(self):
        """Get the current tab's PDF viewer."""
        tab = self._current_tab()
        return tab.viewer if tab else None

    # ── Window Lifecycle ──────────────────────────────────────────────────────

    def _restore_geometry(self) -> None:
        from PySide6.QtCore import QSettings
        qs = QSettings("PDFD", "PDFD")
        geom = qs.value("MainWindow/geometry")
        if geom:
            self.restoreGeometry(geom)

    def closeEvent(self, event: QCloseEvent) -> None:
        # Check for unsaved changes across all tabs
        unsaved_tabs = []
        for i in range(self._tab_widget.count()):
            tab: DocumentTab = self._tab_widget.widget(i)
            if tab.viewer.is_dirty():
                unsaved_tabs.append(self._tab_widget.tabText(i))

        if unsaved_tabs:
            # Prompt user for unsaved changes
            msg = "You have unsaved changes in:\n\n" + "\n".join(f"  • {t}" for t in unsaved_tabs)
            msg += "\n\nDo you want to save before closing?"
            reply = QMessageBox.question(
                self, "Unsaved Changes", msg,
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel
            )
            if reply == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return
            elif reply == QMessageBox.StandardButton.Save:
                # Try to save current document
                if self._viewer:
                    self._save()
                    if self._viewer.is_dirty():
                        # Save failed or user cancelled save-as
                        event.ignore()
                        return

        from PySide6.QtCore import QSettings
        qs = QSettings("PDFD", "PDFD")
        qs.setValue("MainWindow/geometry", self.saveGeometry())
        self._job_queue.shutdown()
        self._pdf_service.close_all()
        super().closeEvent(event)
