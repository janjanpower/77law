# api/constants/plans.py
from typing import Optional

PLAN_DISPLAY = {
    "unpaid": "未付費",
    "basic_5": "基礎方案(5人)",
    "pro_10": "進階方案(10人)",
    "team_20": "多人方案(20人)",
    "unlimited": "無上限",
}

PLAN_LIMITS = {
    "unpaid": 0,
    "basic_5": 5,
    "pro_10": 10,
    "team_20": 20,
    "unlimited": 999_999,
}

DEFAULT_PLAN = "unpaid"

ALIASES = {
    "unpaid": "unpaid", "未付費": "unpaid",
    "基礎方案(5人)": "basic_5", "basic": "basic_5", "basic_5": "basic_5",
    "進階方案(10人)": "pro_10", "pro": "pro_10", "pro_10": "pro_10",
    "多人方案(20人)": "team_20", "team": "team_20", "team_20": "team_20",
    "無上限": "unlimited", "unlimited": "unlimited",
}

def canonical_plan(value: Optional[str]) -> str:
    if not value:
        return DEFAULT_PLAN
    return ALIASES.get(str(value).strip().lower(), DEFAULT_PLAN)

def plan_limit(plan_key: Optional[str]) -> int:
    return PLAN_LIMITS.get(canonical_plan(plan_key), PLAN_LIMITS[DEFAULT_PLAN])

def plan_display(plan_key: Optional[str]) -> str:
    return PLAN_DISPLAY.get(canonical_plan(plan_key), PLAN_DISPLAY[DEFAULT_PLAN])
