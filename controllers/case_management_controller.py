#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
案件管理控制器 - 統一的案件操作介面
整合Excel處理和資料夾管理功能
"""

import os
import sys
from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path

# 動態匯入處理
try:
    from utils.file_operations.excel_handler import ExcelHandler
    from utils.folder_management import FolderManager
    print("✅ 從新模組結構匯入成功")
except ImportError:
    try:
        from utils.excel_handler import ExcelHandler
        from utils.folder_manager import FolderManager
        print("✅ 從舊模組結構匯入成功")
    except ImportError:
        print("⚠️ 警告：無法匯入必要模組，請確認模組檔案存在")
        # 提供基本的替代實作
        class ExcelHandler:
            @staticmethod
            def analyze_excel_sheets(file_path):
                return False, "ExcelHandler 不可用", {}
            @staticmethod
            def import_cases_from_excel(file_path):
                return None
            def export_cases_to_excel(self, cases, file_path):
                return False

        class FolderManager:
            def __init__(self, base_folder):
                self.base_folder = base_folder
            def create_case_folder_structure(self, case_data):
                return False
            def get_case_folder_path(self, case_data):
                return None

class CaseManagementController:
    """案件管理控制器 - 統一的案件操作介面"""

    def __init__(self, data_folder: str = "data"):
        """初始化控制器"""
        self.data_folder = data_folder

        # 確保資料夾存在
        Path(data_folder).mkdir(parents=True, exist_ok=True)

        # 初始化服務層組件
        self.excel_handler = ExcelHandler()
        self.folder_manager = FolderManager(data_folder)

        # 檢查組件狀態
        self._check_components()

    def _check_components(self):
        """檢查組件狀態"""
        print("🔧 案件管理控制器初始化:")

        # 檢查Excel處理器
        try:
            if hasattr(self.excel_handler, 'get_dependency_status'):
                print(self.excel_handler.get_dependency_status())
            else:
                print("📦 Excel處理器: 基本功能可用")
        except Exception as e:
            print(f"⚠️ Excel處理器檢查失敗: {e}")

        # 檢查資料夾管理器
        print(f"📁 資料夾管理器: {self.data_folder}")

        if not os.path.exists(self.data_folder):
            print(f"⚠️ 資料夾不存在，將自動建立: {self.data_folder}")
            os.makedirs(self.data_folder, exist_ok=True)

    # ==================== 案件資料夾操作 ====================

    def create_case_folder(self, case_data) -> Tuple[bool, str]:
        """建立案件資料夾"""
        try:
            success = self.folder_manager.create_case_folder_structure(case_data)
            if success:
                folder_path = self.folder_manager.get_case_folder_path(case_data)
                return True, folder_path or "建立成功"
            else:
                return False, "建立失敗"

        except Exception as e:
            return False, f"建立失敗: {e}"

    def get_case_folder_info(self, case_data) -> Dict[str, Any]:
        """取得案件資料夾資訊"""
        try:
            if hasattr(self.folder_manager, 'get_case_folder_info'):
                return self.folder_manager.get_case_folder_info(case_data)
            else:
                # 基本實作
                folder_path = self.folder_manager.get_case_folder_path(case_data)

                if not folder_path or not os.path.exists(folder_path):
                    return {
                        'exists': False,
                        'path': None,
                        'has_files': False,
                        'file_count': 0,
                        'size_mb': 0
                    }

                # 計算檔案數量和大小
                total_files = 0
                total_size = 0

                for root, dirs, files in os.walk(folder_path):
                    total_files += len(files)
                    for file in files:
                        try:
                            file_path = os.path.join(root, file)
                            total_size += os.path.getsize(file_path)
                        except:
                            pass

                return {
                    'exists': True,
                    'path': folder_path,
                    'has_files': total_files > 0,
                    'file_count': total_files,
                    'size_mb': round(total_size / (1024 * 1024), 2)
                }

        except Exception as e:
            print(f"取得案件資料夾資訊失敗: {e}")
            return {
                'exists': False,
                'path': None,
                'has_files': False,
                'file_count': 0,
                'size_mb': 0,
                'error': str(e)
            }

    def list_all_case_folders(self) -> List[str]:
        """列出所有案件資料夾"""
        try:
            return self.folder_manager.list_case_folders()
        except Exception as e:
            print(f"列出案件資料夾失敗: {e}")
            return []

    def validate_case_folder_structure(self, case_data) -> Dict[str, Any]:
        """驗證案件資料夾結構"""
        try:
            if hasattr(self.folder_manager, 'validate_folder_structure'):
                return self.folder_manager.validate_folder_structure(case_data)
            else:
                # 基本驗證
                folder_path = self.folder_manager.get_case_folder_path(case_data)
                return {
                    'valid': folder_path is not None and os.path.exists(folder_path),
                    'message': '基本驗證完成',
                    'path': folder_path
                }
        except Exception as e:
            return {
                'valid': False,
                'message': f'驗證失敗: {e}',
                'path': None
            }

    def repair_case_folder_structure(self, case_data) -> bool:
        """修復案件資料夾結構"""
        try:
            if hasattr(self.folder_manager, 'repair_folder_structure'):
                return self.folder_manager.repair_folder_structure(case_data)
            else:
                # 基本修復：重新建立資料夾
                return self.folder_manager.create_case_folder_structure(case_data)
        except Exception as e:
            print(f"修復資料夾結構失敗: {e}")
            return False

    # ==================== Excel 操作 ====================

    def import_cases_from_excel(self, file_path: str) -> Tuple[bool, str, Optional[List]]:
        """從Excel匯入案件"""
        try:
            if not os.path.exists(file_path):
                return False, "檔案不存在", None

            cases = self.excel_handler.import_cases_from_excel(file_path)

            if cases:
                return True, f"成功匯入 {len(cases)} 筆案件", cases
            else:
                return False, "匯入失敗或檔案為空", None

        except Exception as e:
            return False, f"匯入失敗: {e}", None

    def export_cases_to_excel(self, cases: List[Dict], file_path: str) -> Tuple[bool, str]:
        """匯出案件到Excel"""
        try:
            success = self.excel_handler.export_cases_to_excel(cases, file_path)

            if success:
                return True, f"成功匯出 {len(cases)} 筆案件"
            else:
                return False, "匯出失敗"

        except Exception as e:
            return False, f"匯出失敗: {e}"

    def analyze_excel_file(self, file_path: str) -> Tuple[bool, str, Dict]:
        """分析Excel檔案結構"""
        try:
            return self.excel_handler.analyze_excel_sheets(file_path)
        except Exception as e:
            return False, f"分析失敗: {e}", {}

    def validate_excel_data(self, file_path: str, sheet_name: Optional[str] = None) -> Tuple[bool, str, Dict]:
        """驗證Excel資料"""
        try:
            if hasattr(self.excel_handler, 'validate_excel_data'):
                return self.excel_handler.validate_excel_data(file_path, sheet_name)
            else:
                # 基本驗證
                success, message, sheet_info = self.analyze_excel_file(file_path)
                if success:
                    return True, "基本驗證完成", sheet_info
                else:
                    return False, message, {}
        except Exception as e:
            return False, f"驗證失敗: {e}", {}

    def get_excel_preview(self, file_path: str, sheet_name: Optional[str] = None, rows: int = 10) -> Tuple[bool, str, Dict]:
        """取得Excel預覽"""
        try:
            if hasattr(self.excel_handler, 'get_excel_preview'):
                return self.excel_handler.get_excel_preview(file_path, sheet_name, rows)
            else:
                # 基本預覽
                import pandas as pd
                df = pd.read_excel(file_path, sheet_name=sheet_name, nrows=rows)

                preview_data = {
                    'columns': df.columns.tolist(),
                    'data': df.to_dict('records'),
                    'total_rows_read': len(df),
                    'sheet_name': sheet_name or 'Sheet1'
                }

                return True, "預覽完成", preview_data
        except Exception as e:
            return False, f"預覽失敗: {e}", {}

    # ==================== 整合操作 ====================

    def create_case_with_folder(self, case_data) -> Tuple[bool, str, Dict]:
        """建立案件並自動建立資料夾"""
        try:
            # 1. 建立資料夾
            folder_success, folder_message = self.create_case_folder(case_data)

            if not folder_success:
                return False, f"資料夾建立失敗: {folder_message}", {}

            # 2. 取得資料夾資訊
            folder_info = self.get_case_folder_info(case_data)

            # 3. 返回結果
            return True, "案件建立成功", {
                'folder_created': True,
                'folder_info': folder_info,
                'case_data': case_data.__dict__ if hasattr(case_data, '__dict__') else str(case_data)
            }

        except Exception as e:
            return False, f"案件建立失敗: {e}", {}

    def batch_import_and_create_folders(self, excel_file_path: str) -> Dict[str, Any]:
        """批次匯入並建立案件資料夾"""
        result = {
            'success': False,
            'total_imported': 0,
            'total_folders_created': 0,
            'failed_cases': [],
            'successful_cases': [],
            'message': ''
        }

        try:
            # 1. 從Excel匯入案件資料
            import_success, import_message, cases = self.import_cases_from_excel(excel_file_path)

            if not import_success:
                result['message'] = import_message
                return result

            # 2. 為每個案件建立資料夾
            for i, case_dict in enumerate(cases):
                try:
                    # 建立簡單的案件物件
                    case_obj = type('CaseData', (), case_dict)()

                    # 建立資料夾
                    folder_success, folder_message = self.create_case_folder(case_obj)

                    if folder_success:
                        result['total_folders_created'] += 1
                        result['successful_cases'].append({
                            'index': i,
                            'case': case_dict,
                            'folder_path': folder_message
                        })
                    else:
                        result['failed_cases'].append({
                            'index': i,
                            'case': case_dict,
                            'error': folder_message
                        })

                except Exception as e:
                    result['failed_cases'].append({
                        'index': i,
                        'case': case_dict,
                        'error': str(e)
                    })

            result['total_imported'] = len(cases)
            result['success'] = True
            result['message'] = f"匯入 {len(cases)} 筆案件，成功建立 {result['total_folders_created']} 個資料夾"

        except Exception as e:
            result['message'] = f"批次處理失敗: {e}"

        return result

    def validate_all_case_folders(self) -> Dict[str, Any]:
        """驗證所有案件資料夾"""
        result = {
            'total_folders': 0,
            'valid_folders': 0,
            'invalid_folders': [],
            'recommendations': []
        }

        try:
            folders = self.list_all_case_folders()
            result['total_folders'] = len(folders)

            for folder_name in folders:
                folder_path = os.path.join(self.data_folder, folder_name)

                # 檢查資料夾結構
                required_subfolders = ["案件資訊", "法院文件", "當事人資料"]
                missing_subfolders = []

                for subfolder in required_subfolders:
                    subfolder_path = os.path.join(folder_path, subfolder)
                    if not os.path.exists(subfolder_path):
                        missing_subfolders.append(subfolder)

                if missing_subfolders:
                    result['invalid_folders'].append({
                        'folder': folder_name,
                        'missing_subfolders': missing_subfolders
                    })
                else:
                    result['valid_folders'] += 1

            # 產生建議
            if result['invalid_folders']:
                result['recommendations'].append("部分案件資料夾結構不完整，建議使用修復功能")

            if result['valid_folders'] == result['total_folders']:
                result['recommendations'].append("所有案件資料夾結構完整")

        except Exception as e:
            result['error'] = str(e)

        return result

    def get_system_status(self) -> Dict[str, Any]:
        """取得系統狀態"""
        try:
            # Excel處理器狀態
            excel_status = {}
            try:
                if hasattr(self.excel_handler, 'check_dependencies'):
                    excel_status = self.excel_handler.check_dependencies()
                else:
                    excel_status = {'basic_functions': True}
            except:
                excel_status = {'error': True}

            # 資料夾狀態
            folder_validation = self.validate_all_case_folders()

            return {
                'excel_handler': excel_status,
                'folder_manager': {
                    'base_folder': self.data_folder,
                    'folder_exists': os.path.exists(self.data_folder),
                    'validation': folder_validation
                },
                'system_health': {
                    'components_loaded': True,
                    'ready_for_operations': True
                }
            }

        except Exception as e:
            return {
                'error': str(e),
                'system_health': {
                    'components_loaded': False,
                    'ready_for_operations': False
                }
            }