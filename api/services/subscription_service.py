# api/services/subscription_service.py
"""
方案管理服務邏輯層
處理付費用戶、未付費用戶和方案升級的業務邏輯
"""

from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text, and_
from datetime import datetime, timedelta
from api.models_control import (
    TenantUser, PendingUser, Tenant, PlanChangeHistory,
    PlanType, UserStatus
)

class SubscriptionService:
    """方案管理服務類別"""

    def __init__(self):
        self.plan_limits = {
            "basic_5": 5,
            "standard_10": 10,
            "premium_20": 20,
            "enterprise_50": 50
        }
        self.user_status = {
            "pending": "pending",
            "active": "active",
            "suspended": "suspended",
            "expired": "expired"
        }

    def check_user_is_paid(self, user_id: str, db: Session) -> bool:
        """
        檢查用戶是否為付費用戶（用於 N8N Webhook 過濾）

        Args:
            user_id: LINE 用戶ID
            db: 資料庫會話

        Returns:
            bool: 是付費用戶返回 True，否則返回 False
        """
        try:
            tenant_user = db.query(TenantUser).filter(
                and_(
                    TenantUser.user_id == user_id,
                    TenantUser.status == "active"  # ✅ 改為字串比較
                )
            ).first()
            return tenant_user is not None
        except Exception as e:
            print(f"❌ 檢查付費用戶失敗: {e}")
            return False

    def register_pending_user(self, user_id: str, client_id: str, client_name: str,
                            user_name: str = None, email: str = None, phone: str = None,
                            db: Session = None) -> Dict[str, Any]:
        """
        註冊未付費用戶

        Args:
            user_id: LINE 用戶ID
            client_id: 租戶ID
            client_name: 租戶名稱
            user_name: 用戶姓名
            email: 用戶信箱
            phone: 聯絡電話
            db: 資料庫會話

        Returns:
            Dict: 註冊結果
        """
        try:
            # 檢查是否已經是付費用戶
            existing_paid = db.query(TenantUser).filter(TenantUser.user_id == user_id).first()
            if existing_paid:
                return {
                    "success": False,
                    "message": "此用戶已是付費用戶",
                    "user_status": "already_paid"
                }

            # 檢查是否已在待審核列表
            existing_pending = db.query(PendingUser).filter(PendingUser.user_id == user_id).first()
            if existing_pending:
                return {
                    "success": False,
                    "message": "此用戶已在審核列表中",
                    "user_status": "already_pending"
                }

            # 新增到未付費用戶表
            pending_user = PendingUser(
                user_id=user_id,
                client_id=client_id,
                client_name=client_name,
                user_name=user_name,
                email=email,
                phone=phone,
                status="pending"  # ✅ 改為字串
            )

            db.add(pending_user)
            db.commit()

            return {
                "success": True,
                "message": "註冊成功，等待管理員審核",
                "user_status": "pending",
                "user_id": user_id
            }

        except Exception as e:
            db.rollback()
            print(f"❌ 註冊未付費用戶失敗: {e}")
            return {
                "success": False,
                "message": f"註冊失敗: {str(e)}",
                "user_status": "error"
            }

    def get_tenant_plan_status(self, client_id: str, db: Session) -> Dict[str, Any]:
        """
        取得租戶方案狀態

        Args:
            client_id: 租戶ID
            db: 資料庫會話

        Returns:
            Dict: 方案狀態資訊
        """
        try:
            tenant = db.query(Tenant).filter(Tenant.schema_name == client_id).first()
            if not tenant:
                return {"success": False, "message": "租戶不存在"}

            # 計算實際用戶數
            current_paid_users = db.query(TenantUser).filter(
                and_(
                    TenantUser.client_id == client_id,
                    TenantUser.status == UserStatus.ACTIVE
                )
            ).count()

            # 更新租戶的用戶數
            tenant.current_users = current_paid_users
            db.commit()

            pending_users = db.query(PendingUser).filter(
                and_(
                    PendingUser.client_id == client_id,
                    PendingUser.status == UserStatus.PENDING
                )
            ).count()

            return {
                "success": True,
                "tenant_name": tenant.name,
                "plan_type": tenant.plan_type.value,
                "plan_limit": tenant.plan_limit,
                "current_users": current_paid_users,
                "pending_users": pending_users,
                "available_slots": max(0, tenant.plan_limit - current_paid_users),
                "usage_percentage": round((current_paid_users / tenant.plan_limit) * 100, 1),
                "is_plan_full": current_paid_users >= tenant.plan_limit,
                "is_active": tenant.is_active
            }

        except Exception as e:
            print(f"❌ 取得租戶方案狀態失敗: {e}")
            return {"success": False, "message": f"查詢失敗: {str(e)}"}

    def upgrade_plan(self, client_id: str, new_plan_type: PlanType,
                    changed_by: str = None, reason: str = None, db: Session = None) -> Dict[str, Any]:
        """
        升級方案並自動遷移用戶

        Args:
            client_id: 租戶ID
            new_plan_type: 新方案類型
            changed_by: 變更者
            reason: 變更原因
            db: 資料庫會話

        Returns:
            Dict: 升級結果
        """
        try:
            tenant = db.query(Tenant).filter(Tenant.schema_name == client_id).first()
            if not tenant:
                return {"success": False, "message": "租戶不存在"}

            old_plan = tenant.plan_type
            old_limit = tenant.plan_limit
            new_limit = self.plan_limits[new_plan_type]

            # 記錄方案變更歷史
            history = PlanChangeHistory(
                client_id=client_id,
                old_plan_type=old_plan,
                new_plan_type=new_plan_type,
                old_limit=old_limit,
                new_limit=new_limit,
                changed_by=changed_by,
                change_reason=reason
            )

            # 更新租戶方案
            tenant.plan_type = new_plan_type
            tenant.plan_limit = new_limit

            # 如果是升級（人數增加），自動遷移未付費用戶
            migrated_count = 0
            if new_limit > old_limit:
                migrated_count = self._migrate_pending_users(client_id, new_limit, db)
                history.users_migrated = migrated_count

            db.add(history)
            db.commit()

            return {
                "success": True,
                "message": f"方案升級成功：{old_plan.value} -> {new_plan_type.value}",
                "old_plan": old_plan.value,
                "new_plan": new_plan_type.value,
                "old_limit": old_limit,
                "new_limit": new_limit,
                "users_migrated": migrated_count
            }

        except Exception as e:
            db.rollback()
            print(f"❌ 方案升級失敗: {e}")
            return {"success": False, "message": f"升級失敗: {str(e)}"}

    def _migrate_pending_users(self, client_id: str, new_limit: int, db: Session) -> int:
        """
        自動將未付費用戶遷移到付費用戶表

        Args:
            client_id: 租戶ID
            new_limit: 新的人數限制
            db: 資料庫會話

        Returns:
            int: 遷移的用戶數量
        """
        try:
            # 計算當前付費用戶數
            current_paid = db.query(TenantUser).filter(
                and_(
                    TenantUser.client_id == client_id,
                    TenantUser.status == UserStatus.ACTIVE
                )
            ).count()

            # 計算可遷移的名額
            available_slots = new_limit - current_paid
            if available_slots <= 0:
                return 0

            # 取得待遷移的未付費用戶（按申請時間排序）
            pending_users = db.query(PendingUser).filter(
                and_(
                    PendingUser.client_id == client_id,
                    PendingUser.status == UserStatus.PENDING
                )
            ).order_by(PendingUser.requested_at).limit(available_slots).all()

            migrated_count = 0
            for pending_user in pending_users:
                # 遷移到付費用戶表
                tenant_user = TenantUser(
                    user_id=pending_user.user_id,
                    client_id=pending_user.client_id,
                    client_name=pending_user.client_name,
                    status=UserStatus.ACTIVE,
                    activated_at=datetime.now()
                )

                db.add(tenant_user)

                # 更新未付費用戶狀態
                pending_user.status = UserStatus.ACTIVE
                pending_user.approved_by = "system_auto_migration"

                migrated_count += 1

            # 更新租戶用戶數
            tenant = db.query(Tenant).filter(Tenant.schema_name == client_id).first()
            if tenant:
                tenant.current_users = current_paid + migrated_count

            db.commit()
            print(f"✅ 自動遷移 {migrated_count} 個用戶到付費用戶表")
            return migrated_count

        except Exception as e:
            db.rollback()
            print(f"❌ 自動遷移用戶失敗: {e}")
            return 0

    def manually_approve_user(self, user_id: str, approved_by: str,
                            notes: str = None, db: Session = None) -> Dict[str, Any]:
        """
        手動審核並啟用未付費用戶

        Args:
            user_id: LINE 用戶ID
            approved_by: 審核者
            notes: 審核備註
            db: 資料庫會話

        Returns:
            Dict: 審核結果
        """
        try:
            pending_user = db.query(PendingUser).filter(PendingUser.user_id == user_id).first()
            if not pending_user:
                return {"success": False, "message": "找不到待審核用戶"}

            # 檢查租戶方案是否已滿
            tenant = db.query(Tenant).filter(Tenant.schema_name == pending_user.client_id).first()
            if not tenant:
                return {"success": False, "message": "租戶不存在"}

            if tenant.is_plan_full:
                return {
                    "success": False,
                    "message": f"方案已滿（{tenant.current_users}/{tenant.plan_limit}），請先升級方案"
                }

            # 遷移到付費用戶表
            tenant_user = TenantUser(
                user_id=pending_user.user_id,
                client_id=pending_user.client_id,
                client_name=pending_user.client_name,
                status=UserStatus.ACTIVE,
                activated_at=datetime.now()
            )

            db.add(tenant_user)

            # 更新未付費用戶狀態
            pending_user.status = UserStatus.ACTIVE
            pending_user.approved_by = approved_by
            pending_user.notes = notes

            # 更新租戶用戶數
            tenant.current_users += 1

            db.commit()

            return {
                "success": True,
                "message": f"用戶 {user_id} 已成功啟用",
                "user_id": user_id,
                "client_name": pending_user.client_name,
                "remaining_slots": tenant.available_slots
            }

        except Exception as e:
            db.rollback()
            print(f"❌ 手動審核用戶失敗: {e}")
            return {"success": False, "message": f"審核失敗: {str(e)}"}

    def get_pending_users_by_tenant(self, client_id: str, db: Session) -> List[Dict[str, Any]]:
        """
        取得租戶的所有待審核用戶

        Args:
            client_id: 租戶ID
            db: 資料庫會話

        Returns:
            List[Dict]: 待審核用戶列表
        """
        try:
            pending_users = db.query(PendingUser).filter(
                and_(
                    PendingUser.client_id == client_id,
                    PendingUser.status == UserStatus.PENDING
                )
            ).order_by(PendingUser.requested_at).all()

            result = []
            for user in pending_users:
                result.append({
                    "user_id": user.user_id,
                    "user_name": user.user_name,
                    "email": user.email,
                    "phone": user.phone,
                    "requested_at": user.requested_at.isoformat(),
                    "status": user.status.value
                })

            return result

        except Exception as e:
            print(f"❌ 取得待審核用戶失敗: {e}")
            return []

    def get_all_users_by_tenant(self, client_id: str, db: Session) -> Dict[str, Any]:
        """
        取得租戶的所有用戶（付費 + 待審核）

        Args:
            client_id: 租戶ID
            db: 資料庫會話

        Returns:
            Dict: 完整的用戶狀態
        """
        try:
            # 付費用戶
            paid_users = db.query(TenantUser).filter(
                TenantUser.client_id == client_id
            ).all()

            # 待審核用戶
            pending_users = db.query(PendingUser).filter(
                and_(
                    PendingUser.client_id == client_id,
                    PendingUser.status == UserStatus.PENDING
                )
            ).all()

            # 租戶資訊
            tenant = db.query(Tenant).filter(Tenant.schema_name == client_id).first()
            if not tenant:
                return {"success": False, "message": "租戶不存在"}

            return {
                "success": True,
                "tenant_info": {
                    "name": tenant.name,
                    "plan_type": tenant.plan_type.value,
                    "plan_limit": tenant.plan_limit,
                    "current_users": len(paid_users),
                    "pending_users": len(pending_users),
                    "available_slots": tenant.available_slots,
                    "usage_percentage": tenant.plan_usage_percentage
                },
                "paid_users": [
                    {
                        "user_id": user.user_id,
                        "client_name": user.client_name,
                        "status": user.status.value,
                        "activated_at": user.activated_at.isoformat() if user.activated_at else None,
                        "last_login": user.last_login.isoformat() if user.last_login else None
                    }
                    for user in paid_users
                ],
                "pending_users": [
                    {
                        "user_id": user.user_id,
                        "user_name": user.user_name,
                        "email": user.email,
                        "phone": user.phone,
                        "requested_at": user.requested_at.isoformat(),
                        "status": user.status.value
                    }
                    for user in pending_users
                ]
            }

        except Exception as e:
            print(f"❌ 取得租戶用戶資訊失敗: {e}")
            return {"success": False, "message": f"查詢失敗: {str(e)}"}

    def remove_user_from_plan(self, user_id: str, reason: str = None, db: Session = None) -> Dict[str, Any]:
        """
        從方案中移除用戶

        Args:
            user_id: LINE 用戶ID
            reason: 移除原因
            db: 資料庫會話

        Returns:
            Dict: 移除結果
        """
        try:
            tenant_user = db.query(TenantUser).filter(TenantUser.user_id == user_id).first()
            if not tenant_user:
                return {"success": False, "message": "找不到該付費用戶"}

            client_id = tenant_user.client_id

            # 更新用戶狀態為暫停
            tenant_user.status = UserStatus.SUSPENDED

            # 更新租戶用戶數
            tenant = db.query(Tenant).filter(Tenant.schema_name == client_id).first()
            if tenant:
                tenant.current_users = max(0, tenant.current_users - 1)

            db.commit()

            # 檢查是否有待審核用戶可以自動啟用
            auto_promoted = self._auto_promote_pending_user(client_id, db)

            return {
                "success": True,
                "message": f"用戶 {user_id} 已移除",
                "removed_user": user_id,
                "auto_promoted": auto_promoted,
                "remaining_users": tenant.current_users if tenant else 0
            }

        except Exception as e:
            db.rollback()
            print(f"❌ 移除用戶失敗: {e}")
            return {"success": False, "message": f"移除失敗: {str(e)}"}

    def _auto_promote_pending_user(self, client_id: str, db: Session) -> Optional[str]:
        """
        自動提升一個待審核用戶到付費用戶

        Args:
            client_id: 租戶ID
            db: 資料庫會話

        Returns:
            Optional[str]: 被提升的用戶ID，如果沒有則返回 None
        """
        try:
            # 取得最早的待審核用戶
            pending_user = db.query(PendingUser).filter(
                and_(
                    PendingUser.client_id == client_id,
                    PendingUser.status == UserStatus.PENDING
                )
            ).order_by(PendingUser.requested_at).first()

            if not pending_user:
                return None

            # 遷移到付費用戶表
            result = self.manually_approve_user(
                pending_user.user_id,
                "system_auto_promotion",
                "因其他用戶移除而自動提升",
                db
            )

            if result["success"]:
                return pending_user.user_id
            return None

        except Exception as e:
            print(f"❌ 自動提升用戶失敗: {e}")
            return None