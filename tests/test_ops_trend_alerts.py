from fastapi.testclient import TestClient

from app.server.main import app


def test_ops_trend_and_alerts_endpoints_shape():
    with TestClient(app) as c:
        unauthorized = c.get("/ops/throughput-trend")
        assert unauthorized.status_code == 401

        trend = c.get("/ops/throughput-trend", headers={"x-ops-token": "dev-ops-token"})
        assert trend.status_code == 200
        trend_payload = trend.json()
        assert "window_min" in trend_payload
        assert "requests_per_min" in trend_payload
        assert "error_rate_5xx_pct" in trend_payload

        alerts = c.get("/ops/alerts", headers={"x-ops-token": "dev-ops-token"})
        assert alerts.status_code == 200
        alerts_payload = alerts.json()
        assert "level" in alerts_payload
        assert "checks" in alerts_payload
        assert "error_rate_5xx" in alerts_payload["checks"]
        assert "queue_depth" in alerts_payload["checks"]

        health = c.get("/ops/alerts/health", headers={"x-ops-token": "dev-ops-token"})
        assert health.status_code in (200, 503)
        body = health.json()
        assert body["status"] in ("ok", "degraded")
        assert body["level"] in ("ok", "warning", "critical")
