#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Excel處理器 - 檔案操作模組
提供統一的Excel處理功能
"""

import pandas as pd
import os
from typing import List, Dict, Optional, Tuple, Any

class ExcelHandler:
    """Excel處理器 - 統一的Excel操作介面"""

    def __init__(self):
        """初始化Excel處理器"""
        self.supported_engines = self._check_engines()

    def _check_engines(self) -> Dict[str, bool]:
        """檢查可用的Excel引擎"""
        engines = {}
        try:
            import openpyxl
            engines['openpyxl'] = True
        except ImportError:
            engines['openpyxl'] = False

        try:
            import xlsxwriter
            engines['xlsxwriter'] = True
        except ImportError:
            engines['xlsxwriter'] = False

        return engines

    def get_dependency_status(self) -> str:
        """取得依賴狀態報告"""
        status_lines = ["📦 Excel處理器依賴狀態:"]

        try:
            import pandas
            status_lines.append(f"  ✅ pandas: {pandas.__version__}")
        except ImportError:
            status_lines.append("  ❌ pandas: 未安裝")

        for engine, available in self.supported_engines.items():
            icon = "✅" if available else "❌"
            status_lines.append(f"  {icon} {engine}: {'可用' if available else '未安裝'}")

        return "\\n".join(status_lines)


    def read_excel(self, file_path: str, sheet_name: Optional[str] = None) -> pd.DataFrame:
        """讀取Excel檔案"""
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"檔案不存在: {file_path}")

            # 選擇最佳引擎
            engine = 'openpyxl' if self.supported_engines.get('openpyxl') else None

            if sheet_name:
                df = pd.read_excel(file_path, sheet_name=sheet_name, engine=engine)
            else:
                df = pd.read_excel(file_path, engine=engine)

            return df

        except Exception as e:
            print(f"讀取Excel檔案失敗: {e}")
            return pd.DataFrame()

    @staticmethod
    @staticmethod
    def analyze_excel_sheets(file_path: str) -> Tuple[bool, str, Dict[str, List[str]]]:
        """分析Excel工作表結構"""
        try:
            if not os.path.exists(file_path):
                return False, f"檔案不存在: {file_path}", {}

            excel_file = pd.ExcelFile(file_path)
            sheet_info = {}

            for sheet_name in excel_file.sheet_names:
                df = excel_file.parse(sheet_name, nrows=5)
                columns = df.columns.tolist()
                sheet_info[sheet_name] = columns

            return True, "分析完成", sheet_info

        except Exception as e:
            return False, f"分析失敗: {e}", {}

    @staticmethod
    def import_cases_from_excel(file_path: str) -> Optional[List[Dict]]:
        """從Excel匯入案件資料"""
        try:
            if not os.path.exists(file_path):
                return None

            df = pd.read_excel(file_path)
            if df.empty:
                return None

            cases = df.to_dict('records')
            cleaned_cases = []
            for case in cases:
                cleaned_case = {k: v for k, v in case.items() if pd.notna(v)}
                if cleaned_case:
                    cleaned_cases.append(cleaned_case)

            return cleaned_cases

        except Exception as e:
            print(f"匯入案件失敗: {e}")
            return None

    def export_cases_to_excel(self, cases: List[Dict], file_path: str) -> bool:
        """匯出案件到Excel"""
        try:
            if not cases:
                return False

            df = pd.DataFrame(cases)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            engine = 'openpyxl' if self.supported_engines.get('openpyxl') else 'xlsxwriter'
            df.to_excel(file_path, index=False, engine=engine)
            return True

        except Exception as e:
            print(f"匯出案件失敗: {e}")
            return False

    @staticmethod
    def validate_excel_data(file_path: str, sheet_name: Optional[str] = None) -> Tuple[bool, str, Dict]:
        """驗證Excel資料"""
        try:
            df = pd.read_excel(file_path, sheet_name=sheet_name)

            validation_result = {
                'row_count': len(df),
                'column_count': len(df.columns),
                'columns': df.columns.tolist(),
                'empty_rows': df.isnull().all(axis=1).sum(),
                'duplicate_rows': df.duplicated().sum(),
                'data_types': df.dtypes.to_dict()
            }

            return True, "驗證完成", validation_result

        except Exception as e:
            return False, f"驗證失敗: {e}", {}

    @staticmethod
    def get_excel_preview(file_path: str, sheet_name: Optional[str] = None, rows: int = 10) -> Tuple[bool, str, Dict]:
        """取得Excel預覽資料"""
        try:
            df = pd.read_excel(file_path, sheet_name=sheet_name, nrows=rows)

            preview_data = {
                'columns': df.columns.tolist(),
                'data': df.to_dict('records'),
                'total_rows_read': len(df),
                'sheet_name': sheet_name or 'Sheet1'
            }

            return True, "預覽完成", preview_data

        except Exception as e:
            return False, f"預覽失敗: {e}", {}

    @staticmethod
    def check_dependencies() -> Dict[str, bool]:
        """檢查依賴套件"""
        dependencies = {}

        try:
            import pandas
            dependencies['pandas'] = True
        except ImportError:
            dependencies['pandas'] = False

        try:
            import openpyxl
            dependencies['openpyxl'] = True
        except ImportError:
            dependencies['openpyxl'] = False

        try:
            import xlsxwriter
            dependencies['xlsxwriter'] = True
        except ImportError:
            dependencies['xlsxwriter'] = False

        return dependencies