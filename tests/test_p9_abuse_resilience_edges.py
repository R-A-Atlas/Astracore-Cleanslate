from fastapi.testclient import TestClient

from app.core import security_guardrails as sg
from app.server.main import app


def test_rate_limit_cannot_be_bypassed_by_switching_user_and_session(monkeypatch):
    monkeypatch.setattr(sg, "RATE_LIMIT_PER_MIN", 1)
    monkeypatch.setattr(sg, "RATE_LIMIT_WINDOW_SEC", 30)
    sg._REQUEST_WINDOWS.clear()

    with TestClient(app) as c:
        first = c.post(
            "/api/session/start",
            json={"user_id": "abuse_user_a", "session_id": "s1", "operator_key": "opA", "plan": "retail"},
        )
        assert first.status_code == 200

        second = c.post(
            "/api/session/start",
            json={"user_id": "abuse_user_b", "session_id": "s2", "operator_key": "opB", "plan": "retail"},
        )
        assert second.status_code == 429
        assert second.json()["detail"] == "Rate limit exceeded for sensitive endpoint"


def test_same_session_id_across_users_remains_isolated():
    with TestClient(app) as c:
        started = c.post(
            "/api/session/start",
            json={"user_id": "iso_user_a", "session_id": "shared_session", "operator_key": "opA", "plan": "retail"},
        )
        assert started.status_code == 200

        other_user_stop = c.post(
            "/api/session/stop-commit",
            json={"user_id": "iso_user_b", "session_id": "shared_session", "operator_key": "opA"},
        )
        assert other_user_stop.status_code == 404
        assert other_user_stop.json()["detail"] == "Session not found"


def test_ops_token_rotation_does_not_allow_random_token(monkeypatch):
    monkeypatch.setattr(sg, "OPS_TOKEN_HEADER", "x-ops-token")
    monkeypatch.setattr(sg, "OPS_API_TOKEN", "new-token")
    monkeypatch.setattr(sg, "OPS_API_TOKEN_PREV", "old-token")

    with TestClient(app) as c:
        unauthorized = c.get("/ops/status", headers={"x-ops-token": "old-token-extra"})
        assert unauthorized.status_code == 401

        old_ok = c.get("/ops/status", headers={"x-ops-token": "old-token"})
        assert old_ok.status_code == 200

        new_ok = c.get("/ops/status", headers={"x-ops-token": "new-token"})
        assert new_ok.status_code == 200
