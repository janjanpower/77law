#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
資料處理模組
提供資料清理、智慧分析等資料處理功能
"""

# 匯入核心類別
from .data_cleaner import DataCleaner

# 嘗試匯入智慧分析器（可選）
try:
    from .smart_analyzer import SmartAnalyzer
    SMART_ANALYZER_AVAILABLE = True
except ImportError:
    SmartAnalyzer = None
    SMART_ANALYZER_AVAILABLE = False

# 版本資訊
__version__ = '1.0.0'
__author__ = '77LAW Case Management System'

# 公開介面
__all__ = [
    'DataCleaner'
]

# 如果智慧分析器可用，加入公開介面
if SMART_ANALYZER_AVAILABLE:
    __all__.append('SmartAnalyzer')

# 狀態檢查功能
def check_module_status():
    """檢查模組載入狀態"""
    print("📊 資料處理模組狀態:")

    modules = [
        ('DataCleaner', DataCleaner is not None),
        ('SmartAnalyzer', SMART_ANALYZER_AVAILABLE)
    ]

    loaded_count = 0
    for name, available in modules:
        icon = "✅" if available else "❌"
        print(f"  {icon} {name}")
        if available:
            loaded_count += 1

    print(f"\n📋 總計載入成功: {loaded_count}/{len(modules)} 個模組")

    if not SMART_ANALYZER_AVAILABLE:
        print("\n💡 SmartAnalyzer 為可選模組，不影響核心功能")

    return loaded_count

# 便捷函數
def create_data_cleaner():
    """建立資料清理器實例"""
    return DataCleaner()

def create_smart_analyzer():
    """建立智慧分析器實例（如果可用）"""
    if SMART_ANALYZER_AVAILABLE:
        return SmartAnalyzer()
    else:
        raise ImportError("SmartAnalyzer 不可用")

# 快速清理函數
def quick_clean_text(text):
    """快速文字清理"""
    cleaner = DataCleaner()
    return cleaner.clean_text_data(text)

def quick_clean_case_data(case_dict):
    """快速案件資料清理"""
    cleaner = DataCleaner()
    return cleaner.clean_case_data_dict(case_dict)

# 自動狀態檢查（僅在匯入時執行一次）
if __name__ != "__main__":
    loaded_count = check_module_status()

    if loaded_count == 0:
        print("\n⚠️ 資料處理模組載入失敗，請檢查相關檔案")