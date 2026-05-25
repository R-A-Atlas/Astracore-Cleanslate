from fastapi import APIRouter

from app.core.ops_observability import RECENT_ERRORS, RECENT_REQUESTS, get_ops_metrics
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
