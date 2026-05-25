from datetime import datetime, timezone

from app.billing.plan_policy import get_policy


USAGE_COUNTS: dict[str, dict[str, int]] = {}
SEAT_REGISTRY: dict[str, set[str]] = {}

# V1 decision: hard lock once included monthly sessions are exhausted.
# Keep these constants simple so we can switch behavior later.
OVERAGE_MODE = "hard_lock"  # future options: "allow_addon", "metered"
OVERAGE_ADDON_SESSIONS = 0


def _month_key() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _org_key(user_id: str) -> str:
    return user_id.split(":", 1)[0] if ":" in user_id else user_id


def can_start_session(*, user_id: str, plan: str, operator_key: str) -> tuple[bool, str | None]:
    policy = get_policy(plan)
    month = _month_key()

    org = _org_key(user_id)
    seats = SEAT_REGISTRY.setdefault(org, set())
    seats.add(operator_key)
    if len(seats) > policy.max_seats:
        return False, f"Seat limit exceeded for plan '{policy.name}' ({policy.max_seats})"

    key = f"{org}:{month}:{policy.name}"
    bucket = USAGE_COUNTS.setdefault(key, {"started": 0, "committed": 0})
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
    bucket = USAGE_COUNTS.setdefault(key, {"started": 0, "committed": 0})
    bucket["started"] += 1


def mark_session_committed(*, user_id: str, plan: str) -> None:
    month = _month_key()
    org = _org_key(user_id)
    key = f"{org}:{month}:{plan}"
    bucket = USAGE_COUNTS.setdefault(key, {"started": 0, "committed": 0})
    bucket["committed"] += 1
