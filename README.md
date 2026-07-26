# PDF'D

A production-grade Windows desktop PDF workstation built with Python + PySide6 + PyMuPDF + pikepdf.

## Setup (Development)

```powershell
# 1. Create and activate virtualenv
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Install dependencies
pip install -r requirements-dev.txt

# 3. Run the app
python main.py
```

## Run Tests

```powershell
pytest tests/ -v
```

## Build Windows .exe

```powershell
.\build\build_windows.ps1
# Output: dist\PDFD\PDFD.exe
```

Or manually:
```powershell
pip install pyinstaller
pyinstaller build/pdf_forge.spec --clean --noconfirm
```

## Architecture

```
pdf_forge/
├── core/         # Events, logging, exceptions
├── ui/           # PySide6 UI layer (viewer, sidebars, dialogs, panels)
├── tools/        # Tool registry + per-tool job implementations
├── services/     # Domain services (PDFService, OCRService)
├── workers/      # Job queue, worker threads
├── adapters/     # PyMuPDF, pikepdf, Tesseract wrappers
└── persistence/  # Settings, recent files, job history
```

## External Tools (Optional)

| Tool | Purpose | Install |
|------|---------|---------|
| Tesseract OCR | OCR of scanned PDFs | https://github.com/UB-Mannheim/tesseract/wiki |
| LibreOffice | Office → PDF conversion | https://www.libreoffice.org/download/ |
| Ghostscript | Advanced PDF processing | https://www.ghostscript.com/download/gsdnld.html |

Configure paths in Settings → External Tools if not on PATH.
