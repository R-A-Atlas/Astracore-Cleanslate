import time

from fastapi.testclient import TestClient

from app.server.main import app


def _client_with_tmp_auth_store(monkeypatch, tmp_path):
    monkeypatch.setenv("ASTRACORE_AUTH_SECRET", "test-secret")
    monkeypatch.setenv("ASTRACORE_AUTH_USERS_FILE", str(tmp_path / "users.json"))
    monkeypatch.setenv("ASTRACORE_AUTH_RESET_FILE", str(tmp_path / "resets.json"))
    monkeypatch.setenv("ASTRACORE_AUTH_ACCESS_TTL_SEC", "3600")
    monkeypatch.setenv("ASTRACORE_AUTH_RESET_TTL_SEC", "120")
    monkeypatch.setenv("ASTRACORE_AUTH_OAUTH_STATE_TTL_SEC", "120")
    monkeypatch.setenv("ASTRACORE_AUTH_OAUTH_STATES_FILE", str(tmp_path / "oauth_states.json"))
    monkeypatch.setenv("ASTRACORE_AUTH_OAUTH_LINKS_FILE", str(tmp_path / "oauth_links.json"))
    return TestClient(app)


def test_signup_login_and_me(monkeypatch, tmp_path):
    with _client_with_tmp_auth_store(monkeypatch, tmp_path) as c:
        signup = c.post("/api/auth/signup", json={"email": "User@Example.com", "password": "password123"})
        assert signup.status_code == 200
        token = signup.json()["access_token"]

        me = c.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me.status_code == 200
        assert me.json()["email"] == "user@example.com"

        bad_login = c.post("/api/auth/login", json={"email": "user@example.com", "password": "wrong"})
        assert bad_login.status_code == 401
        assert bad_login.json()["detail"]["code"] == "auth_invalid_credentials"

        good_login = c.post("/api/auth/login", json={"email": "user@example.com", "password": "password123"})
        assert good_login.status_code == 200
        assert good_login.json()["token_type"] == "bearer"


def test_password_reset_request_confirm_and_one_time_use(monkeypatch, tmp_path):
    with _client_with_tmp_auth_store(monkeypatch, tmp_path) as c:
        c.post("/api/auth/signup", json={"email": "u2@example.com", "password": "password123"})

        req = c.post("/api/auth/password-reset/request", json={"email": "u2@example.com"})
        assert req.status_code == 200
        token = req.json()["reset_token"]
        assert token

        confirm = c.post(
            "/api/auth/password-reset/confirm",
            json={"token": token, "new_password": "newpassword123"},
        )
        assert confirm.status_code == 200

        reused = c.post(
            "/api/auth/password-reset/confirm",
            json={"token": token, "new_password": "anotherpass123"},
        )
        assert reused.status_code == 400
        assert reused.json()["detail"]["code"] == "auth_reset_used"

        old_login = c.post("/api/auth/login", json={"email": "u2@example.com", "password": "password123"})
        assert old_login.status_code == 401

        new_login = c.post("/api/auth/login", json={"email": "u2@example.com", "password": "newpassword123"})
        assert new_login.status_code == 200


def test_password_reset_expiry(monkeypatch, tmp_path):
    monkeypatch.setenv("ASTRACORE_AUTH_SECRET", "test-secret")
    monkeypatch.setenv("ASTRACORE_AUTH_USERS_FILE", str(tmp_path / "users.json"))
    monkeypatch.setenv("ASTRACORE_AUTH_RESET_FILE", str(tmp_path / "resets.json"))
    monkeypatch.setenv("ASTRACORE_AUTH_RESET_TTL_SEC", "60")

    from app.security import auth as auth_module

    now = int(time.time())
    with TestClient(app) as c:
        c.post("/api/auth/signup", json={"email": "u3@example.com", "password": "password123"})
        token = c.post("/api/auth/password-reset/request", json={"email": "u3@example.com"}).json()["reset_token"]

    resets = auth_module._load_json(auth_module._resets_path(), {})
    resets[token]["exp"] = now - 1
    auth_module._save_json(auth_module._resets_path(), resets)

    with TestClient(app) as c:
        expired = c.post(
            "/api/auth/password-reset/confirm",
            json={"token": token, "new_password": "newpassword123"},
        )
        assert expired.status_code == 400
        assert expired.json()["detail"]["code"] == "auth_reset_expired"


def test_me_requires_bearer(monkeypatch, tmp_path):
    with _client_with_tmp_auth_store(monkeypatch, tmp_path) as c:
        r = c.get("/api/auth/me")
        assert r.status_code == 401
        assert r.json()["detail"]["code"] == "auth_missing_bearer"


def test_oauth_state_validation_and_reuse_rejection(monkeypatch, tmp_path):
    with _client_with_tmp_auth_store(monkeypatch, tmp_path) as c:
        start = c.post("/api/auth/oauth/github/start", json={"link_account": False})
        assert start.status_code == 200
        state = start.json()["state"]

        invalid = c.post(
            "/api/auth/oauth/github/callback",
            json={"state": "bad", "code": "abc", "github_user_id": "gh_1"},
        )
        assert invalid.status_code == 400
        assert invalid.json()["detail"]["code"] == "oauth_state_invalid"

        first = c.post(
            "/api/auth/oauth/github/callback",
            json={"state": state, "code": "abc", "github_user_id": "gh_1"},
        )
        assert first.status_code == 401
        assert first.json()["detail"]["code"] == "oauth_account_not_linked"

        reused = c.post(
            "/api/auth/oauth/github/callback",
            json={"state": state, "code": "abc", "github_user_id": "gh_1"},
        )
        assert reused.status_code == 400
        assert reused.json()["detail"]["code"] == "oauth_state_used"


def test_oauth_link_then_login_and_conflict(monkeypatch, tmp_path):
    with _client_with_tmp_auth_store(monkeypatch, tmp_path) as c:
        token_a = c.post("/api/auth/signup", json={"email": "a@example.com", "password": "password123"}).json()["access_token"]
        token_b = c.post("/api/auth/signup", json={"email": "b@example.com", "password": "password123"}).json()["access_token"]

        missing_auth = c.post("/api/auth/oauth/github/start", json={"link_account": True})
        assert missing_auth.status_code == 401
        assert missing_auth.json()["detail"]["code"] == "auth_missing_bearer"

        start_link = c.post(
            "/api/auth/oauth/github/start",
            json={"link_account": True},
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert start_link.status_code == 200
        state_a = start_link.json()["state"]

        linked = c.post(
            "/api/auth/oauth/github/callback",
            json={"state": state_a, "code": "code1", "github_user_id": "gh_conflict"},
        )
        assert linked.status_code == 200
        assert linked.json()["mode"] == "link"

        start_login = c.post("/api/auth/oauth/github/start", json={"link_account": False})
        state_login = start_login.json()["state"]
        login = c.post(
            "/api/auth/oauth/github/callback",
            json={"state": state_login, "code": "code2", "github_user_id": "gh_conflict"},
        )
        assert login.status_code == 200
        assert login.json()["email"] == "a@example.com"
        assert login.json()["token_type"] == "bearer"

        start_link_b = c.post(
            "/api/auth/oauth/github/start",
            json={"link_account": True},
            headers={"Authorization": f"Bearer {token_b}"},
        )
        state_b = start_link_b.json()["state"]
        conflict = c.post(
            "/api/auth/oauth/github/callback",
            json={"state": state_b, "code": "code3", "github_user_id": "gh_conflict"},
        )
        assert conflict.status_code == 409
        assert conflict.json()["detail"]["code"] == "oauth_link_conflict"
