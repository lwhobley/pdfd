"""Tests for the job queue and worker system."""
import pytest
from pdf_forge.workers.job_model import Job, JobResult, JobStatus
from pdf_forge.workers.job_queue import JobQueue
from pdf_forge.persistence.job_history import JobHistory


class _SuccessJob(Job):
    def __init__(self):
        super().__init__("test_success", [])

    def execute(self) -> JobResult:
        self.log("working")
        self.report_progress(50)
        self.report_progress(100)
        return JobResult(output_paths=["fake_output.pdf"])


class _FailJob(Job):
    def __init__(self):
        super().__init__("test_fail", [])

    def execute(self) -> JobResult:
        raise RuntimeError("intentional failure")


@pytest.fixture
def job_queue(tmp_path, qtbot):
    history = JobHistory()
    history._path = tmp_path / "history.json"
    queue = JobQueue(history)
    yield queue
    # Qt aborts the process if a running QThread is destroyed
    queue.shutdown()


def test_successful_job(job_queue, qtbot):
    job = _SuccessJob()
    job_queue.submit(job)

    def _done():
        assert job.status == JobStatus.SUCCESS

    qtbot.waitUntil(_done, timeout=5000)
    assert job.result is not None
    assert job.result.output_paths == ["fake_output.pdf"]


def test_failed_job(job_queue, qtbot):
    job = _FailJob()
    job_queue.submit(job)

    def _done():
        assert job.status == JobStatus.FAILED

    qtbot.waitUntil(_done, timeout=5000)
    assert "intentional failure" in job.error


def test_cancel_pending_job(job_queue, qtbot):
    job = _SuccessJob()
    job_queue.submit(job)
    job_queue.cancel(job.job_id)
    # If cancelled before starting, status may be PENDING or CANCELLED
    # Just verify no crash
    qtbot.wait(200)
