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
                    {"type": "transcript", "epoch_ms": 2200, "text": "action item assigned to owner after breakout setup", "source": "transcript"},
                    {"type": "transcript", "epoch_ms": 2300, "text": "task completed and status updated", "source": "transcript"},
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
                "min_token_hits": 2,
                "min_coverage_pct": 100,
                "row_type": "transcript",
                "start_epoch_ms": 1000,
                "min_score": 20,
                "include_context": "true",
                "include_follow_through": "true",
                "follow_through_window_ms": 1500,
                "follow_through_min_confidence": 0.7,
                "follow_through_signal_types": "task_completed,status_change",
                "debug": "true",
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
        res_ft_floor = c.get(
            "/api/session/s1/consult",
            params={
                "user_id": "u_consult",
                "query": "breakout setup",
                "mode": "or",
                "row_type": "transcript",
                "include_follow_through": "true",
                "sort": "follow_through_desc",
                "min_follow_through_score": 50,
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
    assert body_or["stats"]["max_score"] >= body_or["stats"]["avg_score"]
    assert body_or["stats"]["token_coverage_pct"] == 100.0
    assert body_or["filters"]["offset"] == 0
    assert body_or["filters"]["mode"] == "or"
    assert body_or["filters"]["sort"] == "score_desc"
    assert body_or["filters"]["fields"] == ["text"]
    assert body_or["filters"]["min_token_hits"] == 2
    assert body_or["filters"]["min_coverage_pct"] == 100
    assert body_or["filters"]["min_score"] == 20
    assert body_or["filters"]["min_follow_through_score"] == 0
    assert body_or["filters"]["follow_through_window_ms"] == 1500
    assert body_or["filters"]["follow_through_min_confidence"] == 0.7
    assert body_or["filters"]["follow_through_signal_types"] == ["status_change", "task_completed"]
    assert body_or["filters"]["include_follow_through"] is True
    assert body_or["filters"]["include_context"] is True
    assert body_or["filters"]["debug"] is True
    assert "debug_counts" in body_or
    assert "debug_counts_scoped" in body_or
    assert "debug_stage_pass" in body_or
    assert body_or["debug_counts"]["query_mode"] >= 0
    assert body_or["debug_counts"]["min_follow_through_score"] >= 0
    assert body_or["debug_counts_scoped"]["query_mode"] >= 0
    assert body_or["debug_counts_scoped"]["min_follow_through_score"] >= 0
    assert body_or["debug_stage_pass"]["after_min_follow_through_score"] == body_or["total_matches"]
    assert "context" in body_or["matches"][0]
    assert body_or["matches"][0]["matched_tokens"] == ["breakout", "setup"]
    assert "follow_through" in body_or["matches"][0]
    assert "follow_through_stats" in body_or
    assert body_or["follow_through_stats"]["max_score"] >= body_or["follow_through_stats"]["avg_score"]
    assert body_or["follow_through_stats"]["signal_count"] >= 1
    assert body_or["follow_through_stats"]["signal_type_counts"]["task_completed"] >= 1
    assert body_or["follow_through_stats"]["signal_type_counts"]["task_created"] == 0
    assert body_or["matches"][0]["follow_through"]["score"] > 0
    ft_signals = body_or["matches"][0]["follow_through"]["signals"]
    assert ft_signals == sorted(ft_signals, key=lambda s: s["epoch_ms"])
    assert all(float(s["confidence"]) >= 0.7 for s in ft_signals)
    assert all(str(s["signal_type"]) in {"task_completed", "status_change"} for s in ft_signals)

    assert res_page2.status_code == 200
    body_p2 = res_page2.json()
    assert body_p2["match_count"] == 1
    assert body_p2["total_matches"] == 2
    assert body_p2["stats"]["token_coverage_pct"] == 100.0
    assert "debug_counts" not in body_p2
    assert "debug_counts_scoped" not in body_p2
    assert "debug_stage_pass" not in body_p2
    assert "follow_through_stats" not in body_p2
    assert "follow_through" not in body_p2["matches"][0]
    assert body_p2["next_offset"] is None
    assert body_p2["filters"]["offset"] == 1

    assert res_ft_floor.status_code == 200
    body_ft = res_ft_floor.json()
    assert body_ft["total_matches"] == 2
    assert body_ft["match_count"] == 2
    assert body_ft["filters"]["min_follow_through_score"] == 50
    assert body_ft["filters"]["sort"] == "follow_through_desc"
    assert all(m["follow_through"]["score"] >= 50 for m in body_ft["matches"])
    ft_scores = [m["follow_through"]["score"] for m in body_ft["matches"]]
    assert ft_scores == sorted(ft_scores, reverse=True)

    assert res_and.status_code == 200
    body_and = res_and.json()
    assert body_and["match_count"] == 2
    assert body_and["stats"]["avg_score"] > 0
    assert body_and["stats"]["max_score"] >= body_and["stats"]["avg_score"]
    assert body_and["matches"][0]["epoch_ms"] >= body_and["matches"][1]["epoch_ms"]
    assert body_and["matches"][0]["matched_tokens"] == ["breakout", "setup"]
    assert all("setup" in (m.get("text") or "") for m in body_and["matches"])
    assert body_and["filters"]["mode"] == "and"
    assert body_and["filters"]["sort"] == "time_desc"
    assert body_and["filters"]["row_type"] == "transcript"


def test_session_consult_rejects_bad_row_type_empty_query_bad_mode_bad_sort_bad_fields_bad_min_token_hits_bad_min_coverage_pct_bad_score_bad_min_follow_through_score_bad_follow_through_window_bad_follow_through_min_confidence_bad_follow_through_signal_types_and_bad_offset():
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
        bad_min_token_hits = c.get(
            "/api/session/s2/consult",
            params={"user_id": "u_consult", "query": "x y", "min_token_hits": "0"},
        )
        bad_min_coverage_pct = c.get(
            "/api/session/s2/consult",
            params={"user_id": "u_consult", "query": "x y", "min_coverage_pct": "120"},
        )
        bad_score = c.get(
            "/api/session/s2/consult",
            params={"user_id": "u_consult", "query": "x y", "min_score": "999"},
        )
        bad_min_follow_through_score = c.get(
            "/api/session/s2/consult",
            params={"user_id": "u_consult", "query": "x y", "min_follow_through_score": "120"},
        )
        bad_follow_through_window = c.get(
            "/api/session/s2/consult",
            params={"user_id": "u_consult", "query": "x y", "follow_through_window_ms": "500"},
        )
        bad_follow_through_min_confidence = c.get(
            "/api/session/s2/consult",
            params={"user_id": "u_consult", "query": "x y", "follow_through_min_confidence": "1.2"},
        )
        bad_follow_through_signal_types = c.get(
            "/api/session/s2/consult",
            params={"user_id": "u_consult", "query": "x y", "follow_through_signal_types": "task_created,invalid"},
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
    assert bad_min_token_hits.status_code == 400
    assert bad_min_coverage_pct.status_code == 400
    assert bad_score.status_code == 400
    assert bad_min_follow_through_score.status_code == 400
    assert bad_follow_through_window.status_code == 400
    assert bad_follow_through_min_confidence.status_code == 400
    assert bad_follow_through_signal_types.status_code == 400
    assert bad_offset.status_code == 400


def test_session_consult_404_without_fusion():
    with TestClient(app) as c:
        res = c.get("/api/session/nope/consult", params={"user_id": "missing", "query": "x"})
    assert res.status_code == 404
