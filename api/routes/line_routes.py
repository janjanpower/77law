from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional
from .models import VerifySecretIn, VerifySecretOut, ResolveRouteIn, ResolveRouteOut
from .database import get_db
from .services import _is_bound_to_lawyer, _lookup_client_by_code, _bind_line_user_to_client

router = APIRouter()

@router.post("/lawyer/verify-secret", response_model=VerifySecretOut)
def verify_secret(payload: VerifySecretIn, db: Session = Depends(get_db)):
    code = (payload.text or "").strip()
    already_bound = _is_bound_to_lawyer(db, payload.line_user_id)

    # 空白輸入
    if not code:
        return VerifySecretOut(
            success=True,
            is_secret=False,
            is_lawyer=already_bound,
            route="USER" if already_bound else "USER",
            message='已登錄過，請輸入"?"查閱案件' if already_bound else "空白輸入"
        )

    # 查詢 tenant
    tenant = _lookup_client_by_code(db, code)
    if not tenant:
        return VerifySecretOut(
            success=True,
            is_secret=False,
            is_lawyer=already_bound,
            route="USER" if already_bound else "USER",
            message='已登錄過，請輸入"?"查閱案件' if already_bound else "不是合法暗號"
        )

    # 已綁定情況
    if already_bound:
        return VerifySecretOut(
            success=True,
            is_secret=True,
            is_lawyer=already_bound,
            client_name=tenant["client_name"],
            client_id=tenant["client_id"],
            route="USER",
            message='已登錄過，請輸入"?"查閱案件'
        )

    # 綁定
    _bind_line_user_to_client(
        db=db,
        line_user_id=payload.line_user_id,
        client_id=tenant["client_id"],
        user_name=payload.client_name
    )

    # 綁定成功
    return VerifySecretOut(
        success=True,
        is_secret=True,
        is_lawyer=True,
        client_name=tenant["client_name"],
        client_id=tenant["client_id"],
        action="BIND_OK",
        route="LOGIN",
        message=f"綁定成功！已綁定至「{tenant['client_name']}」。之後輸入「?」可查看操作選項。"
    )


@router.post("/line/resolve-route", response_model=ResolveRouteOut)
def resolve_route(p: ResolveRouteIn, db: Session = Depends(get_db)):
    """
    判斷 route：
    - 說出暗號 (is_secret=True) 且不是律師 -> LOGIN
    - 說出暗號 (is_secret=True) 且是律師 -> SEARCH
    - 說出 '登錄 XXX' -> REGISTER
    - 其他 -> USER
    已綁定後再輸入暗號或登錄 → USER + 提示
    """
    text_in = (p.text or "").strip()
    already_bound = _is_bound_to_lawyer(db, p.line_user_id)

    # 暗號邏輯
    if p.is_secret:
        if already_bound:
            return ResolveRouteOut(route="USER", message='已登錄過，請輸入"?"查閱案件')
        if p.is_lawyer:
            return ResolveRouteOut(route="SEARCH", message="律師暗號查詢")
        return ResolveRouteOut(route="LOGIN", message="暗號登入")

    # 登錄 XXX
    if text_in.startswith("登錄 "):
        if already_bound:
            return ResolveRouteOut(route="USER", message='已登錄過，請輸入"?"查閱案件')
        return ResolveRouteOut(route="REGISTER", message="註冊當事人")

    # 其他
    return ResolveRouteOut(route="USER", message="一般使用者")
