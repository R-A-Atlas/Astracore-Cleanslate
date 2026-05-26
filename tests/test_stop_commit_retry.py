from fastapi.testclient import TestClient

from app.server.main import app


def test_stop_commit_retries_finalize_once(monkeypatch):
    with TestClient(app) as c:
        started = c.post(
            "/api/session/start",
            json={"user_id": "u_retry", "session_id": "s1", "operator_key": "op", "plan": "retail"},
        )
        assert started.status_code == 200

        calls = {"finalize": 0}

        async def _flaky_finalize(user_id: str, session_id: str):
            calls["finalize"] += 1
            if calls["finalize"] == 1:
                raise RuntimeError("ffmpeg transient")
            return "/tmp/final.webm"

        async def _fake_process(video_path: str, captures_dir: str):
            return {"audio": "/tmp/fake.mp3", "frames": ["/tmp/f1.png"]}

        def _fake_transcribe(_audio):
            return ["line1"]

        def _fake_extract(_frames):
            return [{"f": 1}]

        def _fake_rows(_t, _f):
            return [{"epoch_ms": 1000}, {"epoch_ms": 2000}]

        def _fake_behavior(_t, _f):
            return ["discipline"]

        def _fake_summary(**kwargs):
            return {"ok": True, **kwargs}

        monkeypatch.setattr("app.server.routes_sessions.finalize_session_output", _flaky_finalize)
        monkeypatch.setattr("app.server.routes_sessions.process_session", _fake_process)
        monkeypatch.setattr("app.server.routes_sessions.transcribe_audio", _fake_transcribe)
        monkeypatch.setattr("app.server.routes_sessions.extract_frame_events", _fake_extract)
        monkeypatch.setattr("app.server.routes_sessions.build_event_rows", _fake_rows)
        monkeypatch.setattr("app.server.routes_sessions.infer_behavior_tags", _fake_behavior)
        monkeypatch.setattr("app.server.routes_sessions.build_session_summary", _fake_summary)
        monkeypatch.setattr("app.server.routes_sessions.save_summary", lambda *_: "workspace/outputs/summary.json")
        monkeypatch.setattr("app.server.routes_sessions.build_daily_review", lambda *_: "daily")
        monkeypatch.setattr("app.server.routes_sessions.save_daily_review", lambda *_: "workspace/outputs/daily.md")

        res = c.post(
            "/api/session/stop-commit",
            json={"user_id": "u_retry", "session_id": "s1", "operator_key": "op"},
        )

        assert res.status_code == 200
        assert calls["finalize"] == 2
