# api/routes/line_routes.py — normalized imports & behavior
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional
import re

from api.schemas.line import VerifySecretIn, VerifySecretOut, ResolveRouteIn, ResolveRouteOut
from api.database import get_db
from api.services.lawyer import _is_bound_to_lawyer, _lookup_client_by_code, _bind_line_user_to_client
from api.services.engagement_service import touch_and_check_idle, mark_reminded

router = APIRouter()
CASE_NO_RE = re.compile(r"^\s*\d{2,8}[/-]\d{1,6}\s*$")  # e.g., 114001 or 1234/5678

@router.post("/lawyer/verify-secret", response_model=VerifySecretOut)
def verify_secret(payload: VerifySecretIn, db: Session = Depends(get_db)):
    code = (payload.text or "").strip()
    already_bound = _is_bound_to_lawyer(db, payload.line_user_id)

    if not code:
        return VerifySecretOut(
            success=True,
            is_secret=False,
            is_lawyer=False,
            route="USER",
            message="請輸入暗號。"
        )

    tenant = _lookup_client_by_code(db, code)
    if not tenant:
        return VerifySecretOut(
            success=True,
            is_secret=False,
            is_lawyer=False,
            route="USER",
            message="暗號錯誤。"
        )

    _bind_line_user_to_client(db, payload.line_user_id, tenant)

    return VerifySecretOut(
        success=True,
        is_secret=True,
        is_lawyer=True,
        route="LOGIN",
        message=f"綁定成功：{tenant.get('client_name','')}"
    )

@router.post("/line/resolve-route", response_model=ResolveRouteOut)
def resolve_route(payload: ResolveRouteIn, db: Session = Depends(get_db)):
    text = (payload.text or "").strip()
    is_lawyer = bool(payload.is_lawyer)
    line_user_id = payload.line_user_id or ""

    bound = _is_bound_to_lawyer(db, line_user_id)

    # 已綁定的律師：只接受「當事人」or 案號
    if bound and is_lawyer:
        if ("當事人" in text) or CASE_NO_RE.match(text):
            return ResolveRouteOut(route="SEARCH", message="律師搜尋")
        return ResolveRouteOut(route="SILENT", message="")

    # 已綁定的一般用戶
    if bound and not is_lawyer:
        if touch_and_check_idle(db, line_user_id, idle_minutes=60):
            mark_reminded(db, line_user_id)
            return ResolveRouteOut(route="USER", message='溫馨提醒：已綁定，用戶可輸入「?」自查案件。')
        if text in ("?", "？"):
            return ResolveRouteOut(route="MY_CASE", message="自查案件")
        return ResolveRouteOut(route="SILENT", message="")

    # 未綁定 → 檢查「登錄 XXX」
    if text.startswith(("登錄 ", "登入 ", "登陸 ")):
        name = text.split(" ", 1)[1].strip() if " " in text else ""
        if name:
            return ResolveRouteOut(route="REGISTER", message=f"註冊當事人：{name}")
        return ResolveRouteOut(route="REGISTER", message="註冊當事人")

    return ResolveRouteOut(route="USER", message="一般使用者")

# 舊名稱相容
line_router = router
