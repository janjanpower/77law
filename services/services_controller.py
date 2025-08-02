#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
增強版 Services 層控制器
確保資料夾建立功能正常運作
檔案路徑: services/services_controller.py (覆蓋原版)
"""

from typing import List, Optional, Dict, Any, Tuple
from models.case_model import CaseData
from .case_service import CaseService
from .folder_service import FolderService
from .import_export_service import ImportExportService
from .notification_service import NotificationService
from .validation_service import ValidationService
from .progress_service import ProgressService
import os


class ServicesController:
    """Services 層統一控制器 - 增強版"""

    def __init__(self, data_folder: str, data_file: str = None):
        """
        初始化服務控制器

        Args:
            data_folder: 資料資料夾路徑
            data_file: 案件資料檔案路徑
        """
        self.data_folder = data_folder
        self.data_file = data_file or os.path.join(data_folder, "cases.json")

        # 初始化所有服務
        self._initialize_services()

        print("✅ ServicesController 增強版初始化完成")

    def _initialize_services(self):
        """初始化所有服務"""
        try:
            # 1. 驗證服務（最基礎，其他服務可能會用到）
            self.validation_service = ValidationService()
            print("✅ ValidationService 已初始化")

            # 2. 通知服務（獨立服務）
            self.notification_service = NotificationService()
            print("✅ NotificationService 已初始化")

            # 3. 資料夾服務（依賴驗證服務）
            self.folder_service = FolderService(self.data_folder)
            print("✅ FolderService 已初始化")

            # 4. 匯入匯出服務（依賴驗證和通知服務）
            self.import_export_service = ImportExportService(self.data_folder)
            print("✅ ImportExportService 已初始化")

            # 5. 進度服務（依賴資料夾和通知服務）
            self.progress_service = ProgressService(self.data_folder)
            print("✅ ProgressService 已初始化")

            # 6. 案件服務（核心服務，依賴其他所有服務）
            self.case_service = CaseService(self.data_folder, self.data_file)
            print("✅ CaseService 已初始化")

        except Exception as e:
            print(f"❌ 服務初始化失敗: {e}")
            raise

    # ==================== 增強版案件管理介面 ====================

    def create_case(self, case_data: CaseData, create_folder: bool = True,
                   apply_template: str = None) -> Tuple[bool, str]:
        """
        建立案件（增強版 - 確保資料夾建立）

        Args:
            case_data: 案件資料
            create_folder: 是否建立資料夾
            apply_template: 套用的進度範本名稱

        Returns:
            (成功與否, 結果訊息)
        """
        try:
            print(f"🎯 ServicesController: 開始建立案件 {case_data.client}，建立資料夾: {create_folder}")

            # 1. 先建立案件資料
            case_result = self.case_service.create_case(case_data, False)  # 先不在 CaseService 中建立資料夾
            if not case_result[0]:
                print(f"❌ ServicesController: 案件資料建立失敗 - {case_result[1]}")
                return case_result

            print(f"✅ ServicesController: 案件資料已建立")

            # 2. 強制建立資料夾（如果需要）
            folder_created = False
            if create_folder:
                try:
                    print(f"🏗️ ServicesController: 開始建立案件資料夾...")

                    # 使用 folder_service 直接建立資料夾
                    folder_result = self.folder_service.create_case_folder_structure(case_data)

                    if folder_result[0]:
                        folder_created = True
                        print(f"✅ ServicesController: 資料夾建立成功 - {folder_result[1]}")
                    else:
                        print(f"⚠️ ServicesController: 資料夾建立失敗 - {folder_result[1]}")
                        # 資料夾建立失敗不影響案件建立成功

                except Exception as folder_error:
                    print(f"❌ ServicesController: 資料夾建立異常 - {folder_error}")
                    # 記錄錯誤但不中斷流程

            # 3. 套用進度範本（如果指定）
            template_applied = False
            if apply_template:
                try:
                    template_result = self.progress_service.apply_progress_template(
                        case_data.case_id, apply_template
                    )
                    if template_result[0]:
                        template_applied = True
                        print(f"✅ ServicesController: 成功套用進度範本: {apply_template}")
                    else:
                        print(f"⚠️ ServicesController: 套用進度範本失敗 - {template_result[1]}")
                except Exception as template_error:
                    print(f"❌ ServicesController: 套用進度範本異常 - {template_error}")

            # 4. 產生結果訊息
            success_message = f"成功建立案件: {case_data.client}"

            if create_folder and folder_created:
                success_message += " (含資料夾結構)"
            elif create_folder and not folder_created:
                success_message += " (資料夾建立失敗)"

            if apply_template and template_applied:
                success_message += f" (已套用範本: {apply_template})"

            print(f"✅ ServicesController: 案件建立完成 - {success_message}")
            return True, success_message

        except Exception as e:
            error_msg = f"ServicesController 建立案件失敗: {str(e)}"
            print(f"❌ {error_msg}")

            # 嘗試清理已建立的資料
            try:
                if hasattr(case_data, 'case_id') and case_data.case_id:
                    self.case_service.repository.delete_case(case_data.case_id)
                    print(f"🧹 已清理失敗案件的資料: {case_data.case_id}")
            except:
                pass

            return False, error_msg

    def verify_case_creation(self, case_data: CaseData) -> Dict[str, Any]:
        """
        驗證案件建立結果

        Args:
            case_data: 案件資料

        Returns:
            Dict: 驗證結果
        """
        verification = {
            'case_exists': False,
            'folder_exists': False,
            'folder_structure_complete': False,
            'case_id': case_data.case_id,
            'client': case_data.client,
            'issues': []
        }

        try:
            # 1. 檢查案件資料是否存在
            existing_case = self.case_service.repository.get_case_by_id(case_data.case_id)
            verification['case_exists'] = existing_case is not None

            if not verification['case_exists']:
                verification['issues'].append("案件資料不存在於資料庫中")

            # 2. 檢查資料夾是否存在
            folder_path = self.folder_service.get_case_folder_path(case_data)
            if folder_path and os.path.exists(folder_path):
                verification['folder_exists'] = True

                # 3. 檢查資料夾結構
                required_subfolders = ['案件資訊', '進度追蹤', '狀紙']
                missing_folders = []

                for subfolder in required_subfolders:
                    subfolder_path = os.path.join(folder_path, subfolder)
                    if not os.path.exists(subfolder_path):
                        missing_folders.append(subfolder)

                verification['folder_structure_complete'] = len(missing_folders) == 0

                if missing_folders:
                    verification['issues'].append(f"缺少子資料夾: {', '.join(missing_folders)}")
            else:
                verification['issues'].append("案件資料夾不存在")

            return verification

        except Exception as e:
            verification['issues'].append(f"驗證過程異常: {str(e)}")
            return verification

    def repair_case_structure(self, case_data: CaseData) -> Tuple[bool, str]:
        """
        修復案件結構

        Args:
            case_data: 案件資料

        Returns:
            Tuple[bool, str]: (是否成功, 結果訊息)
        """
        try:
            print(f"🔧 ServicesController: 開始修復案件結構 {case_data.client}")

            # 1. 驗證當前狀態
            verification = self.verify_case_creation(case_data)

            repairs_needed = []
            repairs_completed = []

            # 2. 修復案件資料（如果需要）
            if not verification['case_exists']:
                repairs_needed.append("重建案件資料")
                try:
                    case_result = self.case_service.create_case(case_data, False)
                    if case_result[0]:
                        repairs_completed.append("重建案件資料")
                    else:
                        return False, f"無法重建案件資料: {case_result[1]}"
                except Exception as e:
                    return False, f"重建案件資料失敗: {str(e)}"

            # 3. 修復資料夾結構（如果需要）
            if not verification['folder_exists'] or not verification['folder_structure_complete']:
                repairs_needed.append("重建資料夾結構")
                try:
                    folder_result = self.folder_service.create_case_folder_structure(case_data, force_recreate=True)
                    if folder_result[0]:
                        repairs_completed.append("重建資料夾結構")
                    else:
                        repairs_needed.append(f"資料夾修復失敗: {folder_result[1]}")
                except Exception as e:
                    repairs_needed.append(f"資料夾修復異常: {str(e)}")

            # 4. 產生結果
            if len(repairs_completed) == len(repairs_needed):
                message = f"修復完成 - 已修復: {', '.join(repairs_completed)}"
                print(f"✅ ServicesController: {message}")
                return True, message
            else:
                failed_repairs = [repair for repair in repairs_needed if repair not in repairs_completed]
                message = f"部分修復失敗 - 成功: {', '.join(repairs_completed)}, 失敗: {', '.join(failed_repairs)}"
                print(f"⚠️ ServicesController: {message}")
                return False, message

        except Exception as e:
            error_msg = f"修復案件結構失敗: {str(e)}"
            print(f"❌ ServicesController: {error_msg}")
            return False, error_msg

    def update_case(self, case_data: CaseData, update_folder: bool = False,
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

            # 1. 更新案件資料
            case_result = self.case_service.update_case(case_data, update_folder)
            if not case_result[0]:
                return case_result

            # 2. 同步進度資訊（如果需要）
            if sync_progress:
                # 這裡可以添加進度同步邏輯
                pass

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

            # 1. 刪除進度資料（如果需要）
            if delete_progress:
                if case_id in self.progress_service.progress_data:
                    del self.progress_service.progress_data[case_id]
                    self.progress_service._save_progress_data()
                    print(f"✅ 已刪除進度資料: {case_id}")

            # 2. 刪除案件資料
            case_result = self.case_service.delete_case(case_id)
            if not case_result[0]:
                return case_result

            # 3. 刪除資料夾（如果需要）
            if delete_folder:
                try:
                    case_data = self.case_service.repository.get_case_by_id(case_id)
                    if case_data:
                        folder_path = self.folder_service.get_case_folder_path(case_data)
                        if folder_path and os.path.exists(folder_path):
                            import shutil
                            shutil.rmtree(folder_path)
                            print(f"✅ 已刪除案件資料夾: {folder_path}")
                except Exception as e:
                    print(f"⚠️ 刪除資料夾失敗: {str(e)}")

            print(f"✅ ServicesController: 案件刪除完成 {case_id}")
            return True, f"成功刪除案件: {case_id}"

        except Exception as e:
            error_msg = f"ServicesController 刪除案件失敗: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg

    # ==================== 診斷和維護工具 ====================

    def diagnose_system_health(self) -> Dict[str, Any]:
        """診斷系統健康狀態"""
        health_report = {
            'overall_status': 'healthy',
            'services_status': {},
            'data_integrity': {},
            'folder_integrity': {},
            'issues': [],
            'recommendations': []
        }

        try:
            # 檢查各服務狀態
            services = ['case_service', 'folder_service', 'progress_service',
                       'validation_service', 'notification_service', 'import_export_service']

            for service_name in services:
                if hasattr(self, service_name):
                    health_report['services_status'][service_name] = 'available'
                else:
                    health_report['services_status'][service_name] = 'missing'
                    health_report['issues'].append(f"{service_name} 不可用")

            # 檢查資料完整性
            try:
                all_cases = self.case_service.repository.get_all_cases()
                health_report['data_integrity']['total_cases'] = len(all_cases)
                health_report['data_integrity']['status'] = 'ok'
            except Exception as e:
                health_report['data_integrity']['status'] = 'error'
                health_report['data_integrity']['error'] = str(e)
                health_report['issues'].append(f"資料完整性問題: {str(e)}")

            # 檢查資料夾完整性
            try:
                folder_issues = 0
                for case in all_cases:
                    verification = self.verify_case_creation(case)
                    if not verification['folder_exists'] or not verification['folder_structure_complete']:
                        folder_issues += 1

                health_report['folder_integrity']['cases_with_issues'] = folder_issues
                health_report['folder_integrity']['status'] = 'ok' if folder_issues == 0 else 'issues'

                if folder_issues > 0:
                    health_report['issues'].append(f"{folder_issues} 個案件的資料夾結構有問題")
                    health_report['recommendations'].append("建議執行批次修復資料夾結構")

            except Exception as e:
                health_report['folder_integrity']['status'] = 'error'
                health_report['folder_integrity']['error'] = str(e)

            # 設定整體狀態
            if health_report['issues']:
                health_report['overall_status'] = 'issues' if len(health_report['issues']) < 3 else 'critical'

        except Exception as e:
            health_report['overall_status'] = 'error'
            health_report['issues'].append(f"診斷過程異常: {str(e)}")

        return health_report

    def batch_repair_folders(self) -> Dict[str, Any]:
        """批次修復所有案件的資料夾結構"""
        repair_result = {
            'total_processed': 0,
            'successful_repairs': 0,
            'failed_repairs': 0,
            'skipped': 0,
            'details': []
        }

        try:
            all_cases = self.case_service.repository.get_all_cases()
            repair_result['total_processed'] = len(all_cases)

            for case in all_cases:
                try:
                    verification = self.verify_case_creation(case)

                    if verification['folder_exists'] and verification['folder_structure_complete']:
                        repair_result['skipped'] += 1
                        repair_result['details'].append(f"跳過 {case.client}: 結構完整")
                        continue

                    # 需要修復
                    repair_success, repair_message = self.repair_case_structure(case)

                    if repair_success:
                        repair_result['successful_repairs'] += 1
                        repair_result['details'].append(f"修復成功 {case.client}: {repair_message}")
                    else:
                        repair_result['failed_repairs'] += 1
                        repair_result['details'].append(f"修復失敗 {case.client}: {repair_message}")

                except Exception as e:
                    repair_result['failed_repairs'] += 1
                    repair_result['details'].append(f"修復異常 {case.client}: {str(e)}")

        except Exception as e:
            repair_result['details'].append(f"批次修復過程異常: {str(e)}")

        return repair_result
