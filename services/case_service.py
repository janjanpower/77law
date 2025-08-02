#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
案件業務邏輯服務
專責處理案件相關的業務邏輯，與控制層分離
"""

from typing import List, Optional, Dict, Any, Tuple
from models.case_model import CaseData
import uuid
import os
import json
from datetime import datetime


class CaseRepository:
    """簡化的案件資料存取器"""

    def __init__(self, data_file: str):
        self.data_file = data_file
        self.cases = []
        self._load_cases()

    def _load_cases(self):
        """載入案件資料"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.cases = [CaseData.from_dict(item) if isinstance(item, dict) else item for item in data]
        except Exception as e:
            print(f"⚠️ 載入案件資料失敗: {e}")
            self.cases = []

    def _save_cases(self):
        """儲存案件資料"""
        try:
            os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
            with open(self.data_file, 'w', encoding='utf-8') as f:
                data = [case.to_dict() if hasattr(case, 'to_dict') else case for case in self.cases]
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            print(f"⚠️ 儲存案件資料失敗: {e}")

    def get_all_cases(self):
        """取得所有案件"""
        return self.cases

    def get_case_by_id(self, case_id: str):
        """根據ID取得案件"""
        for case in self.cases:
            if hasattr(case, 'case_id') and case.case_id == case_id:
                return case
        return None

    def create_case(self, case_data):
        """建立案件"""
        try:
            self.cases.append(case_data)
            self._save_cases()
            return True
        except Exception as e:
            print(f"⚠️ 建立案件失敗: {e}")
            return False

    def update_case(self, case_data):
        """更新案件"""
        try:
            for i, case in enumerate(self.cases):
                if hasattr(case, 'case_id') and case.case_id == case_data.case_id:
                    self.cases[i] = case_data
                    self._save_cases()
                    return True
            return False
        except Exception as e:
            print(f"⚠️ 更新案件失敗: {e}")
            return False

    def delete_case(self, case_id: str):
        """刪除案件"""
        try:
            original_count = len(self.cases)
            self.cases = [case for case in self.cases if not (hasattr(case, 'case_id') and case.case_id == case_id)]
            if len(self.cases) < original_count:
                self._save_cases()
                return True
            return False
        except Exception as e:
            print(f"⚠️ 刪除案件失敗: {e}")
            return False

    def get_cases_by_client(self, client_name: str):
        """根據當事人取得案件"""
        return [case for case in self.cases if hasattr(case, 'client') and case.client == client_name]

    def get_cases_by_type(self, case_type: str):
        """根據類型取得案件"""
        return [case for case in self.cases if hasattr(case, 'case_type') and case.case_type == case_type]

    def get_cases_by_status(self, status: str):
        """根據狀態取得案件"""
        return [case for case in self.cases if hasattr(case, 'status') and case.status == status]

    def search_cases(self, keyword: str, fields=None):
        """搜尋案件"""
        if not keyword:
            return self.cases

        if fields is None:
            fields = ['client', 'case_type', 'case_id', 'notes']

        results = []
        keyword_lower = keyword.lower()

        for case in self.cases:
            for field in fields:
                if hasattr(case, field):
                    field_value = getattr(case, field)
                    if field_value and keyword_lower in str(field_value).lower():
                        results.append(case)
                        break

        return results


class CaseService:
    """案件業務邏輯服務"""

    def __init__(self, data_folder: str, data_file: str = None):
        """
        初始化案件服務

        Args:
            data_folder: 資料資料夾路徑
            data_file: 案件資料檔案路徑
        """
        self.data_folder = data_folder
        self.data_file = data_file or os.path.join(data_folder, "cases.json")

        # 初始化資料存取器
        self.repository = CaseRepository(self.data_file)

        # 延遲初始化其他服務以避免循環依賴
        self.validation_service = None
        self.folder_service = None
        self.notification_service = None

        print("✅ CaseService 初始化完成")

    def _get_validation_service(self):
        """延遲取得驗證服務"""
        if self.validation_service is None:
            try:
                from .validation_service import ValidationService
                self.validation_service = ValidationService()
            except ImportError:
                print("⚠️ ValidationService 不可用")
                self.validation_service = None
        return self.validation_service

    def _get_folder_service(self):
        """延遲取得資料夾服務"""
        if self.folder_service is None:
            try:
                from .folder_service import FolderService
                self.folder_service = FolderService(self.data_folder)
            except ImportError:
                print("⚠️ FolderService 不可用")
                self.folder_service = None
        return self.folder_service

    def _get_notification_service(self):
        """延遲取得通知服務"""
        if self.notification_service is None:
            try:
                from .notification_service import NotificationService
                self.notification_service = NotificationService()
            except ImportError:
                print("⚠️ NotificationService 不可用")
                self.notification_service = None
        return self.notification_service

    # ==================== 核心業務邏輯 ====================

    def create_case(self, case_data: CaseData, create_folder: bool = True) -> Tuple[bool, str]:
        """
        建立新案件（完整業務流程）

        Args:
            case_data: 案件資料
            create_folder: 是否建立資料夾結構

        Returns:
            (成功與否, 訊息)
        """
        try:
            print(f"🏗️ 開始建立案件: {case_data.client}")

            # 1. 業務驗證
            validation_result = self.validate_case_for_creation(case_data)
            if not validation_result[0]:
                return False, f"案件資料驗證失敗: {validation_result[1]}"

            # 2. 生成案件ID（如果沒有）
            if not case_data.case_id:
                case_data.case_id = self.generate_case_id(case_data)

            # 3. 檢查重複
            if self.is_case_duplicate(case_data):
                return False, f"案件已存在: {case_data.case_id}"

            # 4. 設定預設值
            self._set_case_defaults(case_data)

            # 5. 儲存到資料庫
            save_result = self.repository.create_case(case_data)
            if not save_result:
                return False, "案件資料儲存失敗"

            # 6. 建立資料夾結構（如果需要）
            if create_folder:
                folder_result = self.folder_service.create_case_folder_structure(case_data)
                if not folder_result[0]:
                    print(f"⚠️ 警告: 資料夾建立失敗 - {folder_result[1]}")
                    # 不因資料夾建立失敗而中斷整個流程

            # 7. 發送通知
            self.notification_service.notify_case_created(case_data)

            print(f"✅ 成功建立案件: {case_data.case_id}")
            return True, f"成功建立案件: {case_data.client}"

        except Exception as e:
            error_msg = f"建立案件失敗: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg

    def update_case(self, case_data: CaseData, update_folder: bool = False) -> Tuple[bool, str]:
        """
        更新案件（完整業務流程）

        Args:
            case_data: 更新後的案件資料
            update_folder: 是否同步更新資料夾

        Returns:
            (成功與否, 訊息)
        """
        try:
            print(f"🔄 開始更新案件: {case_data.case_id}")

            # 1. 檢查案件是否存在
            existing_case = self.repository.get_case_by_id(case_data.case_id)
            if not existing_case:
                return False, f"案件不存在: {case_data.case_id}"

            # 2. 業務驗證
            validation_result = self.validate_case_for_update(case_data, existing_case)
            if not validation_result[0]:
                return False, f"案件資料驗證失敗: {validation_result[1]}"

            # 3. 設定更新時間
            case_data.last_modified = datetime.now()

            # 4. 更新資料庫
            update_result = self.repository.update_case(case_data)
            if not update_result:
                return False, "案件資料更新失敗"

            # 5. 同步資料夾（如果需要）
            if update_folder:
                folder_sync_result = self.folder_service.sync_case_folder(existing_case, case_data)
                if not folder_sync_result[0]:
                    print(f"⚠️ 警告: 資料夾同步失敗 - {folder_sync_result[1]}")

            # 6. 發送通知
            self.notification_service.notify_case_updated(case_data, existing_case)

            print(f"✅ 成功更新案件: {case_data.case_id}")
            return True, f"成功更新案件: {case_data.client}"

        except Exception as e:
            error_msg = f"更新案件失敗: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg

    def delete_case(self, case_id: str, delete_folder: bool = True, force: bool = False) -> Tuple[bool, str]:
        """
        刪除案件（完整業務流程）

        Args:
            case_id: 案件ID
            delete_folder: 是否刪除資料夾
            force: 是否強制刪除

        Returns:
            (成功與否, 訊息)
        """
        try:
            print(f"🗑️ 開始刪除案件: {case_id}")

            # 1. 檢查案件是否存在
            case_data = self.repository.get_case_by_id(case_id)
            if not case_data:
                return False, f"案件不存在: {case_id}"

            # 2. 業務驗證（檢查是否可以刪除）
            can_delete, reason = self.validate_case_for_deletion(case_data, force)
            if not can_delete:
                return False, f"無法刪除案件: {reason}"

            # 3. 刪除相關資料夾（如果需要）
            if delete_folder:
                folder_delete_result = self.folder_service.delete_case_folder(case_data)
                if not folder_delete_result[0]:
                    if not force:
                        return False, f"資料夾刪除失敗: {folder_delete_result[1]}"
                    else:
                        print(f"⚠️ 警告: 強制模式 - 忽略資料夾刪除失敗")

            # 4. 刪除資料庫記錄
            delete_result = self.repository.delete_case(case_id)
            if not delete_result:
                return False, "案件資料刪除失敗"

            # 5. 發送通知
            self.notification_service.notify_case_deleted(case_data)

            print(f"✅ 成功刪除案件: {case_id}")
            return True, f"成功刪除案件: {case_data.client}"

        except Exception as e:
            error_msg = f"刪除案件失敗: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg

    # ==================== 查詢業務邏輯 ====================

    def get_case_by_id(self, case_id: str) -> Optional[CaseData]:
        """根據ID取得案件"""
        return self.repository.get_case_by_id(case_id)

    def get_cases_by_client(self, client_name: str) -> List[CaseData]:
        """根據當事人姓名取得案件列表"""
        return self.repository.get_cases_by_client(client_name)

    def get_cases_by_type(self, case_type: str) -> List[CaseData]:
        """根據案件類型取得案件列表"""
        return self.repository.get_cases_by_type(case_type)

    def get_cases_by_status(self, status: str) -> List[CaseData]:
        """根據案件狀態取得案件列表"""
        return self.repository.get_cases_by_status(status)

    def search_cases(self, keyword: str, fields: List[str] = None) -> List[CaseData]:
        """
        搜尋案件

        Args:
            keyword: 搜尋關鍵字
            fields: 要搜尋的欄位列表

        Returns:
            符合條件的案件列表
        """
        if fields is None:
            fields = ['client', 'case_type', 'case_id', 'notes']

        return self.repository.search_cases(keyword, fields)

    def get_urgent_cases(self, days_threshold: int = 7) -> List[CaseData]:
        """
        取得緊急案件（即將到期）

        Args:
            days_threshold: 天數閾值

        Returns:
            緊急案件列表
        """
        all_cases = self.repository.get_all_cases()
        urgent_cases = []

        from datetime import datetime, timedelta
        threshold_date = datetime.now() + timedelta(days=days_threshold)

        for case in all_cases:
            if case.important_dates:
                for date_info in case.important_dates:
                    if date_info.date and date_info.date <= threshold_date:
                        urgent_cases.append(case)
                        break

        return urgent_cases

    # ==================== 業務驗證邏輯 ====================

    def validate_case_for_creation(self, case_data: CaseData) -> Tuple[bool, str]:
        """驗證案件是否可以建立"""
        # 基本資料驗證
        basic_validation = self.validation_service.validate_case_data(case_data)
        if not basic_validation[0]:
            return basic_validation

        # 業務邏輯驗證
        if not case_data.client or case_data.client.strip() == "":
            return False, "當事人姓名不能為空"

        if not case_data.case_type:
            return False, "案件類型不能為空"

        return True, "驗證通過"

    def validate_case_for_update(self, new_data: CaseData, existing_data: CaseData) -> Tuple[bool, str]:
        """驗證案件是否可以更新"""
        # 基本資料驗證
        basic_validation = self.validation_service.validate_case_data(new_data)
        if not basic_validation[0]:
            return basic_validation

        # 業務邏輯驗證
        if new_data.case_id != existing_data.case_id:
            return False, "不能修改案件ID"

        return True, "驗證通過"

    def validate_case_for_deletion(self, case_data: CaseData, force: bool = False) -> Tuple[bool, str]:
        """驗證案件是否可以刪除"""
        if force:
            return True, "強制刪除模式"

        # 檢查是否有進行中的程序
        if case_data.status == "進行中":
            return False, "案件正在進行中，無法刪除"

        # 可以添加更多業務規則
        return True, "可以刪除"

    def is_case_duplicate(self, case_data: CaseData) -> bool:
        """檢查案件是否重複"""
        existing_case = self.repository.get_case_by_id(case_data.case_id)
        return existing_case is not None

    # ==================== 輔助方法 ====================

    def generate_case_id(self, case_data: CaseData) -> str:
        """生成案件ID"""
        # 基於案件類型和時間戳生成ID
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        case_type_code = case_data.case_type[:2].upper() if case_data.case_type else "XX"
        unique_suffix = str(uuid.uuid4())[:8].upper()

        return f"{case_type_code}{timestamp}{unique_suffix}"

    def _set_case_defaults(self, case_data: CaseData):
        """設定案件預設值"""
        if not case_data.creation_date:
            case_data.creation_date = datetime.now()

        if not case_data.status:
            case_data.status = "待處理"

        if not case_data.last_modified:
            case_data.last_modified = datetime.now()

    # ==================== 統計和報告 ====================

    def get_case_statistics(self) -> Dict[str, Any]:
        """取得案件統計資訊"""
        all_cases = self.repository.get_all_cases()

        stats = {
            'total_cases': len(all_cases),
            'by_status': {},
            'by_type': {},
            'urgent_cases': len(self.get_urgent_cases()),
            'recent_cases': 0  # 最近30天建立的案件
        }

        # 統計各狀態的案件數量
        for case in all_cases:
            status = case.status or "未設定"
            stats['by_status'][status] = stats['by_status'].get(status, 0) + 1

            case_type = case.case_type or "未設定"
            stats['by_type'][case_type] = stats['by_type'].get(case_type, 0) + 1

        # 統計最近30天的案件
        from datetime import timedelta
        thirty_days_ago = datetime.now() - timedelta(days=30)
        stats['recent_cases'] = len([
            case for case in all_cases
            if case.creation_date and case.creation_date >= thirty_days_ago
        ])

        return stats

    def get_client_case_summary(self, client_name: str) -> Dict[str, Any]:
        """取得特定當事人的案件摘要"""
        client_cases = self.get_cases_by_client(client_name)

        summary = {
            'client_name': client_name,
            'total_cases': len(client_cases),
            'active_cases': len([c for c in client_cases if c.status == "進行中"]),
            'completed_cases': len([c for c in client_cases if c.status == "已完成"]),
            'case_types': list(set([c.case_type for c in client_cases if c.case_type])),
            'latest_case': max(client_cases, key=lambda x: x.creation_date) if client_cases else None
        }

        return summary