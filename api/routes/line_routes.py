# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, Literal, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text
import re

from api.database import get_db  # 既有的 DB session

line_router = APIRouter(prefix="/api/line", tags=["line"])

# ========= I/O =========
class ResolveRouteIn(BaseModel):
    is_secret: bool = False
    is_lawyer: bool = False
    client_name: Optional[str] = None
    line_user_id: Optional[str] = None
    text: Optional[str] = None

class ResolveRouteOutA(BaseModel):
    route: Literal["AUTH", "GUEST"]
    action: Literal["QUERY", "LOGIN", "CONFIRM", "OTHER", "BIND_OK", "LAWYER_QUERY", "SILENT"]
    success: bool
    is_lawyer: bool
    client_name: Optional[str] = None
    message: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None


# ========= helpers =========

def _norm_query(text_raw: str) -> bool:
    """吃全形？、去零寬與前後空白、把「?」外層引號去掉後再比對。"""
    if not text_raw:
        return False
    t = re.sub(r"[\u200B-\u200D\uFEFF]", "", text_raw)  # 去零寬
    t = t.replace("？", "?").strip()                     # 全形→半形，去空白
    t = t.strip('\'"「」')                               # 去引號
    return t == "?"

def _is_registered_user(db: Session, line_user_id: str) -> bool:
    """視為已登錄：login_users 或 pending_line_users.status='registered'（依實況調整）"""
    row = db.execute(text("""
        SELECT 1 FROM login_users WHERE line_user_id = :lid
        UNION ALL
        SELECT 1 FROM pending_line_users WHERE line_user_id = :lid AND status = 'registered'
        LIMIT 1
    """), {"lid": line_user_id}).first()
    return bool(row)

def _upsert_pending_name(db: Session, uid: str, name: str) -> None:
    db.execute(text("""
        INSERT INTO pending_line_users (line_user_id, expected_name, status, created_at, updated_at)
        VALUES (:lid, :name, 'pending', NOW(), NOW())
        ON CONFLICT (line_user_id)
        DO UPDATE SET expected_name = EXCLUDED.expected_name,
                      status = 'pending',
                      updated_at = NOW()
    """), {"lid": uid, "name": name})
    db.commit()

# ======== 律師綁定（依 secret_code 綁定到 client_line_users）========
def _lookup_lawyer_by_code(db: Session, code: str):
    """
    依 secret_code 找律師。請把表名/欄位改成你的實際表：
    假設 lawyers(id, name, secret_code, active)
    """
    row = db.execute(text("""
        SELECT id, name
        FROM lawyers
        WHERE secret_code = :code AND active = TRUE
        LIMIT 1
    """), {"code": code}).first()
    if row:
        return {"id": row[0], "name": row[1]}
    return None

def _bind_client_to_lawyer(db: Session, line_user_id: str, lawyer_id: int):
    db.execute(text("""
        INSERT INTO client_line_users (line_user_id, lawyer_id, created_at, updated_at)
        VALUES (:lid, :lawyer_id, NOW(), NOW())
        ON CONFLICT (line_user_id)
        DO UPDATE SET lawyer_id = EXCLUDED.lawyer_id, updated_at = NOW()
    """), {"lid": line_user_id, "lawyer_id": lawyer_id})
    db.commit()

def _is_bound_to_lawyer(db: Session, line_user_id: str) -> bool:
    row = db.execute(text("""
        SELECT 1 FROM client_line_users WHERE line_user_id = :lid LIMIT 1
    """), {"lid": line_user_id}).first()
    return bool(row)

def _looks_like_name(s: str) -> bool:
    """判斷是否像「姓名」（中文/英文，2~20 字；排除 ? / 是 / 否 / 登錄 XXX）。"""
    if not s:
        return False
    s = re.sub(r"[\u200B-\u200D\uFEFF]", "", s).strip()
    if s in ("?", "？", "是", "否"):  # 排除常見單字
        return False
    if re.match(r"^(?:登錄|登陸|登入|登录)\s+", s, flags=re.I):
        return False
    return bool(re.fullmatch(r"[A-Za-z\u4e00-\u9fa5][A-Za-z\u4e00-\u9fa5\s]{1,19}", s))

@line_router.post("/resolve-route", response_model=ResolveRouteOutA)
def resolve_route(p: ResolveRouteIn, db: Session = Depends(get_db)) -> ResolveRouteOutA:
    """
    方案A：兩條 route（AUTH/GUEST）+ action 控制。
    本版規則：
      - 已綁定律師：只有「姓名」→ LAWYER_QUERY；其他一律 SILENT
      - 輸入 secret_code：綁定並回 BIND_OK
      - 已註冊一般用戶：只有「?」→ QUERY；其他一律 SILENT
      - 未註冊：維持 LOGIN / CONFIRM / 是 / 否 流程
    """
    if not p.line_user_id:
        raise HTTPException(status_code=400, detail="line_user_id is required")

    uid = p.line_user_id
    text_in = (p.text or "").strip()

    # 0) 使用者輸入的是律師 secret_code → 立即綁定到 client_line_users
    lawyer = _lookup_lawyer_by_code(db, text_in)
    if lawyer:
        _bind_client_to_lawyer(db, uid, lawyer["id"])
        return ResolveRouteOutA(
            route="AUTH",
            action="BIND_OK",
            success=True,
            is_lawyer=True,    # 代表「已具有律師綁定關係」
            client_name=p.client_name,
            message=f"綁定成功！已綁定律師「{lawyer['name']}」。之後輸入「?」可查看案件/操作選項。",
            payload={"lawyer_id": lawyer["id"], "lawyer_name": lawyer["name"]}
        )

    # 1) 已綁定到律師 → 只接受姓名，否則靜默
    if _is_bound_to_lawyer(db, uid):
        if _looks_like_name(text_in):
            return ResolveRouteOutA(
                route="AUTH",
                action="LAWYER_QUERY",
                success=True,
                is_lawyer=True,
                message=None,
                payload={"client_name": text_in}
            )
        return ResolveRouteOutA(
            route="AUTH",
            action="SILENT",
            success=True,
            is_lawyer=True,
            message=None,
            payload={}
        )

    # 2) 一般用戶姓名確認（是 / 否）
    if text_in in ("是", "yes", "Yes", "YES"):
        row = db.execute(text("""
            SELECT expected_name FROM pending_line_users WHERE line_user_id = :lid
        """), {"lid": uid}).first()
        if row and row[0]:
            db.execute(text("""
                UPDATE pending_line_users
                SET status = 'registered', updated_at = NOW()
                WHERE line_user_id = :lid
            """), {"lid": uid})
            db.commit()
            return ResolveRouteOutA(
                route="AUTH",
                action="OTHER",
                success=bool(p.is_secret),
                is_lawyer=False,
                client_name=row[0],
                message="綁定成功！登錄完成！之後輸入「?」可以瀏覽您的案件進度",
                payload={}
            )
        return ResolveRouteOutA(
            route="GUEST",
            action="LOGIN",
            success=bool(p.is_secret),
            is_lawyer=False,
            message="您好，您尚未登錄，請輸入「登錄 您的大名」完成登錄",
            payload={}
        )

    if text_in in ("否", "no", "No", "NO"):
        db.execute(text("""
            UPDATE pending_line_users
            SET expected_name = NULL, status = 'pending', updated_at = NOW()
            WHERE line_user_id = :lid
        """), {"lid": uid})
        db.commit()
        return ResolveRouteOutA(
            route="GUEST",
            action="LOGIN",
            success=bool(p.is_secret),
            is_lawyer=False,
            message="好的，請重新輸入：「登錄 您的大名」",
            payload={}
        )

    # 3) 已登錄的一般用戶 → 只接受「?」，否則靜默
    if _is_registered_user(db, uid):
        if _norm_query(text_in):
            return ResolveRouteOutA(
                route="AUTH",
                action="QUERY",
                success=bool(p.is_secret),
                is_lawyer=False,
                client_name=p.client_name,
                payload={}
            )
        return ResolveRouteOutA(
            route="AUTH",
            action="SILENT",
            success=bool(p.is_secret),
            is_lawyer=False,
            client_name=p.client_name,
            message=None,
            payload={}
        )

    # 4) 未登錄：收到「登錄 XXX」→ 進入確認；否則提示 LOGIN
    m = re.match(r"^(?:登錄|登陸|登入|登录)\s+(.+)$", text_in, flags=re.I)
    if m:
        name = m.group(1).strip()
        _upsert_pending_name(db, uid, name)
        return ResolveRouteOutA(
            route="GUEST",
            action="CONFIRM",
            success=bool(p.is_secret),
            is_lawyer=False,
            client_name=name,
            message=f"您的大名「{name}」，無誤請回覆「是」，有誤請回覆「否」",
            payload={"client_name": name}
        )

    return ResolveRouteOutA(
        route="GUEST",
        action="LOGIN",
        success=bool(p.is_secret),
        is_lawyer=False,
        message="您好，您尚未登錄，請輸入「登錄 您的大名」完成登錄",
        payload={}
    )
