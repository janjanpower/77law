#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
案件服務 - 修正版本
提供案件管理的核心業務邏輯，包含案件編號生成功能
"""

from typing import List, Optional, Dict, Any, Tuple
from models.case_model import CaseData
from datetime import datetime
import json
import os


class CaseRepository:
    """案件資料存取器"""

    def __init__(self, data_file: str):
        """
        初始化資料存取器

        Args:
            data_file: 資料檔案路徑
        """
        self.data_file = data_file
        self.cases = []
        self._load_data()

    def _load_data(self) -> bool:
        """載入資料"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # 資料遷移處理
                migrated_data = [self._migrate_case_data(case_data) for case_data in data]
                self.cases = [CaseData.from_dict(case_data) for case_data in migrated_data]

                print(f"✅ 成功載入 {len(self.cases)} 筆案件資料")
            else:
                print(f"⚠️ 資料檔案不存在，建立新的空資料庫：{self.data_file}")
                self.cases = []
                self._save_data()

            return True

        except Exception as e:
            print(f"❌ 載入案件資料失敗: {e}")
            import traceback
            traceback.print_exc()
            self.cases = []
            return False

    def _migrate_case_data(self, case_data: dict) -> dict:
        """遷移舊格式資料"""
        # 確保必要欄位存在
        required_fields = {
            'case_id': '',
            'client': '',
            'case_type': '',
            'status': '待處理',
            'notes': '',
            'creation_date': datetime.now().isoformat(),
            'updated_date': datetime.now().isoformat()
        }

        for field, default_value in required_fields.items():
            if field not in case_data:
                case_data[field] = default_value

        return case_data

    def _save_data(self) -> bool:
        """儲存資料"""
        try:
            print(f"🔄 開始儲存 {len(self.cases)} 筆案件資料到: {self.data_file}")

            data = [case.to_dict() for case in self.cases]

            # 確保資料夾存在
            os.makedirs(os.path.dirname(self.data_file), exist_ok=True)

            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            print(f"✅ 成功儲存 {len(self.cases)} 筆案件資料")
            return True

        except Exception as e:
            print(f"❌ 儲存案件資料失敗: {e}")
            import traceback
            traceback.print_exc()
            return False

    # 基本CRUD操作
    def create_case(self, case_data: CaseData) -> Tuple[bool, str]:
        """建立案件"""
        try:
            # 檢查案件編號是否重複
            if any(c.case_id == case_data.case_id for c in self.cases):
                return False, f"案件編號 {case_data.case_id} 已存在"

            # 新增案件到列表
            self.cases.append(case_data)

            # 儲存資料
            if self._save_data():
                return True, f"成功建立案件: {case_data.client}"
            else:
                # 儲存失敗，回復變更
                self.cases.remove(case_data)
                return False, "儲存案件資料失敗"

        except Exception as e:
            return False, f"建立案件失敗: {str(e)}"

    def update_case(self, case_data: CaseData) -> Tuple[bool, str]:
        """更新案件"""
        try:
            for i, case in enumerate(self.cases):
                if case.case_id == case_data.case_id:
                    case_data.updated_date = datetime.now()
                    self.cases[i] = case_data

                    if self._save_data():
                        return True, f"成功更新案件: {case_data.client}"
                    else:
                        return False, "儲存更新資料失敗"

            return False, f"找不到案件編號: {case_data.case_id}"

        except Exception as e:
            return False, f"更新案件失敗: {str(e)}"

    def delete_case(self, case_id: str) -> Tuple[bool, str]:
        """刪除案件"""
        try:
            for i, case in enumerate(self.cases):
                if case.case_id == case_id:
                    deleted_case = self.cases.pop(i)

                    if self._save_data():
                        return True, f"成功刪除案件: {deleted_case.client}"
                    else:
                        # 儲存失敗，回復變更
                        self.cases.insert(i, deleted_case)
                        return False, "儲存刪除資料失敗"

            return False, f"找不到案件編號: {case_id}"

        except Exception as e:
            return False, f"刪除案件失敗: {str(e)}"

    # 查詢操作
    def get_case_by_id(self, case_id: str) -> Optional[CaseData]:
        """根據ID取得案件"""
        for case in self.cases:
            if case.case_id == case_id:
                return case
        return None

    def get_all_cases(self) -> List[CaseData]:
        """取得所有案件"""
        return self.cases.copy()

    def get_cases_by_type(self, case_type: str) -> List[CaseData]:
        """根據類型取得案件"""
        return [case for case in self.cases if case.case_type == case_type]

    def get_cases_by_status(self, status: str) -> List[CaseData]:
        """根據狀態取得案件"""
        return [case for case in self.cases if hasattr(case, 'status') and case.status == status]

    def search_cases(self, keyword: str, fields=None) -> List[CaseData]:
        """搜尋案件"""
        if not keyword:
            return self.cases.copy()

        if fields is None:
            fields = ['client', 'case_type', 'case_id', 'notes']

        results = []
        keyword_lower = keyword.lower()

        for case in self.cases:
            for field in fields:
                if hasattr(case, field):
                    field_value = getattr(case, field)
                    if field_value and keyword_lower in str(field_value).lower():
                        results.append(case)
                        break

        return results


class CaseService:
    """案件業務邏輯服務 - 修正版本"""

    def __init__(self, data_folder: str, data_file: str = None):
        """
        初始化案件服務

        Args:
            data_folder: 資料資料夾路徑
            data_file: 案件資料檔案路徑
        """
        self.data_folder = data_folder
        self.data_file = data_file or os.path.join(data_folder, "cases.json")

        # 初始化資料存取器
        self.repository = CaseRepository(self.data_file)

        # 延遲初始化其他服務以避免循環依賴
        self.validation_service = None
        self.folder_service = None
        self.notification_service = None

        print("✅ CaseService 初始化完成")

    def _get_validation_service(self):
        """延遲取得驗證服務"""
        if self.validation_service is None:
            # 使用簡化的驗證服務
            from .validation_service import ValidationService
            self.validation_service = ValidationService()
        return self.validation_service

    def _get_folder_service(self):
        """延遲取得資料夾服務"""
        if self.folder_service is None:
            from .folder_service import FolderService
            self.folder_service = FolderService(self.data_folder)
        return self.folder_service

    def _get_notification_service(self):
        """延遲取得通知服務"""
        if self.notification_service is None:
            from .notification_service import NotificationService
            self.notification_service = NotificationService()
        return self.notification_service

    # ==================== 案件編號管理 ====================

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
            minguo_year = current_year - 1911

            # 取得現有所有案件編號
            all_cases = self.repository.get_all_cases()
            existing_ids = {case.case_id for case in all_cases if case.case_id}

            # 找出當年度最大編號
            current_year_prefix = f"{minguo_year:03d}"
            max_number = 0

            for case_id in existing_ids:
                if case_id.startswith(current_year_prefix) and len(case_id) == 6:
                    try:
                        number = int(case_id[3:])
                        max_number = max(max_number, number)
                    except ValueError:
                        continue

            # 產生新編號
            new_number = max_number + 1
            new_case_id = f"{current_year_prefix}{new_number:03d}"

            print(f"✅ CaseService: 產生新案件編號: {new_case_id}")
            return new_case_id

        except Exception as e:
            print(f"❌ CaseService: 產生案件編號失敗: {e}")
            # 備用方案
            current_year = datetime.now().year
            minguo_year = current_year - 1911
            backup_id = f"{minguo_year:03d}001"
            print(f"⚠️ CaseService: 使用備用編號: {backup_id}")
            return backup_id

    def validate_case_id_format(self, case_id: str) -> Tuple[bool, str]:
        """驗證案件編號格式"""
        if not case_id or len(case_id) != 6:
            return False, "案件編號必須是6位數字"

        try:
            year_part = int(case_id[:3])
            number_part = int(case_id[3:])

            if year_part < 100 or year_part > 200:
                return False, "年分範圍錯誤"
            if number_part < 1 or number_part > 999:
                return False, "編號範圍錯誤"

            return True, "格式正確"
        except ValueError:
            return False, "必須是數字格式"

    def check_case_id_duplicate(self, case_id: str, exclude_case_id: str = None) -> bool:
        """檢查案件編號是否重複"""
        all_cases = self.repository.get_all_cases()
        for case in all_cases:
            if case.case_id == case_id and case.case_id != exclude_case_id:
                return True
        return False

    # ==================== 案件業務邏輯 ====================

    def create_case(self, case_data: CaseData, create_folder: bool = True) -> Tuple[bool, str]:
        """建立案件（含業務邏輯驗證）"""
        try:
            # 1. 驗證案件資料
            validation_service = self._get_validation_service()
            is_valid, error_msg = validation_service.validate_case_data(case_data)
            if not is_valid:
                return False, f"資料驗證失敗: {error_msg}"

            # 2. 如果沒有案件編號，自動產生
            if not case_data.case_id:
                case_data.case_id = self.generate_case_id(case_data.case_type)

            # 3. 檢查編號重複
            if self.check_case_id_duplicate(case_data.case_id):
                return False, f"案件編號 {case_data.case_id} 已存在"

            # 4. 建立案件資料
            result = self.repository.create_case(case_data)
            if not result[0]:
                return result

            # 5. 建立資料夾（如果需要）
            if create_folder:
                try:
                    folder_service = self._get_folder_service()
                    folder_result = folder_service.create_case_folder_structure(case_data)
                    if not folder_result[0]:
                        print(f"⚠️ 警告: 建立資料夾失敗 - {folder_result[1]}")
                except Exception as e:
                    print(f"⚠️ 警告: 建立資料夾異常 - {e}")

            print(f"✅ CaseService: 成功建立案件 {case_data.client}")
            return True, f"成功建立案件: {case_data.client}"

        except Exception as e:
            return False, f"建立案件失敗: {str(e)}"

    def update_case(self, case_data: CaseData, update_folder: bool = False) -> Tuple[bool, str]:
        """更新案件"""
        try:
            # 驗證資料
            validation_service = self._get_validation_service()
            is_valid, error_msg = validation_service.validate_case_data(case_data)
            if not is_valid:
                return False, f"資料驗證失敗: {error_msg}"

            # 更新案件
            result = self.repository.update_case(case_data)
            if not result[0]:
                return result

            # 更新資料夾（如果需要）
            if update_folder:
                try:
                    folder_service = self._get_folder_service()
                    folder_service.update_case_folder_structure(case_data)
                except Exception as e:
                    print(f"⚠️ 警告: 更新資料夾失敗 - {e}")

            return True, f"成功更新案件: {case_data.client}"

        except Exception as e:
            return False, f"更新案件失敗: {str(e)}"

    def delete_case(self, case_id: str) -> Tuple[bool, str]:
        """刪除案件"""
        try:
            # 先取得案件資料
            case_data = self.repository.get_case_by_id(case_id)
            if not case_data:
                return False, f"找不到案件: {case_id}"

            # 刪除案件資料
            result = self.repository.delete_case(case_id)
            return result

        except Exception as e:
            return False, f"刪除案件失敗: {str(e)}"

    # ==================== 查詢方法 ====================

    def get_case_by_id(self, case_id: str) -> Optional[CaseData]:
        """根據ID取得案件"""
        return self.repository.get_case_by_id(case_id)

    def get_all_cases(self) -> List[CaseData]:
        """取得所有案件"""
        return self.repository.get_all_cases()

    def search_cases(self, keyword: str) -> List[CaseData]:
        """搜尋案件"""
        return self.repository.search_cases(keyword)

    def get_case_statistics(self) -> Dict[str, Any]:
        """取得案件統計"""
        all_cases = self.repository.get_all_cases()
        total = len(all_cases)

        by_type = {}
        by_status = {}

        for case in all_cases:
            # 統計類型
            case_type = case.case_type or "未分類"
            by_type[case_type] = by_type.get(case_type, 0) + 1

            # 統計狀態 - 使用progress作為狀態
            status = getattr(case, 'progress', '待處理')
            by_status[status] = by_status.get(status, 0) + 1

        return {
            'total_cases': total,
            'by_type': by_type,
            'by_status': by_status,
            'last_updated': datetime.now().isoformat()
        }