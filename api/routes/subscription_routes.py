# api/routes/subscription_routes.py
"""
方案管理路由控制層
處理付費用戶註冊、方案升級、用戶審核等功能
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from api.database import get_control_db
from api.services.subscription_service import SubscriptionService
from api.models_control import PlanType, UserStatus

router = APIRouter()

# 初始化方案管理服務
subscription_service = SubscriptionService()

# Pydantic 模型定義
class RegisterPendingUserRequest(BaseModel):
    """註冊未付費用戶請求"""
    user_id: str = Field(..., description="LINE 用戶ID")
    client_id: str = Field(..., description="租戶ID")
    client_name: str = Field(..., description="事務所名稱")
    user_name: Optional[str] = Field(None, description="用戶姓名")
    email: Optional[str] = Field(None, description="用戶信箱")
    phone: Optional[str] = Field(None, description="聯絡電話")

class UpgradePlanRequest(BaseModel):
    """方案升級請求"""
    client_id: str = Field(..., description="租戶ID")
    new_plan_type: PlanType = Field(..., description="新方案類型")
    changed_by: Optional[str] = Field(None, description="變更者")
    reason: Optional[str] = Field(None, description="變更原因")

class ApproveUserRequest(BaseModel):
    """審核用戶請求"""
    user_id: str = Field(..., description="LINE 用戶ID")
    approved_by: str = Field(..., description="審核者")
    notes: Optional[str] = Field(None, description="審核備註")

class RemoveUserRequest(BaseModel):
    """移除用戶請求"""
    user_id: str = Field(..., description="LINE 用戶ID")
    reason: Optional[str] = Field(None, description="移除原因")

# API 端點定義

@router.post("/check-paid-user")
def check_paid_user_for_webhook(
    user_id: str,
    db: Session = Depends(get_control_db)
):
    """
    檢查用戶是否為付費用戶（供 N8N Webhook 使用）

    Args:
        user_id: LINE 用戶ID
        db: 資料庫會話

    Returns:
        Dict: 檢查結果，包含是否為付費用戶
    """
    try:
        is_paid = subscription_service.check_user_is_paid(user_id, db)

        return {
            "user_id": user_id,
            "is_paid_user": is_paid,
            "should_process": is_paid,  # N8N 可以直接使用這個欄位判斷
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"檢查付費用戶失敗: {str(e)}"
        )

@router.post("/register-pending")
def register_pending_user(
    request: RegisterPendingUserRequest,
    db: Session = Depends(get_control_db)
):
    """
    註冊未付費用戶（註冊系統使用）

    Args:
        request: 註冊請求
        db: 資料庫會話

    Returns:
        Dict: 註冊結果
    """
    try:
        result = subscription_service.register_pending_user(
            user_id=request.user_id,
            client_id=request.client_id,
            client_name=request.client_name,
            user_name=request.user_name,
            email=request.email,
            phone=request.phone,
            db=db
        )

        if result["success"]:
            return {
                "success": True,
                "message": result["message"],
                "user_id": request.user_id,
                "status": result["user_status"],
                "next_steps": "請等待管理員審核或方案升級後自動啟用"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["message"]
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"註冊失敗: {str(e)}"
        )

@router.get("/plan-status/{client_id}")
def get_plan_status(
    client_id: str,
    db: Session = Depends(get_control_db)
):
    """
    取得租戶方案狀態

    Args:
        client_id: 租戶ID
        db: 資料庫會話

    Returns:
        Dict: 方案狀態詳細資訊
    """
    try:
        result = subscription_service.get_tenant_plan_status(client_id, db)

        if result["success"]:
            return result
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result["message"]
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查詢方案狀態失敗: {str(e)}"
        )

@router.post("/upgrade-plan")
def upgrade_plan(
    request: UpgradePlanRequest,
    db: Session = Depends(get_control_db)
):
    """
    升級方案（自動遷移未付費用戶）

    Args:
        request: 升級請求
        db: 資料庫會話

    Returns:
        Dict: 升級結果
    """
    try:
        result = subscription_service.upgrade_plan(
            client_id=request.client_id,
            new_plan_type=request.new_plan_type,
            changed_by=request.changed_by,
            reason=request.reason,
            db=db
        )

        if result["success"]:
            return result
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["message"]
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"方案升級失敗: {str(e)}"
        )

@router.post("/approve-user")
def approve_user(
    request: ApproveUserRequest,
    db: Session = Depends(get_control_db)
):
    """
    手動審核並啟用未付費用戶

    Args:
        request: 審核請求
        db: 資料庫會話

    Returns:
        Dict: 審核結果
    """
    try:
        result = subscription_service.manually_approve_user(
            user_id=request.user_id,
            approved_by=request.approved_by,
            notes=request.notes,
            db=db
        )

        if result["success"]:
            return result
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["message"]
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"用戶審核失敗: {str(e)}"
        )

@router.get("/pending-users/{client_id}")
def get_pending_users(
    client_id: str,
    db: Session = Depends(get_control_db)
):
    """
    取得租戶的待審核用戶列表

    Args:
        client_id: 租戶ID
        db: 資料庫會話

    Returns:
        List: 待審核用戶列表
    """
    try:
        pending_users = subscription_service.get_pending_users_by_tenant(client_id, db)

        return {
            "client_id": client_id,
            "pending_count": len(pending_users),
            "pending_users": pending_users
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"取得待審核用戶失敗: {str(e)}"
        )

@router.get("/all-users/{client_id}")
def get_all_users(
    client_id: str,
    db: Session = Depends(get_control_db)
):
    """
    取得租戶的所有用戶狀態

    Args:
        client_id: 租戶ID
        db: 資料庫會話

    Returns:
        Dict: 完整的用戶管理資訊
    """
    try:
        result = subscription_service.get_all_users_by_tenant(client_id, db)

        if result["success"]:
            return result
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result["message"]
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"取得用戶資訊失敗: {str(e)}"
        )

@router.post("/remove-user")
def remove_user(
    request: RemoveUserRequest,
    db: Session = Depends(get_control_db)
):
    """
    從方案中移除用戶

    Args:
        request: 移除請求
        db: 資料庫會話

    Returns:
        Dict: 移除結果
    """
    try:
        result = subscription_service.remove_user_from_plan(
            user_id=request.user_id,
            reason=request.reason,
            db=db
        )

        if result["success"]:
            return result
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["message"]
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"移除用戶失敗: {str(e)}"
        )

@router.get("/plan-history/{client_id}")
def get_plan_history(
    client_id: str,
    limit: int = 10,
    db: Session = Depends(get_control_db)
):
    """
    取得方案變更歷史

    Args:
        client_id: 租戶ID
        limit: 返回記錄數限制
        db: 資料庫會話

    Returns:
        List: 方案變更歷史
    """
    try:
        from api.models_control import PlanChangeHistory

        history = db.query(PlanChangeHistory).filter(
            PlanChangeHistory.client_id == client_id
        ).order_by(PlanChangeHistory.created_at.desc()).limit(limit).all()

        result = []
        for record in history:
            result.append({
                "id": record.id,
                "old_plan": record.old_plan_type.value if record.old_plan_type else None,
                "new_plan": record.new_plan_type.value,
                "old_limit": record.old_limit,
                "new_limit": record.new_limit,
                "changed_by": record.changed_by,
                "change_reason": record.change_reason,
                "users_migrated": record.users_migrated,
                "changed_at": record.created_at.isoformat()
            })

        return {
            "client_id": client_id,
            "history_count": len(result),
            "history": result
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"取得方案歷史失敗: {str(e)}"
        )