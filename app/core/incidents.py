from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INCIDENTS_DIR = Path("workspace/ops/incidents")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)


def write_failure_incident_bundle(*, user_id: str, session_id: str, operator_key: str, stage: str, error: str, state: dict[str, Any] | None = None) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = INCIDENTS_DIR / f"incident_{user_id}_{session_id}_{stamp}.json"
    payload = {
        "created_at": _utc_now(),
        "user_id": user_id,
        "session_id": session_id,
        "operator_key": operator_key,
        "stage": stage,
        "error": error,
        "state": state or {},
    }
    _atomic_write_json(out, payload)
    return str(out)
