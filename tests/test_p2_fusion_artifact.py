import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.server.main import app


def test_stop_commit_writes_fusion_timeline_artifact(monkeypatch):
    with TestClient(app) as c:
        started = c.post(
            "/api/session/start",
            json={"user_id": "u_fusion", "session_id": "s1", "operator_key": "op", "plan": "retail"},
        )
        assert started.status_code == 200

        async def _ok_finalize(*_args, **_kwargs):
            return "/tmp/final.webm"

        async def _ok_process(*_args, **_kwargs):
            return {"audio": "/tmp/fake.mp3", "frames": ["/tmp/f1.png"]}

        monkeypatch.setattr("app.server.routes_sessions.finalize_session_output", _ok_finalize)
        monkeypatch.setattr("app.server.routes_sessions.process_session", _ok_process)
        monkeypatch.setattr(
            "app.server.routes_sessions.transcribe_audio",
            lambda *_: [{"start_ms": 0, "end_ms": 1000, "text": "hello"}],
        )
        monkeypatch.setattr(
            "app.server.routes_sessions.extract_frame_events",
            lambda *_: [{"index": 0, "frame": "f1.png", "event": "visual-change-detected"}],
        )
        monkeypatch.setattr(
            "app.server.routes_sessions.build_event_rows",
            lambda *_: [
                {"id": "t_0", "type": "transcript", "epoch_ms": 0, "source": "transcript", "text": "hello"},
                {"id": "f_0", "type": "frame", "epoch_ms": 1001, "source": "frame_ocr", "frame": "f1.png"},
            ],
        )
        monkeypatch.setattr("app.server.routes_sessions.infer_behavior_tags", lambda *_: [])
        monkeypatch.setattr("app.server.routes_sessions.build_session_summary", lambda **kwargs: {"ok": True, **kwargs})
        monkeypatch.setattr("app.server.routes_sessions.save_summary", lambda *_: "workspace/outputs/summary.json")
        monkeypatch.setattr("app.server.routes_sessions.build_daily_review", lambda *_: "daily")
        monkeypatch.setattr("app.server.routes_sessions.save_daily_review", lambda *_: "workspace/outputs/daily.md")

        res = c.post(
            "/api/session/stop-commit",
            json={"user_id": "u_fusion", "session_id": "s1", "operator_key": "op"},
        )
        assert res.status_code == 200

        fusion_path = Path(res.json()["fusion_timeline_path"])
        assert fusion_path.exists()

        payload = json.loads(fusion_path.read_text())
        assert payload["user_id"] == "u_fusion"
        assert payload["session_id"] == "s1"
        assert payload["counts"]["timeline_rows"] == 2
        assert payload["timeline_rows"][0]["type"] == "transcript"
