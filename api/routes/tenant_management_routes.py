#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
事務所管理控制層 - API 路由
處理所有事務所相關的 HTTP 請求
與現有 login_routes.py 保持一致的風格
"""

from fastapi import APIRouter, Depends, HTTPException, status, Path, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from api.database import get_control_db
from api.services.tenant_business_service import TenantBusinessService
from datetime import datetime

router = APIRouter()

# 初始化業務邏輯服務
tenant_service = TenantBusinessService()

# ===== Pydantic 模型定義（與現有風格一致）=====

class TenantLoginRequest(BaseModel):
    """事務所登入請求"""
    account: str = Field(..., description="帳號")
    password: str = Field(..., description="密碼")

class QRGenerateRequest(BaseModel):
    """QR Code 生成請求"""
    client_id: str = Field(..., description="事務所代碼")

class UserBindRequest(BaseModel):
    """用戶綁定請求"""
    user_id: str = Field(..., description="LINE 用戶 ID")
    binding_code: str = Field(..., description="綁定代碼")

class LoginResponse(BaseModel):
    """登入回應（與現有 LoginResponse 保持一致）"""
    success: bool
    message: str
    user_data: Optional[dict] = None
    login_type: Optional[str] = None

# ===== API 端點定義 =====

@router.post("/login", response_model=LoginResponse)
def tenant_admin_login(
    request: TenantLoginRequest,
    db: Session = Depends(get_control_db)
):
    """
    事務所管理員登入

    根據您的流程圖：帳號密碼 → 驗證 TenantInfo → 顯示事務所資訊
    """
    try:
        user_data = tenant_service.authenticate_tenant(
            request.account,
            request.password,
            db
        )

        if user_data:
            return LoginResponse(
                success=True,
                message=f"✅ 事務所管理員登入成功，歡迎 {user_data['client_name']}",
                user_data=user_data,
                login_type="tenant_admin"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="帳號或密碼錯誤"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"登入過程發生錯誤: {str(e)}"
        )

@router.post("/generate-qr")
def generate_binding_qr_code(
    request: QRGenerateRequest,
    db: Session = Depends(get_control_db)
):
    """
    生成用戶綁定 QR Code

    根據您的流程圖：事務所生成 QR Code → 用戶掃描綁定
    """
    try:
        result = tenant_service.generate_qr_code_for_binding(request.client_id, db)

        if result and 'error' not in result:
            return {
                "success": True,
                "message": "QR Code 生成成功",
                "qr_info": result,
                "timestamp": datetime.now().isoformat()
            }
        elif result and 'error' in result:
            if result['error'] == 'PLAN_LIMIT_EXCEEDED':
                raise HTTPException(status_code=400, detail=result['message'])
            else:
                raise HTTPException(status_code=404, detail="找不到對應的事務所")
        else:
            raise HTTPException(status_code=404, detail="找不到對應的事務所")

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 生成 QR Code API 錯誤: {e}")
        raise HTTPException(status_code=500, detail="系統錯誤")

@router.post("/bind-user", response_model=LoginResponse)
def bind_line_user_to_tenant(
    request: UserBindRequest,
    db: Session = Depends(get_control_db)
):
    """
    LINE BOT 呼叫：綁定 LINE 用戶到事務所

    根據您的流程圖：用戶掃描 QR Code → 驗證綁定代碼 → 新增到 TenantUser
    """
    try:
        result = tenant_service.bind_user_with_code(
            request.user_id,
            request.binding_code,
            db
        )

        if result and 'error' not in result:
            return LoginResponse(
                success=True,
                message=f"✅ 成功綁定到事務所：{result['client_name']}",
                user_data=result,
                login_type="tenant_binding"
            )
        elif result and 'error' in result:
            error_messages = {
                'INVALID_QR_CODE': 'QR Code 無效或已過期',
                'QR_CODE_EXPIRED': 'QR Code 已過期，請重新生成',
                'QR_CODE_USED': 'QR Code 已被使用',
                'USER_ALREADY_BOUND': result['message'],
                'PLAN_LIMIT_EXCEEDED': result['message']
            }

            status_code = 409 if result['error'] == 'USER_ALREADY_BOUND' else 400
            raise HTTPException(
                status_code=status_code,
                detail=error_messages.get(result['error'], result['message'])
            )
        else:
            raise HTTPException(status_code=400, detail="綁定失敗")

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 用戶綁定 API 錯誤: {e}")
        raise HTTPException(status_code=500, detail="系統錯誤")

@router.get("/bound-count/{client_id}")
def get_bound_users_count(
    client_id: str = Path(..., description="事務所代碼"),
    db: Session = Depends(get_control_db)
):
    """
    查詢已綁定人數

    根據您的 API 規格：GET /bound-count?client_id=xxx → 顯示已綁定人數
    """
    try:
        result = tenant_service.get_bound_users_count(client_id, db)

        if result:
            return {
                "success": True,
                "message": "查詢成功",
                "client_id": result['client_id'],
                "client_name": result['client_name'],
                "bound_users": result['bound_users'],
                "plan_limit": result['plan_limit'],
                "remaining_slots": result['remaining_slots'],
                "usage_percentage": result['usage_percentage'],
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=404, detail="找不到對應的事務所")

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 查詢綁定人數 API 錯誤: {e}")
        raise HTTPException(status_code=500, detail="系統錯誤")

@router.get("/user-limit/{client_id}")
def get_user_limit(
    client_id: str = Path(..., description="事務所代碼"),
    db: Session = Depends(get_control_db)
):
    """
    查詢方案上限

    根據您的 API 規格：GET /user-limit?client_id=xxx → 顯示方案上限
    """
    try:
        result = tenant_service.get_user_limit(client_id, db)

        if result:
            return {
                "success": True,
                "message": "查詢成功",
                "client_id": result['client_id'],
                "client_name": result['client_name'],
                "user_limit": result['user_limit'],
                "plan_type": result['plan_type'],
                "is_active": result['is_active'],
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=404, detail="找不到對應的事務所")

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 查詢方案上限 API 錯誤: {e}")
        raise HTTPException(status_code=500, detail="系統錯誤")

@router.get("/tenant-by-line-user/{user_id}")
def get_tenant_by_line_user_id(
    user_id: str = Path(..., description="LINE 用戶 ID"),
    db: Session = Depends(get_control_db)
):
    """
    事務所查詢 user_id 對應資料

    根據您的 API 規格：GET /tenant-by-line-user/{user_id} → 查詢用戶所屬事務所
    與現有的 tenant_routes.py 保持一致
    """
    try:
        result = tenant_service.authenticate_by_tenant_user_id(user_id, db)

        if result:
            return {
                "success": True,
                "message": "查詢成功",
                "user_id": result['user_id'],
                "client_id": result['client_id'],
                "client_name": result['client_name'],
                "status": result['status'],
                "login_type": result['login_type'],
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=404, detail="找不到對應的用戶綁定記錄")

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 查詢用戶資料 API 錯誤: {e}")
        raise HTTPException(status_code=500, detail="系統錯誤")

@router.get("/all-tenant-users")
def get_all_tenant_users(db: Session = Depends(get_control_db)):
    """
    所有綁定使用者

    根據您的 API 規格：GET /all-tenant-users → 管理員查看所有綁定用戶
    與現有的 tenant_routes.py 保持一致
    """
    try:
        users = tenant_service.get_all_tenant_users(db)

        return {
            "success": True,
            "message": "查詢成功",
            "total_count": len(users),
            "users": users,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        print(f"❌ 查詢所有用戶 API 錯誤: {e}")
        raise HTTPException(status_code=500, detail="系統錯誤")

# ===== LINE BOT Webhook 專用端點（與您的流程圖匹配）=====

@router.get("/bind-user")
def handle_qr_code_scan_for_line_bot(
    code: str = Query(..., description="綁定代碼"),
    db: Session = Depends(get_control_db)
):
    """
    處理 QR Code 掃描（LINE BOT Webhook 專用）

    當用戶在 LINE 中掃描 QR Code 時，BOT 會先呼叫此端點取得綁定資訊
    然後再呼叫 /bind-user POST 端點完成實際綁定
    """
    try:
        # 檢查綁定代碼是否有效
        if code not in tenant_service.qr_cache:
            raise HTTPException(status_code=404, detail="QR Code 無效或已過期")

        binding_info = tenant_service.qr_cache[code]

        # 檢查是否過期
        if datetime.now() > binding_info['expiry_time']:
            del tenant_service.qr_cache[code]
            raise HTTPException(status_code=410, detail="QR Code 已過期")

        # 檢查是否已使用
        if binding_info['used']:
            raise HTTPException(status_code=409, detail="QR Code 已被使用")

        return {
            "success": True,
            "message": f"準備綁定到事務所：{binding_info['client_name']}",
            "binding_data": {
                "client_id": binding_info['client_id'],
                "client_name": binding_info['client_name'],
                "binding_code": code
            },
            "timestamp": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 處理 QR Code 掃描錯誤: {e}")
        raise HTTPException(status_code=500, detail="系統錯誤")

# ===== 系統維護端點 =====

@router.post("/cleanup-expired-qr")
def cleanup_expired_qr_codes():
    """
    清理過期的 QR Code（系統維護用）

    建議定期呼叫此端點清理過期的 QR Code
    """
    try:
        cleaned_count = tenant_service.cleanup_expired_qr_codes()

        return {
            "success": True,
            "message": f"已清理 {cleaned_count} 個過期的 QR Code",
            "cleaned_count": cleaned_count,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        print(f"❌ 清理過期 QR Code 錯誤: {e}")
        raise HTTPException(status_code=500, detail="系統錯誤")