#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
資料夾管理器 - 修改版本
🔥 修改：支援「案件編號_當事人」格式的資料夾管理
整合所有資料夾管理功能，提供完整的向後相容介面
"""

import os
from typing import Optional, Dict, List, Any
from models.case_model import CaseData


class FolderManager:
    """
    資料夾管理器 - 修改版本
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
        僅使用新格式建立，禁止在建立時使用舊格式或模糊比對。
        """
        try:
            if not hasattr(self, 'creator') or self.creator is None:
                from .folder_creator import FolderCreator
                self.creator = FolderCreator(self.base_data_folder)
            success, msg = self.creator.create_case_folder_structure(case_data)
            if not success:
                print(f"❌ 新增案件資料夾失敗（嚴格模式）: {msg}")
                return False
            return True
        except Exception as e:
            print(f"❌ 建立案件資料夾例外（嚴格模式）: {e}")
            return False

        """
        🔥 修改：為案件建立完整的資料夾結構（使用新格式）

        Args:
            case_data: 案件資料

        Returns:
            建立是否成功
        """
        try:
            if not self.creator:
                print("❌ FolderCreator 不可用，嘗試使用備用方法")
                return self._create_basic_folder_structure(case_data)

            # 使用專門的建立器（已修改為支援新格式）
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
        """🔥 修改：備用的基本資料夾建立方法（使用新格式）"""
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

            # 🔥 修改：建立案件資料夾（使用新格式：案件編號_當事人）
            if self.validator:
                safe_folder_name = self.validator.get_safe_case_folder_name(case_data)
            else:
                # 如果validator不可用，使用簡單的清理方法
                safe_case_id = "".join(c for c in case_data.case_id if c.isalnum() or c in " -_")
                safe_client_name = "".join(c for c in case_data.client if c.isalnum() or c in " -_")
                safe_folder_name = f"{safe_case_id}_{safe_client_name}".strip()[:50]

            case_folder = os.path.join(case_type_path, safe_folder_name)
            os.makedirs(case_folder, exist_ok=True)
            print(f"✅ 建立案件資料夾: {safe_folder_name}")

            # 建立基本子資料夾
            sub_folders = [
                '案件資訊', '進度追蹤', '狀紙'
            ]

            for folder_name in sub_folders:
                folder_path = os.path.join(case_folder, folder_name)
                os.makedirs(folder_path, exist_ok=True)
                print(f"  ✅ 建立子資料夾: {folder_name}")

            print(f"✅ 備用方法成功建立基本資料夾結構")
            return True

        except Exception as e:
            print(f"❌ 備用方法也失敗: {e}")
            return False

    # ==================== 資料夾查詢介面 ====================

    def get_case_folder_path(self, case_data: CaseData) -> Optional[str]:
        """
        🔥 修改：取得案件的資料夾路徑（支援新舊格式查找）

        Args:
            case_data: 案件資料

        Returns:
            資料夾路徑或None
        """
        try:
            if self.operations:
                return self.operations.get_case_folder_path(case_data)
            else:
                # 降級處理
                return self._get_case_folder_path_fallback(case_data)

        except Exception as e:
            print(f"❌ 取得案件資料夾路徑失敗: {e}")
            return None

    def _get_case_folder_path_fallback(self, case_data: CaseData) -> Optional[str]:
        """🔥 修改：降級的資料夾路徑查找方法"""
        try:
            import os
            from config.settings import AppConfig

            case_type_folder_name = AppConfig.CASE_TYPE_FOLDERS.get(case_data.case_type)
            if not case_type_folder_name:
                return None

            case_type_path = os.path.join(self.base_data_folder, case_type_folder_name)
            if not os.path.exists(case_type_path):
                return None

            # 🔥 新增：嘗試新格式
            if self.validator:
                new_format, old_formats = self.validator.generate_case_folder_patterns(case_data)

                # 檢查新格式
                new_folder_path = os.path.join(case_type_path, new_format)
                if os.path.exists(new_folder_path):
                    return new_folder_path

                # 檢查舊格式
                for old_format in old_formats:
                    old_folder_path = os.path.join(case_type_path, old_format)
                    if os.path.exists(old_folder_path):
                        return old_folder_path
            else:
                # 簡單的檢查方式
                safe_client_name = "".join(c for c in case_data.client if c.isalnum() or c in " -_").strip()[:50]
                client_folder = os.path.join(case_type_path, safe_client_name)
                if os.path.exists(client_folder):
                    return client_folder

            return None

        except Exception as e:
            print(f"❌ 降級資料夾查找失敗: {e}")
            return None

    # ==================== 進度資料夾管理 ====================

    def create_progress_folder(self, case_data: CaseData, stage_name: str) -> bool:
        """
        🔥 修改：建立進度階段資料夾（使用新的資料夾路徑邏輯）

        Args:
            case_data: 案件資料
            stage_name: 階段名稱

        Returns:
            bool: 建立是否成功
        """
        try:
            print(f"📁 準備建立進度階段資料夾: {stage_name}")

            # 🔥 修改：使用新的資料夾路徑邏輯
            case_folder = self.get_case_folder_path(case_data)
            if not case_folder:
                print(f"❌ 找不到案件資料夾: {case_data.case_id} - {case_data.client}")
                return False

            # 方法1：使用 creator 如果可用
            if hasattr(self, 'creator') and self.creator:
                try:
                    success = self.creator.create_progress_folder(case_folder, stage_name)
                    if success:
                        print(f"✅ 使用creator成功建立進度階段資料夾: {stage_name}")
                        return True
                except Exception as e:
                    print(f"⚠️ creator方法失敗，嘗試備用方法: {e}")

            # 方法2：直接建立
            return self._create_progress_folder_direct(case_folder, stage_name)

        except Exception as e:
            print(f"❌ 建立進度階段資料夾失敗: {e}")
            return False

    def _create_progress_folder_direct(self, case_folder: str, stage_name: str) -> bool:
        """
        🔥 修改：直接建立進度資料夾的方法

        Args:
            case_folder: 案件資料夾路徑
            stage_name: 階段名稱

        Returns:
            建立是否成功
        """
        try:
            if not os.path.exists(case_folder):
                print(f"❌ 案件資料夾不存在: {case_folder}")
                return False

            progress_base_folder = os.path.join(case_folder, '進度追蹤')

            # 確保進度追蹤資料夾存在
            if not os.path.exists(progress_base_folder):
                os.makedirs(progress_base_folder, exist_ok=True)
                print(f"✅ 建立進度追蹤資料夾: {progress_base_folder}")

            # 清理階段名稱
            if self.validator:
                safe_stage_name = self.validator.sanitize_folder_name(stage_name)
            else:
                # 簡單的名稱清理
                safe_stage_name = "".join(c for c in stage_name if c.isalnum() or c in " -_").strip()
                if not safe_stage_name:
                    safe_stage_name = "未知階段"

            stage_folder_path = os.path.join(progress_base_folder, safe_stage_name)

            if not os.path.exists(stage_folder_path):
                os.makedirs(stage_folder_path, exist_ok=True)
                print(f"✅ 建立進度階段資料夾: {stage_name}")
            else:
                print(f"ℹ️ 進度階段資料夾已存在: {stage_name}")

            return True

        except Exception as e:
            print(f"❌ 直接建立進度資料夾失敗: {e}")
            return False
    # ==================== 資料夾遷移功能 ====================

    def migrate_folder_to_new_format(self, case_data: CaseData) -> tuple[bool, str]:
        """
        🔥 新增：將舊格式資料夾遷移到新格式

        Args:
            case_data: 案件資料

        Returns:
            (success, message)
        """
        try:
            if self.operations:
                return self.operations.migrate_folder_to_new_format(case_data)
            else:
                return False, "資料夾操作功能不可用"

        except Exception as e:
            error_msg = f"資料夾遷移失敗: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg

    def check_folder_format(self, case_data: CaseData) -> Dict[str, Any]:
        """
        🔥 新增：檢查案件資料夾格式

        Args:
            case_data: 案件資料

        Returns:
            格式檢查結果
        """
        try:
            result = {
                'exists': False,
                'format': 'unknown',
                'path': None,
                'needs_migration': False,
                'new_format_name': None
            }

            case_folder_path = self.get_case_folder_path(case_data)
            if not case_folder_path:
                return result

            result['exists'] = True
            result['path'] = case_folder_path

            if self.validator and self.operations:
                folder_name = os.path.basename(case_folder_path)
                result['format'] = self.operations._detect_folder_format(folder_name)

                # 取得新格式名稱
                new_format, _ = self.validator.generate_case_folder_patterns(case_data)
                result['new_format_name'] = new_format

                # 判斷是否需要遷移
                result['needs_migration'] = (result['format'] == 'old' and folder_name != new_format)

            return result

        except Exception as e:
            print(f"❌ 檢查資料夾格式失敗: {e}")
            return {'exists': False, 'format': 'unknown', 'path': None, 'needs_migration': False}

    # ==================== 其他管理功能 ====================

    def get_case_folder_info(self, case_data: CaseData) -> dict:
        """取得案件資料夾資訊"""
        try:
            if self.operations:
                case_folder = self.get_case_folder_path(case_data)
                if case_folder:
                    return self.operations._get_folder_info(case_folder)

            return {
                'exists': False,
                'path': None,
                'file_count': 0,
                'size_mb': 0,
                'last_modified': None
            }

        except Exception as e:
            print(f"❌ 取得案件資料夾資訊失敗: {e}")
            return {'exists': False, 'path': None, 'file_count': 0, 'size_mb': 0}

    def delete_case_folder(self, case_data: CaseData, confirm: bool = False) -> bool:
        """刪除案件資料夾"""
        try:
            if self.operations:
                success, message = self.operations.delete_case_folder(case_data, confirm)
                if not success:
                    print(f"❌ {message}")
                return success
            else:
                print("❌ 資料夾操作功能不可用")
                return False

        except Exception as e:
            print(f"❌ 刪除案件資料夾失敗: {e}")
            return False

    # ==================== 向後相容的方法 ====================

    def get_stage_folder_path(self, case_data: CaseData, stage_name: str) -> Optional[str]:
        """取得特定階段的資料夾路徑"""
        try:
            if self.operations:
                return self.operations.get_stage_folder_path(case_data, stage_name)
            else:
                # 降級處理
                case_folder = self.get_case_folder_path(case_data)
                if not case_folder:
                    return None

                import os
                stage_folder_path = os.path.join(case_folder, '進度追蹤', stage_name)
                return stage_folder_path if os.path.exists(stage_folder_path) else None

        except Exception as e:
            print(f"❌ 取得階段資料夾路徑失敗: {e}")
            return None

    def get_progress_folder_path(self, case_data: CaseData, stage_name: str) -> Optional[str]:
        """
        🔥 修改：取得進度階段資料夾路徑（使用新的資料夾路徑邏輯）

        Args:
            case_data: 案件資料
            stage_name: 階段名稱

        Returns:
            階段資料夾路徑或None
        """
        try:
            # 🔥 修改：使用新的資料夾路徑邏輯
            case_folder = self.get_case_folder_path(case_data)
            if not case_folder:
                return None

            # 清理階段名稱
            if self.validator:
                safe_stage_name = self.validator.sanitize_folder_name(stage_name)
            else:
                safe_stage_name = "".join(c for c in stage_name if c.isalnum() or c in " -_").strip()

            stage_folder_path = os.path.join(case_folder, '進度追蹤', safe_stage_name)
            return stage_folder_path if os.path.exists(stage_folder_path) else None

        except Exception as e:
            print(f"❌ 取得進度階段資料夾路徑失敗: {e}")
            return None

    def delete_progress_folder(self, case_data: CaseData, stage_name: str) -> bool:
        """
        🔥 修改：刪除進度階段資料夾（使用新的資料夾路徑邏輯）

        Args:
            case_data: 案件資料
            stage_name: 階段名稱

        Returns:
            刪除是否成功
        """
        try:
            stage_folder_path = self.get_progress_folder_path(case_data, stage_name)
            if not stage_folder_path:
                print(f"❌ 找不到進度階段資料夾: {stage_name}")
                return False

            if not os.path.exists(stage_folder_path):
                print(f"ℹ️ 進度階段資料夾不存在: {stage_name}")
                return True

            # 檢查資料夾是否為空
            if os.listdir(stage_folder_path):
                print(f"⚠️ 階段資料夾 {stage_name} 內含檔案，將一併刪除")

            # 刪除整個資料夾及其內容
            shutil.rmtree(stage_folder_path)
            print(f"✅ 已刪除階段資料夾: {stage_name}")
            return True

        except Exception as e:
            print(f"❌ 刪除進度階段資料夾失敗: {e}")
            return False

    def update_case_info_excel(self, case_data: CaseData) -> bool:
        """
        🔥 修改：更新案件資訊Excel檔案（使用新的資料夾路徑邏輯）

        Args:
            case_data: 案件資料

        Returns:
            更新是否成功
        """
        try:
            # 🔥 修改：使用新的資料夾路徑邏輯
            case_folder = self.get_case_folder_path(case_data)
            if not case_folder:
                print(f"❌ 找不到案件資料夾: {case_data.case_id} - {case_data.client}")
                return False

            # 方法1：使用Excel生成器
            if hasattr(self, 'excel_generator') and self.excel_generator:
                try:
                    success, message = self.excel_generator.update_case_info_excel(case_folder, case_data)
                    if success:
                        print(f"✅ 使用excel_generator更新Excel: {message}")
                        return True
                    else:
                        print(f"⚠️ excel_generator更新失敗: {message}")
                except Exception as e:
                    print(f"⚠️ excel_generator失敗，嘗試備用方法: {e}")

            # 方法2：降級處理
            return self._update_case_info_excel_fallback(case_folder, case_data)

        except Exception as e:
            print(f"❌ 更新案件資訊Excel檔案失敗: {e}")
            return False

    def _update_case_info_excel_fallback(self, case_folder: str, case_data: CaseData) -> bool:
        """
        🔥 新增：Excel更新的降級處理方法

        Args:
            case_folder: 案件資料夾路徑
            case_data: 案件資料

        Returns:
            更新是否成功
        """
        try:
            case_info_folder = os.path.join(case_folder, '案件資訊')
            if not os.path.exists(case_info_folder):
                print(f"❌ 找不到案件資訊資料夾: {case_info_folder}")
                return False

            # 檢查是否有pandas
            try:
                import pandas as pd
            except ImportError:
                print(f"⚠️ 缺少pandas套件，無法更新Excel")
                return False

            # 尋找Excel檔案
            excel_files = [f for f in os.listdir(case_info_folder)
                        if f.endswith('.xlsx') and '案件資訊' in f]

            if excel_files:
                # 更新現有檔案
                excel_path = os.path.join(case_info_folder, excel_files[0])
                return self._recreate_case_info_excel(excel_path, case_data)
            else:
                # 建立新檔案
                safe_case_id = "".join(c for c in case_data.case_id if c.isalnum() or c in " -_")
                safe_client_name = "".join(c for c in case_data.client if c.isalnum() or c in " -_")
                excel_filename = f"{safe_case_id}_{safe_client_name}_案件資訊.xlsx"
                excel_path = os.path.join(case_info_folder, excel_filename)
                return self._recreate_case_info_excel(excel_path, case_data)

        except Exception as e:
            print(f"❌ Excel降級更新失敗: {e}")
            return False

    def _recreate_case_info_excel(self, excel_path: str, case_data: CaseData) -> bool:
        """
        🔥 修改：重新建立案件資訊Excel檔案（包含最新的案件編號）

        Args:
            excel_path: Excel檔案路徑
            case_data: 案件資料

        Returns:
            建立是否成功
        """
        try:
            import pandas as pd

            # 準備基本資訊資料
            basic_info = [
                ['案件編號', case_data.case_id],  # 🔥 確保使用最新的案件編號
                ['案件類型', case_data.case_type],
                ['當事人', case_data.client],
                ['委任律師', getattr(case_data, 'lawyer', '') or ''],
                ['法務', getattr(case_data, 'legal_affairs', '') or ''],
                ['進度追蹤', case_data.progress],
                ['進度日期', case_data.progress_date or ''],
                ['建立日期', case_data.created_date.strftime('%Y-%m-%d %H:%M:%S') if case_data.created_date else ''],
                ['更新日期', case_data.updated_date.strftime('%Y-%m-%d %H:%M:%S') if case_data.updated_date else '']
            ]

            # 準備詳細資訊資料
            detail_info = [
                ['案由', getattr(case_data, 'case_reason', '') or ''],
                ['案號', getattr(case_data, 'case_number', '') or ''],
                ['對造', getattr(case_data, 'opposing_party', '') or ''],
                ['負責法院', getattr(case_data, 'court', '') or ''],
                ['負責股別', getattr(case_data, 'division', '') or '']
            ]

            with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
                # 基本資訊工作表
                df_basic = pd.DataFrame(basic_info, columns=['項目', '內容'])
                df_basic.to_excel(writer, sheet_name='基本資訊', index=False)

                # 詳細資訊工作表
                df_detail = pd.DataFrame(detail_info, columns=['項目', '內容'])
                df_detail.to_excel(writer, sheet_name='詳細資訊', index=False)

                # 進度階段工作表（如果有進度階段）
                if case_data.progress_stages:
                    progress_info = []
                    for stage, date in sorted(case_data.progress_stages.items(), key=lambda x: x[1] or ''):
                        # 取得備註
                        note = ""
                        if hasattr(case_data, 'progress_notes') and case_data.progress_notes:
                            note = case_data.progress_notes.get(stage, "")

                        # 取得時間
                        time = ""
                        if hasattr(case_data, 'progress_times') and case_data.progress_times:
                            time = case_data.progress_times.get(stage, "")

                        progress_info.append([stage, date or '', time, note])

                    if progress_info:
                        df_progress = pd.DataFrame(progress_info, columns=['進度階段', '日期', '時間', '備註'])
                        df_progress.to_excel(writer, sheet_name='進度階段', index=False)

                # 調整欄位寬度和格式
                for sheet_name in writer.sheets:
                    worksheet = writer.sheets[sheet_name]
                    worksheet.column_dimensions['A'].width = 15
                    worksheet.column_dimensions['B'].width = 30

                    # 如果是進度階段工作表，調整額外欄位
                    if sheet_name == '進度階段':
                        worksheet.column_dimensions['C'].width = 15  # 時間欄位
                        worksheet.column_dimensions['D'].width = 40  # 備註欄位

                    # 設定標題列格式
                    for cell in worksheet[1]:
                        cell.font = cell.font.copy(bold=True)

            print(f"✅ 重新建立案件資訊Excel: {os.path.basename(excel_path)}")
            return True

        except Exception as e:
            print(f"❌ 重新建立案件資訊Excel失敗: {e}")
            return False
