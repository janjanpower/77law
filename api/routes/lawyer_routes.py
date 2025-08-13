# api/routes/lawyer_routes.py
# -*- coding: utf-8 -*-
from __future__ import annotations

import datetime
import os
import re
from typing import Optional, Dict, Any

from urllib.parse import quote
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from api.database import get_db
from api.models_control import LoginUser, ClientLineUsers  # 你現有的模型
# 若專案內有 PendingLineUser（綁定/審核中的一般用戶），可保留；沒有就註解掉下面兩行相關用法
try:
    from api.models_control import PendingLineUser
except Exception:
    PendingLineUser = None  # type: ignore

# ===== 依你的實際資料表調整（已沿用你現有命名）=====
TABLE_BOUND_USER = "public.client_line_users"   # 一般用戶綁定表
TABLE_BOUND_LAWYER = "public.login_users"      # 律師/事務所主檔（含 plan/user_limit）

# ✅ 與 main.py 對應的名稱（你原檔如此）
lawyer_router = APIRouter(prefix="/api/lawyer", tags=["lawyer"])

# ────────────────────────────────────────────────────────────────────────────
# I/O Schemas
# ────────────────────────────────────────────────────────────────────────────
class BindUserRequest(BaseModel):
    success: bool
    user_id: str
    client_id: str                 # 從 verify-secret 回傳帶進來
    role: str = "user"             # 'user' | 'lawyer'，預設一般用戶

class BindUserResponse(BaseModel):
    success: bool
    client_name: str | None = None
    plan_type: str | None = None
    limit: int = 0
    usage: int = 0
    available: int = 0
    message: str | None = None

class VerifySecretIn(BaseModel):
    text: Optional[str] = None
    line_user_id: Optional[str] = None
    user_id: Optional[str] = None         # 相容舊參數
    reply_token: Optional[str] = None
    eventType: Optional[str] = None
    body: Optional[Dict[str, Any]] = None # 允許直接丟 LINE 原始 webhook body
    debug: bool = False                   # 便於除錯

class VerifySecretOut(BaseModel):
    success: bool
    client_id: Optional[str] = None
    client_name: Optional[str] = None
    is_lawyer: bool = False
    route: str
    bind_url: Optional[str] = None
    debug: Optional[Dict[str, Any]] = None

class CaseSearchIn(BaseModel):
    text: str
    line_user_id: Optional[str] = None

# ────────────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────────────
def _build_plan_message(title: str, client_name: str, plan_type: Optional[str], limit_val: Optional[int], usage_val: int) -> str:
    plan = plan_type or "未設定"
    lim  = str(limit_val) if isinstance(limit_val, int) else "未設定"
    return (
        f"{title}\n"
        f"事務所：{client_name}\n"
        f"方案：{plan}\n"
        f"上限人數：{lim}\n"
        f"當前人數：{usage_val}"
    )

def _normalize_text(s: str) -> str:
    if not s:
        return ""
    # 去零寬字元
    s = re.sub(r"[\u200B-\u200D\uFEFF]", "", s)
    # 全形空白 -> 半形
    s = s.replace("\u3000", " ")
    return s.strip()

def _has_question(s: str) -> bool:
    # 允許包含 ? 或 全形 ？
    return bool(re.search(r"[?？]", s))

def _get_role_by_line_id(db: Session, lid: str) -> Optional[str]:
    """
    回傳 'USER' / 'LAWYER' / None
    - USER：client_line_users 有此 line_user_id && is_active = TRUE（或 NULL 視為 TRUE）
    - LAWYER：login_users（或你的律師表）有此 line_user_id && is_active = TRUE（或 NULL）
    """
    if not lid:
        return None

    # 已綁定的一般用戶？
    row_user = db.execute(
        text(f"""
          SELECT 1 FROM {TABLE_BOUND_USER}
           WHERE line_user_id = :lid
             AND COALESCE(is_active, TRUE) = TRUE
           LIMIT 1
        """),
        {"lid": lid},
    ).first()
    if row_user:
        return "USER"

    # 律師（若你的律師也會保存 line_user_id）
    try:
        row_lawyer = db.execute(
            text(f"""
              SELECT 1 FROM {TABLE_BOUND_LAWYER}
               WHERE line_user_id = :lid
                 AND COALESCE(is_active, TRUE) = TRUE
               LIMIT 1
            """),
            {"lid": lid},
        ).first()
        if row_lawyer:
            return "LAWYER"
    except Exception:
        pass

    return None

# ────────────────────────────────────────────────────────────────────────────
# 綁定：由後端決定是否超過「一般用戶上限」（沿用你原本欄位 max_users/user_limit）
# ────────────────────────────────────────────────────────────────────────────
@lawyer_router.post("/bind-user", response_model=BindUserResponse)
def bind_user(payload: BindUserRequest, db: Session = Depends(get_db)):
    if not payload.success:
        return BindUserResponse(success=False, message="未執行綁定")

    # 權威：從 login_users 取 client_name / 方案
    tenant = (db.query(LoginUser)
              .filter(LoginUser.client_id == payload.client_id,
                      LoginUser.is_active.is_(True))
              .first())
    if not tenant:
        return BindUserResponse(success=False, message="找不到事務所或未啟用")

    client_id   = tenant.client_id
    client_name = tenant.client_name
    plan_type   = getattr(tenant, "plan_type", None)
    max_users   = int(getattr(tenant, "max_users", 0) or getattr(tenant, "user_limit", 0) or 0)

    # 當前使用數（一般：全部 is_active；如只想限 USER，就把 role 條件加上）
    usage_before = db.query(func.count(ClientLineUsers.id)).filter(
        ClientLineUsers.client_id == client_id,
        ClientLineUsers.is_active.is_(True)
    ).scalar() or 0
    usage_before = int(usage_before)

    # 是否已存在啟用綁定
    existed = db.query(ClientLineUsers).filter(
        ClientLineUsers.client_id == client_id,
        ClientLineUsers.line_user_id == payload.user_id,
        ClientLineUsers.is_active.is_(True)
    ).first()

    if existed:
        msg = _build_plan_message("ℹ️ 已經綁定", client_name, plan_type, max_users, usage_before)
        return BindUserResponse(
            success=True,
            client_name=client_name,
            plan_type=plan_type,
            limit=max_users,
            usage=usage_before,
            available=max(0, max_users - usage_before),
            message=msg,
        )

    # 方案額滿（只限制一般用戶；若要限制律師，請在 DB 觸發器做，或這裡判斷 payload.role == 'lawyer'）
    if payload.role != "lawyer" and max_users and usage_before >= max_users:
        msg = _build_plan_message("⚠️ 已額滿，需要升級方案", client_name, plan_type, max_users, usage_before)
        return BindUserResponse(
            success=False,
            client_name=client_name,
            plan_type=plan_type,
            limit=max_users,
            usage=usage_before,
            available=0,
            message=msg,
        )

    # Upsert（以權威名稱寫入）
    db.execute(text("""
        INSERT INTO client_line_users (client_id, client_name, line_user_id, user_role, is_active, bound_at)
        VALUES (:client_id, :client_name, :line_user_id, :role, TRUE, NOW())
        ON CONFLICT (client_id, line_user_id)
        DO UPDATE SET client_name = EXCLUDED.client_name,
                      user_role   = EXCLUDED.user_role,
                      is_active   = TRUE,
                      bound_at    = NOW();
    """), {"client_id": client_id, "client_name": client_name,
           "line_user_id": payload.user_id, "role": payload.role})
    db.commit()

    usage_now = db.query(func.count(ClientLineUsers.id)).filter(
        ClientLineUsers.client_id == client_id,
        ClientLineUsers.is_active.is_(True)
    ).scalar() or 0
    usage_now = int(usage_now)

    msg = _build_plan_message("🎉 綁定成功", client_name, plan_type, max_users, usage_now)
    return BindUserResponse(
        success=True,
        client_name=client_name,
        plan_type=plan_type,
        limit=max_users,
        usage=usage_now,
        available=max(0, max_users - usage_now),
        message=msg,
    )

# ────────────────────────────────────────────────────────────────────────────
# 驗證 secret（供 n8n Switch 使用）— 加入 REGISTERED_USER 規則
# ────────────────────────────────────────────────────────────────────────────
@lawyer_router.post("/verify-secret", response_model=VerifySecretOut)
async def verify_secret(request: Request, db: Session = Depends(get_db)):
    """
    分流規則：
    1) 已綁定的一般用戶 + 訊息包含 ?/？ ⇒ REGISTERED_USER
    2) 有效暗號且不是已綁定律師 ⇒ LOGIN（給綁定網址）
    3) 已綁定律師（或暗號 + 已綁定） ⇒ LAWYER
    4) 其餘 ⇒ USER
    """
    try:
        payload: Dict[str, Any] = await request.json()
    except Exception:
        # 保底：空 payload
        payload = {}

    text_in = _normalize_text(
        payload.get("text")
        or payload.get("message")
        or ((payload.get("body") or {}).get("events", [{}])[0].get("message") or {}).get("text")
        or ""
    )
    lid = (payload.get("line_user_id") or payload.get("user_id")
           or ((payload.get("body") or {}).get("events", [{}])[0].get("source") or {}).get("userId")
           or "").strip()
    debug = bool(payload.get("debug"))

    # 角色偵測
    role = _get_role_by_line_id(db, lid)
    has_q = _has_question(text_in)

    # 1) 已綁定的一般用戶 + 問號 → REGISTERED_USER
    if role == "USER" and has_q:
        out = {
            "success": False,
            "is_lawyer": False,
            "client_id": None,
            "client_name": None,
            "route": "REGISTERED_USER",
            "bind_url": None,
        }
        if debug:
            out["debug"] = {"text_in": text_in, "role": role, "has_question": has_q, "line_user_id_len": len(lid)}
        return out  # 直接返回

    # 解析暗號（事務所登入碼）
    secret_rec = None
    if text_in:
        secret_rec = (
            db.query(LoginUser)
              .filter(func.btrim(LoginUser.secret_code) == text_in)
              .first()
        )
    is_secret = bool(secret_rec)
    client_id_from_secret = getattr(secret_rec, "client_id", None) if secret_rec else None
    client_name_from_secret = getattr(secret_rec, "client_name", None) if secret_rec else None

    # 是否已綁定律師（可限制同事務所）
    is_lawyer = False
    chosen_client_id_from_lawyer = None
    if lid:
        q = (db.query(ClientLineUsers)
               .filter(ClientLineUsers.line_user_id == lid,
                       ClientLineUsers.is_active == True))
        if client_id_from_secret:
            q = q.filter(ClientLineUsers.client_id == client_id_from_secret)
        clu = q.first()
        if clu:
            is_lawyer = True
            chosen_client_id_from_lawyer = getattr(clu, "client_id", None)

    # 路由決策
    if (not is_secret) and is_lawyer:
        route = "LAWYER"
        chosen_client_id = chosen_client_id_from_lawyer
        chosen_client_name = None
    elif is_secret and (not is_lawyer):
        route = "LOGIN"
        chosen_client_id = client_id_from_secret
        chosen_client_name = client_name_from_secret
    elif (not is_secret) and (not is_lawyer):
        route = "USER"
        chosen_client_id = None
        chosen_client_name = None
    else:
        # 同時是暗號 & 綁定律師 → 視為 LAWYER
        route = "LAWYER"
        chosen_client_id = chosen_client_id_from_lawyer or client_id_from_secret
        chosen_client_name = client_name_from_secret if client_id_from_secret == chosen_client_id else None

    # 綁定網址（僅 LOGIN）
    bind_url = None
    if route == "LOGIN" and is_secret:
        base = os.getenv("API_BASE_URL") or os.getenv("APP_BASE_URL") or "https://example.com"
        bind_url = f"{base}/api/tenant/bind-user?code={quote(text_in)}"
        if client_id_from_secret:
            bind_url += f"&client_id={quote(str(client_id_from_secret))}"

    # 若只知道 client_id，補查 client_name
    if chosen_client_id and not chosen_client_name:
        rec = db.query(LoginUser).filter(LoginUser.client_id == str(chosen_client_id)).first()
        if rec:
            chosen_client_name = rec.client_name

    out = {
        "success": bool(is_secret),
        "is_lawyer": bool(is_lawyer),
        "client_id": chosen_client_id,
        "client_name": chosen_client_name,
        "route": route,
        "bind_url": bind_url,
    }
    if debug:
        out["debug"] = {
            "text_in": text_in,
            "role_by_line_id": role,
            "has_question": has_q,
            "is_secret": is_secret,
            "line_user_id_len": len(lid),
        }
    return out

# ────────────────────────────────────────────────────────────────────────────
# 方案查詢（沿用你檔案中的邏輯）
# ────────────────────────────────────────────────────────────────────────────
def _extract_client_name(payload: dict) -> Optional[str]:
    if not isinstance(payload, dict):
        return None
    name = payload.get("client_name") or payload.get("tenant")
    if isinstance(name, str) and name.strip():
        return name.strip()
    for key in ("body", "data"):
        sub = payload.get(key)
        if isinstance(sub, dict):
            name = sub.get("client_name") or sub.get("tenant")
            if isinstance(name, str) and name.strip():
                return name.strip()
    return None

@lawyer_router.post("/check-client-plan")
async def check_client_plan(request: Request, db: Session = Depends(get_db)):
    try:
        payload = await request.json()
    except Exception:
        return {"success": False, "client_name": None, "plan_type": None, "limit": None, "usage": None, "available": None, "message": "invalid_json"}

    client_name = _extract_client_name(payload)
    if not client_name:
        return {"success": False, "client_name": None, "plan_type": None, "limit": None, "usage": None, "available": None, "message": "client_name_required"}

    user = (
        db.query(LoginUser)
        .filter(func.btrim(LoginUser.client_name) == client_name.strip())
        .first()
    )
    if not user:
        return {"success": False, "client_name": client_name, "plan_type": None, "limit": None, "usage": None, "available": None, "message": "client_not_found"}

    plan_type = getattr(user, "plan_type", None)
    limit_val = getattr(user, "user_limit", None) or getattr(user, "max_users", None)

    usage_val = db.query(func.count(ClientLineUsers.id)).filter(
        ClientLineUsers.client_id == user.client_id,
        ClientLineUsers.is_active.is_(True)
    ).scalar() or 0
    usage_val = int(usage_val)
    available = max(limit_val - usage_val, 0) if isinstance(limit_val, int) else None

    if isinstance(limit_val, int) and usage_val >= limit_val:
        msg = _build_plan_message("⚠️ 已額滿，需要升級方案", user.client_name, plan_type, limit_val, usage_val)
        ok = False
    else:
        msg = _build_plan_message("✅ 目前方案資訊", user.client_name, plan_type, limit_val, usage_val)
        ok = True

    return {
        "success": ok,
        "client_name": user.client_name,
        "plan_type": plan_type,
        "limit": limit_val,
        "usage": usage_val,
        "available": available,
        "message": msg
    }

# ────────────────────────────────────────────────────────────────────────────
# 健康檢查 / 測試
# ────────────────────────────────────────────────────────────────────────────
@lawyer_router.get("/verify-secret/ping")
async def verify_secret_ping():
    return {"ok": True, "ts": datetime.datetime.utcnow().isoformat()}

# ────────────────────────────────────────────────────────────────────────────
# 簡易案件關鍵字查詢（維持你原檔）
# ────────────────────────────────────────────────────────────────────────────
@lawyer_router.post("/case-search")
def case_search(payload: CaseSearchIn, db: Session = Depends(get_db)):
    from api.models_cases import CaseRecord
    key = (payload.text or "").strip().split()[-1]
    if not key:
        return {"message": "請輸入關鍵字或案號"}

    rows = (
        db.query(CaseRecord)
          .filter(
              (CaseRecord.case_id == key) |
              (CaseRecord.case_number.ilike(f"%{key}%")) |
              (CaseRecord.client.ilike(f"%{key}%"))
          )
          .order_by(text("updated_at DESC NULLS LAST"))
          .limit(5)
          .all()
    )
    if not rows:
        return {"message": f"找不到符合「{key}」的案件"}

    def fmt(r):
        return f"{r.client or '-'} / {r.case_type or '-'} / {r.case_number or r.case_id} / 進度:{r.progress or '-'}"

    return {"message": "查到以下案件：\n" + "\n".join(fmt(r) for r in rows)}
