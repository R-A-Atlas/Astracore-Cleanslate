#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "[INFO] running private beta smoke flow"

python - <<'PY'
import json
import os
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from app.billing.usage_enforcement import _month_key
from app.server.main import app


def _ok(name: str, extra: str = "") -> None:
    msg = f"[PASS] {name}"
    if extra:
        msg += f" :: {extra}"
    print(msg)


def _fail(name: str, detail: str) -> None:
    print(f"[FAIL] {name} :: {detail}")
    raise SystemExit(1)


def _assert(step: str, cond: bool, detail: str) -> None:
    if not cond:
        _fail(step, detail)


forced = os.getenv("PRIVATE_BETA_SMOKE_FORCE_FAIL_STEP", "").strip().lower()

with tempfile.TemporaryDirectory(prefix="private-beta-smoke-") as td:
    root = Path(td)
    env = {
        "ASTRACORE_AUTH_SECRET": "private-beta-smoke-secret",
        "ASTRACORE_AUTH_USERS_FILE": str(root / "users.json"),
        "ASTRACORE_AUTH_RESET_FILE": str(root / "resets.json"),
        "ASTRACORE_AUTH_OAUTH_STATES_FILE": str(root / "oauth_states.json"),
        "ASTRACORE_AUTH_OAUTH_LINKS_FILE": str(root / "oauth_links.json"),
        "ASTRACORE_USER_SETTINGS_FILE": str(root / "user_settings.json"),
        "ASTRACORE_SESSIONS_DIR": str(root / "sessions"),
        "ASTRACORE_INTEL_DIR": str(root / "intel"),
        "ASTRACORE_GOOGLE_OAUTH_CLIENT_ID": "private-beta-local-client",
        "ASTRACORE_GOOGLE_OAUTH_REDIRECT_URI": "http://localhost/private-beta-callback",
        "ASTRACORE_BILLING_SUBSCRIPTIONS_FILE": str(root / "subscriptions.json"),
    }

    prev = {k: os.environ.get(k) for k in env}
    os.environ.update(env)
    try:
        with TestClient(app) as c:
            email = "private-beta@example.com"
            password = "password123"

            signup = c.post("/api/auth/signup", json={"email": email, "password": password})
            _assert("signup", signup.status_code == 200, f"status={signup.status_code} body={signup.text}")
            signup_token = signup.json().get("access_token", "")
            _assert("signup", bool(signup_token), "missing access_token")
            _ok("signup", email)
            if forced == "signup":
                _fail("signup", "forced failure")

            login = c.post("/api/auth/login", json={"email": email, "password": password})
            _assert("login", login.status_code == 200, f"status={login.status_code} body={login.text}")
            token = login.json().get("access_token", "")
            _assert("login", bool(token), "missing access_token")
            authz = {"Authorization": f"Bearer {token}"}
            _ok("login")
            if forced == "login":
                _fail("login", "forced failure")

            gstart = c.post("/api/auth/oauth/google/start", json={"link_account": False})
            _assert("google_start", gstart.status_code == 200, f"status={gstart.status_code} body={gstart.text}")
            state = gstart.json().get("state", "")
            _assert("google_start", bool(state), "missing state")
            _ok("google_start")

            gcallback = c.post(
                "/api/auth/oauth/google/callback",
                json={"state": state, "code": "local-google:pb-sub:private-beta@example.com"},
            )
            _assert("google_callback", gcallback.status_code == 200, f"status={gcallback.status_code} body={gcallback.text}")
            _assert("google_callback", gcallback.json().get("mode") == "login", f"unexpected mode={gcallback.json().get('mode')}")
            _ok("google_callback")

            dashboard = c.get("/api/dashboard/summary", headers=authz)
            _assert("dashboard_summary", dashboard.status_code == 200, f"status={dashboard.status_code} body={dashboard.text}")
            _ok("dashboard_summary")

            settings_payload = {
                "profile": {"name": "Private Beta User", "timezone": "UTC"},
                "experience": {"coach_tone": "direct", "coaching_preferences": ["weekly recap"]},
                "privacy": {"retention_days": 30, "export_request": False},
            }
            ssave = c.put("/api/settings/me", json=settings_payload, headers=authz)
            _assert("settings_save", ssave.status_code == 200, f"status={ssave.status_code} body={ssave.text}")
            _assert("settings_save", ssave.json() == settings_payload, "saved payload mismatch")
            _ok("settings_save")

            sload = c.get("/api/settings/me", headers=authz)
            _assert("settings_load", sload.status_code == 200, f"status={sload.status_code} body={sload.text}")
            _assert("settings_load", sload.json() == settings_payload, "loaded payload mismatch")
            _ok("settings_load")

            usage_path = root / "usage_counts.json"
            month = _month_key()
            usage_key = f"{email}:{month}:retail"
            usage_path.write_text(json.dumps({usage_key: {"started": 300, "committed": 0}}))
            os.environ["ASTRACORE_BILLING_USAGE_FILE"] = str(usage_path)

            import app.billing.usage_enforcement as ue
            ue.USAGE_STORE_PATH = usage_path
            ue.SEATS_STORE_PATH = root / "seat_registry.json"

            blocked = c.post(
                "/api/session/start",
                json={"user_id": email, "session_id": "s-limit", "operator_key": "op-1", "plan": "retail"},
            )
            _assert("billing_enforcement", blocked.status_code == 403, f"status={blocked.status_code} body={blocked.text}")
            _assert(
                "billing_enforcement",
                "Monthly session limit reached" in blocked.text,
                "missing monthly limit message",
            )
            _ok("billing_enforcement")

            print("SMOKE_OK private beta gate")
    finally:
        for k, v in prev.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
PY
