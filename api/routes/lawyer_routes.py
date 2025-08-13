# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Optional, Tuple
import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text

from api.database import get_db

# ===== 依你的實際資料表名稱調整這兩個常數 =====
TABLE_BOUND_USER = "public.client_line_users"   # 一般用戶綁定表：line_user_id / is_active
TABLE_BOUND_LAWYER = "public.login_users"      # （可選）律師綁定表：line_user_id / is_active

# ────────────────────────────────────────────────────────────────────────────
# 請求模型
# ────────────────────────────────────────────────────────────────────────────

class VerifyIn(BaseModel):
    text: str = ""
    line_user_id: str

class VerifyOut(BaseModel):
    route: str

# ────────────────────────────────────────────────────────────────────────────
# 共用查詢：由 line_user_id 判斷角色
# ────────────────────────────────────────────────────────────────────────────

def _get_binding_role(db: Session, line_user_id: str) -> Optional[str]:
    """
    回傳 'USER' / 'LAWYER' / None
    - USER：在 client_line_users 找到 line_user_id 且 is_active = TRUE
    - LAWYER：（可選）在 login_users 找到 line_user_id 且 is_active = TRUE
    """
    if not line_user_id:
        return None

    # 一般用戶是否已綁定
    row_user = db.execute(
        text(f"""
            SELECT 1
            FROM {TABLE_BOUND_USER}
            WHERE line_user_id = :lid AND (is_active = TRUE OR is_active IS NULL)
            LIMIT 1
        """),
        {"lid": line_user_id},
    ).first()
    if row_user:
        return "USER"

    # 律師是否綁定（若你的設計是律師也會寫入某表；沒有的話可忽略）
    try:
        row_lawyer = db.execute(
            text(f"""
                SELECT 1
                FROM {TABLE_BOUND_LAWYER}
                WHERE line_user_id = :lid AND (is_active = TRUE OR is_active IS NULL)
                LIMIT 1
            """),
            {"lid": line_user_id},
        ).first()
        if row_lawyer:
            return "LAWYER"
    except Exception:
        # 若沒有這張表或欄位，直接忽略即可
        pass

    return None

# ────────────────────────────────────────────────────────────────────────────
# Router：/api/lawyer 既有路由（更新 verify-secret 規則）
# ────────────────────────────────────────────────────────────────────────────

router = APIRouter(prefix="/api/lawyer", tags=["lawyer"])

@router.post("/verify-secret", response_model=VerifyOut)
def verify_secret(payload: VerifyIn, db: Session = Depends(get_db)):
    """
    分流規則（供 n8n 的 Switch 使用）：
    1) 已綁定的一般用戶 + 文字為「? / ？」 → REGISTERED_USER
    2) 未綁定 + 文字「登錄 XXX」 → REGISTER
    3) 已綁定律師（或你的其他律師驗證規則） → LAWYER
    4) 其餘 → USER
    """
    text_in = (payload.text or "").strip()
    lid = payload.line_user_id or ""

    role = _get_binding_role(db, lid)

    # 1) 一般用戶輸入「?」→ 直接走 REGISTERED_USER
    if role == "USER" and text_in in ("?", "？"):
        return VerifyOut(route="REGISTERED_USER")

    # 2) 未綁定但輸入「登錄 XXX」→ 讓 n8n 走註冊流程
    if role is None and re.match(r"^登(錄|陸)\s+.+", text_in):
        return VerifyOut(route="REGISTER")

    # 3) 律師（你也可以在這裡加其他律師暗號判斷）
    if role == "LAWYER":
        return VerifyOut(route="LAWYER")

    # 4) 其餘情況 → USER（一般對話/使用說明）
    return VerifyOut(route="USER")


# ────────────────────────────────────────────────────────────────────────────
# 可選：/api/user/verify（給 n8n 或除錯查看綁定狀態）
# ────────────────────────────────────────────────────────────────────────────

router_user = APIRouter(prefix="/api/user", tags=["user"])

class VerifyUserIn(BaseModel):
    line_user_id: str

class VerifyUserOut(BaseModel):
    route: str   # REGISTERED_USER or UNREGISTERED_USER
    role: Optional[str] = None  # USER / LAWYER / None（回饋資訊）

@router_user.post("/verify", response_model=VerifyUserOut)
def verify_user(payload: VerifyUserIn, db: Session = Depends(get_db)):
    role = _get_binding_role(db, payload.line_user_id)
    if role == "USER":
        return VerifyUserOut(route="REGISTERED_USER", role=role)
    return VerifyUserOut(route="UNREGISTERED_USER", role=role)
