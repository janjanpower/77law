#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Excel服務 - 服務層
統一所有Excel相關的業務邏輯
整合現有的 ExcelHandler, SmartExcelAnalyzer
"""

import os
from typing import Dict, List, Optional, Tuple, Any
from models.case_model import CaseData

# 安全的依賴導入
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

try:
    import openpyxl
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False

try:
    import xlrd
    XLRD_AVAILABLE = True
except ImportError:
    XLRD_AVAILABLE = False

# 導入現有工具
try:
    from utils.smart_excel_analyzer import SmartExcelAnalyzer
    SMART_ANALYZER_AVAILABLE = True
except ImportError:
    SMART_ANALYZER_AVAILABLE = False

try:
    from utils.data_cleaner import DataCleaner
    DATA_CLEANER_AVAILABLE = True
except ImportError:
    DATA_CLEANER_AVAILABLE = False


class ExcelService:
    """Excel服務 - 統一Excel處理業務邏輯"""

    def __init__(self):
        """初始化Excel服務"""
        self._check_dependencies()

        # 初始化智慧分析器
        self.smart_analyzer = None
        if SMART_ANALYZER_AVAILABLE:
            try:
                self.smart_analyzer = SmartExcelAnalyzer()
                print("✅ 智慧Excel分析器已載入")
            except Exception as e:
                print(f"⚠️ 智慧分析器初始化失敗: {e}")

    def _check_dependencies(self) -> None:
        """檢查依賴"""
        if not PANDAS_AVAILABLE:
            print("⚠️ pandas 不可用，Excel功能將受限")

    # ====== Excel檔案分析 ======

    def analyze_excel_file(self, file_path: str) -> Tuple[bool, str, Dict[str, Any]]:
        """
        分析Excel檔案結構

        Args:
            file_path: Excel檔案路徑

        Returns:
            (success, message, analysis_result)
        """
        try:
            if not os.path.exists(file_path):
                return False, f"檔案不存在: {file_path}", {}

            if not PANDAS_AVAILABLE:
                return False, "pandas 不可用，無法分析Excel檔案", {}

            # 使用智慧分析器如果可用
            if self.smart_analyzer:
                return self._smart_analyze_file(file_path)
            else:
                return self._basic_analyze_file(file_path)

        except Exception as e:
            error_msg = f"分析Excel檔案失敗: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg, {}

    def _smart_analyze_file(self, file_path: str) -> Tuple[bool, str, Dict[str, Any]]:
        """使用智慧分析器分析檔案"""
        try:
            # 呼叫智慧分析器
            analysis_result = self.smart_analyzer.analyze_excel_file(file_path)

            if analysis_result['success']:
                return True, "檔案分析完成", analysis_result
            else:
                return False, analysis_result.get('message', '分析失敗'), analysis_result

        except Exception as e:
            return False, f"智慧分析失敗: {str(e)}", {}

    def _basic_analyze_file(self, file_path: str) -> Tuple[bool, str, Dict[str, Any]]:
        """基本檔案分析"""
        try:
            # 讀取所有工作表名稱
            excel_file = pd.ExcelFile(file_path)
            sheet_names = excel_file.sheet_names

            analysis_result = {
                'success': True,
                'file_path': file_path,
                'sheet_count': len(sheet_names),
                'sheet_names': sheet_names,
                'sheets_analysis': {}
            }

            # 分析每個工作表
            for sheet_name in sheet_names:
                sheet_analysis = self._analyze_sheet(file_path, sheet_name)
                analysis_result['sheets_analysis'][sheet_name] = sheet_analysis

            return True, f"成功分析 {len(sheet_names)} 個工作表", analysis_result

        except Exception as e:
            return False, f"基本分析失敗: {str(e)}", {}

    def _analyze_sheet(self, file_path: str, sheet_name: str) -> Dict[str, Any]:
        """分析單個工作表"""
        try:
            df = pd.read_excel(file_path, sheet_name=sheet_name, nrows=10)

            return {
                'row_count': len(df),
                'column_count': len(df.columns),
                'columns': df.columns.tolist(),
                'has_data': not df.empty,
                'preview_data': df.head(5).to_dict('records') if not df.empty else []
            }

        except Exception as e:
            return {
                'error': str(e),
                'has_data': False,
                'row_count': 0,
                'column_count': 0
            }

    # ====== Excel資料匯入 ======

    def import_cases_from_excel(self, file_path: str, sheet_name: str = None) -> Tuple[bool, str, List[CaseData]]:
        """
        從Excel匯入案件資料

        Args:
            file_path: Excel檔案路徑
            sheet_name: 工作表名稱，None為自動選擇

        Returns:
            (success, message, cases_list)
        """
        try:
            if not os.path.exists(file_path):
                return False, f"檔案不存在: {file_path}", []

            # 使用智慧分析器匯入如果可用
            if self.smart_analyzer:
                return self._smart_import_cases(file_path, sheet_name)
            else:
                return self._basic_import_cases(file_path, sheet_name)

        except Exception as e:
            error_msg = f"匯入案件失敗: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg, []

    def _smart_import_cases(self, file_path: str, sheet_name: str) -> Tuple[bool, str, List[CaseData]]:
        """使用智慧分析器匯入案件"""
        try:
            # 先分析檔案
            success, message, analysis = self._smart_analyze_file(file_path)
            if not success:
                return False, f"檔案分析失敗: {message}", []

            # 提取案件資料
            extracted_data = self.smart_analyzer.extract_case_data_from_analysis(analysis, sheet_name)

            if not extracted_data['success']:
                return False, extracted_data.get('message', '資料提取失敗'), []

            cases = extracted_data.get('cases', [])
            message = f"成功匯入 {len(cases)} 筆案件資料"

            return True, message, cases

        except Exception as e:
            return False, f"智慧匯入失敗: {str(e)}", []

    def _basic_import_cases(self, file_path: str, sheet_name: str) -> Tuple[bool, str, List[CaseData]]:
        """基本案件匯入"""
        try:
            # 如果未指定工作表，選擇第一個
            if not sheet_name:
                excel_file = pd.ExcelFile(file_path)
                sheet_name = excel_file.sheet_names[0]

            # 讀取資料
            df = pd.read_excel(file_path, sheet_name=sheet_name)

            if df.empty:
                return False, "工作表沒有資料", []

            # 基本欄位對應
            column_mapping = self._create_basic_column_mapping(df.columns)

            # 轉換為CaseData
            cases = self._convert_dataframe_to_cases(df, column_mapping)

            message = f"成功匯入 {len(cases)} 筆案件資料"
            return True, message, cases

        except Exception as e:
            return False, f"基本匯入失敗: {str(e)}", []

    def _create_basic_column_mapping(self, columns: List[str]) -> Dict[str, str]:
        """建立基本欄位對應"""
        mapping = {}

        # 簡單的關鍵字對應
        field_keywords = {
            'client': ['當事人', '客戶', '姓名', '委託人'],
            'case_type': ['案件類型', '類型', '案由'],
            'case_reason': ['案由', '事由', '原因'],
            'case_number': ['案號', '機關', '案件號'],
            'court': ['法院', '管轄法院'],
            'lawyer': ['律師', '委任律師'],
            'legal_affairs': ['法務', '承辦人'],
            'opposing_party': ['對造', '相對人', '被告']
        }

        for field, keywords in field_keywords.items():
            for col in columns:
                if any(keyword in str(col) for keyword in keywords):
                    mapping[field] = col
                    break

        return mapping

    def _convert_dataframe_to_cases(self, df: pd.DataFrame, column_mapping: Dict[str, str]) -> List[CaseData]:
        """將DataFrame轉換為CaseData列表"""
        cases = []

        for index, row in df.iterrows():
            try:
                # 建立CaseData物件
                case_data = CaseData(
                    case_id=self._get_field_value(row, column_mapping, 'case_id', f"CASE_{index+1:04d}"),
                    client=self._get_field_value(row, column_mapping, 'client', ''),
                    case_type=self._get_field_value(row, column_mapping, 'case_type', '刑事'),
                    case_reason=self._get_field_value(row, column_mapping, 'case_reason', ''),
                    case_number=self._get_field_value(row, column_mapping, 'case_number', ''),
                    court=self._get_field_value(row, column_mapping, 'court', ''),
                    lawyer=self._get_field_value(row, column_mapping, 'lawyer', ''),
                    legal_affairs=self._get_field_value(row, column_mapping, 'legal_affairs', ''),
                    opposing_party=self._get_field_value(row, column_mapping, 'opposing_party', ''),
                    division=''  # 預設值
                )

                # 只有當事人不為空才加入
                if case_data.client and case_data.client.strip():
                    cases.append(case_data)

            except Exception as e:
                print(f"⚠️ 第 {index+1} 列資料轉換失敗: {e}")
                continue

        return cases

    def _get_field_value(self, row: pd.Series, mapping: Dict[str, str], field: str, default: str = '') -> str:
        """從行資料中取得欄位值"""
        try:
            if field in mapping and mapping[field] in row:
                value = row[mapping[field]]
                if pd.notna(value):
                    return str(value).strip()
            return default
        except Exception:
            return default

    # ====== Excel資料匯出 ======

    def export_cases_to_excel(self, cases: List[CaseData], file_path: str) -> Tuple[bool, str]:
        """
        匯出案件資料到Excel

        Args:
            cases: 案件資料列表
            file_path: 匯出檔案路徑

        Returns:
            (success, message)
        """
        try:
            if not cases:
                return False, "沒有資料可匯出"

            if not PANDAS_AVAILABLE:
                return False, "pandas 不可用，無法匯出Excel"

            # 轉換為DataFrame
            df = self._convert_cases_to_dataframe(cases)

            # 匯出到Excel
            df.to_excel(file_path, index=False, engine='openpyxl' if OPENPYXL_AVAILABLE else None)

            message = f"成功匯出 {len(cases)} 筆案件資料到 {file_path}"
            print(f"✅ {message}")
            return True, message

        except Exception as e:
            error_msg = f"匯出案件失敗: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg

    def _convert_cases_to_dataframe(self, cases: List[CaseData]) -> pd.DataFrame:
        """將CaseData列表轉換為DataFrame"""
        data = []

        for case in cases:
            row = {
                '案件編號': case.case_id,
                '當事人': case.client,
                '案件類型': case.case_type,
                '案由': case.case_reason,
                '案號': case.case_number,
                '法院': case.court,
                '委任律師': case.lawyer,
                '法務': case.legal_affairs,
                '對造': case.opposing_party,
                '庭別': case.division,
                '進度': case.progress,
                '進度日期': case.progress_date.strftime('%Y-%m-%d') if case.progress_date else '',
                '建立日期': case.created_date.strftime('%Y-%m-%d') if case.created_date else ''
            }
            data.append(row)

        return pd.DataFrame(data)

    # ====== 案件資訊Excel建立 ======

    def create_case_info_excel(self, folder_path: str, case_data: CaseData) -> Tuple[bool, str]:
        """
        建立案件資訊Excel檔案

        Args:
            folder_path: 資料夾路徑
            case_data: 案件資料

        Returns:
            (success, message)
        """
        try:
            if not PANDAS_AVAILABLE:
                return False, "pandas 不可用，無法建立Excel檔案"

            # 準備案件資訊資料
            case_info_data = self._prepare_case_info_data(case_data)

            # 建立Excel檔案
            excel_file_path = os.path.join(folder_path, f"{case_data.client}_案件資訊.xlsx")

            with pd.ExcelWriter(excel_file_path, engine='openpyxl' if OPENPYXL_AVAILABLE else None) as writer:
                # 基本資訊工作表
                basic_info_df = pd.DataFrame(case_info_data['basic_info'])
                basic_info_df.to_excel(writer, sheet_name='基本資訊', index=False)

                # 進度追蹤工作表
                progress_df = pd.DataFrame(case_info_data['progress_tracking'])
                progress_df.to_excel(writer, sheet_name='進度追蹤', index=False)

                # 重要日期工作表
                dates_df = pd.DataFrame(case_info_data['important_dates'])
                dates_df.to_excel(writer, sheet_name='重要日期', index=False)

            message = f"成功建立案件資訊Excel: {excel_file_path}"
            print(f"✅ {message}")
            return True, message

        except Exception as e:
            error_msg = f"建立案件資訊Excel失敗: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg

    def _prepare_case_info_data(self, case_data: CaseData) -> Dict[str, List[Dict]]:
        """準備案件資訊資料"""
        return {
            'basic_info': [
                {'項目': '案件編號', '內容': case_data.case_id},
                {'項目': '當事人', '內容': case_data.client},
                {'項目': '案件類型', '內容': case_data.case_type},
                {'項目': '案由', '內容': case_data.case_reason or ''},
                {'項目': '案號', '內容': case_data.case_number or ''},
                {'項目': '法院', '內容': case_data.court or ''},
                {'項目': '委任律師', '內容': case_data.lawyer or ''},
                {'項目': '法務', '內容': case_data.legal_affairs or ''},
                {'項目': '對造', '內容': case_data.opposing_party or ''},
                {'項目': '庭別', '內容': case_data.division or ''},
                {'項目': '建立日期', '內容': case_data.created_date.strftime('%Y-%m-%d') if case_data.created_date else ''}
            ],
            'progress_tracking': [
                {'階段': case_data.progress or '待處理', '日期': case_data.progress_date.strftime('%Y-%m-%d') if case_data.progress_date else '', '備註': ''}
            ],
            'important_dates': [
                {'日期類型': '建立日期', '日期': case_data.created_date.strftime('%Y-%m-%d') if case_data.created_date else '', '備註': '案件建立'}
            ]
        }

    # ====== 工具方法 ======

    @staticmethod
    def get_dependency_status() -> Dict[str, bool]:
        """取得依賴狀態"""
        return {
            'pandas': PANDAS_AVAILABLE,
            'openpyxl': OPENPYXL_AVAILABLE,
            'xlrd': XLRD_AVAILABLE,
            'smart_analyzer': SMART_ANALYZER_AVAILABLE,
            'data_cleaner': DATA_CLEANER_AVAILABLE
        }

    def validate_excel_file(self, file_path: str) -> Tuple[bool, str]:
        """
        驗證Excel檔案

        Args:
            file_path: Excel檔案路徑

        Returns:
            (is_valid, message)
        """
        try:
            if not os.path.exists(file_path):
                return False, "檔案不存在"

            if not file_path.lower().endswith(('.xlsx', '.xls')):
                return False, "不是有效的Excel檔案格式"

            if not PANDAS_AVAILABLE:
                return False, "pandas 不可用，無法驗證檔案"

            # 嘗試讀取檔案
            excel_file = pd.ExcelFile(file_path)
            if not excel_file.sheet_names:
                return False, "檔案沒有工作表"

            # 檢查檔案大小（限制為50MB）
            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
            if file_size_mb > 50:
                return False, f"檔案過大: {file_size_mb:.2f}MB，限制50MB"

            return True, "檔案驗證通過"

        except Exception as e:
            return False, f"檔案驗證失敗: {str(e)}"

    def get_excel_preview(self, file_path: str, sheet_name: str = None, max_rows: int = 10) -> Tuple[bool, str, Dict[str, Any]]:
        """
        取得Excel檔案預覽

        Args:
            file_path: Excel檔案路徑
            sheet_name: 工作表名稱，None為第一個工作表
            max_rows: 最大預覽行數

        Returns:
            (success, message, preview_data)
        """
        try:
            if not os.path.exists(file_path):
                return False, "檔案不存在", {}

            if not PANDAS_AVAILABLE:
                return False, "pandas 不可用", {}

            # 選擇工作表
            excel_file = pd.ExcelFile(file_path)
            if not sheet_name:
                sheet_name = excel_file.sheet_names[0]

            if sheet_name not in excel_file.sheet_names:
                return False, f"工作表 '{sheet_name}' 不存在", {}

            # 讀取預覽資料
            df = pd.read_excel(file_path, sheet_name=sheet_name, nrows=max_rows)

            preview_data = {
                'sheet_name': sheet_name,
                'total_sheets': len(excel_file.sheet_names),
                'sheet_names': excel_file.sheet_names,
                'row_count': len(df),
                'column_count': len(df.columns),
                'columns': df.columns.tolist(),
                'preview_data': df.to_dict('records'),
                'has_data': not df.empty
            }

            return True, "預覽載入成功", preview_data

        except Exception as e:
            error_msg = f"載入預覽失敗: {str(e)}"
            return False, error_msg, {}