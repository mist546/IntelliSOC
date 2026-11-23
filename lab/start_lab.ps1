# Builds and starts the IntelliSOC attack lab (target + attacker).
# Run from anywhere; needs Docker Desktop running.
#
#   .\start_lab.ps1          direct mode: the soc-agent tails the target's logs
#   .\start_lab.ps1 -Wazuh   Wazuh mode: a Wazuh agent on the target ships them
#                            to a Wazuh manager container; the soc-agent tails
#                            the manager's archives.json instead
#
# Switching modes recreates the target (and adds/removes the manager), so the
# same attack is never reported twice.
param([switch]$Wazuh)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if ($Wazuh) {
    New-Item -ItemType Directory -Force -Path "..\data\live_logs\wazuh" | Out-Null
    docker compose -f docker-compose.yml -f docker-compose.wazuh.yml up -d --build --remove-orphans
} else {
    New-Item -ItemType Directory -Force -Path "..\data\live_logs\lab" | Out-Null
    docker compose up -d --build --remove-orphans
}
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "Lab up. Target: ssh 127.0.0.1:2222 / http://127.0.0.1:8080"
Write-Host "Attack from the attacker box:"
Write-Host "    .\attack.ps1 ssh-brute | web | (no argument: interactive shell)"
if ($Wazuh) {
    Write-Host "Wazuh mode: target logs -> wazuh-agent -> wazuh-manager ->"
    Write-Host "data\live_logs\wazuh\archives.json (the soc-agent tails it)."
    Write-Host "The manager takes about a minute to start; check the agent with:"
    Write-Host "    docker compose exec wazuh-manager /var/ossec/bin/agent_control -l"
} else {
    Write-Host "Logs stream to data\live_logs\lab\ (the soc-agent tails them)."
}
