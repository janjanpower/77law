#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
輔助工具模組
提供事件管理、日誌記錄等輔助功能
"""

# 嘗試匯入各個輔助工具
try:
    from .event_manager import EventManager
    EVENT_MANAGER_AVAILABLE = True
except ImportError:
    EventManager = None
    EVENT_MANAGER_AVAILABLE = False

try:
    from .logger import Logger
    LOGGER_AVAILABLE = True
except ImportError:
    Logger = None
    LOGGER_AVAILABLE = False

# 版本資訊
__version__ = '1.0.0'
__author__ = '77LAW Case Management System'

# 公開介面
__all__ = []

if EVENT_MANAGER_AVAILABLE:
    __all__.append('EventManager')

if LOGGER_AVAILABLE:
    __all__.append('Logger')

# 狀態檢查功能
def check_module_status():
    """檢查模組載入狀態"""
    print("🔧 輔助工具模組狀態:")

    modules = [
        ('EventManager', EVENT_MANAGER_AVAILABLE),
        ('Logger', LOGGER_AVAILABLE)
    ]

    loaded_count = 0
    for name, available in modules:
        icon = "✅" if available else "❌"
        print(f"  {icon} {name}")
        if available:
            loaded_count += 1

    print(f"\n📋 總計載入成功: {loaded_count}/{len(modules)} 個模組")

    if loaded_count == 0:
        print("\n💡 輔助工具為可選模組，不影響核心功能")

    return loaded_count

# 便捷函數
def create_event_manager():
    """建立事件管理器實例（如果可用）"""
    if EVENT_MANAGER_AVAILABLE:
        return EventManager()
    else:
        raise ImportError("EventManager 不可用")

def create_logger(name: str = "77LAW"):
    """建立日誌記錄器實例（如果可用）"""
    if LOGGER_AVAILABLE:
        return Logger(name)
    else:
        raise ImportError("Logger 不可用")

# 自動狀態檢查（僅在匯入時執行一次）
if __name__ != "__main__":
    check_module_status()