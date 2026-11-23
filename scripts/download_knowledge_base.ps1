# Downloads public security references straight into the knowledge base layout
# (data/knowledge_base/): MITRE ATT&CK STIX JSON, NIST PDFs (SP 800-61r3, CSF 2.0,
# SP 800-92), OWASP material, CWE, CISA KEV, NVD CVEs, Sigma rules.
# Run from the project root, then run .\scripts\ingest_knowledge_base.ps1
#   .\scripts\download_knowledge_base.ps1                      # lists sources
#   .\scripts\download_knowledge_base.ps1 -All
#   .\scripts\download_knowledge_base.ps1 -Source nist,mitre
param(
    [switch]$All,
    [string[]]$Source
)

$ErrorActionPreference = "Stop"
Set-Location "$PSScriptRoot\..\backend"
$extra = @()
if ($All) { $extra += "--all" }
foreach ($s in $Source) { $extra += "--source"; $extra += $s }
& ".\.venv\Scripts\python.exe" scripts\download_knowledge_base.py @extra
