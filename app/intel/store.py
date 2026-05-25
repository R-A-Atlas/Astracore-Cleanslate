import json
from datetime import datetime, timezone
from pathlib import Path

INTEL_DIR = Path("workspace/memory/intel")


def _path(user_id: str, session_id: str) -> Path:
    INTEL_DIR.mkdir(parents=True, exist_ok=True)
    return INTEL_DIR / f"{user_id}__{session_id}__summary.json"


def _transcript_path(user_id: str, session_id: str) -> Path:
    INTEL_DIR.mkdir(parents=True, exist_ok=True)
    return INTEL_DIR / f"{user_id}__{session_id}__transcript.json"


def save_summary(user_id: str, session_id: str, payload: dict) -> str:
    p = _path(user_id, session_id)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=2))
    tmp.replace(p)
    return str(p)


def save_transcript(user_id: str, session_id: str, *, audio_path: str | None, segments: list[dict], provider: str = "local_stub") -> str:
    p = _transcript_path(user_id, session_id)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "user_id": user_id,
        "session_id": session_id,
        "provider": provider,
        "audio_path": audio_path,
        "segment_count": len(segments),
        "segments": segments,
    }
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=2))
    tmp.replace(p)
    return str(p)
