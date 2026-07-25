"""OCR service — abstraction over Tesseract and EasyOCR backends.

Detection order:
  1. Tesseract (via pytesseract) — preferred, widely installed, fast
  2. EasyOCR — fallback, no binary required, GPU-optional
  3. fitz built-in OCR (Tesseract via fitz.TextPage) — last resort
"""
from __future__ import annotations
import io
import logging
from typing import Protocol

log = logging.getLogger(__name__)


class OCRBackend(Protocol):
    name: str

    def is_available(self) -> bool: ...
    def ocr_image_to_text(self, pil_image) -> str: ...
    def ocr_image_to_hocr(self, pil_image) -> bytes | None: ...


class TesseractBackend:
    name = "tesseract"

    def __init__(self, tesseract_cmd: str = "", language: str = "eng") -> None:
        self._cmd = tesseract_cmd
        self._language = language

    def is_available(self) -> bool:
        try:
            import pytesseract
            if self._cmd:
                pytesseract.pytesseract.tesseract_cmd = self._cmd
            pytesseract.get_tesseract_version()
            return True
        except Exception:
            return False

    def _setup(self) -> "pytesseract":
        import pytesseract
        if self._cmd:
            pytesseract.pytesseract.tesseract_cmd = self._cmd
        return pytesseract

    def ocr_image_to_text(self, pil_image) -> str:
        ts = self._setup()
        return ts.image_to_string(pil_image, lang=self._language)

    def ocr_image_to_hocr(self, pil_image) -> bytes | None:
        ts = self._setup()
        try:
            return ts.image_to_pdf_or_hocr(pil_image, lang=self._language, extension="hocr")
        except Exception:
            return None

    def ocr_image_to_pdf(self, pil_image) -> bytes | None:
        """Return a single-page searchable PDF bytes from one image."""
        ts = self._setup()
        try:
            return ts.image_to_pdf_or_hocr(pil_image, lang=self._language, extension="pdf")
        except Exception:
            return None


class EasyOCRBackend:
    name = "easyocr"

    def __init__(self, languages: list[str] | None = None) -> None:
        self._languages = languages or ["en"]
        self._reader = None

    def is_available(self) -> bool:
        try:
            import easyocr  # noqa: F401
            return True
        except ImportError:
            return False

    def _get_reader(self):
        if self._reader is None:
            import easyocr
            self._reader = easyocr.Reader(self._languages, gpu=False, verbose=False)
        return self._reader

    def ocr_image_to_text(self, pil_image) -> str:
        import numpy as np
        reader = self._get_reader()
        arr = np.array(pil_image)
        results = reader.readtext(arr)
        return "\n".join(text for _, text, _ in results)

    def ocr_image_to_hocr(self, pil_image) -> bytes | None:
        return None  # EasyOCR doesn't produce hOCR natively


class OCRService:
    """Selects the best available OCR backend and exposes a unified API."""

    def __init__(self, tesseract_cmd: str = "", language: str = "eng") -> None:
        self._backends: list[OCRBackend] = [
            TesseractBackend(tesseract_cmd, language),
            EasyOCRBackend(),
        ]
        self._active: OCRBackend | None = None

    def detect(self) -> str | None:
        for backend in self._backends:
            if backend.is_available():
                self._active = backend
                log.info("OCR backend selected: %s", backend.name)
                return backend.name
        log.warning("No OCR backend available")
        return None

    @property
    def backend_name(self) -> str | None:
        return self._active.name if self._active else None

    def is_available(self) -> bool:
        if self._active is None:
            self.detect()
        return self._active is not None

    def ocr_page_image(self, pil_image) -> str:
        if not self.is_available():
            raise RuntimeError("No OCR backend available")
        return self._active.ocr_image_to_text(pil_image)

    def ocr_page_to_pdf_bytes(self, pil_image) -> bytes | None:
        """Return searchable-PDF bytes for one page, or None if unsupported."""
        if not self.is_available():
            return None
        if isinstance(self._active, TesseractBackend):
            return self._active.ocr_image_to_pdf(pil_image)
        return None
