import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.server.main import app


def test_stop_commit_writes_transcript_artifact(monkeypatch):
    with TestClient(app) as c:
        started = c.post(
            "/api/session/start",
            json={"user_id": "u_p2", "session_id": "s1", "operator_key": "op", "plan": "retail"},
        )
        assert started.status_code == 200

        async def _ok_finalize(*_args, **_kwargs):
            return "/tmp/final.webm"

        async def _ok_process(*_args, **_kwargs):
            return {"audio": "/tmp/fake.mp3", "frames": ["/tmp/f1.png"]}

        def _fake_transcribe(_audio):
            return [{"start_ms": 0, "end_ms": 1000, "text": "hello"}]

        monkeypatch.setattr("app.server.routes_sessions.finalize_session_output", _ok_finalize)
        monkeypatch.setattr("app.server.routes_sessions.process_session", _ok_process)
        monkeypatch.setattr("app.server.routes_sessions.transcribe_audio", _fake_transcribe)
        monkeypatch.setattr("app.server.routes_sessions.extract_frame_events", lambda *_: [{"x": 1}])
        monkeypatch.setattr("app.server.routes_sessions.build_event_rows", lambda *_: [{"epoch_ms": 1}])
        monkeypatch.setattr("app.server.routes_sessions.infer_behavior_tags", lambda *_: [])
        monkeypatch.setattr("app.server.routes_sessions.build_session_summary", lambda **kwargs: {"ok": True, **kwargs})
        monkeypatch.setattr("app.server.routes_sessions.save_summary", lambda *_: "workspace/outputs/summary.json")
        monkeypatch.setattr("app.server.routes_sessions.build_daily_review", lambda *_: "daily")
        monkeypatch.setattr("app.server.routes_sessions.save_daily_review", lambda *_: "workspace/outputs/daily.md")

        res = c.post(
            "/api/session/stop-commit",
            json={"user_id": "u_p2", "session_id": "s1", "operator_key": "op"},
        )
        assert res.status_code == 200
        transcript_path = Path(res.json()["transcript_path"])
        assert transcript_path.exists()

        payload = json.loads(transcript_path.read_text())
        assert payload["user_id"] == "u_p2"
        assert payload["session_id"] == "s1"
        assert payload["segment_count"] == 1
        assert payload["segments"][0]["text"] == "hello"
