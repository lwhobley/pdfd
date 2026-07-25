"""QThread-based worker that executes a single Job."""
from __future__ import annotations
import logging
from PySide6.QtCore import QThread, Signal

from pdf_forge.workers.job_model import Job, JobResult, JobStatus
from pdf_forge.core.exceptions import JobCancelledError

log = logging.getLogger(__name__)


class WorkerThread(QThread):
    progress = Signal(str, int)    # job_id, percent
    log_line = Signal(str, str)    # job_id, message
    finished = Signal(str, bool)   # job_id, success

    def __init__(self, job: Job, parent=None) -> None:
        super().__init__(parent)
        self._job = job

    @property
    def job(self) -> Job:
        return self._job

    def run(self) -> None:
        job = self._job
        job.status = JobStatus.RUNNING

        def _progress(pct: int) -> None:
            self.progress.emit(job.job_id, pct)

        def _log(msg: str) -> None:
            log.debug("[job:%s] %s", job.job_id, msg)
            self.log_line.emit(job.job_id, msg)

        job.set_callbacks(_progress, _log)
        _log(f"Starting {job.tool_id}")

        try:
            result = job.execute()
            if job.cancel_flag:
                raise JobCancelledError()
            job.result = result
            job.status = JobStatus.SUCCESS
            _log("Done.")
            self.finished.emit(job.job_id, True)
        except JobCancelledError:
            job.status = JobStatus.CANCELLED
            _log("Cancelled.")
            self.finished.emit(job.job_id, False)
        except Exception as exc:
            job.status = JobStatus.FAILED
            job.error = str(exc)
            log.exception("[job:%s] failed: %s", job.job_id, exc)
            _log(f"Error: {exc}")
            self.finished.emit(job.job_id, False)
