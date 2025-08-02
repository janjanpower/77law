#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
案件控制器 - 修正版本
使用新的 Services 層架構，同時保持向後相容性
新增 update_case_id 方法以支援案件編號更新功能
"""

from typing import List, Optional, Tuple, Dict, Any
from models.case_model import CaseData
from services.services_controller import ServicesController
from config.settings import AppConfig
import os
import shutil
from datetime import datetime


class CaseController:
    """案件控制器 - 修正版本（委託給 Services 層 + 向後相容）"""

    def __init__(self, data_folder: str = None):
        """
        初始化案件控制器

        Args:
            data_folder: 資料資料夾路徑
        """
        self.data_folder = data_folder or AppConfig.DATA_CONFIG.get('data_folder', './data')

        # 確保資料夾存在
        os.makedirs(self.data_folder, exist_ok=True)

        # 初始化服務控制器（所有業務邏輯都委託給它）
        self.services = ServicesController(self.data_folder)

        # 向後相容：維護cases屬性用於generate_case_id
        self.cases = []
        self.data_file = os.path.join(self.data_folder, "cases.json")

        # 載入現有案件資料
        self.load_cases()

        print("✅ CaseController 初始化完成 (使用 Services 架構 + 向後相容)")

    # ==================== 資料載入與儲存 ====================

    def load_cases(self) -> bool:
        """載入案件資料（向後相容）"""
        try:
            # 委託給services層載入資料
            self.cases = self.services.case_service.repository.get_all_cases()
            print(f"✅ 成功載入 {len(self.cases)} 筆案件資料")
            return True
        except Exception as e:
            print(f"❌ 載入案件資料失敗: {e}")
            self.cases = []
            return False

    def save_cases(self) -> bool:
        """儲存案件資料（向後相容）"""
        try:
            # 委託給services層儲存資料
            return self.services.case_service.repository._save_data()
        except Exception as e:
            print(f"❌ 儲存案件資料失敗: {e}")
            return False

    # ==================== 案件CRUD操作 ====================

    def add_case(self, case_data: CaseData, create_folder: bool = True,
                 apply_template: str = None) -> bool:
        """
        新增案件

        Args:
            case_data: 案件資料
            create_folder: 是否建立資料夾
            apply_template: 套用的進度範本名稱

        Returns:
            bool: 是否新增成功
        """
        try:
            print(f"🎯 控制器: 開始新增案件 {case_data.client}，建立資料夾: {create_folder}")

            # 修正：使用正確的方法名稱和參數
            result = self.services.create_case(case_data, create_folder, apply_template)

            if result[0]:
                print(f"✅ 控制器: 成功新增案件 {case_data.client}")

                # 如果 services 層沒有成功建立資料夾，嘗試直接調用 folder_service
                if create_folder:
                    try:
                        case_folder_path = self.get_case_folder_path(case_data.case_id)
                        if not case_folder_path or not os.path.exists(case_folder_path):
                            print("⚠️ 控制器: Services 層未建立資料夾，嘗試直接建立...")

                            # 直接調用 folder_service 建立資料夾
                            folder_result = self.services.folder_service.create_case_folder_structure(case_data)

                            if folder_result[0]:
                                print(f"✅ 控制器: 資料夾建立成功 - {folder_result[1]}")
                            else:
                                print(f"⚠️ 控制器: 資料夾建立失敗 - {folder_result[1]}")
                        else:
                            print(f"✅ 控制器: 資料夾已存在 - {case_folder_path}")
                    except Exception as folder_error:
                        print(f"⚠️ 控制器: 資料夾建立異常 - {folder_error}")

                # 重新載入cases以保持同步
                self.load_cases()
            else:
                print(f"❌ 控制器: 新增案件失敗 - {result[1]}")

            return result[0]
        except Exception as e:
            print(f"❌ CaseController.add_case 失敗: {e}")
            import traceback
            traceback.print_exc()
            return False

    def update_case(self, case_data: CaseData, update_folder: bool = False) -> bool:
        """
        更新案件

        Args:
            case_data: 更新後的案件資料
            update_folder: 是否同步更新資料夾

        Returns:
            bool: 是否更新成功
        """
        try:
            result = self.services.update_case(case_data, update_folder, sync_progress=True)
            if result[0]:
                print(f"✅ 控制器: 成功更新案件 {case_data.case_id}")
                # 重新載入cases以保持同步
                self.load_cases()
            else:
                print(f"❌ 控制器: 更新案件失敗 - {result[1]}")
            return result[0]
        except Exception as e:
            print(f"❌ CaseController.update_case 失敗: {e}")
            return False

    def update_case_id(self, old_case_id: str, case_type: str, new_case_id: str) -> Tuple[bool, str]:
        """
        更新案件編號（同時更新檔案名稱和內容中的案件編號）
        使用 CaseIdUpdateService 進行全面更新

        Args:
            old_case_id: 原案件編號
            case_type: 案件類型
            new_case_id: 新案件編號

        Returns:
            Tuple[bool, str]: (是否成功, 訊息)
        """
        try:
            print(f"🔄 開始更新案件編號: {old_case_id} → {new_case_id}")

            # 1. 導入並初始化 CaseIdUpdateService
            from .case_id_update_service import CaseIdUpdateService

            update_service = CaseIdUpdateService(
                data_folder=self.data_folder,
                config={
                    'case_type_folders': AppConfig.CASE_TYPE_FOLDERS
                }
            )

            # 2. 驗證新案件編號格式
            is_valid, validation_msg = update_service.validate_case_id_format(new_case_id)
            if not is_valid:
                return False, validation_msg

            new_case_id = new_case_id.strip().upper()

            # 3. 檢查新案件編號是否已存在（排除自己）
            existing_case = self.services.case_service.repository.get_case_by_id(new_case_id)
            if existing_case and existing_case.case_id != old_case_id:
                return False, f"案件編號 {new_case_id} 已存在"

            # 4. 取得原案件資料
            original_case = self.services.case_service.repository.get_case_by_id(old_case_id)
            if not original_case:
                return False, f"找不到原案件: {old_case_id}"

            # 5. 備份原案件資料（可選）
            backup_success, backup_path = update_service.backup_before_update(old_case_id, case_type)
            if backup_success:
                print(f"✅ 已建立備份: {backup_path}")

            # 6. 更新案件資料中的編號
            updated_case = CaseData(
                case_id=new_case_id,
                client=original_case.client,
                case_type=original_case.case_type,
                status=getattr(original_case, 'status', ''),
                notes=getattr(original_case, 'notes', ''),
                creation_date=getattr(original_case, 'creation_date', datetime.now()),
                progress_stages=getattr(original_case, 'progress_stages', {}),
                important_dates=getattr(original_case, 'important_dates', {}),
                template_name=getattr(original_case, 'template_name', None)
            )

            # 7. 在資料庫中更新案件編號（先刪除舊的，再新增新的）
            delete_result = self.services.case_service.repository.delete_case(old_case_id)
            if not delete_result[0]:
                return False, f"刪除原案件資料失敗: {delete_result[1]}"

            create_result = self.services.case_service.repository.create_case(updated_case)
            if not create_result[0]:
                # 如果新增失敗，嘗試恢復原資料
                self.services.case_service.repository.create_case(original_case)
                return False, f"新增更新案件資料失敗: {create_result[1]}"

            # 8. 使用 CaseIdUpdateService 進行全面更新
            update_success, update_message, update_details = update_service.update_case_id_comprehensive(
                old_case_id=old_case_id,
                new_case_id=new_case_id,
                case_type=case_type,
                case_data=updated_case
            )

            # 9. 更新進度資料中的案件編號（使用 services 層）
            self._update_progress_case_id(old_case_id, new_case_id)

            # 10. 重新載入資料以同步
            self.load_cases()

            # 11. 產生詳細的結果訊息
            if update_success:
                detailed_message = f"案件編號更新成功: {old_case_id} → {new_case_id}\n"
                if update_details['folder_renamed']:
                    detailed_message += "✅ 資料夾已重新命名\n"
                if update_details['files_updated'] > 0:
                    detailed_message += f"✅ 已更新 {update_details['files_updated']} 個檔案的內容\n"
                if update_details['files_failed'] > 0:
                    detailed_message += f"⚠️ {update_details['files_failed']} 個檔案更新失敗\n"
                if backup_success:
                    detailed_message += f"📁 備份位置: {backup_path}"

                return True, detailed_message.strip()
            else:
                return False, update_message

        except ImportError:
            # 如果無法導入 CaseIdUpdateService，使用舊版邏輯
            print("⚠️ 無法導入 CaseIdUpdateService，使用基本更新邏輯")
            return self._update_case_id_basic(old_case_id, case_type, new_case_id)
        except Exception as e:
            error_msg = f"更新案件編號失敗: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg

    def _update_case_id_basic(self, old_case_id: str, case_type: str, new_case_id: str) -> Tuple[bool, str]:
        """
        基本的案件編號更新邏輯（備用方案）

        Args:
            old_case_id: 原案件編號
            case_type: 案件類型
            new_case_id: 新案件編號

        Returns:
            Tuple[bool, str]: (是否成功, 訊息)
        """
        try:
            # 基本驗證
            if not new_case_id or not new_case_id.strip():
                return False, "案件編號不能為空"

            new_case_id = new_case_id.strip().upper()

            # 檢查重複
            existing_case = self.services.case_service.repository.get_case_by_id(new_case_id)
            if existing_case and existing_case.case_id != old_case_id:
                return False, f"案件編號 {new_case_id} 已存在"

            # 取得原案件
            original_case = self.services.case_service.repository.get_case_by_id(old_case_id)
            if not original_case:
                return False, f"找不到原案件: {old_case_id}"

            # 建立新案件資料
            updated_case = CaseData(
                case_id=new_case_id,
                client=original_case.client,
                case_type=original_case.case_type,
                status=getattr(original_case, 'status', ''),
                notes=getattr(original_case, 'notes', ''),
                creation_date=getattr(original_case, 'creation_date', datetime.now()),
                progress_stages=getattr(original_case, 'progress_stages', {}),
                important_dates=getattr(original_case, 'important_dates', {}),
                template_name=getattr(original_case, 'template_name', None)
            )

            # 更新資料庫
            delete_result = self.services.case_service.repository.delete_case(old_case_id)
            if not delete_result[0]:
                return False, f"刪除原案件資料失敗: {delete_result[1]}"

            create_result = self.services.case_service.repository.create_case(updated_case)
            if not create_result[0]:
                self.services.case_service.repository.create_case(original_case)
                return False, f"新增更新案件資料失敗: {create_result[1]}"

            # 基本的資料夾更新
            folder_success = self._update_case_folder_name(old_case_id, new_case_id, case_type)
            content_success = self._update_folder_content_case_id(new_case_id, old_case_id, case_type)

            # 更新進度
            self._update_progress_case_id(old_case_id, new_case_id)

            # 重新載入
            self.load_cases()

            message = f"案件編號更新成功: {old_case_id} → {new_case_id}"
            if not folder_success:
                message += "（資料夾更新失敗）"
            if not content_success:
                message += "（部分內容更新失敗）"

            return True, message

        except Exception as e:
            return False, f"基本更新失敗: {str(e)}"

    def _update_case_folder_name(self, old_case_id: str, new_case_id: str, case_type: str) -> bool:
        """
        更新案件資料夾名稱

        Args:
            old_case_id: 原案件編號
            new_case_id: 新案件編號
            case_type: 案件類型

        Returns:
            bool: 是否成功
        """
        try:
            # 取得資料夾路徑
            case_type_folder = AppConfig.CASE_TYPE_FOLDERS.get(case_type, case_type)
            old_folder_path = os.path.join(self.data_folder, case_type_folder, old_case_id)
            new_folder_path = os.path.join(self.data_folder, case_type_folder, new_case_id)

            # 檢查原資料夾是否存在
            if not os.path.exists(old_folder_path):
                print(f"⚠️ 原案件資料夾不存在: {old_folder_path}")
                return True  # 資料夾不存在也算成功

            # 檢查目標資料夾是否已存在
            if os.path.exists(new_folder_path):
                print(f"⚠️ 目標資料夾已存在: {new_folder_path}")
                return False

            # 重新命名資料夾
            shutil.move(old_folder_path, new_folder_path)
            print(f"✅ 資料夾重新命名成功: {old_folder_path} → {new_folder_path}")
            return True

        except Exception as e:
            print(f"❌ 更新資料夾名稱失敗: {e}")
            return False

    def _update_folder_content_case_id(self, new_case_id: str, old_case_id: str, case_type: str) -> bool:
        """
        更新資料夾內容中的案件編號

        Args:
            new_case_id: 新案件編號
            old_case_id: 原案件編號
            case_type: 案件類型

        Returns:
            bool: 是否成功
        """
        try:
            # 取得新的資料夾路徑
            case_type_folder = AppConfig.CASE_TYPE_FOLDERS.get(case_type, case_type)
            folder_path = os.path.join(self.data_folder, case_type_folder, new_case_id)

            if not os.path.exists(folder_path):
                print(f"⚠️ 案件資料夾不存在: {folder_path}")
                return True

            updated_files = []
            failed_files = []

            # 遍歷資料夾中的所有檔案
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    file_path = os.path.join(root, file)

                    # 只處理文字檔案
                    if self._is_text_file(file_path):
                        try:
                            if self._update_file_case_id(file_path, old_case_id, new_case_id):
                                updated_files.append(file_path)
                        except Exception as e:
                            print(f"❌ 更新檔案失敗 {file_path}: {e}")
                            failed_files.append(file_path)

            print(f"✅ 內容更新完成 - 成功: {len(updated_files)}, 失敗: {len(failed_files)}")
            return len(failed_files) == 0

        except Exception as e:
            print(f"❌ 更新資料夾內容失敗: {e}")
            return False

    def _is_text_file(self, file_path: str) -> bool:
        """
        判斷是否為文字檔案

        Args:
            file_path: 檔案路徑

        Returns:
            bool: 是否為文字檔案
        """
        text_extensions = {'.txt', '.doc', '.docx', '.rtf', '.md', '.html', '.xml', '.json', '.csv'}
        _, ext = os.path.splitext(file_path.lower())
        return ext in text_extensions

    def _update_file_case_id(self, file_path: str, old_case_id: str, new_case_id: str) -> bool:
        """
        更新單個檔案中的案件編號

        Args:
            file_path: 檔案路徑
            old_case_id: 原案件編號
            new_case_id: 新案件編號

        Returns:
            bool: 是否有更新
        """
        try:
            # 嘗試不同的編碼讀取檔案
            encodings = ['utf-8', 'big5', 'gbk', 'cp950', 'latin1']
            content = None
            used_encoding = None

            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        content = f.read()
                    used_encoding = encoding
                    break
                except UnicodeDecodeError:
                    continue

            if content is None:
                print(f"⚠️ 無法讀取檔案: {file_path}")
                return False

            # 檢查是否包含舊案件編號
            if old_case_id not in content:
                return False

            # 替換案件編號
            updated_content = content.replace(old_case_id, new_case_id)

            # 寫回檔案
            with open(file_path, 'w', encoding=used_encoding) as f:
                f.write(updated_content)

            print(f"✅ 檔案內容已更新: {file_path}")
            return True

        except Exception as e:
            print(f"❌ 更新檔案內容失敗 {file_path}: {e}")
            return False

    def _update_progress_case_id(self, old_case_id: str, new_case_id: str):
        """
        更新進度資料中的案件編號

        Args:
            old_case_id: 原案件編號
            new_case_id: 新案件編號
        """
        try:
            # 檢查進度服務是否可用
            if hasattr(self.services, 'progress_service') and self.services.progress_service:
                progress_data = self.services.progress_service.progress_data

                if old_case_id in progress_data:
                    # 移動進度資料到新的案件編號
                    progress_data[new_case_id] = progress_data.pop(old_case_id)

                    # 保存進度資料
                    self.services.progress_service._save_progress_data()
                    print(f"✅ 進度資料已更新: {old_case_id} → {new_case_id}")

        except Exception as e:
            print(f"⚠️ 更新進度資料失敗: {e}")

    def delete_case(self, case_id: str, delete_folder: bool = True, force: bool = False) -> bool:
        """
        刪除案件

        Args:
            case_id: 案件ID
            delete_folder: 是否刪除資料夾
            force: 是否強制刪除

        Returns:
            bool: 是否刪除成功
        """
        try:
            result = self.services.delete_case(case_id, delete_folder, delete_progress=True, force=force)
            if result[0]:
                print(f"✅ 控制器: 成功刪除案件 {case_id}")
                # 重新載入cases以保持同步
                self.load_cases()
            else:
                print(f"❌ 控制器: 刪除案件失敗 - {result[1]}")
            return result[0]
        except Exception as e:
            print(f"❌ CaseController.delete_case 失敗: {e}")
            return False

    # ==================== 案件編號生成（向後相容）====================

    def generate_case_id(self, case_type: str = None) -> str:
        """
        產生新的案件編號 - 民國年分(三碼)+XXX(三碼)格式

        Args:
            case_type: 案件類型（可選，用於未來擴展）

        Returns:
            str: 新的案件編號
        """
        try:
            # 計算民國年分
            current_year = datetime.now().year
            roc_year = current_year - 1911

            # 取得現有案件編號，找出最大序號
            existing_ids = [case.case_id for case in self.cases if case.case_id]

            # 過濾出同年度的案件編號
            year_prefix = f"{roc_year:03d}"
            same_year_ids = [
                case_id for case_id in existing_ids
                if len(case_id) >= 6 and case_id[:3] == year_prefix
            ]

            # 找出最大序號
            max_seq = 0
            for case_id in same_year_ids:
                try:
                    seq_part = case_id[3:6]
                    if seq_part.isdigit():
                        max_seq = max(max_seq, int(seq_part))
                except (ValueError, IndexError):
                    continue

            # 產生新的序號
            new_seq = max_seq + 1
            new_case_id = f"{year_prefix}{new_seq:03d}"

            print(f"✅ 產生新案件編號: {new_case_id}")
            return new_case_id

        except Exception as e:
            print(f"❌ 產生案件編號失敗: {e}")
            # 回退策略：使用時間戳
            timestamp = datetime.now().strftime("%y%m%d")
            return f"ERR{timestamp}"

    # ==================== 查詢方法（向後相容）====================

    def get_case_by_id(self, case_id: str) -> Optional[CaseData]:
        """根據ID取得案件"""
        return self.services.case_service.repository.get_case_by_id(case_id)

    def get_all_cases(self) -> List[CaseData]:
        """取得所有案件"""
        return self.services.case_service.repository.get_all_cases()

    def get_cases(self) -> List[CaseData]:
        """取得所有案件 - 向後相容方法"""
        return self.get_all_cases()

    def get_cases_by_type(self, case_type: str) -> List[CaseData]:
        """根據類型取得案件"""
        return self.services.case_service.repository.get_cases_by_type(case_type)

    def search_cases(self, keyword: str) -> List[CaseData]:
        """搜尋案件"""
        try:
            return self.services.case_service.repository.search_cases(keyword)
        except Exception as e:
            print(f"❌ 搜尋案件失敗: {e}")
            return []

    def get_case_folder_path(self, case_id: str) -> Optional[str]:
        """取得案件資料夾路徑"""
        try:
            case = self.get_case_by_id(case_id)
            if not case:
                return None

            case_type_folder = AppConfig.CASE_TYPE_FOLDERS.get(case.case_type, case.case_type)
            folder_path = os.path.join(self.data_folder, case_type_folder, case_id)

            return folder_path if os.path.exists(folder_path) else None
        except Exception as e:
            print(f"❌ 取得資料夾路徑失敗: {e}")
            return None
