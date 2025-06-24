from typing import List, Optional
from models.case_model import CaseData
from utils.excel_handler import ExcelHandler
import json
import os
from datetime import datetime

class CaseController:
    """案件資料控制器"""

    def __init__(self, data_file: str = "cases_data.json"):
        self.data_file = data_file
        self.cases: List[CaseData] = []
        self.load_cases()

    def load_cases(self) -> bool:
        """載入案件資料"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.cases = [CaseData.from_dict(case_data) for case_data in data]
            return True
        except Exception as e:
            print(f"載入案件資料失敗: {e}")
            return False

    def save_cases(self) -> bool:
        """儲存案件資料"""
        try:
            data = [case.to_dict() for case in self.cases]
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"儲存案件資料失敗: {e}")
            return False

    def add_case(self, case: CaseData) -> bool:
        """新增案件"""
        try:
            # 檢查案件編號是否重複
            if any(c.case_id == case.case_id for c in self.cases):
                raise ValueError(f"案件編號 {case.case_id} 已存在")

            self.cases.append(case)
            return self.save_cases()
        except Exception as e:
            print(f"新增案件失敗: {e}")
            return False

    def update_case(self, case_id: str, updated_case: CaseData) -> bool:
        """更新案件"""
        try:
            for i, case in enumerate(self.cases):
                if case.case_id == case_id:
                    updated_case.updated_date = datetime.now()
                    self.cases[i] = updated_case
                    return self.save_cases()
            raise ValueError(f"找不到案件編號: {case_id}")
        except Exception as e:
            print(f"更新案件失敗: {e}")
            return False

    def delete_case(self, case_id: str) -> bool:
        """刪除案件"""
        try:
            self.cases = [case for case in self.cases if case.case_id != case_id]
            return self.save_cases()
        except Exception as e:
            print(f"刪除案件失敗: {e}")
            return False

    def get_cases(self) -> List[CaseData]:
        """取得所有案件"""
        return self.cases.copy()

    def get_case_by_id(self, case_id: str) -> Optional[CaseData]:
        """根據編號取得案件"""
        for case in self.cases:
            if case.case_id == case_id:
                return case
        return None

    def search_cases(self, keyword: str) -> List[CaseData]:
        """搜尋案件"""
        results = []
        keyword = keyword.lower()

        for case in self.cases:
            if (keyword in case.case_id.lower() or
                keyword in case.case_type.lower() or
                keyword in case.client.lower() or
                (case.lawyer and keyword in case.lawyer.lower()) or
                (case.legal_affairs and keyword in case.legal_affairs.lower()) or
                keyword in case.progress.lower()):
                results.append(case)

        return results

    def export_to_excel(self, file_path: str) -> bool:
        """匯出案件資料到 Excel"""
        return ExcelHandler.export_cases_to_excel(self.cases, file_path)

    def import_from_excel(self, file_path: str) -> bool:
        """從 Excel 匯入案件資料"""
        imported_cases = ExcelHandler.import_cases_from_excel(file_path)
        if imported_cases:
            # 合併資料（避免重複）
            existing_ids = {case.case_id for case in self.cases}
            new_cases = [case for case in imported_cases if case.case_id not in existing_ids]

            self.cases.extend(new_cases)
            return self.save_cases()
        return False

    def generate_case_id(self) -> str:
        """產生新的案件編號"""
        existing_ids = {case.case_id for case in self.cases}
        year = datetime.now().year

        for i in range(1, 10000):
            case_id = f"C{year}{i:04d}"
            if case_id not in existing_ids:
                return case_id

        raise RuntimeError("無法產生唯一的案件編號")
