# api/routes/user_routes.py
# -*- coding: utf-8 -*-

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging, traceback, re

from api.database import get_db
from api.models_cases import CaseRecord  # 你專案已有的 ORM，若沒有請改用原生 SQL 查案件

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

user_router = APIRouter(prefix="/api/user", tags=["user"])

# -------------------- Pydantic --------------------
class LookupIn(BaseModel):
    line_user_id: Optional[str] = None
    user_name:   Optional[str] = None
    destination: Optional[str] = None
    text:        Optional[str] = None  # 可有可無

    class Config:
        allow_population_by_field_name = True  # 允許用欄位本名或別名

class LookupOut(BaseModel):
    client_id: Optional[str] = None

class RegisterIn(BaseModel):
    line_user_id: str = Field(..., min_length=5)
    user_name:   Optional[str] = None
    client_id:   Optional[str] = None
    text:        Optional[str] = None
    destination: Optional[str] = None
      # 相容舊流程（原始文字）

class RegisterOut(BaseModel):
    success: bool
    message: str
    expected_name: Optional[str] = None
    cases: Optional[List[Dict[str, Any]]] = None

class MyCasesIn(BaseModel):
    line_user_id: str

class MyCasesOut(BaseModel):
    success: bool
    message: str
    count: Optional[int] = None
    name: Optional[str] = None

# -------------------- Helpers --------------------
def _parse_intent(text_msg: str):
    msg = (text_msg or "").strip()
    if not msg:
        return "none", None
    m = re.match(r"^(?:登錄|登陸|登入|登录)\s*(.+)$", msg, flags=re.I)
    if m:
        return "prepare", m.group(1).strip()
    if msg in ("是","yes","Yes","YES"): return "confirm_yes", None
    if msg in ("否","no","No","NO"):   return "confirm_no", None
    if msg in ("?","？"):               return "show_cases", None
    return "none", None

# ==================================================
# 1) 依 LINE 或姓名查 client_id（給 n8n 的「查 client_id」節點）
# ==================================================
@user_router.post("/lookup-client", response_model=LookupOut)
def lookup_client(payload: LookupIn, db: Session = Depends(get_db)):
    line_user_id = (payload.line_user_id or "").strip()
    user_name    = (payload.user_name   or "").strip()
    destination  = (payload.destination or "").strip()

    # 0) 先試：用 LINE Webhook 的 destination 直接映射到事務所
    if destination:
        row = db.execute(text("""
            SELECT client_id
            FROM line_channel_bindings
            WHERE destination_id = :dest AND is_active = TRUE
            LIMIT 1
        """), {"dest": destination}).first()
        if row and row[0]:
            return {"client_id": row[0]}

    # 1) 其次：line_user_id 是否已綁定
    row = db.execute(text("""
        SELECT client_id
        FROM client_line_users
        WHERE line_user_id = :lid AND is_active = TRUE
        LIMIT 1
    """), {"lid": line_user_id}).first()
    if row and row[0]:
        return {"client_id": row[0]}

    # 2) 最後保底：把「登錄 」前綴去掉再對 login_users
    name = re.sub(r"^(?:登錄|登陸|登入|登录)\s+", "", user_name).strip()
    row = db.execute(text("""
        SELECT client_id
        FROM login_users
        WHERE client_name = :name
          AND is_active = TRUE
        LIMIT 1
    """), {"name": name}).first()

    return {"client_id": row[0] if row else None}

# ==================================================
# 2) 註冊（n8n 的「用戶確認註冊」會呼叫）
# ==================================================
@user_router.post("/register", response_model=RegisterOut)
def register_user(payload: RegisterIn, db: Session = Depends(get_db)):
    try:
        lid     = (payload.line_user_id or "").strip()
        name    = (payload.user_name   or "").strip()
        cid     = (payload.client_id   or "").strip()
        text_in = (payload.text        or "").strip()
        dest    = (payload.destination or "").strip()

        # 0) 先從 destination 反推 client_id（若沒帶 cid）
        if not cid and dest:
            row = db.execute(text("""
                SELECT client_id FROM line_channel_bindings
                WHERE destination_id = :dest AND is_active = TRUE
                LIMIT 1
            """), {"dest": dest}).first()
            if row and row[0]:
                cid = row[0]

        # 1) 再從既有綁定表反推（若仍沒 cid）
        if not cid and lid:
            row = db.execute(text("""
                SELECT client_id FROM client_line_users
                WHERE line_user_id = :lid AND is_active = TRUE
                LIMIT 1
            """), {"lid": lid}).first()
            if row and row[0]:
                cid = row[0]

        # 2) 解析「登錄 XXX」→ name，並一律清掉前綴
        if not name and text_in:
            intent, cname = _parse_intent(text_in)
            if intent == "prepare" and cname:
                name = cname.strip()
        name = re.sub(r"^(?:登錄|登陸|登入|登录)\s+", "", name).strip()

        if not lid or not name:
            return RegisterOut(success=False, message="缺少必要欄位(line_user_id/user_name)")

        # 3) 已註冊早退（避免覆蓋 expected_name）
        row = db.execute(text("""
            SELECT 1 FROM pending_line_users
            WHERE line_user_id = :lid
              AND status = 'registered'
            LIMIT 1
        """), {"lid": lid}).first()
        if row:
            # （可選）若此時回推得到了 cid，幫忙回填 client_id 一次
            if cid:
                db.execute(text("""
                    UPDATE pending_line_users
                    SET client_id = :cid, updated_at = NOW()
                    WHERE line_user_id = :lid AND (client_id IS NULL OR client_id = '')
                """), {"cid": cid, "lid": lid})
                db.commit()
            return RegisterOut(success=True, expected_name=name,
                               message="您已完成登錄，請輸入「?」查詢案件進度。")

        # 4) 第一次註冊：有 cid 與無 cid 分支（已加 WHERE，避免覆蓋已註冊）
        if cid:
            db.execute(text("""
                INSERT INTO pending_line_users (client_id, line_user_id, expected_name, status, created_at, updated_at)
                VALUES (:cid, :lid, :name, 'registered', NOW(), NOW())
                ON CONFLICT (client_id, line_user_id)
                DO UPDATE
                SET expected_name = EXCLUDED.expected_name,
                    status        = 'registered',
                    updated_at    = NOW()
                WHERE pending_line_users.status <> 'registered';
            """), {"cid": cid, "lid": lid, "name": name})
        else:
            db.execute(text("""
                INSERT INTO pending_line_users (line_user_id, expected_name, status, created_at, updated_at)
                VALUES (:lid, :name, 'registered', NOW(), NOW())
                ON CONFLICT (line_user_id)
                DO UPDATE
                SET expected_name = EXCLUDED.expected_name,
                    status        = 'registered',
                    updated_at    = NOW()
                WHERE pending_line_users.status <> 'registered';
            """), {"lid": lid, "name": name})
        db.commit()

        # 5)（可選）若剛才無 cid 但此刻能推回，幫忙回填一次
        if not cid and dest:
            row = db.execute(text("""
                SELECT client_id FROM line_channel_bindings
                WHERE destination_id = :dest AND is_active = TRUE
                LIMIT 1
            """), {"dest": dest}).first()
            if row and row[0]:
                cid = row[0]
                db.execute(text("""
                    UPDATE pending_line_users
                    SET client_id = :cid, updated_at = NOW()
                    WHERE line_user_id = :lid AND (client_id IS NULL OR client_id = '')
                """), {"cid": cid, "lid": lid})
                db.commit()
        else:
            db.execute(text("""
                INSERT INTO pending_line_users (line_user_id, expected_name, status, created_at, updated_at)
                VALUES (:lid, :name, 'registered', NOW(), NOW())
                ON CONFLICT (line_user_id)
                DO UPDATE
                SET expected_name = EXCLUDED.expected_name,
                    status        = 'registered',
                    updated_at    = NOW()
                WHERE pending_line_users.status <> 'registered';

            """), {"lid": lid, "name": name})
        db.commit()

        # 回查幾筆案件（有 client_id 就加租戶條件）
        q = db.query(CaseRecord).filter(CaseRecord.client == name)
        if cid:
            q = q.filter(CaseRecord.client_id == cid)
        cases = q.order_by(CaseRecord.updated_at.desc()).limit(5).all()

        if cases:
            lines = [f"歡迎 {name}！註冊成功。", "", f"找到 {len(cases)} 件案件："]
            for c in cases:
                lines.append(f"• {c.case_type or '案件'} / {c.case_number or c.case_id} / 進度: {c.progress or '處理中'}")
            lines.append("")
            lines.append("輸入「?」查看完整案件列表。")
            msg = "\n".join(lines)
        else:
            msg = f"歡迎 {name}！註冊成功。\n\n目前沒有案件記錄。\n輸入「?」可隨時查看案件狀態。"

        return RegisterOut(
            success=True,
            expected_name=name,
            message=msg,
            cases=[{"case_id": c.case_id, "case_type": c.case_type, "progress": c.progress} for c in cases] if cases else []
        )

    except Exception as e:
        db.rollback()
        logger.error(f"/register 失敗: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="REG_500: 系統錯誤")

# ==================================================
# 3) 查個人案件（n8n 的「?」分支）
# ==================================================
@user_router.post("/my-cases", response_model=MyCasesOut)
def my_cases(payload: MyCasesIn, db: Session = Depends(get_db)):
    lid = (payload.line_user_id or '').strip()
    if not lid:
        return MyCasesOut(success=False, message="缺少 line_user_id")

    row = db.execute(text("""
        SELECT client_id, expected_name
          FROM pending_line_users
         WHERE line_user_id = :lid
           AND status IN ('pending','registered')
         ORDER BY updated_at DESC NULLS LAST, created_at DESC NULLS LAST
         LIMIT 1
    """), {"lid": lid}).first()

    if not row or not row[1]:
        return MyCasesOut(success=False, message="請先輸入「登錄 您的姓名」才能查詢案件")

    cid, name = row[0], row[1]

    q = db.query(CaseRecord).filter(CaseRecord.client == name)
    if cid:
        q = q.filter(CaseRecord.client_id == cid)
    cases = q.order_by(CaseRecord.updated_at.desc()).limit(5).all()

    if not cases:
        return MyCasesOut(success=True, name=name, count=0, message=f"{name} 目前沒有案件記錄")

    def fmt(c: CaseRecord) -> str:
        return f"• {c.case_type or '案件'} / {c.case_number or c.case_id} / 進度: {c.progress or '處理中'}"

    msg = "📋 {} 的案件：\n\n{}".format(name, "\n".join(fmt(c) for c in cases))
    return MyCasesOut(success=True, name=name, count=len(cases), message=msg)

@user_router.get("/health")
def health_check():
    return {"status": "healthy", "service": "user_routes", "timestamp": datetime.utcnow().isoformat()}

# 供 main.py 引用
router = user_router
