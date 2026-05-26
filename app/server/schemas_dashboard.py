from pydantic import BaseModel


class DashboardSummaryResponse(BaseModel):
    sessions_count: int
    latest_session_status: str | None
    top_behavior_flags: list[str]
    usage_quota_snapshot: dict


class DashboardRecentSessionEntry(BaseModel):
    session_id: str
    status: str
    updated_at: str | None
    plan: str | None


class DashboardRecentSessionsResponse(BaseModel):
    recent_sessions: list[DashboardRecentSessionEntry]
