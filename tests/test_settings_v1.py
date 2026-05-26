from pathlib import Path

from fastapi.testclient import TestClient

from app.server.main import app


def _client(monkeypatch, tmp_path: Path) -> TestClient:
    monkeypatch.setenv("ASTRACORE_AUTH_SECRET", "test-secret")
    monkeypatch.setenv("ASTRACORE_AUTH_USERS_FILE", str(tmp_path / "users.json"))
    monkeypatch.setenv("ASTRACORE_AUTH_RESET_FILE", str(tmp_path / "resets.json"))
    monkeypatch.setenv("ASTRACORE_AUTH_OAUTH_STATES_FILE", str(tmp_path / "oauth_states.json"))
    monkeypatch.setenv("ASTRACORE_AUTH_OAUTH_LINKS_FILE", str(tmp_path / "oauth_links.json"))
    monkeypatch.setenv("ASTRACORE_USER_SETTINGS_FILE", str(tmp_path / "user_settings.json"))
    return TestClient(app)


def _signup_token(c: TestClient, email: str) -> str:
    r = c.post("/api/auth/signup", json={"email": email, "password": "password123"})
    assert r.status_code == 200
    return r.json()["access_token"]


def _payload(name: str, retention_days: int = 30) -> dict:
    return {
        "profile": {"name": name, "timezone": "America/New_York"},
        "experience": {"coach_tone": "direct", "coaching_preferences": ["short check-ins", "weekly recap"]},
        "privacy": {"retention_days": retention_days, "export_request": False},
    }


def test_settings_requires_auth(monkeypatch, tmp_path):
    with _client(monkeypatch, tmp_path) as c:
        r = c.get("/api/settings/me")
        assert r.status_code == 401


def test_settings_save_load_roundtrip_user_a(monkeypatch, tmp_path):
    with _client(monkeypatch, tmp_path) as c:
        token_a = _signup_token(c, "a@example.com")
        payload = _payload("Alice")

        put_resp = c.put("/api/settings/me", json=payload, headers={"Authorization": f"Bearer {token_a}"})
        assert put_resp.status_code == 200
        assert put_resp.json() == payload

        get_resp = c.get("/api/settings/me", headers={"Authorization": f"Bearer {token_a}"})
        assert get_resp.status_code == 200
        assert get_resp.json() == payload


def test_user_b_cannot_see_user_a_data(monkeypatch, tmp_path):
    with _client(monkeypatch, tmp_path) as c:
        token_a = _signup_token(c, "a@example.com")
        token_b = _signup_token(c, "b@example.com")

        payload_a = _payload("Alice", retention_days=120)
        put_resp = c.put("/api/settings/me", json=payload_a, headers={"Authorization": f"Bearer {token_a}"})
        assert put_resp.status_code == 200

        get_b = c.get("/api/settings/me", headers={"Authorization": f"Bearer {token_b}"})
        assert get_b.status_code == 200
        body_b = get_b.json()
        assert body_b["profile"]["name"] != "Alice"
        assert body_b["privacy"]["retention_days"] == 365


def test_bad_retention_days_rejected(monkeypatch, tmp_path):
    with _client(monkeypatch, tmp_path) as c:
        token_a = _signup_token(c, "a@example.com")
        bad_payload = _payload("Alice", retention_days=0)

        r = c.put("/api/settings/me", json=bad_payload, headers={"Authorization": f"Bearer {token_a}"})
        assert r.status_code == 422
