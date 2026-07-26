# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec — PDF Forge Desktop
#
# Run from the project root:
#   pyinstaller build/pdf_forge.spec --clean --noconfirm
#
# All paths are relative to this file's directory (build/).

import os
from PyInstaller.utils.hooks import collect_all, collect_data_files

# ── Collect third-party packages with native extensions or data files ─────────
_datas, _binaries, _hidden = [], [], []

# Required packages — fail fast if missing
for _pkg in (
    "fitz",                    # PyMuPDF — native PDF engine
    "pikepdf",                 # QPDF wrapper — has QPDF DLLs on Windows
    "pdfplumber",              # table extraction
    "pdfminer",                # pdfplumber dependency — has cmap data files
    "pyhanko",                 # digital signatures — has font data
    "pyhanko_certvalidator",   # certificate validation
    "reportlab",               # PDF generation — has font data
    "openpyxl",                # Excel export — has template data
):
    try:
        d, b, h = collect_all(_pkg)
        _datas += d
        _binaries += b
        _hidden += h
    except Exception as e:
        print(f"[WARNING] collect_all({_pkg!r}) failed: {e}")

# PIL — PyInstaller has a built-in hook for binaries; grab data files
try:
    _datas += collect_data_files("PIL")
except Exception:
    pass

# cv2 (opencv-python-headless) — optional, may not be installed
try:
    d, b, h = collect_all("cv2")
    _datas += d; _binaries += b; _hidden += h
except Exception:
    pass

# ── Spec ──────────────────────────────────────────────────────────────────────
block_cipher = None

a = Analysis(
    ["../main.py"],
    pathex=[".."],
    binaries=_binaries,
    datas=_datas + [
        # Bundle the assets directory (icons, styles, etc.)
        ("../pdf_forge/assets", "pdf_forge/assets"),
    ],
    hiddenimports=_hidden + [
        # PySide6 extras not always auto-detected by hooks
        "PySide6.QtSvg",
        "PySide6.QtPrintSupport",
        "PySide6.QtOpenGL",
        # Thin wrappers / pure-Python deps
        "pytesseract",
        "chardet",
        "chardet.universaldetector",
        # pdfminer high-level API
        "pdfminer.high_level",
        "pdfminer.layout",
        "pdfminer.pdfpage",
        # python-docx (used by LibreOffice adapter fallback)
        "docx",
    ],
    hookspath=[],
    hooksconfig={},
    # Runs at startup in the frozen process (before any app code)
    # SPECPATH is PyInstaller's built-in pointing to the spec file's directory
    runtime_hooks=[os.path.join(SPECPATH, "rthooks", "rthook_tesseract.py")],
    # Safe excludes: things we know are not used
    excludes=["tkinter", "_tkinter", "doctest", "xmlrpc"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="PDFD",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    # UPX off: avoids antivirus false positives and Qt DLL corruption
    upx=False,
    console=False,    # windowed app — no console window on launch
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # Windows version resource (shows in Properties → Details tab)
    version="version_info.txt",
    icon="../pdf_forge/assets/icons/app.ico",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name="PDFD",
)
