#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
資料夾服務 - 服務層
統一所有資料夾相關的業務邏輯
整合現有的 FolderManager, FolderCreator, FolderOperations, FolderValidator
"""

import os
import shutil
from typing import Optional, List, Dict, Any, Tuple
from models.case_model import CaseData
from config.settings import AppConfig


class FolderService:
    """資料夾服務 - 統一資料夾操作業務邏輯"""

    def __init__(self, base_data_folder: str):
        """
        初始化資料夾服務

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

    # ====== 案件資料夾管理 ======

    def create_case_folder(self, case_data: CaseData) -> Tuple[bool, str]:
        """
        建立案件資料夾結構

        Args:
            case_data: 案件資料

        Returns:
            (success, message_or_path)
        """
        try:
            # 1. 驗證案件資料
            if not self._validate_case_data(case_data):
                return False, "案件資料驗證失敗"

            # 2. 取得案件類型資料夾
            case_type_folder = self._get_or_create_case_type_folder(case_data.case_type)
            if not case_type_folder:
                return False, f"無法建立案件類型資料夾: {case_data.case_type}"

            # 3. 建立當事人資料夾
            client_folder = self._create_client_folder(case_type_folder, case_data.client)
            if not client_folder:
                return False, f"無法建立當事人資料夾: {case_data.client}"

            # 4. 建立子資料夾結構
            sub_folders_success = self._create_sub_folders(client_folder)
            if not sub_folders_success:
                return False, "建立子資料夾失敗"

            # 5. 建立案件資訊Excel
            excel_success = self._create_case_info_excel(client_folder, case_data)
            if not excel_success:
                print("⚠️ Excel檔案建立失敗，但資料夾結構已建立")

            print(f"✅ 成功建立案件資料夾: {client_folder}")
            return True, client_folder

        except Exception as e:
            print(f"❌ 建立案件資料夾失敗: {e}")
            return False, str(e)

    def get_case_folder_path(self, case_data: CaseData) -> Optional[str]:
        """
        取得案件資料夾路徑

        Args:
            case_data: 案件資料

        Returns:
            資料夾路徑或None
        """
        try:
            case_type_folder = self._get_case_type_folder_path(case_data)
            if not case_type_folder or not os.path.exists(case_type_folder):
                return None

            safe_client_name = self._get_safe_client_name(case_data.client)
            client_folder = os.path.join(case_type_folder, safe_client_name)

            return client_folder if os.path.exists(client_folder) else None

        except Exception as e:
            print(f"❌ 取得案件資料夾路徑失敗: {e}")
            return None

    def delete_case_folder(self, case_data: CaseData, confirm: bool = False) -> Tuple[bool, str]:
        """
        刪除案件資料夾

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

            if not confirm:
                return False, "需要確認刪除操作"

            if not os.path.exists(case_folder):
                return False, f"資料夾不存在: {case_folder}"

            # 執行刪除
            shutil.rmtree(case_folder)
            print(f"✅ 成功刪除案件資料夾: {case_folder}")
            return True, f"成功刪除案件資料夾: {case_data.client}"

        except Exception as e:
            error_msg = f"刪除案件資料夾失敗: {case_data.client} - {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg

    def get_case_folder_info(self, case_data: CaseData) -> Dict[str, Any]:
        """
        取得案件資料夾資訊

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
                'size_mb': 0.0,
                'validation': None
            }

        # 計算資料夾大小和檔案數量
        size_info = self._get_folder_size_info(case_folder)

        # 驗證資料夾結構
        structure_validation = self._validate_folder_structure(case_folder)

        return {
            'exists': True,
            'path': case_folder,
            'has_files': size_info['has_files'],
            'file_count': size_info['file_count'],
            'size_mb': size_info['total_size_mb'],
            'validation': structure_validation
        }

    # ====== 進度階段資料夾管理 ======

    def create_progress_folder(self, case_data: CaseData, stage_name: str) -> Tuple[bool, str]:
        """
        建立進度階段資料夾

        Args:
            case_data: 案件資料
            stage_name: 階段名稱

        Returns:
            (success, message_or_path)
        """
        try:
            case_folder = self.get_case_folder_path(case_data)
            if not case_folder:
                return False, f"找不到案件資料夾: {case_data.client}"

            progress_base_folder = os.path.join(case_folder, '進度追蹤')
            if not os.path.exists(progress_base_folder):
                os.makedirs(progress_base_folder, exist_ok=True)

            safe_stage_name = self._sanitize_folder_name(stage_name)
            stage_folder = os.path.join(progress_base_folder, safe_stage_name)

            if os.path.exists(stage_folder):
                return True, f"階段資料夾已存在: {stage_folder}"

            os.makedirs(stage_folder, exist_ok=True)
            print(f"✅ 建立進度階段資料夾: {safe_stage_name}")
            return True, stage_folder

        except Exception as e:
            error_msg = f"建立進度階段資料夾失敗: {stage_name} - {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg

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

    def delete_stage_folder(self, case_data: CaseData, stage_name: str) -> Tuple[bool, str]:
        """
        刪除進度階段資料夾

        Args:
            case_data: 案件資料
            stage_name: 階段名稱

        Returns:
            (success, message)
        """
        try:
            stage_folder = self.get_stage_folder_path(case_data, stage_name)
            if not stage_folder:
                return False, f"找不到階段資料夾: {stage_name}"

            if not os.path.exists(stage_folder):
                return False, f"階段資料夾不存在: {stage_name}"

            shutil.rmtree(stage_folder)
            print(f"✅ 成功刪除階段資料夾: {stage_name}")
            return True, f"成功刪除階段資料夾: {stage_name}"

        except Exception as e:
            error_msg = f"刪除階段資料夾失敗: {stage_name} - {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg

    # ====== 批次操作 ======

    def batch_create_case_folders(self, cases: List[CaseData]) -> Dict[str, Any]:
        """
        批次建立案件資料夾

        Args:
            cases: 案件資料列表

        Returns:
            批次操作結果
        """
        result = {
            'total': len(cases),
            'success': 0,
            'failed': 0,
            'success_paths': [],
            'errors': []
        }

        for i, case_data in enumerate(cases, 1):
            try:
                print(f"📁 [{i}/{len(cases)}] 處理案件: {case_data.case_id} - {case_data.client}")

                success, path_or_error = self.create_case_folder(case_data)

                if success:
                    result['success'] += 1
                    result['success_paths'].append(path_or_error)
                    print(f"  ✅ 成功")
                else:
                    result['failed'] += 1
                    result['errors'].append(f"{case_data.client}: {path_or_error}")
                    print(f"  ❌ 失敗: {path_or_error}")

            except Exception as e:
                result['failed'] += 1
                error_msg = f"{case_data.client}: {str(e)}"
                result['errors'].append(error_msg)
                print(f"  ❌ 異常: {error_msg}")

        print(f"🎯 批次建立完成 - 成功: {result['success']}, 失敗: {result['failed']}")
        return result

    # ====== 私有輔助方法 ======

    def _validate_case_data(self, case_data: CaseData) -> bool:
        """驗證案件資料"""
        if not case_data:
            return False
        if not case_data.client or not case_data.client.strip():
            return False
        if not case_data.case_type or case_data.case_type not in AppConfig.CASE_TYPES:
            return False
        return True

    def _get_case_type_folder_path(self, case_type: str) -> Optional[str]:
        """取得案件類型資料夾路徑"""
        case_type_folder_name = AppConfig.CASE_TYPE_FOLDERS.get(case_type)
        if not case_type_folder_name:
            return None
        return os.path.join(self.base_data_folder, case_type_folder_name)

    def _get_or_create_case_type_folder(self, case_type: str) -> Optional[str]:
        """取得或建立案件類型資料夾"""
        case_type_path = self._get_case_type_folder_path(case_type)
        if not case_type_path:
            return None

        if not os.path.exists(case_type_path):
            os.makedirs(case_type_path, exist_ok=True)
            print(f"✅ 建立案件類型資料夾: {case_type}")

        return case_type_path

    def _get_safe_client_name(self, client_name: str) -> str:
        """取得安全的當事人名稱"""
        return self._sanitize_folder_name(client_name)

    def _sanitize_folder_name(self, name: str) -> str:
        """清理資料夾名稱"""
        if not name:
            return "未知"

        # 移除或替換不安全字符
        unsafe_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
        safe_name = name.strip()

        for char in unsafe_chars:
            safe_name = safe_name.replace(char, '_')

        # 移除多餘空白和點號
        safe_name = ' '.join(safe_name.split())
        safe_name = safe_name.strip('.')

        # 限制長度
        if len(safe_name) > 50:
            safe_name = safe_name[:50]

        return safe_name if safe_name else "未知"

    def _create_client_folder(self, case_type_folder: str, client_name: str) -> Optional[str]:
        """建立當事人資料夾"""
        safe_client_name = self._get_safe_client_name(client_name)
        client_folder = os.path.join(case_type_folder, safe_client_name)

        if not os.path.exists(client_folder):
            os.makedirs(client_folder, exist_ok=True)
            print(f"✅ 建立當事人資料夾: {safe_client_name}")

        return client_folder

    def _create_sub_folders(self, client_folder: str) -> bool:
        """建立子資料夾結構"""
        try:
            sub_folders = ['案件資訊', '進度追蹤', '狀紙']

            for folder_name in sub_folders:
                folder_path = os.path.join(client_folder, folder_name)
                if not os.path.exists(folder_path):
                    os.makedirs(folder_path, exist_ok=True)
                    print(f"  ✅ 建立子資料夾: {folder_name}")

            return True

        except Exception as e:
            print(f"❌ 建立子資料夾失敗: {e}")
            return False

    def _create_case_info_excel(self, client_folder: str, case_data: CaseData) -> bool:
        """建立案件資訊Excel（簡化版本）"""
        try:
            # 這裡可以整合 ExcelService 來建立Excel檔案
            # 目前返回True，表示成功（或可忽略）
            case_info_folder = os.path.join(client_folder, '案件資訊')
            excel_file = os.path.join(case_info_folder, f"{case_data.client}_案件資訊.xlsx")

            # TODO: 整合ExcelService建立實際Excel檔案
            print(f"  📋 Excel檔案位置: {excel_file}")
            return True

        except Exception as e:
            print(f"⚠️ 建立案件資訊Excel失敗: {e}")
            return False

    def _get_folder_size_info(self, folder_path: str) -> Dict[str, Any]:
        """取得資料夾大小資訊"""
        total_size = 0
        file_count = 0

        try:
            for dirpath, dirnames, filenames in os.walk(folder_path):
                for filename in filenames:
                    file_path = os.path.join(dirpath, filename)
                    if os.path.exists(file_path):
                        total_size += os.path.getsize(file_path)
                        file_count += 1

            return {
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'file_count': file_count,
                'has_files': file_count > 0
            }

        except Exception as e:
            print(f"⚠️ 計算資料夾大小失敗: {e}")
            return {
                'total_size_mb': 0.0,
                'file_count': 0,
                'has_files': False
            }

    def _validate_folder_structure(self, folder_path: str) -> Dict[str, Any]:
        """驗證資料夾結構"""
        result = {
            'is_valid': True,
            'missing_folders': [],
            'errors': [],
            'warnings': []
        }

        try:
            required_subfolders = ['狀紙', '進度追蹤', '案件資訊']

            for subfolder in required_subfolders:
                subfolder_path = os.path.join(folder_path, subfolder)
                if not os.path.exists(subfolder_path):
                    result['missing_folders'].append(subfolder)
                    result['warnings'].append(f"缺少子資料夾: {subfolder}")

            if result['missing_folders']:
                result['is_valid'] = False

        except Exception as e:
            result['is_valid'] = False
            result['errors'].append(f"驗證過程發生錯誤: {e}")

        return result