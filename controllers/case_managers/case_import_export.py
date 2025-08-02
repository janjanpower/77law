#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
案件匯入匯出管理器
專責案件資料的匯入匯出功能

"""

import os
from datetime import datetime
from typing import List, Tuple, Dict, Any
from models.case_model import CaseData
from utils.excel import ExcelHandler


class CaseImportExport:
    """案件匯入匯出管理器"""

    def __init__(self, data_folder: str):
        """
        初始化匯入匯出管理器

        Args:
            data_folder: 資料資料夾路徑
        """
        self.data_folder = data_folder

    def export_to_excel(self, cases: List[CaseData], file_path: str = None) -> bool:
        """
        匯出案件資料到 Excel

        Args:
            cases: 案件資料列表
            file_path: 匯出檔案路徑，None則自動生成

        Returns:
            bool: 匯出是否成功
        """
        try:
            if file_path is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"案件資料匯出_{timestamp}.xlsx"
                file_path = os.path.join(self.data_folder, filename)

            success = ExcelHandler.export_cases_to_excel(cases, file_path)
            if success:
                print(f"已匯出案件資料到：{file_path}")
            return success

        except Exception as e:
            print(f"匯出Excel失敗: {e}")
            return False

    def import_from_excel(self, file_path: str) -> Tuple[bool, List[CaseData], str]:
        """
        從 Excel 匯入案件資料

        Args:
            file_path: Excel檔案路徑

        Returns:
            Tuple[bool, List[CaseData], str]: (成功與否, 匯入的案件列表, 訊息)
        """
        try:
            imported_cases = ExcelHandler.import_cases_from_excel(file_path)

            if imported_cases:
                print(f"從Excel成功匯入 {len(imported_cases)} 筆案件資料")
                return True, imported_cases, f"成功匯入 {len(imported_cases)} 筆案件資料"
            else:
                return False, [], "未能從Excel檔案中讀取到有效的案件資料"

        except Exception as e:
            error_msg = f"匯入Excel失敗: {str(e)}"
            print(error_msg)
            return False, [], error_msg

    def _case_matches_criteria(self, case: CaseData, criteria: Dict[str, Any]) -> bool:
        """
        檢查案件是否符合篩選條件

        Args:
            case: 案件資料
            criteria: 篩選條件

        Returns:
            bool: 是否符合條件
        """
        for key, value in criteria.items():
            if value is None or value == "":
                continue

            case_value = getattr(case, key, None)

            if key == 'case_type' and case_value != value:
                return False
            elif key == 'progress' and case_value != value:
                return False
            elif key == 'lawyer' and case_value != value:
                return False
            elif key == 'legal_affairs' and case_value != value:
                return False
            elif key == 'date_range':
                # 日期範圍篩選
                if not self._check_date_range(case.progress_date, value):
                    return False
            elif key == 'keyword':
                # 關鍵字搜尋
                if not self._check_keyword_match(case, value):
                    return False

        return True

    def _check_date_range(self, case_date: str, date_range: Dict[str, str]) -> bool:
        """
        檢查日期是否在指定範圍內

        Args:
            case_date: 案件日期
            date_range: 日期範圍 {'start': 'YYYY-MM-DD', 'end': 'YYYY-MM-DD'}

        Returns:
            bool: 是否在範圍內
        """
        if not case_date:
            return False

        try:
            start_date = date_range.get('start')
            end_date = date_range.get('end')

            if start_date and case_date < start_date:
                return False
            if end_date and case_date > end_date:
                return False

            return True

        except Exception:
            return False

    def _check_keyword_match(self, case: CaseData, keyword: str) -> bool:
        """
        檢查案件是否符合關鍵字搜尋

        Args:
            case: 案件資料
            keyword: 搜尋關鍵字

        Returns:
            bool: 是否符合
        """
        keyword = keyword.lower()
        search_fields = [
            case.case_id, case.client, case.lawyer, case.legal_affairs,
            case.progress, case.case_reason, case.court, case.division
        ]

        for field in search_fields:
            if field and keyword in field.lower():
                return True

        return False

    def _get_filter_description(self, filter_criteria: Dict[str, Any]) -> str:
        """
        取得篩選條件的描述

        Args:
            filter_criteria: 篩選條件

        Returns:
            str: 篩選描述
        """
        descriptions = []

        if filter_criteria.get('case_type'):
            descriptions.append(filter_criteria['case_type'])
        if filter_criteria.get('progress'):
            descriptions.append(filter_criteria['progress'])
        if filter_criteria.get('keyword'):
            descriptions.append(f"關鍵字{filter_criteria['keyword']}")

        return "_".join(descriptions) if descriptions else "篩選資料"


    def update_excel_content_for_case_id_change(self, old_case_id: str, new_case_id: str) -> Tuple[bool, str]:
        """
        更新Excel檔案內容中的案件編號 - CaseImportExport的職責

        Args:
            old_case_id: 原案件編號
            new_case_id: 新案件編號

        Returns:
            Tuple[bool, str]: (是否成功, 訊息)
        """
        try:
            print(f"📋 CaseImportExport 更新Excel內容: {old_case_id} → {new_case_id}")

            # 找到要更新的案件
            case_data = self._find_case_by_id(new_case_id)
            if not case_data:
                return False, f"找不到案件: {new_case_id}"

            # 找到Excel檔案
            excel_files = self._find_all_excel_files_for_case(case_data)
            if not excel_files:
                return False, "找不到相關的Excel檔案"

            updated_count = 0
            total_count = len(excel_files)

            for excel_file in excel_files:
                try:
                    if self._update_excel_file_content(excel_file, old_case_id, new_case_id, case_data):
                        updated_count += 1
                        print(f"   ✅ 更新Excel內容: {os.path.basename(excel_file)}")
                    else:
                        print(f"   ⚠️ 更新Excel內容失敗: {os.path.basename(excel_file)}")

                except Exception as e:
                    print(f"   ❌ 更新Excel檔案失敗 {os.path.basename(excel_file)}: {e}")

            if updated_count > 0:
                message = f"Excel內容更新完成 ({updated_count}/{total_count} 檔案)"
                print(f"✅ {message}")
                return True, message
            else:
                return False, "所有Excel檔案內容更新失敗"

        except Exception as e:
            print(f"❌ CaseImportExport 更新Excel內容失敗: {e}")
            return False, f"Excel內容更新失敗: {str(e)}"

    def _update_excel_file_content(self, excel_file_path: str, old_case_id: str, new_case_id: str, case_data: CaseData) -> bool:
        """更新單個Excel檔案的內容"""
        try:
            # 檢查pandas是否可用
            try:
                import pandas as pd
            except ImportError:
                print(f"⚠️ 缺少pandas套件，無法更新Excel內容")
                return False

            # 讀取Excel檔案
            excel_sheets = pd.read_excel(excel_file_path, sheet_name=None, engine='openpyxl')

            updated = False

            # 更新每個工作表
            for sheet_name, df in excel_sheets.items():
                # 將所有包含舊案件編號的內容替換為新案件編號
                for column in df.columns:
                    if df[column].dtype == 'object':  # 只處理文字欄位
                        mask = df[column].astype(str).str.contains(old_case_id, na=False)
                        if mask.any():
                            df.loc[mask, column] = df.loc[mask, column].astype(str).str.replace(old_case_id, new_case_id)
                            updated = True
                            print(f"     工作表 '{sheet_name}' 欄位 '{column}' 已更新")

            if updated:
                # 寫回Excel檔案
                with pd.ExcelWriter(excel_file_path, engine='openpyxl') as writer:
                    for sheet_name, df in excel_sheets.items():
                        df.to_excel(writer, sheet_name=sheet_name, index=False)

                print(f"     Excel檔案內容更新完成: {os.path.basename(excel_file_path)}")

            return updated

        except Exception as e:
            print(f"❌ 更新Excel檔案內容失敗: {e}")
            return False

    def _find_all_excel_files_for_case(self, case_data: CaseData) -> List[str]:
        """尋找案件相關的所有Excel檔案"""
        try:
            excel_files = []

            # 取得案件資料夾路徑
            case_folder_path = self._get_case_folder_path(case_data)
            if not case_folder_path:
                return excel_files

            # 遞歸尋找所有Excel檔案
            for root, dirs, files in os.walk(case_folder_path):
                for filename in files:
                    if filename.endswith('.xlsx') and not filename.startswith('~'):
                        excel_files.append(os.path.join(root, filename))

            return excel_files

        except Exception as e:
            print(f"❌ 尋找Excel檔案失敗: {e}")
            return []