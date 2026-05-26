from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("utf-8")


def _b64url_decode(value: str) -> bytes:
    pad = "=" * ((4 - len(value) % 4) % 4)
    return base64.urlsafe_b64decode((value + pad).encode("utf-8"))


def _token_secret() -> str:
    return os.getenv("ASTRACORE_AUTH_SECRET", "dev-auth-secret").strip() or "dev-auth-secret"


def sign_payload(payload: dict) -> str:
    payload_json = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    payload_part = _b64url_encode(payload_json.encode("utf-8"))
    sig = hmac.new(_token_secret().encode("utf-8"), payload_part.encode("utf-8"), hashlib.sha256).digest()
    return f"{payload_part}.{_b64url_encode(sig)}"


def verify_token(token: str) -> dict | None:
    if not token or "." not in token:
        return None
    payload_part, sig_part = token.split(".", 1)
    expected = hmac.new(_token_secret().encode("utf-8"), payload_part.encode("utf-8"), hashlib.sha256).digest()
    got = _b64url_decode(sig_part)
    if not hmac.compare_digest(expected, got):
        return None
    payload = json.loads(_b64url_decode(payload_part).decode("utf-8"))
    exp = int(payload.get("exp", 0))
    if exp <= int(time.time()):
        return None
    return payload
