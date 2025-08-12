# api/routes/user_routes.py
# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, Tuple

from api.database import get_db

user_router = APIRouter(prefix="/api/user", tags=["user"])

# ---------- I/O ----------
class UserRegisterIn(BaseModel):
    line_user_id: str = Field(..., min_length=5)
    text: str = Field(..., description="原訊息：可能是『登錄 XXX』或『是/否』")

class UserRegisterOut(BaseModel):
    success: bool
    message: str
    code: Optional[str] = None        # need_confirm / already_lawyer / invalid_format / no_pending
    expected_name: Optional[str] = None

class MyCasesIn(BaseModel):
    line_user_id: str = Field(..., min_length=5)

class MyCasesOut(BaseModel):
    success: bool
    message: str
    count: Optional[int] = None
    name: Optional[str] = None

# ---------- Helpers ----------

def _parse_intent(text_msg: str) -> Tuple[str, Optional[str]]:
    msg = (text_msg or "").strip()
    if not msg:
        return "none", None

    # 🔧 同時支援"登錄"和"登陸"
    if msg.startswith("登錄"):
        name = msg.replace("登錄", "", 1).strip()
        return ("prepare", name) if name else ("none", None)
    elif msg.startswith("登陸"):  # 相容舊格式
        name = msg.replace("登陸", "", 1).strip()
        return ("prepare", name) if name else ("none", None)

    if msg in ("是", "yes", "Yes", "YES"):
        return "confirm_yes", None
    if msg in ("否", "no", "No", "NO"):
        return "confirm_no", None
    if msg in ("?", "？"):
        return "show_cases", None
    return "none", None

def _is_lawyer(db: Session, line_user_id: str) -> bool:
    row = db.execute(text("""
        SELECT 1 FROM client_line_users
        WHERE line_user_id = :lid AND is_active = TRUE
        LIMIT 1
    """), {"lid": line_user_id}).first()
    return bool(row)

# ---------- 兩段式登記 ----------
@user_router.post("/register", response_model=UserRegisterOut)
def register_user(p: UserRegisterIn, db: Session = Depends(get_db)):
    intent, name = _parse_intent(p.text)

    # A) 準備階段：使用者輸入「登錄 XXX」
    if intent == "prepare":
        # 律師一律擋
        if _is_lawyer(db, p.line_user_id):
            return JSONResponse(
                status_code=409,
                content={
                    "success": False,
                    "code": "already_lawyer",
                    "message": "您已是律師，無需登記一般用戶"
                }
            )
        # 暫存成「確認中」
        db.execute(text("""
            INSERT INTO pending_line_users (line_user_id, expected_name, status)
            VALUES (:lid, :name, 'confirming')
            ON CONFLICT (line_user_id) DO UPDATE
              SET expected_name = EXCLUDED.expected_name,
                  status = 'confirming',
                  updated_at = NOW()
        """), {"lid": p.line_user_id, "name": name})
        db.commit()
        return UserRegisterOut(
            success=False,
            code="need_confirm",
            expected_name=name,
            message=f"您確認大名是 {name} 嗎？請回覆「是」或「否」"
        )

    # B) 使用者回覆「是」：才正式登記
    if intent == "confirm_yes":
        row = db.execute(text("""
            SELECT expected_name FROM pending_line_users
            WHERE line_user_id = :lid AND status = 'confirming'
        """), {"lid": p.line_user_id}).first()
        if not row:
            return UserRegisterOut(success=False, code="no_pending", message="找不到待確認的姓名，請輸入「登錄 您的大名」")
        name = row[0]
        db.execute(text("""
            UPDATE pending_line_users
            SET status = 'pending', updated_at = NOW()
            WHERE line_user_id = :lid
        """), {"lid": p.line_user_id})
        db.commit()
        return UserRegisterOut(success=True, expected_name=name, message=f"已登記：{name}")

    # C) 使用者回覆「否」：取消
    if intent == "confirm_no":
        db.execute(text("""
            DELETE FROM pending_line_users
            WHERE line_user_id = :lid AND status = 'confirming'
        """), {"lid": p.line_user_id})
        db.commit()
        return UserRegisterOut(success=False, message="已取消，請重新輸入「登錄 您的大名」")

    # D) 問號：查個人案件（整合原 /my-cases 的邏輯）
    if intent == "show_cases":
        row = db.execute(text("""
            SELECT expected_name
            FROM pending_line_users
            WHERE line_user_id = :lid AND status IN ('pending','registered','confirming')
        """), {"lid": p.line_user_id}).first()
        if not row or not row[0]:
            return UserRegisterOut(success=False, code="invalid_format",
                                   message="請輸入「登錄 您的大名」才能查詢自己的案件")
        expected_name = row[0]
        from api.models_cases import CaseRecord
        rows = (db.query(CaseRecord)
                  .filter(CaseRecord.client == expected_name)
                  .order_by(CaseRecord.updated_at.desc())
                  .limit(5).all())
        if not rows:
            return UserRegisterOut(success=True, message=f"{expected_name} 尚無案件資料")
        def fmt(r): return f"{r.client} / {r.case_type or ''} / {r.case_number or r.case_id} / 進度:{r.progress or '-'}"
        return UserRegisterOut(success=True, message="你的案件：\n" + "\n".join(fmt(r) for r in rows))

    # 其它文字一律不寫入
    return UserRegisterOut(success=False, code="invalid_format", message="請輸入「登錄 您的大名」")

# ---------- 查個人案件（給「?」用） ----------
@user_router.post("/my-cases", response_model=MyCasesOut)
def my_cases(p: MyCasesIn, db: Session = Depends(get_db)):
    row = db.execute(text("""
        SELECT expected_name
        FROM pending_line_users
        WHERE line_user_id = :lid AND status IN ('pending','registered')
    """), {"lid": p.line_user_id}).first()
    if not row or not row[0]:
        return MyCasesOut(success=False, message="請輸入「登錄 您的大名」才能查詢自己的案件")

    expected_name = row[0]
    from api.models_cases import CaseRecord
    q = (db.query(CaseRecord)
           .filter(CaseRecord.client == expected_name)
           .order_by(CaseRecord.updated_at.desc())
           .limit(5))
    rows = q.all()

    if not rows:
        return MyCasesOut(success=True, name=expected_name, count=0, message=f"{expected_name} 尚無案件資料")

    def fmt(r):
        return f"{r.client} / {r.case_type or ''} / {r.case_number or r.case_id} / 進度:{r.progress or '-'}"

    msg = "你的案件：\n" + "\n".join(fmt(r) for r in rows)
    return MyCasesOut(success=True, name=expected_name, count=len(rows), message=msg)
