# -*- coding: utf-8 -*-
"""
api/routes/api_routes.py
— Consolidated auth routes with JWT
— /client-login 簽發 JWT；/me 範例端點驗證 JWT
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import hashlib
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field, constr
import random, string
# === DB session dependency ===
try:
    from api.database import SessionLocal  # 專案既有
    from sqlalchemy.orm import Session
except Exception:
    # 後備：直接用 DATABASE_URL 建立 SessionLocal（部署環境建議使用專案內的 SessionLocal）
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker, Session
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

# === ORM Models ===
try:
    from api.models_control import LoginUser, ClientLineUsers
except Exception:
    # 若模組路徑不同，可視情況調整
    from models_control import LoginUser, ClientLineUsers  # type: ignore

# === JWT 設定 ===
import jwt  # PyJWT

JWT_SECRET = os.getenv("JWT_SECRET", "CHANGE_ME_TO_A_RANDOM_SECRET")
JWT_ALG = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "8"))

def _create_access_token(subject: str, claims: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    exp = now + timedelta(hours=JWT_EXPIRE_HOURS)
    payload = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    if claims:
        payload.update(claims)
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)
    return {"token": token, "expires_at": exp}

bearer_scheme = HTTPBearer(auto_error=True)

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> Dict[str, Any]:
    """FastAPI 依賴：驗證並解碼 JWT，回傳 payload（無效或過期會拋 401）。"""
    try:
        token = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# === Schemas ===
class ClientLoginRequest(BaseModel):
    client_id: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1)

class ClientLoginResponse(BaseModel):
    success: bool = True
    token: str
    token_type: str = "bearer"
    expires_at: datetime
    client_id: str
    client_name: str
    user_status: str
    plan_type: Optional[str] = None
    max_users: Optional[int] = None
    current_users: Optional[int] = None
    available_slots: Optional[int] = None
    usage_percentage: Optional[float] = None
    last_login: Optional[datetime] = None

class MeResponse(BaseModel):
    client_id: str
    client_name: Optional[str] = None
    role: Optional[str] = None
    plan: Optional[str] = None
    exp: Optional[int] = None

# === Router ===
router = APIRouter()

@router.post("/client-login", response_model=ClientLoginResponse, summary="Client credential login (JWT)")
def client_login(payload: ClientLoginRequest, db: Session = Depends(get_db)) -> ClientLoginResponse:
    """
    驗證 client_id/password 後簽發 JWT。
    成功回傳：token、到期時間與當前使用量統計。
    """
    client_id = payload.client_id.strip()
    password = payload.password

    # TODO: 建議之後將密碼改為雜湊；此處依現有資料表邏輯比對明碼
    client = db.query(LoginUser).filter(
        LoginUser.client_id == client_id,
        LoginUser.password == password,
        LoginUser.is_active == True
    ).first()

    if not client:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials or inactive user")

    # 可選：檢查 user_status
    if getattr(client, "user_status", "active") != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"user_status={client.user_status}")

    # 更新最後登入時間（忽略失敗）
    try:
        client.last_login = datetime.now()
        db.commit()
    except Exception:
        db.rollback()

    # 使用量統計
    current_users = db.query(ClientLineUsers).filter(
        ClientLineUsers.client_id == client.client_id,
        ClientLineUsers.is_active == True
    ).count()

    max_users = int(getattr(client, "max_users", 0) or 0)
    available_slots = (max_users - current_users) if max_users else 0
    usage_percentage = round((current_users / max_users) * 100, 2) if max_users else 0.0

    # 簽發 Token（把常用資訊放進 claims）
    claims = {
        "name": getattr(client, "client_name", client.client_id),
        "role": "client",
        "plan": getattr(client, "plan_type", None),
    }
    token_pack = _create_access_token(subject=client.client_id, claims=claims)

    return ClientLoginResponse(
        success=True,
        token=token_pack["token"],
        expires_at=token_pack["expires_at"],
        client_id=client.client_id,
        client_name=getattr(client, "client_name", client.client_id),
        user_status=getattr(client, "user_status", "active"),
        plan_type=getattr(client, "plan_type", None),
        max_users=max_users or None,
        current_users=current_users,
        available_slots=available_slots or None,
        usage_percentage=usage_percentage,
        last_login=getattr(client, "last_login", None),
    )

@router.get("/me", response_model=MeResponse, summary="Decode token and return client info")
def me(payload: Dict[str, Any] = Depends(verify_token)) -> MeResponse:
    """帶 Authorization: Bearer <token>，回傳 token 內的基本資訊。"""
    return MeResponse(
        client_id=str(payload.get("sub")),
        client_name=payload.get("name"),
        role=payload.get("role"),
        plan=payload.get("plan"),
        exp=payload.get("exp"),
    )


# ============================== 註冊 =====================

def hash_password(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def gen_secret_code(n: int = 8) -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(random.choices(alphabet, k=n))

class RegisterRequest(BaseModel):
    client_name: constr(strip_whitespace=True, min_length=1, max_length=100)
    client_id:   constr(strip_whitespace=True, min_length=3, max_length=50)
    password:    constr(min_length=6, max_length=128)

class RegisterResponse(BaseModel):
    message: str
    client_id: str
    secret_code: str

@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    # 檢查 client_id 是否已存在
    exists = db.query(LoginUser).filter(LoginUser.client_id == req.client_id).first()
    if exists:
        raise HTTPException(status_code=400, detail="client_id 已被使用")

    # 產生唯一 secret_code（簡易重試避免撞碼）
    sc = gen_secret_code()
    for _ in range(5):
        if not db.query(LoginUser).filter(LoginUser.secret_code == sc).first():
            break
        sc = gen_secret_code()

    user = LoginUser(
        client_id=req.client_id,
        client_name=req.client_name,
        password=req.password,
        secret_code=sc
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return RegisterResponse(
        message="註冊成功，請妥善保存您的律師登陸號。",
        client_id=user.client_id,
        secret_code=user.secret_code,
    )