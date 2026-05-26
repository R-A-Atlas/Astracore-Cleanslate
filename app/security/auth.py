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


def _oauth_states_path() -> Path:
    raw = os.getenv("ASTRACORE_AUTH_OAUTH_STATES_FILE", "workspace/memory/auth/oauth_states.json").strip()
    return Path(raw)


def _oauth_links_path() -> Path:
    raw = os.getenv("ASTRACORE_AUTH_OAUTH_LINKS_FILE", "workspace/memory/auth/oauth_links.json").strip()
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


def _oauth_state_ttl_sec() -> int:
    try:
        return max(60, int(os.getenv("ASTRACORE_AUTH_OAUTH_STATE_TTL_SEC", "600").strip()))
    except ValueError:
        return 600


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


def create_oauth_user(email: str) -> dict:
    users = _load_json(_users_path(), {})
    norm_email = email.strip().lower()
    if norm_email in users:
        return {"email": norm_email}
    users[norm_email] = {
        "email": norm_email,
        "salt": "",
        "password_hash": "",
        "created_at": int(time.time()),
        "oauth_only": True,
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


def issue_oauth_state(*, mode: str, email: str | None = None) -> str:
    if mode not in {"login", "link"}:
        raise HTTPException(status_code=400, detail={"code": "oauth_invalid_mode", "message": "invalid oauth mode"})
    state = secrets.token_urlsafe(32)
    now = int(time.time())
    states = _load_json(_oauth_states_path(), {})
    states[state] = {"mode": mode, "email": email.lower() if email else None, "exp": now + _oauth_state_ttl_sec(), "used": False}
    _save_json(_oauth_states_path(), states)
    return state


def _consume_oauth_state(state: str) -> dict:
    states = _load_json(_oauth_states_path(), {})
    item = states.get(state)
    if not item:
        raise HTTPException(status_code=400, detail={"code": "oauth_state_invalid", "message": "invalid oauth state"})
    now = int(time.time())
    if bool(item.get("used")):
        raise HTTPException(status_code=400, detail={"code": "oauth_state_used", "message": "oauth state already used"})
    if int(item.get("exp", 0)) <= now:
        raise HTTPException(status_code=400, detail={"code": "oauth_state_expired", "message": "oauth state expired"})
    states[state]["used"] = True
    _save_json(_oauth_states_path(), states)
    return item


def complete_github_oauth(*, state: str, code: str, github_user_id: str, github_email: str | None = None) -> dict:
    if not code.strip():
        raise HTTPException(status_code=400, detail={"code": "oauth_code_invalid", "message": "missing oauth code"})
    oauth_state = _consume_oauth_state(state)
    links = _load_json(_oauth_links_path(), {"github": {"by_id": {}, "by_email": {}}})
    gh = links.setdefault("github", {})
    by_id = gh.setdefault("by_id", {})
    by_email = gh.setdefault("by_email", {})
    gh_id = github_user_id.strip()

    if oauth_state["mode"] == "link":
        owner_email = str(oauth_state.get("email") or "").lower()
        if not owner_email:
            raise HTTPException(status_code=400, detail={"code": "oauth_link_invalid_state", "message": "link state missing owner"})
        users = _load_json(_users_path(), {})
        if owner_email not in users:
            raise HTTPException(status_code=400, detail={"code": "oauth_link_user_missing", "message": "link owner missing"})
        existing_owner = by_id.get(gh_id)
        if existing_owner and existing_owner != owner_email:
            raise HTTPException(status_code=409, detail={"code": "oauth_link_conflict", "message": "github account already linked"})
        by_id[gh_id] = owner_email
        by_email[owner_email] = gh_id
        _save_json(_oauth_links_path(), links)
        return {"status": "ok", "mode": "link", "email": owner_email, "github_user_id": gh_id}

    linked_email = by_id.get(gh_id)
    if not linked_email:
        raise HTTPException(status_code=401, detail={"code": "oauth_account_not_linked", "message": "github account is not linked"})
    token = issue_access_token(linked_email)
    return {"status": "ok", "mode": "login", "email": linked_email, "access_token": token, "token_type": "bearer"}


def complete_google_oauth(*, state: str, code: str, google_sub: str, google_email: str) -> dict:
    if not code.strip():
        raise HTTPException(status_code=400, detail={"code": "oauth_code_invalid", "message": "missing oauth code"})
    oauth_state = _consume_oauth_state(state)
    links = _load_json(_oauth_links_path(), {"github": {"by_id": {}, "by_email": {}}, "google": {"by_id": {}, "by_email": {}}})
    gl = links.setdefault("google", {})
    by_id = gl.setdefault("by_id", {})
    by_email = gl.setdefault("by_email", {})
    sub = google_sub.strip()
    email = google_email.strip().lower()

    if oauth_state["mode"] == "link":
        owner_email = str(oauth_state.get("email") or "").lower()
        if not owner_email:
            raise HTTPException(status_code=400, detail={"code": "oauth_link_invalid_state", "message": "link state missing owner"})
        users = _load_json(_users_path(), {})
        if owner_email not in users:
            raise HTTPException(status_code=400, detail={"code": "oauth_link_user_missing", "message": "link owner missing"})
        existing_owner = by_id.get(sub)
        if existing_owner and existing_owner != owner_email:
            raise HTTPException(status_code=409, detail={"code": "oauth_link_conflict", "message": "google account already linked"})
        by_id[sub] = owner_email
        by_email[owner_email] = sub
        _save_json(_oauth_links_path(), links)
        return {"status": "ok", "mode": "link", "email": owner_email, "google_sub": sub}

    linked_email = by_id.get(sub)
    if linked_email:
        token = issue_access_token(linked_email)
        return {"status": "ok", "mode": "login", "email": linked_email, "access_token": token, "token_type": "bearer"}

    users = _load_json(_users_path(), {})
    target_email = email
    if target_email not in users:
        create_oauth_user(target_email)
    by_id[sub] = target_email
    by_email[target_email] = sub
    _save_json(_oauth_links_path(), links)
    token = issue_access_token(target_email)
    return {"status": "ok", "mode": "login", "email": target_email, "access_token": token, "token_type": "bearer"}
