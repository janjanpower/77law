#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Excel統一介面模組
將現有的Excel處理模組整合為統一介面
"""

# 導入專責模組
try:
    from .excel_handler import ExcelHandler
    from .excel_reader import ExcelReader
    from .excel_writer import ExcelWriter
    from .excel_analyzer import ExcelAnalyzer
    from .excel_validator import ExcelValidator

    # 模組載入成功標記
    ALL_MODULES_LOADED = True
    print("✅ 所有Excel子模組載入成功")

except ImportError as e:
    print(f"⚠️ 部分Excel子模組載入失敗: {e}")
    ALL_MODULES_LOADED = False

    # 建立基本的替代實作
    import pandas as pd
    from typing import List, Dict, Optional, Tuple, Any

    class ExcelHandler:
        """基本Excel處理器"""
        @staticmethod
        def check_dependencies():
            try:
                import pandas as pd
                import openpyxl
                return {'pandas': True, 'openpyxl': True, 'excel_modules': False}
            except ImportError:
                return {'pandas': False, 'openpyxl': False, 'excel_modules': False}

        @staticmethod
        def analyze_excel_sheets(file_path: str) -> Tuple[bool, str, Dict[str, List[str]]]:
            return False, "Excel模組未完全載入", {}

        @staticmethod
        def import_cases_from_excel(file_path: str) -> Optional[List]:
            print("⚠️ Excel模組未完全載入，功能受限")
            return None

    # 設定其他類別為None
    ExcelReader = ExcelWriter = ExcelAnalyzer = ExcelValidator = None

# 匯出所有可用的類別
__all__ = ['ExcelHandler']

if ALL_MODULES_LOADED:
    __all__.extend(['ExcelReader', 'ExcelWriter', 'ExcelAnalyzer', 'ExcelValidator'])

# 為了向後相容，確保ExcelHandler總是可用
if 'ExcelHandler' not in locals():
    class ExcelHandler:
        @staticmethod
        def check_dependencies():
            return {'excel_modules': False}

# 模組資訊
__version__ = '2.0.0'
__description__ = 'Excel統一介面模組'