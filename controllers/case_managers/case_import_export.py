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

    def merge_imported_cases(self, existing_cases: List[CaseData], imported_cases: List[CaseData],
                           merge_strategy: str = 'skip_duplicates') -> Tuple[List[CaseData], Dict[str, Any]]:
        """
        合併匯入的案件資料

        Args:
            existing_cases: 現有案件列表
            imported_cases: 匯入的案件列表
            merge_strategy: 合併策略 ('skip_duplicates', 'overwrite', 'keep_both')

        Returns:
            Tuple[List[CaseData], Dict[str, Any]]: (合併後的案件列表, 合併統計資訊)
        """
        merged_cases = existing_cases.copy()
        stats = {
            'total_imported': len(imported_cases),
            'added': 0,
            'skipped': 0,
            'overwritten': 0,
            'duplicates': [],
            'errors': []
        }

        try:
            # 建立現有案件的查找字典 (case_type + case_id -> index)
            existing_lookup = {}
            for i, case in enumerate(existing_cases):
                key = f"{case.case_type}_{case.case_id}"
                existing_lookup[key] = i

            for imported_case in imported_cases:
                key = f"{imported_case.case_type}_{imported_case.case_id}"

                if key in existing_lookup:
                    # 處理重複案件
                    existing_index = existing_lookup[key]
                    duplicate_info = {
                        'case_id': imported_case.case_id,
                        'case_type': imported_case.case_type,
                        'existing_client': existing_cases[existing_index].client,
                        'imported_client': imported_case.client
                    }
                    stats['duplicates'].append(duplicate_info)

                    if merge_strategy == 'skip_duplicates':
                        stats['skipped'] += 1
                        continue
                    elif merge_strategy == 'overwrite':
                        merged_cases[existing_index] = imported_case
                        stats['overwritten'] += 1
                    elif merge_strategy == 'keep_both':
                        # 為重複案件生成新編號
                        new_case_id = self._generate_unique_case_id(
                            imported_case.case_type,
                            imported_case.case_id,
                            merged_cases
                        )
                        imported_case.case_id = new_case_id
                        merged_cases.append(imported_case)
                        stats['added'] += 1
                else:
                    # 新增案件
                    merged_cases.append(imported_case)
                    stats['added'] += 1

            print(f"合併完成 - 新增: {stats['added']}, 跳過: {stats['skipped']}, 覆寫: {stats['overwritten']}")
            return merged_cases, stats

        except Exception as e:
            error_msg = f"合併匯入資料失敗: {str(e)}"
            print(error_msg)
            stats['errors'].append(error_msg)
            return existing_cases, stats

    def _generate_unique_case_id(self, case_type: str, original_case_id: str,
                                existing_cases: List[CaseData]) -> str:
        """
        為重複案件生成唯一的案件編號

        Args:
            case_type: 案件類型
            original_case_id: 原始案件編號
            existing_cases: 現有案件列表

        Returns:
            str: 唯一的案件編號
        """
        base_id = original_case_id
        counter = 1

        # 如果原編號是 CIVIL001，嘗試 CIVIL001_1, CIVIL001_2 等
        while True:
            new_case_id = f"{base_id}_{counter}"

            # 檢查是否重複
            is_duplicate = any(
                case.case_id == new_case_id and case.case_type == case_type
                for case in existing_cases
            )

            if not is_duplicate:
                return new_case_id

            counter += 1

            # 防止無限循環
            if counter > 999:
                timestamp = datetime.now().strftime("%H%M%S")
                return f"{base_id}_{timestamp}"

    def export_filtered_cases(self, cases: List[CaseData], filter_criteria: Dict[str, Any],
                             file_path: str = None) -> bool:
        """
        匯出符合條件的案件資料

        Args:
            cases: 案件資料列表
            filter_criteria: 篩選條件字典
            file_path: 匯出檔案路徑

        Returns:
            bool: 匯出是否成功
        """
        try:
            # 篩選案件
            filtered_cases = self._filter_cases(cases, filter_criteria)

            if not filtered_cases:
                print("沒有符合條件的案件資料可供匯出")
                return False

            # 生成檔案名稱
            if file_path is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filter_desc = self._get_filter_description(filter_criteria)
                filename = f"案件資料_{filter_desc}_{timestamp}.xlsx"
                file_path = os.path.join(self.data_folder, filename)

            # 匯出
            success = ExcelHandler.export_cases_to_excel(filtered_cases, file_path)
            if success:
                print(f"已匯出 {len(filtered_cases)} 筆符合條件的案件資料到：{file_path}")

            return success

        except Exception as e:
            print(f"匯出篩選案件失敗: {e}")
            return False

    def _filter_cases(self, cases: List[CaseData], filter_criteria: Dict[str, Any]) -> List[CaseData]:
        """
        根據條件篩選案件

        Args:
            cases: 案件資料列表
            filter_criteria: 篩選條件

        Returns:
            List[CaseData]: 篩選後的案件列表
        """
        filtered_cases = []

        for case in cases:
            if self._case_matches_criteria(case, filter_criteria):
                filtered_cases.append(case)

        return filtered_cases

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

    def validate_import_file(self, file_path: str) -> Tuple[bool, str]:
        """
        驗證匯入檔案的有效性

        Args:
            file_path: 檔案路徑

        Returns:
            Tuple[bool, str]: (是否有效, 驗證訊息)
        """
        try:
            # 檢查檔案是否存在
            if not os.path.exists(file_path):
                return False, "檔案不存在"

            # 檢查檔案副檔名
            if not file_path.lower().endswith(('.xlsx', '.xls')):
                return False, "檔案格式必須是 Excel (.xlsx 或 .xls)"

            # 檢查檔案大小（避免過大的檔案）
            file_size = os.path.getsize(file_path)
            max_size = 50 * 1024 * 1024  # 50MB
            if file_size > max_size:
                return False, f"檔案大小超過限制 ({file_size / 1024 / 1024:.1f}MB > 50MB)"

            # 嘗試讀取檔案檢查是否損壞
            try:
                ExcelHandler.validate_excel_file(file_path)
                return True, "檔案驗證通過"
            except Exception as e:
                return False, f"檔案格式錯誤: {str(e)}"

        except Exception as e:
            return False, f"驗證檔案時發生錯誤: {str(e)}"

    def get_import_preview(self, file_path: str, max_rows: int = 10) -> Tuple[bool, List[Dict], str]:
        """
        取得匯入檔案的預覽資料

        Args:
            file_path: 檔案路徑
            max_rows: 最大預覽行數

        Returns:
            Tuple[bool, List[Dict], str]: (成功與否, 預覽資料, 訊息)
        """
        try:
            # 先驗證檔案
            is_valid, message = self.validate_import_file(file_path)
            if not is_valid:
                return False, [], message

            # 讀取預覽資料
            preview_data = ExcelHandler.get_excel_preview(file_path, max_rows)

            if preview_data:
                return True, preview_data, f"成功讀取 {len(preview_data)} 行預覽資料"
            else:
                return False, [], "無法讀取檔案內容"

        except Exception as e:
            error_msg = f"讀取預覽資料失敗: {str(e)}"
            print(error_msg)
            return False, [], error_msg