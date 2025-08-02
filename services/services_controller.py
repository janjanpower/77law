#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Services 層控制器 - 修復版本
提供統一的服務層介面，整合所有業務邏輯服務
解決循環依賴和初始化問題
"""

from typing import List, Optional, Dict, Any, Tuple
import os
import sys
from datetime import datetime


class ServicesController:
    """Services 層統一控制器 - 修復版本"""

    def __init__(self, data_folder: str, data_file: str = None):
        """
        初始化服務控制器

        Args:
            data_folder: 資料資料夾路徑
            data_file: 案件資料檔案路徑
        """
        self.data_folder = data_folder
        self.data_file = data_file or os.path.join(data_folder, "cases.json")

        # 確保資料夾存在
        os.makedirs(self.data_folder, exist_ok=True)

        # 服務實例
        self.case_service = None
        self.validation_service = None
        self.folder_service = None
        self.notification_service = None
        self.import_export_service = None
        self.progress_service = None

        # 初始化服務
        self._initialize_services()

        print("✅ ServicesController 初始化完成")

    def _initialize_services(self):
        """安全地初始化所有服務（避免循環依賴）"""
        try:
            # 1. 先初始化獨立的服務
            self._init_validation_service()
            self._init_notification_service()

            # 2. 初始化依賴較少的服務
            self._init_folder_service()
            self._init_import_export_service()
            self._init_progress_service()

            # 3. 最後初始化核心案件服務
            self._init_case_service()

            print("✅ 所有服務初始化完成")

        except Exception as e:
            print(f"❌ 服務初始化失敗: {e}")
            # 建立基本服務以確保系統可以運行
            self._create_fallback_services()

    def _init_validation_service(self):
        """初始化驗證服務"""
        try:
            from .validation_service import ValidationService
            self.validation_service = ValidationService()
            print("✅ ValidationService 已初始化")
        except ImportError as e:
            print(f"⚠️ ValidationService 載入失敗: {e}")
            try:
                from .simple_validation_service import get_simple_validation_service
                self.validation_service = get_simple_validation_service()
                print("✅ 使用簡化驗證服務")
            except ImportError:
                print("⚠️ 簡化驗證服務也無法載入，使用Mock服務")
                self.validation_service = self._create_mock_validation_service()

    def _init_notification_service(self):
        """初始化通知服務"""
        try:
            from .notification_service import NotificationService
            self.notification_service = NotificationService()
            print("✅ NotificationService 已初始化")
        except ImportError as e:
            print(f"⚠️ NotificationService 載入失敗: {e}")
            self.notification_service = self._create_mock_notification_service()

    def _init_folder_service(self):
        """初始化資料夾服務"""
        try:
            from .folder_service import FolderService
            self.folder_service = FolderService(self.data_folder)
            print("✅ FolderService 已初始化")
        except ImportError as e:
            print(f"⚠️ FolderService 載入失敗: {e}")
            self.folder_service = self._create_mock_folder_service()

    def _init_import_export_service(self):
        """初始化匯入匯出服務"""
        try:
            from .import_export_service import ImportExportService
            self.import_export_service = ImportExportService(self.data_folder)
            print("✅ ImportExportService 已初始化")
        except ImportError as e:
            print(f"⚠️ ImportExportService 載入失敗: {e}")
            self.import_export_service = self._create_mock_import_export_service()

    def _init_progress_service(self):
        """初始化進度服務"""
        try:
            from .progress_service import ProgressService
            self.progress_service = ProgressService(self.data_folder)
            print("✅ ProgressService 已初始化")
        except ImportError as e:
            print(f"⚠️ ProgressService 載入失敗: {e}")
            self.progress_service = self._create_mock_progress_service()

    def _init_case_service(self):
        """初始化案件服務"""
        try:
            from .case_service import CaseService
            self.case_service = CaseService(self.data_folder, self.data_file)
            print("✅ CaseService 已初始化")
        except ImportError as e:
            print(f"⚠️ CaseService 載入失敗: {e}")
            self.case_service = self._create_mock_case_service()

    # ==================== Mock 服務創建 ====================

    def _create_mock_validation_service(self):
        """創建模擬驗證服務"""
        class MockValidationService:
            def validate_case_data(self, case_data):
                return True, "Mock validation passed"
        return MockValidationService()

    def _create_mock_notification_service(self):
        """創建模擬通知服務"""
        class MockNotificationService:
            def notify_case_created(self, case_data):
                print(f"🔔 Mock: 案件建立通知 - {case_data.client}")
            def notify_case_updated(self, case_data, old_data=None):
                print(f"🔔 Mock: 案件更新通知 - {case_data.client}")
            def notify_case_deleted(self, case_data):
                print(f"🔔 Mock: 案件刪除通知 - {case_data.client}")
        return MockNotificationService()

    def _create_mock_folder_service(self):
        """創建模擬資料夾服務"""
        class MockFolderService:
            def create_case_folder_structure(self, case_data):
                print(f"📁 Mock: 建立資料夾 - {case_data.client}")
                return True, "Mock folder created"
            def delete_case_folder(self, case_data):
                print(f"📁 Mock: 刪除資料夾 - {case_data.client}")
                return True, "Mock folder deleted"
        return MockFolderService()

    def _create_mock_import_export_service(self):
        """創建模擬匯入匯出服務"""
        class MockImportExportService:
            def import_cases_from_excel(self, file_path, **kwargs):
                return False, "Mock: 匯入功能未實現"
            def export_cases_to_excel(self, cases, file_path, **kwargs):
                return False, "Mock: 匯出功能未實現"
        return MockImportExportService()

    def _create_mock_progress_service(self):
        """創建模擬進度服務"""
        class MockProgressService:
            def apply_progress_template(self, case_id, template_name):
                print(f"📋 Mock: 套用進度範本 {template_name} 到案件 {case_id}")
                return True, "Mock template applied"
        return MockProgressService()

    def _create_mock_case_service(self):
        """創建模擬案件服務"""
        class MockCaseService:
            def __init__(self, data_folder):
                self.data_folder = data_folder  # 修復：添加 data_folder 屬性
                try:
                    from repositories.case_repository import CaseRepository
                    self.repository = CaseRepository(os.path.join(data_folder, "cases.json"))
                except ImportError:
                    self.repository = None

            def create_case(self, case_data, create_folder=True):
                print(f"🏗️ Mock: 建立案件 - {case_data.client}")
                if self.repository:
                    return self.repository.create_case(case_data), "Mock case created"
                return True, "Mock case created"

            def update_case(self, case_data, update_folder=False):
                print(f"🔄 Mock: 更新案件 - {case_data.client}")
                if self.repository:
                    return self.repository.update_case(case_data), "Mock case updated"
                return True, "Mock case updated"

            def delete_case(self, case_id, delete_folder=True, force=False):
                print(f"🗑️ Mock: 刪除案件 - {case_id}")
                if self.repository:
                    return self.repository.delete_case(case_id), "Mock case deleted"
                return True, "Mock case deleted"

        return MockCaseService(self.data_folder)  # 傳入 data_folder

    def _create_fallback_services(self):
        """創建備用服務確保系統可運行"""
        print("🚨 正在創建備用服務...")

        if self.validation_service is None:
            self.validation_service = self._create_mock_validation_service()
        if self.notification_service is None:
            self.notification_service = self._create_mock_notification_service()
        if self.folder_service is None:
            self.folder_service = self._create_mock_folder_service()
        if self.import_export_service is None:
            self.import_export_service = self._create_mock_import_export_service()
        if self.progress_service is None:
            self.progress_service = self._create_mock_progress_service()
        if self.case_service is None:
            self.case_service = self._create_mock_case_service()

        print("✅ 備用服務創建完成")

    # ==================== 案件管理統一介面 ====================

    def create_case(self, case_data, create_folder: bool = True,
                   apply_template: str = None) -> Tuple[bool, str]:
        """
        建立案件（整合完整流程）

        Args:
            case_data: 案件資料
            create_folder: 是否建立資料夾
            apply_template: 套用的進度範本名稱

        Returns:
            (成功與否, 結果訊息)
        """
        try:
            print(f"🎯 ServicesController: 開始建立案件 {case_data.client}")

            # 1. 驗證案件資料
            if self.validation_service:
                validation_result = self.validation_service.validate_case_data(case_data)
                if not validation_result[0]:
                    return False, f"驗證失敗: {validation_result[1]}"

            # 2. 建立案件
            if self.case_service:
                case_result = self.case_service.create_case(case_data, create_folder)
                if not case_result[0]:
                    return False, f"案件建立失敗: {case_result[1]}"
            else:
                return False, "案件服務未可用"

            # 3. 建立資料夾（如果需要且服務可用）
            if create_folder and self.folder_service:
                folder_result = self.folder_service.create_case_folder_structure(case_data)
                if not folder_result[0]:
                    print(f"⚠️ 警告: 資料夾建立失敗 - {folder_result[1]}")

            # 4. 套用進度範本（如果指定且服務可用）
            if apply_template and self.progress_service:
                template_result = self.progress_service.apply_progress_template(
                    case_data.case_id, apply_template
                )
                if not template_result[0]:
                    print(f"⚠️ 警告: 套用進度範本失敗 - {template_result[1]}")
                else:
                    print(f"✅ 成功套用進度範本: {apply_template}")

            # 5. 發送通知
            if self.notification_service:
                self.notification_service.notify_case_created(case_data)

            print(f"✅ ServicesController: 案件建立完成 {case_data.client}")
            return True, f"成功建立案件: {case_data.client}"

        except Exception as e:
            error_msg = f"ServicesController 建立案件失敗: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg

    def update_case(self, case_data, update_folder: bool = False,
                   sync_progress: bool = True) -> Tuple[bool, str]:
        """
        更新案件（整合完整流程）

        Args:
            case_data: 更新後的案件資料
            update_folder: 是否同步更新資料夾
            sync_progress: 是否同步進度資訊

        Returns:
            (成功與否, 結果訊息)
        """
        try:
            print(f"🎯 ServicesController: 開始更新案件 {case_data.case_id}")

            # 1. 驗證案件資料
            if self.validation_service:
                validation_result = self.validation_service.validate_case_data(case_data)
                if not validation_result[0]:
                    return False, f"驗證失敗: {validation_result[1]}"

            # 2. 更新案件資料
            if self.case_service:
                case_result = self.case_service.update_case(case_data, update_folder)
                if not case_result[0]:
                    return False, f"案件更新失敗: {case_result[1]}"
            else:
                return False, "案件服務未可用"

            # 3. 發送通知
            if self.notification_service:
                self.notification_service.notify_case_updated(case_data)

            print(f"✅ ServicesController: 案件更新完成 {case_data.case_id}")
            return True, f"成功更新案件: {case_data.client}"

        except Exception as e:
            error_msg = f"ServicesController 更新案件失敗: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg

    def delete_case(self, case_id: str, delete_folder: bool = True,
                   delete_progress: bool = True, force: bool = False) -> Tuple[bool, str]:
        """
        刪除案件（整合完整流程）

        Args:
            case_id: 案件ID
            delete_folder: 是否刪除資料夾
            delete_progress: 是否刪除進度資料
            force: 是否強制刪除

        Returns:
            (成功與否, 結果訊息)
        """
        try:
            print(f"🎯 ServicesController: 開始刪除案件 {case_id}")

            # 1. 取得案件資料用於通知
            case_data = None
            if self.case_service and hasattr(self.case_service, 'repository'):
                case_data = self.case_service.repository.get_case_by_id(case_id)

            # 2. 刪除案件資料
            if self.case_service:
                case_result = self.case_service.delete_case(case_id, delete_folder, force)
                if not case_result[0]:
                    return False, f"案件刪除失敗: {case_result[1]}"
            else:
                return False, "案件服務未可用"

            # 3. 發送通知
            if self.notification_service and case_data:
                self.notification_service.notify_case_deleted(case_data)

            print(f"✅ ServicesController: 案件刪除完成 {case_id}")
            return True, f"成功刪除案件: {case_id}"

        except Exception as e:
            error_msg = f"ServicesController 刪除案件失敗: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg

    # ==================== 資料匯入匯出統一介面 ====================

    def import_cases_from_excel(self, file_path: str, merge_strategy: str = 'skip_duplicates',
                               create_folders: bool = True, apply_templates: bool = False) -> Tuple[bool, Dict[str, Any]]:
        """
        從Excel匯入案件（整合完整流程）

        Args:
            file_path: Excel檔案路徑
            merge_strategy: 合併策略
            create_folders: 是否為匯入的案件建立資料夾
            apply_templates: 是否自動套用進度範本

        Returns:
            (成功與否, 詳細結果)
        """
        try:
            print(f"🎯 ServicesController: 開始從Excel匯入案件")

            if not self.import_export_service:
                return False, {'error': '匯入匯出服務未可用'}

            # 1. 匯入資料
            import_result = self.import_export_service.import_cases_from_excel(
                file_path, merge_strategy
            )

            if not import_result[0]:
                return import_result

            print(f"✅ ServicesController: Excel匯入完成")
            return import_result

        except Exception as e:
            error_msg = f"ServicesController Excel匯入失敗: {str(e)}"
            print(f"❌ {error_msg}")
            return False, {'error': error_msg}

    def export_cases_to_excel(self, cases = None, file_path: str = None,
                             include_progress: bool = True, include_metadata: bool = True) -> Tuple[bool, str]:
        """
        匯出案件到Excel（整合完整流程）

        Args:
            cases: 要匯出的案件列表，None表示所有案件
            file_path: 匯出檔案路徑
            include_progress: 是否包含進度資訊
            include_metadata: 是否包含元資料

        Returns:
            (成功與否, 檔案路徑或錯誤訊息)
        """
        try:
            print(f"🎯 ServicesController: 開始匯出案件到Excel")

            if not self.import_export_service:
                return False, '匯入匯出服務未可用'

            # 1. 取得案件資料（如果沒有指定）
            if cases is None and self.case_service and hasattr(self.case_service, 'repository'):
                cases = self.case_service.repository.get_all_cases()

            if not cases:
                return False, '沒有案件資料可匯出'

            # 2. 執行匯出
            export_result = self.import_export_service.export_cases_to_excel(
                cases, file_path, include_metadata
            )

            print(f"✅ ServicesController: Excel匯出完成")
            return export_result

        except Exception as e:
            error_msg = f"ServicesController Excel匯出失敗: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg

    # ==================== 系統狀態和維護 ====================

    def get_system_status(self) -> Dict[str, Any]:
        """取得系統狀態"""
        status = {
            'services_controller': 'active',
            'data_folder': self.data_folder,
            'services_status': {
                'case_service': self.case_service is not None,
                'validation_service': self.validation_service is not None,
                'folder_service': self.folder_service is not None,
                'notification_service': self.notification_service is not None,
                'import_export_service': self.import_export_service is not None,
                'progress_service': self.progress_service is not None,
            },
            'timestamp': datetime.now().isoformat()
        }
        return status

    def get_available_services(self) -> List[str]:
        """取得可用的服務列表"""
        services = []
        if self.case_service: services.append('案件服務')
        if self.validation_service: services.append('驗證服務')
        if self.folder_service: services.append('資料夾服務')
        if self.notification_service: services.append('通知服務')
        if self.import_export_service: services.append('匯入匯出服務')
        if self.progress_service: services.append('進度服務')
        return services

    def restart_services(self):
        """重新啟動所有服務"""
        try:
            print("🔄 正在重新啟動服務...")
            self._initialize_services()
            print("✅ 服務重新啟動完成")
            return True
        except Exception as e:
            print(f"❌ 服務重新啟動失敗: {e}")
            return False