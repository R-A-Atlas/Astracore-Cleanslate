from __future__ import annotations

import os
from urllib.parse import urlencode

from fastapi import HTTPException


def _google_client_id() -> str:
    return os.getenv("ASTRACORE_GOOGLE_OAUTH_CLIENT_ID", "").strip()


def _google_redirect_uri() -> str:
    return os.getenv("ASTRACORE_GOOGLE_OAUTH_REDIRECT_URI", "").strip()


def build_google_authorize_url(state: str) -> str:
    client_id = _google_client_id()
    redirect_uri = _google_redirect_uri()
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "prompt": "select_account",
    }
    return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"


def resolve_google_identity_from_code(code: str) -> dict:
    raw = code.strip()
    # Local deterministic fallback for tests/dev without network calls.
    # Format: local-google:<subject>:<email>
    if raw.startswith("local-google:"):
        parts = raw.split(":", 2)
        if len(parts) != 3 or not parts[1] or "@" not in parts[2]:
            raise HTTPException(status_code=400, detail={"code": "oauth_code_invalid", "message": "invalid local google code"})
        return {"sub": parts[1], "email": parts[2].strip().lower()}

    raise HTTPException(
        status_code=400,
        detail={"code": "oauth_code_exchange_unavailable", "message": "google code exchange unavailable in local mode"},
    )
