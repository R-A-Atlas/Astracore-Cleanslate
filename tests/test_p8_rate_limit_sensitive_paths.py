from fastapi.testclient import TestClient

from app.core import security_guardrails as sg
from app.server.main import app


def test_sensitive_paths_rate_limited_with_retry_after(monkeypatch):
    monkeypatch.setattr(sg, "RATE_LIMIT_PER_MIN", 1)
    monkeypatch.setattr(sg, "RATE_LIMIT_WINDOW_SEC", 30)
    sg._REQUEST_WINDOWS.clear()

    with TestClient(app) as c:
        start_payload = {
            "user_id": "rate_user",
            "session_id": "s1",
            "operator_key": "opA",
            "plan": "retail",
        }

        first = c.post("/api/session/start", json=start_payload)
        assert first.status_code == 200

        second = c.post("/api/session/start", json=start_payload)
        assert second.status_code == 429
        body = second.json()
        assert body["detail"] == "Rate limit exceeded for sensitive endpoint"
        assert body["limit_per_min"] == 1
        assert int(second.headers["Retry-After"]) >= 1
        assert body["retry_after_seconds"] == int(second.headers["Retry-After"])


def test_rate_limit_applies_to_stop_commit_but_not_health(monkeypatch):
    monkeypatch.setattr(sg, "RATE_LIMIT_PER_MIN", 1)
    monkeypatch.setattr(sg, "RATE_LIMIT_WINDOW_SEC", 30)
    sg._REQUEST_WINDOWS.clear()

    with TestClient(app) as c:
        stop_payload = {
            "user_id": "rate_user_2",
            "session_id": "missing_session",
            "operator_key": "opA",
        }

        first = c.post("/api/session/stop-commit", json=stop_payload)
        assert first.status_code == 404

        second = c.post("/api/session/stop-commit", json=stop_payload)
        assert second.status_code == 429
        assert "Retry-After" in second.headers

        health = c.get("/health")
        assert health.status_code == 200
