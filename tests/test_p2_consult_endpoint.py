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
                    {"type": "frame", "epoch_ms": 2050, "event": "visual-change-detected", "frame": "f1.png", "source": "frame_ocr"},
                    {"type": "transcript", "epoch_ms": 2100, "text": "breakout breakout setup", "source": "transcript"},
                    {"type": "transcript", "epoch_ms": 2200, "text": "breakout momentum setup", "source": "transcript"},
                ]
            }
        )
    )

    with TestClient(app) as c:
        res_or = c.get(
            "/api/session/s1/consult",
            params={
                "user_id": "u_consult",
                "query": "breakout setup",
                "mode": "or",
                "sort": "score_desc",
                "fields": "text",
                "row_type": "transcript",
                "start_epoch_ms": 1000,
                "min_score": 20,
                "include_context": "true",
                "limit": 1,
                "offset": 0,
            },
        )
        res_page2 = c.get(
            "/api/session/s1/consult",
            params={
                "user_id": "u_consult",
                "query": "breakout setup",
                "mode": "or",
                "row_type": "transcript",
                "start_epoch_ms": 1000,
                "min_score": 20,
                "limit": 1,
                "offset": 1,
            },
        )
        res_and = c.get(
            "/api/session/s1/consult",
            params={"user_id": "u_consult", "query": "breakout setup", "mode": "and", "sort": "time_desc", "row_type": "transcript", "start_epoch_ms": 1000},
        )

    assert res_or.status_code == 200
    body_or = res_or.json()
    assert body_or["status"] == "ok"
    assert body_or["match_count"] == 1
    assert body_or["total_matches"] == 2
    assert body_or["next_offset"] == 1
    assert body_or["filters"]["offset"] == 0
    assert body_or["filters"]["mode"] == "or"
    assert body_or["filters"]["sort"] == "score_desc"
    assert body_or["filters"]["fields"] == ["text"]
    assert body_or["filters"]["min_score"] == 20
    assert body_or["filters"]["include_context"] is True
    assert "context" in body_or["matches"][0]

    assert res_page2.status_code == 200
    body_p2 = res_page2.json()
    assert body_p2["match_count"] == 1
    assert body_p2["total_matches"] == 2
    assert body_p2["next_offset"] is None
    assert body_p2["filters"]["offset"] == 1

    assert res_and.status_code == 200
    body_and = res_and.json()
    assert body_and["match_count"] == 2
    assert body_and["matches"][0]["epoch_ms"] >= body_and["matches"][1]["epoch_ms"]
    assert all("setup" in (m.get("text") or "") for m in body_and["matches"])
    assert body_and["filters"]["mode"] == "and"
    assert body_and["filters"]["sort"] == "time_desc"
    assert body_and["filters"]["row_type"] == "transcript"


def test_session_consult_rejects_bad_row_type_empty_query_bad_mode_bad_sort_bad_fields_bad_score_and_bad_offset():
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
        bad_mode = c.get(
            "/api/session/s2/consult",
            params={"user_id": "u_consult", "query": "x y", "mode": "xor"},
        )
        bad_sort = c.get(
            "/api/session/s2/consult",
            params={"user_id": "u_consult", "query": "x y", "sort": "random"},
        )
        bad_fields = c.get(
            "/api/session/s2/consult",
            params={"user_id": "u_consult", "query": "x y", "fields": "text,audio"},
        )
        bad_score = c.get(
            "/api/session/s2/consult",
            params={"user_id": "u_consult", "query": "x y", "min_score": "999"},
        )
        bad_offset = c.get(
            "/api/session/s2/consult",
            params={"user_id": "u_consult", "query": "x y", "offset": "-1"},
        )

    assert bad_type.status_code == 400
    assert empty_q.status_code == 400
    assert bad_mode.status_code == 400
    assert bad_sort.status_code == 400
    assert bad_fields.status_code == 400
    assert bad_score.status_code == 400
    assert bad_offset.status_code == 400


def test_session_consult_404_without_fusion():
    with TestClient(app) as c:
        res = c.get("/api/session/nope/consult", params={"user_id": "missing", "query": "x"})
    assert res.status_code == 404
