# api/routes/line_routes.py
# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, Literal, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text
import re

from api.database import get_db  # 你現有的 DB session 來源

line_router = APIRouter(prefix="/api/line", tags=["line"])

# ---- 入參：維持你原本欄位，不動 ----
class ResolveRouteIn(BaseModel):
    is_secret: bool = False
    is_lawyer: bool = False
    client_name: Optional[str] = None
    line_user_id: Optional[str] = None
    text: Optional[str] = None

# ---- 方案A：新回傳格式 ----
class ResolveRouteOutA(BaseModel):
    route: Literal["AUTH", "GUEST"]
    action: Literal["QUERY", "LOGIN", "CONFIRM", "OTHER"]
    success: bool
    is_lawyer: bool
    client_name: Optional[str] = None
    message: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None


@line_router.post("/resolve-route", response_model=ResolveRouteOutA)
def resolve_route(p: ResolveRouteIn, db: Session = Depends(get_db)) -> ResolveRouteOutA:
    """
    方案 A：
      - route: AUTH | GUEST
      - action:
          QUERY    → 已登錄且輸入「?」
          LOGIN    → 未登錄，引導「登錄 您的大名」
          CONFIRM  → 收到「登錄 XXX」，請回「是/否」
          OTHER    → 其他（例如律師、或已登錄但不是「?」）
    並且：
      - 使用 DB 的 pending_line_users 做「暫存姓名/完成登錄」
    """
    if not p.line_user_id:
        raise HTTPException(status_code=400, detail="line_user_id is required")

    text_in = (p.text or "").strip()
    uid = p.line_user_id

    # ===== 1) 律師優先（暗號 + is_lawyer）=====
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

    # ===== 2) 一般用戶：先處理「是 / 否」=====
    if text_in in ("是", "yes", "Yes", "YES"):
        row = db.execute(text("""
            SELECT expected_name
            FROM pending_line_users
            WHERE line_user_id = :lid
        """), {"lid": uid}).first()

        if row and row[0]:
            # 完成登錄：把狀態設為 registered
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
                message="登錄完成！之後輸入「?」可以瀏覽您的案件進度",
                payload={}
            )
        # 沒暫存姓名 → 引導重新來
        return ResolveRouteOutA(
            route="GUEST",
            action="LOGIN",
            success=bool(p.is_secret),
            is_lawyer=False,
            client_name=None,
            message="您好，您尚未登錄，請輸入「登錄 您的大名」完成登錄",
            payload={}
        )

    if text_in in ("否", "no", "No", "NO"):
        # 清除暫存或至少清空姓名、回到 LOGIN
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
            client_name=None,
            message="好的，請重新輸入：「登錄 您的大名」",
            payload={}
        )

    # ===== 3) 已登錄者（透過 pending_line_users 狀態判斷）=====
    # 只要狀態是 registered，就視為「已登錄」
    registered = db.execute(text("""
        SELECT 1
        FROM pending_line_users
        WHERE line_user_id = :lid AND status = 'registered'
        LIMIT 1
    """), {"lid": uid}).first()

    if registered:
        if text_in in ("?", "？"):
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
            action="OTHER",
            success=bool(p.is_secret),
            is_lawyer=False,
            client_name=p.client_name,
            message="您已登錄，輸入「?」即可查詢案件進度",
            payload={}
        )

    # ===== 4) 未登錄者 =====
    m = re.match(r"^(?:登錄|登陸|登入|登录)\s+(.+)$", text_in, flags=re.I)
    if m:
        name = m.group(1).strip()
        # upsert 暫存：有則更新、無則新增
        db.execute(text("""
            INSERT INTO pending_line_users (line_user_id, expected_name, status, created_at, updated_at)
            VALUES (:lid, :name, 'pending', NOW(), NOW())
            ON CONFLICT (line_user_id)
            DO UPDATE SET expected_name = EXCLUDED.expected_name,
                          status = 'pending',
                          updated_at = NOW();
        """), {"lid": uid, "name": name})
        db.commit()
        return ResolveRouteOutA(
            route="GUEST",
            action="CONFIRM",
            success=bool(p.is_secret),
            is_lawyer=False,
            client_name=name,
            message=f"您的大名「{name}」，無誤請回覆「是」，有誤請回覆「否」",
            payload={"client_name": name}
        )

    # 其他 → 引導去登錄
    return ResolveRouteOutA(
        route="GUEST",
        action="LOGIN",
        success=bool(p.is_secret),
        is_lawyer=False,
        client_name=None,
        message="您好，您尚未登錄，請輸入「登錄 您的大名」完成登錄",
        payload={}
    )
