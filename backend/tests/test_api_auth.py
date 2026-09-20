def test_register_and_login(client):
    resp = client.post(
        "/api/auth/register",
        json={"username": "alice", "email": "alice@example.com", "password": "SecurePass1!"},
    )
    assert resp.status_code == 201
    assert resp.json()["role"] == "ADMIN"  # first registered user becomes admin

    login_resp = client.post("/api/auth/login", data={"username": "alice", "password": "SecurePass1!"})
    assert login_resp.status_code == 200
    assert "access_token" in login_resp.json()


def test_login_wrong_password_rejected(client):
    client.post(
        "/api/auth/register",
        json={"username": "bob", "email": "bob@example.com", "password": "SecurePass1!"},
    )
    resp = client.post("/api/auth/login", data={"username": "bob", "password": "wrong"})
    assert resp.status_code == 401


def test_protected_endpoint_requires_auth(client):
    resp = client.get("/api/alerts")
    assert resp.status_code == 401


def test_health_endpoint_no_auth_required(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["checks"]["database"] == "ok"
