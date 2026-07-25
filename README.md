# PDF Forge Desktop

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
# Output: dist\PDFForgeDesktop\PDFForgeDesktop.exe
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

## Milestone Progress

- [x] M0: Bootstrap — project skeleton, job system, tool registry, settings
- [x] M1: Viewer + core tools — open/view/thumbnails, merge/split/rotate/delete/extract
- [ ] M2: Page organizer — drag-and-drop grid, batch ops, bookmarks
- [ ] M3: Edit + OCR — annotations, watermark, page numbers, OCR
- [ ] M4: Convert + Secure — Office→PDF, encrypt/decrypt, sign
- [ ] M5: Workflow builder — visual node editor

## External Tools (Optional)

| Tool | Purpose | Install |
|------|---------|---------|
| Tesseract OCR | OCR of scanned PDFs | https://github.com/UB-Mannheim/tesseract/wiki |
| LibreOffice | Office → PDF conversion | https://www.libreoffice.org/download/ |
| Ghostscript | Advanced PDF processing | https://www.ghostscript.com/download/gsdnld.html |

Configure paths in Settings → External Tools if not on PATH.
