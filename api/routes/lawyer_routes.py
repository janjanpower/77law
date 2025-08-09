# api/routes/lawyer_routes.py
# -*- coding: utf-8 -*-

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
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
    allow_bind: bool


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
def bind_user(payload: BindLawyerIn):
    """
    綁定用戶 API
    - 如果 allow_bind = False，直接拒絕
    - 如果 allow_bind = True，直接回傳假資料（不連資料庫）
    """

    # 如果不是 True，直接拒絕
    if not payload.allow_bind:
        return BindLawyerOut(
            success=False,
            reason="bind_not_allowed"
        )

    # 假資料（不連資料庫）
    fake_tenant = {
        "id": "C001",
        "name": "喜憨兒事務所",
        "plan": "basic",
        "limit": 3,
        "usage": 1
    }

    # 直接回傳綁定成功
    return BindLawyerOut(
        success=True,
        tenant={
            "id": fake_tenant["id"],
            "name": fake_tenant["name"]
        },
        role="lawyer"
    )

# 假資料 - 暗號 -> 事務所資料
TENANTS = {
    "55688": {
        "id": "C001",
        "name": "喜憨兒事務所",
        "plan": "basic",
        "limit": 3,
        "usage": 1
    }
}
@router.post("/check_tenant_plan")
def check_tenant_plan(data: TenantCheckRequest):
    if data.is_lawyer:  # True 才回整包假資料
        return {"success": True, "tenants": TENANTS}

    tenant_info = TENANTS.get(data.tenant_code)
    if not tenant_info:
        return {"success": False, "reason": "invalid_tenant_code"}
    return {
        "success": True,
        "tenant": tenant_info["name"],
        "limit": tenant_info["limit"],
        "usage": tenant_info["usage"],
    }
