import json
from dataclasses import asdict
from pathlib import Path

from app.server.state import SessionState

SESSIONS_DIR = Path("workspace/memory/sessions")


def _path(user_id: str, session_id: str) -> Path:
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    return SESSIONS_DIR / f"{user_id}__{session_id}.json"


def save_session(state: SessionState) -> None:
    p = _path(state.user_id, state.session_id)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(asdict(state), indent=2))
    tmp.replace(p)


def load_session(user_id: str, session_id: str) -> dict | None:
    p = _path(user_id, session_id)
    if not p.exists():
        return None
    return json.loads(p.read_text())
