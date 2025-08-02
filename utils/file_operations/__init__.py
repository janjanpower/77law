#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
檔案操作模組
提供統一的檔案和資料夾操作功能
"""

# 匯入核心類別
from .folder_manager import FolderManager
from .excel_handler import ExcelHandler
from .file_validator import FileValidator

# 版本資訊
__version__ = '1.0.0'
__author__ = '77LAW Case Management System'

# 公開介面
__all__ = [
    'FolderManager',
    'ExcelHandler',
    'FileValidator'
]

# 狀態檢查功能
def check_module_status():
    """檢查模組載入狀態"""
    print("📦 檔案操作模組狀態:")

    modules = [
        ('FolderManager', FolderManager is not None),
        ('ExcelHandler', ExcelHandler is not None),
        ('FileValidator', FileValidator is not None)
    ]

    loaded_count = 0
    for name, available in modules:
        icon = "✅" if available else "❌"
        print(f"  {icon} {name}")
        if available:
            loaded_count += 1

    print(f"\n📋 總計載入成功: {loaded_count}/{len(modules)} 個模組")

    # 檢查依賴
    if hasattr(ExcelHandler, 'get_dependency_status'):
        try:
            excel_handler = ExcelHandler()
            print("\n" + excel_handler.get_dependency_status())
        except Exception as e:
            print(f"\n⚠️ Excel處理器狀態檢查失敗: {e}")

    return loaded_count

# 便捷函數
def create_folder_manager(base_folder: str):
    """建立資料夾管理器實例"""
    return FolderManager(base_folder)

def create_excel_handler():
    """建立Excel處理器實例"""
    return ExcelHandler()

def create_file_validator():
    """建立檔案驗證器實例"""
    return FileValidator()

# 自動狀態檢查（僅在匯入時執行一次）
if __name__ != "__main__":
    loaded_count = check_module_status()

    if loaded_count < 3:
        print("\n⚠️ 部分模組載入失敗，請檢查相關檔案是否存在")
        print("💡 執行 utils.file_operations.check_module_status() 查看詳細狀態")