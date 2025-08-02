#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
資料夾服務 - 重構版本
統一所有資料夾相關的業務邏輯
整合新重構的 FolderManager、FileValidator 等模組
"""

import os
from typing import Optional, List, Dict, Any, Tuple
from models.case_model import CaseData

# 匯入重構後的模組
try:
    from utils.file_operations.folder_manager import FolderManager
    from utils.file_operations.file_validator import FileValidator
    from utils.file_operations.excel_handler import ExcelHandler
    CORE_MODULES_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ 警告：無法匯入核心模組 - {e}")
    print("⚠️ 嘗試使用舊版模組...")

    # 回退到舊版模組
    try:
        from utils.folder_manager import FolderManager
        from utils.excel_handler import ExcelHandler
        FileValidator = None
        CORE_MODULES_AVAILABLE = False
    except ImportError:
        FolderManager = None
        ExcelHandler = None
        FileValidator = None
        CORE_MODULES_AVAILABLE = False


class FolderService:
    """資料夾服務 - 統一資料夾操作業務邏輯"""

    def __init__(self, base_data_folder: str):
        """
        初始化資料夾服務

        Args:
            base_data_folder: 基礎資料資料夾路徑
        """
        self.base_data_folder = base_data_folder

        # 初始化核心元件
        if CORE_MODULES_AVAILABLE:
            self.folder_manager = FolderManager(base_data_folder) if FolderManager else None
            self.file_validator = FileValidator() if FileValidator else None
            self.excel_handler = ExcelHandler() if ExcelHandler else None
        else:
            # 回退模式
            self.folder_manager = FolderManager(base_data_folder) if FolderManager else None
            self.file_validator = None
            self.excel_handler = ExcelHandler() if ExcelHandler else None

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

            # 2. 使用資料夾管理器建立結構
            if not self.folder_manager:
                return False, "資料夾管理器不可用"

            success = self.folder_manager.create_case_folder_structure(case_data)

            if success:
                folder_path = self.folder_manager.get_case_folder_path(case_data)

                # 3. 建立案件資訊Excel
                if self.excel_handler and folder_path:
                    try:
                        excel_success, excel_result = self.excel_handler.create_case_info_excel(
                            os.path.join(folder_path, '案件資訊'), case_data
                        )
                        if not excel_success:
                            print(f"⚠️ Excel檔案建立失敗: {excel_result}")
                    except Exception as e:
                        print(f"⚠️ Excel檔案建立過程發生錯誤: {e}")

                return True, folder_path or "資料夾建立成功"
            else:
                return False, "資料夾建立失敗"

        except Exception as e:
            error_msg = f"建立案件資料夾失敗: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg

    def get_case_folder_path(self, case_data: CaseData) -> Optional[str]:
        """
        取得案件資料夾路徑

        Args:
            case_data: 案件資料

        Returns:
            資料夾路徑或None
        """
        try:
            if not self.folder_manager:
                return None

            return self.folder_manager.get_case_folder_path(case_data)

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
            if not self.folder_manager:
                return False, "資料夾管理器不可用"

            return self.folder_manager.delete_case_folder(case_data, confirm)

        except Exception as e:
            error_msg = f"刪除案件資料夾失敗: {str(e)}"
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
        try:
            if not self.folder_manager:
                return {'exists': False, 'error': '資料夾管理器不可用'}

            folder_info = self.folder_manager.get_case_folder_info(case_data)

            # 增加驗證資訊
            if self.file_validator and folder_info.get('exists'):
                try:
                    validation = self.file_validator.validate_folder_structure(folder_info['path'])
                    folder_info['validation'] = validation
                except Exception as e:
                    folder_info['validation_error'] = str(e)

            return folder_info

        except Exception as e:
            return {
                'exists': False,
                'error': f'取得資料夾資訊失敗: {str(e)}'
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
            if not self.folder_manager:
                return False, "資料夾管理器不可用"

            # 清理階段名稱
            if self.file_validator:
                clean_stage_name = self.file_validator.sanitize_folder_name(stage_name)
            else:
                clean_stage_name = stage_name

            success = self.folder_manager.create_progress_folder(case_data, clean_stage_name)

            if success:
                stage_path = self.folder_manager.get_stage_folder_path(case_data, clean_stage_name)
                return True, stage_path or f"階段資料夾建立成功: {clean_stage_name}"
            else:
                return False, f"階段資料夾建立失敗: {stage_name}"

        except Exception as e:
            error_msg = f"建立進度階段資料夾失敗: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg

    def delete_progress_folder(self, case_data: CaseData, stage_name: str) -> Tuple[bool, str]:
        """
        刪除進度階段資料夾

        Args:
            case_data: 案件資料
            stage_name: 階段名稱

        Returns:
            (success, message)
        """
        try:
            if not self.folder_manager:
                return False, "資料夾管理器不可用"

            success = self.folder_manager.delete_progress_folder(case_data, stage_name)

            if success:
                return True, f"階段資料夾刪除成功: {stage_name}"
            else:
                return False, f"階段資料夾刪除失敗: {stage_name}"

        except Exception as e:
            error_msg = f"刪除進度階段資料夾失敗: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg

    def get_stage_folder_path(self, case_data: CaseData, stage_name: str) -> Optional[str]:
        """
        取得階段資料夾路徑

        Args:
            case_data: 案件資料
            stage_name: 階段名稱

        Returns:
            階段資料夾路徑或None
        """
        try:
            if not self.folder_manager:
                return None

            return self.folder_manager.get_stage_folder_path(case_data, stage_name)

        except Exception as e:
            print(f"❌ 取得階段資料夾路徑失敗: {e}")
            return None

    # ====== Excel檔案管理 ======

    def create_case_info_excel(self, case_data: CaseData) -> Tuple[bool, str]:
        """
        建立案件資訊Excel檔案

        Args:
            case_data: 案件資料

        Returns:
            (success, message_or_path)
        """
        try:
            if not self.excel_handler:
                return False, "Excel處理器不可用"

            case_folder = self.get_case_folder_path(case_data)
            if not case_folder:
                return False, f"找不到案件資料夾: {case_data.client}"

            case_info_folder = os.path.join(case_folder, '案件資訊')

            return self.excel_handler.create_case_info_excel(case_info_folder, case_data)

        except Exception as e:
            error_msg = f"建立案件資訊Excel失敗: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg

    def update_case_info_excel(self, case_data: CaseData) -> Tuple[bool, str]:
        """
        更新案件資訊Excel檔案

        Args:
            case_data: 案件資料

        Returns:
            (success, message)
        """
        try:
            if not self.excel_handler:
                return False, "Excel處理器不可用"

            case_folder = self.get_case_folder_path(case_data)
            if not case_folder:
                return False, f"找不到案件資料夾: {case_data.client}"

            success = self.excel_handler.update_case_info_excel(case_folder, case_data)

            if success:
                return True, "案件資訊Excel更新成功"
            else:
                return False, "案件資訊Excel更新失敗"

        except Exception as e:
            error_msg = f"更新案件資訊Excel失敗: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg

    # ====== 驗證功能 ======

    def validate_folder_structure(self, case_data: CaseData) -> Dict[str, Any]:
        """
        驗證案件資料夾結構

        Args:
            case_data: 案件資料

        Returns:
            驗證結果字典
        """
        try:
            if self.file_validator:
                case_folder = self.get_case_folder_path(case_data)
                if case_folder:
                    return self.file_validator.validate_folder_structure(case_folder)
                else:
                    return {
                        'is_valid': False,
                        'errors': ['找不到案件資料夾'],
                        'missing_folders': [],
                        'warnings': []
                    }
            elif self.folder_manager:
                # 使用資料夾管理器的驗證功能
                return self.folder_manager.validate_folder_structure(case_data)
            else:
                return {
                    'is_valid': False,
                    'errors': ['驗證器不可用'],
                    'missing_folders': [],
                    'warnings': []
                }

        except Exception as e:
            return {
                'is_valid': False,
                'errors': [f'驗證過程發生錯誤: {str(e)}'],
                'missing_folders': [],
                'warnings': []
            }

    def validate_case_data(self, case_data: CaseData) -> Dict[str, Any]:
        """
        驗證案件資料

        Args:
            case_data: 案件資料

        Returns:
            驗證結果字典
        """
        try:
            if self.file_validator:
                return self.file_validator.validate_case_data(case_data)
            else:
                # 基本驗證
                result = {
                    'is_valid': True,
                    'errors': [],
                    'warnings': []
                }

                if not case_data.client:
                    result['errors'].append("當事人姓名為必填欄位")
                if not case_data.case_type:
                    result['errors'].append("案件類型為必填欄位")

                if result['errors']:
                    result['is_valid'] = False

                return result

        except Exception as e:
            return {
                'is_valid': False,
                'errors': [f'驗證過程發生錯誤: {str(e)}'],
                'warnings': []
            }

    def _validate_case_data(self, case_data: CaseData) -> bool:
        """內部驗證案件資料"""
        try:
            validation = self.validate_case_data(case_data)
            return validation.get('is_valid', False)
        except Exception:
            return False

    # ====== 批量操作功能 ======

    def create_multiple_case_folders(self, case_list: List[CaseData]) -> Dict[str, Any]:
        """
        批量建立案件資料夾

        Args:
            case_list: 案件資料列表

        Returns:
            批量操作結果
        """
        result = {
            'total': len(case_list),
            'success': 0,
            'failed': 0,
            'details': [],
            'errors': []
        }

        try:
            for i, case_data in enumerate(case_list):
                try:
                    success, message = self.create_case_folder(case_data)

                    detail = {
                        'index': i,
                        'client': case_data.client,
                        'success': success,
                        'message': message
                    }

                    result['details'].append(detail)

                    if success:
                        result['success'] += 1
                        print(f"✅ [{i+1}/{len(case_list)}] {case_data.client}")
                    else:
                        result['failed'] += 1
                        print(f"❌ [{i+1}/{len(case_list)}] {case_data.client}: {message}")

                except Exception as e:
                    result['failed'] += 1
                    error_msg = f"處理第 {i+1} 個案件失敗: {str(e)}"
                    result['errors'].append(error_msg)
                    print(f"❌ [{i+1}/{len(case_list)}] {error_msg}")

            print(f"\n📊 批量建立完成: 成功 {result['success']}, 失敗 {result['failed']}")

        except Exception as e:
            result['errors'].append(f"批量操作失敗: {str(e)}")

        return result

    def validate_multiple_folders(self, case_list: List[CaseData]) -> Dict[str, Any]:
        """
        批量驗證案件資料夾

        Args:
            case_list: 案件資料列表

        Returns:
            批量驗證結果
        """
        result = {
            'total': len(case_list),
            'valid': 0,
            'invalid': 0,
            'details': [],
            'summary': {}
        }

        try:
            all_issues = []

            for i, case_data in enumerate(case_list):
                try:
                    validation = self.validate_folder_structure(case_data)

                    detail = {
                        'index': i,
                        'client': case_data.client,
                        'is_valid': validation.get('is_valid', False),
                        'errors': validation.get('errors', []),
                        'warnings': validation.get('warnings', []),
                        'missing_folders': validation.get('missing_folders', [])
                    }

                    result['details'].append(detail)

                    if detail['is_valid']:
                        result['valid'] += 1
                    else:
                        result['invalid'] += 1
                        all_issues.extend(detail['errors'])

                except Exception as e:
                    result['invalid'] += 1
                    result['details'].append({
                        'index': i,
                        'client': case_data.client,
                        'is_valid': False,
                        'errors': [f'驗證失敗: {str(e)}'],
                        'warnings': [],
                        'missing_folders': []
                    })

            # 生成摘要
            from collections import Counter
            result['summary'] = {
                'common_issues': dict(Counter(all_issues)),
                'validation_rate': (result['valid'] / result['total'] * 100) if result['total'] > 0 else 0
            }

        except Exception as e:
            result['errors'] = [f"批量驗證失敗: {str(e)}"]

        return result

    # ====== 修復功能 ======

    def auto_repair_folder_structure(self, case_data: CaseData, dry_run: bool = True) -> Dict[str, Any]:
        """
        自動修復案件資料夾結構

        Args:
            case_data: 案件資料
            dry_run: 是否僅模擬執行

        Returns:
            修復結果
        """
        try:
            if self.file_validator:
                case_folder = self.get_case_folder_path(case_data)
                if case_folder:
                    return self.file_validator.auto_fix_folder_structure(case_folder, dry_run)
                else:
                    return {
                        'success': False,
                        'actions_taken': [],
                        'errors': ['找不到案件資料夾']
                    }
            else:
                return {
                    'success': False,
                    'actions_taken': [],
                    'errors': ['修復功能不可用']
                }

        except Exception as e:
            return {
                'success': False,
                'actions_taken': [],
                'errors': [f'修復過程發生錯誤: {str(e)}']
            }

    # ====== 狀態查詢功能 ======

    def get_service_status(self) -> Dict[str, Any]:
        """
        取得服務狀態

        Returns:
            服務狀態字典
        """
        status = {
            'service_available': True,
            'components': {},
            'base_folder': self.base_data_folder,
            'base_folder_exists': os.path.exists(self.base_data_folder)
        }

        try:
            # 檢查各元件狀態
            status['components']['folder_manager'] = {
                'available': self.folder_manager is not None,
                'type': type(self.folder_manager).__name__ if self.folder_manager else None
            }

            status['components']['file_validator'] = {
                'available': self.file_validator is not None,
                'type': type(self.file_validator).__name__ if self.file_validator else None
            }

            status['components']['excel_handler'] = {
                'available': self.excel_handler is not None,
                'type': type(self.excel_handler).__name__ if self.excel_handler else None
            }

            # 檢查Excel處理器依賴
            if self.excel_handler and hasattr(self.excel_handler, 'is_available'):
                status['components']['excel_handler']['excel_ready'] = self.excel_handler.is_available()

            # 總體可用性檢查
            essential_components = [self.folder_manager]
            status['service_available'] = all(comp is not None for comp in essential_components)

        except Exception as e:
            status['error'] = str(e)
            status['service_available'] = False

        return status

    def get_statistics(self) -> Dict[str, Any]:
        """
        取得資料夾服務統計資訊

        Returns:
            統計資訊字典
        """
        stats = {
            'base_folder_info': {},
            'case_type_distribution': {},
            'total_case_folders': 0
        }

        try:
            # 基礎資料夾資訊
            if os.path.exists(self.base_data_folder):
                stats['base_folder_info'] = self._get_folder_size_info(self.base_data_folder)

                # 統計案件類型分佈
                from config.settings import AppConfig
                case_type_folders = AppConfig.CASE_TYPE_FOLDERS

                for case_type, folder_name in case_type_folders.items():
                    type_folder = os.path.join(self.base_data_folder, folder_name)
                    if os.path.exists(type_folder):
                        case_count = len([d for d in os.listdir(type_folder)
                                        if os.path.isdir(os.path.join(type_folder, d))])
                        stats['case_type_distribution'][case_type] = case_count
                        stats['total_case_folders'] += case_count

        except Exception as e:
            stats['error'] = str(e)

        return stats

    def _get_folder_size_info(self, folder_path: str) -> Dict[str, Any]:
        """取得資料夾大小資訊"""
        try:
            total_size = 0
            total_files = 0

            for root, dirs, files in os.walk(folder_path):
                total_files += len(files)
                for file in files:
                    try:
                        file_path = os.path.join(root, file)
                        total_size += os.path.getsize(file_path)
                    except:
                        pass

            return {
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'total_files': total_files,
                'total_folders': len([d for d in os.listdir(folder_path)
                                    if os.path.isdir(os.path.join(folder_path, d))])
            }

        except Exception as e:
            return {'error': str(e)}

    # ====== 向後相容方法 ======

    def create_case_folder_structure(self, case_data: CaseData) -> bool:
        """向後相容的資料夾建立方法"""
        success, message = self.create_case_folder(case_data)
        if not success:
            print(f"❌ {message}")
        return success

    def get_case_folder_path_legacy(self, case_data: CaseData) -> Optional[str]:
        """向後相容的路徑取得方法"""
        return self.get_case_folder_path(case_data)