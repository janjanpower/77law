# -*- coding: utf-8 -*-
"""
api/routes/api_routes.py
- Login rule: is_active==True -> allow; else require tenant_status==True
- Registration: is_active defaults to False; tenant_status per plan (unpaid=False else True)
- Ensure: create tenant schema on register, then UPDATE login_users.tenant_db_url / tenant_db_ready
"""

from __future__ import annotations

import os
import hashlib
import random
import string
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, constr, Field
from sqlalchemy.orm import Session
from sqlalchemy import text

from api.database import get_db
from api.models_control import LoginUser  # 含 tenant_db_url / tenant_db_ready 欄位
from api.services.tenant_bootstrap import ensure_tenant_schema

router = APIRouter()

bearer_scheme = HTTPBearer(auto_error=False)


# ============================== Util ==============================

def hash_password(raw: str) -> str:
    """簡易雜湊（若你已改為純文字密碼就不要呼叫這個）"""
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def gen_secret_code(n: int = 8) -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(random.choices(alphabet, k=n))


def canonical_plan(raw: str) -> str:
    """將 plan 字串正規化到有限集合（未定義者一律視為 unpaid）"""
    raw = (raw or "").strip().lower()
    if raw in {"unpaid", "free", "trial"}:
        return "unpaid"
    if raw in {"basic", "standard"}:
        return "basic"
    if raw in {"pro", "premium"}:
        return "pro"
    return "unpaid"


# ============================== Schemas ==============================

class ClientLoginRequest(BaseModel):
    client_id: constr(strip_whitespace=True, min_length=3, max_length=50)
    password: constr(min_length=1, max_length=128)


class ClientLoginResponse(BaseModel):
    client_id: str
    is_active: bool
    tenant_status: bool
    message: str = "ok"


class RegisterRequest(BaseModel):
    client_name: constr(strip_whitespace=True, min_length=1, max_length=100)
    client_id:   constr(strip_whitespace=True, min_length=3, max_length=50)
    password:    constr(min_length=1, max_length=128)
    plan_type:   Optional[str] = Field(default="unpaid")


class RegisterResponse(BaseModel):
    message: str
    client_id: str
    secret_code: str


class MeResponse(BaseModel):
    client_id: str
    client_name: str
    is_active: bool
    tenant_status: bool
    tenant_db_url: Optional[str] = None
    tenant_db_ready: Optional[bool] = None


# ============================== Routes ==============================

@router.post("/client-login", response_model=ClientLoginResponse, summary="Client credential login (JWT-like rule)")
def client_login(req: ClientLoginRequest, db: Session = Depends(get_db)):
    user: LoginUser | None = (
        db.query(LoginUser)
        .filter(LoginUser.client_id == req.client_id.strip())
        .first()
    )
    if not user:
        raise HTTPException(status_code=401, detail="帳號或密碼錯誤")

    # 若你已存純文字密碼，請改為：ok = (user.password == req.password)
    ok = (user.password == req.password) or (user.password == hash_password(req.password))
    if not ok:
        raise HTTPException(status_code=401, detail="帳號或密碼錯誤")

    # 登入規則：is_active 為 True 直接允許；否則需 tenant_status 為 True
    if not getattr(user, "is_active", False) and not getattr(user, "tenant_status", False):
        raise HTTPException(status_code=403, detail="帳號未啟用或租戶狀態未就緒")

    # 更新最後登入時間（可選）
    try:
        setattr(user, "last_login", datetime.now(timezone.utc))
        db.commit()
    except Exception:
        db.rollback()

    return ClientLoginResponse(
        client_id=user.client_id,
        is_active=bool(getattr(user, "is_active", False)),
        tenant_status=bool(getattr(user, "tenant_status", False)),
        message="ok",
    )


@router.get("/me", response_model=MeResponse)
def me(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
       db: Session = Depends(get_db)):
    """
    假設你用 JWT，這裡應該解析 token 取得 client_id。
    為了最小可用，先用 Authorization: Bearer <client_id> 直接查。
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(status_code=401, detail="Missing token")
    client_id = credentials.credentials

    user: LoginUser | None = (
        db.query(LoginUser)
        .filter(LoginUser.client_id == client_id)
        .first()
    )
    if not user:
        raise HTTPException(status_code=404, detail="user not found")

    return MeResponse(
        client_id=user.client_id,
        client_name=user.client_name,
        is_active=bool(getattr(user, "is_active", False)),
        tenant_status=bool(getattr(user, "tenant_status", False)),
        tenant_db_url=getattr(user, "tenant_db_url", None),
        tenant_db_ready=getattr(user, "tenant_db_ready", None),
    )


# ============================== Register ==============================

@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    # 唯一性檢查
    exists = db.query(LoginUser).filter(LoginUser.client_id == req.client_id).first()
    if exists:
        raise HTTPException(status_code=400, detail="client_id 已被使用")

    # 產生不重複的 secret_code
    sc = gen_secret_code()
    for _ in range(5):
        if not db.query(LoginUser).filter(LoginUser.secret_code == sc).first():
            break
        sc = gen_secret_code()

    # Plan 與狀態
    plan_key = canonical_plan(req.plan_type or "unpaid")
    tenant_value = False if plan_key == "unpaid" else True

    # 建立使用者（欄位存在才帶入，避免不同 DB 版本報錯）
    user_kwargs: Dict[str, Any] = {
        "client_id": req.client_id.strip(),
        "client_name": req.client_name.strip(),
        "password": req.password,            # 若你已改為雜湊：改成 password=hash_password(req.password)
        "secret_code": sc,
        "is_active": False,                  # 預設需後台啟用
    }
    # 有些欄位在舊 DB 可能不存在，因此用 hasattr 防呆
    if hasattr(LoginUser, "plan_type"):
        user_kwargs["plan_type"] = plan_key
    if hasattr(LoginUser, "tenant_status"):
        user_kwargs["tenant_status"] = tenant_value

    user = LoginUser(**user_kwargs)
    db.add(user)
    db.commit()
    db.refresh(user)

    # === 立刻建立 tenant schema，並把 URL/READY 寫回 login_users ===
    try:
        tenant_url = ensure_tenant_schema(user.client_id)

        # ORM 對齊（保留記憶體狀態，但不依賴它）
        if hasattr(LoginUser, "tenant_db_url"):
            setattr(user, "tenant_db_url", tenant_url)
        if hasattr(LoginUser, "tenant_db_ready"):
            setattr(user, "tenant_db_ready", True)

        # ✅ 直接用 SQL 寫回，最保險
        db.execute(
            text("""
                UPDATE login_users
                   SET tenant_db_url = :url,
                       tenant_db_ready = TRUE
                 WHERE client_id = :cid
            """),
            {"url": tenant_url, "cid": user.client_id}
        )
        db.commit()

    except Exception:
        db.rollback()
        # 失敗時，保留帳號但標記未就緒
        try:
            db.execute(
                text("""
                    UPDATE login_users
                       SET tenant_db_ready = FALSE
                     WHERE client_id = :cid
                """),
                {"cid": user.client_id}
            )
            db.commit()
        except Exception:
            db.rollback()

    return RegisterResponse(
        message="註冊成功，請妥善保存您的登錄資訊。",
        client_id=user.client_id,
        secret_code=user.secret_code,
    )
