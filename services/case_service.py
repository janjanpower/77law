#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
案件業務邏輯服務 - 更新版本
使用分離的 Repository 層，專責處理業務邏輯
"""

from typing import List, Optional, Dict, Any, Tuple
from models.case_model import CaseData
from repositories.case_repository import CaseRepository
from repositories.progress_repository import ProgressRepository
import uuid
import os
from datetime import datetime


class CaseService:
    """案件業務邏輯服務 - 使用 Repository 架構"""

    def __init__(self, data_folder: str, data_file: str = None, progress_file: str = None):
        """
        初始化案件服務

        Args:
            data_folder: 資料資料夾路徑
            data_file: 案件資料檔案路徑
            progress_file: 進度資料檔案路徑
        """
        self.data_folder = data_folder
        self.data_file = data_file or os.path.join(data_folder, "cases.json")
        self.progress_file = progress_file or os.path.join(data_folder, "progress_data.json")

        # 初始化資料存取層
        self.repository = CaseRepository(self.data_file)
        self.progress_repository = ProgressRepository(data_folder, self.progress_file)

        # 延遲初始化其他服務以避免循環依賴
        self.validation_service = None
        self.folder_service = None
        self.notification_service = None

        print("✅ CaseService 初始化完成 (使用 Repository 架構)")

    def _get_validation_service(self):
        """延遲取得驗證服務"""
        if self.validation_service is None:
            from services.validation_service import ValidationService
            self.validation_service = ValidationService()
        return self.validation_service

    def _get_folder_service(self):
        """延遲取得資料夾服務"""
        if self.folder_service is None:
            from services.folder_service import FolderService
            self.folder_service = FolderService(self.data_folder)
        return self.folder_service

    def _get_notification_service(self):
        """延遲取得通知服務"""
        if self.notification_service is None:
            from services.notification_service import NotificationService
            self.notification_service = NotificationService()
        return self.notification_service

    # ==================== 案件 CRUD 操作 ====================

    def create_case(self, case_data: CaseData, create_folder: bool = True,
                   apply_template: str = None) -> Tuple[bool, str]:
        """
        建立案件（完整業務流程）

        Args:
            case_data: 案件資料
            create_folder: 是否建立資料夾
            apply_template: 套用的進度範本名稱

        Returns:
            (成功與否, 訊息)
        """
        try:
            print(f"🏗️ 開始建立案件: {case_data.client}")

            # 1. 業務驗證
            validation_service = self._get_validation_service()
            validation_result = validation_service.validate_case_data(case_data)
            if not validation_result[0]:
                return False, f"案件資料驗證失敗: {validation_result[1]}"

            # 2. 檢查重複
            if self.is_case_duplicate(case_data):
                return False, f"案件ID已存在: {case_data.case_id}"

            # 3. 生成案件ID（如果沒有）
            if not case_data.case_id:
                case_data.case_id = self.generate_case_id(case_data)

            # 4. 設定預設值
            self._set_case_defaults(case_data)

            # 5. 儲存到資料庫
            save_result = self.repository.create_case(case_data)
            if not save_result:
                return False, "案件資料儲存失敗"

            # 6. 建立資料夾結構（如果需要）
            if create_folder:
                folder_service = self._get_folder_service()
                folder_result = folder_service.create_case_folder_structure(case_data)
                if not folder_result[0]:
                    print(f"⚠️ 警告: 資料夾建立失敗 - {folder_result[1]}")

            # 7. 套用進度範本（如果指定）
            if apply_template:
                template_result = self._apply_progress_template(case_data.case_id, apply_template)
                if not template_result[0]:
                    print(f"⚠️ 警告: 進度範本套用失敗 - {template_result[1]}")

            # 8. 發送通知
            notification_service = self._get_notification_service()
            notification_service.notify_case_created(case_data)

            print(f"✅ 成功建立案件: {case_data.case_id}")
            return True, f"成功建立案件: {case_data.client}"

        except Exception as e:
            error_msg = f"建立案件失敗: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg

    def update_case(self, case_data: CaseData, update_folder: bool = False,
                   sync_progress: bool = False) -> Tuple[bool, str]:
        """
        更新案件（完整業務流程）

        Args:
            case_data: 更新後的案件資料
            update_folder: 是否同步更新資料夾
            sync_progress: 是否同步進度資料

        Returns:
            (成功與否, 訊息)
        """
        try:
            print(f"🔄 開始更新案件: {case_data.case_id}")

            # 1. 檢查案件是否存在
            existing_case = self.repository.get_case_by_id(case_data.case_id)
            if not existing_case:
                return False, f"案件不存在: {case_data.case_id}"

            # 2. 業務驗證
            validation_result = self.validate_case_for_update(case_data, existing_case)
            if not validation_result[0]:
                return False, f"案件資料驗證失敗: {validation_result[1]}"

            # 3. 設定更新時間
            case_data.last_modified = datetime.now()

            # 4. 更新資料庫
            update_result = self.repository.update_case(case_data)
            if not update_result:
                return False, "案件資料更新失敗"

            # 5. 同步資料夾（如果需要）
            if update_folder:
                folder_service = self._get_folder_service()
                folder_sync_result = folder_service.sync_case_folder(existing_case, case_data)
                if not folder_sync_result[0]:
                    print(f"⚠️ 警告: 資料夾同步失敗 - {folder_sync_result[1]}")

            # 6. 同步進度資料（如果需要）
            if sync_progress:
                progress_sync_result = self._sync_case_progress(existing_case, case_data)
                if not progress_sync_result[0]:
                    print(f"⚠️ 警告: 進度同步失敗 - {progress_sync_result[1]}")

            # 7. 發送通知
            notification_service = self._get_notification_service()
            notification_service.notify_case_updated(case_data, existing_case)

            print(f"✅ 成功更新案件: {case_data.case_id}")
            return True, f"成功更新案件: {case_data.client}"

        except Exception as e:
            error_msg = f"更新案件失敗: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg

    def delete_case(self, case_id: str, delete_folder: bool = True,
                   delete_progress: bool = True, force: bool = False) -> Tuple[bool, str]:
        """
        刪除案件（完整業務流程）

        Args:
            case_id: 案件ID
            delete_folder: 是否刪除資料夾
            delete_progress: 是否刪除進度資料
            force: 是否強制刪除

        Returns:
            (成功與否, 訊息)
        """
        try:
            print(f"🗑️ 開始刪除案件: {case_id}")

            # 1. 檢查案件是否存在
            case_data = self.repository.get_case_by_id(case_id)
            if not case_data:
                return False, f"案件不存在: {case_id}"

            # 2. 業務驗證（檢查是否可以刪除）
            can_delete, reason = self.validate_case_for_deletion(case_data, force)
            if not can_delete:
                return False, f"無法刪除案件: {reason}"

            # 3. 刪除相關資料夾（如果需要）
            if delete_folder:
                folder_service = self._get_folder_service()
                folder_delete_result = folder_service.delete_case_folder(case_data)
                if not folder_delete_result[0]:
                    if not force:
                        return False, f"資料夾刪除失敗: {folder_delete_result[1]}"
                    else:
                        print(f"⚠️ 警告: 強制模式 - 忽略資料夾刪除失敗")

            # 4. 刪除進度資料（如果需要）
            if delete_progress:
                progress_delete_result = self.progress_repository.delete_case_progress(case_id)
                if not progress_delete_result:
                    if not force:
                        return False, "進度資料刪除失敗"
                    else:
                        print(f"⚠️ 警告: 強制模式 - 忽略進度刪除失敗")

            # 5. 刪除資料庫記錄
            delete_result = self.repository.delete_case(case_id)
            if not delete_result:
                return False, "案件資料刪除失敗"

            # 6. 發送通知
            notification_service = self._get_notification_service()
            notification_service.notify_case_deleted(case_data)

            print(f"✅ 成功刪除案件: {case_id}")
            return True, f"成功刪除案件: {case_data.client}"

        except Exception as e:
            error_msg = f"刪除案件失敗: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg

    # ==================== 查詢業務邏輯 ====================

    def get_case_by_id(self, case_id: str) -> Optional[CaseData]:
        """根據ID取得案件"""
        return self.repository.get_case_by_id(case_id)

    def get_cases_by_client(self, client_name: str) -> List[CaseData]:
        """根據當事人姓名取得案件列表"""
        return self.repository.get_cases_by_client(client_name)

    def get_cases_by_type(self, case_type: str) -> List[CaseData]:
        """根據案件類型取得案件列表"""
        return self.repository.get_cases_by_type(case_type)

    def get_cases_by_status(self, status: str) -> List[CaseData]:
        """根據案件狀態取得案件列表"""
        return self.repository.get_cases_by_status(status)

    def search_cases(self, keyword: str, fields: List[str] = None) -> List[CaseData]:
        """
        搜尋案件

        Args:
            keyword: 搜尋關鍵字
            fields: 要搜尋的欄位列表

        Returns:
            符合條件的案件列表
        """
        if fields is None:
            fields = ['client', 'case_type', 'case_id', 'notes']

        return self.repository.search_cases(keyword, fields)

    def get_urgent_cases(self, days_threshold: int = 7) -> List[CaseData]:
        """
        取得緊急案件（基於進度到期日）

        Args:
            days_threshold: 天數閾值

        Returns:
            緊急案件列表
        """
        try:
            # 取得即將到期的進度階段
            upcoming_stages = self.progress_repository.get_upcoming_stages(days_threshold)

            # 取得對應的案件
            urgent_case_ids = set()
            for stage in upcoming_stages:
                urgent_case_ids.add(stage.case_id)

            urgent_cases = []
            for case_id in urgent_case_ids:
                case_data = self.repository.get_case_by_id(case_id)
                if case_data:
                    urgent_cases.append(case_data)

            return urgent_cases

        except Exception as e:
            print(f"❌ 取得緊急案件失敗: {e}")
            return []

    def get_overdue_cases(self) -> List[CaseData]:
        """
        取得逾期案件

        Returns:
            逾期案件列表
        """
        try:
            # 取得逾期的進度階段
            overdue_stages = self.progress_repository.get_overdue_stages()

            # 取得對應的案件
            overdue_case_ids = set()
            for stage in overdue_stages:
                overdue_case_ids.add(stage.case_id)

            overdue_cases = []
            for case_id in overdue_case_ids:
                case_data = self.repository.get_case_by_id(case_id)
                if case_data:
                    overdue_cases.append(case_data)

            return overdue_cases

        except Exception as e:
            print(f"❌ 取得逾期案件失敗: {e}")
            return []

    # ==================== 業務驗證邏輯 ====================

    def validate_case_for_update(self, case_data: CaseData, existing_case: CaseData) -> Tuple[bool, str]:
        """驗證案件是否可以更新"""
        # 不能修改案件ID
        if case_data.case_id != existing_case.case_id:
            return False, "不能修改案件ID"

        return True, "驗證通過"

    def validate_case_for_deletion(self, case_data: CaseData, force: bool = False) -> Tuple[bool, str]:
        """驗證案件是否可以刪除"""
        if force:
            return True, "強制刪除模式"

        # 檢查是否有進行中的程序
        if hasattr(case_data, 'status') and case_data.status == "進行中":
            return False, "案件正在進行中，無法刪除"

        # 檢查是否有未完成的進度階段
        try:
            case_stages = self.progress_repository.get_case_progress_stages(case_data.case_id)
            in_progress_stages = [stage for stage in case_stages if stage.status in ['進行中', '待處理']]

            if in_progress_stages and not force:
                return False, f"案件有 {len(in_progress_stages)} 個未完成的進度階段，無法刪除"
        except Exception as e:
            print(f"⚠️ 檢查進度階段失敗: {e}")

        return True, "可以刪除"

    def is_case_duplicate(self, case_data: CaseData) -> bool:
        """檢查案件是否重複"""
        existing_case = self.repository.get_case_by_id(case_data.case_id)
        return existing_case is not None

    # ==================== 輔助方法 ====================

    def generate_case_id(self, case_data: CaseData) -> str:
        """生成案件ID"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        case_type_code = case_data.case_type[:2].upper() if case_data.case_type else "XX"
        unique_suffix = str(uuid.uuid4())[:8].upper()

        return f"{case_type_code}{timestamp}{unique_suffix}"

    def _set_case_defaults(self, case_data: CaseData):
        """設定案件預設值"""
        if not case_data.creation_date:
            case_data.creation_date = datetime.now()

        if not hasattr(case_data, 'status') or not case_data.status:
            case_data.status = "待處理"

        if not case_data.last_modified:
            case_data.last_modified = datetime.now()

    # ==================== 進度相關業務邏輯 ====================

    def _apply_progress_template(self, case_id: str, template_name: str) -> Tuple[bool, str]:
        """
        套用進度範本到案件

        Args:
            case_id: 案件ID
            template_name: 範本名稱

        Returns:
            (成功與否, 訊息)
        """
        try:
            # 這裡可以根據範本名稱載入預定義的進度階段
            # 暫時使用簡單的預設範本
            default_templates = {
                "民事訴訟": [
                    {"stage_name": "收案評估", "description": "評估案件可行性", "priority": "高", "due_days": 3},
                    {"stage_name": "起訴準備", "description": "準備起訴書狀", "priority": "高", "due_days": 14},
                    {"stage_name": "開庭準備", "description": "準備開庭資料", "priority": "一般", "due_days": 30},
                    {"stage_name": "結案處理", "description": "案件結案作業", "priority": "一般", "due_days": 60}
                ],
                "刑事辯護": [
                    {"stage_name": "案件分析", "description": "分析案件事實", "priority": "緊急", "due_days": 1},
                    {"stage_name": "證據蒐集", "description": "蒐集有利證據", "priority": "高", "due_days": 7},
                    {"stage_name": "辯護準備", "description": "準備辯護策略", "priority": "高", "due_days": 14},
                    {"stage_name": "出庭辯護", "description": "法庭辯護", "priority": "緊急", "due_days": 30}
                ]
            }

            template_stages = default_templates.get(template_name, [])
            if not template_stages:
                return False, f"找不到範本: {template_name}"

            result = self.progress_repository.create_stages_from_template(case_id, template_stages)

            if result['success_count'] > 0:
                return True, f"成功套用範本，建立了 {result['success_count']} 個進度階段"
            else:
                return False, f"套用範本失敗: {', '.join(result['errors'])}"

        except Exception as e:
            return False, f"套用進度範本失敗: {str(e)}"

    def _sync_case_progress(self, old_case: CaseData, new_case: CaseData) -> Tuple[bool, str]:
        """
        同步案件進度資料

        Args:
            old_case: 原始案件資料
            new_case: 更新後案件資料

        Returns:
            (成功與否, 訊息)
        """
        try:
            # 檢查是否需要同步
            if old_case.case_type == new_case.case_type:
                return True, "案件類型未變更，無需同步進度"

            # 如果案件類型改變，可以選擇保留現有進度或重新套用範本
            print(f"📝 案件類型從 {old_case.case_type} 變更為 {new_case.case_type}")

            # 這裡可以添加更複雜的同步邏輯
            return True, "進度同步完成"

        except Exception as e:
            return False, f"進度同步失敗: {str(e)}"

    def get_case_with_progress(self, case_id: str) -> Optional[Dict[str, Any]]:
        """
        取得案件及其進度資訊

        Args:
            case_id: 案件ID

        Returns:
            包含案件和進度資料的字典
        """
        try:
            case_data = self.repository.get_case_by_id(case_id)
            if not case_data:
                return None

            progress_summary = self.progress_repository.get_case_progress_summary(case_id)
            progress_stages = self.progress_repository.get_case_progress_stages(case_id)

            return {
                'case_data': case_data,
                'progress_summary': progress_summary,
                'progress_stages': progress_stages
            }

        except Exception as e:
            print(f"❌ 取得案件進度資訊失敗: {e}")
            return None

    # ==================== 統計和報告 ====================

    def get_case_statistics(self) -> Dict[str, Any]:
        """取得案件統計資訊"""
        try:
            all_cases = self.repository.get_all_cases()

            # 基本統計
            total_cases = len(all_cases)
            type_counts = self.repository.get_case_count_by_type()
            status_counts = self.repository.get_case_count_by_status()

            # 進度統計
            progress_stats = self.progress_repository.get_progress_statistics()
            overdue_stages = self.progress_repository.get_overdue_stages()

            # 綜合統計
            statistics = {
                'total_cases': total_cases,
                'case_by_type': type_counts,
                'case_by_status': status_counts,
                'progress_overview': {
                    'total_stages': progress_stats['total_stages'],
                    'completion_rate': progress_stats['completion_rate'],
                    'overdue_stages': len(overdue_stages)
                },
                'urgent_cases_count': len(self.get_urgent_cases()),
                'overdue_cases_count': len(self.get_overdue_cases())
            }

            return statistics

        except Exception as e:
            print(f"❌ 取得統計資訊失敗: {e}")
            return {}

    def get_workload_report(self) -> Dict[str, Any]:
        """取得工作負荷報告"""
        try:
            # 取得負責人工作負荷
            workload_stats = self.progress_repository.get_workload_by_assignee()

            # 取得案件分布
            all_cases = self.repository.get_all_cases()

            report = {
                'assignee_workload': workload_stats,
                'total_cases': len(all_cases),
                'cases_with_progress': len([case for case in all_cases
                                          if self.progress_repository.get_case_progress_stages(case.case_id)]),
                'generated_at': datetime.now().isoformat()
            }

            return report

        except Exception as e:
            print(f"❌ 取得工作負荷報告失敗: {e}")
            return {}

    # ==================== 批次操作 ====================

    def batch_update_cases(self, updates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        批次更新案件

        Args:
            updates: 更新資料列表

        Returns:
            批次更新結果
        """
        return self.repository.batch_update_cases(updates)

    def batch_assign_progress(self, case_ids: List[str], assignee: str) -> Dict[str, Any]:
        """
        批次指派案件進度

        Args:
            case_ids: 案件ID列表
            assignee: 負責人

        Returns:
            批次指派結果
        """
        try:
            result = {
                'success_count': 0,
                'failed_count': 0,
                'errors': []
            }

            for case_id in case_ids:
                # 取得案件的所有進度階段
                stages = self.progress_repository.get_case_progress_stages(case_id)
                stage_ids = [stage.stage_id for stage in stages if stage.status != '已完成']

                if stage_ids:
                    assign_result = self.progress_repository.batch_assign_stages(stage_ids, assignee)
                    result['success_count'] += assign_result['success_count']
                    result['failed_count'] += assign_result['failed_count']
                    result['errors'].extend(assign_result['errors'])
                else:
                    result['failed_count'] += 1
                    result['errors'].append(f"案件 {case_id} 沒有可指派的進度階段")

            return result

        except Exception as e:
            return {
                'success_count': 0,
                'failed_count': len(case_ids),
                'errors': [f"批次指派失敗: {str(e)}"]
            }

    # ==================== 資料完整性檢查 ====================

    def validate_data_integrity(self) -> Dict[str, Any]:
        """驗證資料完整性"""
        try:
            # 驗證案件資料
            case_validation = self.repository.validate_data_integrity()

            # 驗證進度資料
            progress_validation = self.progress_repository.validate_progress_integrity()

            # 檢查案件與進度的關聯性
            orphaned_progress = []
            all_cases = self.repository.get_all_cases()
            case_ids = set(case.case_id for case in all_cases)

            all_stages = self.progress_repository.get_all_progress_stages()
            for stage in all_stages:
                if stage.case_id not in case_ids:
                    orphaned_progress.append(stage.stage_id)

            overall_validation = {
                'is_valid': case_validation['is_valid'] and progress_validation['is_valid'] and len(orphaned_progress) == 0,
                'case_validation': case_validation,
                'progress_validation': progress_validation,
                'orphaned_progress_stages': orphaned_progress,
                'total_issues': (len(case_validation.get('duplicates', [])) +
                               len(case_validation.get('missing_fields', [])) +
                               len(progress_validation.get('duplicate_ids', [])) +
                               len(progress_validation.get('missing_fields', [])) +
                               len(orphaned_progress))
            }

            return overall_validation

        except Exception as e:
            return {
                'is_valid': False,
                'error': str(e),
                'total_issues': -1
            }

    def cleanup_orphaned_data(self) -> Dict[str, int]:
        """清理孤立資料"""
        try:
            result = {
                'cleaned_progress_stages': 0,
                'cleaned_case_metadata': 0
            }

            # 清理孤立的進度階段
            all_cases = self.repository.get_all_cases()
            case_ids = set(case.case_id for case in all_cases)

            all_stages = self.progress_repository.get_all_progress_stages()
            valid_stages = []
            cleaned_progress = 0

            for stage in all_stages:
                if stage.case_id in case_ids:
                    valid_stages.append(stage)
                else:
                    print(f"🧹 清理孤立進度階段: {stage.stage_id}")
                    cleaned_progress += 1

            # 更新進度資料
            self.progress_repository.progress_stages = valid_stages
            self.progress_repository._save_progress_data()

            result['cleaned_progress_stages'] = cleaned_progress

            print(f"✅ 資料清理完成，清理了 {cleaned_progress} 個孤立進度階段")
            return result

        except Exception as e:
            print(f"❌ 資料清理失敗: {e}")
            return {'error': str(e)}

    # ==================== 匯出功能 ====================

    def export_case_data(self, export_path: str, include_progress: bool = True) -> bool:
        """
        匯出案件資料

        Args:
            export_path: 匯出檔案路徑
            include_progress: 是否包含進度資料

        Returns:
            匯出是否成功
        """
        try:
            all_cases = self.repository.get_all_cases()

            export_data = {
                'export_time': datetime.now().isoformat(),
                'total_cases': len(all_cases),
                'include_progress': include_progress,
                'cases': []
            }

            for case in all_cases:
                case_export = case.to_dict() if hasattr(case, 'to_dict') else case.__dict__

                if include_progress:
                    progress_summary = self.progress_repository.get_case_progress_summary(case.case_id)
                    progress_stages = self.progress_repository.get_case_progress_stages(case.case_id)

                    case_export['progress_summary'] = progress_summary
                    case_export['progress_stages'] = [stage.to_dict() for stage in progress_stages]

                export_data['cases'].append(case_export)

            # 寫入檔案
            import json
            os.makedirs(os.path.dirname(export_path), exist_ok=True)
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2, default=str)

            print(f"✅ 案件資料匯出成功: {export_path}")
            return True

        except Exception as e:
            print(f"❌ 匯出案件資料失敗: {e}")
            return False