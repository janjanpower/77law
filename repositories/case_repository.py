#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
案件資料存取層 (Case Repository)
專責處理案件資料的CRUD操作和查詢邏輯
"""

import os
import json
import threading
from typing import List, Optional, Dict, Any
from datetime import datetime
from models.case_model import CaseData


class CaseRepository:
    """案件資料存取器 - 專責資料持久化"""

    def __init__(self, data_file: str):
        """
        初始化案件資料存取器

        Args:
            data_file: 案件資料檔案路徑
        """
        self.data_file = data_file
        self.cases = []
        self._lock = threading.Lock()  # 執行緒安全
        self._load_cases()

    # ==================== 資料載入與儲存 ====================

    def _load_cases(self) -> bool:
        """
        載入案件資料

        Returns:
            bool: 載入是否成功
        """
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 確保資料格式正確
                    self.cases = []
                    for item in data:
                        try:
                            if isinstance(item, dict):
                                case_data = CaseData.from_dict(item)
                                self.cases.append(case_data)
                            elif isinstance(item, CaseData):
                                self.cases.append(item)
                            elif isinstance(item, str):
                                # 處理可能的字串資料（跳過或記錄錯誤）
                                print(f"⚠️ 跳過無效的案件資料: {item}")
                                continue
                            else:
                                print(f"⚠️ 未知的資料格式: {type(item)}")
                        except Exception as item_error:
                            print(f"⚠️ 處理案件資料項目失敗: {item_error}")
                            continue

                print(f"✅ 成功載入 {len(self.cases)} 筆案件資料")
                return True
            else:
                print("📂 案件資料檔案不存在，將建立新檔案")
                self.cases = []
                return True

        except Exception as e:
            print(f"❌ 載入案件資料失敗: {e}")
            print(f"錯誤詳情: {type(e).__name__}: {str(e)}")
            self.cases = []
            return False

    def _save_cases(self) -> bool:
        """
        儲存案件資料到檔案

        Returns:
            bool: 儲存是否成功
        """
        try:
            # 確保目錄存在
            os.makedirs(os.path.dirname(self.data_file), exist_ok=True)

            # 將資料轉換為字典格式
            data = []
            for case in self.cases:
                if hasattr(case, 'to_dict'):
                    data.append(case.to_dict())
                else:
                    # 如果沒有 to_dict 方法，嘗試直接序列化
                    data.append(case.__dict__)

            # 寫入檔案
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)

            print(f"✅ 成功儲存 {len(self.cases)} 筆案件資料")
            return True

        except Exception as e:
            print(f"❌ 儲存案件資料失敗: {e}")
            return False

    def reload_data(self) -> bool:
        """
        重新載入資料（用於資料同步）

        Returns:
            bool: 重新載入是否成功
        """
        with self._lock:
            return self._load_cases()

    # ==================== CRUD 操作 ====================

    def create_case(self, case_data: CaseData) -> bool:
        """
        新增案件

        Args:
            case_data: 案件資料

        Returns:
            bool: 新增是否成功
        """
        try:
            with self._lock:
                # 檢查是否已存在相同ID的案件
                if self.get_case_by_id(case_data.case_id):
                    print(f"❌ 案件ID已存在: {case_data.case_id}")
                    return False

                # 設定建立時間
                if not case_data.creation_date:
                    case_data.creation_date = datetime.now()

                # 新增到記憶體
                self.cases.append(case_data)

                # 儲存到檔案
                return self._save_cases()

        except Exception as e:
            print(f"❌ 新增案件失敗: {e}")
            return False

    def update_case(self, case_data: CaseData) -> bool:
        """
        更新案件

        Args:
            case_data: 更新後的案件資料

        Returns:
            bool: 更新是否成功
        """
        try:
            with self._lock:
                # 找到要更新的案件索引
                case_index = None
                for i, case in enumerate(self.cases):
                    if case.case_id == case_data.case_id:
                        case_index = i
                        break

                if case_index is None:
                    print(f"❌ 找不到要更新的案件: {case_data.case_id}")
                    return False

                # 設定更新時間
                case_data.last_modified = datetime.now()

                # 更新案件資料
                self.cases[case_index] = case_data

                # 儲存到檔案
                return self._save_cases()

        except Exception as e:
            print(f"❌ 更新案件失敗: {e}")
            return False

    def delete_case(self, case_id: str) -> bool:
        """
        刪除案件

        Args:
            case_id: 案件ID

        Returns:
            bool: 刪除是否成功
        """
        try:
            with self._lock:
                # 找到要刪除的案件
                case_to_delete = None
                for i, case in enumerate(self.cases):
                    if case.case_id == case_id:
                        case_to_delete = i
                        break

                if case_to_delete is None:
                    print(f"❌ 找不到要刪除的案件: {case_id}")
                    return False

                # 從記憶體中移除
                deleted_case = self.cases.pop(case_to_delete)
                print(f"🗑️ 準備刪除案件: {deleted_case.client} ({case_id})")

                # 儲存到檔案
                return self._save_cases()

        except Exception as e:
            print(f"❌ 刪除案件失敗: {e}")
            return False

    # ==================== 查詢操作 ====================

    def get_all_cases(self) -> List[CaseData]:
        """
        取得所有案件

        Returns:
            List[CaseData]: 所有案件資料
        """
        with self._lock:
            # 過濾掉無效的資料
            valid_cases = []
            for case in self.cases:
                try:
                    if isinstance(case, str):
                        print(f"⚠️ 跳過無效的字串資料: {case}")
                        continue

                    # 檢查是否有基本屬性
                    if hasattr(case, 'case_id') and hasattr(case, 'client'):
                        valid_cases.append(case)
                    else:
                        print(f"⚠️ 跳過缺少基本屬性的案件: {case}")
                except Exception as e:
                    print(f"⚠️ 檢查案件時發生錯誤: {e}")
                    continue

            return valid_cases

    def get_case_by_id(self, case_id: str) -> Optional[CaseData]:
        """
        根據ID取得案件

        Args:
            case_id: 案件ID

        Returns:
            Optional[CaseData]: 案件資料或None
        """
        with self._lock:
            for case in self.cases:
                if hasattr(case, 'case_id') and case.case_id == case_id:
                    return case
            return None

    def get_cases_by_client(self, client_name: str) -> List[CaseData]:
        """
        根據當事人姓名取得案件

        Args:
            client_name: 當事人姓名

        Returns:
            List[CaseData]: 符合條件的案件列表
        """
        with self._lock:
            return [case for case in self.cases
                   if hasattr(case, 'client') and case.client == client_name]

    def get_cases_by_type(self, case_type: str) -> List[CaseData]:
        """
        根據案件類型取得案件

        Args:
            case_type: 案件類型

        Returns:
            List[CaseData]: 符合條件的案件列表
        """
        with self._lock:
            results = []
            for case in self.cases:
                try:
                    # 安全檢查：確保是有效的案件物件
                    if isinstance(case, str):
                        print(f"⚠️ 跳過無效的字串資料: {case}")
                        continue

                    if hasattr(case, 'case_type') and case.case_type == case_type:
                        results.append(case)
                except Exception as e:
                    print(f"⚠️ 處理案件資料時發生錯誤: {e}")
                    continue
            return results

    def get_cases_by_status(self, status: str) -> List[CaseData]:
        """
        根據案件狀態取得案件

        Args:
            status: 案件狀態

        Returns:
            List[CaseData]: 符合條件的案件列表
        """
        with self._lock:
            return [case for case in self.cases
                   if hasattr(case, 'status') and case.status == status]

    def search_cases(self, keyword: str, fields: List[str] = None) -> List[CaseData]:
        """
        搜尋案件

        Args:
            keyword: 搜尋關鍵字
            fields: 要搜尋的欄位列表

        Returns:
            List[CaseData]: 符合條件的案件列表
        """
        if not keyword:
            return self.get_all_cases()

        if fields is None:
            fields = ['client', 'case_type', 'case_id', 'notes']

        with self._lock:
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

    def get_cases_by_date_range(self, start_date: datetime, end_date: datetime,
                               date_field: str = 'creation_date') -> List[CaseData]:
        """
        根據日期範圍取得案件

        Args:
            start_date: 開始日期
            end_date: 結束日期
            date_field: 日期欄位名稱

        Returns:
            List[CaseData]: 符合條件的案件列表
        """
        with self._lock:
            results = []
            for case in self.cases:
                if hasattr(case, date_field):
                    case_date = getattr(case, date_field)
                    if case_date and isinstance(case_date, datetime):
                        if start_date <= case_date <= end_date:
                            results.append(case)
            return results

    # ==================== 統計查詢 ====================

    def get_case_count(self) -> int:
        """
        取得案件總數

        Returns:
            int: 案件總數
        """
        with self._lock:
            return len(self.cases)

    def get_case_count_by_type(self) -> Dict[str, int]:
        """
        取得各類型案件數量統計

        Returns:
            Dict[str, int]: 各類型案件數量
        """
        with self._lock:
            type_counts = {}
            for case in self.cases:
                if hasattr(case, 'case_type') and case.case_type:
                    case_type = case.case_type
                    type_counts[case_type] = type_counts.get(case_type, 0) + 1
            return type_counts

    def get_case_count_by_status(self) -> Dict[str, int]:
        """
        取得各狀態案件數量統計

        Returns:
            Dict[str, int]: 各狀態案件數量
        """
        with self._lock:
            status_counts = {}
            for case in self.cases:
                if hasattr(case, 'status') and case.status:
                    status = case.status
                    status_counts[status] = status_counts.get(status, 0) + 1
            return status_counts

    # ==================== 資料驗證 ====================

    def validate_data_integrity(self) -> Dict[str, Any]:
        """
        驗證資料完整性

        Returns:
            Dict[str, Any]: 驗證結果
        """
        with self._lock:
            validation_result = {
                'is_valid': True,
                'total_cases': len(self.cases),
                'issues': [],
                'duplicates': [],
                'missing_fields': []
            }

            # 檢查重複的案件ID
            case_ids = []
            for case in self.cases:
                if hasattr(case, 'case_id'):
                    if case.case_id in case_ids:
                        validation_result['duplicates'].append(case.case_id)
                        validation_result['is_valid'] = False
                    else:
                        case_ids.append(case.case_id)

            # 檢查必要欄位
            required_fields = ['case_id', 'client', 'case_type']
            for i, case in enumerate(self.cases):
                missing = []
                for field in required_fields:
                    if not hasattr(case, field) or not getattr(case, field):
                        missing.append(field)

                if missing:
                    validation_result['missing_fields'].append({
                        'case_index': i,
                        'missing_fields': missing
                    })
                    validation_result['is_valid'] = False

            return validation_result

    # ==================== 批次操作 ====================

    def batch_update_cases(self, updates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        批次更新案件

        Args:
            updates: 更新資料列表，格式: [{'case_id': '', 'updates': {}}]

        Returns:
            Dict[str, Any]: 批次更新結果
        """
        result = {
            'success_count': 0,
            'failed_count': 0,
            'errors': []
        }

        try:
            with self._lock:
                for update_data in updates:
                    case_id = update_data.get('case_id')
                    updates_dict = update_data.get('updates', {})

                    # 找到案件
                    case_found = False
                    for i, case in enumerate(self.cases):
                        if case.case_id == case_id:
                            # 更新欄位
                            for field, value in updates_dict.items():
                                if hasattr(case, field):
                                    setattr(case, field, value)

                            # 設定更新時間
                            case.last_modified = datetime.now()
                            case_found = True
                            result['success_count'] += 1
                            break

                    if not case_found:
                        result['failed_count'] += 1
                        result['errors'].append(f"找不到案件: {case_id}")

                # 儲存變更
                if result['success_count'] > 0:
                    self._save_cases()

        except Exception as e:
            result['errors'].append(f"批次更新失敗: {str(e)}")

        return result

    # ==================== 備份與恢復 ====================

    def backup_data(self, backup_path: str) -> bool:
        """
        備份資料

        Args:
            backup_path: 備份檔案路徑

        Returns:
            bool: 備份是否成功
        """
        try:
            # 確保備份目錄存在
            os.makedirs(os.path.dirname(backup_path), exist_ok=True)

            # 建立備份資料
            backup_data = {
                'backup_time': datetime.now().isoformat(),
                'total_cases': len(self.cases),
                'cases': [case.to_dict() if hasattr(case, 'to_dict') else case.__dict__
                         for case in self.cases]
            }

            # 寫入備份檔案
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, ensure_ascii=False, indent=2, default=str)

            print(f"✅ 案件資料備份成功: {backup_path}")
            return True

        except Exception as e:
            print(f"❌ 備份失敗: {e}")
            return False