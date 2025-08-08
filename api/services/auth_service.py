# api/services/auth_service.py

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime

# 使用新的資料庫模型
try:
    from api.models_control import LoginUser, ClientLineUsers
except ImportError:
    from models_control import LoginUser, ClientLineUsers

class AuthService:
    """認證服務類別 - 適配新資料庫結構"""

    def authenticate_by_line_user_id(self, user_id: str, db: Session) -> Optional[Dict[str, Any]]:
        """使用LINE用戶ID進行認證"""
        try:
            # 查詢LINE用戶綁定記錄
            line_user = db.query(ClientLineUsers).filter(
                ClientLineUsers.line_user_id == user_id,
                ClientLineUsers.is_active == True
            ).first()

            if not line_user:
                return None

            # 取得對應的事務所資訊
            client = db.query(LoginUser).filter(
                LoginUser.client_id == line_user.client_id,
                LoginUser.is_active == True
            ).first()

            if not client:
                return None

            # 更新最後登入時間
            client.last_login = datetime.now()
            db.commit()

            return {
                "user_id": line_user.line_user_id,
                "client_id": client.client_id,
                "client_name": client.client_name,
                "user_name": line_user.user_name,
                "plan_type": client.plan_type,
                "login_type": "line_user_id"
            }

        except Exception as e:
            print(f"❌ LINE 用戶認證失敗: {e}")
            return None

    def authenticate_by_client_credentials(self, client_id: str, password: str, db: Session) -> Optional[Dict[str, Any]]:
        """使用事務所憑證進行認證"""
        try:
            client = db.query(LoginUser).filter(
                LoginUser.client_id == client_id,
                LoginUser.password == password,
                LoginUser.is_active == True
            ).first()

            if not client:
                return None

            # 更新最後登入時間
            client.last_login = datetime.now()
            db.commit()

            return {
                "client_id": client.client_id,
                "client_name": client.client_name,
                "plan_type": client.plan_type,
                "user_status": client.user_status,
                "current_users": client.current_users,
                "max_users": client.max_users,
                "login_type": "client_credentials"
            }

        except Exception as e:
            print(f"❌ 客戶端憑證認證失敗: {e}")
            return None

    def check_user_plan_status(self, line_user_id: str, db: Session) -> Optional[Dict[str, Any]]:
        """檢查LINE用戶的方案狀態"""
        try:
            # 查詢用戶綁定資訊
            line_user = db.query(ClientLineUsers).filter(
                ClientLineUsers.line_user_id == line_user_id,
                ClientLineUsers.is_active == True
            ).first()

            if not line_user:
                return None

            # 取得事務所資訊
            client = db.query(LoginUser).filter(
                LoginUser.client_id == line_user.client_id
            ).first()

            if not client:
                return None

            # 計算實際用戶數
            actual_users = db.query(ClientLineUsers).filter(
                ClientLineUsers.client_id == client.client_id,
                ClientLineUsers.is_active == True
            ).count()

            # 更新實際用戶數
            client.current_users = actual_users
            db.commit()

            return {
                "line_user_id": line_user_id,
                "client_name": client.client_name,
                "plan_type": client.plan_type,
                "user_status": client.user_status,
                "current_users": actual_users,
                "max_users": client.max_users,
                "usage_percentage": round((actual_users / client.max_users) * 100, 1),
                "is_plan_active": client.user_status == "active"
            }

        except Exception as e:
            print(f"❌ 檢查用戶方案狀態失敗: {e}")
            return None

    def get_client_line_users(self, client_id: str, db: Session) -> List[Dict[str, Any]]:
        """取得事務所的所有LINE用戶"""
        try:
            line_users = db.query(ClientLineUsers).filter(
                ClientLineUsers.client_id == client_id,
                ClientLineUsers.is_active == True
            ).all()

            return [
                {
                    "line_user_id": user.line_user_id,
                    "user_name": user.user_name,
                    "bound_at": user.bound_at.isoformat()
                }
                for user in line_users
            ]

        except Exception as e:
            print(f"❌ 取得事務所LINE用戶失敗: {e}")
            return []
