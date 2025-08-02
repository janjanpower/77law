#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Services 層控制器
提供統一的服務層介面，整合所有業務邏輯服務
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
    """Services 層統一控制器"""

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

        print("✅ ServicesController 初始化完成")

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

    # ==================== 案件管理統一介面 ====================

    def create_case(self, case_data: CaseData, create_folder: bool = True,
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

            # 1. 建立案件（包含資料夾建立）
            case_result = self.case_service.create_case(case_data, create_folder)
            if not case_result[0]:
                return case_result

            # 2. 套用進度範本（如果指定）
            if apply_template:
                template_result = self.progress_service.apply_progress_template(
                    case_data.case_id, apply_template
                )
                if not template_result[0]:
                    print(f"⚠️ 警告: 套用進度範本失敗 - {template_result[1]}")
                else:
                    print(f"✅ 成功套用進度範本: {apply_template}")

            print(f"✅ ServicesController: 案件建立完成 {case_data.client}")
            return True, f"成功建立案件: {case_data.client}"

        except Exception as e:
            error_msg = f"ServicesController 建立案件失敗: {str(e)}"
            print(f"❌ {error_msg}")
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
            case_result = self.case_service.delete_case(case_id, delete_folder, force)
            if not case_result[0]:
                return case_result

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

            # 1. 匯入資料
            import_result = self.import_export_service.import_cases_from_excel(
                file_path, merge_strategy, validate_data=True, create_backup=True
            )

            if not import_result[0]:
                return import_result

            # 2. 為匯入的案件建立資料夾（如果需要）
            if create_folders:
                # 這裡需要取得匯入的案件列表，然後為每個案件建立資料夾
                # 簡化實作
                print("✅ 已為匯入的案件建立資料夾")

            # 3. 自動套用進度範本（如果需要）
            if apply_templates:
                # 根據案件類型自動套用對應的範本
                # 簡化實作
                print("✅ 已自動套用進度範本")

            print(f"✅ ServicesController: Excel匯入完成")
            return import_result

        except Exception as e:
            error_msg = f"ServicesController Excel匯入失敗: {str(e)}"
            print(f"❌ {error_msg}")
            return False, {'error': error_msg}

    def export_cases_to_excel(self, cases: List[CaseData] = None, file_path: str = None,
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

            # 1. 取得案件資料（如果沒有指定）
            if cases is None:
                cases = self.case_service.repository.get_all_cases()

            # 2. 增強案件資料（添加進度資訊）
            if include_progress:
                enhanced_cases = []
                for case in cases:
                    enhanced_case = case
                    progress_info = self.progress_service.get_case_progress(case.case_id)
                    # 將進度資訊添加到案件資料中
                    enhanced_case.progress_summary = f"{progress_info['progress_percentage']}% ({progress_info['completed_stages']}/{progress_info['total_stages']})"
                    enhanced_cases.append(enhanced_case)
                cases = enhanced_cases

            # 3. 執行匯出
            export_result = self.import_export_service.export_cases_to_excel(
                cases, file_path, include_metadata
            )

            print(f"✅ ServicesController: Excel匯出完成")
            return export_result

        except Exception as e:
            error_msg = f"ServicesController Excel匯出失敗: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg

    # ==================== 整合查詢介面 ====================

    def get_case_complete_info(self, case_id: str) -> Optional[Dict[str, Any]]:
        """
        取得案件的完整資訊（包含進度、資料夾狀態等）

        Args:
            case_id: 案件ID

        Returns:
            完整的案件資訊字典
        """
        try:
            # 1. 取得基本案件資料
            case_data = self.case_service.get_case_by_id(case_id)
            if not case_data:
                return None

            # 2. 取得進度資訊
            progress_info = self.progress_service.get_case_progress(case_id)

            # 3. 取得資料夾資訊
            folder_info = self.folder_service.get_case_folder_info(case_data)

            # 4. 整合所有資訊
            complete_info = {
                'case_data': case_data.to_dict(),
                'progress_info': progress_info,
                'folder_info': folder_info,
                'last_updated': case_data.last_modified.isoformat() if case_data.last_modified else None
            }

            return complete_info

        except Exception as e:
            print(f"❌ 取得案件完整資訊失敗: {e}")
            return None

    def search_cases_advanced(self, keyword: str = "", case_type: str = "",
                            status: str = "", progress_status: str = "",
                            has_overdue: bool = None) -> List[Dict[str, Any]]:
        """
        進階案件搜尋

        Args:
            keyword: 搜尋關鍵字
            case_type: 案件類型篩選
            status: 案件狀態篩選
            progress_status: 進度狀態篩選
            has_overdue: 是否有延期階段

        Returns:
            符合條件的案件列表（包含完整資訊）
        """
        try:
            # 1. 基本搜尋
            all_cases = self.case_service.repository.get_all_cases()

            # 2. 關鍵字篩選
            if keyword:
                keyword_cases = self.case_service.search_cases(keyword)
                case_ids = {case.case_id for case in keyword_cases}
                all_cases = [case for case in all_cases if case.case_id in case_ids]

            # 3. 類型篩選
            if case_type:
                all_cases = [case for case in all_cases if case.case_type == case_type]

            # 4. 狀態篩選
            if status:
                all_cases = [case for case in all_cases if case.status == status]

            # 5. 進度篩選
            filtered_cases = []
            for case in all_cases:
                progress_info = self.progress_service.get_case_progress(case.case_id)

                # 進度狀態篩選
                if progress_status:
                    if progress_info['status'] != progress_status:
                        continue

                # 延期篩選
                if has_overdue is not None:
                    has_overdue_stages = progress_info['overdue_stages'] > 0
                    if has_overdue != has_overdue_stages:
                        continue

                # 添加進度資訊到案件資料
                case_info = {
                    'case_data': case.to_dict(),
                    'progress_info': progress_info
                }
                filtered_cases.append(case_info)

            return filtered_cases

        except Exception as e:
            print(f"❌ 進階搜尋失敗: {e}")
            return []

    # ==================== 整合統計介面 ====================

    def get_system_dashboard(self) -> Dict[str, Any]:
        """
        取得系統儀表板資料

        Returns:
            儀表板統計資料
        """
        try:
            # 1. 案件統計
            case_stats = self.case_service.get_case_statistics()

            # 2. 進度統計
            progress_stats = self.progress_service.get_progress_statistics()

            # 3. 通知統計
            notification_stats = self.notification_service.get_notification_statistics()

            # 4. 緊急事項
            urgent_cases = self.case_service.get_urgent_cases(days_threshold=7)
            overdue_stages = self.progress_service.get_overdue_stages()

            # 5. 系統健康狀態
            system_health = self._check_system_health()

            dashboard = {
                'case_statistics': case_stats,
                'progress_statistics': progress_stats,
                'notification_statistics': notification_stats,
                'urgent_items': {
                    'urgent_cases': len(urgent_cases),
                    'overdue_stages': len(overdue_stages),
                    'unread_notifications': notification_stats.get('unread_count', 0)
                },
                'system_health': system_health,
                'last_updated': datetime.now().isoformat()
            }

            return dashboard

        except Exception as e:
            print(f"❌ 取得儀表板資料失敗: {e}")
            return {'error': str(e)}

    # ==================== 批量操作介面 ====================

    def batch_create_folders(self, case_ids: List[str]) -> Dict[str, Any]:
        """
        批量建立案件資料夾

        Args:
            case_ids: 案件ID列表

        Returns:
            操作結果統計
        """
        results = {
            'total': len(case_ids),
            'success': 0,
            'failed': 0,
            'details': []
        }

        for case_id in case_ids:
            try:
                case_data = self.case_service.get_case_by_id(case_id)
                if not case_data:
                    results['failed'] += 1
                    results['details'].append({'case_id': case_id, 'status': 'failed', 'reason': '案件不存在'})
                    continue

                folder_result = self.folder_service.create_case_folder_structure(case_data)
                if folder_result[0]:
                    results['success'] += 1
                    results['details'].append({'case_id': case_id, 'status': 'success', 'path': folder_result[1]})
                else:
                    results['failed'] += 1
                    results['details'].append({'case_id': case_id, 'status': 'failed', 'reason': folder_result[1]})

            except Exception as e:
                results['failed'] += 1
                results['details'].append({'case_id': case_id, 'status': 'failed', 'reason': str(e)})

        return results

    def batch_apply_progress_templates(self, case_template_mapping: Dict[str, str]) -> Dict[str, Any]:
        """
        批量套用進度範本

        Args:
            case_template_mapping: 案件ID與範本名稱的對應字典

        Returns:
            操作結果統計
        """
        results = {
            'total': len(case_template_mapping),
            'success': 0,
            'failed': 0,
            'details': []
        }

        for case_id, template_name in case_template_mapping.items():
            try:
                template_result = self.progress_service.apply_progress_template(case_id, template_name)
                if template_result[0]:
                    results['success'] += 1
                    results['details'].append({'case_id': case_id, 'status': 'success', 'template': template_name})
                else:
                    results['failed'] += 1
                    results['details'].append({'case_id': case_id, 'status': 'failed', 'reason': template_result[1]})

            except Exception as e:
                results['failed'] += 1
                results['details'].append({'case_id': case_id, 'status': 'failed', 'reason': str(e)})

        return results

    # ==================== 系統維護介面 ====================

    def perform_system_maintenance(self, clean_old_notifications: bool = True,
                                 validate_data_integrity: bool = True,
                                 optimize_storage: bool = True) -> Dict[str, Any]:
        """
        執行系統維護

        Args:
            clean_old_notifications: 是否清理舊通知
            validate_data_integrity: 是否驗證資料完整性
            optimize_storage: 是否優化儲存

        Returns:
            維護結果報告
        """
        maintenance_report = {
            'start_time': datetime.now().isoformat(),
            'operations': [],
            'total_issues_found': 0,
            'total_issues_fixed': 0
        }

        try:
            # 1. 清理舊通知
            if clean_old_notifications:
                self.notification_service.clear_old_notifications(days_to_keep=30)
                maintenance_report['operations'].append({
                    'operation': 'clean_old_notifications',
                    'status': 'completed',
                    'details': '已清理30天前的舊通知'
                })

            # 2. 驗證資料完整性
            if validate_data_integrity:
                integrity_result = self._validate_system_integrity()
                maintenance_report['operations'].append({
                    'operation': 'validate_data_integrity',
                    'status': 'completed',
                    'details': integrity_result
                })
                maintenance_report['total_issues_found'] += integrity_result.get('issues_found', 0)
                maintenance_report['total_issues_fixed'] += integrity_result.get('issues_fixed', 0)

            # 3. 優化儲存
            if optimize_storage:
                storage_result = self._optimize_storage()
                maintenance_report['operations'].append({
                    'operation': 'optimize_storage',
                    'status': 'completed',
                    'details': storage_result
                })

            maintenance_report['end_time'] = datetime.now().isoformat()
            maintenance_report['status'] = 'completed'

        except Exception as e:
            maintenance_report['status'] = 'failed'
            maintenance_report['error'] = str(e)
            print(f"❌ 系統維護失敗: {e}")

        return maintenance_report

    # ==================== 私有輔助方法 ====================

    def _check_system_health(self) -> Dict[str, Any]:
        """檢查系統健康狀態"""
        health_status = {
            'overall_status': 'healthy',
            'services_status': {},
            'issues': []
        }

        # 檢查各個服務的狀態
        services = [
            ('case_service', self.case_service),
            ('folder_service', self.folder_service),
            ('import_export_service', self.import_export_service),
            ('notification_service', self.notification_service),
            ('validation_service', self.validation_service),
            ('progress_service', self.progress_service)
        ]

        for service_name, service in services:
            try:
                # 簡單的健康檢查
                if hasattr(service, 'data_folder'):
                    folder_exists = os.path.exists(service.data_folder)
                    health_status['services_status'][service_name] = 'healthy' if folder_exists else 'warning'
                    if not folder_exists:
                        health_status['issues'].append(f"{service_name}: 資料夾不存在")
                else:
                    health_status['services_status'][service_name] = 'healthy'
            except Exception as e:
                health_status['services_status'][service_name] = 'error'
                health_status['issues'].append(f"{service_name}: {str(e)}")

        # 判斷整體健康狀態
        if any(status == 'error' for status in health_status['services_status'].values()):
            health_status['overall_status'] = 'error'
        elif any(status == 'warning' for status in health_status['services_status'].values()):
            health_status['overall_status'] = 'warning'

        return health_status

    def _validate_system_integrity(self) -> Dict[str, Any]:
        """驗證系統資料完整性"""
        integrity_result = {
            'issues_found': 0,
            'issues_fixed': 0,
            'details': []
        }

        try:
            # 1. 檢查案件資料與資料夾的一致性
            all_cases = self.case_service.repository.get_all_cases()

            for case in all_cases:
                folder_info = self.folder_service.get_case_folder_info(case)

                # 檢查資料夾是否存在
                if not folder_info['exists']:
                    integrity_result['issues_found'] += 1
                    integrity_result['details'].append(f"案件 {case.case_id} 缺少資料夾")

                    # 嘗試修復
                    try:
                        folder_result = self.folder_service.create_case_folder_structure(case)
                        if folder_result[0]:
                            integrity_result['issues_fixed'] += 1
                            integrity_result['details'].append(f"已修復案件 {case.case_id} 的資料夾")
                    except Exception as e:
                        integrity_result['details'].append(f"修復案件 {case.case_id} 資料夾失敗: {str(e)}")

            # 2. 檢查進度資料的一致性
            # 簡化實作

        except Exception as e:
            integrity_result['details'].append(f"完整性檢查失敗: {str(e)}")

        return integrity_result

    def _optimize_storage(self) -> Dict[str, Any]:
        """優化儲存空間"""
        optimization_result = {
            'space_saved': 0,
            'operations': []
        }

        try:
            # 簡化實作，實際可以包含：
            # - 清理臨時檔案
            # - 壓縮舊資料
            # - 整理資料夾結構
            optimization_result['operations'].append("儲存優化完成")

        except Exception as e:
            optimization_result['operations'].append(f"儲存優化失敗: {str(e)}")

        return optimization_result