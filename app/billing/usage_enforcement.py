from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

from app.billing.plan_policy import get_policy


USAGE_STORE_PATH = Path("workspace/memory/billing/usage_counts.json")
SEATS_STORE_PATH = Path("workspace/memory/billing/seat_registry.json")

OVERAGE_MODE = "hard_lock"  # future options: "allow_addon", "metered"
OVERAGE_ADDON_SESSIONS = 0

_STORE_LOCK = Lock()


def _month_key() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _org_key(user_id: str) -> str:
    return user_id.split(":", 1)[0] if ":" in user_id else user_id


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def _atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True))
    tmp.replace(path)


def _load_usage() -> dict[str, dict[str, int]]:
    with _STORE_LOCK:
        data = _read_json(USAGE_STORE_PATH)
    return {k: {"started": int(v.get("started", 0)), "committed": int(v.get("committed", 0))} for k, v in data.items()}


def _save_usage(payload: dict[str, dict[str, int]]) -> None:
    with _STORE_LOCK:
        _atomic_write_json(USAGE_STORE_PATH, payload)


def _load_seats() -> dict[str, set[str]]:
    with _STORE_LOCK:
        data = _read_json(SEATS_STORE_PATH)
    return {org: set(operators) for org, operators in data.items()}


def _save_seats(payload: dict[str, set[str]]) -> None:
    serializable = {org: sorted(list(operators)) for org, operators in payload.items()}
    with _STORE_LOCK:
        _atomic_write_json(SEATS_STORE_PATH, serializable)


def can_start_session(*, user_id: str, plan: str, operator_key: str) -> tuple[bool, str | None]:
    policy = get_policy(plan)
    month = _month_key()

    org = _org_key(user_id)
    seats_by_org = _load_seats()
    seats = seats_by_org.setdefault(org, set())
    seats.add(operator_key)
    if len(seats) > policy.max_seats:
        return False, f"Seat limit exceeded for plan '{policy.name}' ({policy.max_seats})"
    _save_seats(seats_by_org)

    usage = _load_usage()
    key = f"{org}:{month}:{policy.name}"
    bucket = usage.setdefault(key, {"started": 0, "committed": 0})
    included_limit = policy.max_sessions_per_month + OVERAGE_ADDON_SESSIONS
    if bucket["started"] >= included_limit:
        if OVERAGE_MODE == "hard_lock":
            return False, (
                f"Monthly session limit reached for plan '{policy.name}' "
                f"({included_limit}). V1 hard lock is active; overage is disabled."
            )
        return False, (
            f"Monthly session limit reached for plan '{policy.name}' "
            f"({included_limit})."
        )

    return True, None


def mark_session_started(*, user_id: str, plan: str) -> None:
    month = _month_key()
    org = _org_key(user_id)
    key = f"{org}:{month}:{plan}"
    usage = _load_usage()
    bucket = usage.setdefault(key, {"started": 0, "committed": 0})
    bucket["started"] += 1
    _save_usage(usage)


def mark_session_committed(*, user_id: str, plan: str) -> None:
    month = _month_key()
    org = _org_key(user_id)
    key = f"{org}:{month}:{plan}"
    usage = _load_usage()
    bucket = usage.setdefault(key, {"started": 0, "committed": 0})
    bucket["committed"] += 1
    _save_usage(usage)


def get_usage_status(*, user_id: str, plan: str) -> dict:
    policy = get_policy(plan)
    org = _org_key(user_id)
    month = _month_key()
    key = f"{org}:{month}:{policy.name}"

    usage = _load_usage()
    seats_by_org = _load_seats()
    bucket = usage.get(key, {"started": 0, "committed": 0})
    included_limit = policy.max_sessions_per_month + OVERAGE_ADDON_SESSIONS

    return {
        "org": org,
        "plan": policy.name,
        "month": month,
        "started": int(bucket.get("started", 0)),
        "committed": int(bucket.get("committed", 0)),
        "limit": included_limit,
        "remaining": max(0, included_limit - int(bucket.get("started", 0))),
        "active_seats": sorted(list(seats_by_org.get(org, set()))),
        "seat_limit": policy.max_seats,
    }
