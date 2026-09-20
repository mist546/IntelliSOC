# Starts the Mini-SOC frontend dev server locally.
# Run from the project root: .\scripts\start_frontend.ps1

$ErrorActionPreference = "Stop"
Set-Location "$PSScriptRoot\..\frontend"

if (-not (Test-Path "node_modules")) {
    Write-Host "Installing frontend dependencies..."
    npm install
}

npm run dev
