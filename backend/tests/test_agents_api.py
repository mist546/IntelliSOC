from app.models.log_event import LogEvent


def _register(client, auth_headers, name="del-agent") -> dict:
    resp = client.post("/api/agents/register", headers=auth_headers, json={"name": name, "hostname": "host1"})
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_delete_agent_revokes_key_and_keeps_logs(client, auth_headers, db_session):
    registered = _register(client, auth_headers)
    agent_headers = {"X-Agent-Id": registered["id"], "X-Agent-Key": registered["api_key"]}
    db_session.add(
        LogEvent(
            source="del-agent",
            source_type="auth_log",
            event_type="SSH_LOGIN_FAILED",
            message="Failed password",
            raw_log="Failed password",
            agent_id=registered["id"],
        )
    )
    db_session.commit()

    resp = client.delete(f"/api/agents/{registered['id']}", headers=auth_headers)

    assert resp.status_code == 200
    assert client.get("/api/agents", headers=auth_headers).json() == []
    assert client.post("/api/agents/heartbeat", headers=agent_headers).status_code == 401
    db_session.expire_all()
    log = db_session.query(LogEvent).one()
    assert log.agent_id is None


def test_delete_unknown_agent_returns_404(client, auth_headers):
    assert client.delete("/api/agents/does-not-exist", headers=auth_headers).status_code == 404


def test_delete_agent_requires_admin(client, auth_headers):
    registered = _register(client, auth_headers)
    # auth_headers belongs to the first (ADMIN) user; a second user is an ANALYST.
    client.post(
        "/api/auth/register",
        json={"username": "analyst2", "email": "analyst2@example.com", "password": "TestPass123!"},
    )
    token = client.post("/api/auth/login", data={"username": "analyst2", "password": "TestPass123!"}).json()["access_token"]

    resp = client.delete(f"/api/agents/{registered['id']}", headers={"Authorization": f"Bearer {token}"})

    assert resp.status_code == 403
    assert len(client.get("/api/agents", headers=auth_headers).json()) == 1
