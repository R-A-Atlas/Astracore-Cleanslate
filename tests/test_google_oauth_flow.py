from fastapi.testclient import TestClient

from app.server.main import app


def _client_with_tmp_auth_store(monkeypatch, tmp_path):
    monkeypatch.setenv("ASTRACORE_AUTH_SECRET", "test-secret")
    monkeypatch.setenv("ASTRACORE_AUTH_USERS_FILE", str(tmp_path / "users.json"))
    monkeypatch.setenv("ASTRACORE_AUTH_RESET_FILE", str(tmp_path / "resets.json"))
    monkeypatch.setenv("ASTRACORE_AUTH_OAUTH_STATE_TTL_SEC", "120")
    monkeypatch.setenv("ASTRACORE_AUTH_OAUTH_STATES_FILE", str(tmp_path / "oauth_states.json"))
    monkeypatch.setenv("ASTRACORE_AUTH_OAUTH_LINKS_FILE", str(tmp_path / "oauth_links.json"))
    monkeypatch.setenv("ASTRACORE_GOOGLE_OAUTH_CLIENT_ID", "google-client")
    monkeypatch.setenv("ASTRACORE_GOOGLE_OAUTH_REDIRECT_URI", "http://localhost/callback")
    return TestClient(app)


def test_google_oauth_rejects_missing_and_invalid_state(monkeypatch, tmp_path):
    with _client_with_tmp_auth_store(monkeypatch, tmp_path) as c:
        missing = c.post("/api/auth/oauth/google/callback", json={"state": "", "code": "local-google:sub1:user@example.com"})
        assert missing.status_code == 422

        invalid = c.post(
            "/api/auth/oauth/google/callback",
            json={"state": "not-real", "code": "local-google:sub1:user@example.com"},
        )
        assert invalid.status_code == 400
        assert invalid.json()["detail"]["code"] == "oauth_state_invalid"


def test_google_oauth_links_existing_email_on_first_login(monkeypatch, tmp_path):
    with _client_with_tmp_auth_store(monkeypatch, tmp_path) as c:
        c.post("/api/auth/signup", json={"email": "person@example.com", "password": "password123"})
        start = c.post("/api/auth/oauth/google/start", json={"link_account": False})
        assert start.status_code == 200
        assert "state=" in start.json()["authorize_url"]

        callback = c.post(
            "/api/auth/oauth/google/callback",
            json={"state": start.json()["state"], "code": "local-google:sub-abc:person@example.com"},
        )
        assert callback.status_code == 200
        body = callback.json()
        assert body["status"] == "ok"
        assert body["mode"] == "login"
        assert body["email"] == "person@example.com"
        assert body["token_type"] == "bearer"


def test_google_oauth_first_time_user_creation_and_state_one_time_use(monkeypatch, tmp_path):
    with _client_with_tmp_auth_store(monkeypatch, tmp_path) as c:
        start = c.post("/api/auth/oauth/google/start", json={"link_account": False})
        state = start.json()["state"]

        callback = c.post(
            "/api/auth/oauth/google/callback",
            json={"state": state, "code": "local-google:new-sub:new-user@example.com"},
        )
        assert callback.status_code == 200
        assert callback.json()["email"] == "new-user@example.com"

        reused = c.post(
            "/api/auth/oauth/google/callback",
            json={"state": state, "code": "local-google:new-sub:new-user@example.com"},
        )
        assert reused.status_code == 400
        assert reused.json()["detail"]["code"] == "oauth_state_used"
