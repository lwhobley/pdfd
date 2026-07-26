"""Application settings backed by QSettings (registry on Windows)."""
from __future__ import annotations
from PySide6.QtCore import QSettings


class AppSettings:
    _GROUP_GENERAL = "General"
    _GROUP_VIEWER = "Viewer"
    _GROUP_PATHS = "Paths"

    def __init__(self) -> None:
        self._qs = QSettings("PDFD", "PDFD")

    # ── General ───────────────────────────────────────────────────────────────

    @property
    def theme(self) -> str:
        return self._qs.value(f"{self._GROUP_GENERAL}/theme", "dark")

    @theme.setter
    def theme(self, value: str) -> None:
        self._qs.setValue(f"{self._GROUP_GENERAL}/theme", value)

    @property
    def default_output_dir(self) -> str:
        import os
        return self._qs.value(
            f"{self._GROUP_PATHS}/default_output_dir",
            os.path.expanduser("~/Documents"),
        )

    @default_output_dir.setter
    def default_output_dir(self, path: str) -> None:
        self._qs.setValue(f"{self._GROUP_PATHS}/default_output_dir", path)

    # ── Viewer ────────────────────────────────────────────────────────────────

    @property
    def zoom_default(self) -> float:
        return float(self._qs.value(f"{self._GROUP_VIEWER}/zoom_default", 1.0))

    @zoom_default.setter
    def zoom_default(self, value: float) -> None:
        self._qs.setValue(f"{self._GROUP_VIEWER}/zoom_default", value)

    @property
    def thumbnail_size(self) -> int:
        return int(self._qs.value(f"{self._GROUP_VIEWER}/thumbnail_size", 140))

    @thumbnail_size.setter
    def thumbnail_size(self, value: int) -> None:
        self._qs.setValue(f"{self._GROUP_VIEWER}/thumbnail_size", value)

    # ── External tools ────────────────────────────────────────────────────────

    @property
    def libreoffice_path(self) -> str:
        return self._qs.value(f"{self._GROUP_PATHS}/libreoffice_path", "")

    @libreoffice_path.setter
    def libreoffice_path(self, path: str) -> None:
        self._qs.setValue(f"{self._GROUP_PATHS}/libreoffice_path", path)

    @property
    def tesseract_path(self) -> str:
        return self._qs.value(f"{self._GROUP_PATHS}/tesseract_path", "")

    @tesseract_path.setter
    def tesseract_path(self, path: str) -> None:
        self._qs.setValue(f"{self._GROUP_PATHS}/tesseract_path", path)

    def sync(self) -> None:
        self._qs.sync()
