# api/routes/lawyer_routes.py
# -*- coding: utf-8 -*-

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, constr
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

# 你專案現有的 DB 與模型
from api.database import get_db
from api.models_control import LoginUser, ClientLineUsers

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

# ---------- Endpoints ----------

@router.post("/check-limit", response_model=CheckLimitOut)
def check_limit(payload: CheckLimitIn, db: Session = Depends(get_db)):
    client = resolve_client_by_code(db, payload.tenant_code)
    if not client:
        return CheckLimitOut(success=False, reason="invalid_tenant_code")

    limit = int(getattr(client, "max_users", 0) or 0)
    usage = count_current_usage(db, client.client_id)

    if limit and usage >= limit:
        return CheckLimitOut(
            success=False,
            reason="limit_reached",
            limit=limit,
            usage=usage,
            tenant={"id": client.client_id, "name": client.client_name},
        )

    return CheckLimitOut(
        success=True,
        limit=limit,
        usage=usage,
        tenant={"id": client.client_id, "name": client.client_name},
    )


@router.post("/bind-user", response_model=BindLawyerOut)
def bind_user(payload: BindLawyerIn, db: Session = Depends(get_db)):
    client = resolve_client_by_code(db, payload.tenant_code)
    if not client:
        return BindLawyerOut(success=False, reason="invalid_tenant_code")

    # （可選）保守起見再檢查一次上限
    limit = int(getattr(client, "max_users", 0) or 0)
    usage = count_current_usage(db, client.client_id)
    if limit and usage >= limit:
        return BindLawyerOut(success=False, reason="limit_reached")

    ok = upsert_lawyer_binding(db, client.client_id, payload.line_user_id)
    if ok:
        return BindLawyerOut(
            success=True,
            tenant={"id": client.client_id, "name": client.client_name},
            role="lawyer",
        )
    return BindLawyerOut(success=False, reason="already_bound")

@router.post("/check_tenant_plan")
def check_tenant_plan(data: TenantCheckRequest):
    # 如果是律師身份，就直接回 TENANTS
    if getattr(data, "is_lawyer", False) is True:
        return {
            "success": True,
            "tenants": TENANTS  # 回整包假資料
        }

    # 一般情況：只回指定 tenant
    tenant_info = TENANTS.get(data.tenant_code)
    if not tenant_info:
        return {"success": False, "reason": "invalid_tenant_code"}
    return {
        "success": True,
        "tenant": tenant_info["name"],
        "limit": tenant_info["limit"],
        "usage": tenant_info["usage"]
    }

TENANTS = {
    "55688": {
        "id": "C001",
        "name": "喜憨兒事務所",
        "plan": "basic",
        "limit": 3,
        "usage": 1
    }

}


class VerifySecretRequest(BaseModel):
    # 使用者傳來的原始訊息（可能含空白或其他字）
    message: constr(strip_whitespace=True, min_length=1)
    # 建議帶上 line_user_id 方便後續綁定
    line_user_id: constr(strip_whitespace=True, min_length=5) | None = None

class VerifySecretResponse(BaseModel):
    success: bool
    client_id: str | None = None
    client_name: str | None = None
    secret_code: str | None = None
    message: str

@router.post("/verify-secret", response_model=VerifySecretResponse)
def verify_secret(req: VerifySecretRequest, db: Session = Depends(get_db)):
    raw = req.message.upper().strip()

    # 只取英數大寫，找出第一組 8 碼候選碼
    import re
    m = re.search(r"[A-Z0-9]{8}", re.sub(r"[^A-Z0-9]", "", raw))
    if not m:
        return VerifySecretResponse(success=False, message="未找到8碼暗號")

    code = m.group(0)

    user = db.query(LoginUser).filter(LoginUser.secret_code == code).first()
    if not user:
        return VerifySecretResponse(success=False, message="暗號無效")

    return VerifySecretResponse(
        success=True,
        client_id=user.client_id,
        client_name=user.client_name,
        secret_code=user.secret_code,
        message="暗號驗證通過"
    )