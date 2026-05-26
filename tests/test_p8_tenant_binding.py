from fastapi.testclient import TestClient

from app.server.main import app


def test_stop_commit_rejects_operator_mismatch():
    with TestClient(app) as c:
        started = c.post(
            "/api/session/start",
            json={"user_id": "u_bind", "session_id": "s1", "operator_key": "op1", "plan": "retail"},
        )
        assert started.status_code == 200

        res = c.post(
            "/api/session/stop-commit",
            json={"user_id": "u_bind", "session_id": "s1", "operator_key": "op2"},
        )
        assert res.status_code == 403
        assert "Operator binding mismatch" in res.json()["detail"]


def test_upload_part_rejects_operator_mismatch(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with TestClient(app) as c:
        started = c.post(
            "/api/session/start",
            json={"user_id": "u_bind2", "session_id": "s1", "operator_key": "op1", "plan": "retail"},
        )
        assert started.status_code == 200

        files = {"file": ("part.webm", b"fake", "video/webm")}
        data = {
            "user_id": "u_bind2",
            "session_id": "s1",
            "operator_key": "op2",
            "part_index": "1",
        }
        res = c.post("/api/upload/part", files=files, data=data)
        assert res.status_code == 403
        assert "Operator binding mismatch" in res.json()["detail"]
