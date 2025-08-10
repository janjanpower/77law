# api/models_control.py
# 注意：全專案只用 api.database 的 Base，避免 Table 重新定義衝突

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, func
try:
    from api.database import Base
except ImportError:
    # fallback for relative run
    from database import Base  # type: ignore

class LoginUser(Base):
    __tablename__ = "login_users"
    id = Column(Integer, primary_key=True, index=True)
    client_name = Column(String, nullable=False, unique=True)
    client_id = Column(String, nullable=False, unique=True)
    password = Column(String, nullable=False)  # TODO: 後續可改為 password_hash
    # 統一：DB 端也保底預設 unpaid
    plan_type = Column(Text, nullable=False, server_default="unpaid")
    # 依現行命名沿用：unpaid -> NULL；付費 -> TRUE
    teanat_status = Column(Boolean, nullable=True)
    user_status = Column(String, default="active")
    max_users = Column(Integer, default=0)
    current_users = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)

class ClientLineUsers(Base):
    __tablename__ = "client_line_users"
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(String, nullable=False)
    line_user_id = Column(String, nullable=False, unique=True)
    user_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    bound_at = Column(DateTime(timezone=True), server_default=func.now())
