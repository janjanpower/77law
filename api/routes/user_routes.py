# api/routes/user_routes.py - 修復版本
# -*- coding: utf-8 -*-

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, Tuple, Dict, Any
import re
import traceback
import logging

from api.database import get_db
from api.models_control import PendingLineUser  # 確保有這個 model
from api.models_cases import CaseRecord  # 查案件用

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

user_router = APIRouter(prefix="/api/user", tags=["user"])

# ---------- I/O 模型 ----------
class UserRegisterIn(BaseModel):
    line_user_id: str = Field(..., min_length=5)
    text: str = Field(..., description="原訊息：可能是『登錄 XXX』或『是/否』")
    client_name: Optional[str] = Field(default=None, description="客戶名稱（從 N8N 來的）")

class UserRegisterOut(BaseModel):
    success: bool
    message: str
    code: Optional[str] = None
    expected_name: Optional[str] = None
    cases: Optional[list] = None

class MyCasesIn(BaseModel):
    line_user_id: str = Field(..., min_length=5)

class MyCasesOut(BaseModel):
    success: bool
    message: str
    count: Optional[int] = None
    name: Optional[str] = None

# ---------- Helper Functions ----------
def _parse_intent(text_msg: str) -> Tuple[str, Optional[str]]:
    """解析用戶意圖"""
    try:
        msg = (text_msg or "").strip()
        if not msg:
            return "none", None

        # 支援多種「登錄」字形
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

def _is_lawyer(db: Session, line_user_id: str) -> bool:
    """檢查是否為律師"""
    try:
        row = db.execute(text("""
            SELECT 1 FROM client_line_users
            WHERE line_user_id = :lid AND is_active = TRUE
            LIMIT 1
        """), {"lid": line_user_id}).first()
        return bool(row)
    except Exception as e:
        logger.error(f"檢查律師身份失敗: {e}")
        return False

def _safe_db_operation(db: Session, operation_name: str, sql_query: str, params: Dict[str, Any]):
    """安全的資料庫操作"""
    try:
        result = db.execute(text(sql_query), params)
        db.commit()
        return result
    except Exception as e:
        logger.error(f"{operation_name} 失敗: {e}")
        db.rollback()
        raise

# ---------- 兩段式登記 (原邏輯保持) ----------
@user_router.post("/register", response_model=UserRegisterOut)
def register_user(payload: UserRegisterIn, db: Session = Depends(get_db)):
    """
    用戶註冊端點 - 處理 N8N 來的請求
    支援多種格式：
    1. 直接從 N8N 來的 client_name (新增)
    2. 原有的兩段式註冊流程
    """
    try:
        logger.info(f"收到註冊請求: line_user_id={payload.line_user_id}, text={payload.text}, client_name={payload.client_name}")

        # === 新增邏輯：如果是從 N8N 來的且有 client_name，直接註冊 ===
        if payload.client_name and payload.client_name.strip():
            return _handle_n8n_registration(payload, db)

        # === 原有邏輯：兩段式註冊 ===
        return _handle_traditional_registration(payload, db)

    except Exception as e:
        logger.error(f"註冊失敗: {e}")
        logger.error(f"錯誤詳情: {traceback.format_exc()}")
        return UserRegisterOut(
            success=False,
            message=f"系統錯誤，請稍後再試。錯誤代碼: REG_500"
        )

def _handle_n8n_registration(payload: UserRegisterIn, db: Session) -> UserRegisterOut:
    """處理從 N8N 來的註冊請求"""
    try:
        client_name = payload.client_name.strip()
        line_user_id = payload.line_user_id

        logger.info(f"處理 N8N 註冊: {client_name} ({line_user_id})")

        # 檢查是否已經註冊
        existing = db.execute(text("""
            SELECT expected_name, status FROM pending_line_users
            WHERE line_user_id = :lid
        """), {"lid": line_user_id}).first()

        if existing:
            if existing[1] in ('registered', 'pending'):
                return UserRegisterOut(
                    success=True,
                    message=f"{existing[0]}，您已經註冊過了。\n輸入「?」查看您的案件。"
                )

        # 新註冊或更新
        _safe_db_operation(db, "插入或更新用戶", """
            INSERT INTO pending_line_users (line_user_id, expected_name, status, created_at, updated_at)
            VALUES (:lid, :name, 'registered', NOW(), NOW())
            ON CONFLICT (line_user_id)
            DO UPDATE SET
                expected_name = :name,
                status = 'registered',
                updated_at = NOW()
        """, {"lid": line_user_id, "name": client_name})

        # 查詢用戶案件
        cases = db.query(CaseRecord).filter(CaseRecord.client == client_name).limit(3).all()

        if cases:
            case_summary = f"找到 {len(cases)} 件案件：\n"
            for case in cases:
                case_summary += f"• {case.case_type or '案件'} - {case.progress or '處理中'}\n"
            message = f"歡迎 {client_name}！註冊成功。\n\n{case_summary}\n輸入「?」查看完整案件列表。"
        else:
            message = f"歡迎 {client_name}！註冊成功。\n\n目前沒有案件記錄。\n輸入「?」可隨時查看案件狀態。"

        return UserRegisterOut(
            success=True,
            message=message,
            expected_name=client_name,
            cases=[{
                "case_id": case.case_id,
                "case_type": case.case_type,
                "progress": case.progress
            } for case in cases] if cases else []
        )

    except Exception as e:
        logger.error(f"N8N 註冊處理失敗: {e}")
        raise

def _handle_traditional_registration(payload: UserRegisterIn, db: Session) -> UserRegisterOut:
    """處理傳統的兩段式註冊"""
    try:
        # 解析用戶意圖
        intent, candidate_name = _parse_intent(payload.text)
        logger.info(f"解析意圖: {intent}, 候選名稱: {candidate_name}")

        # A) 準備階段：「登錄 XXX」
        if intent == "prepare":
            if not candidate_name:
                return UserRegisterOut(
                    success=False,
                    code="invalid_format",
                    message="請輸入「登錄 您的姓名」，例如：登錄 王小明"
                )

            # 檢查是否已註冊
            existing = db.execute(text("""
                SELECT expected_name FROM pending_line_users
                WHERE line_user_id = :lid AND status IN ('registered', 'pending')
            """), {"lid": payload.line_user_id}).first()

            if existing:
                return UserRegisterOut(
                    success=True,
                    message=f"您已註冊為：{existing[0]}\n輸入「?」查看案件"
                )

            # 插入或更新為確認狀態
            _safe_db_operation(db, "插入確認狀態", """
                INSERT INTO pending_line_users (line_user_id, expected_name, status, created_at, updated_at)
                VALUES (:lid, :name, 'confirming', NOW(), NOW())
                ON CONFLICT (line_user_id)
                DO UPDATE SET
                    expected_name = :name,
                    status = 'confirming',
                    updated_at = NOW()
            """, {"lid": payload.line_user_id, "name": candidate_name})

            return UserRegisterOut(
                success=True,
                message=f"確認您的姓名是「{candidate_name}」嗎？\n請回覆「是」或「否」"
            )

        # B) 確認「是」
        if intent == "confirm_yes":
            row = db.execute(text("""
                SELECT expected_name FROM pending_line_users
                WHERE line_user_id = :lid AND status = 'confirming'
            """), {"lid": payload.line_user_id}).first()

            if not row:
                return UserRegisterOut(
                    success=False,
                    message="請先輸入「登錄 您的姓名」"
                )

            name = row[0]
            _safe_db_operation(db, "確認註冊", """
                UPDATE pending_line_users
                SET status = 'registered', updated_at = NOW()
                WHERE line_user_id = :lid
            """, {"lid": payload.line_user_id})

            return UserRegisterOut(
                success=True,
                expected_name=name,
                message=f"註冊成功！歡迎 {name}，輸入「?」查看您的案件"
            )

        # C) 確認「否」
        if intent == "confirm_no":
            _safe_db_operation(db, "取消註冊", """
                DELETE FROM pending_line_users
                WHERE line_user_id = :lid AND status = 'confirming'
            """, {"lid": payload.line_user_id})

            return UserRegisterOut(
                success=False,
                message="已取消，請重新輸入「登錄 您的姓名」"
            )

        # D) 查詢案件「?」
        if intent == "show_cases":
            return _show_user_cases(payload.line_user_id, db)

        # E) 其他文字
        return UserRegisterOut(
            success=False,
            code="invalid_format",
            message="請輸入「登錄 您的姓名」開始使用"
        )

    except Exception as e:
        logger.error(f"傳統註冊處理失敗: {e}")
        raise

def _show_user_cases(line_user_id: str, db: Session) -> UserRegisterOut:
    """顯示用戶案件"""
    try:
        row = db.execute(text("""
            SELECT expected_name
            FROM pending_line_users
            WHERE line_user_id = :lid AND status IN ('pending','registered','confirming')
        """), {"lid": line_user_id}).first()

        if not row or not row[0]:
            return UserRegisterOut(
                success=False,
                code="not_registered",
                message="請先輸入「登錄 您的姓名」才能查詢案件"
            )

        expected_name = row[0]
        cases = (db.query(CaseRecord)
                  .filter(CaseRecord.client == expected_name)
                  .order_by(CaseRecord.updated_at.desc())
                  .limit(5).all())

        if not cases:
            return UserRegisterOut(
                success=True,
                message=f"{expected_name} 目前沒有案件記錄"
            )

        def format_case(case):
            return f"• {case.case_type or '案件'} / {case.case_number or case.case_id} / 進度: {case.progress or '處理中'}"

        message = f"📋 {expected_name} 的案件列表：\n\n"
        message += "\n".join(format_case(case) for case in cases)

        return UserRegisterOut(
            success=True,
            message=message,
            expected_name=expected_name,
            cases=[{
                "case_id": case.case_id,
                "case_type": case.case_type,
                "progress": case.progress
            } for case in cases]
        )

    except Exception as e:
        logger.error(f"顯示案件失敗: {e}")
        raise

# ---------- 查個人案件 API ----------
@user_router.post("/my-cases", response_model=MyCasesOut)
def my_cases(payload: MyCasesIn, db: Session = Depends(get_db)):
    """查詢個人案件 - 供 N8N 和其他系統呼叫"""
    try:
        logger.info(f"查詢案件請求: {payload.line_user_id}")

        row = db.execute(text("""
            SELECT expected_name
            FROM pending_line_users
            WHERE line_user_id = :lid AND status IN ('pending','registered')
        """), {"lid": payload.line_user_id}).first()

        if not row or not row[0]:
            return MyCasesOut(
                success=False,
                message="請先輸入「登錄 您的姓名」才能查詢案件"
            )

        expected_name = row[0]
        cases = (db.query(CaseRecord)
                  .filter(CaseRecord.client == expected_name)
                  .order_by(CaseRecord.updated_at.desc())
                  .limit(5).all())

        if not cases:
            return MyCasesOut(
                success=True,
                name=expected_name,
                count=0,
                message=f"{expected_name} 目前沒有案件記錄"
            )

        def format_case(case):
            return f"• {case.case_type or '案件'} / {case.case_number or case.case_id} / 進度: {case.progress or '處理中'}"

        message = f"📋 {expected_name} 的案件：\n\n"
        message += "\n".join(format_case(case) for case in cases)

        return MyCasesOut(
            success=True,
            name=expected_name,
            count=len(cases),
            message=message
        )

    except Exception as e:
        logger.error(f"查詢案件失敗: {e}")
        logger.error(f"錯誤詳情: {traceback.format_exc()}")
        return MyCasesOut(
            success=False,
            message="系統錯誤，請稍後再試"
        )

# ---------- 健康檢查端點 ----------
@user_router.get("/health")
def health_check():
    """用戶路由健康檢查"""
    return {"status": "healthy", "service": "user_routes", "timestamp": "2025-08-12"}

# ========== 為了與原代碼相容，保留原有的路由註冊方式 ==========
# 這樣可以確保不影響現有功能
router = user_router  # 別名，供其他地方 import 使用