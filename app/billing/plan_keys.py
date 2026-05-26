from __future__ import annotations

BACKEND_PLANS = {"retail", "team", "restricted"}

# UI-facing names/labels -> backend billing enforcement plan keys.
PLAN_ALIASES = {
    "starter": "retail",
    "trader starter": "retail",
    "pro": "team",
    "trader pro": "team",
    "desk": "team",
    "trader desk": "team",
}

_PLAN_VALIDATION_METRICS = {
    "total_requests": 0,
    "backend_direct_hits": 0,
    "alias_hits": 0,
    "defaulted_blank": 0,
    "invalid_attempts": 0,
}


def get_plan_validation_metrics() -> dict:
    return {
        **_PLAN_VALIDATION_METRICS,
        "allowed_backend_plans": sorted(BACKEND_PLANS),
        "allowed_aliases": sorted(PLAN_ALIASES.keys()),
    }


def reset_plan_validation_metrics() -> None:
    for k in _PLAN_VALIDATION_METRICS:
        _PLAN_VALIDATION_METRICS[k] = 0


def normalize_requested_plan(plan: str | None) -> str:
    _PLAN_VALIDATION_METRICS["total_requests"] += 1
    raw = str(plan or "retail").strip().lower()
    if not raw:
        _PLAN_VALIDATION_METRICS["defaulted_blank"] += 1
        return "retail"
    if raw in BACKEND_PLANS:
        _PLAN_VALIDATION_METRICS["backend_direct_hits"] += 1
        return raw
    if raw in PLAN_ALIASES:
        _PLAN_VALIDATION_METRICS["alias_hits"] += 1
        return PLAN_ALIASES[raw]
    _PLAN_VALIDATION_METRICS["invalid_attempts"] += 1
    raise ValueError(
        f"Unsupported plan '{plan}'. Allowed backend plans: retail, team, restricted; aliases: starter, pro, desk"
    )
