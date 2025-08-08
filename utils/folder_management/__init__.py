#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
資料夾管理模組
提供統一的資料夾管理功能介面
"""

# 安全匯入所有模組
import sys
import os

# 添加當前目錄到 Python 路徑
current_dir = os.path.dirname(__file__)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# 嘗試匯入各個模組
_modules_loaded = {}

def safe_import(module_name, class_name):
    """安全匯入模組和類別"""
    try:
        if module_name in _modules_loaded:
            module = _modules_loaded[module_name]
        else:
            if module_name == 'folder_validator':
                from . import folder_validator as module
            elif module_name == 'folder_creator':
                from . import folder_creator as module
            elif module_name == 'folder_operations':
                from . import folder_operations as module
            elif module_name == 'excel_generator':
                from . import excel_generator as module
            elif module_name == 'folder_manager':
                from . import folder_manager as module
            else:
                return None

            _modules_loaded[module_name] = module

        return getattr(module, class_name, None)
    except ImportError as e:
        print(f"⚠️ 警告: 無法載入 {module_name}.{class_name} - {e}")
        return None
    except Exception as e:
        print(f"⚠️ 警告: 載入 {module_name}.{class_name} 時發生錯誤 - {e}")
        return None

# 嘗試匯入所有類別
FolderValidator = safe_import('folder_validator', 'FolderValidator')
FolderCreator = safe_import('folder_creator', 'FolderCreator')
FolderOperations = safe_import('folder_operations', 'FolderOperations')
ExcelGenerator = safe_import('excel_generator', 'ExcelGenerator')
FolderManager = safe_import('folder_manager', 'FolderManager')

# 檢查哪些模組成功載入
_available_modules = []
_missing_modules = []

for name, cls in [
    ('FolderValidator', FolderValidator),
    ('FolderCreator', FolderCreator),
    ('FolderOperations', FolderOperations),
    ('ExcelGenerator', ExcelGenerator),
    ('FolderManager', FolderManager)
]:
    if cls is not None:
        _available_modules.append(name)
    else:
        _missing_modules.append(name)

# 如果有缺失的模組，提供備用實作
if FolderManager is None and FolderValidator is not None:
    # 建立最小化的 FolderManager
    class MinimalFolderManager:
        def __init__(self, base_data_folder: str):
            self.base_data_folder = base_data_folder
            if FolderValidator:
                self.validator = FolderValidator()

        def create_case_folder_structure(self, case_data):
            print("⚠️ 警告: 使用最小化的 FolderManager，功能受限")
            return False

        def get_case_folder_path(self, case_data):
            return None

        def __str__(self):
            return f"MinimalFolderManager(base_folder='{self.base_data_folder}')"

    FolderManager = MinimalFolderManager
    print("⚠️ 使用最小化的 FolderManager")

# 建立匯出清單
__all__ = []

# 只匯出成功載入的模組
for name, cls in [
    ('FolderValidator', FolderValidator),
    ('FolderCreator', FolderCreator),
    ('FolderOperations', FolderOperations),
    ('ExcelGenerator', ExcelGenerator),
    ('FolderManager', FolderManager)
]:
    if cls is not None:
        __all__.append(name)
        globals()[name] = cls

# 版本資訊
__version__ = '2.0.0'
__author__ = '77LAW Case Management System'

# 狀態報告
def print_import_status():
    """列印匯入狀態"""
    print("📦 資料夾管理模組載入狀態:")

    for module in _available_modules:
        print(f"  ✅ {module}")

    for module in _missing_modules:
        print(f"  ❌ {module}")

    if _missing_modules:
        print(f"\n⚠️ 警告: {len(_missing_modules)} 個模組載入失敗")
        print("請檢查以下檔案是否存在且內容正確:")
        for module in _missing_modules:
            filename = module.lower().replace('manager', '_manager').replace('creator', '_creator').replace('validator', '_validator').replace('operations', '_operations').replace('generator', '_generator')
            if not filename.endswith('.py'):
                filename = filename.replace('folder', 'folder_') + '.py'
            print(f"  - {filename}")
    else:
        print("🎉 所有模組載入成功!")

    print(f"\n📋 可用模組: {len(__all__)} 個")

# 自動狀態檢查
if _missing_modules:
    print_import_status()