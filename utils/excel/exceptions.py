#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Excel處理模組自訂例外類別
統一處理Excel相關的錯誤情況
"""


class ExcelBaseException(Exception):
    """Excel處理基礎例外類別"""
    pass


class ExcelFileNotFoundError(ExcelBaseException):
    """Excel檔案未找到例外"""
    pass


class ExcelEngineNotAvailableError(ExcelBaseException):
    """Excel處理引擎不可用例外"""
    pass


class ExcelSheetNotFoundError(ExcelBaseException):
    """Excel工作表未找到例外"""
    pass


class ExcelDataValidationError(ExcelBaseException):
    """Excel資料驗證失敗例外"""
    pass


class ExcelColumnMappingError(ExcelBaseException):
    """Excel欄位對應失敗例外"""
    pass


class ExcelWriteError(ExcelBaseException):
    """Excel寫入失敗例外"""
    pass


class ExcelDependencyError(ExcelBaseException):
    """Excel依賴模組不可用例外"""
    pass