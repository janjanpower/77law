#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
事務所管理業務邏輯層
處理事務所登入、用戶綁定、數據查詢等核心業務邏輯
與現有 auth_service.py 保持一致的風格
"""

from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from api.models_control import TenantUser, Tenant
import uuid
import qrcode
import io
import base64
from datetime import datetime, timedelta


class TenantBusinessService:
    """事務所業務邏輯服務類別 - 邏輯層"""

    def __init__(self):
        """初始化服務"""
        self.qr_cache = {}  # QR Code 快取，生產環境建議使用 Redis

    def authenticate_tenant(self, account: str, password: str, db: Session) -> Optional[Dict[str, Any]]:
        """
        事務所登入驗證

        Args:
            account (str): 帳號（client_id）
            password (str): 密碼
            db (Session): 資料庫會話

        Returns:
            Optional[Dict]: 認證成功返回事務所資訊，失敗返回 None
        """
        try:
            # 查詢事務所（使用現有的 Tenant 表，假設有 password 欄位）
            tenant = db.query(Tenant).filter(Tenant.schema_name == account).first()

            if not tenant:
                return None

            # 簡單密碼驗證（實際應該使用加密比對）
            # 如果 Tenant 表沒有 password 欄位，需要先新增
            if not hasattr(tenant, 'password'):
                # 暫時允許任何密碼（開發階段）
                print(f"⚠️ 警告：Tenant 表缺少 password 欄位，暫時跳過密碼驗證")
            elif tenant.password != password:
                return None

            # 計算綁定用戶數
            bound_users_count = db.query(TenantUser).filter(
                TenantUser.client_id == tenant.schema_name
            ).count()

            return {
                "client_id": tenant.schema_name,
                "client_name": tenant.name,
                "user_limit": tenant.plan_limit,
                "bound_users_count": bound_users_count,
                "remaining_slots": max(0, tenant.plan_limit - bound_users_count),
                "usage_percentage": round((bound_users_count / tenant.plan_limit) * 100, 1) if tenant.plan_limit > 0 else 0,
                "login_type": "tenant_admin"
            }

        except Exception as e:
            print(f"❌ 事務所登入驗證失敗: {e}")
            return None

    def generate_qr_code_for_binding(self, client_id: str, db: Session) -> Optional[Dict[str, Any]]:
        """
        為事務所生成綁定用的 QR Code

        Args:
            client_id (str): 事務所代碼
            db (Session): 資料庫會話

        Returns:
            Optional[Dict]: 成功返回 QR Code 資訊，失敗返回 None
        """
        try:
            # 驗證事務所是否存在
            tenant = db.query(Tenant).filter(Tenant.schema_name == client_id).first()
            if not tenant:
                return None

            # 檢查是否還有可綁定名額
            current_users = db.query(TenantUser).filter(
                TenantUser.client_id == client_id
            ).count()

            if current_users >= tenant.plan_limit:
                return {
                    "error": "PLAN_LIMIT_EXCEEDED",
                    "message": f"已達到方案上限（{current_users}/{tenant.plan_limit}）"
                }

            # 生成唯一綁定代碼
            binding_code = str(uuid.uuid4())
            expiry_time = datetime.now() + timedelta(minutes=10)

            # 存入快取
            self.qr_cache[binding_code] = {
                'client_id': client_id,
                'client_name': tenant.name,
                'expiry_time': expiry_time,
                'used': False
            }

            # 生成 QR Code URL
            qr_data = f"https://law-controller.herokuapp.com/api/tenant-management/bind-user?code={binding_code}"

            # 生成 QR Code 圖片
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(qr_data)
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white")
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            img_base64 = base64.b64encode(buffer.getvalue()).decode()

            return {
                'binding_code': binding_code,
                'qr_data': qr_data,
                'qr_image_base64': f"data:image/png;base64,{img_base64}",
                'expiry_time': expiry_time.isoformat(),
                'remaining_slots': tenant.plan_limit - current_users,
                'client_name': tenant.name
            }

        except Exception as e:
            print(f"❌ 生成 QR Code 失敗: {e}")
            return None

    def bind_user_with_code(self, user_id: str, binding_code: str, db: Session) -> Optional[Dict[str, Any]]:
        """
        使用綁定代碼將 LINE 用戶與事務所綁定

        Args:
            user_id (str): LINE 用戶 ID
            binding_code (str): 綁定代碼
            db (Session): 資料庫會話

        Returns:
            Optional[Dict]: 綁定結果
        """
        try:
            # 檢查綁定代碼
            if binding_code not in self.qr_cache:
                return {"error": "INVALID_QR_CODE", "message": "QR Code 無效或已過期"}

            binding_info = self.qr_cache[binding_code]

            # 檢查過期
            if datetime.now() > binding_info['expiry_time']:
                del self.qr_cache[binding_code]
                return {"error": "QR_CODE_EXPIRED", "message": "QR Code 已過期"}

            # 檢查是否已使用
            if binding_info['used']:
                return {"error": "QR_CODE_USED", "message": "QR Code 已被使用"}

            client_id = binding_info['client_id']
            client_name = binding_info['client_name']

            # 檢查用戶是否已綁定
            existing_user = db.query(TenantUser).filter(TenantUser.user_id == user_id).first()
            if existing_user:
                return {
                    "error": "USER_ALREADY_BOUND",
                    "message": f"此用戶已綁定到事務所：{existing_user.client_name}"
                }

            # 再次檢查名額
            tenant = db.query(Tenant).filter(Tenant.schema_name == client_id).first()
            current_users = db.query(TenantUser).filter(TenantUser.client_id == client_id).count()

            if current_users >= tenant.plan_limit:
                return {
                    "error": "PLAN_LIMIT_EXCEEDED",
                    "message": f"事務所已達到方案上限（{current_users}/{tenant.plan_limit}）"
                }

            # 創建綁定記錄
            new_tenant_user = TenantUser(
                user_id=user_id,
                client_id=client_id,
                client_name=client_name,
                status="active",
                activated_at=datetime.now()
            )

            db.add(new_tenant_user)
            db.commit()

            # 標記為已使用
            binding_info['used'] = True

            return {
                'user_id': user_id,
                'client_id': client_id,
                'client_name': client_name,
                'binding_time': datetime.now().isoformat(),
                'login_type': 'tenant_binding'
            }

        except Exception as e:
            db.rollback()
            print(f"❌ 用戶綁定失敗: {e}")
            return None

    def get_bound_users_count(self, client_id: str, db: Session) -> Optional[Dict[str, Any]]:
        """
        查詢已綁定人數

        Args:
            client_id (str): 事務所代碼
            db (Session): 資料庫會話

        Returns:
            Optional[Dict]: 綁定人數資訊
        """
        try:
            tenant = db.query(Tenant).filter(Tenant.schema_name == client_id).first()
            if not tenant:
                return None

            bound_count = db.query(TenantUser).filter(TenantUser.client_id == client_id).count()

            return {
                'client_id': client_id,
                'client_name': tenant.name,
                'bound_users': bound_count,
                'plan_limit': tenant.plan_limit,
                'remaining_slots': max(0, tenant.plan_limit - bound_count),
                'usage_percentage': round((bound_count / tenant.plan_limit) * 100, 1) if tenant.plan_limit > 0 else 0
            }

        except Exception as e:
            print(f"❌ 查詢綁定人數失敗: {e}")
            return None

    def get_user_limit(self, client_id: str, db: Session) -> Optional[Dict[str, Any]]:
        """
        查詢方案上限

        Args:
            client_id (str): 事務所代碼
            db (Session): 資料庫會話

        Returns:
            Optional[Dict]: 方案上限資訊
        """
        try:
            tenant = db.query(Tenant).filter(Tenant.schema_name == client_id).first()
            if not tenant:
                return None

            return {
                'client_id': client_id,
                'client_name': tenant.name,
                'user_limit': tenant.plan_limit,
                'plan_type': getattr(tenant, 'plan_type', 'unknown'),
                'is_active': getattr(tenant, 'is_active', True)
            }

        except Exception as e:
            print(f"❌ 查詢方案上限失敗: {e}")
            return None

    def authenticate_by_tenant_user_id(self, user_id: str, db: Session) -> Optional[Dict[str, Any]]:
        """
        通過 user_id 查詢事務所用戶資訊（與現有 auth_service 風格一致）

        Args:
            user_id (str): LINE 用戶 ID
            db (Session): 資料庫會話

        Returns:
            Optional[Dict]: 用戶資訊
        """
        try:
            tenant_user = db.query(TenantUser).filter(TenantUser.user_id == user_id).first()
            if tenant_user:
                return {
                    "user_id": tenant_user.user_id,
                    "client_id": tenant_user.client_id,
                    "client_name": tenant_user.client_name,
                    "status": tenant_user.status,
                    "login_type": "tenant_user"
                }
            return None

        except Exception as e:
            print(f"❌ 查詢事務所用戶失敗: {e}")
            return None

    def get_all_tenant_users(self, db: Session) -> List[Dict[str, Any]]:
        """
        取得所有綁定使用者

        Args:
            db (Session): 資料庫會話

        Returns:
            List[Dict]: 所有用戶列表
        """
        try:
            all_users = db.query(TenantUser).all()

            users_data = []
            for user in all_users:
                users_data.append({
                    'user_id': user.user_id,
                    'client_id': user.client_id,
                    'client_name': user.client_name,
                    'status': user.status,
                    'activated_at': user.activated_at.isoformat() if user.activated_at else None,
                    'last_login': getattr(user, 'last_login', None)
                })

            return users_data

        except Exception as e:
            print(f"❌ 查詢所有用戶失敗: {e}")
            return []

    def cleanup_expired_qr_codes(self) -> int:
        """
        清理過期的 QR Code

        Returns:
            int: 清理的數量
        """
        try:
            current_time = datetime.now()
            expired_codes = [
                code for code, info in self.qr_cache.items()
                if current_time > info['expiry_time']
            ]

            for code in expired_codes:
                del self.qr_cache[code]

            print(f"✅ 已清理 {len(expired_codes)} 個過期的 QR Code")
            return len(expired_codes)

        except Exception as e:
            print(f"❌ 清理過期 QR Code 失敗: {e}")
            return 0