# -*- coding: utf-8 -*-
"""
api/routes/api_routes.py (patched: use is_active + tenant_status for login)
- Login rule: is_active==True -> allow; else require tenant_status==True
- Registration: is_active defaults to False; tenant_status per plan (unpaid=False else True)
- Backward compatible with tenant_status existing columns
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import hashlib
import random, string

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field, constr
from api.services.storage import s3_put_bytes
from api.services.tenant_bootstrap import ensure_tenant_schema

# === DB session dependency ===
try:
    from api.database import SessionLocal  # 專案既有
    from sqlalchemy.orm import Session
except Exception:
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
    from models_control import LoginUser, ClientLineUsers  # type: ignore

# === JWT 設定 ===
import jwt  # PyJWT
from api.constants.plans import canonical_plan, plan_limit

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
    """驗證並解碼 JWT，回傳 payload（無效或過期會拋 401）。"""
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
    plan_type: Optional[str] = None
    max_users: Optional[int] = None
    current_users: Optional[int] = None
    available_slots: Optional[int] = None
    usage_percentage: Optional[float] = None
    last_login: Optional[datetime] = None
    is_active: Optional[bool] = None
    tenant_status: Optional[bool] = None

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
    新規則：is_active==True 無條件登入；否則需 tenant_status==True。
    不再使用 user_status 作為登入門檻。
    """
    client_id = payload.client_id.strip()
    password = payload.password

    # 改成 AND（兩者都要 True）
    client = db.query(LoginUser).filter(
        LoginUser.client_id == client_id,
        LoginUser.password == password,
        LoginUser.is_active == True,
        LoginUser.tenant_status == True,
    ).first()
    if not client or getattr(client, "password", None) != password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    # 讀取 is_active（若沒有欄位，預設 False）
    is_active_flag = bool(getattr(client, "is_active", False))

    # 讀取 tenant_status（若沒有則退回 tenant_status；再退回 plan_type 推論）
    if hasattr(client, "tenant_status"):
        tenant_ok = bool(getattr(client, "tenant_status", False))
    elif hasattr(client, "tenant_status"):
        tenant_ok = bool(getattr(client, "tenant_status", False))
    else:
        tenant_ok = str(getattr(client, "plan_type", "unpaid") or "unpaid").lower() != "unpaid"

    # 登入規則
    allowed = bool(is_active_flag) or bool(tenant_ok)
    if not allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account inactive or plan not enabled")

    # 更新最後登入時間（不影響主流程）
    try:
        setattr(client, "last_login", datetime.now())
        db.commit()
    except Exception:
        db.rollback()

    # 使用量統計（若沒有此表或欄位則以 0 處理）
    try:
        current_users = db.query(ClientLineUsers).filter(
            ClientLineUsers.client_id == client.client_id,
            getattr(ClientLineUsers, "is_active", True) == True
        ).count()
    except Exception:
        current_users = 0

    max_users = int(getattr(client, "max_users", 0) or 0)
    available_slots = (max_users - current_users) if max_users else 0
    usage_percentage = round((current_users / max_users) * 100, 2) if max_users else 0.0

    # 簽發 Token
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
        plan_type=getattr(client, "plan_type", None),
        max_users=max_users or None,
        current_users=current_users,
        available_slots=available_slots or None,
        usage_percentage=usage_percentage,
        last_login=getattr(client, "last_login", None),
        is_active=bool(is_active_flag),
        tenant_status=bool(tenant_ok),
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
    plan_type:   Optional[str] = "unpaid"  # ✅ 預設 unpaid

class RegisterResponse(BaseModel):
    message: str
    client_id: str
    secret_code: str

@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    # 唯一性檢查
    exists = db.query(LoginUser).filter(LoginUser.client_id == req.client_id).first()
    if exists:
        raise HTTPException(status_code=400, detail="client_id 已被使用")

    # 產生不重複的 secret_code
    sc = gen_secret_code()
    for _ in range(5):
        if not db.query(LoginUser).filter(LoginUser.secret_code == sc).first():
            break
        sc = gen_secret_code()

    # ✅ 規則：unpaid → tenant_status = False；其他 → True
    plan_key = canonical_plan((req.plan_type or "unpaid").strip())
    tenant_value = False if plan_key == "unpaid" else True

    # 建立使用者（欄位存在才帶入，避免不同 DB 版本報錯）
    user_kwargs: Dict[str, Any] = {
        "client_id": req.client_id.strip(),
        "client_name": req.client_name.strip(),
        "password": req.password,           # 若已改為雜湊：password_hash=hash_password(req.password)
        "secret_code": sc,
        # ✅ 新規則：註冊預設 is_active=False
        "is_active": False,
    }
    if hasattr(LoginUser, "plan_type"):
        user_kwargs["plan_type"] = plan_key
    if hasattr(LoginUser, "tenant_status"):
        user_kwargs["tenant_status"] = tenant_value
    elif hasattr(LoginUser, "tenant_status"):
        user_kwargs["tenant_status"] = tenant_value

    user = LoginUser(**user_kwargs)
    db.add(user)
    db.commit()
    db.refresh(user)

    # === 立刻建立 tenant schema，並把 URL/READY 寫回 login_users ===
    try:
        tenant_url = ensure_tenant_schema(user.client_id)
        if hasattr(LoginUser, "tenant_db_url"):
            setattr(user, "tenant_db_url", tenant_url)
        if hasattr(LoginUser, "tenant_db_ready"):
            setattr(user, "tenant_db_ready", True)
        db.commit()
    except Exception as e:
        db.rollback()
        # 若建失敗，你可以選擇：保持帳號存在，但 tenant_db_ready=False
        try:
            if hasattr(LoginUser, "tenant_db_ready"):
                setattr(user, "tenant_db_ready", False)
            db.commit()
        except Exception:
            db.rollback()

    return RegisterResponse(
        message="註冊成功，請妥善保存您的登錄資訊。",
        client_id=user.client_id,
        secret_code=user.secret_code,
    )
