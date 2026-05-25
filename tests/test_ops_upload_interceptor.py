from fastapi.testclient import TestClient

from app.server.main import app


def test_ops_upload_interceptor_endpoint_requires_token_and_returns_shape():
    with TestClient(app) as c:
        unauthorized = c.get("/ops/upload-interceptor")
        assert unauthorized.status_code == 401

        authorized = c.get(
            "/ops/upload-interceptor",
            headers={"x-ops-token": "dev-ops-token"},
        )
        assert authorized.status_code == 200
        payload = authorized.json()

        assert "results_total" in payload
        assert "ready_total" in payload
        assert "failed_total" in payload
        assert "queue_depth" in payload
        assert "processing_sessions" in payload
        assert "recent_failed" in payload
