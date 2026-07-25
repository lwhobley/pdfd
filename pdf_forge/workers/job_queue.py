"""Job queue — manages submission, execution, and lifecycle of all jobs."""
from __future__ import annotations
import logging
from collections import deque
from datetime import datetime, timezone
from typing import Optional

from PySide6.QtCore import QObject, Signal

from pdf_forge.workers.job_model import Job, JobStatus
from pdf_forge.workers.worker_thread import WorkerThread
from pdf_forge.core.events import events
from pdf_forge.persistence.job_history import JobHistory, HistoryEntry

log = logging.getLogger(__name__)

MAX_CONCURRENT = 2


class JobQueue(QObject):
    """Manages up to MAX_CONCURRENT parallel WorkerThreads."""

    job_submitted = Signal(object)   # Job
    job_started = Signal(object)     # Job
    job_finished = Signal(object)    # Job

    def __init__(self, history: JobHistory, parent=None) -> None:
        super().__init__(parent)
        self._history = history
        self._pending: deque[Job] = deque()
        self._active: dict[str, WorkerThread] = {}
        self._all: dict[str, Job] = {}

    def submit(self, job: Job) -> str:
        self._all[job.job_id] = job
        self._pending.append(job)
        self.job_submitted.emit(job)
        events.job_submitted.emit(job.job_id)
        log.info("Job submitted: %s (%s)", job.job_id, job.tool_id)
        self._maybe_start_next()
        return job.job_id

    def cancel(self, job_id: str) -> None:
        job = self._all.get(job_id)
        if not job:
            return
        job.cancel()
        if job_id in self._active:
            self._active[job_id].requestInterruption()

    def shutdown(self, timeout_ms: int = 5000) -> None:
        """Cancel everything and wait for active threads to finish.

        Must be called before the queue is destroyed — Qt aborts the process
        if a running QThread is destroyed.
        """
        self._pending.clear()
        for job_id, worker in list(self._active.items()):
            job = self._all.get(job_id)
            if job:
                job.cancel()
            worker.requestInterruption()

        for job_id, worker in list(self._active.items()):
            if not worker.wait(timeout_ms):
                log.warning("Job %s did not stop in time; terminating", job_id)
                worker.terminate()
                worker.wait()
        self._active.clear()

    def get(self, job_id: str) -> Optional[Job]:
        return self._all.get(job_id)

    def active_count(self) -> int:
        return len(self._active)

    def _maybe_start_next(self) -> None:
        while self._pending and len(self._active) < MAX_CONCURRENT:
            job = self._pending.popleft()
            self._start(job)

    def _start(self, job: Job) -> None:
        worker = WorkerThread(job, parent=self)
        worker.progress.connect(self._on_progress)
        worker.log_line.connect(self._on_log)
        worker.finished.connect(self._on_finished)
        self._active[job.job_id] = worker
        job._started_at = datetime.now(timezone.utc).isoformat()
        worker.start()
        self.job_started.emit(job)
        events.job_started.emit(job.job_id)
        log.info("Job started: %s", job.job_id)

    def _on_progress(self, job_id: str, pct: int) -> None:
        events.job_progress.emit(job_id, pct)

    def _on_log(self, job_id: str, msg: str) -> None:
        events.job_log.emit(job_id, msg)

    def _on_finished(self, job_id: str, success: bool) -> None:
        worker = self._active.pop(job_id, None)
        if worker:
            worker.deleteLater()

        job = self._all.get(job_id)
        if job:
            finished_at = datetime.now(timezone.utc).isoformat()
            entry = HistoryEntry(
                job_id=job.job_id,
                tool_id=job.tool_id,
                status=job.status.name.lower(),
                input_paths=job.input_paths,
                output_paths=job.result.output_paths if job.result else [],
                started_at=getattr(job, "_started_at", ""),
                finished_at=finished_at,
                error=job.error,
            )
            self._history.record(entry)
            self.job_finished.emit(job)
            events.job_finished.emit(job_id, success)

        self._maybe_start_next()
