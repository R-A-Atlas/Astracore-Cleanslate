from pathlib import Path

from fastapi.testclient import TestClient

from app.server.main import app


def test_stop_commit_writes_incident_bundle_on_failure(monkeypatch):
    with TestClient(app) as c:
        started = c.post(
            "/api/session/start",
            json={"user_id": "u_inc", "session_id": "s1", "operator_key": "op", "plan": "retail"},
        )
        assert started.status_code == 200

        async def _always_fail(*_args, **_kwargs):
            raise RuntimeError("forced finalize failure")

        monkeypatch.setattr("app.server.routes_sessions.finalize_session_output", _always_fail)

        res = c.post(
            "/api/session/stop-commit",
            json={"user_id": "u_inc", "session_id": "s1", "operator_key": "op"},
        )

        assert res.status_code == 500
        detail = res.json().get("detail", "")
        assert "incident=" in detail
        incident_path = detail.split("incident=", 1)[1]
        assert Path(incident_path).exists()
