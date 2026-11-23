"""Real-time features: the live event broker, stream authentication,
agent heartbeats and background (step-by-step) investigations."""
import asyncio
import threading
from datetime import timedelta
from pathlib import Path

from app.agents import investigator as investigator_module
from app.api.routes.stream import format_sse
from app.models.investigation import Investigation
from app.schemas.llm_output import LLMAnalysis
from app.services.ingestion import log_ingestion
from app.services.live_events import LiveEventBroker, issue_stream_ticket, redeem_stream_ticket
from app.utils.time import utc_now

SAMPLE_LOG = Path(__file__).resolve().parent.parent.parent / "data" / "sample_logs" / "auth_brute_force.log"


def _capture(monkeypatch, module) -> list[tuple[str, dict]]:
    published: list[tuple[str, dict]] = []
    monkeypatch.setattr(module, "publish_event", lambda event_type, data: published.append((event_type, data)))
    return published


def _no_llm_or_rag(monkeypatch):
    from app.services.rag.service import RAGSearchResponse
    from app.tools import knowledge_tools

    unavailable = RAGSearchResponse(available=False, results=[], message="disabled in test")
    monkeypatch.setattr(knowledge_tools, "_search", lambda *args, **kwargs: unavailable)
    monkeypatch.setattr(investigator_module, "is_llm_available", lambda: True)
    analysis = LLMAnalysis(
        attack_type="SSH Brute Force", severity="HIGH", confidence=0.9, summary="s",
        evidence=["e"], recommended_actions=["Block the source IP"],
    )
    monkeypatch.setattr(investigator_module, "generate_structured_analysis", lambda prompt: (analysis, None))


def test_broker_delivers_messages_published_from_another_thread():
    broker = LiveEventBroker()

    async def scenario():
        queue = broker.subscribe()
        thread = threading.Thread(target=broker.publish, args=("alert.created", {"id": "a1"}))
        thread.start()
        message = await asyncio.wait_for(queue.get(), timeout=2)
        thread.join()
        broker.unsubscribe(queue)
        return message

    message = asyncio.run(scenario())
    assert message["type"] == "alert.created" and message["data"] == {"id": "a1"}
    assert broker.subscriber_count == 0
    assert format_sse(message).startswith("data: {") and format_sse(message).endswith("\n\n")


def test_stream_tickets_are_single_use():
    ticket = issue_stream_ticket("user-1")
    assert redeem_stream_ticket(ticket) == "user-1"
    assert redeem_stream_ticket(ticket) is None
    assert redeem_stream_ticket("made-up") is None


def test_stream_requires_a_valid_ticket(client, auth_headers):
    assert client.post("/api/stream/ticket").status_code == 401
    assert client.get("/api/stream", params={"ticket": "bogus"}).status_code == 401

    resp = client.post("/api/stream/ticket", headers=auth_headers)
    assert resp.status_code == 200 and resp.json()["ticket"]


def test_ingestion_publishes_alerts_after_commit(client, auth_headers, monkeypatch):
    published = _capture(monkeypatch, log_ingestion)
    client.post(
        "/api/logs/upload",
        headers=auth_headers,
        files={"file": ("auth_brute_force.log", SAMPLE_LOG.read_text(), "text/plain")},
    )
    types = [t for t, _ in published]
    assert types[0] == "logs.ingested"
    rules = {d["detection_rule"] for t, d in published if t == "alert.created"}
    assert {"SSH_BRUTE_FORCE", "FAILED_THEN_SUCCESS"} <= rules
    assert "incident.updated" in types


def test_agent_heartbeat_marks_agent_online(client, auth_headers):
    registered = client.post(
        "/api/agents/register", headers=auth_headers, json={"name": "hb-agent", "hostname": "host1"}
    ).json()
    agents = client.get("/api/agents", headers=auth_headers).json()
    assert agents[0]["connection_status"] == "NEVER_SEEN"

    agent_headers = {"X-Agent-Id": registered["id"], "X-Agent-Key": registered["api_key"]}
    assert client.post("/api/agents/heartbeat", headers={"X-Agent-Id": registered["id"], "X-Agent-Key": "wrong"}).status_code == 401
    assert client.post("/api/agents/heartbeat", headers=agent_headers).status_code == 200

    agents = client.get("/api/agents", headers=auth_headers).json()
    assert agents[0]["connection_status"] == "ONLINE"


def test_agent_connection_status_ages_out():
    from app.schemas.agent import AgentOut

    def status(seconds_ago):
        return AgentOut(
            id="a", name="n", hostname="h", is_active=True, created_at=utc_now(),
            last_seen_at=utc_now() - timedelta(seconds=seconds_ago),
        ).connection_status

    assert status(10) == "ONLINE"
    assert status(300) == "STALE"
    assert status(3600) == "OFFLINE"


def test_investigation_runs_in_background_and_streams_each_step(client, auth_headers, investigate, monkeypatch):
    _no_llm_or_rag(monkeypatch)
    published = _capture(monkeypatch, investigator_module)
    client.post(
        "/api/logs/upload",
        headers=auth_headers,
        files={"file": ("auth_brute_force.log", SAMPLE_LOG.read_text(), "text/plain")},
    )
    alert = next(a for a in client.get("/api/alerts", headers=auth_headers).json() if a["detection_rule"] == "SSH_BRUTE_FORCE")

    investigation = investigate(alert["id"])

    assert investigation["status"] == "COMPLETED" and investigation["completed_at"]
    types = [t for t, _ in published]
    assert types[0] == "investigation.started" and types[-1] == "investigation.completed"
    steps = [d["step"]["action"] for t, d in published if t == "investigation.step"]
    assert steps == [s["action"] for s in investigation["trace"]]
    assert client.get(f"/api/alerts/{alert['id']}", headers=auth_headers).json()["status"] == "INVESTIGATING"


def test_second_request_while_running_does_not_start_a_duplicate(db_session):
    from tests.test_agent_investigator import _make_alert

    alert = _make_alert(db_session)
    first, created_first = investigator_module.start_investigation(db_session, alert)
    second, created_second = investigator_module.start_investigation(db_session, alert)
    assert created_first and not created_second and first.id == second.id


def test_background_job_failure_marks_investigation_failed(db_session, monkeypatch):
    from tests.test_agent_investigator import _make_alert

    alert = _make_alert(db_session)
    investigation, _ = investigator_module.start_investigation(db_session, alert)

    def boom(*args, **kwargs):
        raise RuntimeError("ollama exploded")

    monkeypatch.setattr(investigator_module, "investigate_alert", boom)
    investigator_module.run_investigation_job(db_session.get_bind(), investigation.id)

    db_session.expire_all()
    failed = db_session.get(Investigation, investigation.id)
    assert failed.status == "FAILED" and "ollama exploded" in failed.error_message
