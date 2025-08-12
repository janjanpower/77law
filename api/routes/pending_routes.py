# api/routes/pending_routes.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, Literal
from sqlalchemy.orm import Session
from sqlalchemy import select
# api/routes/pending_routes.py — ensure alias name exists
from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
def health():
    return {"ok": True}

from api.database import get_db
from api.models_control import (
    PendingLineUser,
    track_pending_central,
    track_pending_in_tenant,
    ClientLineUsers,   # 注意：複數
    LoginUser,
)

router = APIRouter(prefix="/api", tags=["pending"])


# ====== 輸入 / 輸出 Schema ======

class PendingIn(BaseModel):
    line_user_id: str
    expected_name: Optional[str] = None
    # 不從前端接 client_id；由後端自行推導


class PendingOut(BaseModel):
    ok: bool
    where: Literal["tenant", "control"]
    status: Literal["already_bound", "pending"]
    block_login_prompt: bool
    client_id: Optional[str] = None
    client_name: Optional[str] = None
    person_name: Optional[str] = None
    message: Optional[str] = None     # 已綁定給用戶看的訊息
    login_text: Optional[str] = None  # 未綁定時，提示用戶輸入「登陸 XXX」


# ====== 小工具 ======

def _resolve_binding(db: Session, line_user_id: str) -> Optional[ClientLineUsers]:
    """查此 LINE 使用者是否已綁定於某事務所（client）。"""
    return db.query(ClientLineUsers).filter(
        ClientLineUsers.line_user_id == line_user_id
    ).first()


def _get_tenant_conn_by_client(db: Session, client_id: str) -> tuple[str, Optional[str]]:
    """
    由 client_id 取得該租戶的資料庫連線字串與顯示名稱。
    這裡示範從 login_users 取 tenant_db_url / client_name。
    """
    rec: Optional[LoginUser] = db.query(LoginUser).filter(LoginUser.client_id == client_id).first()
    if not rec or not getattr(rec, "tenant_db_url", None):
        raise HTTPException(status_code=404, detail="tenant_db_url not found for client_id")
    return rec.tenant_db_url, getattr(rec, "client_name", None)


# ====== 核心端點：/api/safe/pending/track ======

@router.post("/safe/pending/track", response_model=PendingOut)
def safe_pending_track(p: PendingIn, db: Session = Depends(get_db)):
    """
    規則：
    1) 若 line_user_id 已綁定在任一事務所 → 回傳 status=already_bound、block_login_prompt=True
       並提示「直接輸入 ? 可查詢進度」，不再要求輸入『登陸 XXX』。
    2) 若尚未綁定 → 記錄 pending（能判斷 client 就寫 tenant，否則寫 control），
       並回傳 status=pending、login_text（引導輸入『登陸 XXX』）。
    """
    line_user_id = (p.line_user_id or "").strip()
    if not line_user_id:
        raise HTTPException(status_code=400, detail="line_user_id required")

    # --- A) 已綁定就直接阻斷登入提示 ---
    bound = _resolve_binding(db, line_user_id)
    if bound:
        client_id = getattr(bound, "client_id", None)
        client_name = getattr(bound, "client_name", None)
        person_name = getattr(bound, "person_name", None)

        return PendingOut(
            ok=True,
            where="tenant" if client_id else "control",
            status="already_bound",
            block_login_prompt=True,
            client_id=client_id,
            client_name=client_name,
            person_name=person_name,
            message=(
                f"您已綁定 {client_name}。之後直接輸入「?」即可查詢案件進度。"
                if client_name else
                "您已完成綁定。之後直接輸入「?」即可查詢案件進度。"
            ),
            login_text=None,
        )

    # --- B) 未綁定 → 建立/更新 pending 記錄 ---
    # 嘗試由其他可信線索判斷 client（目前僅示範『尚未綁定＝無 client』，因此先寫 control）
    # 若你的流程能從別處推得 client_id，可在此補上推導邏輯。
    client_id = None

    if client_id:
        tenant_db_url, tenant_client_name = _get_tenant_conn_by_client(db, client_id)
        u: PendingLineUser = track_pending_in_tenant(
            client_id=client_id,
            tenant_db_url=tenant_db_url,
            line_user_id=line_user_id,
            expected_name=p.expected_name,
        )
        where = "tenant"
        display_client_name = tenant_client_name
    else:
        u: PendingLineUser = track_pending_central(
            db,
            line_user_id=line_user_id,
            expected_name=p.expected_name,
        )
        where = "control"
        display_client_name = None

    # 準備引導文案（未綁定才需要）
    expected = (u.expected_name or p.expected_name or "").strip()
    if expected:
        login_text = (
            "請在聊天室輸入：\n\n"
            f"登陸 {expected}\n\n"
            "完成綁定後，輸入「?」即可查詢案件進度。"
        )
    else:
        login_text = (
            "請在聊天室輸入：\n\n"
            "登陸 當事人姓名\n\n"
            "例如：登陸 王小明\n"
            "完成綁定後，輸入「?」即可查詢案件進度。"
        )

    return PendingOut(
        ok=True,
        where=where,
        status="pending",
        block_login_prompt=False,
        client_id=client_id,
        client_name=display_client_name,
        person_name=None,
        message=None,
        login_text=login_text,
    )

pending_router = router
