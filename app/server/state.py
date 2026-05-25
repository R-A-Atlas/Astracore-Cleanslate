from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class SessionState:
    user_id: str
    session_id: str
    operator_key: str
    status: str = "started"
    parts_uploaded: int = 0
    merged_video: str | None = None
    audio_path: str | None = None
    frame_count: int = 0
    error: str | None = None
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


SESSIONS: dict[str, SessionState] = {}


def key(user_id: str, session_id: str) -> str:
    return f"{user_id}:{session_id}"
