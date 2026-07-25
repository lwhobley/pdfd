"""LibreOffice headless bridge for Office-to-PDF conversion.

Tries to find soffice in (in order):
  1. AppSettings.libreoffice_path
  2. Known Windows install paths
  3. PATH
"""
from __future__ import annotations
import os
import subprocess
import shutil
import logging
from pathlib import Path

log = logging.getLogger(__name__)

_WINDOWS_CANDIDATES = [
    r"C:\Program Files\LibreOffice\program\soffice.exe",
    r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
]


def find_soffice(configured_path: str = "") -> str | None:
    if configured_path and os.path.isfile(configured_path):
        return configured_path
    for candidate in _WINDOWS_CANDIDATES:
        if os.path.isfile(candidate):
            return candidate
    found = shutil.which("soffice") or shutil.which("libreoffice")
    return found


def convert_to_pdf(
    input_path: str,
    output_dir: str,
    soffice: str,
    timeout: int = 120,
) -> str:
    """Run LibreOffice headless conversion; return output PDF path.

    LibreOffice writes <basename>.pdf into output_dir.
    """
    os.makedirs(output_dir, exist_ok=True)
    cmd = [
        soffice,
        "--headless",
        "--norestore",
        "--convert-to", "pdf",
        "--outdir", output_dir,
        input_path,
    ]
    log.debug("LibreOffice cmd: %s", cmd)
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"LibreOffice exited {result.returncode}:\n{result.stderr}"
        )
    # LibreOffice names the output <stem>.pdf
    stem = Path(input_path).stem
    out_path = os.path.join(output_dir, stem + ".pdf")
    if not os.path.exists(out_path):
        raise FileNotFoundError(
            f"LibreOffice did not produce expected output: {out_path}\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
    return out_path
