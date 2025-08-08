# api/routes/webhook_filter.py
"""
N8N Webhook 過濾端點
專門用於檢查 LINE Bot 用戶是否為付費用戶
"""

import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Dict, Any, List
from api.database import get_control_db
from api.services.subscription_service import SubscriptionService

router = APIRouter()

# 初始化方案管理服務
subscription_service = SubscriptionService()

class N8NWebhookRequest(BaseModel):
    """N8N Webhook 請求格式"""
    user_id: str = Field(..., description="LINE 用戶ID")
    message: str = Field(..., description="用戶訊息")
    timestamp: str = Field(..., description="訊息時間戳")
    message_type: str = Field(default="text", description="訊息類型")

class N8NWebhookResponse(BaseModel):
    """N8N Webhook 回應格式"""
    should_process: bool = Field(..., description="是否應該處理此訊息")
    user_id: str = Field(..., description="用戶ID")
    is_paid_user: bool = Field(..., description="是否為付費用戶")
    client_info: Dict[str, Any] = Field(default_factory=dict, description="客戶資訊")
    message: str = Field(..., description="處理訊息")
    timestamp: str = Field(..., description="檢查時間戳")

@router.post("/webhook/filter", response_model=N8NWebhookResponse)
def filter_webhook_for_paid_users(
    request: N8NWebhookRequest,
    db: Session = Depends(get_control_db)
):
    """
    N8N Webhook 過濾端點：只有付費用戶的訊息才會被處理

    在您的 N8N 工作流中，將此端點放在 LINEBOT WEBHOOK 之後，
    只有當 should_process = true 時才繼續執行後續節點

    Args:
        request: N8N Webhook 請求
        db: 資料庫會話

    Returns:
        N8NWebhookResponse: 過濾結果
    """
    try:
        # 檢查是否為付費用戶
        is_paid = subscription_service.check_user_is_paid(request.user_id, db)

        client_info = {}
        if is_paid:
            # 如果是付費用戶，取得客戶資訊
            from api.models_control import TenantUser
            tenant_user = db.query(TenantUser).filter(
                TenantUser.user_id == request.user_id
            ).first()

            if tenant_user:
                client_info = {
                    "client_id": tenant_user.client_id,
                    "client_name": tenant_user.client_name,
                    "user_status": tenant_user.status.value
                }

                # 更新最後登入時間
                tenant_user.last_login = datetime.now()
                db.commit()

        return N8NWebhookResponse(
            should_process=is_paid,
            user_id=request.user_id,
            is_paid_user=is_paid,
            client_info=client_info,
            message="✅ 付費用戶，繼續處理" if is_paid else "❌ 非付費用戶，停止處理",
            timestamp=datetime.now().isoformat()
        )

    except Exception as e:
        # 發生錯誤時，為了安全起見，不處理訊息
        return N8NWebhookResponse(
            should_process=False,
            user_id=request.user_id,
            is_paid_user=False,
            client_info={},
            message=f"系統錯誤，停止處理: {str(e)}",
            timestamp=datetime.now().isoformat()
        )

@router.get("/webhook/user-status/{user_id}")
def get_user_webhook_status(
    user_id: str,
    db: Session = Depends(get_control_db)
):
    """
    取得用戶的 Webhook 處理狀態（用於除錯）

    Args:
        user_id: LINE 用戶ID
        db: 資料庫會話

    Returns:
        Dict: 用戶狀態詳情
    """
    try:
        # 檢查付費用戶狀態
        from api.models_control import TenantUser, PendingUser

        paid_user = db.query(TenantUser).filter(TenantUser.user_id == user_id).first()
        pending_user = db.query(PendingUser).filter(PendingUser.user_id == user_id).first()

        if paid_user:
            return {
                "user_id": user_id,
                "status": "paid_user",
                "should_process_webhook": True,
                "client_id": paid_user.client_id,
                "client_name": paid_user.client_name,
                "activated_at": paid_user.activated_at.isoformat() if paid_user.activated_at else None,
                "last_login": paid_user.last_login.isoformat() if paid_user.last_login else None
            }
        elif pending_user:
            return {
                "user_id": user_id,
                "status": "pending_user",
                "should_process_webhook": False,
                "client_id": pending_user.client_id,
                "client_name": pending_user.client_name,
                "requested_at": pending_user.requested_at.isoformat(),
                "message": "等待審核或方案升級"
            }
        else:
            return {
                "user_id": user_id,
                "status": "unknown_user",
                "should_process_webhook": False,
                "message": "用戶未註冊，請先註冊"
            }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"取得用戶狀態失敗: {str(e)}"
        )

@router.post("/webhook/batch-check")
def batch_check_paid_users(
    user_ids: List[str],
    db: Session = Depends(get_control_db)
):
    """
    批量檢查多個用戶的付費狀態

    Args:
        user_ids: LINE 用戶ID 列表
        db: 資料庫會話

    Returns:
        Dict: 批量檢查結果
    """
    try:
        results = {}
        paid_count = 0

        for user_id in user_ids:
            is_paid = subscription_service.check_user_is_paid(user_id, db)
            results[user_id] = {
                "is_paid_user": is_paid,
                "should_process": is_paid
            }
            if is_paid:
                paid_count += 1

        return {
            "total_users": len(user_ids),
            "paid_users": paid_count,
            "unpaid_users": len(user_ids) - paid_count,
            "results": results,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"批量檢查失敗: {str(e)}"
        )