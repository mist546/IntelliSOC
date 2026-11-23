# Setup Guide

## Prerequisites

- **Python 3.11** (3.13/3.14 are not recommended yet - several ML/vector-DB
  dependencies such as `chromadb` and `scikit-learn` lag behind the newest
  CPython releases on prebuilt wheels). If you only have a newer Python
  installed, use the `py` launcher to select 3.11, or install it from
  python.org.
- **Node.js 18+** (frontend).
- **Ollama** (https://ollama.com) installed and running (`ollama serve`,
  or it may already run as a background service after installation).
- **Docker Desktop** - optional, only needed for the containerized setup.

## 1. Download the required models (do this first, separately)

```powershell
ollama pull gemma4:latest        # default local LLM used for AI analysis
ollama pull nomic-embed-text     # required for RAG embeddings
```

`gemma4:latest` (~9.6GB) was chosen as the default after benchmarking on
this project's development machine (CPU-only): it reliably produces clean
JSON without the very slow "extended thinking" behavior some reasoning
models (e.g. `qwen3:4b`) exhibit even when asked to skip it. **If your
machine is slower, or you'd rather use a smaller/faster model**, set
`OLLAMA_MODEL` in your `.env` to any chat-capable model you already have
pulled - the system only requires that the model can follow a system
prompt and produce JSON-shaped text; it does not require Ollama's strict
`format: json` mode (which this project deliberately avoids - see
`docs/rag.md`/`docs/agent-workflow.md` context in the LLM service code
comments for why).

If you'd rather use Ollama's hosted cloud models instead of a local model,
see "Using Ollama Cloud" below.

> **Windows note - use `http://127.0.0.1:11434`, not `localhost`.** On Windows
> `localhost` resolves to IPv6 `::1` first and Ollama only listens on IPv4,
> so every request first waits ~2 s for the IPv6 connection to fail. That
> tax applied to every embedding and LLM call (measured 2.1 s vs 0.1 s per
> request). `.env.example` and the config default now use `127.0.0.1`.

## 2. Backend setup

```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Copy the environment template and adjust if needed:

```powershell
cd ..
copy .env.example .env
```

The defaults work out of the box for local development (SQLite database
created automatically under `data/`).

### Database setup

SQLite is used by default - no setup required, the file is created
automatically on first run at `data/mini_soc.db`. To use PostgreSQL
instead (all models are PostgreSQL-compatible), set in `.env`:

```
DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/minisoc
```

and additionally `pip install psycopg2-binary` in the backend venv (not
included by default to keep the base install lighter for the common
SQLite path).

### Ingest the knowledge base (required for RAG)

```powershell
.\scripts\ingest_knowledge_base.ps1
```

This indexes every `.md`, `.txt`, `.pdf` and MITRE ATT&CK `.json` file
under `data/knowledge_base/` via Ollama and stores it in a local persistent
Chroma collection at `rag/chroma_db/`. It is incremental: unchanged files
are skipped, changed files re-indexed and deleted files removed, so re-run
it whenever you add or edit documents. Use `-Reset` after changing the
embedding model or prefixes (it tells you when that is needed).

The public reference material (MITRE ATT&CK, the NIST PDFs, OWASP, CWE,
CISA KEV, recent NVD CVEs, Sigma rules, SSH hardening) is not stored in git;
fetch it once:

```powershell
.\scripts\download_knowledge_base.ps1           # lists the sources
.\scripts\download_knowledge_base.ps1 -All      # ~60 MB download
.\scripts\ingest_knowledge_base.ps1             # ~7,100 chunks, about 2 minutes
```

To check retrieval quality afterwards:
`cd backend; .\.venv\Scripts\python.exe scripts\evaluate_rag.py` (see `docs/rag.md`).

See `data/knowledge_base/README.md` for exactly what each source contains
and how to add your own documents (UI upload or drop files in `custom/`).

### Seed demo data (recommended before your first run)

```powershell
.\scripts\seed_demo_data.ps1
```

Creates an admin user (`admin` / `AdminPass123!` - **change this
password**, or just register your own user via the UI instead) and ingests
every file in `data/sample_logs/` directly into the database, producing a
ready-to-explore set of alerts and incidents without needing to run the
backend server first.

### Run the backend

```powershell
.\scripts\start_backend.ps1
```

Or manually: `cd backend && .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload`

API available at `http://localhost:8000`, interactive docs at
`http://localhost:8000/docs`.

## 3. Frontend setup

```powershell
.\scripts\start_frontend.ps1
```

Or manually: `cd frontend && npm install && npm run dev`

Dev server at `http://localhost:5173`. Copy `frontend/.env.example` to
`frontend/.env` if you need to point at a non-default backend URL.

## 4. SOC endpoint agent (live, real-time collection)

Register an agent (as an admin, e.g. via `/docs` Swagger UI or `curl`):

```
POST /api/agents/register   {"name": "demo-collector", "hostname": "demo-host"}
```

This returns an `id` and `api_key` **shown only once** - copy them.

```powershell
cd soc-agent
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:MINISOC_AGENT_ID="<id from registration>"
$env:MINISOC_AGENT_KEY="<api_key from registration>"
.\.venv\Scripts\python.exe agent.py --once --replay   # single pass, for a demo
# or, to continuously tail:
.\.venv\Scripts\python.exe agent.py
```

The agent polls every 2 s and sends a heartbeat every 30 s, so the
**Agents** page shows it as ONLINE (STALE/OFFLINE if it stops). If the
backend is unreachable nothing is lost: file offsets and the Windows event
bookmark only advance once a batch has been delivered, so the backlog is
sent when the backend comes back. It collects
from two kinds of source (see `soc-agent/config.yaml`):

- **Tailed log files.** By default `data/live_logs/auth.log`, the file the
  attack simulator writes to (created on the first simulator run). On a
  real Linux host point `watched_files` at `/var/log/auth.log`,
  `/var/log/syslog`, etc. Both classic (`Jan 12 10:15:23`) and RFC 3339
  (`2026-01-12T10:15:23.123456+05:00`, the default on Ubuntu 23.10+)
  syslog timestamps are understood; ones without a timezone are read as
  the host's local time and converted to UTC.
- **The live Windows Security event log** (Windows only,
  `windows_event_log.enabled: true`). Events 4625/4624/4740/4720/4648/1102
  are read with the built-in `wevtutil` tool, with a bookmark so restarts
  neither resend nor skip events; the first start begins at the newest
  record. Routine service/system-account logons are filtered out, and
  logons with no network source (console, `runas`, local API) are
  attributed to `127.0.0.1` so local password guessing is caught by the
  same brute-force rules. **Reading the Security log requires running the
  agent from an elevated (Run as Administrator) terminal**; otherwise the
  agent prints a warning and carries on with the files only.

### Watching an attack live

With the backend, frontend and agent running, open the dashboard and in a
second terminal run the simulator:

```powershell
cd soc-agent
.\.venv\Scripts\python.exe simulate_attack.py                           # SSH brute force from 203.0.113.55, then a successful login
.\.venv\Scripts\python.exe simulate_attack.py --ip random               # repeat runs (an open alert for the same IP suppresses duplicates for 30 min)
.\.venv\Scripts\python.exe simulate_attack.py --scenario windows-logon  # REAL failed Windows logons (needs the elevated agent)
```

The SSH scenario appends current-time sshd lines about 1.5 s apart; a few
seconds after the 10th failure the dashboard toasts the HIGH
`SSH_BRUTE_FORCE` alert, then the CRITICAL `FAILED_THEN_SUCCESS` one. The
Windows scenario calls the Windows `LogonUser` API with wrong passwords for
a non-existent account (`intellisoc-sim-user`, so nothing can be locked
out); Windows itself writes the 4625 events, provided logon-failure
auditing is on (the default - check with
`auditpol /get /subcategory:"Logon"` in an elevated terminal). The same
simulator is available from the project root as
`.\scripts\simulate_attack.ps1`.

### Collecting logs with Wazuh

Wazuh agents can replace the soc-agent for collection from other machines.
A Wazuh agent only talks to a **Wazuh manager**, so the flow is:

```
[VMs: Wazuh agent] --1514/1515--> [Linux VM: wazuh-manager + soc-agent bridge]
    --POST /api/events/wazuh--> [IntelliSOC backend :8000] --> detection --> dashboard
```

The bridge is the ordinary soc-agent, run on the manager with
`config.wazuh.yaml`: it tails `/var/ossec/logs/alerts/alerts.json` and
forwards the raw alerts. The backend maps each one to the underlying log
type (sshd/sudo -> `AUTH_LOG`, Windows Security -> `WINDOWS_EVENT`,
Apache/Nginx access -> `APACHE_ACCESS`/`NGINX_ACCESS`), so IntelliSOC's own
detection rules fire exactly as they do for uploaded files. Wazuh's rule,
level, MITRE IDs and agent are kept in each event's metadata. Wazuh's own
rule hits do **not** become IntelliSOC alerts: anything else (file
integrity, rootcheck, ...) is stored as a `WAZUH` event only. Wazuh writes
each log line once, under its single best-matching rule - so a frequency
rule such as 5763 "sshd: brute force" or 40112 "authentication success
after failures" carries a line that appears nowhere else, and it is
parsed like any other (verified against a real Wazuh 4.14 manager).

No VMs? The attack lab can run a Wazuh manager and agent in Docker instead
- see "Wazuh in Docker" below. The VM steps that follow are for collecting
from real machines.

**Scripted setup (Ubuntu/Debian VMs).** Two scripts in `soc-agent/` do
steps 2-4 below. After registering a `wazuh-bridge` agent on the Agents
page and copying `soc-agent/` to the manager VM:

```bash
# manager VM - Wazuh manager + IntelliSOC bridge (systemd service)
sudo bash setup_wazuh_bridge.sh --backend http://<PC-IP>:8000 --agent-id <id> --agent-key <api_key>
# each monitored Linux VM - Wazuh agent (add --enable-ssh-password-auth for SSH demos)
sudo bash setup_wazuh_agent.sh --manager <manager-VM-IP>
```

Both check connectivity first and stop with a hint if something is
unreachable, and both are safe to re-run. `setup_wazuh_agent.sh` also
handles end-of-life Debian 10, whose packages moved to archive.debian.org.

**1. Network.** Give the VMs a Bridged or Host-only adapter so they can
reach each other and your PC (NAT usually can't). On the PC, allow the
backend port from an elevated PowerShell (`start_backend.ps1` already
listens on all interfaces):

```powershell
New-NetFirewallRule -DisplayName "IntelliSOC API" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow
```

**2. Wazuh manager** (Ubuntu VM, ~2 GB RAM is enough for the manager alone
- IntelliSOC is the dashboard, so the Wazuh indexer/dashboard are not
needed). Follow Wazuh's "Wazuh server - step-by-step installation" docs for
the current version; in short:

```bash
curl -s https://packages.wazuh.com/key/GPG-KEY-WAZUH | sudo gpg --no-default-keyring --keyring gnupg-ring:/usr/share/keyrings/wazuh.gpg --import && sudo chmod 644 /usr/share/keyrings/wazuh.gpg
echo "deb [signed-by=/usr/share/keyrings/wazuh.gpg] https://packages.wazuh.com/4.x/apt/ stable main" | sudo tee /etc/apt/sources.list.d/wazuh.list
sudo apt update && sudo apt install wazuh-manager
sudo systemctl enable --now wazuh-manager
```

**3. Wazuh agents** on each monitored VM, pointed at the manager's IP:

- Linux (with the same apt repository added):
  `sudo WAZUH_MANAGER="<manager-ip>" apt install wazuh-agent && sudo systemctl enable --now wazuh-agent`.
  Make sure `/var/ossec/etc/ossec.conf` has a `<localfile>` for
  `/var/log/auth.log` (`<log_format>syslog</log_format>`), and for a web
  server its access log (`<log_format>apache</log_format>`). On Debian 12 /
  minimal images without `/var/log/auth.log`, `sudo apt install rsyslog`.
  For SSH brute-force demos, sshd needs `PasswordAuthentication yes`.
- Windows: install the MSI with
  `msiexec.exe /i wazuh-agent-<version>.msi /q WAZUH_MANAGER="<manager-ip>"`,
  then `NET START WazuhSvc`. The Security channel (4625, 4624, ...) is
  collected by default.

Check on the manager: `sudo /var/ossec/bin/agent_control -l` lists the
connected agents, and `sudo tail -f /var/ossec/logs/alerts/alerts.json`
shows alerts arriving.

**4. The bridge.** Register an agent on IntelliSOC's **Agents** page (e.g.
name `wazuh-bridge`), then on the manager VM:

```bash
# copy the soc-agent/ folder here first (scp, git clone, shared folder...)
sudo apt install python3-venv          # Python 3.10+
cd soc-agent
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
# edit config.wazuh.yaml: backend_url: "http://<your PC's IP>:8000"
export MINISOC_AGENT_ID=<id> MINISOC_AGENT_KEY=<api_key>
sudo -E .venv/bin/python agent.py --config config.wazuh.yaml
```

`sudo` is needed because `alerts.json` is `wazuh:wazuh 0660`. The bridge
shows ONLINE on the Agents page; Wazuh's daily rotation of `alerts.json` is
handled, and if IntelliSOC is down the bridge keeps its place and sends the
backlog once it is back. To run it permanently, a systemd unit such as
`/etc/systemd/system/intellisoc-bridge.service`:

```ini
[Unit]
Description=IntelliSOC Wazuh bridge
After=network-online.target wazuh-manager.service

[Service]
WorkingDirectory=/opt/intellisoc/soc-agent
Environment=MINISOC_AGENT_ID=<id>
Environment=MINISOC_AGENT_KEY=<api_key>
ExecStart=/opt/intellisoc/soc-agent/.venv/bin/python agent.py --config config.wazuh.yaml
Restart=always

[Install]
WantedBy=multi-user.target
```

then `sudo systemctl daemon-reload && sudo systemctl enable --now intellisoc-bridge`.

**5. Try it.** From any machine, `ssh wronguser@<linux-vm>` with a wrong
password 10+ times: the HIGH "SSH Brute Force" alert appears live, with
the host set to the Wazuh agent's name. On the Windows VM, ten wrong
passwords (e.g. `runas /user:%COMPUTERNAME%\someuser cmd`) raise "Windows
logon Brute Force".

Note that `alerts.json` only contains events that match a Wazuh rule at or
above `log_alert_level` (default 3). Failed/successful logins and web
attacks do; ordinary `200 OK` web requests don't, so they never reach
IntelliSOC. Without any VMs, the mapping can be tried by uploading
`data/sample_logs/wazuh_alerts.json` (or `wazuh_archives.json`, a real
archive recorded from the Docker lab below) on the **Logs** page.

### Wazuh in Docker (attack lab)

The attack lab (`lab/`, see `lab/README.md`) has a Wazuh mode that needs
nothing but Docker Desktop: the target container runs a Wazuh agent, and a
Wazuh manager runs in a third container.

```
attacker --attacks--> target (sshd, nginx, wazuh-agent) --1514/1515--> wazuh-manager
   wazuh-manager writes every event to archives.json
   --bind mount--> data/live_logs/wazuh/archives.json
   --soc-agent on this PC (WAZUH_ALERTS)--> POST /api/events/wazuh --> detection
```

```powershell
cd lab
.\start_lab.ps1 -Wazuh       # first run downloads the Wazuh image (~1 GB)
.\attack.ps1 ssh-brute       # then: .\attack.ps1 web
```

The soc-agent's default `config.yaml` already watches
`data/live_logs/wazuh/archives.json`, so start it as usual (section 4).
Plain `.\start_lab.ps1` switches back to direct mode. Only one mode runs at
a time - in Wazuh mode the target's logs stay inside Docker - so an attack
is never reported twice.

How it differs from the VM setup:

- **Every event, not just alerts.** The manager (`lab/wazuh/ossec.conf`)
  has `logall_json` on and the soc-agent tails `archives.json`, so
  IntelliSOC sees every log line - ordinary `200 OK` requests and sshd lines
  that match no Wazuh rule too - exactly as in direct mode. Lines that
  matched no Wazuh rule have no `rule` field and are stored as
  `WAZUH_EVENT` if they aren't auth or web lines.
- **No bridge to install.** `archives.json` is bind-mounted to this PC, and
  the regular soc-agent forwards it.
- **Manager only.** No Wazuh indexer or dashboard (IntelliSOC is the
  dashboard); Filebeat is removed from the image and the manager's own
  scanners are off. A few `IndexerConnector initialization failed`
  warnings at manager start-up are expected and harmless.
- **Versions.** Manager and agent are pinned to Wazuh 4.14.10
  (`lab/wazuh/Dockerfile`, `WAZUH_VERSION` in `lab/target/Dockerfile`);
  change both together - an agent must not be newer than its manager.

Useful checks:

```powershell
cd lab
docker compose -f docker-compose.yml -f docker-compose.wazuh.yml exec wazuh-manager /var/ossec/bin/agent_control -l
docker compose -f docker-compose.yml -f docker-compose.wazuh.yml logs -f wazuh-manager
Get-Content ..\data\live_logs\wazuh\archives.json -Tail 5 -Wait
```

The manager's ports 1514/1515 are published on `127.0.0.1`, so a Wazuh
agent installed on this Windows PC can report to it as well (install the
MSI with `WAZUH_MANAGER="127.0.0.1"`); its Security-log events then arrive
through the same path as `WINDOWS_EVENT`s. This optional path has not been
tested.

## 5. Run the tests

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests/ -v
```

See `docs/testing.md` for what's covered and why one test is a real
(unmocked) integration test against your local Ollama instance.

## 6. Docker (optional)

```powershell
docker compose up --build
```

**Important**: Ollama is intentionally *not* containerized - it must run
on your host machine (`ollama serve`) with the required models pulled. The
backend container reaches it via `host.docker.internal`. This keeps GPU
passthrough and model-storage concerns entirely out of Docker, which would
otherwise be a significant added complexity for a student FYP.

> Note: the Docker configuration in this repository has been written to be
> correct (all data-directory paths are explicitly set as container
> environment variables, since only `backend/` is baked into the image and
> `data/`/`rag/` are brought in via the `./data:/app/data` volume mount at
> runtime) but **has not been build-tested in this environment**, because
> Docker Desktop's daemon was not running on the development machine used
> to build this project. Please run `docker compose up --build` yourself
> and report any issues - the local (non-Docker) setup above is fully
> tested and is the recommended path for now.

## Using Ollama Cloud instead of a local model

The backend has two providers, switchable at runtime on the Settings page
(or with `LLM_PROVIDER` in `.env`):

| `LLM_PROVIDER` | Model setting | Default | Runs on |
|---|---|---|---|
| `ollama_local` | `OLLAMA_MODEL` | `gemma4:latest` | your machine, fully offline |
| `ollama_cloud` | `OLLAMA_CLOUD_MODEL` | `gpt-oss:120b-cloud` | Ollama's cloud |

### Cloud through the local daemon (default) - tested and confirmed working

Once you're signed in to the local `ollama` client (`ollama signin`),
cloud-hosted models appear in `ollama list` with a `-cloud`/`:cloud` suffix
and are served through the same local `/api/generate` endpoint as any local
model. With `LLM_PROVIDER=ollama_cloud` and no `OLLAMA_CLOUD_API_KEY`, the
backend sends `OLLAMA_CLOUD_MODEL` to the local daemon at `OLLAMA_BASE_URL`,
which forwards it using that sign-in. Verified with a real end-to-end
investigation against `gpt-oss:120b-cloud`: **~15 seconds total**, versus
40-90+ seconds against a local CPU-bound model. Which `:cloud` models are in
your account's free tier varies; a 402 ("add usage credits") comes back
instantly, before any generation, so checking a model costs nothing.

### Direct API key, no local daemon required

If `OLLAMA_CLOUD_API_KEY` is set, `ollama_cloud` instead calls
`OLLAMA_CLOUD_BASE_URL` (`https://ollama.com`) directly via
`backend/app/services/llm/ollama_cloud.py`. The key must be a REST API key
from ollama.com/settings/keys - a *different* credential from the SSH
keypair `ollama signin` creates (`~/.ollama/id_ed25519.pub`; pasting that
here gives a 401). On this route model names drop the suffix
(`gpt-oss:120b`, not `gpt-oss:120b-cloud`). Use it only when no local
daemon is available (e.g. a minimal server deployment). Clearing the key
(Settings -> "Remove key") returns to the daemon route.

Either way, Ollama Cloud usage beyond a model's free tier is a paid
service - check `https://ollama.com/settings` before relying on it for a
demo.

### Troubleshooting cloud models

The investigation trace tells you exactly what went wrong ("AI analysis
failed: ..."), and the investigation still completes with all non-LLM
evidence. Common cases seen during development:

| Symptom | Meaning | Fix |
|---|---|---|
| `Ollama Cloud rejected the API key (401)` (direct API) | The REST key is invalid/revoked. `https://ollama.com/api/tags` returns 200 even without a valid key, so only a chat call proves a key works. | Generate a new key at ollama.com/settings/keys, or remove the key to use the daemon route |
| `this model is not included in your free usage` (402) | That `:cloud` model needs paid credits on your account. | Pick another `:cloud` model (`gpt-oss:120b-cloud` was on the free tier at the time of writing) or a local model |
| Every request takes ~2 s longer than expected | `OLLAMA_BASE_URL` uses `localhost` on Windows (IPv6-first). | Use `http://127.0.0.1:11434` |

The Settings page (`PATCH /api/settings/llm`) switches provider/model at
runtime and persists the choice to `.env`, so you can recover from any of
these without restarting the backend.

## What to download / add on your own

Everything required for the golden-path demo is bundled. Optional
additions you may want for a more complete deployment:

- **VirusTotal API key** (`VIRUSTOTAL_API_KEY`) - free tier available at
  virustotal.com - enables real IP/domain/hash reputation lookups in
  addition to the bundled local synthetic threat intel data.
- **NVD API key** (`NVD_API_KEY`) - optional, increases the NVD CVE API's
  rate limit; CVE lookups work without a key at a lower rate limit.
- **Knowledge base documents** - `scripts\download_knowledge_base.ps1 -All`
  pulls MITRE ATT&CK, the NIST PDFs (SP 800-61r3, CSF 2.0, SP 800-92),
  OWASP, CWE, CISA KEV and recent NVD CVEs. Several hand-written playbooks
  are still to be written (listed in `data/knowledge_base/README.md`,
  together with how to add your own documents or PDFs).
- **Windows Security logs** - export them on the Windows host and upload the
  JSON on the Logs page (the brute-force rules apply to Windows logons too):

  ```powershell
  Get-WinEvent -FilterHashtable @{LogName='Security'; Id=4624,4625,4740} -MaxEvents 500 |
      Select-Object Id, TimeCreated, MachineName, Message |
      ConvertTo-Json -Depth 3 | Out-File security_events.json -Encoding utf8
  ```

  A synthetic export is bundled at `data/sample_logs/windows_security_events.json`.
- **A larger/faster local LLM**, or an Ollama Cloud subscription, if you
  want faster or higher-quality AI analysis than the default.
