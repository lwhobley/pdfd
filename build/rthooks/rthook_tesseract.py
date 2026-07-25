# Runtime hook: auto-discovers tesseract.exe at frozen-app startup.
# The app's Settings dialog can override this at any time.
import os
import sys

if getattr(sys, "frozen", False):
    _CANDIDATES = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ]
    try:
        import pytesseract
        for _p in _CANDIDATES:
            if os.path.isfile(_p):
                pytesseract.pytesseract.tesseract_cmd = _p
                break
    except ImportError:
        pass
