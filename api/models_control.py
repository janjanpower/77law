# -*- coding: utf-8 -*-
"""
api/models_control.py
法律案件管理系統 - 完整資料庫模型定義
整合 Heroku PostgreSQL 的使用者認證和 LINE 用戶管理
"""

from datetime import datetime
from typing import Dict, Any, List, Optional

from sqlalchemy import Column, Integer, String, DateTime, Boolean, func, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Session


# 使用現有的 Base 或建立新的
try:
    from api.database import Base
except ImportError:
    try:
        from database import Base
    except ImportError:
        from sqlalchemy.ext.declarative import declarative_base
        Base = declarative_base()

class LoginUser(Base):
    """事務所登入用戶表 - 主要認證表"""
    __tablename__ = "login_users"

    # 基本欄位
    id = Column(Integer, primary_key=True, index=True)
    client_name = Column(String(100), nullable=False, comment="事務所名稱")
    client_id = Column(String(50), unique=True, nullable=False, index=True, comment="事務所專屬帳號")
    password = Column(String(255), nullable=False, comment="密碼 (實際應用中應加密)")

    # 狀態欄位
    is_active = Column(Boolean, default=True, comment="是否啟用")
    user_status = Column(String(20), default="active", comment="用戶狀態: active, suspended, expired")

    # 時間欄位
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="建立時間")
    last_login = Column(DateTime(timezone=True), nullable=True, comment="最後登入時間")

    # 方案相關欄位
    plan_type = Column(String(30), default="basic_5", comment="方案類型")
    max_users = Column(Integer, default=5, comment="方案人數上限")
    current_users = Column(Integer, default=0, comment="目前 LINE 用戶數")

    # 關聯到 LINE 用戶
    line_users = relationship("ClientLineUsers", back_populates="client", cascade="all, delete-orphan")

    # ==================== 計算屬性 ====================

    @property
    def available_slots(self) -> int:
        """可用名額"""
        return max(0, self.max_users - self.current_users)

    @property
    def is_full(self) -> bool:
        """是否已滿"""
        return self.current_users >= self.max_users

    @property
    def usage_percentage(self) -> float:
        """使用率百分比"""
        if self.max_users == 0:
            return 0.0
        return round((self.current_users / self.max_users) * 100, 1)

    @property
    def plan_display_name(self) -> str:
        """方案顯示名稱"""
        plan_names = {
            "basic_5": "基礎方案 (5人)",
            "standard_10": "標準方案 (10人)",
            "premium_20": "進階方案 (20人)",
            "enterprise_50": "企業方案 (50人)",
            "unlimited": "無限制方案"
        }
        return plan_names.get(self.plan_type, f"自訂方案 ({self.max_users}人)")

    @property
    def status_display_name(self) -> str:
        """狀態顯示名稱"""
        status_names = {
            "active": "正常",
            "suspended": "暫停",
            "expired": "過期",
            "trial": "試用"
        }
        return status_names.get(self.user_status, self.user_status)

    @property
    def is_admin(self) -> bool:
        """是否為管理員 (企業方案以上)"""
        return self.plan_type in ["enterprise_50", "unlimited"]

    # ==================== 實例方法 ====================

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式"""
        return {
            "id": self.id,
            "client_name": self.client_name,
            "client_id": self.client_id,
            "is_active": self.is_active,
            "user_status": self.user_status,
            "status_display": self.status_display_name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "plan_type": self.plan_type,
            "plan_display": self.plan_display_name,
            "max_users": self.max_users,
            "current_users": self.current_users,
            "available_slots": self.available_slots,
            "usage_percentage": self.usage_percentage,
            "is_full": self.is_full,
            "is_admin": self.is_admin,
            "contact_email": self.contact_email,
            "contact_phone": self.contact_phone,
            "notes": self.notes
        }

    def update_user_count(self, db: Session):
        """更新當前用戶數量 (從 LINE 用戶表計算)"""
        count = db.query(ClientLineUsers).filter(
            ClientLineUsers.client_id == self.client_id,
            ClientLineUsers.is_active == True
        ).count()
        self.current_users = count
        return count

    def can_add_user(self) -> bool:
        """檢查是否可以新增用戶"""
        return self.current_users < self.max_users and self.user_status == "active"

    def __repr__(self):
        return f"<LoginUser(client_id='{self.client_id}', name='{self.client_name}', users={self.current_users}/{self.max_users})>"


class ClientLineUsers(Base):
    """LINE 用戶綁定表"""
    __tablename__ = "client_line_users"

    # 基本欄位
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(String(50), ForeignKey('login_users.client_id'), nullable=False, index=True, comment="所屬事務所ID")
    line_user_id = Column(String(100), nullable=False, unique=True, index=True, comment="LINE 用戶ID")
    user_name = Column(String(50), nullable=True, comment="用戶名稱")

    # 狀態和時間
    is_active = Column(Boolean, default=True, comment="是否啟用")
    bound_at = Column(DateTime(timezone=True), server_default=func.now(), comment="綁定時間")
    last_activity = Column(DateTime(timezone=True), nullable=True, comment="最後活動時間")

    # 額外資訊
    user_role = Column(String(20), default="member", comment="用戶角色: admin, member, viewer")
    notes = Column(Text, nullable=True, comment="備註")

    # 建立關聯
    client = relationship("LoginUser", back_populates="line_users")

    # ==================== 計算屬性 ====================

    @property
    def role_display_name(self) -> str:
        """角色顯示名稱"""
        role_names = {
            "admin": "管理員",
            "member": "成員",
            "viewer": "檢視者"
        }
        return role_names.get(self.user_role, self.user_role)

    @property
    def is_admin_role(self) -> bool:
        """是否為管理員角色"""
        return self.user_role == "admin"

    @property
    def binding_duration_days(self) -> int:
        """綁定天數"""
        if self.bound_at:
            return (datetime.now() - self.bound_at.replace(tzinfo=None)).days
        return 0

    # ==================== 實例方法 ====================

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式"""
        return {
            "id": self.id,
            "client_id": self.client_id,
            "line_user_id": self.line_user_id,
            "user_name": self.user_name,
            "is_active": self.is_active,
            "user_role": self.user_role,
            "role_display": self.role_display_name,
            "bound_at": self.bound_at.isoformat() if self.bound_at else None,
            "last_activity": self.last_activity.isoformat() if self.last_activity else None,
            "binding_duration_days": self.binding_duration_days,
            "notes": self.notes
        }

    def update_activity(self):
        """更新最後活動時間"""
        self.last_activity = datetime.now()

    def __repr__(self):
        return f"<ClientLineUsers(line_user_id='{self.line_user_id}', client_id='{self.client_id}', name='{self.user_name}')>"


class SystemSettings(Base):
    """系統設定表 (可選)"""
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, index=True)
    setting_key = Column(String(50), unique=True, nullable=False, comment="設定鍵")
    setting_value = Column(Text, nullable=True, comment="設定值")
    setting_type = Column(String(20), default="string", comment="設定類型: string, integer, boolean, json")
    description = Column(Text, nullable=True, comment="設定說明")
    is_active = Column(Boolean, default=True, comment="是否啟用")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "setting_key": self.setting_key,
            "setting_value": self.setting_value,
            "setting_type": self.setting_type,
            "description": self.description,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class LoginHistory(Base):
    """登入歷史記錄表 (可選)"""
    __tablename__ = "login_history"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(String(50), ForeignKey('login_users.client_id'), nullable=False, index=True)
    login_time = Column(DateTime(timezone=True), server_default=func.now(), comment="登入時間")
    ip_address = Column(String(45), nullable=True, comment="IP 位址")
    user_agent = Column(Text, nullable=True, comment="瀏覽器資訊")
    login_status = Column(String(20), default="success", comment="登入狀態: success, failed")
    failure_reason = Column(String(100), nullable=True, comment="失敗原因")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "client_id": self.client_id,
            "login_time": self.login_time.isoformat() if self.login_time else None,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "login_status": self.login_status,
            "failure_reason": self.failure_reason
        }


# ==================== 輔助功能和工具類別 ====================

class DatabaseManager:
    """資料庫管理器 - 提供常用的資料庫操作"""

    @staticmethod
    def get_client_by_id(db: Session, client_id: str) -> Optional[LoginUser]:
        """根據客戶端ID取得客戶端資料"""
        return db.query(LoginUser).filter(
            LoginUser.client_id == client_id,
            LoginUser.is_active == True
        ).first()

    @staticmethod
    def get_line_user_binding(db: Session, line_user_id: str) -> Optional[ClientLineUsers]:
        """根據LINE用戶ID取得綁定資料"""
        return db.query(ClientLineUsers).filter(
            ClientLineUsers.line_user_id == line_user_id,
            ClientLineUsers.is_active == True
        ).first()

    @staticmethod
    def get_client_line_users(db: Session, client_id: str) -> List[ClientLineUsers]:
        """取得事務所的所有LINE用戶"""
        return db.query(ClientLineUsers).filter(
            ClientLineUsers.client_id == client_id,
            ClientLineUsers.is_active == True
        ).all()

    @staticmethod
    def update_all_user_counts(db: Session):
        """更新所有事務所的用戶數量"""
        clients = db.query(LoginUser).filter(LoginUser.is_active == True).all()
        for client in clients:
            client.update_user_count(db)
        db.commit()

    @staticmethod
    def get_plan_statistics(db: Session) -> Dict[str, int]:
        """取得方案統計資料"""
        stats = {}
        plans = db.query(LoginUser.plan_type, func.count(LoginUser.id)).group_by(LoginUser.plan_type).all()
        for plan_type, count in plans:
            stats[plan_type] = count
        return stats

    @staticmethod
    def get_active_clients_count(db: Session) -> int:
        """取得活躍客戶端數量"""
        return db.query(LoginUser).filter(
            LoginUser.is_active == True,
            LoginUser.user_status == "active"
        ).count()

    @staticmethod
    def get_total_line_users_count(db: Session) -> int:
        """取得總LINE用戶數量"""
        return db.query(ClientLineUsers).filter(ClientLineUsers.is_active == True).count()


# ==================== 資料驗證和常數 ====================

class PlanTypes:
    """方案類型常數"""
    BASIC_5 = "basic_5"
    STANDARD_10 = "standard_10"
    PREMIUM_20 = "premium_20"
    ENTERPRISE_50 = "enterprise_50"
    UNLIMITED = "unlimited"

    @classmethod
    def get_all_plans(cls) -> List[str]:
        return [cls.BASIC_5, cls.STANDARD_10, cls.PREMIUM_20, cls.ENTERPRISE_50, cls.UNLIMITED]

    @classmethod
    def get_plan_limits(cls) -> Dict[str, int]:
        return {
            cls.BASIC_5: 5,
            cls.STANDARD_10: 10,
            cls.PREMIUM_20: 20,
            cls.ENTERPRISE_50: 50,
            cls.UNLIMITED: 999999
        }


class UserStatus:
    """用戶狀態常數"""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    EXPIRED = "expired"
    TRIAL = "trial"

    @classmethod
    def get_all_statuses(cls) -> List[str]:
        return [cls.ACTIVE, cls.SUSPENDED, cls.EXPIRED, cls.TRIAL]


class UserRoles:
    """用戶角色常數"""
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"

    @classmethod
    def get_all_roles(cls) -> List[str]:
        return [cls.ADMIN, cls.MEMBER, cls.VIEWER]


# ==================== 使用範例 ====================

if __name__ == "__main__":
    """測試模型定義"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    # 建立測試資料庫
    DATABASE_URL = "sqlite:///./test_models.db"
    engine = create_engine(DATABASE_URL, echo=True)

    # 建立所有表格
    Base.metadata.create_all(bind=engine)

    # 建立會話
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        # 建立測試資料
        test_client = LoginUser(
            client_name="測試事務所",
            client_id="test_001",
            password="test123",
            plan_type=PlanTypes.BASIC_5,
            max_users=5
        )

        db.add(test_client)
        db.commit()

        # 測試方法
        print("✅ 模型測試成功")
        print(f"客戶端資料: {test_client.to_dict()}")
        print(f"可用名額: {test_client.available_slots}")
        print(f"方案顯示: {test_client.plan_display_name}")

    except Exception as e:
        print(f"❌ 模型測試失敗: {e}")
        db.rollback()
    finally:
        db.close()


class TenantUser(Base):
    """子帳號（事務所成員）登入表"""
    __tablename__ = "tenant_users"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(50), ForeignKey('login_users.client_id'), nullable=False, index=True, comment="所屬事務所ID")
    line_user_id = Column(String(100), unique=True, nullable=True, comment="LINE 使用者 ID")  # ← 加這行！
    username = Column(String(50), unique=True, nullable=False, comment="帳號名稱")
    password = Column(String(255), nullable=False, comment="密碼")
    is_active = Column(Boolean, default=True, comment="是否啟用")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)

