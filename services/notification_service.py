#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
通知業務邏輯服務
專責處理系統通知相關的業務邏輯
"""

from typing import List, Optional, Dict, Any, Callable
from models.case_model import CaseData
from datetime import datetime, timedelta
import json
import os
from enum import Enum


class NotificationLevel(Enum):
    """通知級別"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"


class NotificationType(Enum):
    """通知類型"""
    CASE_CREATED = "case_created"
    CASE_UPDATED = "case_updated"
    CASE_DELETED = "case_deleted"
    DEADLINE_REMINDER = "deadline_reminder"
    DATA_IMPORTED = "data_imported"
    DATA_EXPORTED = "data_exported"
    SYSTEM_ERROR = "system_error"
    FOLDER_OPERATION = "folder_operation"


class NotificationService:
    """通知業務邏輯服務"""

    def __init__(self, notification_folder: str = None):
        """
        初始化通知服務

        Args:
            notification_folder: 通知存放資料夾
        """
        self.notification_folder = notification_folder or "./notifications"
        self.notification_history_file = os.path.join(self.notification_folder, "notification_history.json")

        # 通知訂閱者（回調函數）
        self.subscribers: Dict[NotificationType, List[Callable]] = {}

        # 確保通知資料夾存在
        os.makedirs(self.notification_folder, exist_ok=True)


        print("✅ NotificationService 初始化完成")

    # ==================== 通知訂閱管理 ====================

    def subscribe(self, notification_type: NotificationType, callback: Callable):
        """
        訂閱特定類型的通知

        Args:
            notification_type: 通知類型
            callback: 回調函數
        """
        if notification_type not in self.subscribers:
            self.subscribers[notification_type] = []

        self.subscribers[notification_type].append(callback)
        print(f"✅ 已訂閱通知: {notification_type.value}")

    def unsubscribe(self, notification_type: NotificationType, callback: Callable):
        """
        取消訂閱特定類型的通知

        Args:
            notification_type: 通知類型
            callback: 回調函數
        """
        if notification_type in self.subscribers:
            try:
                self.subscribers[notification_type].remove(callback)
                print(f"✅ 已取消訂閱通知: {notification_type.value}")
            except ValueError:
                print(f"⚠️ 回調函數未找到: {notification_type.value}")

    def clear_subscribers(self, notification_type: NotificationType = None):
        """
        清除訂閱者

        Args:
            notification_type: 指定類型，None 表示清除所有
        """
        if notification_type:
            self.subscribers[notification_type] = []
        else:
            self.subscribers.clear()
        print("✅ 已清除通知訂閱者")

    # ==================== 案件相關通知 ====================

    def notify_case_created(self, case_data: CaseData):
        """通知案件已建立"""
        notification = self._create_notification(
            type=NotificationType.CASE_CREATED,
            level=NotificationLevel.SUCCESS,
            title="案件建立成功",
            message=f"已成功建立案件：{case_data.client} ({case_data.case_type})",
            data={'case_id': case_data.case_id, 'client': case_data.client}
        )
        self._send_notification(notification)

    def notify_case_updated(self, new_case_data: CaseData, old_case_data: CaseData):
        """通知案件已更新"""
        changes = self._detect_case_changes(old_case_data, new_case_data)

        notification = self._create_notification(
            type=NotificationType.CASE_UPDATED,
            level=NotificationLevel.INFO,
            title="案件更新",
            message=f"案件 {new_case_data.client} 已更新",
            data={
                'case_id': new_case_data.case_id,
                'client': new_case_data.client,
                'changes': changes
            }
        )
        self._send_notification(notification)

    def notify_case_deleted(self, case_data: CaseData):
        """通知案件已刪除"""
        notification = self._create_notification(
            type=NotificationType.CASE_DELETED,
            level=NotificationLevel.WARNING,
            title="案件已刪除",
            message=f"案件已刪除：{case_data.client} ({case_data.case_type})",
            data={'case_id': case_data.case_id, 'client': case_data.client}
        )
        self._send_notification(notification)

    # ==================== 期限提醒通知 ====================

    def notify_deadline_reminder(self, case_data: CaseData, deadline_info: Dict[str, Any]):
        """通知期限提醒"""
        days_until = deadline_info.get('days_until', 0)
        level = NotificationLevel.ERROR if days_until <= 1 else NotificationLevel.WARNING

        if days_until <= 0:
            title = "⚠️ 期限已到期"
            message = f"案件 {case_data.client} 的 {deadline_info['description']} 已到期"
        elif days_until == 1:
            title = "🚨 明天到期"
            message = f"案件 {case_data.client} 的 {deadline_info['description']} 明天到期"
        else:
            title = f"📅 {days_until} 天後到期"
            message = f"案件 {case_data.client} 的 {deadline_info['description']} 將在 {days_until} 天後到期"

        notification = self._create_notification(
            type=NotificationType.DEADLINE_REMINDER,
            level=level,
            title=title,
            message=message,
            data={
                'case_id': case_data.case_id,
                'client': case_data.client,
                'deadline_date': deadline_info.get('date'),
                'description': deadline_info.get('description'),
                'days_until': days_until
            }
        )
        self._send_notification(notification)

    def check_and_send_deadline_reminders(self, cases: List[CaseData],
                                         reminder_days: List[int] = [1, 3, 7]):
        """
        檢查並發送期限提醒

        Args:
            cases: 要檢查的案件列表
            reminder_days: 提醒天數列表
        """
        today = datetime.now().date()
        reminders_sent = 0

        for case in cases:
            if not case.important_dates:
                continue

            for date_info in case.important_dates:
                if not date_info.date:
                    continue

                deadline_date = date_info.date.date() if hasattr(date_info.date, 'date') else date_info.date
                days_until = (deadline_date - today).days

                if days_until in reminder_days or days_until <= 0:
                    self.notify_deadline_reminder(case, {
                        'date': deadline_date,
                        'description': date_info.description or "重要日期",
                        'days_until': days_until
                    })
                    reminders_sent += 1

        if reminders_sent > 0:
            print(f"📬 已發送 {reminders_sent} 個期限提醒通知")

    # ==================== 資料操作通知 ====================

    def notify_data_imported(self, import_report: Dict[str, Any]):
        """通知資料匯入完成"""
        imported_count = import_report.get('imported_count', 0)
        failed_count = import_report.get('failed_count', 0)

        if failed_count > 0:
            level = NotificationLevel.WARNING
            title = "資料匯入完成（有錯誤）"
            message = f"匯入完成：成功 {imported_count} 筆，失敗 {failed_count} 筆"
        else:
            level = NotificationLevel.SUCCESS
            title = "資料匯入完成"
            message = f"成功匯入 {imported_count} 筆案件資料"

        notification = self._create_notification(
            type=NotificationType.DATA_IMPORTED,
            level=level,
            title=title,
            message=message,
            data=import_report
        )
        self._send_notification(notification)

    def notify_data_exported(self, export_report: Dict[str, Any]):
        """通知資料匯出完成"""
        total_cases = export_report.get('total_cases', 0)
        file_path = export_report.get('file_path', '')

        notification = self._create_notification(
            type=NotificationType.DATA_EXPORTED,
            level=NotificationLevel.SUCCESS,
            title="資料匯出完成",
            message=f"成功匯出 {total_cases} 筆案件資料到 {os.path.basename(file_path)}",
            data=export_report
        )
        self._send_notification(notification)

    # ==================== 系統通知 ====================

    def notify_system_error(self, error_message: str, error_details: Dict[str, Any] = None):
        """通知系統錯誤"""
        notification = self._create_notification(
            type=NotificationType.SYSTEM_ERROR,
            level=NotificationLevel.ERROR,
            title="系統錯誤",
            message=error_message,
            data=error_details or {}
        )
        self._send_notification(notification)

    def notify_folder_operation(self, operation: str, case_data: CaseData, success: bool, message: str = ""):
        """通知資料夾操作結果"""
        level = NotificationLevel.SUCCESS if success else NotificationLevel.ERROR
        title = f"資料夾{operation}{'成功' if success else '失敗'}"

        notification = self._create_notification(
            type=NotificationType.FOLDER_OPERATION,
            level=level,
            title=title,
            message=f"案件 {case_data.client} 的資料夾{operation}{'成功' if success else '失敗'}{': ' + message if message else ''}",
            data={
                'case_id': case_data.case_id,
                'client': case_data.client,
                'operation': operation,
                'success': success
            }
        )
        self._send_notification(notification)


    # ==================== 統計和報告 ====================

    def get_notification_statistics(self, days: int = 7) -> Dict[str, Any]:
        """
        取得通知統計

        Args:
            days: 統計天數

        Returns:
            統計資訊
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_notifications = [
            n for n in self.notification_history
            if datetime.fromisoformat(n.get('timestamp', '')) > cutoff_date
        ]

        stats = {
            'total_notifications': len(recent_notifications),
            'unread_count': len([n for n in recent_notifications if not n.get('read', False)]),
            'by_type': {},
            'by_level': {},
            'by_day': {}
        }

        # 按類型統計
        for notification in recent_notifications:
            ntype = notification.get('type', 'unknown')
            stats['by_type'][ntype] = stats['by_type'].get(ntype, 0) + 1

        # 按級別統計
        for notification in recent_notifications:
            level = notification.get('level', 'unknown')
            stats['by_level'][level] = stats['by_level'].get(level, 0) + 1

        # 按日期統計
        for notification in recent_notifications:
            timestamp = datetime.fromisoformat(notification.get('timestamp', ''))
            date_key = timestamp.date().isoformat()
            stats['by_day'][date_key] = stats['by_day'].get(date_key, 0) + 1

        return stats

    # ==================== 私有輔助方法 ====================

    def _create_notification(self, type: NotificationType, level: NotificationLevel,
                           title: str, message: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """建立通知物件"""
        import uuid

        notification = {
            'id': str(uuid.uuid4()),
            'type': type.value,
            'level': level.value,
            'title': title,
            'message': message,
            'timestamp': datetime.now().isoformat(),
            'read': False,
            'data': data or {}
        }

        return notification

    def _send_notification(self, notification: Dict[str, Any]):
        """發送通知"""
        try:

            # 2. 呼叫訂閱者的回調函數
            notification_type = NotificationType(notification['type'])
            if notification_type in self.subscribers:
                for callback in self.subscribers[notification_type]:
                    try:
                        callback(notification)
                    except Exception as e:
                        print(f"⚠️ 通知回調函數錯誤: {e}")

            # 3. 控制台輸出（基本顯示）
            self._console_notification(notification)

            # 4. 限制歷史記錄數量
            if len(self.notification_history) > 1000:
                self.notification_history = self.notification_history[-500:]
                self._save_notification_history()

        except Exception as e:
            print(f"❌ 發送通知失敗: {e}")

    def _console_notification(self, notification: Dict[str, Any]):
        """控制台通知顯示"""
        level = notification['level']
        title = notification['title']
        message = notification['message']

        # 根據級別選擇圖示
        icons = {
            'info': 'ℹ️',
            'success': '✅',
            'warning': '⚠️',
            'error': '❌'
        }

        icon = icons.get(level, 'ℹ️')
        print(f"{icon} [{title}] {message}")

    def _detect_case_changes(self, old_case: CaseData, new_case: CaseData) -> List[str]:
        """檢測案件變更"""
        changes = []

        # 檢查主要欄位變更
        fields_to_check = [
            ('client', '當事人'),
            ('case_type', '案件類型'),
            ('status', '狀態'),
            ('notes', '備註')
        ]

        for field, display_name in fields_to_check:
            old_value = getattr(old_case, field, None)
            new_value = getattr(new_case, field, None)

            if old_value != new_value:
                changes.append(f"{display_name}: {old_value} → {new_value}")

        return changes

