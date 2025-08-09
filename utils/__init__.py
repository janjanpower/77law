#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工具模組 - 修復版本
正確的模組匯入和向後相容性
"""

# 🔧 修復：正確匯入Excel模組
try:
    from .excel import ExcelHandler
    print("✅ Excel模組載入成功")
    EXCEL_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Excel模組載入失敗，使用備用方案: {e}")
    EXCEL_AVAILABLE = False

    # 備用Excel處理器
    try:
        from .excel_handler import ExcelHandler
        print("✅ 使用備用Excel處理器")
    except ImportError:
        print("❌ 所有Excel處理器都無法載入")
        ExcelHandler = None

# 其他必要模組
try:
    from .date_reminder import DateReminderManager
except ImportError:
    print("⚠️ DateReminderManager 無法載入")
    DateReminderManager = None

try:
    from .notification_manager import NotificationManager
except ImportError:
    print("⚠️ NotificationManager 無法載入")
    NotificationManager = None

# 🔧 修復：正確匯入資料夾管理模組
try:
    from .folder_management import (
        FolderManager,
        FolderCreator,
        FolderValidator,
        FolderOperations,
        ExcelGenerator
    )
    print("✅ 資料夾管理模組載入成功")
    FOLDER_MANAGEMENT_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ 資料夾管理模組載入失敗: {e}")
    FOLDER_MANAGEMENT_AVAILABLE = False
    # 設定為None以避免NameError
    FolderManager = FolderCreator = FolderValidator = FolderOperations = ExcelGenerator = None

# 可選模組
try:
    from .hardware_utils import HardwareUtils
    HARDWARE_UTILS_AVAILABLE = True
except ImportError:
    HARDWARE_UTILS_AVAILABLE = False
    HardwareUtils = None

try:
    from .event_manager import event_manager, EventType
    EVENT_MANAGER_AVAILABLE = True
except ImportError:
    EVENT_MANAGER_AVAILABLE = False
    event_manager = EventType = None

try:
    from .smart_excel_analyzer import SmartExcelAnalyzer
    SMART_EXCEL_AVAILABLE = True
except ImportError:
    SMART_EXCEL_AVAILABLE = False
    SmartExcelAnalyzer = None

try:
    from .data_cleaner import DataCleaner
    DATA_CLEANER_AVAILABLE = True
except ImportError:
    DATA_CLEANER_AVAILABLE = False
    DataCleaner = None

# 動態建立匯出列表
__all__ = []

# 基本模組
for name, obj in [
    ('ExcelHandler', ExcelHandler),
    ('DateReminderManager', DateReminderManager),
    ('NotificationManager', NotificationManager)
]:
    if obj is not None:
        __all__.append(name)

# 資料夾管理模組
if FOLDER_MANAGEMENT_AVAILABLE:
    for name, obj in [
        ('FolderManager', FolderManager),
        ('FolderCreator', FolderCreator),
        ('FolderValidator', FolderValidator),
        ('FolderOperations', FolderOperations),
        ('ExcelGenerator', ExcelGenerator)
    ]:
        if obj is not None:
            __all__.append(name)

# 可選模組
for name, available, obj in [
    ('HardwareUtils', HARDWARE_UTILS_AVAILABLE, HardwareUtils),
    ('SmartExcelAnalyzer', SMART_EXCEL_AVAILABLE, SmartExcelAnalyzer),
    ('DataCleaner', DATA_CLEANER_AVAILABLE, DataCleaner)
]:
    if available and obj is not None:
        __all__.append(name)

if EVENT_MANAGER_AVAILABLE:
    if event_manager is not None:
        __all__.append('event_manager')
    if EventType is not None:
        __all__.append('EventType')

# 版本資訊
__version__ = '2.0.0'
__author__ = '77LAW Case Management System'

def check_module_status():
    """檢查模組載入狀態"""
    print("📦 Utils模組載入狀態:")

    modules = [
        ('ExcelHandler', ExcelHandler is not None),
        ('DateReminderManager', DateReminderManager is not None),
        ('NotificationManager', NotificationManager is not None),
        ('FolderManager', FolderManager is not None),
        ('FolderCreator', FolderCreator is not None),
        ('FolderValidator', FolderValidator is not None),
        ('FolderOperations', FolderOperations is not None),
        ('ExcelGenerator', ExcelGenerator is not None),
        ('SmartExcelAnalyzer', SMART_EXCEL_AVAILABLE),
        ('DataCleaner', DATA_CLEANER_AVAILABLE),
        ('EventManager', EVENT_MANAGER_AVAILABLE)
    ]

    for name, available in modules:
        icon = "✅" if available else "❌"
        print(f"  {icon} {name}")

    print(f"\n📋 總計載入成功: {len(__all__)} 個模組")
    return len(__all__)

def get_import_fix_suggestions():
    """提供匯入修復建議"""
    suggestions = []

    if ExcelHandler is None:
        suggestions.append("Excel處理模組：檢查 utils/excel/ 資料夾結構")

    if FolderManager is None:
        suggestions.append("資料夾管理模組：檢查 utils/folder_management/ 資料夾結構")

    if not HARDWARE_UTILS_AVAILABLE:
        suggestions.append("硬體工具模組：檔案可能不存在，可忽略")

    return suggestions

# 自動狀態檢查
if __name__ != "__main__":
    loaded_count = check_module_status()

    if loaded_count < 5:  # 如果載入的模組太少
        print("\n⚠️ 偵測到模組載入問題，建議檢查：")
        for suggestion in get_import_fix_suggestions():
            print(f"  • {suggestion}")
        print("\n💡 執行 utils.check_module_status() 查看詳細狀態")