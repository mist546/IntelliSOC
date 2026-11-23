# Plays a simulated attack in real time for live demos (see soc-agent/simulate_attack.py).
# Run from the project root while the backend, frontend and soc-agent are running:
#   .\scripts\simulate_attack.ps1
#   .\scripts\simulate_attack.ps1 --ip random
#   .\scripts\simulate_attack.ps1 --scenario windows-logon

$ErrorActionPreference = "Stop"
Set-Location "$PSScriptRoot\..\soc-agent"
& ".\.venv\Scripts\python.exe" simulate_attack.py @args
