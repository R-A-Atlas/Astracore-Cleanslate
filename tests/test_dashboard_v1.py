import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.server.main import app


def _client(monkeypatch, tmp_path: Path) -> TestClient:
    monkeypatch.setenv("ASTRACORE_AUTH_SECRET", "test-secret")
    monkeypatch.setenv("ASTRACORE_AUTH_USERS_FILE", str(tmp_path / "users.json"))
    monkeypatch.setenv("ASTRACORE_AUTH_RESET_FILE", str(tmp_path / "resets.json"))
    monkeypatch.setenv("ASTRACORE_AUTH_OAUTH_STATES_FILE", str(tmp_path / "oauth_states.json"))
    monkeypatch.setenv("ASTRACORE_AUTH_OAUTH_LINKS_FILE", str(tmp_path / "oauth_links.json"))
    monkeypatch.setenv("ASTRACORE_SESSIONS_DIR", str(tmp_path / "sessions"))
    monkeypatch.setenv("ASTRACORE_INTEL_DIR", str(tmp_path / "intel"))
    return TestClient(app)


def _signup_token(c: TestClient, email: str) -> str:
    r = c.post("/api/auth/signup", json={"email": email, "password": "password123"})
    assert r.status_code == 200
    return r.json()["access_token"]


def _write_session(base: Path, user_email: str, session_id: str, *, status: str, updated_at: str, plan: str = "retail") -> None:
    p = base / "sessions"
    p.mkdir(parents=True, exist_ok=True)
    (p / f"{user_email}__{session_id}.json").write_text(
        json.dumps(
            {
                "user_id": user_email,
                "session_id": session_id,
                "operator_key": "op_1",
                "plan": plan,
                "status": status,
                "updated_at": updated_at,
            }
        )
    )


def _write_summary(base: Path, user_email: str, session_id: str, tags: list[str]) -> None:
    p = base / "intel"
    p.mkdir(parents=True, exist_ok=True)
    (p / f"{user_email}__{session_id}__summary.json").write_text(
        json.dumps(
            {
                "user_id": user_email,
                "session_id": session_id,
                "behavior": {"tags": [{"tag": t, "severity": "low"} for t in tags]},
            }
        )
    )


def test_dashboard_summary_and_recent_sessions_happy_path(monkeypatch, tmp_path):
    with _client(monkeypatch, tmp_path) as c:
        token = _signup_token(c, "owner@example.com")

        _write_session(tmp_path, "owner@example.com", "s1", status="ready", updated_at="2026-05-25T10:00:00+00:00")
        _write_session(tmp_path, "owner@example.com", "s2", status="processing", updated_at="2026-05-26T10:00:00+00:00")
        _write_summary(tmp_path, "owner@example.com", "s1", ["discipline-risk-language", "high-activity-session"])
        _write_summary(tmp_path, "owner@example.com", "s2", ["discipline-risk-language"])

        summary = c.get("/api/dashboard/summary", headers={"Authorization": f"Bearer {token}"})
        assert summary.status_code == 200
        payload = summary.json()
        assert payload["sessions_count"] == 2
        assert payload["latest_session_status"] == "processing"
        assert payload["top_behavior_flags"][0] == "discipline-risk-language"
        assert payload["usage_quota_snapshot"]["org"] == "owner@example.com"

        recent = c.get("/api/dashboard/recent-sessions", headers={"Authorization": f"Bearer {token}"})
        assert recent.status_code == 200
        rows = recent.json()["recent_sessions"]
        assert [r["session_id"] for r in rows] == ["s2", "s1"]


def test_dashboard_does_not_leak_cross_user_data(monkeypatch, tmp_path):
    with _client(monkeypatch, tmp_path) as c:
        token_a = _signup_token(c, "a@example.com")
        _signup_token(c, "b@example.com")

        _write_session(tmp_path, "a@example.com", "a1", status="ready", updated_at="2026-05-26T08:00:00+00:00")
        _write_summary(tmp_path, "a@example.com", "a1", ["insufficient-signal"])

        _write_session(tmp_path, "b@example.com", "b1", status="failed", updated_at="2026-05-26T12:00:00+00:00")
        _write_summary(tmp_path, "b@example.com", "b1", ["discipline-risk-language"])

        summary = c.get("/api/dashboard/summary", headers={"Authorization": f"Bearer {token_a}"})
        assert summary.status_code == 200
        payload = summary.json()
        assert payload["sessions_count"] == 1
        assert payload["latest_session_status"] == "ready"
        assert payload["top_behavior_flags"] == ["insufficient-signal"]

        recent = c.get("/api/dashboard/recent-sessions", headers={"Authorization": f"Bearer {token_a}"})
        assert recent.status_code == 200
        rows = recent.json()["recent_sessions"]
        assert len(rows) == 1
        assert rows[0]["session_id"] == "a1"


def test_dashboard_requires_auth(monkeypatch, tmp_path):
    with _client(monkeypatch, tmp_path) as c:
        r = c.get("/api/dashboard/summary")
        assert r.status_code == 401
        assert r.json()["detail"]["code"] == "auth_missing_bearer"
