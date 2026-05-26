import json

from fastapi.testclient import TestClient

from app.server.main import app


def test_session_start_allows_under_limit(tmp_path, monkeypatch):
    monkeypatch.setattr("app.billing.usage_enforcement.USAGE_STORE_PATH", tmp_path / "usage.json")
    monkeypatch.setattr("app.billing.usage_enforcement.SEATS_STORE_PATH", tmp_path / "seats.json")

    with TestClient(app) as c:
        res = c.post(
            "/api/session/start",
            json={"user_id": "orgA:user1", "session_id": "s1", "operator_key": "op1", "plan": "retail"},
        )
        assert res.status_code == 200

        usage = c.get("/api/session/usage-status", params={"user_id": "orgA:user1", "plan": "retail"})
        assert usage.status_code == 200
        payload = usage.json()["usage"]
        assert payload["started"] == 1
        assert payload["remaining"] == payload["limit"] - 1
        assert payload["support"]["ai_support"] == "included"
        assert payload["support"]["queue_tier"] == "standard"
        assert payload["support"]["live_support_scope"] == "bugs_account_only"
        assert payload["support"]["live_support_sla"] == "24-48h"


def test_session_start_blocks_seat_limit(tmp_path, monkeypatch):
    monkeypatch.setattr("app.billing.usage_enforcement.USAGE_STORE_PATH", tmp_path / "usage.json")
    monkeypatch.setattr("app.billing.usage_enforcement.SEATS_STORE_PATH", tmp_path / "seats.json")

    with TestClient(app) as c:
        first = c.post(
            "/api/session/start",
            json={"user_id": "orgB:user1", "session_id": "s1", "operator_key": "op1", "plan": "retail"},
        )
        assert first.status_code == 200

        second = c.post(
            "/api/session/start",
            json={"user_id": "orgB:user2", "session_id": "s2", "operator_key": "op2", "plan": "retail"},
        )
        assert second.status_code == 403
        assert "Seat limit exceeded" in second.json()["detail"]


def test_month_rollover_resets_usage_window(tmp_path, monkeypatch):
    monkeypatch.setattr("app.billing.usage_enforcement.USAGE_STORE_PATH", tmp_path / "usage.json")
    monkeypatch.setattr("app.billing.usage_enforcement.SEATS_STORE_PATH", tmp_path / "seats.json")

    monkeypatch.setattr("app.billing.usage_enforcement._month_key", lambda: "2026-05")

    with TestClient(app) as c:
        started = c.post(
            "/api/session/start",
            json={"user_id": "orgR:user1", "session_id": "s1", "operator_key": "op1", "plan": "retail"},
        )
        assert started.status_code == 200

        may_usage = c.get("/api/session/usage-status", params={"user_id": "orgR:user1", "plan": "retail"}).json()["usage"]
        assert may_usage["month"] == "2026-05"
        assert may_usage["started"] == 1

        monkeypatch.setattr("app.billing.usage_enforcement._month_key", lambda: "2026-06")
        june_usage = c.get("/api/session/usage-status", params={"user_id": "orgR:user1", "plan": "retail"}).json()["usage"]
        assert june_usage["month"] == "2026-06"
        assert june_usage["started"] == 0
        assert june_usage["remaining"] == june_usage["limit"]


def test_session_start_blocks_monthly_limit(tmp_path, monkeypatch):
    usage_path = tmp_path / "usage.json"
    seats_path = tmp_path / "seats.json"
    monkeypatch.setattr("app.billing.usage_enforcement.USAGE_STORE_PATH", usage_path)
    monkeypatch.setattr("app.billing.usage_enforcement.SEATS_STORE_PATH", seats_path)

    usage_path.parent.mkdir(parents=True, exist_ok=True)
    seats_path.parent.mkdir(parents=True, exist_ok=True)

    # Keep seats valid for one operator; exhaust monthly started counter for retail.
    seats_path.write_text(json.dumps({"orgC": ["op1"]}))

    from app.billing.usage_enforcement import _month_key

    month = _month_key()
    usage_key = f"orgC:{month}:retail"
    usage_path.write_text(json.dumps({usage_key: {"started": 300, "committed": 0}}))

    with TestClient(app) as c:
        res = c.post(
            "/api/session/start",
            json={"user_id": "orgC:user1", "session_id": "s1", "operator_key": "op1", "plan": "retail"},
        )
        assert res.status_code == 403
        assert "Monthly session limit reached" in res.json()["detail"]
