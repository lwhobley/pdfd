"""Persistent job history (last N completed jobs)."""
from __future__ import annotations
import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path


MAX_HISTORY = 200


@dataclass
class HistoryEntry:
    job_id: str
    tool_id: str
    status: str          # "success" | "failed" | "cancelled"
    input_paths: list[str] = field(default_factory=list)
    output_paths: list[str] = field(default_factory=list)
    started_at: str = ""
    finished_at: str = ""
    error: str = ""


class JobHistory:
    def __init__(self) -> None:
        base = Path(os.environ.get("APPDATA", Path.home())) / "PDFDADDY"
        base.mkdir(parents=True, exist_ok=True)
        self._path = base / "job_history.json"
        self._entries: list[HistoryEntry] = self._load()

    def _load(self) -> list[HistoryEntry]:
        if not self._path.exists():
            return []
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return [HistoryEntry(**e) for e in data]
        except Exception:
            return []

    def _save(self) -> None:
        try:
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump([asdict(e) for e in self._entries[-MAX_HISTORY:]], f, indent=2)
        except Exception:
            pass

    def record(self, entry: HistoryEntry) -> None:
        self._entries.append(entry)
        self._save()

    def entries(self) -> list[HistoryEntry]:
        return list(reversed(self._entries))

    def clear(self) -> None:
        self._entries.clear()
        self._save()
