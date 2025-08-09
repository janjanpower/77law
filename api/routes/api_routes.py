# -*- coding: utf-8 -*-
"""
api/routes/auth_routes.py
完整的帳密驗證 API 路由 - 整合 Heroku PostgreSQL 資料庫
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from datetime import datetime
import hashlib
import os

# 根據您的專案結構調整導入路徑
try:
    from api.database import get_control_db, Base, engine
    from api.models_control import LoginUser, ClientLineUsers
except ImportError:
    try:
        from database import get_control_db, Base, engine
        from models_control import LoginUser, ClientLineUsers
    except ImportError:
        # 如果模型不存在，在這裡定義完整模型
        from sqlalchemy import Column, Integer, String, DateTime, Boolean, func
        from sqlalchemy.ext.declarative import declarative_base
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        # 資料庫設定
        DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./law_system.db")
        if DATABASE_URL.startswith("postgres://"):
            DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

        engine = create_engine(DATABASE_URL, echo=True)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        Base = declarative_base()

        def get_control_db():
            db = SessionLocal()
            try:
                yield db
            finally:
                db.close()

        class LoginUser(Base):
            __tablename__ = "login_users"
            id = Column(Integer, primary_key=True, index=True)
            client_name = Column(String, nullable=False)
            client_id = Column(String, unique=True, nullable=False)
            password = Column(String, nullable=False)
            is_active = Column(Boolean, default=True)
            created_at = Column(DateTime(timezone=True), server_default=func.now())
            last_login = Column(DateTime(timezone=True), nullable=True)
            plan_type = Column(String, default="basic_5")
            user_status = Column(String, default="active")
            max_users = Column(Integer, default=5)
            current_users = Column(Integer, default=0)

        class ClientLineUsers(Base):
            __tablename__ = "client_line_users"
            id = Column(Integer, primary_key=True, index=True)
            client_id = Column(String, nullable=False)
            line_user_id = Column(String, nullable=False, unique=True)
            user_name = Column(String, nullable=True)
            bound_at = Column(DateTime(timezone=True), server_default=func.now())
            is_active = Column(Boolean, default=True)

# 建立路由器
router = APIRouter()

# ==================== Pydantic 模型定義 ====================

class ClientLoginRequest(BaseModel):
    """客戶端登入請求模型"""
    client_id: str = Field(..., description="事務所客戶端ID", min_length=1, max_length=50)
    password: str = Field(..., description="密碼", min_length=1)

class ClientLoginResponse(BaseModel):
    """客戶端登入回應模型"""
    success: bool
    message: str
    client_data: Dict[str, Any] = {}

class UserPlanInfo(BaseModel):
    """使用者方案資訊模型"""
    client_id: str
    client_name: str
    plan_type: str
    max_users: int
    current_users: int
    available_slots: int
    usage_percentage: float
    user_status: str

class LineUserBindRequest(BaseModel):
    """LINE 使用者綁定請求"""
    client_id: str = Field(..., description="事務所客戶端ID")
    line_user_id: str = Field(..., description="LINE 使用者ID")
    user_name: Optional[str] = Field(None, description="使用者名稱")

# ==================== 主要 API 端點 ====================

@router.post("/client-login", response_model=ClientLoginResponse)
def client_login(request: ClientLoginRequest, db: Session = Depends(get_control_db)):
    """
    客戶端登入驗證端點

    Args:
        request: 登入請求資料
        db: 資料庫會話

    Returns:
        登入結果和使用者資料
    """
    try:
        print(f"🔍 收到登入請求: client_id={request.client_id}")

        # 查詢客戶端資料
        client = db.query(LoginUser).filter(
            LoginUser.client_id == request.client_id,
            LoginUser.password == request.password,  # 注意：實際應用中應使用加密密碼
            LoginUser.is_active == True
        ).first()

        if not client:
            print(f"❌ 登入失敗: 找不到匹配的客戶端 - ID: {request.client_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="客戶端ID或密碼錯誤"
            )

        # 檢查帳戶狀態
        if client.user_status != "active":
            print(f"❌ 登入失敗: 帳戶狀態異常 - {client.user_status}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"帳戶狀態異常: {client.user_status}"
            )

        # 更新最後登入時間
        client.last_login = datetime.now()

        # 重新計算當前使用者數量
        current_line_users = db.query(ClientLineUsers).filter(
            ClientLineUsers.client_id == client.client_id,
            ClientLineUsers.is_active == True
        ).count()
        client.current_users = current_line_users

        db.commit()

        # 準備回傳的客戶端資料
        client_data = {
            "client_id": client.client_id,
            "client_name": client.client_name,
            "plan_type": client.plan_type,
            "user_status": client.user_status,
            "max_users": client.max_users,
            "current_users": client.current_users,
            "available_slots": max(0, client.max_users - client.current_users),
            "usage_percentage": round((client.current_users / client.max_users) * 100, 1) if client.max_users > 0 else 0,
            "last_login": client.last_login.isoformat() if client.last_login else None,
            "created_at": client.created_at.isoformat() if client.created_at else None,
            "is_admin": client.plan_type in ["enterprise_50", "unlimited"]  # 判斷管理員權限
        }

        print(f"✅ 登入成功: {client.client_name} ({client.client_id})")

        return ClientLoginResponse(
            success=True,
            message=f"歡迎 {client.client_name}！",
            client_data=client_data
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 登入程序錯誤: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"伺服器內部錯誤: {str(e)}"
        )

@router.get("/client/{client_id}/plan-info", response_model=UserPlanInfo)
def get_client_plan_info(client_id: str, db: Session = Depends(get_control_db)):
    """
    取得客戶端方案資訊

    Args:
        client_id: 客戶端ID
        db: 資料庫會話

    Returns:
        方案詳細資訊
    """
    try:
        client = db.query(LoginUser).filter(
            LoginUser.client_id == client_id,
            LoginUser.is_active == True
        ).first()

        if not client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="找不到該客戶端"
            )

        # 重新計算當前使用者數量
        current_line_users = db.query(ClientLineUsers).filter(
            ClientLineUsers.client_id == client.client_id,
            ClientLineUsers.is_active == True
        ).count()

        return UserPlanInfo(
            client_id=client.client_id,
            client_name=client.client_name,
            plan_type=client.plan_type,
            max_users=client.max_users,
            current_users=current_line_users,
            available_slots=max(0, client.max_users - current_line_users),
            usage_percentage=round((current_line_users / client.max_users) * 100, 1) if client.max_users > 0 else 0,
            user_status=client.user_status
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查詢失敗: {str(e)}"
        )

@router.post("/bind-line-user")
def bind_line_user(request: LineUserBindRequest, db: Session = Depends(get_control_db)):
    """
    綁定 LINE 使用者到事務所

    Args:
        request: 綁定請求資料
        db: 資料庫會話

    Returns:
        綁定結果
    """
    try:
        # 檢查客戶端是否存在
        client = db.query(LoginUser).filter(
            LoginUser.client_id == request.client_id,
            LoginUser.is_active == True
        ).first()

        if not client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="找不到該事務所"
            )

        # 檢查是否已達人數上限
        current_users = db.query(ClientLineUsers).filter(
            ClientLineUsers.client_id == request.client_id,
            ClientLineUsers.is_active == True
        ).count()

        if current_users >= client.max_users:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"已達人數上限 ({client.max_users} 人)"
            )

        # 檢查 LINE 使用者是否已被其他事務所綁定
        existing_binding = db.query(ClientLineUsers).filter(
            ClientLineUsers.line_user_id == request.line_user_id,
            ClientLineUsers.is_active == True
        ).first()

        if existing_binding:
            if existing_binding.client_id == request.client_id:
                return {"success": True, "message": "該使用者已綁定到此事務所"}
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="該 LINE 使用者已綁定到其他事務所"
                )

        # 建立新的綁定記錄
        new_binding = ClientLineUsers(
            client_id=request.client_id,
            line_user_id=request.line_user_id,
            user_name=request.user_name,
            is_active=True
        )

        db.add(new_binding)

        # 更新客戶端的當前使用者數
        client.current_users = current_users + 1

        db.commit()

        return {
            "success": True,
            "message": f"成功綁定使用者到 {client.client_name}",
            "binding_info": {
                "client_name": client.client_name,
                "user_name": request.user_name,
                "bound_at": new_binding.bound_at.isoformat(),
                "remaining_slots": client.max_users - client.current_users
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"綁定失敗: {str(e)}"
        )

@router.delete("/unbind-line-user/{line_user_id}")
def unbind_line_user(line_user_id: str, db: Session = Depends(get_control_db)):
    """
    解除 LINE 使用者綁定

    Args:
        line_user_id: LINE 使用者ID
        db: 資料庫會話

    Returns:
        解綁結果
    """
    try:
        # 查找綁定記錄
        binding = db.query(ClientLineUsers).filter(
            ClientLineUsers.line_user_id == line_user_id,
            ClientLineUsers.is_active == True
        ).first()

        if not binding:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="找不到該使用者的綁定記錄"
            )

        # 取得客戶端資訊
        client = db.query(LoginUser).filter(
            LoginUser.client_id == binding.client_id
        ).first()

        # 標記為非啟用 (軟刪除)
        binding.is_active = False

        # 更新客戶端的使用者數量
        if client:
            client.current_users = max(0, client.current_users - 1)

        db.commit()

        return {
            "success": True,
            "message": "成功解除使用者綁定",
            "client_name": client.client_name if client else "Unknown"
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"解綁失敗: {str(e)}"
        )

@router.get("/health")
def health_check():
    """健康檢查端點"""
    return {
        "status": "healthy",
        "service": "法律案件管理系統 認證服務",
        "version": "2.0",
        "timestamp": datetime.now().isoformat()
    }

@router.get("/test")
def test_endpoint():
    """測試端點"""
    return {
        "message": "認證 API 正常運作",
        "endpoints": [
            "/api/auth/client-login - 客戶端登入",
            "/api/auth/client/{client_id}/plan-info - 方案資訊",
            "/api/auth/bind-line-user - 綁定 LINE 使用者",
            "/api/auth/unbind-line-user/{line_user_id} - 解綁 LINE 使用者",
            "/api/auth/health - 健康檢查",
            "/api/auth/test - 測試端點"
        ]
    }

# ==================== 資料庫初始化 ====================

def init_database():
    """初始化資料庫和測試資料"""
    try:
        # 建立所有表格
        Base.metadata.create_all(bind=engine)
        print("✅ 資料表創建成功")

        # 檢查是否需要插入測試資料
        from sqlalchemy.orm import sessionmaker
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()

        try:
            # 檢查是否已有資料
            existing_clients = db.query(LoginUser).count()

            if existing_clients == 0:
                print("🔧 插入測試資料...")

                # 建立測試客戶端
                test_clients = [
                    LoginUser(
                        client_name="測試法律事務所",
                        client_id="test_law_firm",
                        password="test123",  # 實際應用中應加密
                        plan_type="basic_5",
                        max_users=5,
                        current_users=0,
                        is_active=True
                    ),
                    LoginUser(
                        client_name="專業法律顧問",
                        client_id="professional_legal",
                        password="pro123",
                        plan_type="standard_10",
                        max_users=10,
                        current_users=0,
                        is_active=True
                    ),
                    LoginUser(
                        client_name="大型律師事務所",
                        client_id="large_law_firm",
                        password="large123",
                        plan_type="enterprise_50",
                        max_users=50,
                        current_users=0,
                        is_active=True
                    )
                ]

                for client in test_clients:
                    db.add(client)

                db.commit()
                print("✅ 測試資料插入完成")

                # 顯示測試帳號資訊
                print("\n📋 測試帳號清單:")
                for client in test_clients:
                    print(f"  - 事務所: {client.client_name}")
                    print(f"    帳號: {client.client_id}")
                    print(f"    密碼: {client.password}")
                    print(f"    方案: {client.plan_type} ({client.max_users}人)")
                    print()

        except Exception as e:
            db.rollback()
            print(f"❌ 插入測試資料失敗: {e}")
            raise
        finally:
            db.close()

    except Exception as e:
        print(f"❌ 資料庫初始化失敗: {e}")
        raise

# ==================== 啟動時自動初始化 ====================

# 當模組被導入時自動初始化資料庫
try:
    init_database()
except Exception as e:
    print(f"⚠️ 資料庫自動初始化失敗: {e}")

if __name__ == "__main__":
    print("🚀 測試認證 API 路由...")
    init_database()
    print("✅ 認證 API 路由設定完成！")