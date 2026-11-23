from datetime import timedelta

import app.services.llm.service as llm_service
from app.config import get_settings
from app.models.investigation import Investigation
from app.utils.time import utc_now


def test_ai_status_reports_active_provider(client, auth_headers, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "LLM_PROVIDER", "ollama_cloud")
    monkeypatch.setattr(settings, "OLLAMA_CLOUD_MODEL", "qwen3:4b")
    monkeypatch.setattr(llm_service, "is_llm_available", lambda: True)

    resp = client.get("/api/ai/status", headers=auth_headers)

    assert resp.status_code == 200
    body = resp.json()
    assert body["provider"] == "ollama_cloud"
    assert body["model"] == "qwen3:4b"
    assert body["embedding_model"] == settings.OLLAMA_EMBED_MODEL
    assert body["reachable"] is True


def test_ai_status_requires_auth(client):
    assert client.get("/api/ai/status").status_code == 401


def test_health_checks_cloud_provider_without_local_daemon(client, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "LLM_PROVIDER", "ollama_cloud")
    monkeypatch.setattr(settings, "OLLAMA_CLOUD_API_KEY", "test-key")
    monkeypatch.setattr(settings, "OLLAMA_BASE_URL", "http://127.0.0.1:1")  # nothing listens here

    resp = client.get("/api/health")

    assert resp.json()["checks"]["ollama"] == "ok"


class _FakeTags:
    status_code = 200

    def __init__(self, names):
        self._names = names

    def json(self):
        return {"models": [{"name": n} for n in self._names]}


def test_cloud_provider_without_key_runs_through_local_daemon(monkeypatch):
    from app.services.llm.ollama_cloud import OllamaCloudProvider
    from app.services.llm.ollama_local import OllamaLocalProvider

    settings = get_settings()
    monkeypatch.setattr(settings, "LLM_PROVIDER", "ollama_cloud")
    monkeypatch.setattr(settings, "OLLAMA_CLOUD_MODEL", "gpt-oss:120b-cloud")

    monkeypatch.setattr(settings, "OLLAMA_CLOUD_API_KEY", "")
    provider = llm_service._get_provider()
    assert isinstance(provider, OllamaLocalProvider)
    assert provider.model == "gpt-oss:120b-cloud"

    monkeypatch.setattr(settings, "OLLAMA_CLOUD_API_KEY", "rest-key")
    assert isinstance(llm_service._get_provider(), OllamaCloudProvider)


def test_local_availability_requires_exact_model(monkeypatch):
    import app.services.llm.ollama_local as ollama_local

    monkeypatch.setattr(ollama_local.httpx, "get", lambda *a, **kw: _FakeTags(["gemma4:latest"]))

    assert ollama_local.OllamaLocalProvider(model="gemma4:latest").is_available()
    assert ollama_local.OllamaLocalProvider(model="gemma4").is_available()  # no tag means :latest
    assert not ollama_local.OllamaLocalProvider(model="gemma4:4b").is_available()


def test_health_reports_missing_model(client, monkeypatch):
    import httpx

    settings = get_settings()
    monkeypatch.setattr(settings, "LLM_PROVIDER", "ollama_local")
    monkeypatch.setattr(settings, "OLLAMA_MODEL", "gemma4:4b")
    monkeypatch.setattr(httpx, "get", lambda *a, **kw: _FakeTags(["gemma4:latest"]))

    resp = client.get("/api/health")

    assert resp.json()["checks"]["ollama"].startswith("error: model 'gemma4:4b' not available")


def test_switching_to_cloud_no_longer_requires_api_key(client, auth_headers, monkeypatch):
    import app.api.routes.llm_settings as llm_settings_route

    settings = get_settings()
    monkeypatch.setattr(settings, "LLM_PROVIDER", "ollama_local")
    monkeypatch.setattr(settings, "OLLAMA_CLOUD_API_KEY", "")
    monkeypatch.setattr(llm_settings_route, "update_env_file", lambda *a, **kw: None)  # keep the real .env untouched
    monkeypatch.setattr(llm_service, "is_llm_available", lambda: True)

    resp = client.patch("/api/settings/llm", headers=auth_headers, json={"provider": "ollama_cloud"})

    assert resp.status_code == 200
    assert resp.json()["provider"] == "ollama_cloud"


def test_list_investigations_returns_all_newest_first(client, auth_headers, db_session):
    now = utc_now()
    for i in range(7):
        db_session.add(Investigation(status="COMPLETED", risk_score=float(i), created_at=now - timedelta(minutes=i)))
    db_session.add(Investigation(status="FAILED", created_at=now - timedelta(hours=1)))
    db_session.commit()

    resp = client.get("/api/investigations", headers=auth_headers)

    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 8  # not capped at the dashboard's 5
    assert [item["risk_score"] for item in items[:7]] == [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
    assert set(items[0]) == {"id", "alert_id", "incident_id", "status", "risk_score", "created_at", "completed_at"}

    failed = client.get("/api/investigations", headers=auth_headers, params={"status": "failed"}).json()
    assert [item["status"] for item in failed] == ["FAILED"]
