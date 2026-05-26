from __future__ import annotations

import json
import os
from collections import Counter
from pathlib import Path

from fastapi import APIRouter, Depends

from app.billing.usage_enforcement import get_usage_status
from app.security.auth import get_current_user
from app.server.schemas_dashboard import DashboardRecentSessionsResponse, DashboardSummaryResponse

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def _sessions_dir() -> Path:
    raw = os.getenv("ASTRACORE_SESSIONS_DIR", "workspace/memory/sessions").strip()
    return Path(raw)


def _intel_dir() -> Path:
    raw = os.getenv("ASTRACORE_INTEL_DIR", "workspace/memory/intel").strip()
    return Path(raw)


def _safe_load_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def _session_files_for_user(user_id: str) -> list[Path]:
    root = _sessions_dir()
    if not root.exists():
        return []
    prefix = f"{user_id}__"
    return sorted([p for p in root.glob(f"{prefix}*.json") if p.is_file()])


def _extract_session_id_from_name(user_id: str, filename: str) -> str:
    # {user}__{session}.json
    prefix = f"{user_id}__"
    if not filename.startswith(prefix) or not filename.endswith(".json"):
        return ""
    return filename[len(prefix) : -len(".json")]


def _latest_session(sessions: list[dict]) -> dict | None:
    if not sessions:
        return None
    return sorted(
        sessions,
        key=lambda s: (str(s.get("updated_at") or ""), str(s.get("session_id") or "")),
        reverse=True,
    )[0]


def _usage_user_key(email: str) -> str:
    # If auth subject already has org:user convention, keep it; otherwise use email directly.
    return email


def _top_behavior_flags(user_id: str, session_ids: list[str], top_n: int = 3) -> list[str]:
    intel = _intel_dir()
    if not intel.exists():
        return []
    counts: Counter[str] = Counter()
    for session_id in session_ids:
        p = intel / f"{user_id}__{session_id}__summary.json"
        if not p.exists():
            continue
        payload = _safe_load_json(p)
        if not isinstance(payload, dict):
            continue
        tags = ((payload.get("behavior") or {}).get("tags") or [])
        for tag in tags:
            if isinstance(tag, dict):
                name = str(tag.get("tag") or "").strip()
                if name:
                    counts[name] += 1
    return [name for name, _ in counts.most_common(top_n)]


@router.get("/summary", response_model=DashboardSummaryResponse)
async def dashboard_summary(user=Depends(get_current_user)):
    user_id = user["email"]
    files = _session_files_for_user(user_id)

    session_rows: list[dict] = []
    for f in files:
        row = _safe_load_json(f)
        if isinstance(row, dict):
            session_rows.append(row)

    latest = _latest_session(session_rows)
    latest_status = str(latest.get("status")) if latest and latest.get("status") is not None else None
    latest_plan = str(latest.get("plan") or "retail") if latest else "retail"

    session_ids = [
        _extract_session_id_from_name(user_id, p.name)
        for p in files
        if _extract_session_id_from_name(user_id, p.name)
    ]

    usage = get_usage_status(user_id=_usage_user_key(user_id), plan=latest_plan)

    return {
        "sessions_count": len(files),
        "latest_session_status": latest_status,
        "top_behavior_flags": _top_behavior_flags(user_id, session_ids),
        "usage_quota_snapshot": usage,
    }


@router.get("/recent-sessions", response_model=DashboardRecentSessionsResponse)
async def dashboard_recent_sessions(user=Depends(get_current_user), limit: int = 10):
    user_id = user["email"]
    files = _session_files_for_user(user_id)

    rows: list[dict] = []
    for p in files:
        data = _safe_load_json(p)
        if not isinstance(data, dict):
            continue
        session_id = _extract_session_id_from_name(user_id, p.name)
        if not session_id:
            continue
        rows.append(
            {
                "session_id": session_id,
                "status": str(data.get("status") or "unknown"),
                "updated_at": data.get("updated_at"),
                "plan": data.get("plan"),
            }
        )

    rows.sort(key=lambda s: (str(s.get("updated_at") or ""), str(s.get("session_id") or "")), reverse=True)
    normalized_limit = max(1, min(int(limit), 50))
    return {"recent_sessions": rows[:normalized_limit]}
