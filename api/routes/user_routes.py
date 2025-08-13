# api/routes/user_routes.py - 最終版（支援 client_id & N8N 直送）
# -*- coding: utf-8 -*-

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, Tuple, Dict, Any, List
from datetime import datetime
import re
import logging
import traceback

from api.database import get_db
from api.models_control import PendingLineUser   # pending_line_users
from api.models_cases import CaseRecord          # case_records

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

user_router = APIRouter(prefix="/api/user", tags=["user"])

# ---------- I/O 模型 ----------
class UserRegisterIn(BaseModel):
    line_user_id: str = Field(..., min_length=5)
    # 兼容舊流程（兩段式）
    text: Optional[str] = Field(default=None, description="原訊息：可能是『登錄 XXX』或『是/否』")
    # 供 N8N 直送
    client_id: Optional[str] = Field(default=None, description="事務所 ID（租戶）")
    client_name: Optional[str] = Field(default=None, description="事務所名稱（可選）")
    user_name: Optional[str] = Field(default=None, description="用戶姓名（若有則優先用）")

class UserRegisterOut(BaseModel):
    success: bool
    message: str
    code: Optional[str] = None
    expected_name: Optional[str] = None
    cases: Optional[List[Dict[str, Any]]] = None

class MyCasesIn(BaseModel):
    line_user_id: str = Field(..., min_length=5)

class MyCasesOut(BaseModel):
    success: bool
    message: str
    count: Optional[int] = None
    name: Optional[str] = None

# ---------- Helpers ----------
def _parse_intent(text_msg: str) -> Tuple[str, Optional[str]]:
    """
    解析用戶意圖：
    - 登錄 XXX  -> ("prepare", "XXX")
    - 是 / 否   -> ("confirm_yes") / ("confirm_no")
    - ? / ？    -> ("show_cases")
    - 其他       -> ("none")
    """
    try:
        msg = (text_msg or "").strip()
        if not msg:
            return "none", None

        # 支援多種「登錄」字形與前綴空白
        m = re.match(r"^(?:登錄|登陸|登入|登录)\s*(.+)$", msg, flags=re.I)
        if m:
            return ("prepare", m.group(1).strip())

        if msg in ("是", "yes", "Yes", "YES"):
            return "confirm_yes", None
        if msg in ("否", "no", "No", "NO"):
            return "confirm_no", None
        if msg in ("?", "？"):
            return "show_cases", None
        return "none", None
    except Exception as e:
        logger.error(f"解析意圖失敗: {e}")
        return "none", None

def _safe_exec(db: Session, op: str, sql: str, params: Dict[str, Any]):
    try:
        res = db.execute(text(sql), params)
        db.commit()
        return res
    except Exception as e:
        db.rollback()
        logger.error(f"{op} 失敗: {e}")
        raise

def _select_one(db: Session, sql: str, params: Dict[str, Any]):
    return db.execute(text(sql), params).first()

# ---------- 註冊入口 ----------
@user_router.post("/register", response_model=UserRegisterOut)
def register_user(payload: UserRegisterIn, db: Session = Depends(get_db)):
    """
    用戶註冊端點
    A) N8N 直送（建議）：只要有 client_id + user_name 即可直接註冊/更新
    B) 舊兩段式流程：登錄 XXX -> 是/否
    """
    try:
        logger.info(f"[REGISTER] {payload.model_dump()}")

        # === A) N8N 直送（優先處理）===
        if (payload.client_id and payload.client_id.strip()) and (payload.user_name and payload.user_name.strip()):
            return _handle_n8n_registration(payload, db)

        # 若只有 client_name（舊版你曾用名稱代替）也支援
        if (payload.client_name and payload.client_name.strip()) and (payload.line_user_id):
            # 將 client_name 暫存入 expected_name，視同已註冊（保持向下相容）
            p2 = UserRegisterIn(
                line_user_id=payload.line_user_id,
                user_name=payload.client_name.strip(),
                client_id=payload.client_id,     # 可能為 None；後續可由 verify-secret/pending 回填
            )
            return _handle_n8n_registration(p2, db)

        # === B) 舊兩段式流程 ===
        return _handle_traditional_registration(payload, db)

    except Exception as e:
        logger.error(f"註冊失敗: {e}")
        logger.error(traceback.format_exc())
        return UserRegisterOut(success=False, message="系統錯誤，請稍後再試。代碼: REG_500")

# ---------- N8N 直送處理 ----------
def _handle_n8n_registration(payload: UserRegisterIn, db: Session) -> UserRegisterOut:
    """
    直接把 (client_id, line_user_id, user_name) 寫入/更新 pending_line_users
    - 以 (client_id, line_user_id) 優先 upsert；若無此唯一約束，退而以 line_user_id upsert。
    """
    line_user_id = payload.line_user_id.strip()
    user_name = (payload.user_name or "").strip()
    client_id = (payload.client_id or "").strip()

    if not line_user_id or not user_name:
        return UserRegisterOut(success=False, message="缺少必要欄位(line_user_id/user_name)")

    # 嘗試用 (client_id, line_user_id) 尋找（租戶隔離）
    row = None
    if client_id:
        row = _select_one(db, """
            SELECT client_id, line_user_id, expected_name, status
            FROM pending_line_users
            WHERE client_id = :cid AND line_user_id = :lid
            LIMIT 1
        """, {"cid": client_id, "lid": line_user_id})

    if row:
        # 更新既有記錄
        _safe_exec(db, "更新 pending_line_users", """
            UPDATE pending_line_users
               SET expected_name = :name,
                   status = 'registered',
                   updated_at = NOW()
             WHERE client_id = :cid AND line_user_id = :lid
        """, {"cid": client_id, "lid": line_user_id, "name": user_name})
    else:
        # 若找不到，採用 upsert 策略
        if client_id:
            # 推薦：你若已建立 UNIQUE (client_id, line_user_id) 就可用 ON CONFLICT
            _safe_exec(db, "插入/更新 pending_line_users", """
                INSERT INTO pending_line_users (client_id, line_user_id, expected_name, status, created_at, updated_at)
                VALUES (:cid, :lid, :name, 'registered', NOW(), NOW())
                ON CONFLICT (client_id, line_user_id)
                DO UPDATE SET expected_name = EXCLUDED.expected_name,
                              status = 'registered',
                              updated_at = NOW()
            """, {"cid": client_id, "lid": line_user_id, "name": user_name})
        else:
            # 沒帶 client_id 仍允許寫入（相容舊資料），但建議儘快補上
            _safe_exec(db, "插入/更新(無 client_id) pending_line_users", """
                INSERT INTO pending_line_users (line_user_id, expected_name, status, created_at, updated_at)
                VALUES (:lid, :name, 'registered', NOW(), NOW())
                ON CONFLICT (line_user_id)
                DO UPDATE SET expected_name = EXCLUDED.expected_name,
                              status = 'registered',
                              updated_at = NOW()
            """, {"lid": line_user_id, "name": user_name})

    # 查使用者的最近 3 筆案件（以租戶 + 姓名篩）
    cases = []
    if client_id:
        cases = (db.query(CaseRecord)
                   .filter(CaseRecord.client_id == client_id,
                           CaseRecord.client == user_name)
                   .order_by(CaseRecord.updated_at.desc())
                   .limit(3).all())
    else:
        # 沒有 client_id 時，以姓名模糊查（相容舊資料，不建議長期使用）
        cases = (db.query(CaseRecord)
                   .filter(CaseRecord.client == user_name)
                   .order_by(CaseRecord.updated_at.desc())
                   .limit(3).all())

    if cases:
        msg_lines = [f"歡迎 {user_name}！註冊成功。", "", f"找到 {len(cases)} 件案件："]
        for c in cases:
            msg_lines.append(f"• {c.case_type or '案件'} / {c.case_number or c.case_id} / 進度:{c.progress or '-'}")
        msg_lines.append("")
        msg_lines.append("輸入「?」查看完整案件列表。")
        message = "\n".join(msg_lines)
    else:
        message = f"歡迎 {user_name}！註冊成功。\n\n目前沒有案件記錄。\n輸入「?」可隨時查看案件狀態。"

    return UserRegisterOut(
        success=True,
        message=message,
        expected_name=user_name,
        cases=[{"case_id": c.case_id, "case_type": c.case_type, "progress": c.progress} for c in cases] if cases else []
    )

# ---------- 舊兩段式流程 ----------
def _handle_traditional_registration(payload: UserRegisterIn, db: Session) -> UserRegisterOut:
    intent, candidate_name = _parse_intent(payload.text or "")
    logger.info(f"[REGISTER/legacy] intent={intent} candidate_name={candidate_name}")

    # A) 準備：「登錄 XXX」
    if intent == "prepare":
        if not candidate_name:
            return UserRegisterOut(success=False, code="invalid_format",
                                   message="請輸入「登錄 您的姓名」，例如：登錄 王小明")

        # 是否已註冊
        existed = _select_one(db, """
            SELECT expected_name, status
              FROM pending_line_users
             WHERE line_user_id = :lid
               AND status IN ('registered','pending')
        """, {"lid": payload.line_user_id})

        if existed:
            return UserRegisterOut(success=True,
                                   message=f"您已註冊為：{existed[0]}\n輸入「?」查看案件")

        # 設為確認中
        _safe_exec(db, "pending_line_users -> confirming", """
            INSERT INTO pending_line_users (line_user_id, expected_name, status, created_at, updated_at)
            VALUES (:lid, :name, 'confirming', NOW(), NOW())
            ON CONFLICT (line_user_id)
            DO UPDATE SET expected_name = :name, status = 'confirming', updated_at = NOW()
        """, {"lid": payload.line_user_id, "name": candidate_name})

        return UserRegisterOut(success=True,
                               message=f"確認您的姓名是「{candidate_name}」嗎？\n請回覆「是」或「否」")

    # B) 確認「是」
    if intent == "confirm_yes":
        row = _select_one(db, """
            SELECT expected_name FROM pending_line_users
             WHERE line_user_id = :lid AND status = 'confirming'
        """, {"lid": payload.line_user_id})

        if not row:
            return UserRegisterOut(success=False, message="請先輸入「登錄 您的姓名」")

        _safe_exec(db, "confirm -> registered", """
            UPDATE pending_line_users
               SET status = 'registered', updated_at = NOW()
             WHERE line_user_id = :lid
        """, {"lid": payload.line_user_id})

        return UserRegisterOut(success=True,
                               expected_name=row[0],
                               message=f"註冊成功！歡迎 {row[0]}，輸入「?」查看您的案件")

    # C) 確認「否」
    if intent == "confirm_no":
        _safe_exec(db, "cancel confirming", """
            DELETE FROM pending_line_users
             WHERE line_user_id = :lid AND status = 'confirming'
        """, {"lid": payload.line_user_id})
        return UserRegisterOut(success=False, message="已取消，請重新輸入「登錄 您的姓名」")

    # D) 查詢案件「?」
    if intent == "show_cases":
        return _show_user_cases(payload.line_user_id, db)

    # E) 其他
    return UserRegisterOut(success=False, code="invalid_format",
                           message="請輸入「登錄 您的姓名」開始使用")

# ---------- 查個人案件 ----------
def _show_user_cases(line_user_id: str, db: Session) -> UserRegisterOut:
    """
    以 pending_line_users 找 expected_name 與 client_id（若有）
    然後以 (client_id, expected_name) 查 case_records
    """
    row = _select_one(db, """
        SELECT client_id, expected_name
          FROM pending_line_users
         WHERE line_user_id = :lid
           AND status IN ('pending','registered','confirming')
         ORDER BY updated_at DESC NULLS LAST, created_at DESC NULLS LAST
         LIMIT 1
    """, {"lid": line_user_id})

    if not row or not row[1]:
        return UserRegisterOut(success=False, code="not_registered",
                               message="請先輸入「登錄 您的姓名」才能查詢案件")

    client_id, expected_name = row[0], row[1]

    q = db.query(CaseRecord).filter(CaseRecord.client == expected_name)
    if client_id:
        q = q.filter(CaseRecord.client_id == client_id)
    cases = q.order_by(CaseRecord.updated_at.desc()).limit(5).all()

    if not cases:
        return UserRegisterOut(success=True, expected_name=expected_name,
                               message=f"{expected_name} 目前沒有案件記錄")

    def fmt(c: CaseRecord) -> str:
        return f"• {c.case_type or '案件'} / {c.case_number or c.case_id} / 進度:{c.progress or '處理中'}"

    msg = "📋 {} 的案件列表：\n\n{}".format(
        expected_name, "\n".join(fmt(c) for c in cases)
    )
    return UserRegisterOut(
        success=True,
        expected_name=expected_name,
        message=msg,
        cases=[{"case_id": c.case_id, "case_type": c.case_type, "progress": c.progress} for c in cases]
    )

@user_router.post("/my-cases", response_model=MyCasesOut)
def my_cases(payload: MyCasesIn, db: Session = Depends(get_db)):
    """供 N8N 呼叫的查個人案件（與 _show_user_cases 同邏輯，簡化回傳）"""
    row = _select_one(db, """
        SELECT client_id, expected_name
          FROM pending_line_users
         WHERE line_user_id = :lid
           AND status IN ('pending','registered')
         ORDER BY updated_at DESC NULLS LAST, created_at DESC NULLS LAST
         LIMIT 1
    """, {"lid": payload.line_user_id})

    if not row or not row[1]:
        return MyCasesOut(success=False, message="請先輸入「登錄 您的姓名」才能查詢案件")

    client_id, expected_name = row[0], row[1]

    q = db.query(CaseRecord).filter(CaseRecord.client == expected_name)
    if client_id:
        q = q.filter(CaseRecord.client_id == client_id)
    cases = q.order_by(CaseRecord.updated_at.desc()).limit(5).all()

    if not cases:
        return MyCasesOut(success=True, name=expected_name, count=0,
                          message=f"{expected_name} 目前沒有案件記錄")

    def fmt(c: CaseRecord) -> str:
        return f"• {c.case_type or '案件'} / {c.case_number or c.case_id} / 進度:{c.progress or '處理中'}"

    msg = "📋 {} 的案件：\n\n{}".format(
        expected_name, "\n".join(fmt(c) for c in cases)
    )
    return MyCasesOut(success=True, name=expected_name, count=len(cases), message=msg)

# ---------- 健康檢查 ----------
@user_router.get("/health")
def health_check():
    return {"status": "healthy", "service": "user_routes", "timestamp": datetime.utcnow().isoformat()}

# 兼容別名
router = user_router
