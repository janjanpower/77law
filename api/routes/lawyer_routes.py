# api/routes/lawyer_routes.py（節錄重點，直接覆蓋 verify-secret 也可）

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text
from api.database import get_db
import re

router = APIRouter(prefix="/api/lawyer", tags=["lawyer"])

TABLE_BOUND_USER = "public.client_line_users"   # 依你的實際資料表調整
TABLE_BOUND_LAWYER = "public.login_users"      # 若無此表可忽略 try/except

class VerifyIn(BaseModel):
    text: str = ""
    line_user_id: str
    debug: bool = False  # 新增：需要時帶 true 方便除錯

def _normalize_text(s: str) -> str:
    if not s:
        return ""
    # 去零寬空白/換行
    s = re.sub(r"[\u200B-\u200D\uFEFF]", "", s)
    # 全形空白 -> 半形
    s = s.replace("\u3000", " ")
    return s.strip()

def _has_question(s: str) -> bool:
    return bool(re.search(r"[?？]", s))

def _get_role(db: Session, lid: str) -> str | None:
    if not lid:
        return None
    # 一般用戶
    row_user = db.execute(
        text(f"""
          SELECT 1 FROM {TABLE_BOUND_USER}
          WHERE line_user_id = :lid
            AND COALESCE(is_active, TRUE) = TRUE
          LIMIT 1
        """),
        {"lid": lid},
    ).first()
    if row_user:
        return "USER"

    # 律師（若你的律師不綁 LINE，可改為其他判斷）
    try:
        row_lawyer = db.execute(
            text(f"""
              SELECT 1 FROM {TABLE_BOUND_LAWYER}
              WHERE line_user_id = :lid
                AND COALESCE(is_active, TRUE) = TRUE
              LIMIT 1
            """),
            {"lid": lid},
        ).first()
        if row_lawyer:
            return "LAWYER"
    except Exception:
        pass

    return None

@router.post("/verify-secret")
def verify_secret(payload: VerifyIn, db: Session = Depends(get_db)):
    text_in = _normalize_text(payload.text or "")
    lid = (payload.line_user_id or "").strip()

    role = _get_role(db, lid)
    is_q = _has_question(text_in)

    # 規則 1：已綁定的一般用戶 + 包含問號 → REGISTERED_USER
    if role == "USER" and is_q:
        out = {"route": "REGISTERED_USER"}
    # 規則 2：未綁定 + 「登錄 XXX」 → REGISTER
    elif role is None and re.match(r"^登(錄|陸)\s+.+", text_in):
        out = {"route": "REGISTER"}
    # 規則 3：律師 → LAWYER
    elif role == "LAWYER":
        out = {"route": "LAWYER"}
    # 其餘 → USER
    else:
        out = {"route": "USER"}

    if payload.debug:
        out["debug"] = {
            "text_in": text_in,
            "has_question": is_q,
            "role_detected": role,
            "line_user_id_len": len(lid),
        }
    return out
