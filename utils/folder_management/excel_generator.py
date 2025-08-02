#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Excel檔案生成器
專責案件資訊Excel檔案的生成和更新
"""

import os
import pandas as pd
from typing import Optional, Dict, Any, List
from models.case_model import CaseData
from datetime import datetime

# 檢查pandas和openpyxl是否可用
try:
    import pandas as pd
    import openpyxl
    EXCEL_AVAILABLE = True
except ImportError:
    EXCEL_AVAILABLE = False


class ExcelGenerator:
    """Excel檔案生成工具"""

    def __init__(self):
        """初始化Excel生成器"""
        if not EXCEL_AVAILABLE:
            print("⚠️ 警告：缺少Excel處理依賴套件 (pandas, openpyxl)")

    def create_case_info_excel(self, case_info_folder: str, case_data: CaseData) -> tuple[bool, str]:
        """
        建立案件資訊Excel檔案

        Args:
            case_info_folder: 案件資訊資料夾路徑
            case_data: 案件資料

        Returns:
            (success, file_path_or_error_message)
        """
        if not EXCEL_AVAILABLE:
            return False, "缺少Excel處理依賴套件"

        try:
            # 產生檔案名稱
            excel_filename = self._generate_excel_filename(case_data)
            excel_path = os.path.join(case_info_folder, excel_filename)

            # 建立Excel檔案
            success = self._create_excel_with_sheets(excel_path, case_data)

            if success:
                print(f"✅ 建立案件資訊Excel: {excel_path}")
                return True, excel_path
            else:
                return False, "Excel檔案建立失敗"

        except Exception as e:
            error_msg = f"建立案件資訊Excel失敗: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg

    def update_case_info_excel(self, case_folder_path: str, case_data: CaseData) -> tuple[bool, str]:
        """
        更新案件資訊Excel檔案

        Args:
            case_folder_path: 案件資料夾路徑
            case_data: 更新後的案件資料

        Returns:
            (success, message)
        """
        if not EXCEL_AVAILABLE:
            return False, "缺少Excel處理依賴套件"

        try:
            case_info_folder = os.path.join(case_folder_path, '案件資訊')
            if not os.path.exists(case_info_folder):
                return False, f"找不到案件資訊資料夾: {case_info_folder}"

            # 尋找現有的Excel檔案
            existing_excel = self._find_existing_excel(case_info_folder, case_data)

            if existing_excel:
                # 更新現有檔案
                success = self._update_existing_excel(existing_excel, case_data)
                message = f"更新現有Excel檔案: {os.path.basename(existing_excel)}"
            else:
                # 建立新檔案
                success, result = self.create_case_info_excel(case_info_folder, case_data)
                message = f"建立新Excel檔案: {os.path.basename(result) if success else result}"

            return success, message

        except Exception as e:
            error_msg = f"更新案件資訊Excel失敗: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg

    def export_cases_to_excel(self, cases: List[CaseData], file_path: str) -> tuple[bool, str]:
        """
        匯出多個案件到單一Excel檔案

        Args:
            cases: 案件資料列表
            file_path: 匯出檔案路徑

        Returns:
            (success, message)
        """
        if not EXCEL_AVAILABLE:
            return False, "缺少Excel處理依賴套件"

        try:
            # 準備資料
            export_data = []
            for case in cases:
                case_dict = self._case_to_export_dict(case)
                export_data.append(case_dict)

            # 建立DataFrame
            df = pd.DataFrame(export_data)

            # 匯出到Excel
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='案件清單', index=False)

                # 調整欄寬
                self._adjust_column_widths(writer.sheets['案件清單'], df)

            print(f"✅ 成功匯出 {len(cases)} 個案件到: {file_path}")
            return True, f"成功匯出 {len(cases)} 個案件"

        except Exception as e:
            error_msg = f"匯出案件到Excel失敗: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg

    def _generate_excel_filename(self, case_data: CaseData) -> str:
        """產生Excel檔案名稱"""
        # 清理客戶名稱中的無效字元
        clean_client = self._sanitize_filename(case_data.client)
        return f"{case_data.case_id}_{clean_client}_案件資訊.xlsx"

    def _sanitize_filename(self, filename: str) -> str:
        """清理檔案名稱中的無效字元"""
        invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
        clean_name = filename

        for char in invalid_chars:
            clean_name = clean_name.replace(char, '_')

        return clean_name.strip()

    def _create_excel_with_sheets(self, excel_path: str, case_data: CaseData) -> bool:
        """建立包含多個工作表的Excel檔案"""
        try:
            with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
                # 基本資訊工作表
                basic_info = self._prepare_basic_info_data(case_data)
                basic_df = pd.DataFrame(basic_info, columns=['項目', '內容'])
                basic_df.to_excel(writer, sheet_name='基本資訊', index=False)

                # 詳細資訊工作表
                detail_info = self._prepare_detail_info_data(case_data)
                detail_df = pd.DataFrame(detail_info, columns=['項目', '內容'])
                detail_df.to_excel(writer, sheet_name='詳細資訊', index=False)

                # 進度追蹤工作表
                if case_data.progress_stages:
                    progress_info = self._prepare_progress_info_data(case_data)
                    progress_df = pd.DataFrame(progress_info, columns=['階段', '日期', '備註', '時間'])
                    progress_df.to_excel(writer, sheet_name='進度追蹤', index=False)

                # 調整欄寬
                for sheet_name in writer.sheets:
                    self._adjust_column_widths(writer.sheets[sheet_name],
                                             basic_df if sheet_name == '基本資訊' else detail_df)

            return True

        except Exception as e:
            print(f"❌ 建立Excel工作表失敗: {e}")
            return False

    def _prepare_basic_info_data(self, case_data: CaseData) -> List[List[str]]:
        """準備基本資訊資料"""
        return [
            ['案件編號', case_data.case_id],
            ['案件類型', case_data.case_type],
            ['當事人', case_data.client],
            ['委任律師', getattr(case_data, 'lawyer', '') or ''],
            ['法務', getattr(case_data, 'legal_affairs', '') or ''],
            ['目前進度', getattr(case_data, 'progress', '') or ''],
            ['進度日期', getattr(case_data, 'progress_date', '') or ''],
            ['建立日期', case_data.created_date.strftime('%Y-%m-%d %H:%M:%S') if case_data.created_date else ''],
            ['更新日期', case_data.updated_date.strftime('%Y-%m-%d %H:%M:%S') if case_data.updated_date else '']
        ]

    def _prepare_detail_info_data(self, case_data: CaseData) -> List[List[str]]:
        """準備詳細資訊資料"""
        return [
            ['案由', getattr(case_data, 'case_reason', '') or ''],
            ['案號', getattr(case_data, 'case_number', '') or ''],
            ['對造', getattr(case_data, 'opposing_party', '') or ''],
            ['負責法院', getattr(case_data, 'court', '') or ''],
            ['負責股別', getattr(case_data, 'division', '') or '']
        ]

    def _prepare_progress_info_data(self, case_data: CaseData) -> List[List[str]]:
        """準備進度追蹤資料"""
        progress_data = []

        for stage, date in case_data.progress_stages.items():
            note = case_data.progress_notes.get(stage, '') if hasattr(case_data, 'progress_notes') else ''
            time = case_data.progress_times.get(stage, '') if hasattr(case_data, 'progress_times') else ''

            progress_data.append([stage, date, note, time])

        # 按日期排序
        progress_data.sort(key=lambda x: x[1] if x[1] else '')

        return progress_data

    def _case_to_export_dict(self, case_data: CaseData) -> Dict[str, Any]:
        """將案件資料轉換為匯出字典"""
        return {
            '案件編號': case_data.case_id,
            '案件類型': case_data.case_type,
            '當事人': case_data.client,
            '委任律師': getattr(case_data, 'lawyer', '') or '',
            '法務': getattr(case_data, 'legal_affairs', '') or '',
            '案由': getattr(case_data, 'case_reason', '') or '',
            '案號': getattr(case_data, 'case_number', '') or '',
            '對造': getattr(case_data, 'opposing_party', '') or '',
            '負責法院': getattr(case_data, 'court', '') or '',
            '負責股別': getattr(case_data, 'division', '') or '',
            '目前進度': getattr(case_data, 'progress', '') or '',
            '進度日期': getattr(case_data, 'progress_date', '') or '',
            '建立日期': case_data.created_date.strftime('%Y-%m-%d') if case_data.created_date else '',
            '更新日期': case_data.updated_date.strftime('%Y-%m-%d') if case_data.updated_date else ''
        }

    def _find_existing_excel(self, case_info_folder: str, case_data: CaseData) -> Optional[str]:
        """尋找現有的Excel檔案"""
        try:
            if not os.path.exists(case_info_folder):
                return None

            # 尋找符合案件ID的Excel檔案
            for filename in os.listdir(case_info_folder):
                if filename.endswith('.xlsx') and case_data.case_id in filename:
                    return os.path.join(case_info_folder, filename)

            return None

        except Exception as e:
            print(f"⚠️ 尋找現有Excel檔案失敗: {e}")
            return None

    def _update_existing_excel(self, excel_path: str, case_data: CaseData) -> bool:
        """更新現有的Excel檔案"""
        try:
            # 備份原檔案
            backup_path = f"{excel_path}.backup"
            if os.path.exists(excel_path):
                os.rename(excel_path, backup_path)

            # 建立新檔案
            success = self._create_excel_with_sheets(excel_path, case_data)

            if success:
                # 刪除備份檔案
                if os.path.exists(backup_path):
                    os.remove(backup_path)
                return True
            else:
                # 恢復備份檔案
                if os.path.exists(backup_path):
                    os.rename(backup_path, excel_path)
                return False

        except Exception as e:
            print(f"❌ 更新Excel檔案失敗: {e}")
            return False

    def _adjust_column_widths(self, worksheet, dataframe):
        """調整Excel欄寬"""
        try:
            for column in dataframe:
                column_length = max(
                    dataframe[column].astype(str).map(len).max(),  # 內容最大長度
                    len(str(column))  # 標題長度
                )
                # 設定欄寬，最小10，最大50
                col_letter = openpyxl.utils.get_column_letter(dataframe.columns.get_loc(column) + 1)
                worksheet.column_dimensions[col_letter].width = min(max(column_length + 2, 10), 50)

        except Exception as e:
            print(f"⚠️ 調整欄寬失敗: {e}")

    @staticmethod
    def get_dependency_status() -> str:
        """取得Excel處理依賴狀態"""
        if EXCEL_AVAILABLE:
            return "✅ Excel處理功能可用 (pandas, openpyxl)"
        else:
            return "❌ Excel處理功能不可用，請安裝: pip install pandas openpyxl"