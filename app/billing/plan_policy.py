from dataclasses import dataclass


@dataclass(frozen=True)
class PlanPolicy:
    name: str
    max_sessions_per_month: int
    max_seats: int


PLAN_POLICIES = {
    # Placeholder caps; final values to be set after Mateo pricing decision.
    "retail": PlanPolicy(name="retail", max_sessions_per_month=300, max_seats=1),
    "team": PlanPolicy(name="team", max_sessions_per_month=2000, max_seats=5),
}


def get_policy(plan: str) -> PlanPolicy:
    return PLAN_POLICIES.get(plan, PLAN_POLICIES["retail"])
