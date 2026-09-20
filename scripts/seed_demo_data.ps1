# Seeds a demo admin user and ingests all sample logs directly into the
# database (no running server required). Run this once before your first
# demo, after the backend venv has been created (start_backend.ps1 creates
# it, or create it manually - see docs/setup.md).
# Run from the project root: .\scripts\seed_demo_data.ps1

$ErrorActionPreference = "Stop"
Set-Location "$PSScriptRoot\..\backend"
& ".\.venv\Scripts\python.exe" scripts\seed_demo_data.py
