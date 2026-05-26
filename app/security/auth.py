from __future__ import annotations

import hashlib
import json
import os
import secrets
import time
from pathlib import Path

from fastapi import Header, HTTPException

from app.security.tokens import sign_payload, verify_token


def _users_path() -> Path:
    raw = os.getenv("ASTRACORE_AUTH_USERS_FILE", "workspace/memory/auth/users.json").strip()
    return Path(raw)


def _resets_path() -> Path:
    raw = os.getenv("ASTRACORE_AUTH_RESET_FILE", "workspace/memory/auth/reset_tokens.json").strip()
    return Path(raw)


def _access_ttl_sec() -> int:
    try:
        return max(60, int(os.getenv("ASTRACORE_AUTH_ACCESS_TTL_SEC", "3600").strip()))
    except ValueError:
        return 3600


def _reset_ttl_sec() -> int:
    try:
        return max(60, int(os.getenv("ASTRACORE_AUTH_RESET_TTL_SEC", "900").strip()))
    except ValueError:
        return 900


def _load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text())


def _save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, separators=(",", ":"), sort_keys=True))


def _salted_hash(password: str, salt: str) -> str:
    return hashlib.sha256(f"{salt}:{password}".encode("utf-8")).hexdigest()


def create_user(email: str, password: str) -> dict:
    users = _load_json(_users_path(), {})
    norm_email = email.strip().lower()
    if norm_email in users:
        raise HTTPException(status_code=409, detail={"code": "auth_email_exists", "message": "email already exists"})
    salt = secrets.token_hex(16)
    users[norm_email] = {
        "email": norm_email,
        "salt": salt,
        "password_hash": _salted_hash(password, salt),
        "created_at": int(time.time()),
    }
    _save_json(_users_path(), users)
    return {"email": norm_email}


def authenticate_user(email: str, password: str) -> dict | None:
    users = _load_json(_users_path(), {})
    norm_email = email.strip().lower()
    user = users.get(norm_email)
    if not user:
        return None
    if _salted_hash(password, user["salt"]) != user["password_hash"]:
        return None
    return {"email": norm_email}


def issue_access_token(email: str) -> str:
    now = int(time.time())
    payload = {"sub": email, "type": "access", "iat": now, "exp": now + _access_ttl_sec()}
    return sign_payload(payload)


def get_current_user(authorization: str | None = Header(default=None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail={"code": "auth_missing_bearer", "message": "missing bearer token"})
    token = authorization.split(" ", 1)[1].strip()
    payload = verify_token(token)
    if not payload or payload.get("type") != "access" or not payload.get("sub"):
        raise HTTPException(status_code=401, detail={"code": "auth_invalid_token", "message": "invalid or expired token"})
    return {"email": str(payload["sub"]).lower()}


def request_password_reset(email: str) -> str:
    users = _load_json(_users_path(), {})
    norm_email = email.strip().lower()
    if norm_email not in users:
        return ""
    token = secrets.token_urlsafe(24)
    resets = _load_json(_resets_path(), {})
    now = int(time.time())
    resets[token] = {"email": norm_email, "exp": now + _reset_ttl_sec(), "used": False}
    _save_json(_resets_path(), resets)
    return token


def confirm_password_reset(token: str, new_password: str) -> str:
    resets = _load_json(_resets_path(), {})
    item = resets.get(token)
    if not item:
        raise HTTPException(status_code=400, detail={"code": "auth_reset_invalid", "message": "invalid reset token"})
    now = int(time.time())
    if bool(item.get("used")):
        raise HTTPException(status_code=400, detail={"code": "auth_reset_used", "message": "reset token already used"})
    if int(item.get("exp", 0)) <= now:
        raise HTTPException(status_code=400, detail={"code": "auth_reset_expired", "message": "reset token expired"})

    users = _load_json(_users_path(), {})
    email = str(item["email"]).lower()
    user = users.get(email)
    if not user:
        raise HTTPException(status_code=400, detail={"code": "auth_reset_invalid", "message": "invalid reset token"})
    salt = secrets.token_hex(16)
    user["salt"] = salt
    user["password_hash"] = _salted_hash(new_password, salt)
    users[email] = user
    resets[token]["used"] = True
    _save_json(_users_path(), users)
    _save_json(_resets_path(), resets)
    return email
