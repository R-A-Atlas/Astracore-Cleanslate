import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.server.main import app


def test_session_consult_reads_fusion_and_filters_matches():
    fusion_path = Path("workspace/memory/intel/u_consult__s1__fusion_timeline.json")
    fusion_path.parent.mkdir(parents=True, exist_ok=True)
    fusion_path.write_text(
        json.dumps(
            {
                "timeline_rows": [
                    {"type": "transcript", "epoch_ms": 0, "text": "price action breakout", "source": "transcript"},
                    {"type": "frame", "epoch_ms": 1000, "event": "visual-change-detected", "frame": "f1.png", "source": "frame_ocr"},
                ]
            }
        )
    )

    with TestClient(app) as c:
        res = c.get("/api/session/s1/consult", params={"user_id": "u_consult", "query": "breakout"})

    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["match_count"] == 1
    assert body["matches"][0]["type"] == "transcript"


def test_session_consult_404_without_fusion():
    with TestClient(app) as c:
        res = c.get("/api/session/nope/consult", params={"user_id": "missing", "query": "x"})
    assert res.status_code == 404
