#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
資料夾驗證器
負責路徑驗證、安全檢查和名稱清理
"""

import os
from typing import Dict, Any

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

    def get_safe_client_name(self, client_name: str) -> str:
        """取得安全的當事人名稱"""
        return self.sanitize_folder_name(client_name)

    def check_folder_conflicts(self, base_path: str, folder_name: str) -> tuple[bool, str]:
        """
        檢查資料夾名稱衝突

        Returns:
            (has_conflict, suggested_name)
        """
        full_path = os.path.join(base_path, folder_name)

        if not os.path.exists(full_path):
            return False, folder_name

        # 產生不衝突的名稱
        counter = 1
        while True:
            suggested_name = f"{folder_name}_{counter}"
            suggested_path = os.path.join(base_path, suggested_name)

            if not os.path.exists(suggested_path):
                return True, suggested_name

            counter += 1
            if counter > 100:  # 防止無限循環
                break

        return True, f"{folder_name}_{counter}"

    def validate_folder_structure(self, folder_path: str) -> Dict[str, Any]:
        """
        驗證資料夾結構完整性

        Returns:
            驗證結果字典
        """
        result = {
            'is_valid': True,
            'missing_folders': [],
            'errors': [],
            'warnings': []
        }

        try:
            if not os.path.exists(folder_path):
                result['is_valid'] = False
                result['errors'].append(f"主資料夾不存在: {folder_path}")
                return result

            # 檢查必要的子資料夾
            required_subfolders = ['狀紙', '進度追蹤', '案件資訊']

            for subfolder in required_subfolders:
                subfolder_path = os.path.join(folder_path, subfolder)
                if not os.path.exists(subfolder_path):
                    result['missing_folders'].append(subfolder)
                    result['warnings'].append(f"缺少子資料夾: {subfolder}")

            # 檢查案件資訊Excel
            case_info_folder = os.path.join(folder_path, '案件資訊')
            if os.path.exists(case_info_folder):
                excel_files = [f for f in os.listdir(case_info_folder) if f.endswith('.xlsx')]
                if not excel_files:
                    result['warnings'].append("案件資訊資料夾中沒有Excel檔案")

            if result['missing_folders']:
                result['is_valid'] = False

        except Exception as e:
            result['is_valid'] = False
            result['errors'].append(f"驗證過程發生錯誤: {str(e)}")

        return result

    def get_folder_size_info(self, folder_path: str) -> Dict[str, Any]:
        """
        取得資料夾大小資訊

        Returns:
            包含檔案數量和大小的字典
        """
        info = {
            'exists': False,
            'file_count': 0,
            'total_size_bytes': 0,
            'total_size_mb': 0.0,
            'has_files': False
        }

        try:
            if not os.path.exists(folder_path):
                return info

            info['exists'] = True
            total_files = 0
            total_size = 0

            for root, dirs, files in os.walk(folder_path):
                total_files += len(files)
                for file in files:
                    try:
                        file_path = os.path.join(root, file)
                        total_size += os.path.getsize(file_path)
                    except (OSError, IOError):
                        continue  # 跳過無法讀取的檔案

            info.update({
                'file_count': total_files,
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'has_files': total_files > 0
            })

        except Exception as e:
            print(f"計算資料夾大小時發生錯誤: {e}")

        return info