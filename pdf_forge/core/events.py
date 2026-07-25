"""App-wide event bus backed by Qt signals.

Usage:
    from pdf_forge.core.events import events
    events.file_opened.connect(my_slot)
    events.file_opened.emit("/path/to/file.pdf")
"""
from PySide6.QtCore import QObject, Signal


class _EventBus(QObject):
    # Document lifecycle
    file_opened = Signal(str)          # path
    file_closed = Signal(str)          # path
    file_saved = Signal(str)           # path
    document_changed = Signal(str)     # path — content modified

    # Job system
    job_submitted = Signal(str)        # job_id
    job_started = Signal(str)          # job_id
    job_progress = Signal(str, int)    # job_id, percent
    job_log = Signal(str, str)         # job_id, message
    job_finished = Signal(str, bool)   # job_id, success
    job_cancelled = Signal(str)        # job_id

    # UI state
    status_message = Signal(str)       # short status bar text
    error_message = Signal(str, str)   # title, detail


events = _EventBus()
