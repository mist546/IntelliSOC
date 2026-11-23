# Starts the Mini-SOC backend API server locally (no Docker).
# Run from the project root: .\scripts\start_backend.ps1

$ErrorActionPreference = "Stop"
Set-Location "$PSScriptRoot\..\backend"

if (-not (Test-Path ".venv")) {
    Write-Host "Creating virtual environment..."
    py -3.11 -m venv .venv
    & ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
    & ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt
}

& ".\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --timeout-graceful-shutdown 3
