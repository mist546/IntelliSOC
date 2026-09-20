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

This embeds every document in `data/knowledge_base/` via Ollama and stores
them in a local persistent Chroma collection at `rag/chroma_db/`. Takes
roughly 1-2 minutes depending on your hardware. Re-run any time you add or
edit knowledge base documents.

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

## 4. SOC endpoint agent (optional, for live log tailing)

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

By default the agent watches `data/sample_logs/auth_brute_force.log` (see
`soc-agent/config.yaml`) since Windows has no native `/var/log/auth.log`.
On a real Linux host, edit `config.yaml`'s `watched_files` to point at
`/var/log/auth.log`, `/var/log/syslog`, `/var/log/apache2/access.log`, etc.

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

There are two independent ways to use a cloud-hosted model instead of a
local one - useful if your machine can't comfortably run a local model, or
you simply want much faster investigations.

### Option A (recommended): local daemon, cloud model - tested and confirmed working

Once you're signed in to the local `ollama` client (`ollama signin`),
cloud-hosted models appear in `ollama list` with a `:cloud` suffix and are
used through the exact same local `/api/generate` endpoint as any local
model - **no code change needed**, just set `OLLAMA_MODEL=<model>:cloud` in
`.env` (e.g. `OLLAMA_MODEL=gpt-oss:120b-cloud`). This was verified during
development with a real end-to-end investigation
(`test_investigation_milestone2.py` run against `gpt-oss:120b-cloud`):
the full investigation - including a real structured AI analysis - completed
in **~15 seconds total**, versus 40-90+ seconds against a local CPU-bound
model. Which specific `:cloud` models are included in your account's free
usage tier (versus requiring paid credits) varies and can only be checked
by trying them; a 402 response ("add usage credits") is returned instantly,
before any generation happens, so checking a model's tier costs nothing.

### Option B: direct API key, no local daemon required

This project also ships a second, independent `OllamaCloudProvider`
(`backend/app/services/llm/ollama_cloud.py`) that talks to
`https://ollama.com` directly with a REST API key
(`OLLAMA_CLOUD_API_KEY`, generated at ollama.com/settings/keys - this is a
*different* credential from the SSH keypair `ollama signin` sets up for the
local CLI) and `LLM_PROVIDER=ollama_cloud`. Use this only if the local
`ollama` daemon isn't available at all (e.g. a minimal server deployment).
This path was implemented and reviewed for correctness but a real
successful generation through it was not tested in this environment (no
API key was available to test with) - Option A above was validated instead
and is the recommended route.

Either way, Ollama Cloud usage beyond a model's free tier is a paid
service - check `https://ollama.com/settings` before relying on it for a
demo.

## What to download / add on your own

Everything required for the golden-path demo is bundled. Optional
additions you may want for a more complete deployment:

- **VirusTotal API key** (`VIRUSTOTAL_API_KEY`) - free tier available at
  virustotal.com - enables real IP/domain/hash reputation lookups in
  addition to the bundled local synthetic threat intel data.
- **NVD API key** (`NVD_API_KEY`) - optional, increases the NVD CVE API's
  rate limit; CVE lookups work without a key at a lower rate limit.
- **More knowledge base documents** - see `docs/rag.md`'s "Extending the
  knowledge base" section.
- **A larger/faster local LLM**, or an Ollama Cloud subscription, if you
  want faster or higher-quality AI analysis than the default.
