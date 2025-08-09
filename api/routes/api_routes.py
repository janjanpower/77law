# -*- coding: utf-8 -*-
"""
api/routes/api_routes.py
— Consolidated auth routes (merged from auth_routes.py)
— Uses AuthService; falls back to direct ORM when service import unavailable
"""

from typing import Optional, Dict, Any
from datetime import datetime
import os

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, sessionmaker

# ==== DB session dependency ====
# Prefer project SessionLocal; fallback to ad-hoc session maker via DATABASE_URL
try:
    from api.database import SessionLocal  # your project's session factory
except Exception:
    from sqlalchemy import create_engine
    DATABASE_URL = os.getenv("DATABASE_URL", "")
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    _engine = create_engine(DATABASE_URL, pool_pre_ping=True) if DATABASE_URL else None
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)  # type: ignore

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==== Models ====
try:
    from api.models_control import LoginUser, ClientLineUsers
except Exception:
    # fallback relative import (if running differently)
    from models_control import LoginUser, ClientLineUsers  # type: ignore

# ==== Service (preferred path) ====
AuthService = None
try:
    from api.services.auth_service import AuthService as _AuthService
    AuthService = _AuthService
except Exception:
    AuthService = None

# ==== Schemas ====
class ClientLoginRequest(BaseModel):
    """Client (tenant) login request"""
    client_id: str = Field(..., min_length=1, max_length=50, description="Tenant client_id")
    password: str = Field(..., min_length=1, description="Password")

class ClientLoginResponse(BaseModel):
    """Client login response with usage and plan info"""
    client_id: str
    client_name: str
    user_status: str
    plan_type: Optional[str] = None
    max_users: Optional[int] = None
    current_users: Optional[int] = None
    available_slots: Optional[int] = None
    usage_percentage: Optional[float] = None
    last_login: Optional[datetime] = None

# ==== Router ====
router = APIRouter()

@router.post("/client-login", response_model=ClientLoginResponse, summary="Client credential login")
def client_login(payload: ClientLoginRequest, db: Session = Depends(get_db)) -> ClientLoginResponse:
    """
    合併自 auth_routes.py 的登入端點：
    - 以 client_id + password 驗證
    - 僅允許 is_active 且 user_status 合規的帳戶
    - 更新 last_login
    - 回傳方案與使用量統計
    """
    client_id = payload.client_id.strip()
    password = payload.password

    # 1) Preferred: use AuthService if available
    if AuthService is not None:
        svc = AuthService()
        result: Optional[Dict[str, Any]] = svc.authenticate_by_client_credentials(client_id, password, db)  # type: ignore
        if not result:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials or inactive user")

        # Expect result to include LoginUser-like fields; compute usage
        # 再查算 current_users（若 service 未附帶）
        if "current_users" not in result or result["current_users"] is None:
            current_users = db.query(ClientLineUsers).filter(
                ClientLineUsers.client_id == client_id,
                ClientLineUsers.is_active == True
            ).count()
        else:
            current_users = int(result["current_users"])

        max_users = int(result.get("max_users", 0) or 0)
        available_slots = max(max_users - current_users, 0) if max_users else None
        usage_percentage = round((current_users / max_users) * 100, 2) if max_users else None

        # 這裡也可由 service 更新 last_login；若未處理則在此補上
        try:
            client = db.query(LoginUser).filter(LoginUser.client_id == client_id).first()
            if client:
                client.last_login = datetime.now()
                db.commit()
        except Exception:
            db.rollback()

        return ClientLoginResponse(
            client_id=result.get("client_id", client_id),
            client_name=result.get("client_name", ""),
            user_status=result.get("user_status", "active"),
            plan_type=result.get("plan_type"),
            max_users=max_users or None,
            current_users=current_users,
            available_slots=available_slots,
            usage_percentage=usage_percentage,
            last_login=result.get("last_login"),
        )

    # 2) Fallback: direct ORM logic (when AuthService import failed)
    client = db.query(LoginUser).filter(
        LoginUser.client_id == client_id,
        LoginUser.password == password,         # NOTE: consider hashing in production
        LoginUser.is_active == True
    ).first()

    if not client:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials or inactive user")

    # 可選：檢查 user_status（若非 active，禁止登入）
    if getattr(client, "user_status", "active") != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"user_status={client.user_status}")

    # 更新 last_login
    client.last_login = datetime.now()
    try:
        db.commit()
    except Exception:
        db.rollback()

    # 使用量統計
    current_users = db.query(ClientLineUsers).filter(
        ClientLineUsers.client_id == client.client_id,
        ClientLineUsers.is_active == True
    ).count()

    max_users = getattr(client, "max_users", None) or 0
    available_slots = max(max_users - current_users, 0) if max_users else None
    usage_percentage = round((current_users / max_users) * 100, 2) if max_users else None

    return ClientLoginResponse(
        client_id=client.client_id,
        client_name=getattr(client, "client_name", client.client_id),
        user_status=getattr(client, "user_status", "active"),
        plan_type=getattr(client, "plan_type", None),
        max_users=max_users or None,
        current_users=current_users,
        available_slots=available_slots,
        usage_percentage=usage_percentage,
        last_login=getattr(client, "last_login", None),
    )
