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
                    {"type": "transcript", "epoch_ms": 2000, "text": "breakout failed", "source": "transcript"},
                    {"type": "frame", "epoch_ms": 1000, "event": "visual-change-detected", "frame": "f1.png", "source": "frame_ocr"},
                    {"type": "transcript", "epoch_ms": 2100, "text": "breakout breakout setup", "source": "transcript"},
                ]
            }
        )
    )

    with TestClient(app) as c:
        res = c.get(
            "/api/session/s1/consult",
            params={"user_id": "u_consult", "query": "breakout", "row_type": "transcript", "start_epoch_ms": 1000},
        )

    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["match_count"] == 2
    assert body["matches"][0]["epoch_ms"] == 2100
    assert body["matches"][0]["match_score"] >= body["matches"][1]["match_score"]
    assert body["matches"][0]["matched_field"] == "text"
    assert "breakout" in body["matches"][0]["matched_snippet"].lower()
    assert body["filters"]["row_type"] == "transcript"
    assert body["scanned_rows"] >= 1


def test_session_consult_rejects_bad_row_type_and_empty_query():
    fusion_path = Path("workspace/memory/intel/u_consult__s2__fusion_timeline.json")
    fusion_path.parent.mkdir(parents=True, exist_ok=True)
    fusion_path.write_text(json.dumps({"timeline_rows": []}))

    with TestClient(app) as c:
        bad_type = c.get(
            "/api/session/s2/consult",
            params={"user_id": "u_consult", "query": "x", "row_type": "audio"},
        )
        empty_q = c.get(
            "/api/session/s2/consult",
            params={"user_id": "u_consult", "query": "   "},
        )

    assert bad_type.status_code == 400
    assert empty_q.status_code == 400


def test_session_consult_404_without_fusion():
    with TestClient(app) as c:
        res = c.get("/api/session/nope/consult", params={"user_id": "missing", "query": "x"})
    assert res.status_code == 404
