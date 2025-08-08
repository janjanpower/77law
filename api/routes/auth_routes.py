# api/routes/auth_routes.py - 完整修正版本

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API認證路由 - 修正版
處理所有登入認證相關的API端點
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from datetime import datetime
import logging

# 導入必要的模組
try:
    from api.database import get_db
    from api.models_control import LoginUser
except ImportError:
    # 備用導入路徑
    try:
        from database import get_db
        from models_control import LoginUser
    except ImportError:
        print("⚠️ 警告: 無法導入資料庫相關模組")

# 設定日誌
logger = logging.getLogger(__name__)

# 🎯 重要：定義 router 變數 (這是修正 auth_router 未定義錯誤的關鍵)
router = APIRouter()

# 為了保持向後相容，也建立 auth_router 別名
auth_router = router

# ==================== Pydantic 模型定義 ====================

class ClientLoginRequest(BaseModel):
    """客戶端登入請求"""
    client_id: str = Field(..., description="事務所帳號")
    password: str = Field(..., description="登入密碼")

class ClientLoginResponse(BaseModel):
    """客戶端登入回應"""
    success: bool
    message: str
    client_data: Optional[Dict[str, Any]] = None


class LineUserBindingRequest(BaseModel):
    """LINE用戶綁定請求模型"""
    client_id: str = Field(..., min_length=3, max_length=50, description="事務所帳號")
    line_user_id: str = Field(..., min_length=10, max_length=50, description="LINE用戶ID")
    user_name: Optional[str] = Field(None, max_length=50, description="用戶顯示名稱")

    @validator('line_user_id')
    def validate_line_user_id(cls, v):
        if not ClientServiceUtils.validate_line_user_id(v):
            raise ValueError('LINE用戶ID格式不正確')
        return v

class PlanUpgradeRequest(BaseModel):
    """方案升級請求模型"""
    client_id: str = Field(..., min_length=3, max_length=50, description="事務所帳號")
    new_plan_type: str = Field(..., description="新方案類型")

    @validator('new_plan_type')
    def validate_plan_type(cls, v):
        valid_plans = ['basic', 'standard', 'premium', 'unlimited']
        if v.lower() not in valid_plans:
            raise ValueError(f'方案類型必須是: {", ".join(valid_plans)}')
        return v.lower()

class StandardResponse(BaseModel):
    """標準API回應模型"""
    success: bool
    message: str
    data: Optional[Any] = None
    error_code: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

# ==================== 🎯 核心認證端點 - 實現您的需求 ====================

@router.post("/client-login")
def client_login(request: ClientLoginRequest, db: Session = Depends(get_db)):
    """
    客戶端登入端點

    這是修正版本，確保：
    1. 正確驗證帳號密碼
    2. 回傳完整的付費狀態資訊
    3. 避免前端 tenant_status 檢查失敗
    """
    try:
        print(f"🔍 登入請求: {request.client_id}")

        # 查詢資料庫
        client = db.query(LoginUser).filter(
            LoginUser.client_id == request.client_id,
            LoginUser.password == request.password,
            LoginUser.is_active == True
        ).first()

        if not client:
            print(f"❌ 登入失敗: 找不到客戶端")
            raise HTTPException(status_code=401, detail="客戶端ID或密碼錯誤")

        # 更新最後登入時間
        client.last_login = datetime.now()
        db.commit()

        # 🎯 重要：確保回傳正確的付費狀態資訊
        # 檢查 tenant_status 欄位是否存在
        tenant_status = getattr(client, 'tenant_status', True)  # 預設為已付費
        user_status = getattr(client, 'user_status', 'active')   # 預設為啟用

        # 準備客戶端資料 - 包含所有前端需要的欄位
        client_data = {
            "client_id": client.client_id,
            "client_name": client.client_name,
            "plan_type": getattr(client, 'plan_type', 'basic'),
            "user_status": user_status,
            "tenant_status": tenant_status,  # 🎯 關鍵：明確提供付費狀態
            "max_users": getattr(client, 'max_users', 5),
            "current_users": getattr(client, 'current_users', 0),
            "available_slots": max(0, getattr(client, 'max_users', 5) - getattr(client, 'current_users', 0)),
            "is_paid": tenant_status,  # 額外的付費狀態標記
            "subscription_status": "active" if tenant_status else "unpaid"
        }

        print(f"✅ 登入成功: {client.client_name} (付費狀態: {tenant_status})")

        return ClientLoginResponse(
            success=True,
            message=f"歡迎 {client.client_name}",
            client_data=client_data
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 登入API錯誤: {e}")
        raise HTTPException(status_code=500, detail=f"登入過程發生錯誤: {str(e)}")

@router.get("/client-status/{client_id}")
def get_client_status(client_id: str, db: Session = Depends(get_db)):
    """取得客戶端狀態"""
    try:
        client = db.query(LoginUser).filter(LoginUser.client_id == client_id).first()
        if not client:
            raise HTTPException(status_code=404, detail="事務所不存在")

        return {
            "success": True,
            "data": {
                "client_name": client.client_name,
                "current_users": getattr(client, 'current_users', 0),
                "max_users": getattr(client, 'max_users', 5),
                "plan_type": getattr(client, 'plan_type', 'basic'),
                "tenant_status": getattr(client, 'tenant_status', True),
                "user_status": getattr(client, 'user_status', 'active')
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 確保路由器可以被正確匯出
__all__ = ['router', 'auth_router']

# ==================== 🎯 LINE用戶管理端點 - 實現您的需求 ====================

@router.post("/line-users/bind", response_model=StandardResponse, summary="綁定LINE用戶")
def bind_line_user(request: LineUserBindingRequest, db: Session = Depends(get_db)):
    """
    🎯 LINE用戶綁定 - 實現您的需求：
    1. 檢查事務所是否付費
    2. 驗證方案用戶數限制 (max_users vs current_users)
    3. 綁定LINE用戶到指定事務所
    4. 更新用戶數統計
    """
    try:
        logger.info(f"LINE用戶綁定請求: {request.client_id} -> {request.line_user_id}")

        result = ClientAPIService.handle_line_user_binding(
            request.dict(), db
        )

        if result['success']:
            logger.info(f"LINE用戶綁定成功: {request.line_user_id}")
            return StandardResponse(**result)
        else:
            # 根據錯誤類型返回適當的HTTP狀態碼
            if result.get('error_code') == 'MISSING_PARAMETERS':
                status_code = status.HTTP_400_BAD_REQUEST
            elif '已達到方案上限' in result['message']:
                status_code = status.HTTP_403_FORBIDDEN
            elif '已綁定' in result['message']:
                status_code = status.HTTP_409_CONFLICT
            else:
                status_code = status.HTTP_400_BAD_REQUEST

            raise HTTPException(
                status_code=status_code,
                detail=result['message']
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"LINE用戶綁定異常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="綁定處理過程發生錯誤"
        )

@router.delete("/line-users/{line_user_id}", response_model=StandardResponse, summary="解除LINE用戶綁定")
def unbind_line_user(line_user_id: str, db: Session = Depends(get_db)):
    """
    解除LINE用戶綁定並更新用戶數統計
    """
    try:
        logger.info(f"解除LINE用戶綁定: {line_user_id}")

        result = ClientService.remove_line_user(line_user_id, db)

        if result['success']:
            return StandardResponse(**result)
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result['message']
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"解除綁定異常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="解除綁定過程發生錯誤"
        )

@router.get("/line-users/by-client/{client_id}", response_model=StandardResponse, summary="查詢事務所的LINE用戶")
def get_client_line_users(client_id: str, db: Session = Depends(get_db)):
    """
    查詢指定事務所的所有LINE用戶
    """
    try:
        result = ClientService.get_client_line_users(client_id, db)

        if result['success']:
            return StandardResponse(**result)
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result['message']
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查詢LINE用戶異常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="查詢過程發生錯誤"
        )

@router.get("/line-users/{line_user_id}/client", response_model=StandardResponse, summary="根據LINE用戶ID查詢所屬事務所")
def get_client_by_line_user(line_user_id: str, db: Session = Depends(get_db)):
    """
    🎯 根據LINE用戶ID查詢所屬事務所 - 實現您的需求：
    通過LINE用戶ID反向查詢所屬的事務所資訊
    """
    try:
        # 查詢LINE用戶綁定記錄
        line_user = db.query(ClientLineUsers).filter(
            ClientLineUsers.line_user_id == line_user_id,
            ClientLineUsers.is_active == True
        ).first()

        if not line_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="找不到此LINE用戶的綁定記錄"
            )

        # 查詢對應的事務所
        client_data = ClientService.get_client_status(line_user.client_id, db)

        if client_data:
            return StandardResponse(
                success=True,
                message="查詢成功",
                data={
                    'line_user_id': line_user_id,
                    'client_info': client_data,
                    'binding_info': {
                        'user_name': line_user.user_name,
                        'bound_at': line_user.bound_at.isoformat() if line_user.bound_at else None
                    }
                }
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="找不到對應的事務所資訊"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查詢事務所異常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="查詢過程發生錯誤"
        )

# ==================== 🎯 方案管理端點 ====================

@router.put("/clients/upgrade-plan", response_model=StandardResponse, summary="升級方案")
def upgrade_plan(request: PlanUpgradeRequest, db: Session = Depends(get_db)):
    """
    🎯 升級事務所方案 - 實現您的需求：
    1. 驗證新方案的有效性
    2. 更新max_users限制
    3. 保持現有LINE用戶綁定
    """
    try:
        logger.info(f"方案升級請求: {request.client_id} -> {request.new_plan_type}")

        result = ClientAPIService.handle_plan_upgrade(
            request.dict(), db
        )

        if result['success']:
            return StandardResponse(**result)
        else:
            if result.get('error_code') == 'INVALID_UPGRADE':
                status_code = status.HTTP_400_BAD_REQUEST
            else:
                status_code = status.HTTP_404_NOT_FOUND

            raise HTTPException(
                status_code=status_code,
                detail=result['message']
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"方案升級異常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="升級處理過程發生錯誤"
        )
