"""Recent files list, persisted via QSettings."""
from __future__ import annotations
from PySide6.QtCore import QSettings
import os


MAX_RECENT = 20


class RecentFiles:
    def __init__(self) -> None:
        self._qs = QSettings("PDFDADDY", "PDFDADDY")
        self._key = "RecentFiles/paths"

    def paths(self) -> list[str]:
        raw = self._qs.value(self._key, [])
        if isinstance(raw, str):
            raw = [raw]
        # Filter to only existing files
        return [p for p in raw if os.path.isfile(p)]

    def add(self, path: str) -> None:
        paths = self.paths()
        path = os.path.normpath(path)
        if path in paths:
            paths.remove(path)
        paths.insert(0, path)
        self._qs.setValue(self._key, paths[:MAX_RECENT])

    def remove(self, path: str) -> None:
        paths = self.paths()
        path = os.path.normpath(path)
        if path in paths:
            paths.remove(path)
            self._qs.setValue(self._key, paths)

    def clear(self) -> None:
        self._qs.setValue(self._key, [])
