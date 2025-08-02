#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通知服務 - 服務層
統一所有通知相關的業務邏輯
整合現有的通知管理器功能
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Callable
from models.case_model import CaseData


class NotificationService:
    """通知服務 - 統一通知業務邏輯"""

    def __init__(self, data_folder: str = "."):
        """
        初始化通知服務

        Args:
            data_folder: 資料儲存資料夾
        """
        self.data_folder = data_folder
        self.notifications_file = os.path.join(data_folder, "notifications.json")
        self.settings_file = os.path.join(data_folder, "notification_settings.json")

        # 通知類型定義
        self.notification_types = {
            'reminder': '提醒',
            'warning': '警告',
            'urgent': '緊急',
            'info': '資訊',
            'success': '成功',
            'error': '錯誤'
        }

        # 預設設定
        self.default_settings = {
            'enabled': True,
            'reminder_days': [1, 3, 7],  # 提前幾天提醒
            'urgent_threshold': 1,       # 緊急閾值（天）
            'auto_dismiss': True,        # 自動消除過期通知
            'sound_enabled': False,      # 聲音提醒
            'popup_enabled': True        # 彈出提醒
        }

        # 載入設定和通知資料
        self.settings = self._load_settings()
        self.notifications = self._load_notifications()

        # 回調函數
        self.callbacks = {
            'on_notification_added': [],
            'on_notification_updated': [],
            'on_notification_dismissed': [],
            'on_urgent_notification': []
        }

    # ====== 通知管理 ======

    def create_notification(self, title: str, message: str, notification_type: str = 'info',
                          target_date: datetime = None, case_id: str = None,
                          auto_dismiss: bool = False) -> str:
        """
        建立通知

        Args:
            title: 通知標題
            message: 通知內容
            notification_type: 通知類型
            target_date: 目標日期
            case_id: 關聯案件ID
            auto_dismiss: 是否自動消除

        Returns:
            通知ID
        """
        try:
            notification_id = self._generate_notification_id()

            notification = {
                'id': notification_id,
                'title': title,
                'message': message,
                'type': notification_type,
                'created_date': datetime.now().isoformat(),
                'target_date': target_date.isoformat() if target_date else None,
                'case_id': case_id,
                'is_read': False,
                'is_dismissed': False,
                'auto_dismiss': auto_dismiss,
                'priority': self._calculate_priority(notification_type, target_date)
            }

            self.notifications.append(notification)
            self._save_notifications()

            # 觸發回調
            self._trigger_callbacks('on_notification_added', notification)

            # 檢查是否為緊急通知
            if self._is_urgent_notification(notification):
                self._trigger_callbacks('on_urgent_notification', notification)

            print(f"✅ 通知建立成功: {notification_id}")
            return notification_id

        except Exception as e:
            print(f"❌ 建立通知失敗: {e}")
            return ""

    def update_notification(self, notification_id: str, **updates) -> bool:
        """
        更新通知

        Args:
            notification_id: 通知ID
            **updates: 更新欄位

        Returns:
            是否成功
        """
        try:
            notification = self._find_notification_by_id(notification_id)
            if not notification:
                return False

            # 更新欄位
            for key, value in updates.items():
                if key in notification:
                    notification[key] = value

            notification['updated_date'] = datetime.now().isoformat()

            self._save_notifications()
            self._trigger_callbacks('on_notification_updated', notification)

            return True

        except Exception as e:
            print(f"❌ 更新通知失敗: {e}")
            return False

    def dismiss_notification(self, notification_id: str) -> bool:
        """
        消除通知

        Args:
            notification_id: 通知ID

        Returns:
            是否成功
        """
        try:
            notification = self._find_notification_by_id(notification_id)
            if not notification:
                return False

            notification['is_dismissed'] = True
            notification['dismissed_date'] = datetime.now().isoformat()

            self._save_notifications()
            self._trigger_callbacks('on_notification_dismissed', notification)

            return True

        except Exception as e:
            print(f"❌ 消除通知失敗: {e}")
            return False

    def mark_as_read(self, notification_id: str) -> bool:
        """
        標記通知為已讀

        Args:
            notification_id: 通知ID

        Returns:
            是否成功
        """
        try:
            notification = self._find_notification_by_id(notification_id)
            if not notification:
                return False

            notification['is_read'] = True
            notification['read_date'] = datetime.now().isoformat()

            self._save_notifications()
            return True

        except Exception as e:
            print(f"❌ 標記已讀失敗: {e}")
            return False

    # ====== 案件相關通知 ======

    def create_case_reminder(self, case_data: CaseData, reminder_date: datetime,
                           message: str = None) -> str:
        """
        建立案件提醒

        Args:
            case_data: 案件資料
            reminder_date: 提醒日期
            message: 自訂訊息

        Returns:
            通知ID
        """
        try:
            title = f"案件提醒 - {case_data.client}"

            if not message:
                message = f"案件 {case_data.client} 需要注意，目前進度：{case_data.progress or '待處理'}"

            return self.create_notification(
                title=title,
                message=message,
                notification_type='reminder',
                target_date=reminder_date,
                case_id=case_data.case_id,
                auto_dismiss=True
            )

        except Exception as e:
            print(f"❌ 建立案件提醒失敗: {e}")
            return ""

    def create_urgent_case_alert(self, case_data: CaseData, reason: str = "") -> str:
        """
        建立緊急案件警示

        Args:
            case_data: 案件資料
            reason: 緊急原因

        Returns:
            通知ID
        """
        try:
            title = f"🚨 緊急案件 - {case_data.client}"
            message = f"案件 {case_data.client} 需要緊急處理"

            if reason:
                message += f"，原因：{reason}"

            return self.create_notification(
                title=title,
                message=message,
                notification_type='urgent',
                target_date=datetime.now(),
                case_id=case_data.case_id,
                auto_dismiss=False
            )

        except Exception as e:
            print(f"❌ 建立緊急警示失敗: {e}")
            return ""

    def create_progress_notification(self, case_data: CaseData, old_progress: str,
                                   new_progress: str) -> str:
        """
        建立進度更新通知

        Args:
            case_data: 案件資料
            old_progress: 舊進度
            new_progress: 新進度

        Returns:
            通知ID
        """
        try:
            title = f"進度更新 - {case_data.client}"
            message = f"案件 {case_data.client} 進度已更新：{old_progress} → {new_progress}"

            return self.create_notification(
                title=title,
                message=message,
                notification_type='info',
                case_id=case_data.case_id,
                auto_dismiss=True
            )

        except Exception as e:
            print(f"❌ 建立進度通知失敗: {e}")
            return ""

    # ====== 自動提醒系統 ======

    def check_case_reminders(self, cases: List[CaseData]) -> List[str]:
        """
        檢查案件提醒

        Args:
            cases: 案件列表

        Returns:
            新建立的通知ID列表
        """
        new_notifications = []

        try:
            today = datetime.now().date()
            reminder_days = self.settings.get('reminder_days', [1, 3, 7])

            for case_data in cases:
                # 檢查是否有需要提醒的日期
                if case_data.progress_date:
                    progress_date = case_data.progress_date.date()
                    days_diff = (progress_date - today).days

                    # 檢查是否在提醒範圍內
                    if days_diff in reminder_days:
                        # 檢查是否已經有相同的提醒
                        if not self._has_existing_reminder(case_data.case_id, progress_date):
                            notification_id = self.create_case_reminder(
                                case_data,
                                case_data.progress_date,
                                f"案件將在 {days_diff} 天後需要處理"
                            )
                            if notification_id:
                                new_notifications.append(notification_id)

        except Exception as e:
            print(f"❌ 檢查案件提醒失敗: {e}")

        return new_notifications

    def check_urgent_cases(self, cases: List[CaseData]) -> List[str]:
        """
        檢查緊急案件

        Args:
            cases: 案件列表

        Returns:
            緊急通知ID列表
        """
        urgent_notifications = []

        try:
            today = datetime.now().date()
            urgent_threshold = self.settings.get('urgent_threshold', 1)

            for case_data in cases:
                if case_data.progress_date:
                    progress_date = case_data.progress_date.date()
                    days_diff = (progress_date - today).days

                    # 檢查是否緊急（即將到期或已過期）
                    if days_diff <= urgent_threshold:
                        if not self._has_existing_urgent_alert(case_data.case_id):
                            reason = "即將到期" if days_diff > 0 else f"已過期 {abs(days_diff)} 天"
                            notification_id = self.create_urgent_case_alert(case_data, reason)
                            if notification_id:
                                urgent_notifications.append(notification_id)

        except Exception as e:
            print(f"❌ 檢查緊急案件失敗: {e}")

        return urgent_notifications

    # ====== 通知查詢 ======

    def get_all_notifications(self, include_dismissed: bool = False) -> List[Dict[str, Any]]:
        """
        取得所有通知

        Args:
            include_dismissed: 是否包含已消除的通知

        Returns:
            通知列表
        """
        try:
            if include_dismissed:
                return self.notifications.copy()
            else:
                return [n for n in self.notifications if not n.get('is_dismissed', False)]

        except Exception as e:
            print(f"❌ 取得通知列表失敗: {e}")
            return []

    def get_unread_notifications(self) -> List[Dict[str, Any]]:
        """
        取得未讀通知

        Returns:
            未讀通知列表
        """
        try:
            return [n for n in self.notifications
                   if not n.get('is_read', False) and not n.get('is_dismissed', False)]

        except Exception as e:
            print(f"❌ 取得未讀通知失敗: {e}")
            return []

    def get_urgent_notifications(self) -> List[Dict[str, Any]]:
        """
        取得緊急通知

        Returns:
            緊急通知列表
        """
        try:
            return [n for n in self.notifications
                   if n.get('type') == 'urgent' and not n.get('is_dismissed', False)]

        except Exception as e:
            print(f"❌ 取得緊急通知失敗: {e}")
            return []

    def get_case_notifications(self, case_id: str) -> List[Dict[str, Any]]:
        """
        取得特定案件的通知

        Args:
            case_id: 案件ID

        Returns:
            案件通知列表
        """
        try:
            return [n for n in self.notifications
                   if n.get('case_id') == case_id and not n.get('is_dismissed', False)]

        except Exception as e:
            print(f"❌ 取得案件通知失敗: {e}")
            return []

    def get_notifications_by_type(self, notification_type: str) -> List[Dict[str, Any]]:
        """
        取得特定類型的通知

        Args:
            notification_type: 通知類型

        Returns:
            特定類型通知列表
        """
        try:
            return [n for n in self.notifications
                   if n.get('type') == notification_type and not n.get('is_dismissed', False)]

        except Exception as e:
            print(f"❌ 取得特定類型通知失敗: {e}")
            return []

    # ====== 通知統計 ======

    def get_notification_stats(self) -> Dict[str, Any]:
        """
        取得通知統計資訊

        Returns:
            統計資訊字典
        """
        try:
            active_notifications = [n for n in self.notifications if not n.get('is_dismissed', False)]

            stats = {
                'total': len(self.notifications),
                'active': len(active_notifications),
                'unread': len([n for n in active_notifications if not n.get('is_read', False)]),
                'urgent': len([n for n in active_notifications if n.get('type') == 'urgent']),
                'by_type': {}
            }

            # 按類型統計
            for notification_type in self.notification_types.keys():
                count = len([n for n in active_notifications if n.get('type') == notification_type])
                stats['by_type'][notification_type] = count

            return stats

        except Exception as e:
            print(f"❌ 取得通知統計失敗: {e}")
            return {}

    # ====== 自動清理 ======

    def cleanup_old_notifications(self, days_to_keep: int = 30) -> int:
        """
        清理舊通知

        Args:
            days_to_keep: 保留天數

        Returns:
            清理的通知數量
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            initial_count = len(self.notifications)

            # 保留未消除的通知和最近的通知
            self.notifications = [
                n for n in self.notifications
                if not n.get('is_dismissed', False) or
                datetime.fromisoformat(n.get('created_date', cutoff_date.isoformat())) > cutoff_date
            ]

            cleaned_count = initial_count - len(self.notifications)

            if cleaned_count > 0:
                self._save_notifications()
                print(f"✅ 清理了 {cleaned_count} 個舊通知")

            return cleaned_count

        except Exception as e:
            print(f"❌ 清理舊通知失敗: {e}")
            return 0

    def auto_dismiss_expired_notifications(self) -> int:
        """
        自動消除過期通知

        Returns:
            消除的通知數量
        """
        try:
            dismissed_count = 0
            today = datetime.now()

            for notification in self.notifications:
                if (notification.get('auto_dismiss', False) and
                    notification.get('target_date') and
                    not notification.get('is_dismissed', False)):

                    target_date = datetime.fromisoformat(notification['target_date'])
                    if target_date < today:
                        notification['is_dismissed'] = True
                        notification['dismissed_date'] = today.isoformat()
                        dismissed_count += 1

            if dismissed_count > 0:
                self._save_notifications()
                print(f"✅ 自動消除了 {dismissed_count} 個過期通知")

            return dismissed_count

        except Exception as e:
            print(f"❌ 自動消除過期通知失敗: {e}")
            return 0

    # ====== 回調管理 ======

    def register_callback(self, event_type: str, callback: Callable):
        """
        註冊回調函數

        Args:
            event_type: 事件類型
            callback: 回調函數
        """
        if event_type in self.callbacks:
            self.callbacks[event_type].append(callback)

    def unregister_callback(self, event_type: str, callback: Callable):
        """
        取消註冊回調函數

        Args:
            event_type: 事件類型
            callback: 回調函數
        """
        if event_type in self.callbacks and callback in self.callbacks[event_type]:
            self.callbacks[event_type].remove(callback)

    def _trigger_callbacks(self, event_type: str, notification: Dict[str, Any]):
        """觸發回調函數"""
        try:
            for callback in self.callbacks.get(event_type, []):
                callback(notification)
        except Exception as e:
            print(f"❌ 觸發回調失敗: {e}")

    # ====== 設定管理 ======

    def update_settings(self, **settings) -> bool:
        """
        更新通知設定

        Args:
            **settings: 設定參數

        Returns:
            是否成功
        """
        try:
            for key, value in settings.items():
                if key in self.default_settings:
                    self.settings[key] = value

            self._save_settings()
            return True

        except Exception as e:
            print(f"❌ 更新設定失敗: {e}")
            return False

    def get_settings(self) -> Dict[str, Any]:
        """
        取得通知設定

        Returns:
            設定字典
        """
        return self.settings.copy()

    def reset_settings(self) -> bool:
        """
        重設為預設設定

        Returns:
            是否成功
        """
        try:
            self.settings = self.default_settings.copy()
            self._save_settings()
            return True

        except Exception as e:
            print(f"❌ 重設設定失敗: {e}")
            return False

    # ====== 私有方法 ======

    def _load_notifications(self) -> List[Dict[str, Any]]:
        """載入通知資料"""
        try:
            if os.path.exists(self.notifications_file):
                with open(self.notifications_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"⚠️ 載入通知資料失敗: {e}")

        return []

    def _save_notifications(self) -> bool:
        """儲存通知資料"""
        try:
            os.makedirs(os.path.dirname(self.notifications_file), exist_ok=True)
            with open(self.notifications_file, 'w', encoding='utf-8') as f:
                json.dump(self.notifications, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"❌ 儲存通知資料失敗: {e}")
            return False

    def _load_settings(self) -> Dict[str, Any]:
        """載入設定"""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    loaded_settings = json.load(f)
                    # 合併預設設定
                    settings = self.default_settings.copy()
                    settings.update(loaded_settings)
                    return settings
        except Exception as e:
            print(f"⚠️ 載入設定失敗: {e}")

        return self.default_settings.copy()

    def _save_settings(self) -> bool:
        """儲存設定"""
        try:
            os.makedirs(os.path.dirname(self.settings_file), exist_ok=True)
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"❌ 儲存設定失敗: {e}")
            return False

    def _generate_notification_id(self) -> str:
        """產生通知ID"""
        import uuid
        return f"NOTIF_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"

    def _find_notification_by_id(self, notification_id: str) -> Optional[Dict[str, Any]]:
        """根據ID尋找通知"""
        for notification in self.notifications:
            if notification.get('id') == notification_id:
                return notification
        return None

    def _calculate_priority(self, notification_type: str, target_date: datetime = None) -> int:
        """計算通知優先級"""
        priority = 0

        # 根據類型設定基礎優先級
        type_priorities = {
            'urgent': 100,
            'warning': 80,
            'reminder': 60,
            'info': 40,
            'success': 20,
            'error': 90
        }
        priority += type_priorities.get(notification_type, 40)

        # 根據距離目標日期調整優先級
        if target_date:
            days_diff = (target_date - datetime.now()).days
            if days_diff <= 0:
                priority += 50  # 已過期
            elif days_diff <= 1:
                priority += 30  # 即將到期
            elif days_diff <= 3:
                priority += 20  # 近期

        return min(priority, 150)  # 限制最大優先級

    def _is_urgent_notification(self, notification: Dict[str, Any]) -> bool:
        """判斷是否為緊急通知"""
        return (notification.get('type') == 'urgent' or
                notification.get('priority', 0) >= 100)

    def _has_existing_reminder(self, case_id: str, target_date) -> bool:
        """檢查是否已有相同的提醒"""
        target_date_str = target_date.isoformat() if hasattr(target_date, 'isoformat') else str(target_date)

        for notification in self.notifications:
            if (notification.get('case_id') == case_id and
                notification.get('type') == 'reminder' and
                notification.get('target_date') == target_date_str and
                not notification.get('is_dismissed', False)):
                return True
        return False

    def _has_existing_urgent_alert(self, case_id: str) -> bool:
        """檢查是否已有緊急警示"""
        today = datetime.now().date().isoformat()

        for notification in self.notifications:
            if (notification.get('case_id') == case_id and
                notification.get('type') == 'urgent' and
                notification.get('created_date', '').startswith(today) and
                not notification.get('is_dismissed', False)):
                return True
        return False