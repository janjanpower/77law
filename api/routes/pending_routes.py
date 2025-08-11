# api/routes/pending_routes.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from api.database import get_db
from api.models_control import (
    PendingLineUser,
    track_pending_central,
    track_pending_in_tenant,
    ClientLineUsers,   # ← 複數
    LoginUser,
)

router = APIRouter(prefix="/api", tags=["pending"])

class PendingIn(BaseModel):
    line_user_id: str
    expected_name: Optional[str] = None
    # 不接受 client_id 來自前端；一律由伺服器推導

def _resolve_client_id_by_line(db: Session, line_user_id: str) -> Optional[str]:
    """
    由可信資料找出使用者屬於哪個事務所：
      1) 已綁定表 client_line_users
    """
    clu = db.query(ClientLineUsers).filter(
        ClientLineUsers.line_user_id == line_user_id
    ).first()
    return getattr(clu, "client_id", None) if clu else None

def _get_tenant_db_url_by_client(db: Session, client_id: str) -> str:
    """
    由 client_id 取得該租戶的資料庫連線字串。
    這裡示範從 login_users 取；若你另有 tenants 表，請改對應查詢。
    """
    rec = db.query(LoginUser).filter(LoginUser.client_id == client_id).first()
    tenant_db_url = getattr(rec, "tenant_db_url", None) if rec else None
    if not tenant_db_url:
        raise HTTPException(status_code=404, detail="tenant_db_url not found for client_id")
    return tenant_db_url

@router.post("/safe/pending/track")
def safe_pending_track(p: PendingIn, db: Session = Depends(get_db)):
    # 1) 嘗試定位此 LINE 使用者屬於哪個事務所
    client_id = _resolve_client_id_by_line(db, p.line_user_id)

    # 2) 寫入對應 DB（能判斷就寫 tenant；否則寫中央）
    if client_id:
        tenant_db_url = _get_tenant_db_url_by_client(db, client_id)
        u = track_pending_in_tenant(
            client_id=client_id,
            tenant_db_url=tenant_db_url,
            line_user_id=p.line_user_id,
            expected_name=p.expected_name,
        )
        scope = "tenant"
    else:
        u = track_pending_central(db, line_user_id=p.line_user_id, expected_name=p.expected_name)
        scope = "control"

    login_text = f"登陸 {u.expected_name}" if u.expected_name else "登陸"
    return {"ok": True, "where": scope, "login_text": login_text}
