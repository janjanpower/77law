# api/routes/lawyer_routes.py
# -*- coding: utf-8 -*-

import datetime
from typing import Optional, Dict, Any

from sqlalchemy import and_, func, select, text

from api.database import get_db
from api.models_control import LoginUser, ClientLineUsers
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session


# 你專案現有的 DB 與模型

router = APIRouter(prefix="/api/lawyer", tags=["lawyer"])

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

# ---------- Helper：用暗號找事務所 ----------
def resolve_client_by_code(db: Session, tenant_code: str) -> Optional[LoginUser]:
    """
    先把【暗號】當作 client_id 查；若你未來有獨立的暗號表，再改掉這裡的邏輯即可。
    如需用 client_name 查，放寬為 or 條件。
    """
    client = (
        db.query(LoginUser)
        .filter(LoginUser.client_id == tenant_code, LoginUser.is_active == True)
        .first()
    )
    # 若要兼容用 client_name 當暗號，可加：
    if not client:
        client = (
            db.query(LoginUser)
            .filter(LoginUser.client_name == tenant_code, LoginUser.is_active == True)
            .first()
        )
    return client



class TenantCheckRequest(BaseModel):
    tenant_code: str
    line_user_id: str


def count_current_usage(db: Session, client_id: str) -> int:
    """計算目前已啟用的 LINE 綁定數（你可依需求只算律師或全部）"""
    return (
        db.query(ClientLineUsers)
        .filter(ClientLineUsers.client_id == client_id, ClientLineUsers.is_active == True)
        .count()
    )

def upsert_lawyer_binding(db: Session, client_id: str, line_user_id: str) -> bool:
    """
    綁定為律師（冪等）：
    - 若已存在此 line_user_id → 更新 client_id / user_role='lawyer' / is_active=True
    - 若不存在 → 新增一筆
    回傳 True 表示狀態已是律師且綁到該 client；False 表示其他不可預期失敗
    """
    row = (
        db.query(ClientLineUsers)
        .filter(ClientLineUsers.line_user_id == line_user_id)
        .first()
    )
    if row:
        # 已存在就更新到律師身分
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

# ---------- 綁定成功 ----------


class BindUserRequest(BaseModel):
    success: bool = Field(..., description="n8n 判斷為 true 才執行綁定")
    client_name: str
    user_id: str

class BindUserResponse(BaseModel):
    success: bool
    client_name: str
    plan_type: str | None = None
    limit: int = 0
    usage: int = 0
    available: int = 0
    message: str | None = None


def _build_plan_message(title: str, client_name: str, plan_type: str | None, limit_val: int | None, usage_val: int) -> str:
    """統一格式：把方案/上限/當前填入訊息"""
    plan = plan_type or "未設定"
    lim  = str(limit_val) if isinstance(limit_val, int) else "未設定"
    return (
        f"{title}\n"
        f"事務所：{client_name}\n"
        f"方案：{plan}\n"
        f"上限人數：{lim}\n"
        f"當前人數：{usage_val}"
    )

@router.post("/bind-user", response_model=BindUserResponse)
def bind_user(payload: BindUserRequest, db: Session = Depends(get_db)):
    if not payload.success:
        return BindUserResponse(
            success=False,
            client_name=payload.client_name,
            message="success=false，未執行綁定"
        )

    # 1) 找到對應的 tenant/login_user（以 client_name 為準；你也可改用 client_id）
    tenant: LoginUser | None = db.execute(
        select(LoginUser).where(LoginUser.client_name == payload.client_name)
    ).scalars().first()

    if not tenant:
        raise HTTPException(status_code=404, detail="找不到對應的事務所")

    client_id = tenant.client_id
    max_users = int(tenant.max_users or 0)
    plan_type = tenant.plan_type

    # 2) upsert 綁定
    upsert_sql = text("""
        INSERT INTO client_line_users (client_id, client_name, line_user_id)
        VALUES (:client_id, :client_name, :line_user_id)
        ON CONFLICT (client_id, line_user_id) DO NOTHING
        RETURNING id;
    """)
    inserted = db.execute(upsert_sql, {
        "client_id": client_id,
        "client_name": payload.client_name,
        "line_user_id": payload.user_id
    }).first()

    # 3) 即時計算 usage（該 client_id 的當前綁定數）
    count_sql = text("""
        SELECT COUNT(*)::int AS c
        FROM client_line_users
        WHERE client_id = :client_id
        AND is_active = TRUE
    """)
    usage = db.execute(count_sql, {"client_id": client_id}).scalar_one()

    available = max(0, max_users - usage)

    available = max(0, max_users - usage)

    # 5) 組回應訊息（含 方案/上限/當前）
    if max_users and usage >= max_users:
        # 額滿
        msg = _build_plan_message("⚠️ 已額滿，需要升級方案", payload.client_name, plan_type, max_users, usage)
        ok = False
    else:
        # 新增或原已綁定都以成功呈現，但文案不同
        base = "🎉 綁定成功" if inserted else "ℹ️ 已綁定於該事務所"
        msg = _build_plan_message(base, payload.client_name, plan_type, max_users, usage)
        ok = True

    return BindUserResponse(
        success=ok,
        client_name=payload.client_name,
        plan_type=plan_type,
        limit=max_users,
        usage=usage,
        available=available,
        message=msg
    )

#===========驗證 secret_code ============
class VerifySecretIn(BaseModel):
    # n8n/簡化後的格式
    text: Optional[str] = None
    user_id: Optional[str] = None
    reply_token: Optional[str] = None
    eventType: Optional[str] = None
    # 也允許直接丟 LINE 原始 webhook body
    body: Optional[Dict[str, Any]] = None

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

@router.post("/verify-secret")
async def verify_secret(request: Request, db: Session = Depends(get_db)):
    payload = await request.json()

    # 嘗試讀取簡化格式
    text = payload.get("text")
    user_id = payload.get("user_id")
    reply_token = payload.get("reply_token")
    event_type = payload.get("eventType")

    # 如果簡化格式沒值，改讀整包 LINE body
    if not text and "body" in payload:
        text, user_id, reply_token, event_type = extract_from_line_body(payload.get("body"))

    # 沒有 text 就直接回 false
    if not text:
        return {"success": False, "client_name": None}

    # 去除左右空白後比對 secret_code（完全相符）
    match = (
        db.query(LoginUser)
        .filter(func.btrim(LoginUser.secret_code) == text.strip())
        .first()
    )

    if match:
        return {"success": True, "client_name": getattr(match, "client_name", None)}
    return {"success": False, "client_name": None}



#===========確認 plan type ============


def _extract_client_name(payload: dict) -> str | None:
    """
    支援多種鍵名來源：
    - client_name
    - tenant
    - body.client_name / body.tenant
    - data.client_name / data.tenant
    """
    if not isinstance(payload, dict):
        return None
    # 直接鍵
    name = payload.get("client_name") or payload.get("tenant")
    if isinstance(name, str) and name.strip():
        return name.strip()

    # 可能包在 body 或 data
    for key in ("body", "data"):
        sub = payload.get(key)
        if isinstance(sub, dict):
            name = sub.get("client_name") or sub.get("tenant")
            if isinstance(name, str) and name.strip():
                return name.strip()

    return None

@router.post("/check-client-plan")
async def check_client_plan(request: Request, db: Session = Depends(get_db)):
    try:
        payload = await request.json()
    except Exception:
        return {
            "success": False, "client_name": None, "plan_type": None,
            "limit": None, "usage": None, "available": None, "message": "invalid_json"
        }

    client_name = _extract_client_name(payload)
    if not client_name:
        return {
            "success": False, "client_name": None, "plan_type": None,
            "limit": None, "usage": None, "available": None, "message": "client_name_required"
        }

    user = (
        db.query(LoginUser)
        .filter(func.btrim(LoginUser.client_name) == client_name.strip())
        .first()
    )
    if not user:
        return {
            "success": False, "client_name": client_name, "plan_type": None,
            "limit": None, "usage": None, "available": None, "message": "client_not_found"
        }

    # 方案與上限（沿用既有欄位）
    plan_type = getattr(user, "plan_type", None)
    limit_val = getattr(user, "user_limit", None) or getattr(user, "max_users", None)

    # 🔁 B 方案：即時計數，不讀 current_users
    usage_val = db.query(func.count(ClientLineUsers.id)).filter(
        ClientLineUsers.client_id == user.client_id,
        ClientLineUsers.is_active == True
    ).scalar() or 0
    usage_val = int(usage_val)

    available = max(limit_val - usage_val, 0) if isinstance(limit_val, int) else None

    # 文案
    if isinstance(limit_val, int) and usage_val >= limit_val:
        msg = _build_plan_message("⚠️ 已額滿，需要升級方案", user.client_name, plan_type, limit_val, usage_val)
        ok = False
    else:
        msg = _build_plan_message("✅ 目前方案資訊", user.client_name, plan_type, limit_val, usage_val)
        ok = True

    return {
        "success": ok,
        "client_name": getattr(user, "client_name", client_name),
        "plan_type": plan_type,
        "limit": limit_val,
        "usage": usage_val,
        "available": available,
        "message": msg
    }
