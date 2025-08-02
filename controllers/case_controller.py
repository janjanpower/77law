#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
案件控制器 - 完整修正版本
整合各個專門管理器，提供統一的對外介面
完全修正資料夾建立問題
"""

from typing import List, Optional, Tuple, Dict, Any
from models.case_model import CaseData
from utils.folder_management.folder_manager import FolderManager
from config.settings import AppConfig
import os

# 導入各個專門管理器
from .case_managers.case_data_manager import CaseDataManager
from .case_managers.case_validator import CaseValidator
from .case_managers.case_import_export import CaseImportExport
from .case_managers.case_progress_manager import CaseProgressManager


class CaseController:
    """案件資料控制器 - 完整修正版本"""

    def __init__(self, data_file: str = None):
        """初始化案件控制器"""
        if data_file is None:
            self.data_file = AppConfig.DATA_CONFIG['case_data_file']
        else:
            self.data_file = data_file

        self.data_folder = os.path.dirname(self.data_file) if os.path.dirname(self.data_file) else '.'

        # 初始化資料夾管理器
        self.folder_manager = FolderManager(self.data_folder)

        # 初始化資料管理器
        self.data_manager = CaseDataManager(self.data_file, self.data_folder)

        # 確保資料夾存在
        self._ensure_data_folder()

        # 載入案件資料
        self.load_cases()

        # 初始化其他管理器（確保使用最新的案件資料）
        self.validator = CaseValidator(self.data_manager.cases)
        self.import_export = CaseImportExport(self.data_folder)
        self.progress_manager = CaseProgressManager(self.data_manager.cases, self.folder_manager)

    def _ensure_data_folder(self):
        """確保資料夾存在"""
        try:
            if not os.path.exists(self.data_folder):
                os.makedirs(self.data_folder)
                print(f"建立資料夾：{self.data_folder}")

            # 建立案件類型資料夾
            for folder_name in AppConfig.CASE_TYPE_FOLDERS.values():
                folder_path = os.path.join(self.data_folder, folder_name)
                if not os.path.exists(folder_path):
                    os.makedirs(folder_path)
                    print(f"建立案件類型資料夾：{folder_path}")

        except Exception as e:
            print(f"建立資料夾失敗: {e}")

    # ==================== 資料CRUD操作 ====================

    def load_cases(self) -> bool:
        """載入案件資料"""
        result = self.data_manager.load_cases()
        if result:
            # 確保所有管理器使用最新的案件資料
            self._sync_managers()
        return result

    def _sync_managers(self):
        """同步各管理器的案件資料"""
        try:
            # 更新驗證器的案件資料
            if hasattr(self, 'validator'):
                self.validator.cases = self.data_manager.cases

            # 更新進度管理器的案件資料
            if hasattr(self, 'progress_manager'):
                self.progress_manager.cases = self.data_manager.cases

            print(f"已同步管理器資料，當前案件數量: {len(self.data_manager.cases)}")

        except Exception as e:
            print(f"同步管理器資料失敗: {e}")

    def save_cases(self) -> bool:
        """儲存案件資料"""
        result = self.data_manager.save_cases()
        if result:
            self._sync_managers()
        return result

    def add_case(self, case_data: CaseData) -> bool:
        """
        新增案件 - 完全修正版本

        Args:
            case_data: 案件資料

        Returns:
            bool: 是否新增成功
        """
        try:
            # 委託給資料管理器處理
            result = self.data_manager.add_case(case_data)

            if result:
                # 同步管理器資料
                self._sync_managers()

                # 建立案件資料夾結構 - 完全修正：使用正確的方法
                try:
                    folder_result = self.folder_manager.create_case_folder_structure(case_data)
                    if folder_result:
                        print(f"成功建立案件資料夾結構: {case_data.client}")
                    else:
                        print(f"警告：案件資料夾建立失敗: {case_data.client}")
                except AttributeError as e:
                    print(f"FolderManager 方法呼叫錯誤: {e}")
                    # 嘗試備用方法
                    try:
                        if hasattr(self.folder_manager, 'creator'):
                            success, message = self.folder_manager.creator.create_case_folder_structure(case_data)
                            if success:
                                print(f"使用備用方法成功建立資料夾: {message}")
                            else:
                                print(f"備用方法也失敗: {message}")
                    except Exception as backup_e:
                        print(f"備用方法失敗: {backup_e}")
                except Exception as e:
                    print(f"建立案件資料夾時發生錯誤: {e}")

            return result

        except Exception as e:
            print(f"CaseController.add_case 失敗: {e}")
            import traceback
            traceback.print_exc()
            return False

    def update_case(self, case_data: CaseData) -> bool:
        """
        更新案件

        Args:
            case_data: 案件資料

        Returns:
            bool: 是否更新成功
        """
        try:
            result = self.data_manager.update_case(case_data)
            if result:
                self._sync_managers()
            return result
        except Exception as e:
            print(f"CaseController.update_case 失敗: {e}")
            return False

    def delete_case(self, case_id: str, case_type: str = None, delete_folder: bool = True) -> bool:
        """
        刪除案件 - 修正版本：確保資料夾正確刪除
        """
        try:
            print(f"🗑️ 開始刪除案件: {case_id}")

            # 如果沒有提供 case_type，從案件資料中取得
            if case_type is None:
                case = self.get_case_by_id(case_id)
                if not case:
                    print(f"❌ 找不到案件: {case_id}")
                    return False
                case_type = case.case_type
            else:
                # 驗證提供的 case_type 是否正確
                case = self.get_case_by_id_and_type(case_id, case_type)
                if not case:
                    print(f"❌ 找不到案件: {case_id} (類型: {case_type})")
                    return False

            # 如果需要刪除資料夾，先處理資料夾
            folder_deletion_success = True
            if delete_folder:
                print(f"📁 準備刪除資料夾...")
                try:
                    folder_deletion_success = self.delete_case_folder(case_id)
                    if folder_deletion_success:
                        print(f"✅ 成功刪除案件資料夾: {case.client}")
                    else:
                        print(f"⚠️ 案件資料夾刪除失敗: {case.client}")
                        # 不中斷執行，繼續刪除資料記錄
                except Exception as e:
                    print(f"❌ 刪除資料夾時發生錯誤: {e}")
                    folder_deletion_success = False
                    # 不中斷執行，繼續刪除資料記錄

            # 刪除案件資料記錄
            print(f"📋 準備刪除案件資料記錄...")
            data_deletion_success = self.data_manager.delete_case(case_id, case_type)

            if data_deletion_success:
                self._sync_managers()
                print(f"✅ 成功刪除案件資料記錄: {case_id}")
            else:
                print(f"❌ 案件資料記錄刪除失敗: {case_id}")

            # 評估整體成功狀態
            overall_success = data_deletion_success

            if delete_folder:
                if folder_deletion_success and data_deletion_success:
                    print(f"✅ 案件完全刪除成功 (包含資料夾)")
                elif data_deletion_success and not folder_deletion_success:
                    print(f"⚠️ 案件資料刪除成功，但資料夾刪除失敗")
                elif not data_deletion_success:
                    print(f"❌ 案件資料刪除失敗")

            return overall_success

        except Exception as e:
            print(f"❌ CaseController.delete_case 失敗: {e}")
            import traceback
            traceback.print_exc()
            return False

    def get_case_by_id_and_type(self, case_id: str, case_type: str) -> Optional[CaseData]:
        """
        根據編號和類型取得案件 - 新增方法確保精確匹配

        Args:
            case_id: 案件編號
            case_type: 案件類型

        Returns:
            匹配的案件資料或 None
        """
        try:
            all_cases = self.get_cases()
            for case in all_cases:
                if case.case_id == case_id and case.case_type == case_type:
                    return case
            return None
        except Exception as e:
            print(f"❌ 取得案件失敗: {e}")
            return None


    def get_cases(self) -> List[CaseData]:
        """取得所有案件"""
        return self.data_manager.get_cases()

    def get_case_by_id(self, case_id: str) -> Optional[CaseData]:
        """根據編號取得案件"""
        return self.data_manager.get_case_by_id(case_id)

    def search_cases(self, keyword: str) -> List[CaseData]:
        """搜尋案件"""
        return self.data_manager.search_cases(keyword)

    def generate_case_id(self, case_type: str) -> str:
        """生成案件編號"""
        return self.data_manager.generate_case_id(case_type)

    # ==================== 案件驗證相關 ====================

    def validate_case_data(self, case_data: CaseData) -> Tuple[bool, List[str]]:
        """驗證案件資料"""
        return self.validator.validate_case_data(case_data)

    def check_case_id_duplicate(self, case_id: str, case_type: str, exclude_case_id: str = None) -> bool:
        """檢查案件編號重複"""
        return self.validator.check_case_id_duplicate(case_id, case_type, exclude_case_id)

    # ==================== 進度管理相關 ====================

    def add_case_progress_stage(self, case_id: str, stage_name: str, stage_date: str,
                               note: str = None, time: str = None) -> bool:
        """新增案件進度階段"""
        try:
            result = self.progress_manager.add_progress_stage(case_id, stage_name, stage_date, note, time)
            if result:
                self._sync_managers()
            return result
        except Exception as e:
            print(f"CaseController.add_case_progress_stage 失敗: {e}")
            return False

    def update_case_progress_stage(self, case_id: str, stage_name: str, stage_date: str,
                                  note: str = None, time: str = None) -> bool:
        """更新案件進度階段"""
        try:
            result = self.progress_manager.update_progress_stage(case_id, stage_name, stage_date, note, time)
            if result:
                self._sync_managers()
            return result
        except Exception as e:
            print(f"CaseController.update_case_progress_stage 失敗: {e}")
            return False

    def remove_case_progress_stage(self, case_id: str, stage_name: str) -> bool:
        """移除案件進度階段"""
        try:
            result = self.progress_manager.remove_progress_stage(case_id, stage_name)
            if result:
                self._sync_managers()
            return result
        except Exception as e:
            print(f"CaseController.remove_case_progress_stage 失敗: {e}")
            return False

    # ==================== 資料夾管理相關 ====================

    def create_case_folder_structure(self, case_data: CaseData) -> bool:
        """建立案件資料夾結構 - 正確的方法名稱"""
        try:
            return self.folder_manager.create_case_folder_structure(case_data)
        except Exception as e:
            print(f"CaseController.create_case_folder_structure 失敗: {e}")
            return False

    def get_case_folder_path(self, case_id: str) -> Optional[str]:
        """取得案件資料夾路徑"""
        try:
            case = self.get_case_by_id(case_id)
            if not case:
                return None
            return self.folder_manager.get_case_folder_path(case)
        except Exception as e:
            print(f"CaseController.get_case_folder_path 失敗: {e}")
            return None

    def get_case_folder_info(self, case_id: str) -> Dict[str, Any]:
        """
        取得案件資料夾資訊（用於刪除前檢查）

        Args:
            case_id: 案件編號

        Returns:
            資料夾資訊字典
        """
        try:
            case = self.get_case_by_id(case_id)
            if not case:
                return {
                    'exists': False,
                    'path': None,
                    'has_files': False,
                    'file_count': 0,
                    'size_mb': 0.0,
                    'validation': None
                }

            # 嘗試從 folder_manager 取得資訊
            if hasattr(self.folder_manager, 'operations') and self.folder_manager.operations:
                return self.folder_manager.operations.get_case_folder_info(case)
            elif hasattr(self.folder_manager, 'get_case_folder_info'):
                return self.folder_manager.get_case_folder_info(case)
            else:
                # 備用方法：基本資訊
                folder_path = self.get_case_folder_path(case_id)
                if folder_path and os.path.exists(folder_path):
                    import os
                    try:
                        # 計算檔案數量
                        file_count = sum([len(files) for r, d, files in os.walk(folder_path)])
                        has_files = file_count > 0

                        # 簡單大小計算
                        total_size = 0
                        for dirpath, dirnames, filenames in os.walk(folder_path):
                            for filename in filenames:
                                filepath = os.path.join(dirpath, filename)
                                try:
                                    total_size += os.path.getsize(filepath)
                                except:
                                    pass
                        size_mb = total_size / (1024 * 1024)

                        return {
                            'exists': True,
                            'path': folder_path,
                            'has_files': has_files,
                            'file_count': file_count,
                            'size_mb': round(size_mb, 2),
                            'validation': {'is_valid': True, 'method': 'basic'}
                        }
                    except Exception as e:
                        print(f"計算資料夾資訊時發生錯誤: {e}")
                        return {
                            'exists': True,
                            'path': folder_path,
                            'has_files': False,
                            'file_count': 0,
                            'size_mb': 0.0,
                            'validation': {'is_valid': False, 'error': str(e)}
                        }
                else:
                    return {
                        'exists': False,
                        'path': folder_path,
                        'has_files': False,
                        'file_count': 0,
                        'size_mb': 0.0,
                        'validation': None
                    }

        except Exception as e:
            print(f"CaseController.get_case_folder_info 失敗: {e}")
            return {
                'exists': False,
                'path': None,
                'has_files': False,
                'file_count': 0,
                'size_mb': 0.0,
                'validation': None,
                'error': str(e)
            }

    def get_case_stage_folder_path(self, case_id: str, stage_name: str) -> Optional[str]:
        """取得案件階段資料夾路徑"""
        try:
            case = self.get_case_by_id(case_id)
            if not case:
                return None

            # 檢查 folder_manager 是否有 get_stage_folder_path 方法
            if hasattr(self.folder_manager, 'get_stage_folder_path'):
                return self.folder_manager.get_stage_folder_path(case, stage_name)
            elif hasattr(self.folder_manager, 'operations'):
                return self.folder_manager.operations.get_stage_folder_path(case, stage_name)
            else:
                print("警告：找不到 get_stage_folder_path 方法")
                return None
        except Exception as e:
            print(f"CaseController.get_case_stage_folder_path 失敗: {e}")
            return None

    def delete_case_folder(self, case_id: str) -> bool:
        """
        刪除案件資料夾 - 修正版本：加強除錯與多重備用方案

        Args:
            case_id: 案件編號

        Returns:
            bool: 是否刪除成功
        """
        try:
            # 取得案件資料
            case = self.get_case_by_id(case_id)
            if not case:
                print(f"❌ 找不到案件: {case_id}")
                return False

            print(f"🗂️ 準備刪除案件資料夾 - 案件: {case.case_id}, 當事人: {case.client}, 類型: {case.case_type}")

            # 嘗試多種方法取得資料夾路徑
            folder_path = None

            # 方法1：使用 folder_manager
            if hasattr(self.folder_manager, 'get_case_folder_path'):
                try:
                    folder_path = self.folder_manager.get_case_folder_path(case)
                    print(f"📁 方法1 (folder_manager) 取得路徑: {folder_path}")
                except Exception as e:
                    print(f"⚠️ 方法1 失敗: {e}")

            # 方法2：使用 operations
            if not folder_path and hasattr(self.folder_manager, 'operations') and self.folder_manager.operations:
                try:
                    folder_path = self.folder_manager.operations.get_case_folder_path(case)
                    print(f"📁 方法2 (operations) 取得路徑: {folder_path}")
                except Exception as e:
                    print(f"⚠️ 方法2 失敗: {e}")

            # 檢查路徑是否有效
            if not folder_path:
                print(f"❌ 無法取得有效的資料夾路徑")
                return False

            # 檢查資料夾是否存在
            import os
            if not os.path.exists(folder_path):
                print(f"ℹ️ 資料夾不存在，視為刪除成功: {folder_path}")
                return True

            # 顯示資料夾資訊
            try:
                folder_contents = os.listdir(folder_path)
                print(f"📋 資料夾內容: {len(folder_contents)} 個項目")
                if folder_contents:
                    print(f"   項目: {folder_contents[:5]}{'...' if len(folder_contents) > 5 else ''}")
            except Exception as e:
                print(f"⚠️ 無法讀取資料夾內容: {e}")

            # 嘗試刪除資料夾
            deletion_success = False

            # 嘗試1：使用 folder_manager 的刪除方法
            if hasattr(self.folder_manager, 'delete_case_folder'):
                try:
                    deletion_success = self.folder_manager.delete_case_folder(case)
                    print(f"🗑️ 方法1 (folder_manager.delete_case_folder): {'成功' if deletion_success else '失敗'}")
                except Exception as e:
                    print(f"⚠️ 方法1 刪除失敗: {e}")

            # 嘗試2：使用 operations 的刪除方法
            if not deletion_success and hasattr(self.folder_manager, 'operations') and self.folder_manager.operations:
                try:
                    success, message = self.folder_manager.operations.delete_case_folder(case)
                    deletion_success = success
                    print(f"🗑️ 方法2 (operations.delete_case_folder): {'成功' if success else '失敗'} - {message}")
                except Exception as e:
                    print(f"⚠️ 方法2 刪除失敗: {e}")

            # 嘗試3：直接使用 shutil.rmtree（最終備用方案）
            if not deletion_success:
                try:
                    import shutil
                    shutil.rmtree(folder_path)
                    deletion_success = True
                    print(f"🗑️ 方法3 (直接刪除): 成功")
                except Exception as e:
                    print(f"❌ 方法3 刪除失敗: {e}")

            # 驗證刪除結果
            if deletion_success:
                # 再次檢查資料夾是否真的被刪除
                if os.path.exists(folder_path):
                    print(f"⚠️ 警告：刪除操作回報成功，但資料夾仍然存在: {folder_path}")
                    deletion_success = False
                else:
                    print(f"✅ 成功刪除案件資料夾: {folder_path}")

            return deletion_success

        except Exception as e:
            print(f"❌ CaseController.delete_case_folder 失敗: {e}")
            import traceback
            traceback.print_exc()
            return False


    def _delete_case_folder_basic(self, case: CaseData) -> bool:
        """備用的資料夾刪除方法"""
        try:
            import shutil
            folder_path = self.get_case_folder_path(case.case_id)
            if folder_path and os.path.exists(folder_path):
                shutil.rmtree(folder_path)
                print(f"✅ 使用備用方法成功刪除資料夾: {folder_path}")
                return True
            else:
                print(f"ℹ️ 資料夾不存在，無需刪除: {case.client}")
                return True
        except Exception as e:
            print(f"❌ 備用刪除方法失敗: {e}")
            return False

    # ==================== 匯入匯出相關 ====================

    def import_from_excel(self, file_path: str, merge_option: str = 'skip') -> Tuple[bool, Dict[str, Any]]:
        """從Excel匯入案件資料"""
        try:
            result = self.import_export.import_from_excel(file_path, merge_option)
            if result[0]:  # 如果成功
                self.load_cases()  # 重新載入資料
                self._sync_managers()
            return result
        except Exception as e:
            print(f"CaseController.import_from_excel 失敗: {e}")
            return False, {'error': str(e)}

    def export_to_excel(self, file_path: str = None, cases: List[CaseData] = None) -> bool:
        """匯出案件資料到Excel"""
        try:
            if cases is None:
                cases = self.get_cases()
            return self.import_export.export_to_excel(file_path, cases)
        except Exception as e:
            print(f"CaseController.export_to_excel 失敗: {e}")
            return False

    # ==================== 統計和查詢相關 ====================

    def get_case_statistics(self) -> Dict[str, Any]:
        """取得案件統計資訊"""
        try:
            return self.data_manager.get_case_statistics()
        except Exception as e:
            print(f"CaseController.get_case_statistics 失敗: {e}")
            return {}

    def get_cases_by_type(self, case_type: str) -> List[CaseData]:
        """根據類型取得案件"""
        try:
            all_cases = self.get_cases()
            return [case for case in all_cases if case.case_type == case_type]
        except Exception as e:
            print(f"CaseController.get_cases_by_type 失敗: {e}")
            return []

    def get_cases_by_progress(self, progress: str) -> List[CaseData]:
        """根據進度取得案件"""
        try:
            all_cases = self.get_cases()
            return [case for case in all_cases if case.progress == progress]
        except Exception as e:
            print(f"CaseController.get_cases_by_progress 失敗: {e}")
            return []

    # ==================== 輔助方法 ====================

    def get_available_case_types(self) -> List[str]:
        """取得可用的案件類型"""
        return list(AppConfig.CASE_TYPE_FOLDERS.keys())

    def get_available_progress_options(self, case_type: str) -> List[str]:
        """取得可用的進度選項"""
        return AppConfig.get_progress_options(case_type)

    def refresh_data(self) -> bool:
        """刷新所有資料"""
        try:
            result = self.load_cases()
            if result:
                self._sync_managers()
            return result
        except Exception as e:
            print(f"CaseController.refresh_data 失敗: {e}")
            return False

    # ==================== 偵錯和診斷方法 ====================

    def diagnose_folder_manager(self) -> Dict[str, Any]:
        """診斷 FolderManager 的狀態"""
        diagnosis = {
            'folder_manager_exists': hasattr(self, 'folder_manager'),
            'folder_manager_type': type(self.folder_manager).__name__ if hasattr(self, 'folder_manager') else None,
            'available_methods': [],
            'creator_exists': False,
            'operations_exists': False
        }

        if hasattr(self, 'folder_manager'):
            diagnosis['available_methods'] = [method for method in dir(self.folder_manager) if not method.startswith('_')]
            diagnosis['creator_exists'] = hasattr(self.folder_manager, 'creator')
            diagnosis['operations_exists'] = hasattr(self.folder_manager, 'operations')

        return diagnosis