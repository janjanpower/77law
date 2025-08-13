# api/routes/lawyer_routes.py
# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import re
import datetime
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func, text

from api.database import get_db

# ---- 依你的專案模型命名導入（兩段 try 以增加容錯） ----
try:
    from api.models_control import LoginUser, ClientLineUsers
except Exception:
    # 若你的模型放在別處，這裡可再調整
    from api.models_control import LoginUser, ClientLineUsers  # type: ignore

try:
    from api.models_cases import CaseRecord
except Exception:
    CaseRecord = None  # type: ignore

# 若你的 DB 有 “律師綁定表” 可在 _get_role_by_line_id() 內擴充；此檔以一般用戶綁定為主

# =============== FastAPI Router（!! 供 main.py include_router 使用） ===============
router = APIRouter(prefix="/api/lawyer", tags=["lawyer"])

# =============== DTOs ===============
class VerifySecretIn(BaseModel):
    text: Optional[str] = None
    line_user_id: Optional[str] = None
    user_id: Optional[str] = None  # 相容舊參數名
    body: Optional[Dict[str, Any]] = None  # 允許直接丟 LINE Webhook body
    debug: bool = False

class VerifySecretOut(BaseModel):
    success: bool
    route: str
    client_id: Optional[str] = None
    client_name: Optional[str] = None
    is_lawyer: bool = False
    bind_url: Optional[str] = None
    debug: Optional[Dict[str, Any]] = None

class BindUserRequest(BaseModel):
    success: bool
    user_id: str                 # = line_user_id
    client_id: str               # 由 verify-secret（LOGIN）得到
    role: str = "user"           # 'user' | 'lawyer'

class BindUserResponse(BaseModel):
    success: bool
    client_name: Optional[str] = None
    plan_type: Optional[str] = None
    limit: Optional[int] = None
    usage: Optional[int] = None
    available: Optional[int] = None
    message: Optional[str] = None

class CaseSearchIn(BaseModel):
    text: str
    line_user_id: Optional[str] = None


# =============== Helpers ===============
def _normalize_text(s: Optional[str]) -> str:
    if not s:
        return ""
    # 去零寬字元
    s = re.sub(r"[\u200B-\u200D\uFEFF]", "", s)
    # 全形空白 → 半形
    s = s.replace("\u3000", " ")
    return s.strip()

def _has_question(s: str) -> bool:
    # 只要包含 ? 或 全形 ？ 就算
    return bool(re.search(r"[?？]", s))

def _get_role_by_line_id(db: Session, line_user_id: str) -> Optional[str]:
    """
    用 line_user_id 判斷是否為已綁定的一般用戶（USER）。
    若你也有『律師的 LINE 綁定表』，可在這裡擴充 LAWYER 分支。
    回傳：'USER' | 'LAWYER' | None
    """
    if not line_user_id:
        return None

    # 一般用戶是否已綁定啟用
    row = db.query(ClientLineUsers).filter(
        ClientLineUsers.line_user_id == line_user_id,
        # 允許 is_active 為 True / 1 / 非空
        (ClientLineUsers.is_active.is_(True)) | (ClientLineUsers.is_active == 1)
    ).first()
    if row:
        return "USER"

    # 如需律師也走 LINE 綁定，這裡補你的律師綁定表查詢
    return None

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


# =============== Endpoints ===============

@router.get("/verify-secret/ping")
def verify_secret_ping():
    return {"ok": True, "ts": datetime.datetime.utcnow().isoformat()}


@router.post("/verify-secret", response_model=VerifySecretOut)
async def verify_secret(request: Request, db: Session = Depends(get_db)):
    """
    分流規則（提供給 n8n 的 Switch）：
    1) 已綁定的一般用戶 + 訊息包含 ?/？ ⇒ REGISTERED_USER
    2) 有效暗號且尚未是律師 ⇒ LOGIN（發綁定網址）
    3) 已綁定律師（或已具律師身份） ⇒ LAWYER
    4) 其餘 ⇒ USER
    """
    try:
        payload = await request.json()
    except Exception:
        payload = {}

    text_in = _normalize_text(
        payload.get("text")
        or ((payload.get("body") or {}).get("events", [{}])[0].get("message") or {}).get("text")
        or ""
    )
    line_user_id = (
        payload.get("line_user_id")
        or payload.get("user_id")
        or ((payload.get("body") or {}).get("events", [{}])[0].get("source") or {}).get("userId")
        or ""
    )
    line_user_id = str(line_user_id).strip()
    debug = bool(payload.get("debug"))

    # 1) 角色偵測 & 問號
    role = _get_role_by_line_id(db, line_user_id)
    has_q = _has_question(text_in)

    if role == "USER" and has_q:
        out = {
            "success": False,
            "route": "REGISTERED_USER",
            "client_id": None,
            "client_name": None,
            "is_lawyer": False,
            "bind_url": None,
        }
        if debug:
            out["debug"] = {"text_in": text_in, "role": role, "has_question": has_q, "line_user_id_len": len(line_user_id)}
        return out

    # 2) 驗證事務所暗號（用 LoginUser.secret_code）
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

    # 3) 是否已是律師（若你的律師身份是看別表，這裡可依需求調整）
    is_lawyer = False
    chosen_client_id_from_lawyer = None
    if line_user_id:
        # 這裡示範用 ClientLineUsers 的 user_role 判斷（若你的欄位叫 role / user_role 請自行對應）
        q = db.query(ClientLineUsers).filter(
            ClientLineUsers.line_user_id == line_user_id,
            ClientLineUsers.is_active == True
        )
        if client_id_from_secret:
            q = q.filter(ClientLineUsers.client_id == client_id_from_secret)
        row = q.first()
        if row and str(getattr(row, "user_role", "")).upper() == "LAWYER":
            is_lawyer = True
            chosen_client_id_from_lawyer = getattr(row, "client_id", None)

    # 4) 路由判斷
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
        # 同時符合 → 視為 LAWYER
        route = "LAWYER"
        chosen_client_id = chosen_client_id_from_lawyer or client_id_from_secret
        chosen_client_name = client_name_from_secret if client_id_from_secret == chosen_client_id else None

    # 5) 綁定網址（只在 LOGIN 時提供）
    bind_url = None
    if route == "LOGIN" and is_secret:
        base = os.getenv("API_BASE_URL") or os.getenv("APP_BASE_URL") or ""
        if base:
            from urllib.parse import quote
            bind_url = f"{base.rstrip('/')}/api/tenant/bind-user?code={quote(text_in)}"
            if client_id_from_secret:
                bind_url += f"&client_id={quote(str(client_id_from_secret))}"

    # 若只知道 client_id，補查 client_name
    if chosen_client_id and not chosen_client_name:
        rec = db.query(LoginUser).filter(LoginUser.client_id == str(chosen_client_id)).first()
        if rec:
            chosen_client_name = rec.client_name

    out = {
        "success": bool(is_secret),
        "route": route,
        "client_id": chosen_client_id,
        "client_name": chosen_client_name,
        "is_lawyer": bool(is_lawyer),
        "bind_url": bind_url,
    }
    if debug:
        out["debug"] = {
            "text_in": text_in,
            "role_by_line_id": role,
            "has_question": has_q,
            "is_secret": is_secret,
            "line_user_id_len": len(line_user_id),
        }
    return out


@router.post("/bind-user", response_model=BindUserResponse)
def bind_user(payload: BindUserRequest, db: Session = Depends(get_db)):
    """
    依方案上限綁定。
    上限來源：LoginUser.user_limit / max_users（擇一存在）
    綁定表：client_line_users（以 (client_id, line_user_id) upsert）
    """
    if not payload.success:
        return BindUserResponse(success=False, message="未執行綁定")

    tenant = (
        db.query(LoginUser)
          .filter(LoginUser.client_id == payload.client_id, LoginUser.is_active.is_(True))
          .first()
    )
    if not tenant:
        return BindUserResponse(success=False, message="找不到事務所或未啟用")

    client_id = tenant.client_id
    client_name = tenant.client_name
    plan_type = getattr(tenant, "plan_type", None)
    limit_val = getattr(tenant, "user_limit", None) or getattr(tenant, "max_users", None)
    limit_val = int(limit_val) if isinstance(limit_val, int) or (isinstance(limit_val, str) and limit_val.isdigit()) else None

    # 當前啟用數（僅一般用戶，或全部：依你需求）
    usage_before = db.query(func.count(ClientLineUsers.id)).filter(
        ClientLineUsers.client_id == client_id,
        ClientLineUsers.is_active.is_(True)
    ).scalar() or 0
    usage_before = int(usage_before)

    # 若存在啟用綁定，視為已綁
    existed = db.query(ClientLineUsers).filter(
        ClientLineUsers.client_id == client_id,
        ClientLineUsers.line_user_id == payload.user_id,
        ClientLineUsers.is_active.is_(True)
    ).first()
    if existed:
        msg = _build_plan_message("ℹ️ 已綁定", client_name, plan_type, limit_val, usage_before)
        return BindUserResponse(
            success=True, client_name=client_name, plan_type=plan_type,
            limit=limit_val, usage=usage_before,
            available=(None if limit_val is None else max(0, limit_val - usage_before)),
            message=msg
        )

    # 方案額滿（若要區分 LAWYER/USER 可在此細分）
    if limit_val is not None and usage_before >= limit_val:
        msg = _build_plan_message("⚠️ 已額滿，需要升級方案", client_name, plan_type, limit_val, usage_before)
        return BindUserResponse(
            success=False, client_name=client_name, plan_type=plan_type,
            limit=limit_val, usage=usage_before, available=0, message=msg
        )

    # Upsert
    db.execute(text("""
        INSERT INTO client_line_users (client_id, client_name, line_user_id, user_role, is_active, bound_at)
        VALUES (:client_id, :client_name, :line_user_id, :role, TRUE, NOW())
        ON CONFLICT (client_id, line_user_id)
        DO UPDATE SET client_name = EXCLUDED.client_name,
                      user_role   = EXCLUDED.user_role,
                      is_active   = TRUE,
                      bound_at    = NOW();
    """), {
        "client_id": client_id,
        "client_name": client_name,
        "line_user_id": payload.user_id,
        "role": payload.role
    })
    db.commit()

    usage_now = db.query(func.count(ClientLineUsers.id)).filter(
        ClientLineUsers.client_id == client_id,
        ClientLineUsers.is_active.is_(True)
    ).scalar() or 0
    usage_now = int(usage_now)

    msg = _build_plan_message("🎉 綁定成功", client_name, plan_type, limit_val, usage_now)
    return BindUserResponse(
        success=True, client_name=client_name, plan_type=plan_type,
        limit=limit_val, usage=usage_now,
        available=(None if limit_val is None else max(0, limit_val - usage_now)),
        message=msg
    )


@router.post("/check-client-plan")
async def check_client_plan(request: Request, db: Session = Depends(get_db)):
    """
    查方案上限與使用數（for 前端/自動化顯示）
    """
    try:
        payload = await request.json()
    except Exception:
        return {"success": False, "message": "invalid_json"}

    # 嘗試從 payload 抓 client_name
    client_name = None
    for k in ("client_name", "tenant"):
        v = payload.get(k)
        if isinstance(v, str) and v.strip():
            client_name = v.strip()
            break
    if not client_name:
        body = payload.get("body") or {}
        v = body.get("client_name") or body.get("tenant")
        if isinstance(v, str) and v.strip():
            client_name = v.strip()

    if not client_name:
        return {"success": False, "message": "client_name_required"}

    user = (
        db.query(LoginUser)
          .filter(func.btrim(LoginUser.client_name) == client_name)
          .first()
    )
    if not user:
        return {"success": False, "client_name": client_name, "message": "client_not_found"}

    plan_type = getattr(user, "plan_type", None)
    limit_val = getattr(user, "user_limit", None) or getattr(user, "max_users", None)
    limit_val = int(limit_val) if isinstance(limit_val, int) or (isinstance(limit_val, str) and limit_val.isdigit()) else None

    usage_val = db.query(func.count(ClientLineUsers.id)).filter(
        ClientLineUsers.client_id == user.client_id,
        ClientLineUsers.is_active.is_(True)
    ).scalar() or 0
    usage_val = int(usage_val)

    available = (None if limit_val is None else max(0, limit_val - usage_val))
    msg = _build_plan_message("✅ 目前方案資訊", user.client_name, plan_type, limit_val, usage_val)
    ok = True
    if (limit_val is not None) and usage_val >= limit_val:
        msg = _build_plan_message("⚠️ 已額滿，需要升級方案", user.client_name, plan_type, limit_val, usage_val)
        ok = False

    return {
        "success": ok,
        "client_name": user.client_name,
        "plan_type": plan_type,
        "limit": limit_val,
        "usage": usage_val,
        "available": available,
        "message": msg
    }


@router.post("/case-search")
def case_search(payload: CaseSearchIn, db: Session = Depends(get_db)):
    """
    簡易案件關鍵字查詢
    - 若你已改成 (case_type, case_id) 唯一鍵，可自行擴充條件
    """
    if CaseRecord is None:
        raise HTTPException(status_code=500, detail="CaseRecord model not available")

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
        ct = getattr(r, "case_type", None) or "-"
        cid = getattr(r, "case_id", None) or "-"
        num = getattr(r, "case_number", None) or "-"
        cli = getattr(r, "client", None) or "-"
        prog = getattr(r, "progress", None) or "-"
        return f"{cli} / {ct} / {num or cid} / 進度:{prog}"

    return {"message": "查到以下案件：\n" + "\n".join(fmt(r) for r in rows)}


# =============== /api/user 補充路由（供 main.py import router_user） ===============
router_user = APIRouter(prefix="/api/user", tags=["user"])

class VerifyUserIn(BaseModel):
    line_user_id: str

class VerifyUserOut(BaseModel):
    route: str            # REGISTERED_USER / UNREGISTERED_USER
    role: Optional[str]   # USER / LAWYER / None

@router_user.post("/verify", response_model=VerifyUserOut)
def verify_user(payload: VerifyUserIn, db: Session = Depends(get_db)):
    role = _get_role_by_line_id(db, payload.line_user_id.strip())
    if role == "USER":
        return VerifyUserOut(route="REGISTERED_USER", role=role)
    elif role == "LAWYER":
        return VerifyUserOut(route="LAWYER", role=role)
    else:
        return VerifyUserOut(route="UNREGISTERED_USER", role=None)