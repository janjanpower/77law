# api/routes/user_routes.py — provides /api/user/register and /api/user/my-cases
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import select, desc

# Absolute imports for Heroku compatibility
from api.database import get_db

# Optional models (guarded import to avoid hard crashes if not present)
try:
    from api.models_control import PendingLineUsers, ClientLineUsers
except Exception:
    PendingLineUsers = None  # type: ignore
    ClientLineUsers = None   # type: ignore

try:
    from api.models_case import CaseRecord  # 假設你的案件模型是這個名稱
except Exception:
    CaseRecord = None  # type: ignore

user_router = APIRouter(prefix="/user", tags=["user"])

# ---------- Schemas ----------
class RegisterIn(BaseModel):
    line_user_id: str = Field(..., description="LINE 使用者 ID")
    name: Optional[str] = Field("", description="當事人姓名（可選）")

class RegisterOut(BaseModel):
    success: bool
    message: str

class MyCasesIn(BaseModel):
    line_user_id: str = Field(..., description="LINE 使用者 ID")

class CaseItem(BaseModel):
    case_id: str
    client: Optional[str] = None
    case_type: Optional[str] = None
    progress: Optional[str] = None
    updated_at: Optional[str] = None

class MyCasesOut(BaseModel):
    success: bool
    line_user_id: str
    cases: List[CaseItem] = []

# ---------- Endpoints ----------

@user_router.post("/register", response_model=RegisterOut)
def register_user(payload: RegisterIn, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    最小可用版：
    - 若存在 PendingLineUsers，寫入/更新 pending 紀錄；否則只回成功訊息，留給 n8n/前端後續處理。
    """
    lid = payload.line_user_id.strip()
    name = (payload.name or "").strip()

    if not lid:
        raise HTTPException(status_code=400, detail="line_user_id 必填")

    if PendingLineUsers is not None:
        # upsert by line_user_id
        existing = db.query(PendingLineUsers).filter(PendingLineUsers.line_user_id == lid).one_or_none()
        if existing:
            if name:
                existing.expected_name = name
            db.add(existing)
        else:
            rec = PendingLineUsers(line_user_id=lid, expected_name=name or None, status="pending")
            db.add(rec)
        db.commit()

    msg = "已建立註冊請求" + (f"：{name}" if name else "")
    return {"success": True, "message": msg}

@user_router.post("/my-cases", response_model=MyCasesOut)
def my_cases(payload: MyCasesIn, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    回傳該 line_user_id 綁定的事務所所屬案件；
    - 若模型存在則做真實查詢；
    - 若缺模型則回傳空列表（避免 404）。
    """
    lid = payload.line_user_id.strip()
    results: List[Dict[str, Any]] = []

    if not lid:
        raise HTTPException(status_code=400, detail="line_user_id 必填")

    if ClientLineUsers is not None and CaseRecord is not None:
        # 取使用者綁定到的客戶/事務所
        bound_rows = db.query(ClientLineUsers).filter(
            ClientLineUsers.line_user_id == lid,
            ClientLineUsers.is_active.is_(True)
        ).all()
        client_ids = [r.client_id for r in bound_rows]

        if client_ids:
            # 查案件
            q = db.query(CaseRecord).filter(CaseRecord.client_id.in_(client_ids)).order_by(desc(CaseRecord.updated_at)).limit(50)
            for row in q.all():
                results.append({
                    "case_id": getattr(row, "case_id", ""),
                    "client": getattr(row, "client", None),
                    "case_type": getattr(row, "case_type", None),
                    "progress": getattr(row, "progress", None),
                    "updated_at": getattr(row, "updated_at", None).isoformat() if getattr(row, "updated_at", None) else None,
                })

    return {"success": True, "line_user_id": lid, "cases": results}
