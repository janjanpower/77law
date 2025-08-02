#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Excel處理統一介面 - 整合所有Excel功能模組
提供向後相容的介面，內部使用重構後的專門模組
"""

import os
from typing import Dict, List, Optional, Tuple, Any

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

from models.case_model import CaseData
from utils.data_cleaner import DataCleaner

# 導入重構後的模組
from .excel_reader import ExcelReader
from .excel_writer import ExcelWriter
from .excel_analyzer import ExcelAnalyzer
from .excel_validator import ExcelValidator
from .exceptions import (
    ExcelFileNotFoundError,
    ExcelEngineNotAvailableError,
    ExcelDependencyError,
    ExcelDataValidationError
)


class EnhancedExcelHandler:
    """增強版Excel處理類別 - 整合所有功能模組"""

    def __init__(self):
        """初始化處理器"""
        self._check_dependencies()

        # 初始化各個專門模組
        self.reader = ExcelReader()
        self.writer = ExcelWriter()
        self.analyzer = ExcelAnalyzer()
        self.validator = ExcelValidator()

        # 智慧分析器整合
        self.smart_analysis_available = False
        self.smart_analyzer = None
        self._last_analysis_result = None

        try:
            # 嘗試導入智慧分析器
            from utils.smart_excel_analyzer import SmartExcelAnalyzer
            self.smart_analyzer = SmartExcelAnalyzer()
            self.smart_analysis_available = True
            print("✅ 智慧分析器已載入")
        except ImportError as e:
            print(f"⚠️ 智慧分析器不可用，使用基本分析模式: {e}")
            self.smart_analysis_available = False

    def _check_dependencies(self) -> None:
        """檢查依賴"""
        if not PANDAS_AVAILABLE:
            raise ExcelDependencyError("pandas 不可用，Excel 功能將受限")

    @staticmethod
    def check_dependencies() -> Dict[str, bool]:
        """檢查Excel處理相關依賴"""
        return {
            'pandas': PANDAS_AVAILABLE,
            'openpyxl': OPENPYXL_AVAILABLE,
            'xlrd': XLRD_AVAILABLE
        }

    def analyze_excel_sheets(self, file_path: str) -> Tuple[bool, str, Dict[str, List[str]]]:
        """
        智慧分析Excel檔案中的工作表

        Args:
            file_path: Excel檔案路徑

        Returns:
            Tuple[bool, str, Dict]: (成功狀態, 分析結果訊息, 分類結果)
        """
        try:
            print(f"🔍 分析Excel檔案: {file_path}")

            # 優先使用智慧分析器
            if self.smart_analysis_available and self.smart_analyzer:
                print("🧠 使用智慧分析模式...")
                success, analysis_report, analysis_result = self.smart_analyzer.analyze_excel_comprehensive(file_path)

                if success:
                    # 轉換為向後相容格式
                    categorized_sheets = analysis_result.get('categorized_sheets', {})
                    self._last_analysis_result = analysis_result
                    print("✅ 智慧分析完成")
                    return True, analysis_report, categorized_sheets
                else:
                    print("⚠️ 智慧分析失敗，回退到基本分析")

            # 使用重構後的分析器
            print("📋 使用重構分析模式...")
            success, analysis_report, analysis_result = self.analyzer.analyze_excel_comprehensive(file_path)

            if success:
                categorized_sheets = analysis_result.get('categorized_sheets', {})
                self._last_analysis_result = analysis_result
                return True, analysis_report, categorized_sheets
            else:
                return False, analysis_report, {}

        except Exception as e:
            error_msg = f"分析Excel檔案失敗：{str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg, {}

    def import_cases_by_category(self, file_path: str) -> Tuple[bool, str, Dict[str, List[CaseData]]]:
        """
        根據分類匯入案件資料

        Args:
            file_path: Excel檔案路徑

        Returns:
            Tuple[bool, str, Dict]: (成功狀態, 結果訊息, 分類案件資料)
        """
        try:
            print(f"🚀 開始匯入案件資料: {file_path}")

            # 優先使用智慧分析器提取資料（如果可用且已分析）
            if (self.smart_analysis_available and
                self.smart_analyzer and
                self._last_analysis_result):

                print("🧠 使用智慧匯入模式...")
                return self.smart_analyzer.extract_data_from_analysis(
                    file_path, self._last_analysis_result
                )

            # 使用重構後的分析器提取資料
            if self._last_analysis_result:
                print("📋 使用重構匯入模式...")
                return self.analyzer.extract_cases_from_analysis(
                    file_path, self._last_analysis_result
                )

            # 如果沒有分析結果，先進行分析
            print("📊 先進行檔案分析...")
            success, message, _ = self.analyze_excel_sheets(file_path)
            if not success:
                return False, message, {'民事': [], '刑事': [], '行政': [], '家事': []}

            # 再次嘗試提取
            return self.analyzer.extract_cases_from_analysis(
                file_path, self._last_analysis_result
            )

        except Exception as e:
            error_msg = f"匯入過程發生錯誤：{str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg, {'民事': [], '刑事': [], '行政': [], '家事': []}

    def export_cases_to_excel(self, cases: List[CaseData], file_path: str) -> bool:
        """將案件資料匯出為Excel檔案"""
        try:
            return self.writer.export_cases_to_excel(cases, file_path)
        except Exception as e:
            print(f"❌ 匯出Excel失敗: {e}")
            return False

    def export_cases_by_type(self, cases: List[CaseData], file_path: str) -> bool:
        """將案件資料按類型分工作表匯出"""
        try:
            return self.writer.export_cases_by_type(cases, file_path)
        except Exception as e:
            print(f"❌ 分類匯出Excel失敗: {e}")
            return False

    def import_cases_from_excel(self, file_path: str) -> Optional[List[CaseData]]:
        """
        從Excel檔案匯入案件資料（向後相容方法）
        """
        try:
            # 讀取第一個工作表
            df = self.reader.read_sheet_data(file_path)
            if df is None or df.empty:
                return None

            # 建立基本欄位對應
            column_mapping = self._create_basic_column_mapping(df.columns.tolist())

            # 驗證欄位對應
            validation_result = self.validator.validate_field_mapping(df.columns.tolist(), column_mapping)
            if not validation_result.is_valid:
                print(f"❌ 欄位對應驗證失敗: {', '.join(validation_result.errors)}")
                return None

            cases = []
            for _, row in df.iterrows():
                try:
                    # 提取並清理資料
                    raw_case_data = {
                        'case_id': self._safe_get_value(row, column_mapping.get('case_id')),
                        'case_type': self._safe_get_value(row, column_mapping.get('case_type')) or '未知',
                        'client': self._safe_get_value(row, column_mapping.get('client')),
                        'lawyer': self._safe_get_value(row, column_mapping.get('lawyer')),
                        'legal_affairs': self._safe_get_value(row, column_mapping.get('legal_affairs')),
                        'progress': self._safe_get_value(row, column_mapping.get('progress')) or '待處理',
                        'case_reason': self._safe_get_value(row, column_mapping.get('case_reason')),
                        'case_number': self._safe_get_value(row, column_mapping.get('case_number')),
                        'opposing_party': self._safe_get_value(row, column_mapping.get('opposing_party')),
                        'court': self._safe_get_value(row, column_mapping.get('court')),
                        'division': self._safe_get_value(row, column_mapping.get('division'))
                    }

                    # 驗證案件資料
                    case_validation = self.validator.validate_case_data(raw_case_data)
                    if not case_validation.is_valid:
                        continue

                    # 使用驗證後的清理資料
                    cleaned_data = case_validation.validated_data or raw_case_data

                    # 建立CaseData物件
                    case = CaseData(**cleaned_data)
                    cases.append(case)

                except Exception as e:
                    print(f"處理資料時發生錯誤: {e}")
                    continue

            print(f"✅ 成功匯入 {len(cases)} 筆案件")
            return cases

        except Exception as e:
            print(f"❌ 匯入Excel失敗: {e}")
            return None

    def validate_excel_data(
        self,
        file_path: str,
        sheet_name: Optional[str] = None,
        strict_mode: bool = False
    ) -> Dict[str, Any]:
        """
        驗證Excel資料品質

        Args:
            file_path: Excel檔案路徑
            sheet_name: 工作表名稱
            strict_mode: 是否使用嚴格模式

        Returns:
            驗證結果字典
        """
        try:
            # 讀取資料
            df = self.reader.read_sheet_data(file_path, sheet_name)
            if df is None or df.empty:
                return {
                    'is_valid': False,
                    'errors': ['檔案為空或無法讀取'],
                    'warnings': [],
                    'suggestions': [],
                    'quality_score': 0
                }

            # 建立欄位對應
            column_mapping = self._create_basic_column_mapping(df.columns.tolist())

            # 執行驗證
            validation_result = self.validator.validate_dataframe(df, column_mapping, strict_mode)

            # 計算品質分數
            quality_scores = self.validator.get_data_quality_score(df, column_mapping)

            return {
                'is_valid': validation_result.is_valid,
                'errors': validation_result.errors,
                'warnings': validation_result.warnings,
                'suggestions': validation_result.suggestions,
                'quality_score': quality_scores['overall_score'],
                'quality_details': quality_scores,
                'validated_data': validation_result.validated_data
            }

        except Exception as e:
            return {
                'is_valid': False,
                'errors': [f'驗證過程發生錯誤: {str(e)}'],
                'warnings': [],
                'suggestions': [],
                'quality_score': 0
            }

    def get_excel_preview(
        self,
        file_path: str,
        sheet_name: Optional[str] = None,
        max_rows: int = 5
    ) -> Dict[str, Any]:
        """
        取得Excel檔案預覽

        Args:
            file_path: Excel檔案路徑
            sheet_name: 工作表名稱
            max_rows: 預覽行數

        Returns:
            預覽資訊字典
        """
        try:
            # 取得檔案資訊
            file_info = self.reader.read_excel_file_info(file_path)

            # 取得工作表預覽
            preview_info = self.reader.get_sheet_preview(file_path, sheet_name, max_rows)

            return {
                'file_info': file_info,
                'preview': preview_info,
                'success': True
            }

        except Exception as e:
            return {
                'file_info': None,
                'preview': None,
                'success': False,
                'error': str(e)
            }

    def create_case_info_excel(self, case_data: CaseData, file_path: str) -> bool:
        """為單一案件建立詳細資訊Excel檔案"""
        try:
            return self.writer.create_case_info_excel(case_data, file_path)
        except Exception as e:
            print(f"❌ 建立案件資訊Excel失敗: {e}")
            return False

    def _create_basic_column_mapping(self, columns: List[str]) -> Dict[str, str]:
        """建立基本欄位對應關係（向後相容）"""
        mapping = {}

        # 欄位關鍵字對應
        field_keywords = {
            'client': ['當事人', '客戶', '委託人', '姓名'],
            'case_id': ['案件編號', '編號', 'ID', '序號'],
            'case_type': ['案件類型', '類型'],
            'case_reason': ['案由', '事由'],
            'case_number': ['案號', '機關', '案件號碼', '機關案號', '法院案號'],
            'court': ['法院', '負責法院', '管轄法院'],
            'opposing_party': ['對造'],
            'division': ['股別', '負責股別'],
            'lawyer': ['律師', '代理人', '委任律師'],
            'legal_affairs': ['法務', '法務人員'],
            'progress': ['進度', '狀態', '案件狀態']
        }

        for field, keywords in field_keywords.items():
            for col in columns:
                col_clean = str(col).strip()
                if any(keyword in col_clean for keyword in keywords):
                    if field not in mapping:  # 避免重複對應
                        mapping[field] = col
                        break

        return mapping

    def _safe_get_value(self, row, column_name: str) -> Optional[str]:
        """安全地取得欄位值並清理"""
        if not column_name:
            return None

        try:
            value = row.get(column_name, '')
            if pd.isna(value):
                return None

            cleaned_value = DataCleaner.clean_text_data(value)
            return cleaned_value

        except Exception:
            return None

    def get_dependency_status(self) -> str:
        """取得依賴狀態說明"""
        deps = self.check_dependencies()
        status_lines = ["📊 Excel 處理依賴狀態:"]

        for dep, available in deps.items():
            status = "✅" if available else "❌"
            status_lines.append(f"  {status} {dep}")

        if self.smart_analysis_available:
            status_lines.append("  ✅ 智慧分析器")
        else:
            status_lines.append("  ❌ 智慧分析器")

        if not deps['pandas']:
            status_lines.append("\n⚠️ 缺少 pandas，Excel 功能將無法使用")
            status_lines.append("請執行: pip install pandas openpyxl xlrd")

        return "\n".join(status_lines)

    # ==================== 向後相容的靜態方法 ====================

    @staticmethod
    def analyze_excel_sheets_static(file_path: str) -> Tuple[bool, str, Dict[str, List[str]]]:
        """靜態版本的分析方法，用於向後相容"""
        handler = EnhancedExcelHandler()
        return handler.analyze_excel_sheets(file_path)

    @staticmethod
    def import_cases_by_category_static(file_path: str) -> Tuple[bool, str, Dict[str, List[CaseData]]]:
        """靜態版本的匯入方法，用於向後相容"""
        handler = EnhancedExcelHandler()
        # 先分析再匯入
        handler.analyze_excel_sheets(file_path)
        return handler.import_cases_by_category(file_path)


# ==================== 向後相容的ExcelHandler類別 ====================

class ExcelHandler:
    """向後相容的ExcelHandler類別"""

    @staticmethod
    def analyze_excel_sheets(file_path: str) -> Tuple[bool, str, Dict[str, List[str]]]:
        """靜態方法：分析Excel工作表"""
        return EnhancedExcelHandler.analyze_excel_sheets_static(file_path)

    @staticmethod
    def import_cases_by_category(file_path: str) -> Tuple[bool, str, Dict[str, List[CaseData]]]:
        """靜態方法：分類匯入案件"""
        return EnhancedExcelHandler.import_cases_by_category_static(file_path)

    @staticmethod
    def export_cases_to_excel(cases: List[CaseData], file_path: str) -> bool:
        """靜態方法：匯出案件到Excel"""
        handler = EnhancedExcelHandler()
        return handler.export_cases_to_excel(cases, file_path)

    @staticmethod
    def import_cases_from_excel(file_path: str) -> Optional[List[CaseData]]:
        """靜態方法：從Excel匯入案件"""
        handler = EnhancedExcelHandler()
        return handler.import_cases_from_excel(file_path)

    @staticmethod
    def get_dependency_status() -> str:
        """靜態方法：取得依賴狀態"""
        handler = EnhancedExcelHandler()
        return handler.get_dependency_status()

    @staticmethod
    def validate_excel_data(file_path: str, sheet_name: Optional[str] = None) -> Dict[str, Any]:
        """靜態方法：驗證Excel資料"""
        handler = EnhancedExcelHandler()
        return handler.validate_excel_data(file_path, sheet_name)

    @staticmethod
    def get_excel_preview(file_path: str, sheet_name: Optional[str] = None) -> Dict[str, Any]:
        """靜態方法：取得Excel預覽"""
        handler = EnhancedExcelHandler()
        return handler.get_excel_preview(file_path, sheet_name)
