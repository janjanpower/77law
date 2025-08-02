#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
資料夾建立器 - 完整版本
專責案件資料夾結構的建立功能，包含所有缺失的方法
"""

import os
from typing import Any, Optional, Dict, List
from models.case_model import CaseData
from config.settings import AppConfig
from .folder_validator import FolderValidator


class FolderCreator:
    """資料夾建立工具 - 完整版本"""

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

            # 建立當事人資料夾
            client_folder = self._create_client_folder(case_type_folder, case_data.client)
            if not client_folder:
                return False, "建立當事人資料夾失敗"

            # 建立子資料夾結構
            sub_folders = self._create_sub_folders(client_folder)
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
            print(f"📁 路徑: {client_folder}")

            return True, client_folder

        except Exception as e:
            error_msg = f"建立案件資料夾結構失敗: {str(e)}"
            print(f"❌ {error_msg}")
            import traceback
            traceback.print_exc()
            return False, error_msg

    def create_progress_folder(self, case_folder_path: str, stage_name: str) -> bool:
        """
        為特定案件建立單一進度階段資料夾

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

            # 確保進度追蹤資料夾存在
            if not os.path.exists(progress_base_folder):
                os.makedirs(progress_base_folder)
                print(f"✅ 建立進度追蹤資料夾: {progress_base_folder}")

            # 建立階段資料夾
            safe_stage_name = self.validator.sanitize_folder_name(stage_name)
            stage_folder_path = os.path.join(progress_base_folder, safe_stage_name)

            if not os.path.exists(stage_folder_path):
                os.makedirs(stage_folder_path)
                print(f"✅ 建立進度階段資料夾: {stage_name}")
                return True
            else:
                print(f"ℹ️ 進度階段資料夾已存在: {stage_name}")
                return True

        except Exception as e:
            print(f"❌ 建立進度階段資料夾失敗: {e}")
            return False

    def _get_or_create_case_type_folder(self, case_type: str) -> Optional[str]:
        """取得或建立案件類型對應的資料夾路徑"""
        try:
            if not self.validator.validate_case_type(case_type):
                print(f"❌ 無效的案件類型: {case_type}")
                return None

            folder_name = AppConfig.CASE_TYPE_FOLDERS.get(case_type)
            if not folder_name:
                print(f"❌ 找不到案件類型對應的資料夾名稱: {case_type}")
                return None

            case_type_path = os.path.join(self.base_data_folder, folder_name)
            print(f"📂 案件類型資料夾路徑: {case_type_path}")

            # 驗證路徑
            is_valid, error_msg = self.validator.validate_path(case_type_path)
            if not is_valid:
                print(f"❌ 路徑驗證失敗: {error_msg}")
                return None

            if not os.path.exists(case_type_path):
                os.makedirs(case_type_path, exist_ok=True)
                print(f"✅ 建立案件類型資料夾: {case_type_path}")

            return case_type_path

        except Exception as e:
            print(f"❌ 取得案件類型資料夾失敗: {e}")
            return None

    def _create_client_folder(self, case_type_folder: str, client_name: str) -> Optional[str]:
        """建立當事人資料夾"""
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

    def _create_sub_folders(self, client_folder: str) -> Optional[Dict[str, str]]:
        """
        建立案件的子資料夾結構

        Args:
            client_folder: 當事人資料夾路徑

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
                folder_path = os.path.join(client_folder, folder_name)

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

            print(f"✅ 成功建立所有子資料夾 ({len(sub_folders)} 個)")
            return sub_folders

        except Exception as e:
            print(f"❌ 建立子資料夾結構失敗: {e}")
            return None

    def _create_progress_folders(self, progress_base_folder: str, progress_stages: Dict[str, str]) -> bool:
        """
        建立進度階段資料夾

        Args:
            progress_base_folder: 進度追蹤基礎資料夾路徑
            progress_stages: 進度階段字典

        Returns:
            是否全部建立成功
        """
        try:
            if not progress_stages:
                print("ℹ️ 沒有進度階段需要建立資料夾")
                return True

            if not progress_base_folder or not os.path.exists(progress_base_folder):
                print(f"❌ 進度追蹤基礎資料夾不存在: {progress_base_folder}")
                return False

            success_count = 0
            total_count = len(progress_stages)
            print(f"🏗️ 開始建立 {total_count} 個進度階段資料夾...")

            for stage_name in progress_stages.keys():
                try:
                    # 清理階段名稱，確保可以作為資料夾名稱
                    safe_stage_name = self.validator.sanitize_folder_name(stage_name)
                    stage_folder_path = os.path.join(progress_base_folder, safe_stage_name)

                    if not os.path.exists(stage_folder_path):
                        os.makedirs(stage_folder_path, exist_ok=True)
                        print(f"  ✅ 建立進度階段資料夾: {stage_name}")
                    else:
                        print(f"  ℹ️ 進度階段資料夾已存在: {stage_name}")

                    success_count += 1

                except Exception as e:
                    print(f"  ❌ 建立進度階段資料夾失敗: {stage_name} - {e}")
                    continue

            print(f"✅ 進度階段資料夾建立完成: {success_count}/{total_count}")
            return success_count == total_count

        except Exception as e:
            print(f"❌ 建立進度階段資料夾失敗: {e}")
            return False

    def create_batch_folders(self, cases: List[CaseData]) -> Dict[str, Any]:
        """
        批次建立多個案件的資料夾結構

        Args:
            cases: 案件資料列表

        Returns:
            建立結果統計
        """
        result = {
            'total': len(cases),
            'success': 0,
            'failed': 0,
            'errors': [],
            'success_paths': []
        }

        print(f"🏗️ 開始批次建立 {len(cases)} 個案件的資料夾結構...")

        for i, case_data in enumerate(cases, 1):
            try:
                print(f"📁 [{i}/{len(cases)}] 處理案件: {case_data.case_id} - {case_data.client}")

                success, path_or_error = self.create_case_folder_structure(case_data)

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

    def create_stage_folder_for_case(self, case_data: CaseData, stage_name: str) -> bool:
        """
        為指定案件建立特定進度階段資料夾

        Args:
            case_data: 案件資料
            stage_name: 階段名稱

        Returns:
            建立是否成功
        """
        try:
            # 先找到案件資料夾
            case_type_folder = self._get_or_create_case_type_folder(case_data.case_type)
            if not case_type_folder:
                return False

            safe_client_name = self.validator.get_safe_client_name(case_data.client)
            client_folder = os.path.join(case_type_folder, safe_client_name)

            if not os.path.exists(client_folder):
                print(f"❌ 找不到案件資料夾: {client_folder}")
                return False

            # 建立進度階段資料夾
            return self.create_progress_folder(client_folder, stage_name)

        except Exception as e:
            print(f"❌ 為案件建立階段資料夾失敗: {e}")
            return False

    def validate_and_repair_structure(self, case_data: CaseData) -> Dict[str, Any]:
        """
        驗證並修復案件資料夾結構

        Args:
            case_data: 案件資料

        Returns:
            修復結果
        """
        result = {
            'is_valid': False,
            'repaired': False,
            'missing_folders': [],
            'created_folders': [],
            'errors': []
        }

        try:
            # 取得案件資料夾路徑
            case_type_folder = self._get_or_create_case_type_folder(case_data.case_type)
            if not case_type_folder:
                result['errors'].append(f"無法取得案件類型資料夾: {case_data.case_type}")
                return result

            safe_client_name = self.validator.get_safe_client_name(case_data.client)
            client_folder = os.path.join(case_type_folder, safe_client_name)

            if not os.path.exists(client_folder):
                result['missing_folders'].append('主資料夾')
                # 嘗試重新建立
                success, message = self.create_case_folder_structure(case_data)
                if success:
                    result['repaired'] = True
                    result['created_folders'].append('完整結構')
                else:
                    result['errors'].append(message)
                    return result

            # 檢查子資料夾
            required_sub_folders = [
                '案件資訊', '進度追蹤', '狀紙'
            ]

            for folder_name in required_sub_folders:
                folder_path = os.path.join(client_folder, folder_name)
                if not os.path.exists(folder_path):
                    result['missing_folders'].append(folder_name)
                    try:
                        os.makedirs(folder_path, exist_ok=True)
                        result['created_folders'].append(folder_name)
                        result['repaired'] = True
                    except Exception as e:
                        result['errors'].append(f"無法建立 {folder_name}: {str(e)}")

            # 檢查進度階段資料夾
            if case_data.progress_stages:
                progress_folder = os.path.join(client_folder, '進度追蹤')
                for stage_name in case_data.progress_stages.keys():
                    safe_stage_name = self.validator.sanitize_folder_name(stage_name)
                    stage_path = os.path.join(progress_folder, safe_stage_name)
                    if not os.path.exists(stage_path):
                        result['missing_folders'].append(f"進度階段: {stage_name}")
                        try:
                            os.makedirs(stage_path, exist_ok=True)
                            result['created_folders'].append(f"進度階段: {stage_name}")
                            result['repaired'] = True
                        except Exception as e:
                            result['errors'].append(f"無法建立進度階段 {stage_name}: {str(e)}")

            result['is_valid'] = len(result['missing_folders']) == 0 and len(result['errors']) == 0

        except Exception as e:
            result['errors'].append(f"驗證過程發生錯誤: {str(e)}")

        return result

    def get_folder_creation_summary(self, case_data: CaseData) -> Dict[str, Any]:
        """
        取得資料夾建立摘要資訊

        Args:
            case_data: 案件資料

        Returns:
            摘要資訊
        """
        summary = {
            'case_id': case_data.case_id,
            'client': case_data.client,
            'case_type': case_data.case_type,
            'expected_structure': {},
            'would_create': []
        }

        try:
            # 預期的資料夾結構
            case_type_folder = AppConfig.CASE_TYPE_FOLDERS.get(case_data.case_type, case_data.case_type)
            safe_client_name = self.validator.get_safe_client_name(case_data.client)

            base_path = os.path.join(self.base_data_folder, case_type_folder, safe_client_name)

            summary['expected_structure'] = {
                'base_path': base_path,
                'sub_folders': [
                    '案件資訊', '進度追蹤', '相關文件',
                    '證據資料', '庭期紀錄', '通訊記錄'
                ],
                'progress_stages': list(case_data.progress_stages.keys()) if case_data.progress_stages else []
            }

            # 檢查哪些會被建立
            if not os.path.exists(base_path):
                summary['would_create'].append(f"主資料夾: {safe_client_name}")

            for sub_folder in summary['expected_structure']['sub_folders']:
                sub_path = os.path.join(base_path, sub_folder)
                if not os.path.exists(sub_path):
                    summary['would_create'].append(f"子資料夾: {sub_folder}")

            for stage_name in summary['expected_structure']['progress_stages']:
                safe_stage_name = self.validator.sanitize_folder_name(stage_name)
                stage_path = os.path.join(base_path, '進度追蹤', safe_stage_name)
                if not os.path.exists(stage_path):
                    summary['would_create'].append(f"進度階段: {stage_name}")

        except Exception as e:
            summary['error'] = str(e)

        return summary