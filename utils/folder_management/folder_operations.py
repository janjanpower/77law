#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
資料夾操作管理器 - 修改版本
🔥 修改：支援新舊格式資料夾的查找和管理
"""

import os
import shutil
from typing import Optional, List, Dict, Any
from models.case_model import CaseData
from config.settings import AppConfig
from .folder_validator import FolderValidator


class FolderOperations:
    """資料夾操作管理工具"""

    def __init__(self, base_data_folder: str):
        """
        初始化資料夾操作管理器

        Args:
            base_data_folder: 基礎資料資料夾路徑
        """
        self.base_data_folder = base_data_folder
        self.validator = FolderValidator()

    def get_case_folder_path(self, case_data: CaseData, strict: bool = False) -> Optional[str]:
        """
        🔥 修改：取得案件的資料夾路徑（支援新舊格式查找）

        Args:
            case_data: 案件資料

        Returns:
            資料夾路徑或None
        """
        try:
            case_type_folder = self._get_case_type_folder_path(case_data.case_type)
            if not case_type_folder:
                return None

            # 🔥 新增：使用新的查找邏輯
            return self._find_case_folder_with_patterns(case_type_folder, case_data)

        except Exception as e:
            print(f"❌ 取得案件資料夾路徑失敗: {e}")
            return None

    def _find_case_folder_with_patterns(self, case_type_folder: str, case_data: CaseData) -> Optional[str]:
        """
        🔥 新增：使用多種模式查找案件資料夾

        Args:
            case_type_folder: 案件類型資料夾路徑
            case_data: 案件資料

        Returns:
            找到的資料夾路徑或None
        """
        try:
            if not os.path.exists(case_type_folder):
                return None

            # 取得新舊格式的資料夾名稱模式
            new_format, old_formats = self.validator.generate_case_folder_patterns(case_data)

            # 優先查找新格式
            new_folder_path = os.path.join(case_type_folder, new_format)
            if os.path.exists(new_folder_path):
                print(f"✅ 找到新格式資料夾: {new_format}")
                return new_folder_path

            # 查找舊格式（向後相容）
            for old_format in old_formats:
                old_folder_path = os.path.join(case_type_folder, old_format)
                if os.path.exists(old_folder_path):
                    print(f"⚠️ 找到舊格式資料夾: {old_format}")
                    print(f"💡 建議遷移到新格式: {new_format}")
                    return old_folder_path

            # 🔥 新增：模糊搜尋（包含案件編號或當事人名稱的資料夾）
            fuzzy_path = self._fuzzy_search_case_folder(case_type_folder, case_data)
            if fuzzy_path:
                print(f"🔍 模糊搜尋找到資料夾: {os.path.basename(fuzzy_path)}")
                return fuzzy_path

            print(f"❌ 未找到案件資料夾: {case_data.case_id} - {case_data.client}")
            return None

        except Exception as e:
            print(f"❌ 查找案件資料夾失敗: {e}")
            return None

    def _fuzzy_search_case_folder(self, case_type_folder: str, case_data: CaseData) -> Optional[str]:
        """
        🔥 新增：模糊搜尋案件資料夾

        Args:
            case_type_folder: 案件類型資料夾路徑
            case_data: 案件資料

        Returns:
            找到的資料夾路徑或None
        """
        try:
            if not os.path.exists(case_type_folder):
                return None

            case_id = case_data.case_id.lower()
            client_name = case_data.client.lower()

            # 遍歷資料夾，尋找包含案件編號或當事人名稱的資料夾
            for folder_name in os.listdir(case_type_folder):
                folder_path = os.path.join(case_type_folder, folder_name)
                if not os.path.isdir(folder_path):
                    continue

                folder_name_lower = folder_name.lower()

                # 檢查是否包含案件編號
                if case_id in folder_name_lower:
                    return folder_path

                # 檢查是否包含當事人名稱
                if client_name in folder_name_lower:
                    return folder_path

            return None

        except Exception as e:
            print(f"❌ 模糊搜尋失敗: {e}")
            return None

    def get_stage_folder_path(self, case_data: CaseData, stage_name: str) -> Optional[str]:
        """
        取得特定階段的資料夾路徑

        Args:
            case_data: 案件資料
            stage_name: 階段名稱

        Returns:
            階段資料夾路徑或None
        """
        try:
            case_folder = self.get_case_folder_path(case_data)
            if not case_folder:
                return None

            safe_stage_name = self.validator.sanitize_folder_name(stage_name)
            stage_folder_path = os.path.join(case_folder, '進度追蹤', safe_stage_name)

            return stage_folder_path if os.path.exists(stage_folder_path) else None

        except Exception as e:
            print(f"❌ 取得階段資料夾路徑失敗: {e}")
            return None

    def delete_case_folder(self, case_data: CaseData, confirm: bool = False) -> tuple[bool, str]:
        """
        刪除案件的整個案件資料夾

        Args:
            case_data: 案件資料
            confirm: 是否已確認刪除

        Returns:
            (success, message)
        """
        try:
            case_folder = self.get_case_folder_path(case_data)
            if not case_folder:
                return False, f"找不到案件資料夾: {case_data.case_id} - {case_data.client}"

            if not os.path.exists(case_folder):
                return False, f"案件資料夾不存在: {case_folder}"

            if not confirm:
                return False, "請確認是否要刪除案件資料夾"

            # 取得資料夾資訊用於日誌
            folder_info = self._get_folder_info(case_folder)

            # 刪除整個資料夾及其內容
            shutil.rmtree(case_folder)

            message = f"✅ 已刪除案件資料夾: {os.path.basename(case_folder)}"
            if folder_info['file_count'] > 0:
                message += f" (包含 {folder_info['file_count']} 個檔案)"

            print(message)
            return True, message

        except Exception as e:
            error_msg = f"刪除案件資料夾失敗: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg

    def migrate_folder_to_new_format(self, case_data: CaseData) -> tuple[bool, str]:
        """
        🔥 新增：將舊格式資料夾遷移到新格式

        Args:
            case_data: 案件資料

        Returns:
            (success, message)
        """
        try:
            case_type_folder = self._get_case_type_folder_path(case_data.case_type)
            if not case_type_folder:
                return False, f"找不到案件類型資料夾: {case_data.case_type}"

            # 取得新舊格式的資料夾名稱
            new_format, old_formats = self.validator.generate_case_folder_patterns(case_data)

            # 檢查新格式資料夾是否已存在
            new_folder_path = os.path.join(case_type_folder, new_format)
            if os.path.exists(new_folder_path):
                return False, f"新格式資料夾已存在: {new_format}"

            # 尋找舊格式資料夾
            old_folder_path = None
            old_format_found = None

            for old_format in old_formats:
                temp_path = os.path.join(case_type_folder, old_format)
                if os.path.exists(temp_path):
                    old_folder_path = temp_path
                    old_format_found = old_format
                    break

            if not old_folder_path:
                return False, "找不到需要遷移的舊格式資料夾"

            # 執行遷移（重新命名資料夾）
            os.rename(old_folder_path, new_folder_path)

            message = f"✅ 成功遷移資料夾格式: {old_format_found} -> {new_format}"
            print(message)
            return True, message

        except Exception as e:
            error_msg = f"資料夾遷移失敗: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg

    def list_all_case_folders(self, case_type: str) -> List[Dict[str, Any]]:
        """
        🔥 新增：列出指定案件類型的所有案件資料夾

        Args:
            case_type: 案件類型

        Returns:
            資料夾資訊列表
        """
        try:
            case_type_folder = self._get_case_type_folder_path(case_type)
            if not case_type_folder or not os.path.exists(case_type_folder):
                return []

            folder_list = []

            for item in os.listdir(case_type_folder):
                item_path = os.path.join(case_type_folder, item)
                if os.path.isdir(item_path):
                    folder_info = self._get_folder_info(item_path)
                    folder_info['name'] = item
                    folder_info['format'] = self._detect_folder_format(item)
                    folder_list.append(folder_info)

            return folder_list

        except Exception as e:
            print(f"❌ 列出案件資料夾失敗: {e}")
            return []

    def _detect_folder_format(self, folder_name: str) -> str:
        """
        🔥 新增：檢測資料夾格式

        Args:
            folder_name: 資料夾名稱

        Returns:
            格式類型: 'new', 'old', 'unknown'
        """
        try:
            # 新格式檢測：包含底線分隔符
            if '_' in folder_name:
                parts = folder_name.split('_', 1)
                if len(parts) == 2 and parts[0] and parts[1]:
                    return 'new'

            return 'old'

        except Exception:
            return 'unknown'

    def _get_folder_info(self, folder_path: str) -> Dict[str, Any]:
        """
        取得資料夾詳細資訊

        Args:
            folder_path: 資料夾路徑

        Returns:
            資料夾資訊字典
        """
        try:
            if not os.path.exists(folder_path):
                return {
                    'exists': False,
                    'path': folder_path,
                    'file_count': 0,
                    'size_mb': 0,
                    'last_modified': None
                }

            file_count = 0
            total_size = 0
            last_modified = os.path.getmtime(folder_path)

            # 遞歸計算檔案數量和大小
            for root, dirs, files in os.walk(folder_path):
                file_count += len(files)
                for file in files:
                    try:
                        file_path = os.path.join(root, file)
                        total_size += os.path.getsize(file_path)
                        file_modified = os.path.getmtime(file_path)
                        if file_modified > last_modified:
                            last_modified = file_modified
                    except (OSError, FileNotFoundError):
                        continue

            return {
                'exists': True,
                'path': folder_path,
                'file_count': file_count,
                'size_mb': round(total_size / (1024 * 1024), 2),
                'last_modified': last_modified
            }

        except Exception as e:
            print(f"❌ 取得資料夾資訊失敗: {e}")
            return {
                'exists': False,
                'path': folder_path,
                'file_count': 0,
                'size_mb': 0,
                'last_modified': None
            }

    def _get_case_type_folder_path(self, case_type: str) -> Optional[str]:
        """
        取得案件類型資料夾路徑

        Args:
            case_type: 案件類型

        Returns:
            資料夾路徑或None
        """
        try:
            if not self.validator.validate_case_type(case_type):
                return None

            folder_name = AppConfig.CASE_TYPE_FOLDERS.get(case_type)
            if not folder_name:
                return None

            return os.path.join(self.base_data_folder, folder_name)

        except Exception as e:
            print(f"❌ 取得案件類型資料夾路徑失敗: {e}")
            return None