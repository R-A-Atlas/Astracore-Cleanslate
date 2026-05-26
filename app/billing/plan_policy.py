from dataclasses import dataclass


@dataclass(frozen=True)
class PlanPolicy:
    name: str
    max_sessions_per_month: int
    max_seats: int
    support_queue_tier: str
    live_support_scope: str
    live_support_sla: str


PLAN_POLICIES = {
    # Placeholder caps; final values to be set after Mateo pricing decision.
    "retail": PlanPolicy(
        name="retail",
        max_sessions_per_month=300,
        max_seats=1,
        support_queue_tier="standard",
        live_support_scope="bugs_account_only",
        live_support_sla="24-48h",
    ),
    "team": PlanPolicy(
        name="team",
        max_sessions_per_month=2000,
        max_seats=5,
        support_queue_tier="standard",
        live_support_scope="bugs_account_only",
        live_support_sla="24-48h",
    ),
    "restricted": PlanPolicy(
        name="restricted",
        max_sessions_per_month=0,
        max_seats=0,
        support_queue_tier="standard",
        live_support_scope="bugs_account_only",
        live_support_sla="24-48h",
    ),
}


def get_policy(plan: str) -> PlanPolicy:
    return PLAN_POLICIES.get(plan, PLAN_POLICIES["retail"])
