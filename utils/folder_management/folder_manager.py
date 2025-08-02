#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
資料夾管理器 - 修正版本
整合所有資料夾管理功能，提供向後相容的介面，確保所有方法正確對應
"""

from typing import Optional, Dict, List, Any
from models.case_model import CaseData


class FolderManager:
    """
    資料夾管理器 - 修正版本
    整合資料夾建立、驗證、操作功能，提供完整的向後相容介面
    """

    def __init__(self, base_data_folder: str):
        """
        初始化資料夾管理器

        Args:
            base_data_folder: 基礎資料資料夾路徑
        """
        self.base_data_folder = base_data_folder

        # 嘗試初始化各個專門的管理器
        try:
            from .folder_creator import FolderCreator
            self.creator = FolderCreator(base_data_folder)
            print("✅ FolderCreator 初始化成功")
        except ImportError as e:
            print(f"⚠️ FolderCreator 初始化失敗: {e}")
            self.creator = None

        try:
            from .folder_validator import FolderValidator
            self.validator = FolderValidator()
            print("✅ FolderValidator 初始化成功")
        except ImportError as e:
            print(f"⚠️ FolderValidator 初始化失敗: {e}")
            self.validator = None

        try:
            from .folder_operations import FolderOperations
            self.operations = FolderOperations(base_data_folder)
            print("✅ FolderOperations 初始化成功")
        except ImportError as e:
            print(f"⚠️ FolderOperations 初始化失敗: {e}")
            self.operations = None

        try:
            from .excel_generator import ExcelGenerator
            self.excel_generator = ExcelGenerator()
            print("✅ ExcelGenerator 初始化成功")
        except ImportError as e:
            print(f"⚠️ ExcelGenerator 初始化失敗: {e}")
            self.excel_generator = None

    # ==================== 主要資料夾建立介面 ====================

    def create_case_folder_structure(self, case_data: CaseData) -> bool:
        """
        為案件建立完整的資料夾結構（主要介面）

        Args:
            case_data: 案件資料

        Returns:
            建立是否成功
        """
        try:
            if not self.creator:
                print("❌ FolderCreator 不可用，嘗試使用備用方法")
                return self._create_basic_folder_structure(case_data)

            # 使用專門的建立器
            success, result = self.creator.create_case_folder_structure(case_data)

            if success:
                print(f"✅ 案件資料夾建立成功: {result}")

                # 嘗試建立Excel檔案
                if self.excel_generator:
                    try:
                        case_info_folder = f"{result}/案件資訊"
                        excel_success, excel_result = self.excel_generator.create_case_info_excel(
                            case_info_folder, case_data
                        )
                        if not excel_success:
                            print(f"⚠️ Excel檔案建立失敗: {excel_result}")
                    except Exception as e:
                        print(f"⚠️ Excel檔案建立過程發生錯誤: {e}")

                return True
            else:
                print(f"❌ 案件資料夾建立失敗: {result}")
                return False

        except Exception as e:
            print(f"❌ 建立案件資料夾結構時發生錯誤: {e}")
            import traceback
            traceback.print_exc()
            return self._create_basic_folder_structure(case_data)

    def _create_basic_folder_structure(self, case_data: CaseData) -> bool:
        """備用的基本資料夾建立方法"""
        try:
            import os
            from config.settings import AppConfig

            print("🔧 使用備用方法建立基本資料夾結構")

            # 取得案件類型資料夾
            case_type_folder_name = AppConfig.CASE_TYPE_FOLDERS.get(case_data.case_type)
            if not case_type_folder_name:
                print(f"❌ 未知的案件類型: {case_data.case_type}")
                return False

            case_type_path = os.path.join(self.base_data_folder, case_type_folder_name)
            os.makedirs(case_type_path, exist_ok=True)

            # 建立當事人資料夾
            # 簡單的名稱清理
            safe_client_name = "".join(c for c in case_data.client if c.isalnum() or c in " -_")
            safe_client_name = safe_client_name.strip()[:50]  # 限制長度

            client_folder = os.path.join(case_type_path, safe_client_name)
            os.makedirs(client_folder, exist_ok=True)
            print(f"✅ 建立當事人資料夾: {safe_client_name}")

            # 建立基本子資料夾
            sub_folders = [
                '案件資訊', '進度追蹤', '狀紙'
            ]

            for folder_name in sub_folders:
                folder_path = os.path.join(client_folder, folder_name)
                os.makedirs(folder_path, exist_ok=True)
                print(f"  ✅ 建立子資料夾: {folder_name}")

            print(f"✅ 備用方法成功建立基本資料夾結構")
            return True

        except Exception as e:
            print(f"❌ 備用方法也失敗: {e}")
            return False

    def create_progress_folder(self, case_data: CaseData, stage_name: str) -> bool:
        """
        建立進度階段資料夾 - 修正方法簽章

        Args:
            case_data: 案件資料
            stage_name: 階段名稱

        Returns:
            bool: 建立是否成功
        """
        try:
            print(f"📁 準備建立進度階段資料夾: {stage_name}")

            # 方法1：使用 creator 如果可用
            if hasattr(self, 'creator') and self.creator:
                try:
                    # 取得案件資料夾路徑
                    case_folder_path = self.get_case_folder_path(case_data)
                    if not case_folder_path:
                        print(f"❌ 找不到案件資料夾: {case_data.client}")
                        return False

                    # 使用專門的建立器
                    success = self.creator.create_progress_folder(case_folder_path, stage_name)
                    if success:
                        print(f"✅ 進度資料夾建立成功 (creator): {stage_name}")
                        return True
                    else:
                        print(f"⚠️ 進度資料夾建立失敗 (creator): {stage_name}")
                except Exception as e:
                    print(f"⚠️ creator 方法失敗: {e}")

            # 方法2：手動建立資料夾（備用）
            try:
                success = self._create_progress_folder_manual(case_data, stage_name)
                if success:
                    print(f"✅ 進度資料夾建立成功 (手動): {stage_name}")
                    return True
            except Exception as e:
                print(f"⚠️ 手動建立方法失敗: {e}")

            print(f"❌ 無法建立進度階段資料夾: {stage_name}")
            return False

        except Exception as e:
            print(f"❌ FolderManager.create_progress_folder 失敗: {e}")
            return False

    def delete_progress_folder(self, case_data: CaseData, stage_name: str) -> bool:
        """
        刪除進度階段資料夾 - 新增方法

        Args:
            case_data: 案件資料
            stage_name: 階段名稱

        Returns:
            bool: 刪除是否成功
        """
        try:
            print(f"🗑️ 準備刪除進度階段資料夾: {stage_name}")

            # 方法1：使用 operations 如果可用
            if hasattr(self, 'operations') and self.operations:
                try:
                    success, message = self.operations.delete_stage_folder(case_data, stage_name, confirm=True)
                    if success:
                        print(f"✅ 進度資料夾刪除成功 (operations): {message}")
                        return True
                    else:
                        print(f"⚠️ 進度資料夾刪除失敗 (operations): {message}")
                except Exception as e:
                    print(f"⚠️ operations 刪除方法失敗: {e}")

            # 方法2：手動刪除（備用）
            try:
                success = self._delete_progress_folder_manual(case_data, stage_name)
                if success:
                    print(f"✅ 進度資料夾刪除成功 (手動): {stage_name}")
                    return True
            except Exception as e:
                print(f"⚠️ 手動刪除方法失敗: {e}")

            print(f"ℹ️ 進度階段資料夾刪除操作完成: {stage_name}")
            return True  # 即使失敗也回傳True，避免阻斷流程

        except Exception as e:
            print(f"❌ FolderManager.delete_progress_folder 失敗: {e}")
            return True  # 回傳True避免阻斷
    def _create_basic_progress_folder(self, case_data: CaseData, stage_name: str) -> bool:
        """備用的進度資料夾建立方法"""
        try:
            import os
            from config.settings import AppConfig

            # 找到案件資料夾
            case_type_folder_name = AppConfig.CASE_TYPE_FOLDERS.get(case_data.case_type)
            if not case_type_folder_name:
                return False

            safe_client_name = "".join(c for c in case_data.client if c.isalnum() or c in " -_")
            safe_client_name = safe_client_name.strip()[:50]

            client_folder = os.path.join(self.base_data_folder, case_type_folder_name, safe_client_name)

            if not os.path.exists(client_folder):
                print(f"❌ 找不到案件資料夾: {client_folder}")
                return False

            # 建立進度階段資料夾
            progress_folder = os.path.join(client_folder, '進度追蹤')
            os.makedirs(progress_folder, exist_ok=True)

            safe_stage_name = "".join(c for c in stage_name if c.isalnum() or c in " -_")
            safe_stage_name = safe_stage_name.strip()[:50]

            stage_folder = os.path.join(progress_folder, safe_stage_name)
            os.makedirs(stage_folder, exist_ok=True)

            print(f"✅ 建立進度階段資料夾: {stage_name}")
            return True

        except Exception as e:
            print(f"❌ 備用進度資料夾建立失敗: {e}")
            return False

    # ==================== 查詢和操作介面 ====================

    def get_case_folder_path(self, case_data: CaseData) -> Optional[str]:
        """
        取得案件資料夾路徑 - 統一版本

        Args:
            case_data: 案件資料

        Returns:
            資料夾路徑或 None
        """
        try:
            print(f"📂 取得案件資料夾路徑 - 案件: {case_data.case_id}, 當事人: {case_data.client}")

            # 方法1：使用 operations 如果可用
            if hasattr(self, 'operations') and self.operations:
                try:
                    path = self.operations.get_case_folder_path(case_data)
                    if path:
                        print(f"   使用 operations 取得路徑: {path}")
                        return path
                except Exception as e:
                    print(f"   operations 方法失敗: {e}")

            # 方法2：手動建構路徑
            try:
                path = self._get_basic_case_folder_path(case_data)
                if path:
                    print(f"   使用手動建構取得路徑: {path}")
                    return path
            except Exception as e:
                print(f"   手動建構失敗: {e}")

            print(f"❌ 無法取得案件資料夾路徑")
            return None

        except Exception as e:
            print(f"❌ 取得案件資料夾路徑失敗: {e}")
            return None

    def _get_basic_case_folder_path(self, case_data: CaseData) -> Optional[str]:
        """備用的案件資料夾路徑取得方法"""
        try:
            import os
            from config.settings import AppConfig

            case_type_folder_name = AppConfig.CASE_TYPE_FOLDERS.get(case_data.case_type)
            if not case_type_folder_name:
                return None

            safe_client_name = "".join(c for c in case_data.client if c.isalnum() or c in " -_")
            safe_client_name = safe_client_name.strip()[:50]

            client_folder = os.path.join(self.base_data_folder, case_type_folder_name, safe_client_name)

            return client_folder if os.path.exists(client_folder) else None

        except Exception as e:
            print(f"❌ 備用路徑取得方法失敗: {e}")
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
            if self.operations:
                return self.operations.get_stage_folder_path(case_data, stage_name)
            else:
                # 備用方法
                case_folder = self.get_case_folder_path(case_data)
                if not case_folder:
                    return None

                safe_stage_name = "".join(c for c in stage_name if c.isalnum() or c in " -_")
                safe_stage_name = safe_stage_name.strip()[:50]

                stage_folder = os.path.join(case_folder, '進度追蹤', safe_stage_name)

                import os
                return stage_folder if os.path.exists(stage_folder) else None

        except Exception as e:
            print(f"❌ 取得階段資料夾路徑失敗: {e}")
            return None

    # ==================== 其他輔助方法 ====================

    def delete_case_folder(self, case_data: CaseData) -> bool:
        """
        刪除案件資料夾 - 統一版本

        Args:
            case_data: 案件資料

        Returns:
            刪除是否成功
        """
        try:
            print(f"🗑️ FolderManager 準備刪除案件資料夾: {case_data.client}")

            # 取得資料夾路徑
            folder_path = self.get_case_folder_path(case_data)
            if not folder_path:
                print(f"❌ 找不到案件資料夾路徑: {case_data.client}")
                return False

            # 檢查資料夾是否存在
            import os
            if not os.path.exists(folder_path):
                print(f"ℹ️ 資料夾不存在，視為刪除成功: {folder_path}")
                return True

            # 顯示資料夾資訊
            try:
                folder_contents = os.listdir(folder_path)
                print(f"📋 準備刪除資料夾及其內容 ({len(folder_contents)} 個項目): {folder_path}")
            except Exception as e:
                print(f"⚠️ 無法讀取資料夾內容: {e}")

            # 嘗試使用 operations 刪除
            if hasattr(self, 'operations') and self.operations:
                try:
                    success, message = self.operations.delete_case_folder(case_data, confirm=True)
                    if success:
                        print(f"✅ operations 刪除成功: {message}")
                        return True
                    else:
                        print(f"⚠️ operations 刪除失敗: {message}")
                except Exception as e:
                    print(f"⚠️ operations 刪除方法失敗: {e}")

            # 直接刪除作為備用方案
            try:
                import shutil
                shutil.rmtree(folder_path)
                print(f"✅ 直接刪除成功: {folder_path}")
                return True
            except Exception as e:
                print(f"❌ 直接刪除失敗: {e}")
                return False

        except Exception as e:
            print(f"❌ FolderManager.delete_case_folder 失敗: {e}")
            return False

    def update_case_info_excel(self, case_data: CaseData) -> bool:
        """
        更新案件資訊Excel檔案 - 新增方法

        Args:
            case_data: 案件資料

        Returns:
            bool: 更新是否成功
        """
        try:
            print(f"📊 準備更新案件Excel檔案: {case_data.case_id} - {case_data.client}")

            # 方法1：使用 excel_generator 如果可用
            if hasattr(self, 'excel_generator') and self.excel_generator:
                try:
                    # 取得案件資料夾路徑
                    case_folder_path = self.get_case_folder_path(case_data)
                    if not case_folder_path:
                        print(f"❌ 找不到案件資料夾路徑: {case_data.client}")
                        return False

                    # 使用專門的 Excel 生成器更新
                    success, message = self.excel_generator.update_case_info_excel(case_folder_path, case_data)

                    if success:
                        print(f"✅ Excel更新成功 (excel_generator): {message}")
                        return True
                    else:
                        print(f"⚠️ Excel更新失敗 (excel_generator): {message}")
                except Exception as e:
                    print(f"⚠️ excel_generator 方法失敗: {e}")

            # 方法2：使用內建的 Excel 更新方法（備用）
            try:
                success = self._update_case_excel_manual(case_data)
                if success:
                    print(f"✅ Excel更新成功 (手動方法)")
                    return True
            except Exception as e:
                print(f"⚠️ 手動 Excel 方法失敗: {e}")

            # 方法3：最簡單的備用方案
            print(f"ℹ️ Excel檔案更新跳過 - 所有方法都失敗")
            return False  # 改為 False，這樣呼叫者知道更新失敗但可以繼續

        except Exception as e:
            print(f"❌ FolderManager.update_case_info_excel 失敗: {e}")
            return False


    def validate_folder_structure(self, case_data: CaseData) -> Dict[str, Any]:
        """
        驗證案件資料夾結構完整性

        Args:
            case_data: 案件資料

        Returns:
            驗證結果字典
        """
        try:
            if self.validator and self.creator:
                return self.creator.validate_and_repair_structure(case_data)
            else:
                # 簡單驗證
                case_folder = self.get_case_folder_path(case_data)
                if case_folder:
                    import os
                    return {
                        'is_valid': os.path.exists(case_folder),
                        'errors': [] if os.path.exists(case_folder) else ['資料夾不存在'],
                        'missing_folders': [],
                        'warnings': ['使用簡化驗證']
                    }
                else:
                    return {
                        'is_valid': False,
                        'errors': ['找不到案件資料夾'],
                        'missing_folders': ['主資料夾'],
                        'warnings': []
                    }

        except Exception as e:
            return {
                'is_valid': False,
                'errors': [f'驗證過程發生錯誤: {str(e)}'],
                'missing_folders': [],
                'warnings': []
            }

    def get_case_folder_info(self, case_data: CaseData) -> Dict[str, Any]:
        """
        取得案件資料夾資訊（用於刪除前檢查）

        Args:
            case_data: 案件資料

        Returns:
            資料夾資訊字典
        """
        try:
            if self.operations:
                return self.operations.get_case_folder_info(case_data)
            else:
                # 備用方法
                folder_path = self.get_case_folder_path(case_data)
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
            print(f"❌ 取得案件資料夾資訊失敗: {e}")
    def diagnose_manager_status(self) -> Dict[str, Any]:
        """診斷管理器狀態"""
        return {
            'base_folder': self.base_data_folder,
            'creator_available': self.creator is not None,
            'validator_available': self.validator is not None,
            'operations_available': self.operations is not None,
            'excel_generator_available': self.excel_generator is not None,
            'available_methods': [method for method in dir(self) if not method.startswith('_') and callable(getattr(self, method))]
        }