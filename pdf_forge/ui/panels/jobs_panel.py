"""Bottom panel — active jobs, progress bars, logs."""
from __future__ import annotations
import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar,
    QPushButton, QScrollArea, QFrame, QTextEdit, QTabWidget,
)
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QColor, QTextCharFormat, QTextCursor

from pdf_forge.workers.job_model import Job, JobStatus
from pdf_forge.core.events import events

log = logging.getLogger(__name__)


class JobRow(QWidget):
    def __init__(self, job: Job, cancel_fn, parent=None) -> None:
        super().__init__(parent)
        self._job = job
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(8)

        self._lbl_name = QLabel(f"{job.tool_id} [{job.job_id}]")
        self._lbl_name.setMinimumWidth(160)
        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setFixedHeight(8)
        self._lbl_status = QLabel("Pending")
        self._lbl_status.setFixedWidth(70)
        self._btn_cancel = QPushButton("✕")
        self._btn_cancel.setFixedSize(24, 24)
        self._btn_cancel.setToolTip("Cancel job")
        self._btn_cancel.clicked.connect(lambda: cancel_fn(job.job_id))

        layout.addWidget(self._lbl_name)
        layout.addWidget(self._progress, stretch=1)
        layout.addWidget(self._lbl_status)
        layout.addWidget(self._btn_cancel)

    def set_progress(self, pct: int) -> None:
        self._progress.setValue(pct)

    def set_status(self, status: str) -> None:
        self._lbl_status.setText(status)
        if status == "Done":
            self._btn_cancel.setEnabled(False)
            self._progress.setValue(100)
        elif status == "Failed":
            self._lbl_status.setStyleSheet("color: #f38ba8;")
            self._btn_cancel.setEnabled(False)


class JobsPanel(QWidget):
    def __init__(self, job_queue, parent=None) -> None:
        super().__init__(parent)
        self._queue = job_queue
        self._rows: dict[str, JobRow] = {}
        self._setup_ui()
        self._connect_events()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        tabs = QTabWidget()
        tabs.setTabPosition(QTabWidget.TabPosition.South)

        # Jobs tab
        jobs_widget = QWidget()
        jobs_layout = QVBoxLayout(jobs_widget)
        jobs_layout.setContentsMargins(4, 4, 4, 4)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._jobs_container = QWidget()
        self._jobs_inner = QVBoxLayout(self._jobs_container)
        self._jobs_inner.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._jobs_inner.setSpacing(2)
        self._scroll.setWidget(self._jobs_container)
        jobs_layout.addWidget(self._scroll)

        # Log tab
        self._log_view = QTextEdit()
        self._log_view.setReadOnly(True)
        self._log_view.setStyleSheet(
            "background: #181825; color: #a6adc8; font-family: Consolas, monospace; font-size: 12px;"
        )

        tabs.addTab(jobs_widget, "Jobs")
        tabs.addTab(self._log_view, "Logs")
        layout.addWidget(tabs)

    def _connect_events(self) -> None:
        events.job_submitted.connect(self._on_submitted)
        events.job_progress.connect(self._on_progress)
        events.job_log.connect(self._on_log)
        events.job_finished.connect(self._on_finished)

    @Slot(str)
    def _on_submitted(self, job_id: str) -> None:
        job = self._queue.get(job_id)
        if not job:
            return
        row = JobRow(job, self._queue.cancel, parent=self._jobs_container)
        self._rows[job_id] = row
        self._jobs_inner.addWidget(row)

    @Slot(str, int)
    def _on_progress(self, job_id: str, pct: int) -> None:
        row = self._rows.get(job_id)
        if row:
            row.set_progress(pct)
            row.set_status("Running")

    @Slot(str, str)
    def _on_log(self, job_id: str, msg: str) -> None:
        self._log_view.append(f"[{job_id}] {msg}")

    @Slot(str, bool)
    def _on_finished(self, job_id: str, success: bool) -> None:
        row = self._rows.get(job_id)
        if row:
            row.set_status("Done" if success else "Failed")
