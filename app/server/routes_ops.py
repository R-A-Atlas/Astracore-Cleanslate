import os

from fastapi import APIRouter

from app.core.ops_observability import RECENT_ERRORS, RECENT_REQUESTS, get_ops_metrics
from app.core.security_guardrails import OPS_TOKEN_HEADER, RATE_LIMIT_PER_MIN, RATE_LIMIT_WINDOW_SEC
from app.core.settings import load_runtime_settings
from app.server.routes_sessions import UPLOAD_INTERCEPTOR
from app.server.state import SESSIONS

router = APIRouter(prefix="/ops", tags=["ops"])


@router.get("/status")
async def ops_status():
    by_status: dict[str, int] = {}
    for s in SESSIONS.values():
        by_status[s.status] = by_status.get(s.status, 0) + 1
    return {
        "sessions_total": len(SESSIONS),
        "by_status": by_status,
        "metrics": get_ops_metrics(),
    }


@router.get("/metrics")
async def ops_metrics():
    return get_ops_metrics()


@router.get("/upload-interceptor")
async def ops_upload_interceptor(limit_failed: int = 10):
    rows = UPLOAD_INTERCEPTOR.get_results()
    ready = UPLOAD_INTERCEPTOR.get_ready_results()
    failed = UPLOAD_INTERCEPTOR.get_failed_results()
    processing_sessions = [s.__dict__ for s in SESSIONS.values() if s.status == "processing"]
    return {
        "results_total": len(rows),
        "ready_total": len(ready),
        "failed_total": len(failed),
        "queue_depth": len(processing_sessions),
        "processing_sessions": processing_sessions,
        "recent_failed": failed[-limit_failed:],
    }


@router.get("/config")
async def ops_config():
    runtime = load_runtime_settings()
    token = os.getenv("ASTRACORE_OPS_TOKEN", "").strip()
    return {
        "app": {
            "port": runtime.port,
            "environment": runtime.environment,
        },
        "ops_auth": {
            "header": OPS_TOKEN_HEADER,
            "token_configured": bool(token),
        },
        "rate_limit": {
            "sensitive_endpoints_per_min": RATE_LIMIT_PER_MIN,
            "window_seconds": RATE_LIMIT_WINDOW_SEC,
        },
    }


@router.get("/recent-requests")
async def ops_recent_requests(limit: int = 50):
    rows = list(RECENT_REQUESTS)
    return {"count": len(rows), "rows": rows[-limit:]}


@router.get("/recent-errors")
async def ops_recent_errors(limit: int = 20):
    failed_sessions = [s.__dict__ for s in SESSIONS.values() if s.status == "failed"]
    request_errors = list(RECENT_ERRORS)
    return {
        "failed_sessions_count": len(failed_sessions),
        "request_errors_count": len(request_errors),
        "failed_sessions": failed_sessions[-limit:],
        "request_errors": request_errors[-limit:],
    }
