from pathlib import Path

from fastapi.testclient import TestClient

from app.server.main import app


def test_upload_part_does_not_use_full_read(monkeypatch):
    """Route should stream writes and must not call UploadFile.read()."""

    async def _forbidden_read(self, *args, **kwargs):  # pragma: no cover
        raise RuntimeError("full-read-forbidden")

    monkeypatch.setattr("starlette.datastructures.UploadFile.read", _forbidden_read, raising=True)

    with TestClient(app) as c:
        started = c.post(
            "/api/session/start",
            json={"user_id": "u_stream", "session_id": "s1", "operator_key": "op", "plan": "retail"},
        )
        assert started.status_code == 200

        files = {"file": ("part_01.webm", b"abc123", "video/webm")}
        data = {"user_id": "u_stream", "session_id": "s1", "operator_key": "op", "part_index": "1"}
        res = c.post("/api/upload/part", files=files, data=data)

        assert res.status_code == 200
        payload = res.json()
        assert payload["status"] == "ok"
        assert Path(payload["saved"]).exists()
