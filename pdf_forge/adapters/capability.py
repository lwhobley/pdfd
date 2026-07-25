"""Runtime capability detection — checked once at startup and cached."""
from __future__ import annotations
import shutil
import logging

log = logging.getLogger(__name__)


class Capabilities:
    _checked: bool = False
    tesseract: bool = False
    libreoffice: bool = False
    ghostscript: bool = False
    opencv: bool = False
    easyocr: bool = False

    @classmethod
    def detect(cls, settings=None) -> None:
        if cls._checked:
            return
        cls._checked = True

        # Tesseract — check settings path first, then PATH
        tesseract_path = settings.tesseract_path if settings else ""
        if tesseract_path:
            import os
            cls.tesseract = os.path.isfile(tesseract_path)
        else:
            cls.tesseract = shutil.which("tesseract") is not None
        log.info("tesseract: %s", cls.tesseract)

        # LibreOffice
        lo_path = settings.libreoffice_path if settings else ""
        if lo_path:
            import os
            cls.libreoffice = os.path.isfile(lo_path)
        else:
            cls.libreoffice = (
                shutil.which("soffice") is not None
                or shutil.which("libreoffice") is not None
            )
        log.info("libreoffice: %s", cls.libreoffice)

        # Ghostscript
        cls.ghostscript = (
            shutil.which("gs") is not None or shutil.which("gswin64c") is not None
        )
        log.info("ghostscript: %s", cls.ghostscript)

        # OpenCV
        try:
            import cv2  # noqa: F401
            cls.opencv = True
        except ImportError:
            cls.opencv = False
        log.info("opencv: %s", cls.opencv)

        # EasyOCR
        try:
            import easyocr  # noqa: F401
            cls.easyocr = True
        except ImportError:
            cls.easyocr = False
        log.info("easyocr: %s", cls.easyocr)
