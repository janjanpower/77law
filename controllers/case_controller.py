#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
案件控制器 - 重構版本
精簡的控制層，主要負責協調各個服務層
將具體業務邏輯委派給服務層處理
"""

from datetime import datetime
import os
from typing import List, Optional, Tuple, Dict, Any
from models.case_model import CaseData
from config.settings import AppConfig

# 導入服務層
from services.folder_service import FolderService
from services.excel_service import ExcelService
from services.validation_service import ValidationService
from services.notification_service import NotificationService

# 導入原有管理器（過渡期間保留）
from controllers.case_managers.case_data_manager import CaseDataManager
from controllers.case_managers.case_progress_manager import CaseProgressManager


class CaseController:
    """案件控制器 - 重構版本，專注於協調服務層"""

    def __init__(self, data_file: str = None):
        """
        初始化案件控制器

        Args:
            data_file: 資料檔案路徑
        """
        # 初始化基本屬性
        if data_file is None:
            self.data_file = AppConfig.DATA_CONFIG['case_data_file']
        else:
            self.data_file = data_file

        self.data_folder = os.path.dirname(self.data_file) if os.path.dirname(self.data_file) else '.'

        # 初始化服務層
        self._init_services()

        # 初始化管理器（過渡期間保留）
        self._init_managers()

    def _init_services(self, data_folder):
        """初始化服務層"""
        try:
            self.folder_service = FolderService(data_folder)
            self.excel_service = ExcelService()
            self.validation_service = ValidationService()
            self.notification_service = NotificationService(self.data_folder)

            print("✅ 服務層初始化完成")
        except Exception as e:
            print(f"❌ 服務層初始化失敗: {e}")
            raise

    def _init_managers(self):
        """初始化管理器（過渡期間保留）"""
        try:
            self.case_data_manager = CaseDataManager(self.data_file)
            self.progress_manager = CaseProgressManager()

            print("✅ 管理器初始化完成")
        except Exception as e:
            print(f"⚠️ 管理器初始化失敗，使用服務層替代: {e}")
            self.case_data_manager = None
            self.progress_manager = None

    # ====== 案件資料操作 ======

    def create_case(self, case_data):
        success, message = self.folder_service.create_case_folder(case_data)
        return success

    def add_case(self, case_data: CaseData) -> Tuple[bool, str]:
        """
        新增案件

        Args:
            case_data: 案件資料

        Returns:
            (success, message)
        """
        try:
            # 1. 驗證案件資料
            is_valid, errors = self.validation_service.validate_case_data(case_data)
            if not is_valid:
                return False, f"案件資料驗證失敗: {'; '.join(errors)}"

            # 2. 新增到資料管理器
            if self.case_data_manager:
                success, message = self.case_data_manager.add_case(case_data)
                if not success:
                    return False, message

            # 3. 建立資料夾結構
            folder_success, folder_message = self.folder_service.create_case_folder(case_data)
            if not folder_success:
                print(f"⚠️ 資料夾建立失敗: {folder_message}")

            # 4. 建立成功通知
            self.notification_service.create_notification(
                title="案件建立成功",
                message=f"案件 {case_data.client} 已成功建立",
                notification_type="success",
                case_id=case_data.case_id
            )

            return True, f"案件 {case_data.client} 新增成功"

        except Exception as e:
            error_msg = f"新增案件失敗: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg

    def edit_case(self, case_data: CaseData) -> Tuple[bool, str]:
        """
        編輯案件

        Args:
            case_data: 案件資料

        Returns:
            (success, message)
        """
        try:
            # 1. 驗證案件資料
            is_valid, errors = self.validation_service.validate_case_data(case_data)
            if not is_valid:
                return False, f"案件資料驗證失敗: {'; '.join(errors)}"

            # 2. 更新資料管理器
            if self.case_data_manager:
                success, message = self.case_data_manager.update_case(case_data)
                if not success:
                    return False, message

            # 3. 建立更新通知
            self.notification_service.create_notification(
                title="案件更新",
                message=f"案件 {case_data.client} 資訊已更新",
                notification_type="info",
                case_id=case_data.case_id
            )

            return True, f"案件 {case_data.client} 更新成功"

        except Exception as e:
            error_msg = f"編輯案件失敗: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg

    def delete_case(self, case_data: CaseData, delete_folder: bool = False) -> Tuple[bool, str]:
        """
        刪除案件

        Args:
            case_data: 案件資料
            delete_folder: 是否同時刪除資料夾

        Returns:
            (success, message)
        """
        try:
            # 1. 從資料管理器刪除
            if self.case_data_manager:
                success, message = self.case_data_manager.delete_case(case_data.case_id)
                if not success:
                    return False, message

            # 2. 刪除資料夾（如果需要）
            if delete_folder:
                folder_success, folder_message = self.folder_service.delete_case_folder(
                    case_data, confirm=True
                )
                if not folder_success:
                    print(f"⚠️ 資料夾刪除失敗: {folder_message}")

            # 3. 建立刪除通知
            self.notification_service.create_notification(
                title="案件刪除",
                message=f"案件 {case_data.client} 已刪除",
                notification_type="warning"
            )

            return True, f"案件 {case_data.client} 刪除成功"

        except Exception as e:
            error_msg = f"刪除案件失敗: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg

    def get_all_cases(self) -> List[CaseData]:
        """取得所有案件"""
        try:
            if self.case_data_manager:
                return self.case_data_manager.get_all_cases()
            return []
        except Exception as e:
            print(f"❌ 取得案件列表失敗: {e}")
            return []

    def generate_case_id(self, case_type: str) -> str:
        """
        生成案件編號 - 修正版本：民國年+流水號格式

        格式：民國年份 + 3位流水號
        例如：113001 (民國113年第1號案件)

        Args:
            case_type: 案件類型

        Returns:
            str: 生成的案件編號
        """
        try:
            # 取得當前民國年份
            current_year = datetime.now().year
            roc_year = current_year - 1911  # 轉換為民國年

            # 取得同年同類型的現有案件
            same_year_type_cases = [
                case for case in self.cases
                if case.case_type == case_type and
                case.case_id and
                case.case_id.startswith(str(roc_year))
            ]

            # 找出最大的流水號
            max_num = 0
            for case in same_year_type_cases:
                if case.case_id and len(case.case_id) >= 6:  # 民國年(3位) + 流水號(3位)
                    try:
                        # 提取流水號部分
                        num_part = case.case_id[3:]  # 跳過民國年份的3位數
                        if num_part.isdigit():
                            num = int(num_part)
                            max_num = max(max_num, num)
                    except (ValueError, IndexError):
                        continue

            # 生成新編號
            new_num = max_num + 1
            new_case_id = f"{roc_year:03d}{new_num:03d}"

            print(f"為 {case_type} 類型生成新案件編號: {new_case_id} (民國{roc_year}年第{new_num}號)")
            return new_case_id

        except Exception as e:
            print(f"生成案件編號失敗: {e}")
            # 使用時間戳作為備用方案
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            return f"ERR{timestamp}"

    # ====== 進度管理 ======

    def update_case_progress(self, case_data: CaseData, new_progress: str,
                           progress_date=None, notes: str = "") -> Tuple[bool, str]:
        """
        更新案件進度

        Args:
            case_data: 案件資料
            new_progress: 新進度
            progress_date: 進度日期
            notes: 備註

        Returns:
            (success, message)
        """
        try:
            old_progress = case_data.progress

            # 1. 使用進度管理器更新
            if self.progress_manager:
                success, message = self.progress_manager.update_progress(
                    case_data, new_progress, progress_date, notes
                )
                if not success:
                    return False, message

            # 2. 建立進度資料夾
            if new_progress:
                folder_success, folder_message = self.folder_service.create_progress_folder(
                    case_data, new_progress
                )
                if not folder_success:
                    print(f"⚠️ 進度資料夾建立失敗: {folder_message}")

            # 3. 建立進度更新通知
            if old_progress != new_progress:
                self.notification_service.create_progress_notification(
                    case_data, old_progress or "無", new_progress
                )

            return True, f"案件 {case_data.client} 進度已更新為: {new_progress}"

        except Exception as e:
            error_msg = f"更新進度失敗: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg

    # ====== Excel操作 ======

    def import_cases_from_excel(self, file_path: str, sheet_name: str = None) -> Tuple[bool, str, List[CaseData]]:
        """
        從Excel匯入案件

        Args:
            file_path: Excel檔案路徑
            sheet_name: 工作表名稱

        Returns:
            (success, message, cases_list)
        """
        try:
            # 1. 驗證Excel檔案
            is_valid, error_msg = self.validation_service.validate_excel_file(file_path)
            if not is_valid:
                return False, error_msg, []

            # 2. 使用Excel服務匯入
            success, message, cases = self.excel_service.import_cases_from_excel(file_path, sheet_name)
            if not success:
                return False, message, []

            # 3. 批次驗證案件資料
            validation_result = self.validation_service.batch_validate_cases(cases)

            if validation_result['invalid'] > 0:
                print(f"⚠️ 發現 {validation_result['invalid']} 筆無效資料")

            # 4. 建立匯入通知
            self.notification_service.create_notification(
                title="Excel匯入完成",
                message=f"成功匯入 {len(cases)} 筆案件資料",
                notification_type="success"
            )

            return True, f"成功匯入 {len(cases)} 筆案件", cases

        except Exception as e:
            error_msg = f"匯入Excel失敗: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg, []

    def export_cases_to_excel(self, cases: List[CaseData], file_path: str) -> Tuple[bool, str]:
        """
        匯出案件到Excel

        Args:
            cases: 案件列表
            file_path: 匯出檔案路徑

        Returns:
            (success, message)
        """
        try:
            success, message = self.excel_service.export_cases_to_excel(cases, file_path)

            if success:
                self.notification_service.create_notification(
                    title="Excel匯出完成",
                    message=f"成功匯出 {len(cases)} 筆案件資料",
                    notification_type="success"
                )

            return success, message

        except Exception as e:
            error_msg = f"匯出Excel失敗: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg

    # ====== 資料夾操作 ======

    def create_case_folder_structure(self, case_data: CaseData) -> Tuple[bool, str]:
        """建立案件資料夾結構"""
        return self.folder_service.create_case_folder(case_data)

    def get_case_folder_path(self, case_data: CaseData) -> Optional[str]:
        """取得案件資料夾路徑"""
        return self.folder_service.get_case_folder_path(case_data)

    def batch_create_folders(self, cases: List[CaseData]) -> Dict[str, Any]:
        """批次建立資料夾"""
        return self.folder_service.batch_create_case_folders(cases)

    # ====== 通知管理 ======

    def get_urgent_notifications(self) -> List[Dict[str, Any]]:
        """取得緊急通知"""
        return self.notification_service.get_urgent_notifications()

    def check_case_reminders(self, cases: List[CaseData]) -> List[str]:
        """檢查案件提醒"""
        return self.notification_service.check_case_reminders(cases)

    def get_notification_stats(self) -> Dict[str, Any]:
        """取得通知統計"""
        return self.notification_service.get_notification_stats()

    # ====== 工具方法 ======

    def validate_case_data(self, case_data: CaseData) -> Tuple[bool, List[str]]:
        """驗證案件資料"""
        return self.validation_service.validate_case_data(case_data)

    def get_dependency_status(self) -> Dict[str, bool]:
        """取得依賴狀態"""
        return self.excel_service.get_dependency_status()

    def cleanup_old_data(self, days_to_keep: int = 30) -> Dict[str, int]:
        """清理舊資料"""
        try:
            notifications_cleaned = self.notification_service.cleanup_old_notifications(days_to_keep)
            auto_dismissed = self.notification_service.auto_dismiss_expired_notifications()

            return {
                'notifications_cleaned': notifications_cleaned,
                'auto_dismissed': auto_dismissed
            }
        except Exception as e:
            print(f"❌ 清理舊資料失敗: {e}")
            return {'notifications_cleaned': 0, 'auto_dismissed': 0}