# api/constants/plans.py
# 唯一方案設定與正規化函式

PLAN_LIMITS = {
    "unpaid": 0,
    "基礎方案(5人)": 5,
    "進階方案(10人)": 10,
    "多人方案(20人)": 20,
    "無上限": 999,
}

DEFAULT_PLAN = "unpaid"

def normalize_plan(plan: str | None) -> str:
    """將方案字串做去空白與小寫化處理，空值時回傳 DEFAULT_PLAN。"""
    return (plan or DEFAULT_PLAN).strip().lower()
