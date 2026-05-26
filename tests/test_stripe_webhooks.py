from pathlib import Path

from fastapi.testclient import TestClient

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


def test_checkout_requires_auth(monkeypatch, tmp_path):
    with _client(monkeypatch, tmp_path) as c:
        r = c.post("/api/billing/checkout-session", json={"plan": "retail"})
        assert r.status_code == 401


def test_checkout_and_portal_links(monkeypatch, tmp_path):
    with _client(monkeypatch, tmp_path) as c:
        token = _signup_token(c, "paying@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        checkout = c.post("/api/billing/checkout-session", json={"plan": "retail"}, headers=headers)
        assert checkout.status_code == 200
        body = checkout.json()
        assert body["status"] == "ok"
        assert body["checkout_session_id"].startswith("cs_test_")
        assert body["checkout_url"].startswith("https://billing.stripe.local/checkout/")

        portal = c.get("/api/billing/portal-link", headers=headers)
        assert portal.status_code == 200
        assert portal.json()["portal_url"].startswith("https://billing.stripe.local/portal/")


def test_webhook_status_transitions_and_plan_lock(monkeypatch, tmp_path):
    with _client(monkeypatch, tmp_path) as c:
        user_email = "lockme@example.com"

        active = c.post(
            "/api/billing/webhook",
            json={"type": "subscription.active", "data": {"object": {"user_email": user_email, "plan": "retail"}}},
            headers={"x-stripe-webhook-secret": "whsec_test"},
        )
        assert active.status_code == 200
        assert active.json()["updated"] is True
        assert active.json()["status"] == "active"

        allowed = c.post(
            "/api/session/start",
            json={"user_id": user_email, "session_id": "s-active", "operator_key": "op1", "plan": "retail"},
        )
        assert allowed.status_code == 200
        assert allowed.json()["plan"] == "retail"

        past_due = c.post(
            "/api/billing/webhook",
            json={"type": "subscription.past_due", "data": {"object": {"user_email": user_email, "plan": "retail"}}},
            headers={"x-stripe-webhook-secret": "whsec_test"},
        )
        assert past_due.status_code == 200
        assert past_due.json()["status"] == "past_due"

        blocked = c.post(
            "/api/session/start",
            json={"user_id": user_email, "session_id": "s-locked", "operator_key": "op1", "plan": "retail"},
        )
        assert blocked.status_code == 403
        assert "restricted plan lock" in blocked.json()["detail"]


def test_webhook_rejects_bad_secret(monkeypatch, tmp_path):
    with _client(monkeypatch, tmp_path) as c:
        bad = c.post(
            "/api/billing/webhook",
            json={"type": "subscription.active", "data": {"object": {"user_email": "x@example.com", "plan": "retail"}}},
            headers={"x-stripe-webhook-secret": "wrong"},
        )
        assert bad.status_code == 401
