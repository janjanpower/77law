# api/routes/user_routes.py
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text
from api.database import get_db

user_router = APIRouter(prefix="/api/user", tags=["user"])

class UserRegisterIn(BaseModel):
    line_user_id: str
    text: str  # 原訊息，例如 "登陸 王小明"

@user_router.post("/register")
def user_register(p: UserRegisterIn, db: Session = Depends(get_db)):
    msg = (p.text or "").strip()
    if not msg.startswith("登陸"):
        return {"success": False, "message": "請輸入「登陸 您的大名」"}
    expected_name = msg.replace("登陸", "", 1).strip()
    if not expected_name:
        return {"success": False, "message": "請輸入「登陸 您的大名」"}
    db.execute(text("""
        INSERT INTO pending_line_users (line_user_id, expected_name, status)
        VALUES (:lid, :name, 'pending')
        ON CONFLICT (line_user_id) DO UPDATE
          SET expected_name = EXCLUDED.expected_name,
              status = 'pending',
              updated_at = NOW()
    """), {"lid": p.line_user_id, "name": expected_name})
    db.commit()
    return {"success": True, "expected_name": expected_name, "message": f"已登記：{expected_name}"}

class MyCasesIn(BaseModel):
    line_user_id: str

@user_router.post("/my-cases")
def my_cases(p: MyCasesIn, db: Session = Depends(get_db)):
    row = db.execute(text("""
        SELECT expected_name FROM pending_line_users WHERE line_user_id = :lid
    """), {"lid": p.line_user_id}).first()
    if not row or not row[0]:
        return {"success": False, "message": "請輸入「登陸 您的大名」才能查詢自己的案件"}

    expected_name = row[0]
    from api.models_cases import CaseRecord
    cases = (db.query(CaseRecord)
               .filter(CaseRecord.client == expected_name)
               .order_by(CaseRecord.updated_at.desc())
               .limit(5).all())
    if not cases:
        return {"success": True, "message": f"{expected_name} 尚無案件資料"}

    def fmt(c):
        return f"{c.client} / {c.case_type or ''} / {c.case_number or c.case_id} / 進度:{c.progress or '-'}"

    return {"success": True, "name": expected_name,
            "count": len(cases), "message": "你的案件：\n" + "\n".join(fmt(c) for c in cases)}
