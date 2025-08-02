#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Services 層 - 業務邏輯層
提供統一的業務服務介面，確保邏輯層的清晰分層
"""

import sys
import os

# 安全匯入各個服務模組
def safe_import(module_name, class_name):
    """安全匯入服務模組和類別"""
    try:
        if module_name == 'case_service':
            from .case_service import CaseService
            return CaseService
        elif module_name == 'folder_service':
            from .folder_service import FolderService
            return FolderService
        elif module_name == 'import_export_service':
            from .import_export_service import ImportExportService
            return ImportExportService
        elif module_name == 'notification_service':
            from .notification_service import NotificationService
            return NotificationService
        elif module_name == 'validation_service':
            from .validation_service import ValidationService
            return ValidationService
        elif module_name == 'progress_service':
            from .progress_service import ProgressService
            return ProgressService
        else:
            return None
    except ImportError as e:
        print(f"⚠️ 警告: 無法載入服務 {module_name}.{class_name} - {e}")
        return None
    except Exception as e:
        print(f"⚠️ 警告: 載入服務 {module_name}.{class_name} 時發生錯誤 - {e}")
        return None

# 嘗試匯入所有服務
CaseService = safe_import('case_service', 'CaseService')
FolderService = safe_import('folder_service', 'FolderService')
ImportExportService = safe_import('import_export_service', 'ImportExportService')
NotificationService = safe_import('notification_service', 'NotificationService')
ValidationService = safe_import('validation_service', 'ValidationService')
ProgressService = safe_import('progress_service', 'ProgressService')

# 定義對外暴露的服務清單
__all__ = []

# 動態添加可用的服務到 __all__
services_map = {
    'CaseService': CaseService,
    'FolderService': FolderService,
    'ImportExportService': ImportExportService,
    'NotificationService': NotificationService,
    'ValidationService': ValidationService,
    'ProgressService': ProgressService
}

for service_name, service_class in services_map.items():
    if service_class is not None:
        __all__.append(service_name)
        # 將服務類別加入到全局命名空間
        globals()[service_name] = service_class

def check_services_status():
    """檢查服務載入狀態"""
    print("📦 Services 模組載入狀態:")

    for service_name, service_class in services_map.items():
        icon = "✅" if service_class is not None else "❌"
        print(f"  {icon} {service_name}")

    print(f"\n📋 總計載入成功: {len(__all__)} 個服務")
    return len(__all__)

def get_available_services():
    """取得可用的服務清單"""
    return {name: cls for name, cls in services_map.items() if cls is not None}

def create_service_factory():
    """建立服務工廠，統一管理服務實例"""
    return ServiceFactory()

class ServiceFactory:
    """服務工廠類別，用於統一管理和建立服務實例"""

    def __init__(self):
        self._service_instances = {}
        self._available_services = get_available_services()

    def get_service(self, service_name: str, *args, **kwargs):
        """
        取得服務實例（單例模式）

        Args:
            service_name: 服務名稱
            *args, **kwargs: 服務初始化參數

        Returns:
            服務實例或 None
        """
        if service_name not in self._available_services:
            print(f"❌ 服務不可用: {service_name}")
            return None

        # 單例模式：如果已存在實例則直接返回
        if service_name in self._service_instances:
            return self._service_instances[service_name]

        # 建立新的服務實例
        try:
            service_class = self._available_services[service_name]
            service_instance = service_class(*args, **kwargs)
            self._service_instances[service_name] = service_instance
            print(f"✅ 成功建立服務實例: {service_name}")
            return service_instance
        except Exception as e:
            print(f"❌ 建立服務實例失敗: {service_name} - {e}")
            return None

    def reset_service(self, service_name: str):
        """重置指定服務實例"""
        if service_name in self._service_instances:
            del self._service_instances[service_name]
            print(f"🔄 已重置服務實例: {service_name}")

    def reset_all_services(self):
        """重置所有服務實例"""
        self._service_instances.clear()
        print("🔄 已重置所有服務實例")

    def list_active_services(self):
        """列出活躍的服務實例"""
        return list(self._service_instances.keys())

# 自動狀態檢查
if __name__ != "__main__":
    loaded_count = check_services_status()

    if loaded_count < 3:  # 如果載入的服務太少
        print("\n⚠️ 偵測到服務載入問題，建議檢查：")
        print("  • 確保 services/ 資料夾中的所有 .py 檔案存在")
        print("  • 檢查各服務檔案的語法錯誤")
        print("  • 執行 services.check_services_status() 查看詳細狀態")
        print("\n💡 使用 services.create_service_factory() 建立服務管理器")