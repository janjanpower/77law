# api/routes/tenant_routes.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any

# 使用新的資料庫模型
try:
    from api.database import get_db
    from api.models_control import LoginUser, ClientLineUsers
except ImportError:
    from database import get_db
    from models_control import LoginUser, ClientLineUsers

router = APIRouter()

@router.get("/tenant-by-line-user/{user_id}")
def get_tenant_by_user(user_id: str, db: Session = Depends(get_db)):
    """根據LINE用戶ID取得所屬事務所資訊"""
    try:
        # 查詢LINE用戶綁定記錄
        line_user = db.query(ClientLineUsers).filter(
            ClientLineUsers.line_user_id == user_id,
            ClientLineUsers.is_active == True
        ).first()

        if not line_user:
            raise HTTPException(status_code=404, detail="找不到此LINE用戶的綁定記錄")

        # 取得對應的事務所資訊
        client = db.query(LoginUser).filter(
            LoginUser.client_id == line_user.client_id
        ).first()

        if not client:
            raise HTTPException(status_code=404, detail="找不到對應的事務所")

        return {
            "user_id": line_user.line_user_id,
            "client_id": client.client_id,
            "client_name": client.client_name,
            "user_name": line_user.user_name,
            "plan_type": client.plan_type,
            "bound_at": line_user.bound_at.isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查詢失敗: {str(e)}")

@router.get("/all-tenant-users")
def get_all_tenant_users(db: Session = Depends(get_db)):
    """取得所有LINE用戶綁定記錄"""
    try:
        # 聯合查詢取得完整資訊
        results = db.query(
            ClientLineUsers.line_user_id,
            ClientLineUsers.user_name,
            ClientLineUsers.bound_at,
            ClientLineUsers.is_active,
            LoginUser.client_id,
            LoginUser.client_name,
            LoginUser.plan_type
        ).join(
            LoginUser, ClientLineUsers.client_id == LoginUser.client_id
        ).all()

        return [
            {
                "line_user_id": result.line_user_id,
                "user_name": result.user_name,
                "client_id": result.client_id,
                "client_name": result.client_name,
                "plan_type": result.plan_type,
                "is_active": result.is_active,
                "bound_at": result.bound_at.isoformat()
            }
            for result in results
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查詢失敗: {str(e)}")

@router.get("/client-users/{client_id}")
def get_client_users(client_id: str, db: Session = Depends(get_db)):
    """取得指定事務所的所有LINE用戶"""
    try:
        # 檢查事務所是否存在
        client = db.query(LoginUser).filter(LoginUser.client_id == client_id).first()
        if not client:
            raise HTTPException(status_code=404, detail="事務所不存在")

        # 取得該事務所的所有LINE用戶
        line_users = db.query(ClientLineUsers).filter(
            ClientLineUsers.client_id == client_id,
            ClientLineUsers.is_active == True
        ).all()

        return {
            "client_info": {
                "client_id": client.client_id,
                "client_name": client.client_name,
                "plan_type": client.plan_type,
                "max_users": client.max_users,
                "current_users": len(line_users)
            },
            "line_users": [
                {
                    "line_user_id": user.line_user_id,
                    "user_name": user.user_name,
                    "bound_at": user.bound_at.isoformat()
                }
                for user in line_users
            ]
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查詢失敗: {str(e)}")

@router.post("/update-plan/{client_id}")
def update_client_plan(
    client_id: str,
    new_plan: str,
    db: Session = Depends(get_db)
):
    """更新事務所方案"""
    try:
        client = db.query(LoginUser).filter(LoginUser.client_id == client_id).first()
        if not client:
            raise HTTPException(status_code=404, detail="事務所不存在")

        # 方案限制對應
        plan_limits = {
            "basic_5": 5,
            "standard_10": 10,
            "premium_20": 20,
            "enterprise_50": 50
        }

        if new_plan not in plan_limits:
            raise HTTPException(
                status_code=400,
                detail=f"無效的方案類型，支援: {list(plan_limits.keys())}"
            )

        old_plan = client.plan_type
        old_max = client.max_users

        # 更新方案
        client.plan_type = new_plan
        client.max_users = plan_limits[new_plan]

        db.commit()

        return {
            "success": True,
            "message": f"方案已從 {old_plan} 更新為 {new_plan}",
            "old_max_users": old_max,
            "new_max_users": client.max_users,
            "current_users": client.current_users
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"更新失敗: {str(e)}")