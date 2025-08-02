#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
資料夾操作管理器
負責資料夾的CRUD操作、查詢和管理
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

            safe_client_name = self.validator.get_safe_client_name(case_data.client)
            client_folder = os.path.join(case_type_folder, safe_client_name)

            return client_folder if os.path.exists(client_folder) else None

        except Exception as e:
            print(f"❌ 取得案件資料夾路徑失敗: {e}")
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

            # 安全檢查
            if not confirm:
                folder_info = self.get_case_folder_info(case_data)
                if folder_info['has_files']:
                    return False, f"資料夾內含 {folder_info['file_count']} 個檔案，請先確認刪除"

            # 執行刪除
            shutil.rmtree(case_folder)
            print(f"✅ 已刪除案件資料夾: {case_folder}")

            return True, f"成功刪除案件資料夾: {case_data.client}"

        except Exception as e:
            error_msg = f"刪除案件資料夾失敗: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg

    def delete_stage_folder(self, case_data: CaseData, stage_name: str, confirm: bool = False) -> tuple[bool, str]:
        """
        刪除案件的特定進度階段資料夾

        Args:
            case_data: 案件資料
            stage_name: 階段名稱
            confirm: 是否已確認刪除

        Returns:
            tuple[bool, str]: (success, message)
        """
        try:
            # 取得案件資料夾路徑
            case_folder = self.get_case_folder_path(case_data)
            if not case_folder:
                return False, f"找不到案件資料夾: {case_data.client}"

            # 建構階段資料夾路徑
            safe_stage_name = self.validator.sanitize_folder_name(stage_name)
            stage_folder_path = os.path.join(case_folder, '進度追蹤', safe_stage_name)

            # 檢查資料夾是否存在
            if not os.path.exists(stage_folder_path):
                return False, f"階段資料夾不存在: {stage_name}"

            # 檢查資料夾內容
            try:
                folder_contents = os.listdir(stage_folder_path)
                has_files = len(folder_contents) > 0

                if has_files:
                    print(f"⚠️ 警告：階段資料夾 {stage_name} 內含 {len(folder_contents)} 個項目，將一併刪除")

            except Exception as e:
                print(f"⚠️ 無法檢查資料夾內容: {e}")
                has_files = False

            # 執行刪除
            if os.path.isdir(stage_folder_path):
                shutil.rmtree(stage_folder_path)
            else:
                os.remove(stage_folder_path)

            success_message = f"成功刪除階段資料夾: {stage_name}"
            if has_files:
                success_message += f"（包含 {len(folder_contents)} 個項目）"

            print(f"✅ {success_message}")
            return True, success_message

        except PermissionError:
            error_msg = f"權限不足，無法刪除階段資料夾: {stage_name}"
            return False, error_msg

        except FileNotFoundError:
            return False, f"階段資料夾不存在: {stage_name}"

        except Exception as e:
            error_msg = f"刪除階段資料夾失敗: {stage_name} - {str(e)}"
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
                'size_mb': 0.0,
                'validation': None
            }

        # 使用驗證器取得大小資訊
        size_info = self.validator.get_folder_size_info(case_folder)

        # 驗證資料夾結構
        structure_validation = self.validator.validate_folder_structure(case_folder)

        return {
            'exists': True,
            'path': case_folder,
            'has_files': size_info['has_files'],
            'file_count': size_info['file_count'],
            'size_mb': size_info['total_size_mb'],
            'validation': structure_validation
        }

    def move_case_folder(self, case_data: CaseData, new_case_type: str) -> tuple[bool, str]:
        """
        移動案件資料夾到不同的案件類型資料夾

        Args:
            case_data: 案件資料
            new_case_type: 新的案件類型

        Returns:
            (success, message)
        """
        try:
            # 驗證新案件類型
            if not self.validator.validate_case_type(new_case_type):
                return False, f"無效的案件類型: {new_case_type}"

            # 取得原始資料夾路徑
            old_folder = self.get_case_folder_path(case_data)
            if not old_folder:
                return False, f"找不到原始案件資料夾: {case_data.client}"

            # 取得新的目標路徑
            new_case_type_folder = self._get_case_type_folder_path(new_case_type)
            if not new_case_type_folder:
                return False, f"無法建立新案件類型資料夾: {new_case_type}"

            safe_client_name = self.validator.get_safe_client_name(case_data.client)
            new_folder = os.path.join(new_case_type_folder, safe_client_name)

            # 檢查目標是否已存在
            if os.path.exists(new_folder):
                return False, f"目標資料夾已存在: {new_folder}"

            # 執行移動
            shutil.move(old_folder, new_folder)
            print(f"✅ 成功移動案件資料夾: {old_folder} -> {new_folder}")

            return True, f"成功移動案件資料夾到 {new_case_type} 類型"

        except Exception as e:
            error_msg = f"移動案件資料夾失敗: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg

    def copy_case_folder(self, case_data: CaseData, target_path: str) -> tuple[bool, str]:
        """
        複製案件資料夾到指定路徑

        Args:
            case_data: 案件資料
            target_path: 目標路徑

        Returns:
            (success, message)
        """
        try:
            source_folder = self.get_case_folder_path(case_data)
            if not source_folder:
                return False, f"找不到來源案件資料夾: {case_data.client}"

            # 驗證目標路徑
            is_valid, error_msg = self.validator.validate_path(target_path)
            if not is_valid:
                return False, f"目標路徑無效: {error_msg}"

            # 確保目標資料夾不存在
            if os.path.exists(target_path):
                return False, f"目標路徑已存在: {target_path}"

            # 執行複製
            shutil.copytree(source_folder, target_path)
            print(f"✅ 成功複製案件資料夾: {source_folder} -> {target_path}")

            return True, f"成功複製案件資料夾到: {target_path}"

        except Exception as e:
            error_msg = f"複製案件資料夾失敗: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg

    def list_case_folders(self, case_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        列出案件資料夾

        Args:
            case_type: 指定案件類型，None表示列出所有

        Returns:
            案件資料夾資訊列表
        """
        folders = []

        try:
            if case_type:
                case_types = [case_type] if self.validator.validate_case_type(case_type) else []
            else:
                case_types = list(AppConfig.CASE_TYPE_FOLDERS.keys())

            for ct in case_types:
                case_type_folder = self._get_case_type_folder_path(ct)
                if not case_type_folder or not os.path.exists(case_type_folder):
                    continue

                try:
                    for item in os.listdir(case_type_folder):
                        item_path = os.path.join(case_type_folder, item)

                        if os.path.isdir(item_path):
                            # 取得資料夾資訊
                            size_info = self.validator.get_folder_size_info(item_path)
                            validation = self.validator.validate_folder_structure(item_path)

                            folders.append({
                                'client_name': item,
                                'case_type': ct,
                                'path': item_path,
                                'file_count': size_info['file_count'],
                                'size_mb': size_info['total_size_mb'],
                                'is_valid_structure': validation['is_valid'],
                                'missing_folders': validation['missing_folders'],
                                'last_modified': os.path.getmtime(item_path)
                            })

                except OSError as e:
                    print(f"⚠️ 無法讀取資料夾: {case_type_folder} - {e}")
                    continue

        except Exception as e:
            print(f"❌ 列出案件資料夾失敗: {e}")

        return folders

    def find_case_folders_by_name(self, search_name: str, fuzzy: bool = True) -> List[Dict[str, Any]]:
        """
        根據名稱搜尋案件資料夾

        Args:
            search_name: 搜尋名稱
            fuzzy: 是否使用模糊搜尋

        Returns:
            符合條件的案件資料夾列表
        """
        all_folders = self.list_case_folders()
        matched_folders = []

        search_name_lower = search_name.lower()

        for folder in all_folders:
            client_name_lower = folder['client_name'].lower()

            if fuzzy:
                # 模糊搜尋：包含關鍵字
                if search_name_lower in client_name_lower:
                    matched_folders.append(folder)
            else:
                # 精確搜尋
                if client_name_lower == search_name_lower:
                    matched_folders.append(folder)

        return matched_folders

    def get_folder_statistics(self) -> Dict[str, Any]:
        """
        取得資料夾統計資訊

        Returns:
            統計資訊字典
        """
        stats = {
            'total_folders': 0,
            'by_case_type': {},
            'total_files': 0,
            'total_size_mb': 0.0,
            'invalid_structures': 0,
            'empty_folders': 0
        }

        try:
            all_folders = self.list_case_folders()
            stats['total_folders'] = len(all_folders)

            for folder in all_folders:
                # 按案件類型統計
                case_type = folder['case_type']
                if case_type not in stats['by_case_type']:
                    stats['by_case_type'][case_type] = 0
                stats['by_case_type'][case_type] += 1

                # 累計檔案和大小
                stats['total_files'] += folder['file_count']
                stats['total_size_mb'] += folder['size_mb']

                # 統計無效結構
                if not folder['is_valid_structure']:
                    stats['invalid_structures'] += 1

                # 統計空資料夾
                if folder['file_count'] == 0:
                    stats['empty_folders'] += 1

            stats['total_size_mb'] = round(stats['total_size_mb'], 2)

        except Exception as e:
            print(f"❌ 取得資料夾統計失敗: {e}")

        return stats

    def rename_case_folder(self, case_data: CaseData, new_client_name: str) -> tuple[bool, str]:
        """
        重新命名案件資料夾

        Args:
            case_data: 案件資料
            new_client_name: 新的當事人名稱

        Returns:
            (success, message)
        """
        try:
            old_folder = self.get_case_folder_path(case_data)
            if not old_folder:
                return False, f"找不到案件資料夾: {case_data.client}"

            # 取得父資料夾
            parent_folder = os.path.dirname(old_folder)

            # 產生新的安全名稱
            safe_new_name = self.validator.get_safe_client_name(new_client_name)
            new_folder = os.path.join(parent_folder, safe_new_name)

            # 檢查是否已存在
            if os.path.exists(new_folder):
                return False, f"目標名稱已存在: {safe_new_name}"

            # 執行重新命名
            os.rename(old_folder, new_folder)
            print(f"✅ 成功重新命名資料夾: {case_data.client} -> {new_client_name}")

            return True, f"成功重新命名為: {new_client_name}"

        except Exception as e:
            error_msg = f"重新命名資料夾失敗: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg

    def cleanup_empty_folders(self, case_type: Optional[str] = None) -> Dict[str, Any]:
        """
        清理空資料夾

        Args:
            case_type: 指定案件類型，None表示清理所有

        Returns:
            清理結果統計
        """
        result = {
            'total_checked': 0,
            'empty_found': 0,
            'cleaned': 0,
            'errors': []
        }

        try:
            all_folders = self.list_case_folders(case_type)
            result['total_checked'] = len(all_folders)

            for folder in all_folders:
                if folder['file_count'] == 0:
                    result['empty_found'] += 1

                    try:
                        # 檢查資料夾是否真的為空（包含子資料夾）
                        folder_path = folder['path']
                        is_completely_empty = True

                        for root, dirs, files in os.walk(folder_path):
                            if files or dirs:
                                is_completely_empty = False
                                break

                        if is_completely_empty:
                            shutil.rmtree(folder_path)
                            result['cleaned'] += 1
                            print(f"✅ 清理空資料夾: {folder['client_name']}")

                    except Exception as e:
                        error_msg = f"清理 {folder['client_name']} 失敗: {str(e)}"
                        result['errors'].append(error_msg)
                        print(f"❌ {error_msg}")

        except Exception as e:
            result['errors'].append(f"清理過程發生錯誤: {str(e)}")
            print(f"❌ 清理空資料夾失敗: {e}")

        return result

    def backup_case_folder(self, case_data: CaseData, backup_path: str) -> tuple[bool, str]:
        """
        備份案件資料夾

        Args:
            case_data: 案件資料
            backup_path: 備份目標路徑

        Returns:
            (success, message)
        """
        try:
            source_folder = self.get_case_folder_path(case_data)
            if not source_folder:
                return False, f"找不到來源案件資料夾: {case_data.client}"

            # 建立備份檔名（包含時間戳記）
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"{case_data.client}_backup_{timestamp}"
            full_backup_path = os.path.join(backup_path, backup_filename)

            # 確保備份目錄存在
            os.makedirs(backup_path, exist_ok=True)

            # 執行備份
            shutil.copytree(source_folder, full_backup_path)
            print(f"✅ 成功備份案件資料夾: {full_backup_path}")

            return True, f"成功備份到: {full_backup_path}"

        except Exception as e:
            error_msg = f"備份案件資料夾失敗: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg

    def _get_case_type_folder_path(self, case_type: str) -> Optional[str]:
        """取得案件類型資料夾路徑（內部方法）"""
        try:
            if not self.validator.validate_case_type(case_type):
                return None

            folder_name = AppConfig.CASE_TYPE_FOLDERS.get(case_type)
            case_type_path = os.path.join(self.base_data_folder, folder_name)

            # 確保資料夾存在
            if not os.path.exists(case_type_path):
                os.makedirs(case_type_path, exist_ok=True)
                print(f"✅ 建立案件類型資料夾: {case_type_path}")

            return case_type_path

        except Exception as e:
            print(f"❌ 取得案件類型資料夾失敗: {e}")
            return None