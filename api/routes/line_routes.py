# api/routes/line_routes.py — minimal fixed version
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from api.schemas.line import VerifySecretIn, VerifySecretOut, ResolveRouteIn, ResolveRouteOut
from api.database import get_db
from api.services.lawyer import _is_bound_to_lawyer, _lookup_client_by_code, _bind_line_user_to_client

router = APIRouter()

@router.post("/lawyer/verify-secret", response_model=VerifySecretOut)
def verify_secret(payload: VerifySecretIn, db: Session = Depends(get_db)):
    code = (payload.text or "").strip()
    already_bound = _is_bound_to_lawyer(db, payload.line_user_id)

    # 空白
    if not code:
        return VerifySecretOut(
            success=False,
            is_secret=False,
            is_lawyer=False,
            route="USER" if already_bound else "LOGIN",
            message='請輸入暗號，例如：「暗號 ABC123」或直接輸入暗號內容'
        )

    tenant = _lookup_client_by_code(db, code)
    if not tenant:
        return VerifySecretOut(
            success=False,
            is_secret=False,
            is_lawyer=False,
            route="USER" if already_bound else "LOGIN",
            message="暗號錯誤或尚未啟用，請確認後再試"
        )

    # 綁定（若已綁過會當作成功）
    _bind_line_user_to_client(db, payload.line_user_id, tenant)

    return VerifySecretOut(
        success=True,
        is_secret=True,
        is_lawyer=True,
        client_name=tenant["client_name"],
        client_id=tenant["client_id"],
        route="LOGIN",
        message=f'綁定成功！已綁定至「{tenant["client_name"]}」。輸入「?」可查看操作選項。'
    )

@router.post("/line/resolve-route", response_model=ResolveRouteOut)
def resolve_route(payload: ResolveRouteIn, db: Session = Depends(get_db)):
    msg = (payload.text or "").strip()
    already_bound = _is_bound_to_lawyer(db, payload.line_user_id)

    # 說出暗號
    if msg.startswith("暗號") or msg.lower().startswith("code"):
        if already_bound:
            return ResolveRouteOut(route="USER", message='已登錄過，請輸入"?"查閱案件')
        return ResolveRouteOut(route="LOGIN", message="暗號登入")

    # 登錄 XXX（當事人名稱）
    if msg.startswith("登錄 ") or msg.startswith("登入 ") or msg.startswith("登录 ") or msg.startswith("登陸 "):
        if already_bound:
            return ResolveRouteOut(route="USER", message='已登錄過，請輸入"?"查閱案件')
        return ResolveRouteOut(route="REGISTER", message="註冊當事人")

    # 律師（已綁定）查名字 -> SEARCH
    if already_bound:
        # 這裡只判斷是否像是在查名字（含中文字/英數且非特殊指令），你可依需求再強化
        if msg and msg not in ("?", "？"):
            return ResolveRouteOut(route="SEARCH", message="律師名稱查詢")

    # 其他 -> USER
    return ResolveRouteOut(route="USER", message="一般使用者")

# export alias for backward-compat import in main.py
line_router = router
