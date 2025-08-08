# api/routes/login_routes.py
"""
登入路由控制層
統一處理所有登入相關的API端點
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Optional, Union
from api.database import get_control_db
from api.services.auth_service import AuthService

router = APIRouter()

# 初始化認證服務
auth_service = AuthService()

# Pydantic 模型定義
class LineLoginRequest(BaseModel):
    """LINE 用戶登入請求"""
    user_id: str = Field(..., description="LINE 用戶ID")

class UsernamePasswordLoginRequest(BaseModel):
    """用戶名密碼登入請求"""
    username: str = Field(..., description="用戶名")
    password: str = Field(..., description="密碼")

class TenantUserLoginRequest(BaseModel):
    """租戶用戶登入請求"""
    schema_name: str = Field(..., description="租戶 Schema 名稱")
    user_name: str = Field(..., description="用戶名稱")

class LoginResponse(BaseModel):
    """統一的登入回應"""
    success: bool
    message: str
    user_data: Optional[dict] = None
    login_type: Optional[str] = None

# API 端點定義

@router.post("/login/line", response_model=LoginResponse)
def login_with_line_user_id(
    request: LineLoginRequest,
    db: Session = Depends(get_control_db)
):
    """
    使用 LINE 用戶ID 登入

    Args:
        request: LINE 登入請求
        db: 資料庫會話

    Returns:
        LoginResponse: 登入結果
    """
    try:
        user_data = auth_service.authenticate_by_line_user_id(request.user_id, db)

        if user_data:
            return LoginResponse(
                success=True,
                message=f"✅ LINE 用戶登入成功，歡迎 {user_data['client_name']}",
                user_data=user_data,
                login_type="line_user_id"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="找不到對應的 LINE 用戶"
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"登入過程發生錯誤: {str(e)}"
        )

@router.post("/login/username", response_model=LoginResponse)
def login_with_username_password(
    request: UsernamePasswordLoginRequest,
    db: Session = Depends(get_control_db)
):
    """
    使用用戶名和密碼登入

    Args:
        request: 用戶名密碼登入請求
        db: 資料庫會話

    Returns:
        LoginResponse: 登入結果
    """
    try:
        user_data = auth_service.authenticate_by_username_password(
            request.username,
            request.password,
            db
        )

        if user_data:
            return LoginResponse(
                success=True,
                message=f"✅ 用戶登入成功，歡迎 {user_data['username']}",
                user_data=user_data,
                login_type="username_password"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用戶名或密碼錯誤"
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"登入過程發生錯誤: {str(e)}"
        )

@router.post("/login/tenant", response_model=LoginResponse)
def login_with_tenant_user(
    request: TenantUserLoginRequest,
    db: Session = Depends(get_control_db)
):
    """
    租戶用戶登入（在特定 schema 中查詢）

    Args:
        request: 租戶用戶登入請求
        db: 資料庫會話

    Returns:
        LoginResponse: 登入結果
    """
    try:
        user_data = auth_service.authenticate_tenant_user(
            request.schema_name,
            request.user_name,
            db
        )

        if user_data:
            return LoginResponse(
                success=True,
                message=f"✅ 租戶用戶登入成功，歡迎 {request.user_name}",
                user_data=user_data,
                login_type="tenant_user"
            )
        else:
            # 檢查是租戶不存在還是用戶不存在
            if not auth_service.validate_tenant_exists(request.schema_name, db):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="租戶不存在"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="在該租戶中找不到此用戶"
                )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"登入過程發生錯誤: {str(e)}"
        )

# 通用登入端點（向後兼容）
@router.post("/login", response_model=LoginResponse)
def universal_login(
    user_id: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    schema_name: Optional[str] = None,
    user_name: Optional[str] = None,
    db: Session = Depends(get_control_db)
):
    """
    通用登入端點，支援多種登入方式
    優先順序：LINE user_id > 用戶名密碼 > 租戶用戶

    Args:
        user_id: LINE 用戶ID（選填）
        username: 用戶名（選填）
        password: 密碼（選填）
        schema_name: 租戶 Schema（選填）
        user_name: 租戶內的用戶名（選填）
        db: 資料庫會話

    Returns:
        LoginResponse: 登入結果
    """
    try:
        # 方式 1: LINE 用戶ID 登入
        if user_id:
            user_data = auth_service.authenticate_by_line_user_id(user_id, db)
            if user_data:
                return LoginResponse(
                    success=True,
                    message=f"✅ LINE 用戶登入成功",
                    user_data=user_data,
                    login_type="line_user_id"
                )

        # 方式 2: 用戶名密碼登入
        elif username and password:
            user_data = auth_service.authenticate_by_username_password(username, password, db)
            if user_data:
                return LoginResponse(
                    success=True,
                    message=f"✅ 用戶登入成功",
                    user_data=user_data,
                    login_type="username_password"
                )

        # 方式 3: 租戶用戶登入
        elif schema_name and user_name:
            user_data = auth_service.authenticate_tenant_user(schema_name, user_name, db)
            if user_data:
                return LoginResponse(
                    success=True,
                    message=f"✅ 租戶用戶登入成功",
                    user_data=user_data,
                    login_type="tenant_user"
                )

        # 沒有提供足夠的認證資訊
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="請提供以下任一組認證資訊: (user_id) 或 (username + password) 或 (schema_name + user_name)"
            )

        # 所有認證方式都失敗
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="認證失敗，請檢查您的登入資訊"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"登入過程發生錯誤: {str(e)}"
        )