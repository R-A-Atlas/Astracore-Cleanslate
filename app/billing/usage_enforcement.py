from datetime import datetime, timezone

from app.billing.plan_policy import get_policy


USAGE_COUNTS: dict[str, dict[str, int]] = {}
SEAT_REGISTRY: dict[str, set[str]] = {}


def _day_key() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _org_key(user_id: str) -> str:
    return user_id.split(":", 1)[0] if ":" in user_id else user_id


def can_start_session(*, user_id: str, plan: str, operator_key: str) -> tuple[bool, str | None]:
    policy = get_policy(plan)
    day = _day_key()

    org = _org_key(user_id)
    seats = SEAT_REGISTRY.setdefault(org, set())
    seats.add(operator_key)
    if len(seats) > policy.max_seats:
        return False, f"Seat limit exceeded for plan '{policy.name}' ({policy.max_seats})"

    key = f"{user_id}:{day}:{policy.name}"
    bucket = USAGE_COUNTS.setdefault(key, {"started": 0, "committed": 0})
    if bucket["started"] >= policy.max_sessions_per_day:
        return False, f"Daily session limit reached for plan '{policy.name}' ({policy.max_sessions_per_day})"

    return True, None


def mark_session_started(*, user_id: str, plan: str) -> None:
    day = _day_key()
    key = f"{user_id}:{day}:{plan}"
    bucket = USAGE_COUNTS.setdefault(key, {"started": 0, "committed": 0})
    bucket["started"] += 1


def mark_session_committed(*, user_id: str, plan: str) -> None:
    day = _day_key()
    key = f"{user_id}:{day}:{plan}"
    bucket = USAGE_COUNTS.setdefault(key, {"started": 0, "committed": 0})
    bucket["committed"] += 1
