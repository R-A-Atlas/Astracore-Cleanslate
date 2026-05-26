from pathlib import Path

from fastapi.testclient import TestClient

from app.billing.plan_keys import reset_plan_validation_metrics
from app.server.main import app


def _client(monkeypatch, tmp_path: Path) -> TestClient:
    monkeypatch.setenv("ASTRACORE_AUTH_SECRET", "test-secret")
    monkeypatch.setenv("ASTRACORE_AUTH_USERS_FILE", str(tmp_path / "users.json"))
    monkeypatch.setenv("ASTRACORE_AUTH_RESET_FILE", str(tmp_path / "resets.json"))
    monkeypatch.setenv("ASTRACORE_AUTH_OAUTH_STATES_FILE", str(tmp_path / "oauth_states.json"))
    monkeypatch.setenv("ASTRACORE_AUTH_OAUTH_LINKS_FILE", str(tmp_path / "oauth_links.json"))
    monkeypatch.setenv("ASTRACORE_BILLING_SUBSCRIPTIONS_FILE", str(tmp_path / "subscriptions.json"))
    monkeypatch.setenv("ASTRACORE_STRIPE_WEBHOOK_SECRET", "whsec_test")
    monkeypatch.setattr("app.billing.usage_enforcement.USAGE_STORE_PATH", tmp_path / "usage.json")
    monkeypatch.setattr("app.billing.usage_enforcement.SEATS_STORE_PATH", tmp_path / "seats.json")
    return TestClient(app)


def _signup_token(c: TestClient, email: str) -> str:
    r = c.post("/api/auth/signup", json={"email": email, "password": "password123"})
    assert r.status_code == 200
    return r.json()["access_token"]


def test_ops_billing_endpoint_reports_plan_validation_metrics(monkeypatch, tmp_path):
    reset_plan_validation_metrics()
    with _client(monkeypatch, tmp_path) as c:
        token = _signup_token(c, "ops-billing@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        ok = c.post("/api/billing/checkout-session", json={"plan": "pro"}, headers=headers)
        assert ok.status_code == 200

        bad = c.post("/api/billing/checkout-session", json={"plan": "moon"}, headers=headers)
        assert bad.status_code == 400

        ops = c.get("/ops/billing", headers={"x-ops-token": "dev-ops-token"})
        assert ops.status_code == 200
        body = ops.json()
        payload = body["plan_validation"]
        assert payload["total_requests"] >= 2
        assert payload["alias_hits"] >= 1
        assert payload["invalid_attempts"] >= 1
        assert "starter" in payload["allowed_aliases"]
        assert "retail" in payload["allowed_backend_plans"]
        assert body["billing_plan_validation_level"] in ("ok", "warning", "critical")


def test_billing_plan_validation_alert_level_flips_to_critical(monkeypatch, tmp_path):
    reset_plan_validation_metrics()
    monkeypatch.setenv("ASTRACORE_ALERT_BILLING_INVALID_WARN", "1")
    monkeypatch.setenv("ASTRACORE_ALERT_BILLING_INVALID_CRIT", "2")

    with _client(monkeypatch, tmp_path) as c:
        token = _signup_token(c, "ops-billing-alerts@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        bad_1 = c.post("/api/billing/checkout-session", json={"plan": "moon"}, headers=headers)
        bad_2 = c.post("/api/billing/checkout-session", json={"plan": "sun"}, headers=headers)
        assert bad_1.status_code == 400
        assert bad_2.status_code == 400

        ops_billing = c.get("/ops/billing", headers={"x-ops-token": "dev-ops-token"})
        assert ops_billing.status_code == 200
        assert ops_billing.json()["billing_plan_validation_level"] == "critical"

        ops_alerts = c.get("/ops/alerts", headers={"x-ops-token": "dev-ops-token"})
        assert ops_alerts.status_code == 200
        checks = ops_alerts.json()["checks"]
        assert checks["billing_plan_validation"]["invalid_attempts"] >= 2
        assert checks["billing_plan_validation"]["level"] == "critical"
