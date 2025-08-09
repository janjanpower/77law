#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Excel檔案生成器 - 修改版本
🔥 修改：支援「案件編號_當事人」格式的Excel檔案命名和內容更新
"""

import os
import pandas as pd
from typing import Optional, Dict, Any, List, Tuple
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
    """Excel檔案生成工具 - 修改版本"""

    def __init__(self):
        """初始化Excel生成器"""
        if not EXCEL_AVAILABLE:
            print("⚠️ 警告：缺少Excel處理依賴套件 (pandas, openpyxl)")

    def create_case_info_excel(self, case_info_folder: str, case_data: CaseData) -> tuple[bool, str]:
        """
        🔥 修改：建立案件資訊Excel檔案（使用新格式命名）

        Args:
            case_info_folder: 案件資訊資料夾路徑
            case_data: 案件資料

        Returns:
            (success, file_path_or_error_message)
        """
        if not EXCEL_AVAILABLE:
            return False, "缺少Excel處理依賴套件"

        try:
            # 🔥 修改：產生新格式的檔案名稱
            excel_filename = self._generate_new_format_excel_filename(case_data)
            excel_path = os.path.join(case_info_folder, excel_filename)

            # 建立Excel檔案
            success = self._create_excel_with_sheets(excel_path, case_data)

            if success:
                print(f"✅ 建立案件資訊Excel: {excel_filename}")
                return True, excel_path
            else:
                return False, "Excel檔案建立失敗"

        except Exception as e:
            error_msg = f"建立案件資訊Excel失敗: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg

    def update_case_info_excel_after_case_id_change(self, case_folder_path: str,
                                                   old_case_data: CaseData,
                                                   new_case_data: CaseData) -> tuple[bool, str]:
        """
        🔥 新增：案件編號更改後更新Excel檔案

        Args:
            case_folder_path: 案件資料夾路徑
            old_case_data: 舊的案件資料
            new_case_data: 新的案件資料

        Returns:
            (success, message)
        """
        if not EXCEL_AVAILABLE:
            return False, "缺少Excel處理依賴套件"

        try:
            case_info_folder = os.path.join(case_folder_path, '案件資訊')
            if not os.path.exists(case_info_folder):
                return False, f"找不到案件資訊資料夾: {case_info_folder}"

            # 尋找舊的Excel檔案
            old_excel_file = self._find_excel_by_case_data(case_info_folder, old_case_data)

            # 產生新的檔案名稱
            new_excel_filename = self._generate_new_format_excel_filename(new_case_data)
            new_excel_path = os.path.join(case_info_folder, new_excel_filename)

            if old_excel_file and os.path.exists(old_excel_file):
                # 重新命名舊檔案
                try:
                    os.rename(old_excel_file, new_excel_path)
                    print(f"📁 重新命名Excel檔案: {os.path.basename(old_excel_file)} -> {new_excel_filename}")
                except Exception as e:
                    print(f"⚠️ 重新命名失敗，建立新檔案: {e}")
                    # 如果重新命名失敗，建立新檔案
                    success, message = self.create_case_info_excel(case_info_folder, new_case_data)
                    return success, f"建立新Excel檔案: {message}"
            else:
                # 建立新檔案
                success, message = self.create_case_info_excel(case_info_folder, new_case_data)
                return success, f"建立新Excel檔案: {message}"

            # 更新Excel內容
            success = self._update_excel_content(new_excel_path, new_case_data)
            if success:
                return True, f"成功更新Excel檔案: {new_excel_filename}"
            else:
                return False, "更新Excel內容失敗"

        except Exception as e:
            error_msg = f"案件編號更改後更新Excel失敗: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg

    def update_case_info_excel(self, case_folder_path: str, case_data: CaseData) -> tuple[bool, str]:
        """
        🔥 修改：更新案件資訊Excel檔案（支援新舊格式查找）

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

            # 🔥 修改：使用智能查找Excel檔案
            existing_excel = self._find_excel_with_patterns(case_info_folder, case_data)

            if existing_excel:
                # 檢查檔案名稱是否需要更新
                expected_filename = self._generate_new_format_excel_filename(case_data)
                current_filename = os.path.basename(existing_excel)

                if current_filename != expected_filename:
                    # 需要重新命名檔案
                    new_excel_path = os.path.join(case_info_folder, expected_filename)
                    try:
                        os.rename(existing_excel, new_excel_path)
                        existing_excel = new_excel_path
                        print(f"📁 重新命名Excel檔案: {current_filename} -> {expected_filename}")
                    except Exception as e:
                        print(f"⚠️ 重新命名Excel檔案失敗: {e}")

                # 更新檔案內容
                success = self._update_excel_content(existing_excel, case_data)
                message = f"更新Excel檔案: {os.path.basename(existing_excel)}"
            else:
                # 建立新檔案
                success, result = self.create_case_info_excel(case_info_folder, case_data)
                message = f"建立新Excel檔案: {os.path.basename(result) if success else result}"

            return success, message

        except Exception as e:
            error_msg = f"更新案件資訊Excel失敗: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg

    def _generate_new_format_excel_filename(self, case_data: CaseData) -> str:
        """
        🔥 新增：產生新格式的Excel檔案名稱（案件編號_當事人_案件資訊.xlsx）

        Args:
            case_data: 案件資料

        Returns:
            Excel檔案名稱
        """
        try:
            # 清理案件編號和當事人名稱
            safe_case_id = self._sanitize_filename(case_data.case_id)
            safe_client_name = self._sanitize_filename(case_data.client)

            # 組合檔案名稱：案件編號_當事人_案件資訊.xlsx
            filename = f"{safe_case_id}_{safe_client_name}_案件資訊.xlsx"

            # 確保檔案名不會過長
            if len(filename) > 100:
                # 縮短當事人名稱部分
                max_client_length = 100 - len(safe_case_id) - len("__案件資訊.xlsx")
                if max_client_length > 5:
                    safe_client_name = safe_client_name[:max_client_length]
                    filename = f"{safe_case_id}_{safe_client_name}_案件資訊.xlsx"
                else:
                    # 如果還是太長，直接截斷
                    filename = filename[:100]

            return filename

        except Exception as e:
            print(f"❌ 產生Excel檔案名稱失敗: {e}")
            # 降級處理
            return f"{case_data.case_id}_案件資訊.xlsx"

    def _find_excel_with_patterns(self, case_info_folder: str, case_data: CaseData) -> Optional[str]:
        """
        🔥 新增：使用多種模式查找Excel檔案

        Args:
            case_info_folder: 案件資訊資料夾路徑
            case_data: 案件資料

        Returns:
            找到的Excel檔案路徑或None
        """
        try:
            if not os.path.exists(case_info_folder):
                return None

            # 策略1：查找新格式檔案名
            new_format_filename = self._generate_new_format_excel_filename(case_data)
            new_format_path = os.path.join(case_info_folder, new_format_filename)
            if os.path.exists(new_format_path):
                return new_format_path

            # 策略2：查找包含案件編號的Excel檔案
            for filename in os.listdir(case_info_folder):
                if (filename.endswith('.xlsx') and
                    case_data.case_id in filename and
                    '案件資訊' in filename):
                    return os.path.join(case_info_folder, filename)

            # 策略3：查找包含當事人名稱的Excel檔案
            safe_client_name = self._sanitize_filename(case_data.client)
            for filename in os.listdir(case_info_folder):
                if (filename.endswith('.xlsx') and
                    safe_client_name in filename and
                    '案件資訊' in filename):
                    return os.path.join(case_info_folder, filename)

            # 策略4：查找任何案件資訊Excel檔案
            for filename in os.listdir(case_info_folder):
                if filename.endswith('.xlsx') and '案件資訊' in filename:
                    return os.path.join(case_info_folder, filename)

            return None

        except Exception as e:
            print(f"❌ 查找Excel檔案失敗: {e}")
            return None

    def _find_excel_by_case_data(self, case_info_folder: str, case_data: CaseData) -> Optional[str]:
        """
        🔥 新增：根據案件資料查找對應的Excel檔案

        Args:
            case_info_folder: 案件資訊資料夾路徑
            case_data: 案件資料

        Returns:
            找到的Excel檔案路徑或None
        """
        return self._find_excel_with_patterns(case_info_folder, case_data)

    def _create_excel_with_sheets(self, excel_path: str, case_data: CaseData) -> bool:
        """
        🔥 修改：建立包含所有工作表的Excel檔案

        Args:
            excel_path: Excel檔案路徑
            case_data: 案件資料

        Returns:
            建立是否成功
        """
        try:
            with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
                # 基本資訊工作表
                basic_info = self._prepare_basic_info_data(case_data)
                df_basic = pd.DataFrame(basic_info, columns=['項目', '內容'])
                df_basic.to_excel(writer, sheet_name='基本資訊', index=False)

                # 詳細資訊工作表
                detail_info = self._prepare_detail_info_data(case_data)
                df_detail = pd.DataFrame(detail_info, columns=['項目', '內容'])
                df_detail.to_excel(writer, sheet_name='詳細資訊', index=False)

                # 進度階段工作表（如果有進度階段）
                if case_data.progress_stages:
                    progress_info = self._prepare_progress_info_data(case_data)
                    if progress_info:
                        df_progress = pd.DataFrame(progress_info, columns=['進度階段', '日期', '時間', '備註'])
                        df_progress.to_excel(writer, sheet_name='進度階段', index=False)

                # 調整欄位寬度和格式
                self._apply_excel_formatting(writer)

            return True

        except Exception as e:
            print(f"❌ 建立Excel工作表失敗: {e}")
            return False

    def _update_excel_content(self, excel_path: str, case_data: CaseData) -> bool:
        """
        🔥 新增：更新Excel檔案內容

        Args:
            excel_path: Excel檔案路徑
            case_data: 新的案件資料

        Returns:
            更新是否成功
        """
        try:
            # 重新建立Excel檔案以確保內容完全更新
            return self._create_excel_with_sheets(excel_path, case_data)

        except Exception as e:
            print(f"❌ 更新Excel內容失敗: {e}")
            return False

    def _prepare_basic_info_data(self, case_data: CaseData) -> List[List[str]]:
        """準備基本資訊資料"""
        return [
            ['案件編號', case_data.case_id],  # 🔥 確保使用最新的案件編號
            ['案件類型', case_data.case_type],
            ['當事人', case_data.client],
            ['委任律師', getattr(case_data, 'lawyer', '') or ''],
            ['法務', getattr(case_data, 'legal_affairs', '') or ''],
            ['目前進度', case_data.progress],
            ['進度日期', case_data.progress_date or ''],
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
        """準備進度階段資料"""
        try:
            progress_info = []

            # 按日期排序進度階段
            sorted_stages = sorted(case_data.progress_stages.items(), key=lambda x: x[1] or '')

            for stage_name, stage_date in sorted_stages:
                # 取得備註
                note = ""
                if hasattr(case_data, 'progress_notes') and case_data.progress_notes:
                    note = case_data.progress_notes.get(stage_name, "")

                # 取得時間
                time = ""
                if hasattr(case_data, 'progress_times') and case_data.progress_times:
                    time = case_data.progress_times.get(stage_name, "")

                progress_info.append([stage_name, stage_date or '', time, note])

            return progress_info

        except Exception as e:
            print(f"❌ 準備進度資料失敗: {e}")
            return []

    def _apply_excel_formatting(self, writer):
        """應用Excel格式設定"""
        try:
            for sheet_name in writer.sheets:
                worksheet = writer.sheets[sheet_name]

                # 調整欄位寬度
                worksheet.column_dimensions['A'].width = 15
                worksheet.column_dimensions['B'].width = 30

                # 如果是進度階段工作表，調整額外欄位
                if sheet_name == '進度階段':
                    worksheet.column_dimensions['C'].width = 15  # 時間欄位
                    worksheet.column_dimensions['D'].width = 40  # 備註欄位

                # 設定標題列格式
                for cell in worksheet[1]:
                    cell.font = cell.font.copy(bold=True)

        except Exception as e:
            print(f"⚠️ 應用Excel格式失敗: {e}")

    def _sanitize_filename(self, name: str) -> str:
        """
        清理檔案名稱中的無效字元

        Args:
            name: 原始名稱

        Returns:
            清理後的安全名稱
        """
        try:
            if not name:
                return "未知"

            # 移除檔案名不允許的字元
            invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
            clean_name = str(name)

            for char in invalid_chars:
                clean_name = clean_name.replace(char, '_')

            # 移除前後空格和點
            clean_name = clean_name.strip(' .')

            # 限制長度
            if len(clean_name) > 50:
                clean_name = clean_name[:50]

            # 確保不為空
            if not clean_name:
                clean_name = "未知"

            return clean_name

        except Exception as e:
            print(f"❌ 清理檔案名稱失敗: {e}")
            return "未知"