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
        """初始化案件控制器 - 修正版本"""
        if data_file is None:
            self.data_file = AppConfig.DATA_CONFIG['case_data_file']
        else:
            self.data_file = data_file

        self.data_folder = os.path.dirname(self.data_file) if os.path.dirname(self.data_file) else '.'

        # 🔥 修正：確保 folder_manager 正確初始化
        print("🔄 初始化 folder_manager...")
        self.folder_manager = None

        try:
            # 方法1：嘗試使用新版本的 FolderManager
            from utils.folder_management.folder_manager import FolderManager as NewFolderManager
            self.folder_manager = NewFolderManager(self.data_folder)
            print("✅ 使用新版本 FolderManager")
        except ImportError as e:
            print(f"⚠️ 新版本 FolderManager 不可用: {e}")
            try:
                # 方法2：嘗試使用舊版本的 FolderManager
                from utils.folder_manager import FolderManager as OldFolderManager
                self.folder_manager = OldFolderManager(self.data_folder)
                print("✅ 使用舊版本 FolderManager")
            except ImportError as e2:
                print(f"⚠️ 舊版本 FolderManager 也不可用: {e2}")
                print("📝 將建立基本的 folder_manager")
                self.folder_manager = self._create_basic_folder_manager()

        # 確保 folder_manager 有必要的方法
        if self.folder_manager and not hasattr(self.folder_manager, 'get_case_folder_path'):
            print("⚠️ FolderManager 缺少必要方法，嘗試修復...")
            self._patch_folder_manager()

        print(f"📁 FolderManager 狀態: {'可用' if self.folder_manager else '不可用'}")

        # 初始化資料管理器
        from controllers.case_managers.case_data_manager import CaseDataManager
        self.data_manager = CaseDataManager(self.data_file, self.data_folder)

        # 確保資料夾存在
        self._ensure_data_folder()

        # 載入案件資料
        self.load_cases()

        # 初始化其他管理器（確保使用最新的案件資料）
        from controllers.case_managers.case_validator import CaseValidator
        from controllers.case_managers.case_import_export import CaseImportExport
        from controllers.case_managers.case_progress_manager import CaseProgressManager

        self.validator = CaseValidator(self.data_manager.cases)
        self.import_export = CaseImportExport(self.data_folder)
        self.progress_manager = CaseProgressManager(self.data_manager.cases, self.folder_manager)

    def _create_basic_folder_manager(self):
        """建立基本的 folder_manager"""
        class BasicFolderManager:
            def __init__(self, base_data_folder):
                self.base_data_folder = base_data_folder

            def get_case_folder_path(self, case_data):
                """基本的案件資料夾路徑計算"""
                try:
                    from config.settings import AppConfig
                    case_type_folder = AppConfig.CASE_TYPE_FOLDERS.get(
                        case_data.case_type,
                        case_data.case_type
                    )
                    folder_path = os.path.join(self.base_data_folder, case_type_folder, case_data.client)
                    return folder_path if os.path.exists(folder_path) else None
                except Exception as e:
                    print(f"計算案件資料夾路徑失敗: {e}")
                    return None

        return BasicFolderManager(self.data_folder)

    def _patch_folder_manager(self):
        """修補 folder_manager 缺少的方法"""
        try:
            if not hasattr(self.folder_manager, 'get_case_folder_path'):
                def get_case_folder_path(case_data):
                    """為舊版本 FolderManager 添加 get_case_folder_path 方法"""
                    try:
                        from config.settings import AppConfig
                        case_type_folder = AppConfig.CASE_TYPE_FOLDERS.get(case_data.case_type, case_data.case_type)
                        return os.path.join(self.data_folder, case_type_folder, case_data.client)
                    except Exception as e:
                        print(f"計算案件資料夾路徑失敗: {e}")
                        return None

                # 動態添加方法
                self.folder_manager.get_case_folder_path = get_case_folder_path
                print("✅ 已修補 folder_manager.get_case_folder_path 方法")

        except Exception as e:
            print(f"修補 folder_manager 失敗: {e}")

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

    def update_case_id(self, old_case_id: str, new_case_id: str) -> Dict[str, Any]:
        """
        🔥 新增：更改案件編號（包含資料夾重新命名和Excel更新）

        Args:
            old_case_id: 舊的案件編號
            new_case_id: 新的案件編號

        Returns:
            更新結果字典
        """
        result = {
            'success': False,
            'message': '',
            'old_case_id': old_case_id,
            'new_case_id': new_case_id,
            'changes': {
                'case_data_updated': False,
                'folder_renamed': False,
                'excel_updated': False,
                'old_folder_path': None,
                'new_folder_path': None,
                'old_excel_file': None,
                'new_excel_file': None
            }
        }

        try:
            # 1. 檢查舊案件是否存在
            case_data = self.get_case_by_id(old_case_id)
            if not case_data:
                result['message'] = f'找不到案件編號: {old_case_id}'
                return result

            # 2. 檢查新案件編號是否已存在
            if self.get_case_by_id(new_case_id):
                result['message'] = f'新案件編號已存在: {new_case_id}'
                return result

            # 3. 驗證新案件編號格式
            if not self._validate_case_id_format(new_case_id):
                result['message'] = f'新案件編號格式無效: {new_case_id}'
                return result

            print(f"🔄 開始更改案件編號: {old_case_id} -> {new_case_id}")

            # 4. 備份舊的案件資料
            old_case_data = case_data.copy() if hasattr(case_data, 'copy') else case_data

            # 5. 取得舊的資料夾路徑
            old_folder_path = self.folder_manager.get_case_folder_path(case_data)
            result['changes']['old_folder_path'] = old_folder_path

            # 6. 更新案件資料
            case_data.case_id = new_case_id
            case_data.updated_date = datetime.now()

            # 7. 保存案件資料
            save_success = self.save_cases()
            if not save_success:
                # 回復案件編號
                case_data.case_id = old_case_id
                result['message'] = '保存案件資料失敗'
                return result

            result['changes']['case_data_updated'] = True
            print(f"✅ 案件資料已更新")

            # 8. 處理資料夾重新命名
            if old_folder_path and os.path.exists(old_folder_path):
                folder_rename_result = self._rename_case_folder(old_case_data, case_data, old_folder_path)
                result['changes'].update(folder_rename_result)
            else:
                print(f"ℹ️ 舊資料夾不存在，跳過資料夾重新命名")

            # 9. 更新Excel檔案
            new_folder_path = result['changes'].get('new_folder_path') or old_folder_path
            if new_folder_path and os.path.exists(new_folder_path):
                excel_update_result = self._update_excel_after_case_id_change(
                    old_case_data, case_data, new_folder_path
                )
                result['changes'].update(excel_update_result)

            # 10. 生成最終結果
            if result['changes']['case_data_updated']:
                result['success'] = True
                changes_summary = []

                if result['changes']['folder_renamed']:
                    changes_summary.append("資料夾已重新命名")
                if result['changes']['excel_updated']:
                    changes_summary.append("Excel檔案已更新")

                if changes_summary:
                    result['message'] = f"案件編號更改成功，{', '.join(changes_summary)}"
                else:
                    result['message'] = "案件編號更改成功"
            else:
                result['message'] = "案件編號更改失敗"

            return result

        except Exception as e:
            # 發生錯誤時嘗試回復
            try:
                if 'case_data' in locals() and hasattr(case_data, 'case_id'):
                    case_data.case_id = old_case_id
                    self.save_cases()
            except:
                pass

            error_msg = f"更改案件編號時發生錯誤: {str(e)}"
            print(f"❌ {error_msg}")
            result['message'] = error_msg
            return result

    def _rename_case_folder(self, old_case_data: CaseData, new_case_data: CaseData, old_folder_path: str) -> Dict[str, Any]:
        """
        🔥 新增：重新命名案件資料夾

        Args:
            old_case_data: 舊的案件資料
            new_case_data: 新的案件資料
            old_folder_path: 舊的資料夾路徑

        Returns:
            重新命名結果
        """
        rename_result = {
            'folder_renamed': False,
            'old_folder_path': old_folder_path,
            'new_folder_path': None
        }

        try:
            # 使用validator生成新的資料夾名稱
            if hasattr(self.folder_manager, 'validator') and self.folder_manager.validator:
                new_folder_name = self.folder_manager.validator.get_safe_case_folder_name(new_case_data)
            else:
                # 降級處理
                safe_case_id = "".join(c for c in new_case_data.case_id if c.isalnum() or c in " -_")
                safe_client_name = "".join(c for c in new_case_data.client if c.isalnum() or c in " -_")
                new_folder_name = f"{safe_case_id}_{safe_client_name}".strip()[:50]

            # 計算新的資料夾路徑
            parent_folder = os.path.dirname(old_folder_path)
            new_folder_path = os.path.join(parent_folder, new_folder_name)
            rename_result['new_folder_path'] = new_folder_path

            # 檢查新路徑是否已存在
            if os.path.exists(new_folder_path):
                if new_folder_path == old_folder_path:
                    # 路徑相同，無需重新命名
                    rename_result['folder_renamed'] = True
                    print(f"ℹ️ 資料夾路徑無變化，無需重新命名")
                    return rename_result
                else:
                    # 路徑衝突，產生唯一名稱
                    counter = 1
                    while os.path.exists(new_folder_path):
                        unique_folder_name = f"{new_folder_name}_{counter}"
                        new_folder_path = os.path.join(parent_folder, unique_folder_name)
                        counter += 1
                        if counter > 1000:  # 防止無限循環
                            break

            # 執行重新命名
            os.rename(old_folder_path, new_folder_path)
            rename_result['folder_renamed'] = True

            old_folder_name = os.path.basename(old_folder_path)
            new_folder_name = os.path.basename(new_folder_path)
            print(f"📁 資料夾重新命名成功: {old_folder_name} -> {new_folder_name}")

            return rename_result

        except Exception as e:
            print(f"❌ 重新命名資料夾失敗: {e}")
            rename_result['new_folder_path'] = old_folder_path  # 使用舊路徑
            return rename_result

    def _update_excel_after_case_id_change(self, old_case_data: CaseData, new_case_data: CaseData,
                                        folder_path: str) -> Dict[str, Any]:
        """
        🔥 新增：案件編號更改後更新Excel檔案

        Args:
            old_case_data: 舊的案件資料
            new_case_data: 新的案件資料
            folder_path: 案件資料夾路徑

        Returns:
            Excel更新結果
        """
        excel_result = {
            'excel_updated': False,
            'old_excel_file': None,
            'new_excel_file': None
        }

        try:
            # 檢查是否有Excel生成器
            if not hasattr(self.folder_manager, 'excel_generator') or not self.folder_manager.excel_generator:
                print(f"⚠️ Excel生成器不可用，嘗試手動更新")
                return self._manual_update_excel_after_case_id_change(old_case_data, new_case_data, folder_path)

            # 使用Excel生成器更新
            success, message = self.folder_manager.excel_generator.update_case_info_excel_after_case_id_change(
                folder_path, old_case_data, new_case_data
            )

            excel_result['excel_updated'] = success
            if success:
                print(f"✅ Excel檔案更新成功: {message}")
            else:
                print(f"❌ Excel檔案更新失敗: {message}")

            return excel_result

        except Exception as e:
            print(f"❌ 更新Excel檔案時發生錯誤: {e}")
            return excel_result

    def _manual_update_excel_after_case_id_change(self, old_case_data: CaseData, new_case_data: CaseData,
                                                folder_path: str) -> Dict[str, Any]:
        """
        🔥 新增：手動更新Excel檔案（當Excel生成器不可用時）

        Args:
            old_case_data: 舊的案件資料
            new_case_data: 新的案件資料
            folder_path: 案件資料夾路徑

        Returns:
            Excel更新結果
        """
        excel_result = {
            'excel_updated': False,
            'old_excel_file': None,
            'new_excel_file': None
        }

        try:
            case_info_folder = os.path.join(folder_path, '案件資訊')
            if not os.path.exists(case_info_folder):
                print(f"ℹ️ 找不到案件資訊資料夾，跳過Excel更新")
                return excel_result

            # 尋找現有的Excel檔案
            excel_files = [f for f in os.listdir(case_info_folder)
                        if f.endswith('.xlsx') and '案件資訊' in f]

            if not excel_files:
                print(f"ℹ️ 找不到Excel檔案，跳過更新")
                return excel_result

            # 取第一個找到的Excel檔案
            old_excel_file = os.path.join(case_info_folder, excel_files[0])
            excel_result['old_excel_file'] = old_excel_file

            # 產生新的檔案名稱
            safe_case_id = "".join(c for c in new_case_data.case_id if c.isalnum() or c in " -_")
            safe_client_name = "".join(c for c in new_case_data.client if c.isalnum() or c in " -_")
            new_excel_filename = f"{safe_case_id}_{safe_client_name}_案件資訊.xlsx"
            new_excel_file = os.path.join(case_info_folder, new_excel_filename)
            excel_result['new_excel_file'] = new_excel_file

            # 重新命名Excel檔案
            if old_excel_file != new_excel_file:
                os.rename(old_excel_file, new_excel_file)
                print(f"📁 Excel檔案重新命名: {excel_files[0]} -> {new_excel_filename}")

            # 嘗試更新Excel內容（如果有pandas）
            try:
                import pandas as pd

                # 讀取現有Excel內容並更新案件編號
                with pd.ExcelFile(new_excel_file) as xls:
                    updated_sheets = {}

                    for sheet_name in xls.sheet_names:
                        df = pd.read_excel(xls, sheet_name=sheet_name)

                        # 更新基本資訊工作表中的案件編號
                        if sheet_name == '基本資訊' and '項目' in df.columns and '內容' in df.columns:
                            mask = df['項目'] == '案件編號'
                            if mask.any():
                                df.loc[mask, '內容'] = new_case_data.case_id

                        updated_sheets[sheet_name] = df

                # 寫回Excel檔案
                with pd.ExcelWriter(new_excel_file, engine='openpyxl') as writer:
                    for sheet_name, df in updated_sheets.items():
                        df.to_excel(writer, sheet_name=sheet_name, index=False)

                excel_result['excel_updated'] = True
                print(f"✅ Excel內容已更新")

            except ImportError:
                print(f"⚠️ 缺少pandas，僅重新命名Excel檔案")
                excel_result['excel_updated'] = True
            except Exception as e:
                print(f"⚠️ 更新Excel內容失敗，僅重新命名: {e}")
                excel_result['excel_updated'] = True

            return excel_result

        except Exception as e:
            print(f"❌ 手動更新Excel失敗: {e}")
            return excel_result

    def _validate_case_id_format(self, case_id: str) -> bool:
        """
        🔥 新增：驗證案件編號格式

        Args:
            case_id: 案件編號

        Returns:
            格式是否有效
        """
        try:
            if not case_id or not isinstance(case_id, str):
                return False

            # 移除前後空格
            case_id = case_id.strip()

            # 檢查長度
            if len(case_id) < 3 or len(case_id) > 20:
                return False

            # 檢查是否包含無效字元
            invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
            for char in invalid_chars:
                if char in case_id:
                    return False

            # 檢查是否只包含空格
            if not case_id.strip():
                return False

            return True

        except Exception:
            return False

    def update_case_id(self, old_case_id: str, new_case_id: str) -> Dict[str, Any]:
        """
        🔥 修正：更改案件編號（包含資料夾重新命名和Excel更新）

        Args:
            old_case_id: 舊的案件編號
            new_case_id: 新的案件編號

        Returns:
            更新結果字典
        """
        from datetime import datetime  # 確保匯入datetime

        result = {
            'success': False,
            'message': '',
            'old_case_id': old_case_id,
            'new_case_id': new_case_id,
            'changes': {
                'case_data_updated': False,
                'folder_renamed': False,
                'excel_updated': False,
                'old_folder_path': None,
                'new_folder_path': None,
                'old_excel_file': None,
                'new_excel_file': None
            }
        }

        try:
            # 1. 檢查舊案件是否存在
            case_data = self.get_case_by_id(old_case_id)
            if not case_data:
                result['message'] = f'找不到案件編號: {old_case_id}'
                return result

            # 2. 檢查新案件編號是否已存在
            if self.get_case_by_id(new_case_id):
                result['message'] = f'新案件編號已存在: {new_case_id}'
                return result

            # 3. 驗證新案件編號格式
            if not self._validate_case_id_format(new_case_id):
                result['message'] = f'新案件編號格式無效: {new_case_id}'
                return result

            print(f"🔄 開始更改案件編號: {old_case_id} -> {new_case_id}")

            # 4. 備份舊的案件資料
            old_case_data = case_data

            # 5. 取得舊的資料夾路徑
            old_folder_path = self.folder_manager.get_case_folder_path(case_data)
            result['changes']['old_folder_path'] = old_folder_path

            # 6. 更新案件資料
            case_data.case_id = new_case_id
            case_data.updated_date = datetime.now()

            # 7. 保存案件資料
            save_success = self.save_cases()
            if not save_success:
                # 回復案件編號
                case_data.case_id = old_case_id
                result['message'] = '保存案件資料失敗'
                return result

            result['changes']['case_data_updated'] = True
            print(f"✅ 案件資料已更新")

            # 8. 處理資料夾重新命名
            if old_folder_path and os.path.exists(old_folder_path):
                folder_rename_result = self._rename_case_folder(old_case_data, case_data, old_folder_path)
                result['changes'].update(folder_rename_result)
            else:
                print(f"ℹ️ 舊資料夾不存在，跳過資料夾重新命名")

            # 9. 更新Excel檔案
            new_folder_path = result['changes'].get('new_folder_path') or old_folder_path
            if new_folder_path and os.path.exists(new_folder_path):
                excel_update_result = self._update_excel_after_case_id_change(
                    old_case_data, case_data, new_folder_path
                )
                result['changes'].update(excel_update_result)

            # 10. 生成最終結果
            if result['changes']['case_data_updated']:
                result['success'] = True
                changes_summary = []

                if result['changes']['folder_renamed']:
                    changes_summary.append("資料夾已重新命名")
                if result['changes']['excel_updated']:
                    changes_summary.append("Excel檔案已更新")

                if changes_summary:
                    result['message'] = f"案件編號更改成功，{', '.join(changes_summary)}"
                else:
                    result['message'] = "案件編號更改成功"
            else:
                result['message'] = "案件編號更改失敗"

            return result

        except Exception as e:
            # 發生錯誤時嘗試回復
            try:
                if 'case_data' in locals() and hasattr(case_data, 'case_id'):
                    case_data.case_id = old_case_id
                    self.save_cases()
            except:
                pass

            error_msg = f"更改案件編號時發生錯誤: {str(e)}"
            print(f"❌ {error_msg}")
            result['message'] = error_msg
            return result

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

    def add_case_progress_stage(self, case_id: str, stage_name: str, stage_date: str = None, note: str = None, time: str = None) -> bool:
        """
        🔥 修改：新增案件進度階段（使用新的資料夾路徑邏輯）

        Args:
            case_id: 案件編號
            stage_name: 階段名稱
            stage_date: 階段日期
            note: 備註
            time: 時間

        Returns:
            新增是否成功
        """
        try:
            case = self.get_case_by_id(case_id)
            if not case:
                raise ValueError(f"找不到案件編號: {case_id}")

            # 新增進度階段到案件資料
            case.add_progress_stage(stage_name, stage_date, note, time)

            # 保存案件資料
            success = self.save_cases()
            if success:
                # 🔥 修改：使用新的資料夾路徑邏輯建立階段資料夾
                stage_folder_success = self.folder_manager.create_progress_folder(case, stage_name)

                # 更新Excel檔案
                excel_success = self.folder_manager.update_case_info_excel(case)
                if not excel_success:
                    print(f"⚠️ Excel檔案更新失敗")

                case_display_name = AppConfig.format_case_display_name(case)
                print(f"✅ 已新增案件 {case_display_name} 的階段 {stage_name}")

                if not stage_folder_success:
                    print(f"⚠️ 階段資料夾建立失敗，但資料已保存")

            return success

        except Exception as e:
            print(f"❌ 新增案件進度階段失敗: {e}")
            return False

    def update_case_progress_stage(self, case_id: str, stage_name: str, stage_date: str,
                                note: str = None, time: str = None) -> bool:
        """更新案件進度階段 - 修正版本（自動保存）"""
        try:
            print(f"🔄 開始更新進度階段: {case_id} - {stage_name}")

            result = self.progress_manager.update_progress_stage(case_id, stage_name, stage_date, note, time)
            if result:
                # 🔥 關鍵修正：更新進度階段後立即保存
                print(f"💾 保存進度階段更新到檔案...")
                save_result = self.save_cases()
                if save_result:
                    print(f"✅ 進度階段更新已保存到檔案: {stage_name}")
                    self._sync_managers()
                    return True
                else:
                    print(f"❌ 進度階段更新保存失敗: {stage_name}")
                    return False
            else:
                print(f"❌ 進度階段更新失敗: {stage_name}")
                return False
        except Exception as e:
            print(f"❌ CaseController.update_case_progress_stage 失敗: {e}")
            return False

    def remove_case_progress_stage(self, case_id: str, stage_name: str) -> bool:
        """移除案件進度階段 - 修正版本（自動保存）"""
        try:
            print(f"🔄 開始移除進度階段: {case_id} - {stage_name}")

            result = self.progress_manager.remove_progress_stage(case_id, stage_name)
            if result:
                # 🔥 關鍵修正：移除進度階段後立即保存
                print(f"💾 保存進度階段移除到檔案...")
                save_result = self.save_cases()
                if save_result:
                    print(f"✅ 進度階段移除已保存到檔案: {stage_name}")
                    self._sync_managers()
                    return True
                else:
                    print(f"❌ 進度階段移除保存失敗: {stage_name}")
                    return False
            else:
                print(f"❌ 進度階段移除失敗: {stage_name}")
                return False
        except Exception as e:
            print(f"❌ CaseController.remove_case_progress_stage 失敗: {e}")
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
        """取得案件資料夾路徑 - 🔥 修正：使用案件編號_當事人格式"""
        try:
            case = self.get_case_by_id(case_id)
            if not case:
                return None

            return self.folder_manager.get_case_folder_path(case)

        except Exception as e:
            print(f"取得案件資料夾路徑失敗: {e}")
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




# ==================== 使用範例 ====================
"""
使用範例:

# 1. 檢查單一案件資料夾格式
result = case_controller.check_case_folder_format("CASE001")
print(result)

# 2. 遷移單一案件資料夾格式
result = case_controller.migrate_case_folder_format("CASE001")
print(result)

# 3. 批次檢查所有案件
result = case_controller.batch_check_folder_formats()
print(result)

# 4. 批次檢查特定案件類型
result = case_controller.batch_check_folder_formats(case_type="民事")
print(result)

# 5. 批次遷移特定案件
result = case_controller.batch_migrate_folder_formats(case_ids=["CASE001", "CASE002"])
print(result)

# 6. 批次遷移特定案件類型
result = case_controller.batch_migrate_folder_formats(case_type="民事")
print(result)

# 7. 產生遷移報告
report = case_controller.get_folder_migration_report()
print(report)
"""

# ==================== 使用範例 ====================


def check_case_folder_format(self, case_id: str) -> Dict[str, Any]:
    """
    🔥 新增：檢查案件資料夾格式

    Args:
        case_id: 案件編號

    Returns:
        格式檢查結果
    """
    try:
        case_data = self.get_case_by_id(case_id)
        if not case_data:
            return {
                'success': False,
                'message': f'找不到案件: {case_id}',
                'exists': False
            }

        format_info = self.folder_manager.check_folder_format(case_data)

        result = {
            'success': True,
            'case_id': case_id,
            'client': case_data.client,
            'folder_exists': format_info['exists'],
            'current_format': format_info['format'],
            'needs_migration': format_info['needs_migration'],
            'current_path': format_info['path'],
            'new_format_name': format_info['new_format_name']
        }

        if format_info['exists']:
            if format_info['needs_migration']:
                result['message'] = f"資料夾使用舊格式，建議遷移到新格式"
            else:
                result['message'] = f"資料夾格式正確"
        else:
            result['message'] = f"資料夾不存在"

        return result

    except Exception as e:
        print(f"❌ 檢查案件資料夾格式失敗: {e}")
        return {
            'success': False,
            'message': f'檢查失敗: {str(e)}',
            'exists': False
        }

def migrate_case_folder_format(self, case_id: str) -> Dict[str, Any]:
    """
    🔥 新增：遷移案件資料夾格式

    Args:
        case_id: 案件編號

    Returns:
        遷移結果
    """
    try:
        case_data = self.get_case_by_id(case_id)
        if not case_data:
            return {
                'success': False,
                'message': f'找不到案件: {case_id}'
            }

        # 檢查是否需要遷移
        format_info = self.folder_manager.check_folder_format(case_data)
        if not format_info['exists']:
            return {
                'success': False,
                'message': '資料夾不存在，無法遷移'
            }

        if not format_info['needs_migration']:
            return {
                'success': True,
                'message': '資料夾已是新格式，無需遷移',
                'already_migrated': True
            }

        # 執行遷移
        success, message = self.folder_manager.migrate_folder_to_new_format(case_data)

        return {
            'success': success,
            'message': message,
            'case_id': case_id,
            'client': case_data.client,
            'old_format': format_info['current_format'],
            'new_format_name': format_info['new_format_name']
        }

    except Exception as e:
        print(f"❌ 遷移案件資料夾格式失敗: {e}")
        return {
            'success': False,
            'message': f'遷移失敗: {str(e)}'
        }

def batch_check_folder_formats(self, case_type: str = None) -> Dict[str, Any]:
    """
    🔥 新增：批次檢查資料夾格式

    Args:
        case_type: 案件類型（可選，不指定則檢查所有）

    Returns:
        批次檢查結果
    """
    try:
        # 取得要檢查的案件列表
        cases_to_check = []
        if case_type:
            cases_to_check = [case for case in self.cases if case.case_type == case_type]
        else:
            cases_to_check = self.cases.copy()

        result = {
            'success': True,
            'total_cases': len(cases_to_check),
            'checked': 0,
            'needs_migration': [],
            'already_new_format': [],
            'no_folder': [],
            'errors': []
        }

        for case_data in cases_to_check:
            try:
                format_info = self.folder_manager.check_folder_format(case_data)
                result['checked'] += 1

                case_summary = {
                    'case_id': case_data.case_id,
                    'client': case_data.client,
                    'case_type': case_data.case_type,
                    'current_path': format_info.get('path')
                }

                if not format_info['exists']:
                    result['no_folder'].append(case_summary)
                elif format_info['needs_migration']:
                    case_summary['current_format'] = format_info['format']
                    case_summary['new_format_name'] = format_info['new_format_name']
                    result['needs_migration'].append(case_summary)
                else:
                    result['already_new_format'].append(case_summary)

            except Exception as e:
                error_info = {
                    'case_id': case_data.case_id,
                    'client': case_data.client,
                    'error': str(e)
                }
                result['errors'].append(error_info)

        result['summary'] = {
            'needs_migration_count': len(result['needs_migration']),
            'already_new_format_count': len(result['already_new_format']),
            'no_folder_count': len(result['no_folder']),
            'error_count': len(result['errors'])
        }

        return result

    except Exception as e:
        print(f"❌ 批次檢查資料夾格式失敗: {e}")
        return {
            'success': False,
            'message': f'批次檢查失敗: {str(e)}'
        }

def batch_migrate_folder_formats(self, case_ids: List[str] = None, case_type: str = None) -> Dict[str, Any]:
    """
    🔥 新增：批次遷移資料夾格式

    Args:
        case_ids: 指定的案件編號列表（可選）
        case_type: 案件類型（可選）

    Returns:
        批次遷移結果
    """
    try:
        # 決定要遷移的案件
        cases_to_migrate = []

        if case_ids:
            # 根據案件編號列表
            for case_id in case_ids:
                case_data = self.get_case_by_id(case_id)
                if case_data:
                    cases_to_migrate.append(case_data)
        elif case_type:
            # 根據案件類型
            cases_to_migrate = [case for case in self.cases if case.case_type == case_type]
        else:
            # 所有案件
            cases_to_migrate = self.cases.copy()

        result = {
            'success': True,
            'total_cases': len(cases_to_migrate),
            'processed': 0,
            'migrated': [],
            'already_migrated': [],
            'no_folder': [],
            'errors': []
        }

        for case_data in cases_to_migrate:
            try:
                migrate_result = self.migrate_case_folder_format(case_data.case_id)
                result['processed'] += 1

                case_summary = {
                    'case_id': case_data.case_id,
                    'client': case_data.client,
                    'case_type': case_data.case_type
                }

                if migrate_result['success']:
                    if migrate_result.get('already_migrated'):
                        result['already_migrated'].append(case_summary)
                    else:
                        case_summary['new_format_name'] = migrate_result.get('new_format_name')
                        result['migrated'].append(case_summary)
                else:
                    if '不存在' in migrate_result['message']:
                        result['no_folder'].append(case_summary)
                    else:
                        case_summary['error'] = migrate_result['message']
                        result['errors'].append(case_summary)

            except Exception as e:
                error_info = {
                    'case_id': case_data.case_id,
                    'client': case_data.client,
                    'error': str(e)
                }
                result['errors'].append(error_info)

        result['summary'] = {
            'migrated_count': len(result['migrated']),
            'already_migrated_count': len(result['already_migrated']),
            'no_folder_count': len(result['no_folder']),
            'error_count': len(result['errors'])
        }

        return result

    except Exception as e:
        print(f"❌ 批次遷移資料夾格式失敗: {e}")
        return {
            'success': False,
            'message': f'批次遷移失敗: {str(e)}'
        }

def get_folder_migration_report(self) -> str:
    """
    🔥 新增：產生資料夾遷移報告

    Returns:
        格式化的報告字串
    """
    try:
        check_result = self.batch_check_folder_formats()

        if not check_result['success']:
            return f"❌ 無法產生報告: {check_result.get('message', '未知錯誤')}"

        report = "📋 案件資料夾格式檢查報告\n"
        report += "=" * 50 + "\n\n"

        # 總覽
        summary = check_result['summary']
        report += f"📊 總覽統計:\n"
        report += f"  • 總案件數: {check_result['total_cases']}\n"
        report += f"  • 已檢查: {check_result['checked']}\n"
        report += f"  • 需要遷移: {summary['needs_migration_count']}\n"
        report += f"  • 已是新格式: {summary['already_new_format_count']}\n"
        report += f"  • 無資料夾: {summary['no_folder_count']}\n"
        report += f"  • 錯誤: {summary['error_count']}\n\n"

        # 需要遷移的案件
        if check_result['needs_migration']:
            report += "🔄 需要遷移的案件:\n"
            for case in check_result['needs_migration']:
                report += f"  • {case['case_id']} - {case['client']} ({case['case_type']})\n"
                report += f"    當前格式: {case['current_format']}\n"
                report += f"    建議格式: {case['new_format_name']}\n"
            report += "\n"

        # 無資料夾的案件
        if check_result['no_folder']:
            report += "❌ 無資料夾的案件:\n"
            for case in check_result['no_folder']:
                report += f"  • {case['case_id']} - {case['client']} ({case['case_type']})\n"
            report += "\n"

        # 錯誤案件
        if check_result['errors']:
            report += "⚠️ 檢查錯誤的案件:\n"
            for error in check_result['errors']:
                report += f"  • {error['case_id']} - {error['client']}: {error['error']}\n"
            report += "\n"

        # 建議
        report += "💡 建議操作:\n"
        if summary['needs_migration_count'] > 0:
            report += f"  1. 執行批次遷移: 可遷移 {summary['needs_migration_count']} 個案件到新格式\n"
        if summary['no_folder_count'] > 0:
            report += f"  2. 建立資料夾: 有 {summary['no_folder_count']} 個案件需要建立資料夾\n"
        if summary['error_count'] > 0:
            report += f"  3. 檢查錯誤: 有 {summary['error_count']} 個案件需要檢查錯誤\n"

        if summary['needs_migration_count'] == 0 and summary['no_folder_count'] == 0 and summary['error_count'] == 0:
            report += "  ✅ 所有案件資料夾格式都正確，無需額外操作\n"

        return report

    except Exception as e:
        return f"❌ 產生報告失敗: {str(e)}"

# ==================== 案件資料夾管理相關方法 ====================