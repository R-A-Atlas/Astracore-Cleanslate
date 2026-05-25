from fastapi import APIRouter

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
    }


@router.get("/recent-errors")
async def ops_recent_errors(limit: int = 20):
    failed = [s.__dict__ for s in SESSIONS.values() if s.status == "failed"]
    return {"count": len(failed), "rows": failed[-limit:]}
