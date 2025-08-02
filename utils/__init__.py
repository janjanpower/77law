#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
工具層模組 - 重構版本
統一所有工具模組的匯入介面
按照新的資料夾結構組織
"""

# ==================== 核心匯入 ====================

# 檔案操作模組
try:
    from .file_operations import (
        FolderManager,
        ExcelHandler,
        FileValidator,
        check_module_status as check_file_operations_status
    )
    FILE_OPERATIONS_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ 檔案操作模組載入失敗: {e}")
    FolderManager = None
    ExcelHandler = None
    FileValidator = None
    FILE_OPERATIONS_AVAILABLE = False

# 資料處理模組
try:
    from .data_processing import (
        DataCleaner,
        check_module_status as check_data_processing_status
    )
    DATA_PROCESSING_AVAILABLE = True

    # 智慧分析器（可選）
    try:
        from .data_processing import SmartAnalyzer
        SMART_ANALYZER_AVAILABLE = True
    except ImportError:
        SmartAnalyzer = None
        SMART_ANALYZER_AVAILABLE = False

except ImportError as e:
    print(f"⚠️ 資料處理模組載入失敗: {e}")
    DataCleaner = None
    SmartAnalyzer = None
    DATA_PROCESSING_AVAILABLE = False
    SMART_ANALYZER_AVAILABLE = False

# 輔助工具模組（可選）
try:
    from .helpers import (
        check_module_status as check_helpers_status
    )
    HELPERS_AVAILABLE = True

    # 事件管理器（可選）
    try:
        from .helpers import EventManager
        EVENT_MANAGER_AVAILABLE = True
    except ImportError:
        EventManager = None
        EVENT_MANAGER_AVAILABLE = False

    # 日誌記錄器（可選）
    try:
        from .helpers import Logger
        LOGGER_AVAILABLE = True
    except ImportError:
        Logger = None
        LOGGER_AVAILABLE = False

except ImportError:
    HELPERS_AVAILABLE = False
    EventManager = None
    Logger = None
    EVENT_MANAGER_AVAILABLE = False
    LOGGER_AVAILABLE = False

# ==================== 向後相容匯入 ====================

# 嘗試從舊位置匯入（向後相容）
if not FILE_OPERATIONS_AVAILABLE:
    print("🔄 嘗試從舊位置匯入模組...")

    try:
        from .folder_manager import FolderManager as LegacyFolderManager
        FolderManager = LegacyFolderManager
        print("✅ 成功從舊位置匯入 FolderManager")
    except ImportError:
        pass

    try:
        from .excel_handler import ExcelHandler as LegacyExcelHandler
        ExcelHandler = LegacyExcelHandler
        print("✅ 成功從舊位置匯入 ExcelHandler")
    except ImportError:
        pass

# 其他舊模組（可選）
try:
    from .notification_manager import NotificationManager
    NOTIFICATION_MANAGER_AVAILABLE = True
except ImportError:
    NotificationManager = None
    NOTIFICATION_MANAGER_AVAILABLE = False

try:
    from .date_reminder import DateReminderManager
    DATE_REMINDER_AVAILABLE = True
except ImportError:
    DateReminderManager = None
    DATE_REMINDER_AVAILABLE = False

# ==================== 公開介面 ====================

# 必要模組
__all__ = []

# 檔案操作模組
if FolderManager:
    __all__.append('FolderManager')
if ExcelHandler:
    __all__.append('ExcelHandler')
if FileValidator:
    __all__.append('FileValidator')

# 資料處理模組
if DataCleaner:
    __all__.append('DataCleaner')
if SmartAnalyzer:
    __all__.append('SmartAnalyzer')

# 輔助工具模組
if EventManager:
    __all__.append('EventManager')
if Logger:
    __all__.append('Logger')

# 舊模組（向後相容）
if NotificationManager:
    __all__.append('NotificationManager')
if DateReminderManager:
    __all__.append('DateReminderManager')

# ==================== 狀態檢查功能 ====================

def check_module_status():
    """檢查所有工具模組的載入狀態"""
    print("🔧 工具層模組載入狀態:")
    print("=" * 50)

    # 核心模組狀態
    core_modules = [
        ('FolderManager', FolderManager is not None),
        ('ExcelHandler', ExcelHandler is not None),
        ('FileValidator', FileValidator is not None),
        ('DataCleaner', DataCleaner is not None)
    ]

    core_loaded = 0
    print("\n📦 核心模組:")
    for name, available in core_modules:
        icon = "✅" if available else "❌"
        print(f"  {icon} {name}")
        if available:
            core_loaded += 1

    # 可選模組狀態
    optional_modules = [
        ('SmartAnalyzer', SMART_ANALYZER_AVAILABLE),
        ('EventManager', EVENT_MANAGER_AVAILABLE),
        ('Logger', LOGGER_AVAILABLE),
        ('NotificationManager', NOTIFICATION_MANAGER_AVAILABLE),
        ('DateReminderManager', DATE_REMINDER_AVAILABLE)
    ]

    optional_loaded = 0
    print("\n🔧 可選模組:")
    for name, available in optional_modules:
        icon = "✅" if available else "❌"
        print(f"  {icon} {name}")
        if available:
            optional_loaded += 1

    # 模組群組狀態
    print("\n📊 模組群組狀態:")
    groups = [
        ('檔案操作', FILE_OPERATIONS_AVAILABLE),
        ('資料處理', DATA_PROCESSING_AVAILABLE),
        ('輔助工具', HELPERS_AVAILABLE)
    ]

    for group_name, available in groups:
        icon = "✅" if available else "❌"
        print(f"  {icon} {group_name}")

    # 總結
    total_core = len(core_modules)
    total_optional = len(optional_modules)
    total_loaded = core_loaded + optional_loaded
    total_modules = total_core + total_optional

    print(f"\n📋 載入總結:")
    print(f"  • 核心模組: {core_loaded}/{total_core}")
    print(f"  • 可選模組: {optional_loaded}/{total_optional}")
    print(f"  • 總計: {total_loaded}/{total_modules}")
    print(f"  • 成功率: {(total_loaded/total_modules*100):.1f}%")

    # 詳細狀態檢查
    print(f"\n🔍 詳細狀態檢查:")
    if FILE_OPERATIONS_AVAILABLE:
        try:
            check_file_operations_status()
        except:
            print("  ⚠️ 檔案操作模組狀態檢查失敗")

    if DATA_PROCESSING_AVAILABLE:
        try:
            check_data_processing_status()
        except:
            print("  ⚠️ 資料處理模組狀態檢查失敗")

    if HELPERS_AVAILABLE:
        try:
            check_helpers_status()
        except:
            print("  ⚠️ 輔助工具模組狀態檢查失敗")

    # 警告和建議
    warnings = []
    if core_loaded < total_core:
        warnings.append("部分核心模組載入失敗，可能影響系統功能")

    if not FILE_OPERATIONS_AVAILABLE:
        warnings.append("檔案操作模組不可用，請檢查 utils/file_operations/ 資料夾")

    if not DATA_PROCESSING_AVAILABLE:
        warnings.append("資料處理模組不可用，請檢查 utils/data_processing/ 資料夾")

    if warnings:
        print(f"\n⚠️ 注意事項:")
        for warning in warnings:
            print(f"  • {warning}")

    print("=" * 50)
    return {
        'core_loaded': core_loaded,
        'optional_loaded': optional_loaded,
        'total_loaded': total_loaded,
        'success_rate': total_loaded/total_modules*100 if total_modules > 0 else 0,
        'file_operations': FILE_OPERATIONS_AVAILABLE,
        'data_processing': DATA_PROCESSING_AVAILABLE,
        'helpers': HELPERS_AVAILABLE
    }

def get_import_fix_suggestions():
    """提供匯入修復建議"""
    suggestions = []

    if not FILE_OPERATIONS_AVAILABLE:
        suggestions.append("檔案操作模組：檢查 utils/file_operations/ 資料夾結構和檔案")

    if not DATA_PROCESSING_AVAILABLE:
        suggestions.append("資料處理模組：檢查 utils/data_processing/ 資料夾結構和檔案")

    if not ExcelHandler:
        suggestions.append("Excel處理：檢查 pandas 和 openpyxl 套件是否已安裝")

    if not HELPERS_AVAILABLE:
        suggestions.append("輔助工具模組：檢查 utils/helpers/ 資料夾（可選）")

    return suggestions

# ==================== 便捷函數 ====================

def create_folder_manager(base_folder: str):
    """建立資料夾管理器實例"""
    if FolderManager:
        return FolderManager(base_folder)
    else:
        raise ImportError("FolderManager 不可用")

def create_excel_handler():
    """建立Excel處理器實例"""
    if ExcelHandler:
        return ExcelHandler()
    else:
        raise ImportError("ExcelHandler 不可用")

def create_file_validator():
    """建立檔案驗證器實例"""
    if FileValidator:
        return FileValidator()
    else:
        raise ImportError("FileValidator 不可用")

def create_data_cleaner():
    """建立資料清理器實例"""
    if DataCleaner:
        return DataCleaner()
    else:
        raise ImportError("DataCleaner 不可用")

# ==================== 版本資訊 ====================

__version__ = '2.0.0'
__author__ = '77LAW Case Management System'

# ==================== 自動狀態檢查 ====================

# 僅在直接匯入時執行狀態檢查
if __name__ != "__main__":
    status = check_module_status()

    # 如果核心模組載入失敗太多，提供建議
    if status['core_loaded'] < 2:
        print("\n💡 修復建議:")
        suggestions = get_import_fix_suggestions()
        for suggestion in suggestions:
            print(f"  • {suggestion}")
        print("\n🔧 執行 utils.check_module_status() 查看詳細狀態")