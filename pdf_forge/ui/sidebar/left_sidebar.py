"""Left sidebar — tool navigation and recent files."""
from __future__ import annotations
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QFrame, QSizePolicy,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from pdf_forge.persistence.recent_files import RecentFiles
import os


class LeftSidebar(QWidget):
    tool_requested = Signal(str)        # tool_id
    recent_file_clicked = Signal(str)   # path

    _TOOL_SECTIONS = [
        ("Organize", [
            ("merge_pdfs",         "Merge PDFs"),
            ("split_pdf",          "Split PDF"),
            ("rotate_pages",       "Rotate Pages"),
            ("delete_pages",       "Delete Pages"),
            ("extract_pages",      "Extract Pages"),
            ("reverse_pages",      "Reverse Pages"),
            ("add_blank_page",     "Add Blank Page"),
            ("remove_blank_pages", "Remove Blank Pages"),
            ("nup_pdf",            "N-Up PDF"),
            ("edit_metadata",      "Edit Metadata"),
            ("edit_bookmarks",     "Edit Bookmarks"),
        ]),
        ("Edit", [
            ("watermark",            "Watermark"),
            ("add_page_numbers",     "Page Numbers"),
            ("bates_number",         "Bates Numbers"),
            ("header_footer",        "Header / Footer"),
            ("crop_pdf",             "Crop Pages"),
            ("redact",               "Redact Content"),
            ("flatten_pdf",          "Flatten PDF"),
            ("remove_annotations",   "Remove Annotations"),
            ("sign_pdf",             "Sign PDF"),
            ("edit_text",            "Edit Text"),
        ]),
        ("Convert", [
            ("image_to_pdf",  "Image → PDF"),
            ("pdf_to_image",  "PDF → Image"),
            ("pdf_to_text",   "PDF → Text"),
            ("ocr_pdf",       "OCR (Make Searchable)"),
            ("office_to_pdf", "Office → PDF"),
            ("pdf_to_excel",  "PDF → Excel/CSV"),
        ]),
        ("Secure", [
            ("encrypt_pdf",   "Encrypt PDF"),
            ("decrypt_pdf",   "Decrypt PDF"),
            ("compress_pdf",  "Compress PDF"),
            ("linearize_pdf", "Linearize (Web)"),
            ("sanitize_pdf",  "Sanitize PDF"),
        ]),
    ]

    def __init__(self, recent_files: RecentFiles, parent=None) -> None:
        super().__init__(parent)
        self._recent = recent_files
        self.setMinimumWidth(180)
        self.setMaximumWidth(260)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Tools section
        tools_label = QLabel("  TOOLS")
        tools_label.setStyleSheet(
            "color: #6c6f85; font-size: 10px; font-weight: bold;"
            "padding: 10px 0 4px 0; background: transparent;"
        )
        layout.addWidget(tools_label)

        self._tool_list = QListWidget()
        self._tool_list.setStyleSheet(
            "QListWidget { border: none; background: transparent; }"
            "QListWidget::item { padding: 6px 12px; border-radius: 4px; margin: 1px 4px; }"
            "QListWidget::item:selected { background: #313244; }"
            "QListWidget::item:hover { background: #26273a; }"
        )
        self._tool_list.setFrameShape(QFrame.Shape.NoFrame)
        self._tool_list.itemClicked.connect(self._on_tool_clicked)

        for section_name, tools in self._TOOL_SECTIONS:
            header = QListWidgetItem(f"  {section_name}")
            header.setFlags(Qt.ItemFlag.NoItemFlags)
            header.setForeground(Qt.GlobalColor.gray)
            f = QFont()
            f.setPointSize(9)
            f.setBold(True)
            header.setFont(f)
            self._tool_list.addItem(header)
            for tool_id, label in tools:
                item = QListWidgetItem(f"    {label}")
                item.setData(Qt.ItemDataRole.UserRole, tool_id)
                self._tool_list.addItem(item)

        layout.addWidget(self._tool_list, stretch=1)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #313244;")
        layout.addWidget(sep)

        # Recent files section
        recent_label = QLabel("  RECENT FILES")
        recent_label.setStyleSheet(
            "color: #6c6f85; font-size: 10px; font-weight: bold;"
            "padding: 8px 0 4px 0; background: transparent;"
        )
        layout.addWidget(recent_label)

        self._recent_list = QListWidget()
        self._recent_list.setStyleSheet(
            "QListWidget { border: none; background: transparent; }"
            "QListWidget::item { padding: 5px 12px; }"
            "QListWidget::item:hover { background: #26273a; }"
        )
        self._recent_list.setMaximumHeight(180)
        self._recent_list.itemDoubleClicked.connect(self._on_recent_clicked)
        layout.addWidget(self._recent_list)

        self.refresh_recent()

    def refresh_recent(self) -> None:
        self._recent_list.clear()
        for path in self._recent.paths()[:8]:
            item = QListWidgetItem(os.path.basename(path))
            item.setData(Qt.ItemDataRole.UserRole, path)
            item.setToolTip(path)
            self._recent_list.addItem(item)

    def _on_tool_clicked(self, item: QListWidgetItem) -> None:
        tool_id = item.data(Qt.ItemDataRole.UserRole)
        if tool_id:
            self.tool_requested.emit(tool_id)

    def _on_recent_clicked(self, item: QListWidgetItem) -> None:
        path = item.data(Qt.ItemDataRole.UserRole)
        if path:
            self.recent_file_clicked.emit(path)
