#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
資料夾管理器 - 重構版本
整合 folder_management 中的所有資料夾操作功能
保持100%功能完整性並提供統一介面
"""

import os
import shutil
from typing import Optional, List, Dict, Any, Tuple
from models.case_model import CaseData
from config.settings import AppConfig


class FolderManager:
    """資料夾管理核心類別 - 統一所有資料夾操作功能"""

    def __init__(self, base_data_folder: str):
        """
        初始化資料夾管理器

        Args:
            base_data_folder: 基礎資料資料夾路徑
        """
        self.base_data_folder = base_data_folder
        self._ensure_base_folder()

    def _ensure_base_folder(self):
        """確保基礎資料夾存在"""
        if not os.path.exists(self.base_data_folder):
            os.makedirs(self.base_data_folder, exist_ok=True)
            print(f"✅ 建立基礎資料夾: {self.base_data_folder}")

    # ==================== 主要資料夾建立功能 ====================

    def create_case_folder_structure(self, case_data: CaseData) -> bool:
        """
        為案件建立完整的資料夾結構（主要介面）

        Args:
            case_data: 案件資料

        Returns:
            建立是否成功
        """
        try:
            print(f"🏗️ 開始為案件 {case_data.case_id} 建立資料夾結構")
            print(f"   當事人: {case_data.client}")
            print(f"   案件類型: {case_data.case_type}")

            # 1. 取得案件類型對應的資料夾
            case_type_folder = self._get_or_create_case_type_folder(case_data.case_type)
            if not case_type_folder:
                print(f"❌ 未知的案件類型: {case_data.case_type}")
                return False

            # 2. 建立當事人資料夾
            client_folder = self._create_client_folder(case_type_folder, case_data.client)
            if not client_folder:
                print(f"❌ 建立當事人資料夾失敗: {case_data.client}")
                return False

            # 3. 建立子資料夾結構
            sub_folders = self._create_sub_folders(client_folder)
            if not sub_folders:
                print(f"❌ 建立子資料夾結構失敗")
                return False

            # 4. 建立現有的進度階段資料夾
            if case_data.progress_stages:
                progress_success = self._create_progress_folders(
                    sub_folders.get('進度追蹤', ''),
                    case_data.progress_stages
                )
                if not progress_success:
                    print("⚠️ 警告：部分進度資料夾建立失敗")

            print(f"✅ 成功為案件 {case_data.case_id} 建立完整資料夾結構")
            print(f"📁 路徑: {client_folder}")
            return True

        except Exception as e:
            print(f"❌ 建立案件資料夾結構失敗: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def _get_or_create_case_type_folder(self, case_type: str) -> Optional[str]:
        """
        取得或建立案件類型資料夾

        Args:
            case_type: 案件類型

        Returns:
            資料夾路徑或None
        """
        try:
            folder_name = AppConfig.CASE_TYPE_FOLDERS.get(case_type)
            if not folder_name:
                print(f"❌ 未知的案件類型: {case_type}")
                return None

            case_type_path = os.path.join(self.base_data_folder, folder_name)

            if not os.path.exists(case_type_path):
                os.makedirs(case_type_path, exist_ok=True)
                print(f"📁 建立案件類型資料夾: {case_type_path}")

            return case_type_path

        except Exception as e:
            print(f"❌ 取得案件類型資料夾失敗: {e}")
            return None

    def _create_client_folder(self, case_type_folder: str, client_name: str) -> Optional[str]:
        """
        建立當事人資料夾

        Args:
            case_type_folder: 案件類型資料夾路徑
            client_name: 當事人姓名

        Returns:
            當事人資料夾路徑或None
        """
        try:
            safe_client_name = self._sanitize_folder_name(client_name)
            client_folder_path = os.path.join(case_type_folder, safe_client_name)

            if not os.path.exists(client_folder_path):
                os.makedirs(client_folder_path, exist_ok=True)
                print(f"📁 建立當事人資料夾: {safe_client_name}")

            return client_folder_path

        except Exception as e:
            print(f"❌ 建立當事人資料夾失敗: {e}")
            return None

    def _create_sub_folders(self, client_folder: str) -> Optional[Dict[str, str]]:
        """
        建立子資料夾結構

        Args:
            client_folder: 當事人資料夾路徑

        Returns:
            子資料夾字典或None
        """
        try:
            sub_folder_names = ['狀紙', '進度追蹤', '案件資訊']
            created_folders = {}

            for folder_name in sub_folder_names:
                folder_path = os.path.join(client_folder, folder_name)

                if not os.path.exists(folder_path):
                    os.makedirs(folder_path, exist_ok=True)
                    print(f"  📁 建立子資料夾: {folder_name}")

                created_folders[folder_name] = folder_path

            return created_folders

        except Exception as e:
            print(f"❌ 建立子資料夾失敗: {e}")
            return None

    def _create_progress_folders(self, progress_base_folder: str, progress_stages: dict) -> bool:
        """
        建立進度階段資料夾

        Args:
            progress_base_folder: 進度追蹤基礎資料夾路徑
            progress_stages: 進度階段字典

        Returns:
            建立是否成功
        """
        try:
            if not progress_stages:
                return True

            for stage_name in progress_stages.keys():
                safe_stage_name = self._sanitize_folder_name(stage_name)
                stage_folder_path = os.path.join(progress_base_folder, safe_stage_name)

                if not os.path.exists(stage_folder_path):
                    os.makedirs(stage_folder_path, exist_ok=True)
                    print(f"    📁 建立進度資料夾: {safe_stage_name}")

            return True

        except Exception as e:
            print(f"❌ 建立進度資料夾失敗: {e}")
            return False

    # ==================== 資料夾查詢功能 ====================

    def get_case_folder_path(self, case_data: CaseData) -> Optional[str]:
        """
        取得案件的資料夾路徑

        Args:
            case_data: 案件資料

        Returns:
            資料夾路徑或None
        """
        try:
            case_type_folder = self._get_case_type_folder_path(case_data.case_type)
            if not case_type_folder:
                return None

            safe_client_name = self._sanitize_folder_name(case_data.client)
            client_folder = os.path.join(case_type_folder, safe_client_name)

            return client_folder if os.path.exists(client_folder) else None

        except Exception as e:
            print(f"❌ 取得案件資料夾路徑失敗: {e}")
            return None

    def _get_case_type_folder_path(self, case_type: str) -> Optional[str]:
        """取得案件類型資料夾路徑（不建立）"""
        try:
            folder_name = AppConfig.CASE_TYPE_FOLDERS.get(case_type)
            if not folder_name:
                return None

            case_type_path = os.path.join(self.base_data_folder, folder_name)
            return case_type_path if os.path.exists(case_type_path) else None

        except Exception as e:
            print(f"❌ 取得案件類型資料夾路徑失敗: {e}")
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

            safe_stage_name = self._sanitize_folder_name(stage_name)
            stage_folder_path = os.path.join(case_folder, '進度追蹤', safe_stage_name)

            return stage_folder_path if os.path.exists(stage_folder_path) else None

        except Exception as e:
            print(f"❌ 取得階段資料夾路徑失敗: {e}")
            return None

    # ==================== 進度階段管理功能 ====================

    def create_progress_folder(self, case_data: CaseData, stage_name: str) -> bool:
        """
        為案件建立特定進度階段資料夾

        Args:
            case_data: 案件資料
            stage_name: 階段名稱

        Returns:
            建立是否成功
        """
        try:
            case_folder = self.get_case_folder_path(case_data)
            if not case_folder:
                print(f"❌ 找不到案件資料夾: {case_data.client}")
                return False

            progress_base_folder = os.path.join(case_folder, '進度追蹤')
            if not os.path.exists(progress_base_folder):
                os.makedirs(progress_base_folder, exist_ok=True)

            safe_stage_name = self._sanitize_folder_name(stage_name)
            stage_folder_path = os.path.join(progress_base_folder, safe_stage_name)

            if not os.path.exists(stage_folder_path):
                os.makedirs(stage_folder_path, exist_ok=True)
                print(f"✅ 建立進度資料夾: {safe_stage_name}")

            return True

        except Exception as e:
            print(f"❌ 建立進度資料夾失敗: {e}")
            return False

    def delete_progress_folder(self, case_data: CaseData, stage_name: str) -> bool:
        """
        刪除案件的特定進度階段資料夾

        Args:
            case_data: 案件資料
            stage_name: 階段名稱

        Returns:
            刪除是否成功
        """
        try:
            case_folder = self.get_case_folder_path(case_data)
            if not case_folder:
                print(f"❌ 找不到案件資料夾: {case_data.client}")
                return False

            safe_stage_name = self._sanitize_folder_name(stage_name)
            stage_folder_path = os.path.join(case_folder, '進度追蹤', safe_stage_name)

            if os.path.exists(stage_folder_path):
                # 檢查資料夾是否為空
                if os.listdir(stage_folder_path):
                    print(f"⚠️ 警告：階段資料夾 {stage_name} 內含檔案，將一併刪除")

                # 刪除整個資料夾及其內容
                shutil.rmtree(stage_folder_path)
                print(f"✅ 已刪除階段資料夾: {stage_name}")
                return True
            else:
                print(f"⚠️ 階段資料夾不存在: {stage_name}")
                return False

        except Exception as e:
            print(f"❌ 刪除階段資料夾失敗: {e}")
            return False

    # ==================== 資料夾操作功能 ====================

    def delete_case_folder(self, case_data: CaseData, confirm: bool = False) -> Tuple[bool, str]:
        """
        刪除案件的整個當事人資料夾

        Args:
            case_data: 案件資料
            confirm: 是否已確認刪除

        Returns:
            (success, message)
        """
        try:
            case_folder = self.get_case_folder_path(case_data)
            if not case_folder:
                return False, f"找不到案件資料夾: {case_data.client}"

            if not os.path.exists(case_folder):
                return False, f"案件資料夾不存在: {case_folder}"

            if not confirm:
                return False, "需要確認刪除操作"

            # 取得資料夾資訊用於日誌
            folder_info = self.get_case_folder_info(case_data)

            # 刪除整個資料夾
            shutil.rmtree(case_folder)

            message = f"已刪除案件資料夾: {case_data.client}"
            if folder_info.get('file_count', 0) > 0:
                message += f" (包含 {folder_info['file_count']} 個檔案)"

            print(f"✅ {message}")
            return True, message

        except Exception as e:
            error_msg = f"刪除案件資料夾失敗: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg

    def get_case_folder_info(self, case_data: CaseData) -> Dict[str, Any]:
        """
        取得案件資料夾資訊（用於刪除前檢查）

        Args:
            case_data: 案件資料

        Returns:
            資料夾資訊字典
        """
        case_folder = self.get_case_folder_path(case_data)

        if not case_folder or not os.path.exists(case_folder):
            return {
                'exists': False,
                'path': case_folder,
                'has_files': False,
                'file_count': 0,
                'size_mb': 0.0
            }

        try:
            # 計算資料夾大小和檔案數量
            total_files = 0
            total_size = 0

            for root, dirs, files in os.walk(case_folder):
                total_files += len(files)
                for file in files:
                    try:
                        file_path = os.path.join(root, file)
                        total_size += os.path.getsize(file_path)
                    except:
                        pass

            return {
                'exists': True,
                'path': case_folder,
                'has_files': total_files > 0,
                'file_count': total_files,
                'size_mb': round(total_size / (1024 * 1024), 2)
            }

        except Exception as e:
            print(f"❌ 取得案件資料夾資訊失敗: {e}")
            return {
                'exists': False,
                'path': case_folder,
                'has_files': False,
                'file_count': 0,
                'size_mb': 0.0
            }

    # ==================== 驗證功能 ====================

    def validate_folder_structure(self, case_data: CaseData) -> Dict[str, Any]:
        """
        驗證案件資料夾結構完整性

        Args:
            case_data: 案件資料

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
            case_folder = self.get_case_folder_path(case_data)
            if not case_folder or not os.path.exists(case_folder):
                result['is_valid'] = False
                result['errors'].append(f"主資料夾不存在: {case_data.client}")
                return result

            # 檢查必要的子資料夾
            required_subfolders = ['狀紙', '進度追蹤', '案件資訊']

            for subfolder in required_subfolders:
                subfolder_path = os.path.join(case_folder, subfolder)
                if not os.path.exists(subfolder_path):
                    result['missing_folders'].append(subfolder)
                    result['warnings'].append(f"缺少子資料夾: {subfolder}")

            # 檢查進度資料夾
            if case_data.progress_stages:
                progress_folder = os.path.join(case_folder, '進度追蹤')
                for stage_name in case_data.progress_stages.keys():
                    safe_stage_name = self._sanitize_folder_name(stage_name)
                    stage_path = os.path.join(progress_folder, safe_stage_name)
                    if not os.path.exists(stage_path):
                        result['warnings'].append(f"缺少進度階段資料夾: {stage_name}")

            if result['missing_folders'] or result['errors']:
                result['is_valid'] = False

        except Exception as e:
            result['is_valid'] = False
            result['errors'].append(f"驗證過程發生錯誤: {str(e)}")

        return result

    # ==================== 輔助功能 ====================

    def _sanitize_folder_name(self, name: str) -> str:
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
        invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
        for char in invalid_chars:
            clean_name = clean_name.replace(char, '_')

        # 移除前後空格和點
        clean_name = clean_name.strip(' .')

        # 檢查保留名稱
        reserved_names = [
            'CON', 'PRN', 'AUX', 'NUL',
            'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
            'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
        ]
        if clean_name.upper() in reserved_names:
            clean_name = f"案件_{clean_name}"

        # 長度限制
        if len(clean_name) > 100:
            clean_name = clean_name[:100]

        # 空名稱處理
        if not clean_name:
            clean_name = "未知案件"

        return clean_name