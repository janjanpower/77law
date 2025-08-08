#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
資料夾建立器 - 修改版本
🔥 修改：支援「案件編號_當事人」格式的資料夾建立
"""

import os
from typing import Any, Optional, Dict, List
from models.case_model import CaseData
from config.settings import AppConfig
from .folder_validator import FolderValidator


class FolderCreator:
    """資料夾建立工具 - 修改版本"""

    def __init__(self, base_data_folder: str):
        """
        初始化資料夾建立器

        Args:
            base_data_folder: 基礎資料資料夾路徑
        """
        self.base_data_folder = base_data_folder
        self.validator = FolderValidator()

    def create_case_folder_structure(self, case_data: CaseData) -> tuple[bool, str]:
        """
        為案件建立完整的資料夾結構

        Args:
            case_data: 案件資料

        Returns:
            (success, folder_path_or_error_message)
        """
        try:
            print(f"🏗️ 開始為案件 {case_data.case_id} 建立資料夾結構")
            print(f"   當事人: {case_data.client}")
            print(f"   案件類型: {case_data.case_type}")

            # 取得案件類型對應的資料夾
            case_type_folder = self._get_or_create_case_type_folder(case_data.case_type)
            if not case_type_folder:
                return False, f"未知的案件類型: {case_data.case_type}"

            # 🔥 修改：建立案件資料夾（使用新的命名邏輯）
            case_folder = self._create_case_folder(case_type_folder, case_data)
            if not case_folder:
                return False, "建立案件資料夾失敗"

            # 建立子資料夾結構
            sub_folders = self._create_sub_folders(case_folder)
            if not sub_folders:
                return False, "建立子資料夾結構失敗"

            # 建立現有的進度階段資料夾
            if case_data.progress_stages:
                progress_success = self._create_progress_folders(
                    sub_folders.get('進度追蹤', ''),
                    case_data.progress_stages
                )
                if not progress_success:
                    print("⚠️ 警告：部分進度資料夾建立失敗")

            print(f"✅ 成功為案件 {case_data.case_id} 建立完整資料夾結構")
            print(f"📁 路徑: {case_folder}")

            return True, case_folder

        except Exception as e:
            error_msg = f"建立案件資料夾結構失敗: {str(e)}"
            print(f"❌ {error_msg}")
            import traceback
            traceback.print_exc()
            return False, error_msg

    def _create_case_folder(self, case_type_folder: str, case_data: CaseData) -> Optional[str]:
        """
        🔥 修改：建立案件資料夾（使用案件編號_當事人格式）

        Args:
            case_type_folder: 案件類型資料夾路徑
            case_data: 案件資料

        Returns:
            資料夾路徑或None
        """
        try:
            # 使用新的命名邏輯
            safe_folder_name = self.validator.get_safe_case_folder_name(case_data)
            print(f"📁 案件資料夾名稱: {safe_folder_name}")

            # 檢查名稱衝突
            has_conflict, final_name = self.validator.check_folder_conflicts(
                case_type_folder, safe_folder_name
            )

            if has_conflict:
                print(f"⚠️ 檢測到名稱衝突，使用最終名稱: {final_name}")
                safe_folder_name = final_name

            case_folder_path = os.path.join(case_type_folder, safe_folder_name)
            print(f"📁 案件資料夾路徑: {case_folder_path}")

            # 驗證路徑
            is_valid, error_msg = self.validator.validate_path(case_folder_path)
            if not is_valid:
                print(f"❌ 案件資料夾路徑驗證失敗: {error_msg}")
                return None

            if not os.path.exists(case_folder_path):
                os.makedirs(case_folder_path, exist_ok=True)
                print(f"✅ 建立案件資料夾: {safe_folder_name}")
            else:
                print(f"ℹ️ 案件資料夾已存在: {safe_folder_name}")

            return case_folder_path

        except Exception as e:
            print(f"❌ 建立案件資料夾失敗: {e}")
            return None

    def _create_client_folder(self, case_type_folder: str, client_name: str) -> Optional[str]:
        """
        🔥 保留：向後相容方法，但建議使用 _create_case_folder
        """
        try:
            safe_client_name = self.validator.get_safe_client_name(client_name)
            print(f"👤 安全的當事人名稱: {safe_client_name}")

            # 檢查名稱衝突
            has_conflict, final_name = self.validator.check_folder_conflicts(
                case_type_folder, safe_client_name
            )

            if has_conflict:
                print(f"⚠️ 檢測到名稱衝突，使用最終名稱: {final_name}")
                safe_client_name = final_name

            client_folder_path = os.path.join(case_type_folder, safe_client_name)
            print(f"📁 當事人資料夾路徑: {client_folder_path}")

            # 驗證路徑
            is_valid, error_msg = self.validator.validate_path(client_folder_path)
            if not is_valid:
                print(f"❌ 當事人資料夾路徑驗證失敗: {error_msg}")
                return None

            if not os.path.exists(client_folder_path):
                os.makedirs(client_folder_path, exist_ok=True)
                print(f"✅ 建立當事人資料夾: {safe_client_name}")
            else:
                print(f"ℹ️ 當事人資料夾已存在: {safe_client_name}")

            return client_folder_path

        except Exception as e:
            print(f"❌ 建立當事人資料夾失敗: {e}")
            return None

    def _create_sub_folders(self, case_folder: str) -> Optional[Dict[str, str]]:
        """
        建立案件的子資料夾結構

        Args:
            case_folder: 案件資料夾路徑

        Returns:
            子資料夾路徑字典或None
        """
        try:
            # 預設子資料夾結構
            sub_folder_names = [
                '案件資訊',
                '進度追蹤',
                '狀紙',
            ]

            sub_folders = {}
            print(f"🏗️ 開始建立子資料夾結構...")

            for folder_name in sub_folder_names:
                folder_path = os.path.join(case_folder, folder_name)

                try:
                    if not os.path.exists(folder_path):
                        os.makedirs(folder_path, exist_ok=True)
                        print(f"  ✅ 建立子資料夾: {folder_name}")
                    else:
                        print(f"  ℹ️ 子資料夾已存在: {folder_name}")

                    sub_folders[folder_name] = folder_path

                except Exception as e:
                    print(f"  ❌ 建立子資料夾失敗: {folder_name} - {e}")
                    return None

            print(f"✅ 成功建立 {len(sub_folders)} 個子資料夾")
            return sub_folders

        except Exception as e:
            print(f"❌ 建立子資料夾結構失敗: {e}")
            return None

    def _get_or_create_case_type_folder(self, case_type: str) -> Optional[str]:
        """
        取得或建立案件類型資料夾

        Args:
            case_type: 案件類型

        Returns:
            資料夾路徑或None
        """
        try:
            if not self.validator.validate_case_type(case_type):
                print(f"❌ 無效的案件類型: {case_type}")
                return None

            folder_name = AppConfig.CASE_TYPE_FOLDERS.get(case_type)
            if not folder_name:
                print(f"❌ 找不到案件類型對應的資料夾: {case_type}")
                return None

            case_type_path = os.path.join(self.base_data_folder, folder_name)

            if not os.path.exists(case_type_path):
                os.makedirs(case_type_path, exist_ok=True)
                print(f"✅ 建立案件類型資料夾: {case_type_path}")
            else:
                print(f"ℹ️ 案件類型資料夾已存在: {case_type_path}")

            return case_type_path

        except Exception as e:
            print(f"❌ 建立案件類型資料夾失敗: {e}")
            return None

    def _create_progress_folders(self, progress_base_folder: str, progress_stages: Dict[str, Any]) -> bool:
        """
        建立進度階段資料夾

        Args:
            progress_base_folder: 進度追蹤基礎資料夾
            progress_stages: 進度階段字典

        Returns:
            建立是否成功
        """
        try:
            if not progress_stages:
                print("ℹ️ 沒有進度階段需要建立")
                return True

            print(f"🗂️ 開始建立 {len(progress_stages)} 個進度階段資料夾...")

            for stage_name in progress_stages.keys():
                safe_stage_name = self.validator.sanitize_folder_name(stage_name)
                stage_folder_path = os.path.join(progress_base_folder, safe_stage_name)

                try:
                    if not os.path.exists(stage_folder_path):
                        os.makedirs(stage_folder_path, exist_ok=True)
                        print(f"  ✅ 建立進度階段: {stage_name}")
                    else:
                        print(f"  ℹ️ 進度階段已存在: {stage_name}")

                except Exception as e:
                    print(f"  ❌ 建立進度階段失敗: {stage_name} - {e}")
                    return False

            print(f"✅ 成功建立所有進度階段資料夾")
            return True

        except Exception as e:
            print(f"❌ 建立進度階段資料夾失敗: {e}")
            return False

    def create_progress_folder(self, case_folder_path: str, stage_name: str) -> bool:
        """
        在指定案件資料夾中建立進度階段資料夾

        Args:
            case_folder_path: 案件資料夾路徑
            stage_name: 階段名稱

        Returns:
            建立是否成功
        """
        try:
            if not os.path.exists(case_folder_path):
                print(f"❌ 案件資料夾不存在: {case_folder_path}")
                return False

            progress_base_folder = os.path.join(case_folder_path, '進度追蹤')
            if not os.path.exists(progress_base_folder):
                os.makedirs(progress_base_folder, exist_ok=True)
                print(f"✅ 建立進度追蹤資料夾: {progress_base_folder}")

            safe_stage_name = self.validator.sanitize_folder_name(stage_name)
            stage_folder_path = os.path.join(progress_base_folder, safe_stage_name)

            if not os.path.exists(stage_folder_path):
                os.makedirs(stage_folder_path, exist_ok=True)
                print(f"✅ 建立進度階段資料夾: {stage_name}")
                return True
            else:
                print(f"ℹ️ 進度階段資料夾已存在: {stage_name}")
                return True

        except Exception as e:
            print(f"❌ 建立進度階段資料夾失敗: {e}")
            return False