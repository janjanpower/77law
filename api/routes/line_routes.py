# api/routes/line_routes.py
# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, Literal, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text
import re

from api.database import get_db  # 你現有的 DB session

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
    action: Literal["QUERY", "LOGIN", "CONFIRM", "OTHER"]
    success: bool
    is_lawyer: bool
    client_name: Optional[str] = None
    message: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None


# ========= helpers（直接用你的資料表） =========
def _norm_query(text_raw: str) -> bool:
    """更穩的 ? 偵測：吃全形？、前後空白、零寬字元。"""
    if text_raw is None:
        return False
    # 移除零寬
    t = re.sub(r"[\u200B-\u200D\uFEFF]", "", text_raw)
    # 全形問號換半形
    t = t.replace("\uFF1F", "?").strip()
    # 單一問號（允許空白）
    return bool(re.fullmatch(r"\??", t)) and t == "?"


def _is_registered(db: Session, line_user_id: str) -> bool:
    """視為已註冊：client_line_users 有該 uid，或 pending_line_users.status='registered'。"""
    row = db.execute(
        text("SELECT 1 FROM client_line_users WHERE line_user_id = :lid LIMIT 1"),
        {"lid": line_user_id},
    ).first()
    if row:
        return True
    row = db.execute(
        text(
            "SELECT 1 FROM pending_line_users "
            "WHERE line_user_id = :lid AND status = 'registered' LIMIT 1"
        ),
        {"lid": line_user_id},
    ).first()
    return bool(row)


def _upsert_pending_name(db: Session, uid: str, name: str) -> None:
    db.execute(
        text(
            """
            INSERT INTO pending_line_users (line_user_id, expected_name, status, created_at, updated_at)
            VALUES (:lid, :name, 'pending', NOW(), NOW())
            ON CONFLICT (line_user_id)
            DO UPDATE SET expected_name = EXCLUDED.expected_name,
                          status = 'pending',
                          updated_at = NOW()
            """
        ),
        {"lid": uid, "name": name},
    )
    db.commit()


@line_router.post("/resolve-route", response_model=ResolveRouteOutA)
def resolve_route(p: ResolveRouteIn, db: Session = Depends(get_db)) -> ResolveRouteOutA:
    """
    方案A：
      - route: AUTH|GUEST
      - action: QUERY / LOGIN / CONFIRM / OTHER
    """
    if not p.line_user_id:
        raise HTTPException(status_code=400, detail="line_user_id is required")

    uid = p.line_user_id
    text_in = (p.text or "").strip()

    # 1) 律師（暗號 + 身分）→ AUTH/OTHER
    if p.is_secret and p.is_lawyer:
        return ResolveRouteOutA(
            route="AUTH",
            action="OTHER",
            success=True,
            is_lawyer=True,
            client_name=p.client_name,
            message="已確認為律師帳號。",
            payload={}
        )

    # 2) 「是 / 否」優先處理
    if text_in in ("是", "yes", "Yes", "YES"):
        row = db.execute(
            text("SELECT expected_name FROM pending_line_users WHERE line_user_id = :lid"),
            {"lid": uid},
        ).first()
        if row and row[0]:
            # 完成綁定
            db.execute(
                text(
                    "UPDATE pending_line_users "
                    "SET status='registered', updated_at=NOW() "
                    "WHERE line_user_id = :lid"
                ),
                {"lid": uid},
            )
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
        # 沒暫存姓名 → 退回登入提示
        return ResolveRouteOutA(
            route="GUEST",
            action="LOGIN",
            success=bool(p.is_secret),
            is_lawyer=False,
            message="您好，您尚未登錄，請輸入「登錄 您的大名」完成登錄",
            payload={}
        )

    if text_in in ("否", "no", "No", "NO"):
        db.execute(
            text(
                "UPDATE pending_line_users "
                "SET expected_name=NULL, status='pending', updated_at=NOW() "
                "WHERE line_user_id = :lid"
            ),
            {"lid": uid},
        )
        db.commit()
        return ResolveRouteOutA(
            route="GUEST",
            action="LOGIN",
            success=bool(p.is_secret),
            is_lawyer=False,
            message="好的，請重新輸入：「登錄 您的大名」",
            payload={}
        )

    # 3) 已註冊者
    if _is_registered(db, uid):
        if _norm_query(text_in):
            return ResolveRouteOutA(
                route="AUTH",
                action="QUERY",
                success=bool(p.is_secret),
                is_lawyer=False,
                client_name=p.client_name,
                payload={}
            )
        # 非問號 → 提示可用 ?
        return ResolveRouteOutA(
            route="AUTH",
            action="OTHER",
            success=bool(p.is_secret),
            is_lawyer=False,
            client_name=p.client_name,
            message="您已登錄，輸入「?」即可查詢案件進度",
            payload={}
        )

    # 4) 未註冊：收到「登錄 XXX」→ 進入確認
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

    # 5) 其他 → 引導去登錄
    return ResolveRouteOutA(
        route="GUEST",
        action="LOGIN",
        success=bool(p.is_secret),
        is_lawyer=False,
        message="您好，您尚未登錄，請輸入「登錄 您的大名」完成登錄",
        payload={}
    )
