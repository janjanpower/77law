#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Excel處理模組初始化
提供統一的Excel處理功能導入介面
"""

# 主要處理類別
from .excel_handler import ExcelHandler, EnhancedExcelHandler

# 專門功能模組
from .excel_reader import ExcelReader
from .excel_writer import ExcelWriter
from .excel_analyzer import ExcelAnalyzer
from .excel_validator import ExcelValidator

# 例外類別
from .exceptions import (
    ExcelBaseException,
    ExcelFileNotFoundError,
    ExcelEngineNotAvailableError,
    ExcelSheetNotFoundError,
    ExcelDataValidationError,
    ExcelColumnMappingError,
    ExcelWriteError,
    ExcelDependencyError
)

# 版本資訊
__version__ = "2.0.0"
__author__ = "專案團隊"

# 公開介面
__all__ = [
    # 主要處理類別
    'ExcelHandler',
    'EnhancedExcelHandler',

    # 專門功能模組
    'ExcelReader',
    'ExcelWriter',
    'ExcelAnalyzer',
    'ExcelValidator',

    # 例外類別
    'ExcelBaseException',
    'ExcelFileNotFoundError',
    'ExcelEngineNotAvailableError',
    'ExcelSheetNotFoundError',
    'ExcelDataValidationError',
    'ExcelColumnMappingError',
    'ExcelWriteError',
    'ExcelDependencyError',
]

# 便捷函數 - 向後相容
def analyze_excel_sheets(file_path: str):
    """便捷函數：分析Excel工作表"""
    return ExcelHandler.analyze_excel_sheets(file_path)

def import_cases_by_category(file_path: str):
    """便捷函數：分類匯入案件"""
    return ExcelHandler.import_cases_by_category(file_path)

def export_cases_to_excel(cases, file_path: str):
    """便捷函數：匯出案件到Excel"""
    return ExcelHandler.export_cases_to_excel(cases, file_path)

def import_cases_from_excel(file_path: str):
    """便捷函數：從Excel匯入案件"""
    return ExcelHandler.import_cases_from_excel(file_path)

def get_dependency_status():
    """便捷函數：取得依賴狀態"""
    return ExcelHandler.get_dependency_status()

def validate_excel_data(file_path: str, sheet_name=None):
    """便捷函數：驗證Excel資料"""
    return ExcelHandler.validate_excel_data(file_path, sheet_name)

def get_excel_preview(file_path: str, sheet_name=None):
    """便捷函數：取得Excel預覽"""
    return ExcelHandler.get_excel_preview(file_path, sheet_name)


# 模組初始化檢查
def _check_module_health():
    """檢查模組健康狀態"""
    try:
        # 檢查主要依賴
        import pandas as pd

        # 檢查可選依賴
        optional_deps = {}
        try:
            import openpyxl
            optional_deps['openpyxl'] = True
        except ImportError:
            optional_deps['openpyxl'] = False

        try:
            import xlrd
            optional_deps['xlrd'] = True
        except ImportError:
            optional_deps['xlrd'] = False

        return {
            'pandas': True,
            'openpyxl': optional_deps['openpyxl'],
            'xlrd': optional_deps['xlrd'],
            'module_ready': True
        }

    except ImportError:
        return {
            'pandas': False,
            'openpyxl': False,
            'xlrd': False,
            'module_ready': False
        }

# 執行模組健康檢查
_MODULE_STATUS = _check_module_health()

if not _MODULE_STATUS['module_ready']:
    import warnings
    warnings.warn(
        "Excel處理模組初始化失敗：缺少必要依賴 pandas。"
        "請執行: pip install pandas openpyxl xlrd",
        ImportWarning
    )