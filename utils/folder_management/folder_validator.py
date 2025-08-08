#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
資料夾驗證器 - 修改版本
負責路徑驗證、安全檢查和名稱清理
🔥 修改：支援「案件編號_當事人」格式的資料夾命名
"""

import os
from typing import Dict, Any, Tuple
from models.case_model import CaseData
from config.settings import AppConfig


class FolderValidator:
    """資料夾驗證和安全檢查工具"""

    # 無效字元定義
    INVALID_CHARS = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']

    # 保留名稱（Windows系統）
    RESERVED_NAMES = [
        'CON', 'PRN', 'AUX', 'NUL',
        'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
        'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
    ]

    def __init__(self):
        """初始化驗證器"""
        pass

    def sanitize_folder_name(self, name: str) -> str:
        """
        清理資料夾名稱中的無效字元

        Args:
            name: 原始名稱

        Returns:
            清理後的安全名稱
        """
        if not name or not isinstance(name, str):
            return "未知案件"

        clean_name = str(name).strip()

        # 移除無效字元
        for char in self.INVALID_CHARS:
            clean_name = clean_name.replace(char, '_')

        # 移除前後空格和點
        clean_name = clean_name.strip(' .')

        # 檢查保留名稱
        if clean_name.upper() in self.RESERVED_NAMES:
            clean_name = f"案件_{clean_name}"

        # 長度限制
        if len(clean_name) > 100:
            clean_name = clean_name[:100]

        # 空名稱處理
        if not clean_name:
            clean_name = "未知案件"

        return clean_name

    def get_safe_case_folder_name(self, case_data: CaseData) -> str:
        """
        🔥 新增：取得安全的案件資料夾名稱（案件編號_當事人格式）

        Args:
            case_data: 案件資料

        Returns:
            str: 安全的資料夾名稱
        """
        try:
            # 清理案件編號
            safe_case_id = self.sanitize_folder_name(case_data.case_id)

            # 清理當事人名稱
            safe_client_name = self.sanitize_folder_name(case_data.client)

            # 組合名稱：案件編號_當事人
            folder_name = f"{safe_case_id}_{safe_client_name}"

            # 確保總長度不超過限制
            if len(folder_name) > 100:
                # 如果太長，縮短當事人名稱部分
                max_client_length = 100 - len(safe_case_id) - 1  # 減去底線長度
                if max_client_length > 10:  # 確保當事人名稱至少有10個字元
                    safe_client_name = safe_client_name[:max_client_length]
                    folder_name = f"{safe_case_id}_{safe_client_name}"
                else:
                    # 如果案件編號太長，直接截斷
                    folder_name = folder_name[:100]

            print(f"🔄 資料夾名稱生成：{case_data.case_id} + {case_data.client} -> {folder_name}")
            return folder_name

        except Exception as e:
            print(f"❌ 生成案件資料夾名稱失敗: {e}")
            # 降級處理
            return self.sanitize_folder_name(f"{case_data.case_id}_{case_data.client}")

    def get_safe_client_name(self, client_name: str) -> str:
        """
        🔥 保留：向後相容的方法，但建議使用 get_safe_case_folder_name
        """
        return self.sanitize_folder_name(client_name)

    def generate_case_folder_patterns(self, case_data: CaseData) -> Tuple[str, list]:
        """
        🔥 新增：生成案件資料夾的查找模式

        Args:
            case_data: 案件資料

        Returns:
            tuple: (新格式名稱, 舊格式可能名稱列表)
        """
        try:
            # 新格式：案件編號_當事人
            new_format = self.get_safe_case_folder_name(case_data)

            # 舊格式：只有當事人名稱（向後相容）
            old_formats = [
                self.get_safe_client_name(case_data.client),
                self.sanitize_folder_name(case_data.client)  # 額外的清理方式
            ]

            # 移除重複項目
            old_formats = list(set(old_formats))

            return new_format, old_formats

        except Exception as e:
            print(f"❌ 生成資料夾模式失敗: {e}")
            safe_client = self.get_safe_client_name(case_data.client)
            return f"{case_data.case_id}_{safe_client}", [safe_client]

    def validate_path(self, path: str) -> tuple[bool, str]:
        """
        驗證路徑的有效性

        Returns:
            (is_valid, error_message)
        """
        if not path:
            return False, "路徑不能為空"

        try:
            # 檢查路徑長度（Windows限制）
            if len(path) > 260:
                return False, "路徑長度超過系統限制"

            # 檢查父目錄是否存在
            parent_dir = os.path.dirname(path)
            if parent_dir and not os.path.exists(parent_dir):
                return False, f"父目錄不存在: {parent_dir}"

            # 檢查寫入權限
            if os.path.exists(path):
                if not os.access(path, os.W_OK):
                    return False, "沒有寫入權限"
            else:
                # 檢查父目錄的寫入權限
                if parent_dir and not os.access(parent_dir, os.W_OK):
                    return False, "父目錄沒有寫入權限"

            return True, ""

        except Exception as e:
            return False, f"路徑驗證失敗: {str(e)}"

    def validate_case_type(self, case_type: str) -> bool:
        """驗證案件類型是否有效"""
        return case_type in AppConfig.CASE_TYPE_FOLDERS

    def check_folder_conflicts(self, base_path: str, folder_name: str) -> tuple[bool, str]:
        """
        檢查資料夾名稱衝突

        Args:
            base_path: 基礎路徑
            folder_name: 資料夾名稱

        Returns:
            (has_conflict, final_name)
        """
        try:
            final_name = folder_name
            counter = 1

            while os.path.exists(os.path.join(base_path, final_name)):
                final_name = f"{folder_name}_{counter}"
                counter += 1

                # 防止無限循環
                if counter > 1000:
                    final_name = f"{folder_name}_{os.getpid()}"
                    break

            has_conflict = (final_name != folder_name)
            return has_conflict, final_name

        except Exception as e:
            print(f"❌ 檢查資料夾衝突失敗: {e}")
            return False, folder_name