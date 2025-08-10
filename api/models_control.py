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
