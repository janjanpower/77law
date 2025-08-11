# api/models_control.py
# 注意：全專案只用 api.database 的 Base，避免 Table 重新定義衝突

from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text, func, Enum as SAEnum
)
try:
    from api.database import Base
except ImportError:
    from database import Base  # type: ignore

# 與資料庫端 ENUM 對齊
PlanTypeEnum = SAEnum(
    'unpaid', 'basic_5', 'pro_10', 'team_20', 'unlimited',
    name='plan_type_enum'
)

class LoginUser(Base):
    __tablename__ = "login_users"

    id = Column(Integer, primary_key=True, index=True)
    client_name = Column(String, nullable=False, unique=True)
    client_id = Column(String, nullable=False, unique=True)
    password = Column(String, nullable=False)  # TODO: 後續可改為 password_hash

    # 方案與狀態
    plan_type = Column(PlanTypeEnum, nullable=False, server_default="unpaid")
    tenant_status = Column(Boolean, nullable=False, server_default="false")  # 由觸發器維護
    is_active = Column(Boolean, nullable=False, server_default="false")  # 後台人工啟用

    # 付費區間
    paid_from = Column(DateTime(timezone=True), nullable=True)
    paid_until = Column(DateTime(timezone=True), nullable=True)

    # 統計資訊
    user_status = Column(String, default="active")
    max_users = Column(Integer, default=0)
    current_users = Column(Integer, default=0)

    # 事務所專屬案件庫資訊
    tenant_db_url = Column(Text, nullable=True)
    tenant_db_ready = Column(Boolean, nullable=False, server_default="false")

    # 其他欄位
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)
    secret_code = Column(String(32), unique=True, nullable=True)


class ClientLineUsers(Base):
    __tablename__ = "client_line_users"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(String, nullable=False)
    line_user_id = Column(String, nullable=False, unique=True)
    user_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    bound_at = Column(DateTime(timezone=True), server_default=func.now())


# === Pending (unbound) LINE users: model + helpers ============================
from typing import Optional, Dict
from datetime import datetime, timezone, timedelta
from sqlalchemy import Column, BigInteger, String, DateTime, func, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.engine import Engine

from api.database import Base  # 使用你現有的 Base（中央 DB）

class PendingLineUser(Base):
    """
    精簡版暫存：不是律師、也不是 secret code 的 LINE 使用者
    只存最小必要欄位，方便回覆「登入 XXX」。
    """
    __tablename__ = "pending_line_users"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    line_user_id = Column(String(128), unique=True, nullable=False)
    expected_name = Column(String(128))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

# ---- Tenant engine/session cache（避免每次新建連線）----
_TENANT_ENGINES: Dict[str, Engine] = {}
_TENANT_SESSIONMAKERS: Dict[str, sessionmaker] = {}

def _normalize_pg_url(url: str) -> str:
    return url.replace("postgres://", "postgresql://", 1) if url and url.startswith("postgres://") else url

def get_tenant_engine(client_id: str, tenant_db_url: str) -> Engine:
    if client_id in _TENANT_ENGINES:
        return _TENANT_ENGINES[client_id]
    # 小連線池，避免多租戶爆連線
    engine = create_engine(_normalize_pg_url(tenant_db_url), pool_pre_ping=True, pool_size=1, max_overflow=0)
    _TENANT_ENGINES[client_id] = engine
    return engine

def get_tenant_sessionmaker(client_id: str, tenant_db_url: str) -> sessionmaker:
    if client_id in _TENANT_SESSIONMAKERS:
        return _TENANT_SESSIONMAKERS[client_id]
    eng = get_tenant_engine(client_id, tenant_db_url)
    sm = sessionmaker(bind=eng, autoflush=False, autocommit=False)
    _TENANT_SESSIONMAKERS[client_id] = sm
    # 若你之後導入 Alembic，可移除此行；目前先確保租戶 DB 有這張表
    PendingLineUser.__table__.create(bind=eng, checkfirst=True)
    return sm

# 寫中央 DB（當下無法判斷屬於哪個事務所時）
def track_pending_central(db: Session, *, line_user_id: str, expected_name: Optional[str] = None) -> PendingLineUser:
    u = db.query(PendingLineUser).filter_by(line_user_id=line_user_id).first()
    if u:
        if expected_name and not u.expected_name:
            u.expected_name = expected_name
    else:
        u = PendingLineUser(line_user_id=line_user_id, expected_name=expected_name)
        db.add(u)
    db.commit(); db.refresh(u)
    return u

# 寫指定事務所（tenant）DB
def track_pending_in_tenant(*, client_id: str, tenant_db_url: str, line_user_id: str, expected_name: Optional[str] = None) -> PendingLineUser:
    SM = get_tenant_sessionmaker(client_id, tenant_db_url)
    with SM() as tdb:
        u = tdb.query(PendingLineUser).filter_by(line_user_id=line_user_id).first()
        if u:
            if expected_name and not u.expected_name:
                u.expected_name = expected_name
        else:
            u = PendingLineUser(line_user_id=line_user_id, expected_name=expected_name)
            tdb.add(u)
        tdb.commit(); tdb.refresh(u)
        return u
