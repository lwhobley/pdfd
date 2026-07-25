"""PDF document service — owns open document state for the app."""
from __future__ import annotations
import logging
import os
from typing import Optional

from pdf_forge.adapters.pymupdf_adapter import PyMuPDFAdapter
from pdf_forge.core.exceptions import PDFOpenError
from pdf_forge.core.events import events
from pdf_forge.persistence.recent_files import RecentFiles

log = logging.getLogger(__name__)


class DocumentHandle:
    """Represents one open PDF document."""

    def __init__(self, path: str) -> None:
        self.path = path
        self.adapter: PyMuPDFAdapter | None = None
        self.modified: bool = False

    def open(self) -> None:
        try:
            self.adapter = PyMuPDFAdapter(self.path)
        except Exception as e:
            raise PDFOpenError(f"Cannot open {self.path}: {e}") from e

    def close(self) -> None:
        if self.adapter:
            self.adapter.close()
            self.adapter = None

    @property
    def page_count(self) -> int:
        return self.adapter.page_count if self.adapter else 0

    @property
    def title(self) -> str:
        return os.path.basename(self.path)


class PDFService:
    """Manages all open DocumentHandles and coordinates with event bus."""

    def __init__(self, recent_files: RecentFiles) -> None:
        self._recent = recent_files
        self._documents: dict[str, DocumentHandle] = {}  # path → handle

    def open(self, path: str) -> DocumentHandle:
        path = os.path.normpath(path)
        if path in self._documents:
            return self._documents[path]

        handle = DocumentHandle(path)
        handle.open()
        self._documents[path] = handle
        self._recent.add(path)
        events.file_opened.emit(path)
        log.info("Opened: %s (%d pages)", path, handle.page_count)
        return handle

    def close(self, path: str) -> None:
        path = os.path.normpath(path)
        handle = self._documents.pop(path, None)
        if handle:
            handle.close()
            events.file_closed.emit(path)

    def get(self, path: str) -> Optional[DocumentHandle]:
        return self._documents.get(os.path.normpath(path))

    def open_documents(self) -> list[DocumentHandle]:
        return list(self._documents.values())

    def close_all(self) -> None:
        for path in list(self._documents.keys()):
            self.close(path)
