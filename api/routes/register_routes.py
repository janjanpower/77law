# api/routes/register_routes.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

# 導入新的資料庫模型
try:
    from api.database import get_control_db
    from api.models_control import LoginUser, ClientLineUsers
except ImportError:
    try:
        from database import get_control_db
        from models_control import LoginUser, ClientLineUsers
    except ImportError:
        # 如果模型不存在，在這裡定義
        from sqlalchemy import Column, Integer, String, DateTime, Boolean, func
        from sqlalchemy.ext.declarative import declarative_base
        Base = declarative_base()

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

router = APIRouter()

# Pydantic 模型
class ClientRegisterRequest(BaseModel):
    """事務所註冊請求"""
    client_name: str = Field(..., description="事務所名稱")
    client_id: str = Field(..., description="事務所專屬帳號")
    password: str = Field(..., description="登入密碼")
    plan_type: str = Field(default="basic_5", description="方案類型")
    contact_email: Optional[str] = Field(None, description="聯絡信箱")
    contact_phone: Optional[str] = Field(None, description="聯絡電話")

class LineUserRegisterRequest(BaseModel):
    """LINE用戶註冊請求"""
    line_user_id: str = Field(..., description="LINE用戶ID")
    client_name: str = Field(..., description="要綁定的事務所名稱")
    user_name: Optional[str] = Field(None, description="用戶名稱")

class RegisterResponse(BaseModel):
    """註冊回應"""
    success: bool
    message: str
    client_id: Optional[str] = None
    current_users: Optional[int] = None
    max_users: Optional[int] = None

@router.post("/register-client", response_model=RegisterResponse)
def register_client(request: ClientRegisterRequest, db: Session = Depends(get_control_db)):
    """註冊新的事務所客戶端"""
    try:
        # 檢查client_id是否已存在
        existing_client = db.query(LoginUser).filter(
            LoginUser.client_id == request.client_id
        ).first()

        if existing_client:
            raise HTTPException(
                status_code=400,
                detail="此客戶端ID已存在"
            )

        # 檢查client_name是否已存在
        existing_name = db.query(LoginUser).filter(
            LoginUser.client_name == request.client_name
        ).first()

        if existing_name:
            raise HTTPException(
                status_code=400,
                detail="此事務所名稱已存在"
            )

        # 設定方案人數限制
        plan_limits = {
            "basic_5": 5,
            "standard_10": 10,
            "premium_20": 20,
            "enterprise_50": 50
        }

        max_users = plan_limits.get(request.plan_type, 5)

        # 建立新的客戶端
        new_client = LoginUser(
            client_name=request.client_name,
            client_id=request.client_id,
            password=request.password,
            plan_type=request.plan_type,
            user_status="active",
            max_users=max_users,
            current_users=0,
            is_active=True
        )

        db.add(new_client)
        db.commit()
        db.refresh(new_client)

        print(f"✅ 新客戶端註冊成功: {request.client_name}")

        return RegisterResponse(
            success=True,
            message=f"事務所 {request.client_name} 註冊成功",
            client_id=request.client_id,
            current_users=0,
            max_users=max_users
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"註冊失敗: {str(e)}"
        )

@router.post("/register-line-user", response_model=RegisterResponse)
def register_line_user(request: LineUserRegisterRequest, db: Session = Depends(get_control_db)):
    """註冊LINE用戶到指定事務所"""
    try:
        # 根據事務所名稱找到對應的客戶端
        client = db.query(LoginUser).filter(
            LoginUser.client_name == request.client_name,
            LoginUser.is_active == True
        ).first()

        if not client:
            raise HTTPException(
                status_code=404,
                detail="找不到指定的事務所"
            )

        # 檢查方案是否已滿
        if client.current_users >= client.max_users:
            raise HTTPException(
                status_code=400,
                detail=f"事務所方案已滿 ({client.current_users}/{client.max_users})"
            )

        # 檢查LINE用戶是否已註冊
        existing_line_user = db.query(ClientLineUsers).filter(
            ClientLineUsers.line_user_id == request.line_user_id
        ).first()

        if existing_line_user:
            if existing_line_user.client_id == client.client_id:
                return RegisterResponse(
                    success=False,
                    message="此LINE用戶已綁定到該事務所"
                )
            else:
                raise HTTPException(
                    status_code=400,
                    detail="此LINE用戶已綁定到其他事務所"
                )

        # 新增LINE用戶
        new_line_user = ClientLineUsers(
            client_id=client.client_id,
            line_user_id=request.line_user_id,
            user_name=request.user_name,
            is_active=True
        )

        db.add(new_line_user)

        # 更新客戶端用戶數
        client.current_users += 1

        db.commit()

        print(f"✅ LINE用戶綁定成功: {request.line_user_id} -> {client.client_name}")

        return RegisterResponse(
            success=True,
            message=f"LINE用戶成功綁定到 {client.client_name}",
            client_id=client.client_id,
            current_users=client.current_users,
            max_users=client.max_users
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"綁定失敗: {str(e)}"
        )

@router.get("/client-info/{client_id}")
def get_client_info(client_id: str, db: Session = Depends(get_control_db)):
    """取得客戶端資訊"""
    try:
        client = db.query(LoginUser).filter(
            LoginUser.client_id == client_id
        ).first()

        if not client:
            raise HTTPException(status_code=404, detail="客戶端不存在")

        # 取得綁定的LINE用戶
        line_users = db.query(ClientLineUsers).filter(
            ClientLineUsers.client_id == client_id,
            ClientLineUsers.is_active == True
        ).all()

        return {
            "success": True,
            "data": {
                "client_name": client.client_name,
                "client_id": client.client_id,
                "plan_type": client.plan_type,
                "user_status": client.user_status,
                "current_users": len(line_users),
                "max_users": client.max_users,
                "is_active": client.is_active,
                "created_at": client.created_at.isoformat() if client.created_at else None,
                "line_users": [
                    {
                        "line_user_id": user.line_user_id,
                        "user_name": user.user_name,
                        "bound_at": user.bound_at.isoformat()
                    }
                    for user in line_users
                ]
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
