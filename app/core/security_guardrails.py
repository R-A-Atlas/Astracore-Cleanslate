from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Deque

from fastapi import Request
from starlette.responses import JSONResponse

from app.core.settings import load_security_settings

_SECURITY = load_security_settings()
OPS_TOKEN_HEADER = _SECURITY.ops_token_header
OPS_API_TOKEN = _SECURITY.ops_token

# Per-IP, per-endpoint rate limit for high-impact write endpoints.
RATE_LIMIT_PER_MIN = _SECURITY.rate_limit_per_min
RATE_LIMIT_WINDOW_SEC = _SECURITY.rate_limit_window_sec
SENSITIVE_PATHS = {
    "/api/session/start",
    "/api/session/stop-commit",
    "/api/upload/part",
}

_REQUEST_WINDOWS: dict[str, Deque[float]] = defaultdict(deque)


def _client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for", "").strip()
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _rate_limited(request: Request) -> tuple[bool, int]:
    if request.url.path not in SENSITIVE_PATHS:
        return False, 0

    ip = _client_ip(request)
    key = f"{request.url.path}:{ip}"
    now = time.time()
    q = _REQUEST_WINDOWS[key]

    while q and now - q[0] > RATE_LIMIT_WINDOW_SEC:
        q.popleft()

    if len(q) >= RATE_LIMIT_PER_MIN:
        retry_after = max(1, int(RATE_LIMIT_WINDOW_SEC - (now - q[0])))
        return True, retry_after

    q.append(now)
    return False, 0


async def ops_auth_and_rate_limit_middleware(request: Request, call_next):
    path = request.url.path

    if path.startswith("/ops"):
        provided = request.headers.get(OPS_TOKEN_HEADER)
        if not OPS_API_TOKEN or provided != OPS_API_TOKEN:
            return JSONResponse(
                status_code=401,
                content={
                    "detail": "Unauthorized: missing or invalid ops token",
                    "required_header": OPS_TOKEN_HEADER,
                },
            )

    limited, retry_after = _rate_limited(request)
    if limited:
        return JSONResponse(
            status_code=429,
            headers={"Retry-After": str(retry_after)},
            content={
                "detail": "Rate limit exceeded for sensitive endpoint",
                "limit_per_min": RATE_LIMIT_PER_MIN,
                "retry_after_seconds": retry_after,
            },
        )

    return await call_next(request)
