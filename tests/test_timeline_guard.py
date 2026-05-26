from fastapi.testclient import TestClient

from app.server.main import app


def test_stop_commit_fails_on_timeline_drift(monkeypatch):
    with TestClient(app) as c:
        started = c.post(
            "/api/session/start",
            json={"user_id": "u_drift", "session_id": "s1", "operator_key": "op", "plan": "retail"},
        )
        assert started.status_code == 200

        async def _fake_finalize(user_id: str, session_id: str):
            return "/tmp/fake_final.webm"

        async def _fake_process(video_path: str, captures_dir: str):
            return {"audio": "/tmp/fake.mp3", "frames": ["/tmp/f1.png", "/tmp/f2.png"]}

        def _fake_transcribe(_audio):
            return ["line1", "line2"]

        def _fake_extract(_frames):
            return [{"f": 1}, {"f": 2}]

        def _fake_event_rows(_t, _f):
            return [{"epoch_ms": 1_000}, {"epoch_ms": 40_500}]  # >30s drift

        def _fake_behavior(_t, _f):
            return ["discipline"]

        def _fake_summary(**kwargs):
            return {"ok": True, **kwargs}

        def _fake_save_summary(_u, _s, _summary):
            return "workspace/outputs/summary.json"

        def _fake_daily(_summary):
            return "daily"

        def _fake_daily_save(_daily):
            return "workspace/outputs/daily.md"

        monkeypatch.setattr("app.server.routes_sessions.finalize_session_output", _fake_finalize)
        monkeypatch.setattr("app.server.routes_sessions.process_session", _fake_process)
        monkeypatch.setattr("app.server.routes_sessions.transcribe_audio", _fake_transcribe)
        monkeypatch.setattr("app.server.routes_sessions.extract_frame_events", _fake_extract)
        monkeypatch.setattr("app.server.routes_sessions.build_event_rows", _fake_event_rows)
        monkeypatch.setattr("app.server.routes_sessions.infer_behavior_tags", _fake_behavior)
        monkeypatch.setattr("app.server.routes_sessions.build_session_summary", _fake_summary)
        monkeypatch.setattr("app.server.routes_sessions.save_summary", _fake_save_summary)
        monkeypatch.setattr("app.server.routes_sessions.build_daily_review", _fake_daily)
        monkeypatch.setattr("app.server.routes_sessions.save_daily_review", _fake_daily_save)

        res = c.post(
            "/api/session/stop-commit",
            json={"user_id": "u_drift", "session_id": "s1", "operator_key": "op"},
        )

        assert res.status_code == 500
        assert "timeline" in res.json()["detail"].lower()
