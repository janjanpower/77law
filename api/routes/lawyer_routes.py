# api/routes/lawyer_routes.py
# -*- coding: utf-8 -*-

import datetime
import os
from typing import Optional, Dict, Any

from urllib.parse import quote
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from api.database import get_db
from api.models_control import LoginUser, ClientLineUsers

# ✅ 與 main.py 對應的名稱
lawyer_router = APIRouter(prefix="/api/lawyer", tags=["lawyer"])

# ---------- I/O Schemas ----------
class CheckLimitIn(BaseModel):
    tenant_code: str = Field(..., description="事務所代碼/暗號（先用 client_id，必要時自行改 mapping）")
    line_user_id: str = Field(..., min_length=5)

class CheckLimitOut(BaseModel):
    success: bool
    limit: Optional[int] = None
    usage: Optional[int] = None
    tenant: Optional[Dict[str, Any]] = None
    reason: Optional[str] = None  # "limit_reached" | "invalid_tenant_code"

class BindLawyerIn(BaseModel):
    tenant_code: str
    line_user_id: str

class BindLawyerOut(BaseModel):
    success: bool
    tenant: Optional[Dict[str, Any]] = None
    role: Optional[str] = None     # "lawyer"
    reason: Optional[str] = None   # "already_bound" | "invalid_tenant_code"

# ---------- Helper ----------
def resolve_client_by_code(db: Session, tenant_code: str) -> Optional[LoginUser]:
    """以 client_id（或 client_name）解析事務所。"""
    client = (
        db.query(LoginUser)
        .filter(LoginUser.client_id == tenant_code, LoginUser.is_active == True)
        .first()
    )
    if not client:
        client = (
            db.query(LoginUser)
            .filter(LoginUser.client_name == tenant_code, LoginUser.is_active == True)
            .first()
        )
    return client

def count_current_usage(db: Session, client_id: str) -> int:
    """目前已啟用的 LINE 綁定數。"""
    return (
        db.query(ClientLineUsers)
        .filter(ClientLineUsers.client_id == client_id, ClientLineUsers.is_active == True)
        .count()
    )

def upsert_lawyer_binding(db: Session, client_id: str, line_user_id: str) -> bool:
    """將使用者綁為律師（冪等）。"""
    row = (
        db.query(ClientLineUsers)
        .filter(ClientLineUsers.line_user_id == line_user_id)
        .first()
    )
    if row:
        row.client_id = client_id
        row.user_role = "lawyer"
        row.is_active = True
    else:
        row = ClientLineUsers(
            client_id=client_id,
            line_user_id=line_user_id,
            user_role="lawyer",
            is_active=True,
        )
        db.add(row)
    db.commit()
    return True

# ---------- 綁定成功（後端決定名稱） ----------
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

    # 當前使用數
    usage_before = db.query(func.count(ClientLineUsers.id)).filter(
        ClientLineUsers.client_id == client_id,
        ClientLineUsers.is_active.is_(True)
    ).scalar() or 0
    usage_before = int(usage_before)

    # 已綁定？
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

    # 方案額滿（只限制一般用戶，律師可視需求放寬）
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
# =========== 驗證 secret_code ============
class VerifySecretIn(BaseModel):
    text: Optional[str] = None
    user_id: Optional[str] = None
    reply_token: Optional[str] = None
    eventType: Optional[str] = None
    body: Optional[Dict[str, Any]] = None  # 允許直接丟 LINE 原始 webhook body

class VerifySecretOut(BaseModel):
    success: bool
    client_name: Optional[str] = None

def extract_from_line_body(body: dict):
    """從 LINE webhook body 擷取需要的欄位"""
    try:
        ev = (body or {}).get("events", [{}])[0]
        text = (ev.get("message") or {}).get("text")
        user_id = (ev.get("source") or {}).get("userId")
        reply_token = ev.get("replyToken")
        event_type = ev.get("type")
        return text, user_id, reply_token, event_type
    except Exception:
        return None, None, None, None

@lawyer_router.post("/verify-secret")
async def verify_secret(request: Request, db: Session = Depends(get_db)):
    p = await request.json()
    text_in      = (p.get("text") or "").strip()
    line_user_id = p.get("line_user_id") or p.get("user_id")
    channel_id   = p.get("destination")            # ★ 讀 LINE 的 channel（事務所綁定點）

    # 1) 已綁定律師 or 已註冊/待審用戶
    bind_row = db.query(ClientLineUsers)\
                 .filter(ClientLineUsers.line_user_id == line_user_id,
                         ClientLineUsers.is_active.is_(True)).first()
    pending_row = None
    if not bind_row and line_user_id:
        pending_row = db.query(PendingLineUser)\
                        .filter(PendingLineUser.line_user_id == line_user_id,
                                PendingLineUser.status.in_(["pending","registered"]))\
                        .first()

    client_id_from_lawyer  = getattr(bind_row,   "client_id", None)
    client_id_from_pending = getattr(pending_row,"client_id", None)

    # 2) 暗號所屬的事務所
    secret_rec = None
    if text_in:
        secret_rec = db.query(LoginUser)\
                       .filter(func.btrim(LoginUser.secret_code)==text_in).first()
    client_id_from_secret = getattr(secret_rec, "client_id", None)

    # 3) Channel 對應（冷啟用）
    tenant = None
    if not (client_id_from_lawyer or client_id_from_pending or client_id_from_secret) and channel_id:
        tenant = db.execute(text("""
            SELECT client_id FROM bot_channels WHERE channel_id = :cid LIMIT 1
        """), {"cid": channel_id}).first()
    client_id_from_channel = tenant[0] if tenant else None

    # 路由（保持你原語意）
    if bind_row and not secret_rec:
        route = "LAWYER";       chosen_client_id = client_id_from_lawyer
    elif (not bind_row) and secret_rec:
        route = "LOGIN";        chosen_client_id = client_id_from_secret
    elif (not bind_row) and (not secret_rec):
        route = "USER";         chosen_client_id = client_id_from_pending or client_id_from_channel
    else:
        route = "LAWYER";       chosen_client_id = client_id_from_lawyer or client_id_from_secret

    # 已註冊一般用戶 + 有暗號（你原本特例）
    if pending_row and secret_rec:
        route = "REGISTERED_USER"
        chosen_client_id = client_id_from_pending or client_id_from_secret

    # 最後回傳：任何 route 都盡量帶 client_id（可能為 None）
    return {
        "success": bool(secret_rec),
        "is_lawyer": bool(bind_row),
        "client_id": chosen_client_id,
        "client_name": getattr(secret_rec, "client_name", None),
        "route": route,
        "bind_url": None
    }

    # === 原有邏輯：未註冊用戶的暗號檢查 ===
    # 1) 檢查暗號
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

    # 2) 是否律師
    is_lawyer = False
    client_id_from_lawyer = None
    if line_user_id:
        q = (db.query(ClientLineUsers)
               .filter(ClientLineUsers.line_user_id == line_user_id,
                       ClientLineUsers.is_active == True))
        if client_id_from_secret:
            q = q.filter(ClientLineUsers.client_id == client_id_from_secret)
        clu = q.first()
        if clu:
            is_lawyer = True
            client_id_from_lawyer = getattr(clu, "client_id", None)

    # 3) 路由決定
    if (not is_secret) and is_lawyer:
        route = "LAWYER"
        chosen_client_id = client_id_from_lawyer
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
        route = "LAWYER"
        chosen_client_id = client_id_from_lawyer or client_id_from_secret
        chosen_client_name = client_name_from_secret if client_id_from_secret == chosen_client_id else None

    # 4) 綁定網址（僅 LOGIN）
    bind_url = None
    if route == "LOGIN" and is_secret:
        base = os.getenv("API_BASE_URL") or os.getenv("APP_BASE_URL") or "https://example.com"
        bind_url = f"{base}/api/tenant/bind-user?code={quote(text_in)}"
        if client_id_from_secret:
            bind_url += f"&client_id={quote(str(client_id_from_secret))}"

    # 5) 若只知道 client_id，補查 client_name
    if chosen_client_id and not chosen_client_name:
        rec = db.query(LoginUser).filter(LoginUser.client_id == str(chosen_client_id)).first()
        if rec:
            chosen_client_name = rec.client_name

    return {
        "success": bool(is_secret),
        "is_lawyer": bool(is_lawyer),
        "client_id": chosen_client_id,
        "client_name": chosen_client_name,
        "route": route,
        "bind_url": bind_url,
    }

# =========== 方案查詢 ============
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
        ClientLineUsers.is_active == True
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

# =========== 健康檢查/測試 ============
@lawyer_router.get("/verify-secret/ping")
async def verify_secret_ping():
    return {"ok": True, "ts": datetime.datetime.utcnow().isoformat()}

class CaseSearchIn(BaseModel):
    text: str
    line_user_id: Optional[str] = None

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
          .order_by(CaseRecord.updated_at.desc())
          .limit(5)
          .all()
    )
    if not rows:
        return {"message": f"找不到符合「{key}」的案件"}

    def fmt(r):
        return f"{r.client} / {r.case_type or ''} / {r.case_number or r.case_id} / 進度:{r.progress or '-'}"

    return {"message": "查到以下案件：\n" + "\n".join(fmt(r) for r in rows)}
