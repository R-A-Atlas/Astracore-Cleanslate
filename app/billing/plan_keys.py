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


def normalize_requested_plan(plan: str | None) -> str:
    raw = str(plan or "retail").strip().lower()
    if not raw:
        return "retail"
    if raw in BACKEND_PLANS:
        return raw
    if raw in PLAN_ALIASES:
        return PLAN_ALIASES[raw]
    raise ValueError(
        f"Unsupported plan '{plan}'. Allowed backend plans: retail, team, restricted; aliases: starter, pro, desk"
    )
