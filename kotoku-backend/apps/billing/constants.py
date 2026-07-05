"""
Billing plan definitions — single source of truth for all plan metadata.
Do NOT expose cost/margin or storage-in-GB fields to users.
"""
from dataclasses import dataclass, field
from typing import List


@dataclass(frozen=True)
class PlanFeatures:
    team_seats: int
    bulk_creation: bool
    reporting: bool
    archive_search: bool


@dataclass(frozen=True)
class Plan:
    id: str
    family: str                     # "personal" | "enterprise"
    name: str
    tagline: str
    price_ghs: int                  # monthly price in GHS
    max_agreements_per_month: int   # hard cap for Personal; soft cap for Enterprise
    retention_months: int
    features: PlanFeatures
    is_soft_cap: bool = False       # True for Enterprise plans


PLANS: List[Plan] = [
    Plan(
        id="personal_basic",
        family="personal",
        name="Personal Basic",
        tagline="Protect one important deal each month",
        price_ghs=49,
        max_agreements_per_month=1,
        retention_months=12,
        features=PlanFeatures(team_seats=1, bulk_creation=False, reporting=False, archive_search=False),
    ),
    Plan(
        id="personal_plus",
        family="personal",
        name="Personal Plus",
        tagline="Ideal for side hustles and small landlords",
        price_ghs=79,
        max_agreements_per_month=3,
        retention_months=24,
        features=PlanFeatures(team_seats=1, bulk_creation=False, reporting=False, archive_search=False),
    ),
    Plan(
        id="personal_protect",
        family="personal",
        name="Personal Protect",
        tagline="For serious individual dealmakers",
        price_ghs=99,
        max_agreements_per_month=7,
        retention_months=36,
        features=PlanFeatures(team_seats=1, bulk_creation=False, reporting=False, archive_search=False),
    ),
    Plan(
        id="enterprise_standard",
        family="enterprise",
        name="Enterprise Standard",
        tagline="Run your operation on solid agreements",
        price_ghs=400,
        max_agreements_per_month=20,
        retention_months=60,  # 5 years
        features=PlanFeatures(team_seats=3, bulk_creation=True, reporting=True, archive_search=False),
        is_soft_cap=True,
    ),
    Plan(
        id="enterprise_plus",
        family="enterprise",
        name="Enterprise Plus",
        tagline="For high-volume dealers and platforms",
        price_ghs=1200,
        max_agreements_per_month=80,
        retention_months=120,  # 10 years
        features=PlanFeatures(team_seats=10, bulk_creation=True, reporting=True, archive_search=True),
        is_soft_cap=True,
    ),
]

PLAN_MAP: dict[str, Plan] = {p.id: p for p in PLANS}

DEFAULT_PLAN_ID = "personal_basic"

# Personal plan IDs in upgrade order
PERSONAL_UPGRADE_ORDER = ["personal_basic", "personal_plus", "personal_protect", "enterprise_standard"]

# Misuse heuristics thresholds
MISUSE_CONSECUTIVE_MONTHS_AT_CAP = 3
MISUSE_ROLLING_90_DAY_AGREEMENTS = 15
MISUSE_LIFETIME_PERSONAL_CAP = 100


def get_plan(plan_id: str) -> Plan:
    plan = PLAN_MAP.get(plan_id)
    if plan is None:
        return PLAN_MAP[DEFAULT_PLAN_ID]
    return plan


def get_recommended_upgrades(current_plan: Plan) -> List[Plan]:
    """Return 1-3 suggested upgrade plans above the current one."""
    if current_plan.family == "enterprise":
        if current_plan.id == "enterprise_standard":
            return [PLAN_MAP["enterprise_plus"]]
        return []

    # Personal: suggest next personal tier + Enterprise Standard
    personal_ids = ["personal_basic", "personal_plus", "personal_protect"]
    try:
        idx = personal_ids.index(current_plan.id)
    except ValueError:
        idx = -1

    upgrades = []
    if idx < len(personal_ids) - 1:
        upgrades.append(PLAN_MAP[personal_ids[idx + 1]])
    upgrades.append(PLAN_MAP["enterprise_standard"])
    return upgrades
