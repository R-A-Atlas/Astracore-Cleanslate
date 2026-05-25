from dataclasses import dataclass


@dataclass(frozen=True)
class PlanPolicy:
    name: str
    max_sessions_per_day: int
    max_seats: int


PLAN_POLICIES = {
    "retail": PlanPolicy(name="retail", max_sessions_per_day=3, max_seats=1),
    "team": PlanPolicy(name="team", max_sessions_per_day=20, max_seats=5),
}


def get_policy(plan: str) -> PlanPolicy:
    return PLAN_POLICIES.get(plan, PLAN_POLICIES["retail"])
