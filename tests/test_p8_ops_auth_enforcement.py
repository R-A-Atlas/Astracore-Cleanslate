from fastapi.testclient import TestClient

from app.core import security_guardrails as sg
from app.server.main import app

OPS_ENDPOINTS = [
    "/ops/status",
    "/ops/metrics",
    "/ops/upload-interceptor",
    "/ops/throughput-trend",
    "/ops/alerts",
    "/ops/alerts/health",
    "/ops/alerts/healthz",
    "/ops/config",
    "/ops/recent-requests",
    "/ops/recent-errors",
]


def test_all_ops_endpoints_reject_missing_or_invalid_token():
    with TestClient(app) as c:
        for endpoint in OPS_ENDPOINTS:
            missing = c.get(endpoint)
            assert missing.status_code == 401, endpoint
            missing_payload = missing.json()
            assert "missing or invalid ops token" in missing_payload["detail"]
            assert missing_payload["required_header"] == "x-ops-token"

            wrong = c.get(endpoint, headers={"x-ops-token": "wrong-token"})
            assert wrong.status_code == 401, endpoint
            wrong_payload = wrong.json()
            assert "missing or invalid ops token" in wrong_payload["detail"]
            assert wrong_payload["required_header"] == "x-ops-token"


def test_ops_and_non_ops_boundary_behavior():
    with TestClient(app) as c:
        health = c.get("/health")
        assert health.status_code == 200

        status = c.get("/ops/status", headers={"x-ops-token": "dev-ops-token"})
        assert status.status_code == 200
        status_payload = status.json()
        assert "sessions_total" in status_payload
        assert "metrics" in status_payload


def test_ops_token_header_can_be_overridden(monkeypatch):
    monkeypatch.setattr(sg, "OPS_TOKEN_HEADER", "x-internal-ops")
    monkeypatch.setattr(sg, "OPS_API_TOKEN", "rotated-token")
    monkeypatch.setattr(sg, "OPS_API_TOKEN_PREV", "")

    with TestClient(app) as c:
        wrong_header = c.get("/ops/status", headers={"x-ops-token": "rotated-token"})
        assert wrong_header.status_code == 401
        wrong_payload = wrong_header.json()
        assert wrong_payload["required_header"] == "x-internal-ops"

        right_header = c.get("/ops/status", headers={"x-internal-ops": "rotated-token"})
        assert right_header.status_code == 200


def test_ops_token_rotation_accepts_previous_token(monkeypatch):
    monkeypatch.setattr(sg, "OPS_TOKEN_HEADER", "x-ops-token")
    monkeypatch.setattr(sg, "OPS_API_TOKEN", "new-token")
    monkeypatch.setattr(sg, "OPS_API_TOKEN_PREV", "old-token")

    with TestClient(app) as c:
        old_token_req = c.get("/ops/status", headers={"x-ops-token": "old-token"})
        assert old_token_req.status_code == 200

        new_token_req = c.get("/ops/status", headers={"x-ops-token": "new-token"})
        assert new_token_req.status_code == 200

        bad_token_req = c.get("/ops/status", headers={"x-ops-token": "bad-token"})
        assert bad_token_req.status_code == 401
