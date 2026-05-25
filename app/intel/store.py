import json
from pathlib import Path

INTEL_DIR = Path("workspace/memory/intel")


def _path(user_id: str, session_id: str) -> Path:
    INTEL_DIR.mkdir(parents=True, exist_ok=True)
    return INTEL_DIR / f"{user_id}__{session_id}__summary.json"


def save_summary(user_id: str, session_id: str, payload: dict) -> str:
    p = _path(user_id, session_id)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=2))
    tmp.replace(p)
    return str(p)
