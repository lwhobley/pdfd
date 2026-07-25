# build_windows.ps1 - Build PDFDADDY for Windows
#
# Usage (from project root):
#   .\build\build_windows.ps1
#
# Prerequisites:
#   - Python 3.11+ on PATH (or a .venv in the project root)
#   - pip install pyinstaller
#   - Inno Setup 6 (optional, for installer): https://jrsoftware.org/isinfo.php

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$version = "0.1.0"
$distDir = "$root\dist\PDFDADDY"
# Keep PyInstaller scratch out of build\ (which holds the spec) and out of
# OneDrive, whose sync locks files and makes --clean fail with WinError 5.
$workDir = "$env:LOCALAPPDATA\PDFDADDY-build"

function Write-Step($msg) { Write-Host "==> $msg" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "    $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "    [WARN] $msg" -ForegroundColor Yellow }

# Venv
Write-Step "Checking virtual environment..."
if (-not (Test-Path ".venv\Scripts\Activate.ps1")) {
    Write-Step "Creating .venv..."
    python -m venv .venv
}
. ".venv\Scripts\Activate.ps1"

# Dependencies
Write-Step "Installing / updating dependencies..."
pip install -r requirements.txt -q --disable-pip-version-check
pip install pyinstaller -q --disable-pip-version-check
Write-Ok "Dependencies ready."

# PyInstaller
Write-Step "Running PyInstaller..."
pyinstaller build\pdf_forge.spec --clean --noconfirm --workpath "$workDir"

if (-not (Test-Path $distDir)) {
    Write-Host "==> BUILD FAILED - PyInstaller did not produce output." -ForegroundColor Red
    exit 1
}

$exePath = "$distDir\PDFDADDY.exe"
if (-not (Test-Path $exePath)) {
    Write-Host "==> BUILD FAILED - exe not found at $exePath" -ForegroundColor Red
    exit 1
}

$sizeMB = [math]::Round((Get-ChildItem $distDir -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB, 1)
Write-Ok "PyInstaller output: $distDir"
Write-Ok "Bundle size:        $sizeMB MB"

# Code signing (optional)
# $certThumbprint = "YOUR_CERT_THUMBPRINT_HERE"
# $signtool = "C:\Program Files (x86)\Windows Kits\10\bin\10.0.22621.0\x64\signtool.exe"
# if (Test-Path $signtool) {
#     Write-Step "Signing executable..."
#     & $signtool sign /sha1 $certThumbprint /fd sha256 /td sha256 `
#         /tr http://timestamp.digicert.com $exePath
#     Write-Ok "Signed: $exePath"
# } else {
#     Write-Warn "signtool.exe not found - skipping code signing."
# }

# Inno Setup installer
$iscc = $null
$isccCandidates = @(
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    "C:\Program Files\Inno Setup 6\ISCC.exe"
)
foreach ($candidate in $isccCandidates) {
    if (Test-Path $candidate) { $iscc = $candidate; break }
}

if ($iscc) {
    Write-Step "Compiling installer with Inno Setup..."
    & $iscc "installer\setup.iss"
    $setupExe = "$root\dist\PDFDADDY-$version-win64-setup.exe"
    if (Test-Path $setupExe) {
        $setupMB = [math]::Round((Get-Item $setupExe).Length / 1MB, 1)
        Write-Ok "Installer: $setupExe ($setupMB MB)"
    }
} else {
    Write-Warn "Inno Setup not found - skipping installer."
    Write-Warn "Install from https://jrsoftware.org/isinfo.php, then re-run."
}

# Summary
Write-Host ""
Write-Host "Build complete!" -ForegroundColor Green
Write-Host "  App bundle : $distDir" -ForegroundColor Yellow
Write-Host "  Executable : $exePath" -ForegroundColor Yellow
