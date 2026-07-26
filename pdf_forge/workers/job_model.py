"""Job data model — the unit of background work in PDF Forge."""
from __future__ import annotations
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable


class JobStatus(Enum):
    PENDING = auto()
    RUNNING = auto()
    SUCCESS = auto()
    FAILED = auto()
    CANCELLED = auto()


@dataclass
class JobResult:
    output_paths: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    modified_doc: Any = None  # fitz.Document for in-place edits; None for file-based


class Job:
    """Base class for all background jobs.

    Subclasses implement execute(). The executor calls cancel_flag to check
    for cancellation — it should do so at natural checkpoints.
    """

    def __init__(self, tool_id: str, input_paths: list[str]) -> None:
        self.job_id: str = str(uuid.uuid4())[:8]
        self.tool_id: str = tool_id
        self.input_paths: list[str] = input_paths
        self.status: JobStatus = JobStatus.PENDING
        self.result: JobResult | None = None
        self.error: str = ""

        self._cancelled: bool = False
        self._progress_cb: Callable[[int], None] | None = None
        self._log_cb: Callable[[str], None] | None = None

    @property
    def cancel_flag(self) -> bool:
        return self._cancelled

    def cancel(self) -> None:
        self._cancelled = True

    def set_callbacks(
        self,
        progress: Callable[[int], None],
        log: Callable[[str], None],
    ) -> None:
        self._progress_cb = progress
        self._log_cb = log

    def report_progress(self, percent: int) -> None:
        if self._progress_cb:
            self._progress_cb(min(100, max(0, percent)))

    def log(self, message: str) -> None:
        if self._log_cb:
            self._log_cb(message)

    def execute(self) -> JobResult:
        raise NotImplementedError
