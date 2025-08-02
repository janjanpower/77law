#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
案件控制器 - 更新版本
使用分離的 Repository 層架構，專注於請求處理和回應
"""

from datetime import datetime
from typing import List, Optional, Tuple, Dict, Any
from models.case_model import CaseData
from services.case_service import CaseService
from repositories.case_repository import CaseRepository
from repositories.progress_repository import ProgressRepository
from repositories.file_repository import FileRepository
from config.settings import AppConfig
import os


class CaseController:
    """案件控制器 - 使用 Repository 架構"""

    def __init__(self, data_folder: str = None):
        """
        初始化案件控制器

        Args:
            data_folder: 資料資料夾路徑
        """
        self.data_folder = data_folder or AppConfig.DATA_CONFIG.get('data_folder', './data')

        # 確保資料夾存在
        os.makedirs(self.data_folder, exist_ok=True)

        # 初始化服務層
        self.case_service = CaseService(self.data_folder)

        # 直接初始化 Repository 層（用於特定需求）
        self.case_repository = self.case_service.repository
        self.progress_repository = self.case_service.progress_repository
        self.file_repository = FileRepository(self.data_folder)

        self.load_cases()
        # 延遲初始化其他服務
        self.folder_service = None
        self.import_export_service = None

        print("✅ CaseController 初始化完成 (使用 Repository 架構)")

    def load_cases(self) -> None:
        """
        載入所有案件資料，儲存在 self.cases 屬性中
        """
        try:
            self.cases = self.case_repository.get_all_cases()
            print(f"📂 已載入案件資料，共 {len(self.cases)} 筆")
        except Exception as e:
            self.cases = []
            print(f"❌ 載入案件資料失敗: {str(e)}")

    def _get_folder_service(self):
        """延遲取得資料夾服務"""
        if self.folder_service is None:
            from services.folder_service import FolderService
            self.folder_service = FolderService(self.data_folder)
        return self.folder_service

    def _get_import_export_service(self):
        """延遲取得匯入匯出服務"""
        if self.import_export_service is None:
            from services.import_export_service import ImportExportService
            self.import_export_service = ImportExportService(self.data_folder)
        return self.import_export_service

    # ==================== 案件CRUD操作 ====================

    def add_case(self, case_data: CaseData) -> bool:
        """
        新增案件 - 修正：整合新的驗證邏輯

        Args:
            case_data: 案件資料

        Returns:
            bool: 新增是否成功
        """
        try:
            print(f"➕ 控制器: 開始新增案件 - {case_data.client}")

            # 1. 基本驗證（使用修正後的ValidationService）
            validation_result = self.validate_case_data(case_data)
            if not validation_result[0]:
                print(f"❌ 控制器: 案件資料驗證失敗 - {validation_result[1]}")
                return False

            # 2. 自動生成案件編號（如果沒有提供）
            if not case_data.case_id:
                case_data.case_id = self.generate_case_id(case_data.case_type)
                print(f"📝 控制器: 自動生成案件編號 - {case_data.case_id}")

            # 3. 檢查同類型內是否重複（修正後的邏輯）
            if self.check_case_id_duplicate(case_data.case_id, case_data.case_type):
                print(f"❌ 控制器: 案件編號重複 - {case_data.case_id} (類型: {case_data.case_type})")
                return False

            # 4. 委託給服務層處理業務邏輯
            success, message = self.case_service.create_case(case_data)

            if success:
                # 5. 重新載入案件資料
                self.load_cases()
                print(f"✅ 控制器: 案件新增成功 - {case_data.case_id}")
                return True
            else:
                print(f"❌ 控制器: 新增案件失敗 - {message}")
                return False

        except Exception as e:
            print(f"❌ 控制器: 新增案件時發生錯誤 - {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def update_case_id(self, old_case_id: str, new_case_id: str, case_type: str) -> tuple:
        """
        更新案件編號 - 修正：加入案件類型檢查

        Args:
            old_case_id: 舊案件編號
            new_case_id: 新案件編號
            case_type: 案件類型

        Returns:
            tuple: (成功與否, 訊息)
        """
        try:
            # 驗證新編號格式
            if not self.validate_case_id_format(new_case_id):
                return False, "案件編號格式錯誤，應為6位數字(民國年分3碼+流水號3碼)"

            # 檢查同類型內是否重複（修正後的邏輯）
            if self.check_case_id_duplicate(new_case_id, case_type, old_case_id):
                return False, f"案件編號 {new_case_id} 在 {case_type} 類型中已存在"

            # 找到並更新案件
            for case in self.cases:
                if case.case_id == old_case_id:
                    case.case_id = new_case_id
                    from datetime import datetime
                    case.updated_date = datetime.now()

                    success = self.save_cases()
                    if success:
                        # 更新案件資訊Excel檔案
                        try:
                            self.folder_manager.update_case_info_excel(case)
                        except Exception as e:
                            print(f"更新Excel失敗: {e}")

                        from config.settings import AppConfig
                        case_display_name = AppConfig.format_case_display_name(case)
                        print(f"已更新案件編號：{old_case_id} → {new_case_id} ({case_display_name})")
                        return True, "案件編號更新成功"
                    else:
                        return False, "儲存案件資料失敗"

            return False, f"找不到案件編號: {old_case_id}"

        except Exception as e:
            print(f"更新案件編號失敗: {e}")
            import traceback
            traceback.print_exc()
            return False, f"更新失敗: {str(e)}"

    def update_case(self, case_data: CaseData, update_folder: bool = False,
                   sync_progress: bool = False) -> bool:
        """
        更新案件

        Args:
            case_data: 更新後的案件資料
            update_folder: 是否同步更新資料夾
            sync_progress: 是否同步進度資料

        Returns:
            bool: 是否更新成功
        """
        try:
            result = self.case_service.update_case(case_data, update_folder, sync_progress)
            if result[0]:
                print(f"✅ 控制器: 成功更新案件 {case_data.case_id}")
            else:
                print(f"❌ 控制器: 更新案件失敗 - {result[1]}")
            return result[0]
        except Exception as e:
            print(f"❌ CaseController.update_case 失敗: {e}")
            return False

    def delete_case(self, case_id: str, delete_folder: bool = True,
                   delete_progress: bool = True, force: bool = False) -> bool:
        """
        刪除案件

        Args:
            case_id: 案件ID
            delete_folder: 是否刪除資料夾
            delete_progress: 是否刪除進度資料
            force: 是否強制刪除

        Returns:
            bool: 是否刪除成功
        """
        try:
            result = self.case_service.delete_case(case_id, delete_folder, delete_progress, force)
            if result[0]:
                print(f"✅ 控制器: 成功刪除案件 {case_id}")
            else:
                print(f"❌ 控制器: 刪除案件失敗 - {result[1]}")
            return result[0]
        except Exception as e:
            print(f"❌ CaseController.delete_case 失敗: {e}")
            return False

    # ==================== 案件查詢操作 ====================

    def get_case_by_id(self, case_id: str) -> Optional[CaseData]:
        """根據ID取得案件"""
        return self.case_repository.get_case_by_id(case_id)

    def get_cases(self) -> List[CaseData]:
        """取得所有案件"""
        return self.case_repository.get_all_cases()

    def get_cases_by_client(self, client_name: str) -> List[CaseData]:
        """根據當事人姓名取得案件"""
        return self.case_repository.get_cases_by_client(client_name)

    def get_cases_by_type(self, case_type: str) -> List[CaseData]:
        """根據案件類型取得案件"""
        return self.case_repository.get_cases_by_type(case_type)

    def get_cases_by_status(self, status: str) -> List[CaseData]:
        """根據案件狀態取得案件"""
        return self.case_repository.get_cases_by_status(status)

    def search_cases(self, keyword: str, **filters) -> List[CaseData]:
        """
        搜尋案件

        Args:
            keyword: 搜尋關鍵字
            **filters: 其他篩選條件

        Returns:
            符合條件的案件列表
        """
        return self.case_repository.search_cases(keyword)

    def get_case_complete_info(self, case_id: str) -> Optional[Dict[str, Any]]:
        """取得案件完整資訊（包含進度、資料夾狀態等）"""
        return self.case_service.get_case_with_progress(case_id)

    def get_urgent_cases(self, days_threshold: int = 7) -> List[CaseData]:
        """取得緊急案件"""
        return self.case_service.get_urgent_cases(days_threshold)

    def get_overdue_cases(self) -> List[CaseData]:
        """取得逾期案件"""
        return self.case_service.get_overdue_cases()

    # ==================== 進度管理操作 ====================

    def get_case_progress(self, case_id: str) -> Dict[str, Any]:
        """取得案件進度摘要"""
        return self.progress_repository.get_case_progress_summary(case_id)

    def get_case_progress_stages(self, case_id: str) -> List[Any]:
        """取得案件的所有進度階段"""
        return self.progress_repository.get_case_progress_stages(case_id)

    def update_progress_stage(self, stage_data: Dict[str, Any]) -> bool:
        """
        更新進度階段

        Args:
            stage_data: 階段資料

        Returns:
            bool: 更新是否成功
        """
        try:
            from repositories.progress_repository import ProgressStage

            # 取得現有階段
            stage_id = stage_data.get('stage_id')
            existing_stage = self.progress_repository.get_progress_stage(stage_id)

            if not existing_stage:
                print(f"❌ 找不到進度階段: {stage_id}")
                return False

            # 更新欄位
            for field, value in stage_data.items():
                if hasattr(existing_stage, field):
                    setattr(existing_stage, field, value)

            # 儲存更新
            result = self.progress_repository.update_progress_stage(existing_stage)

            if result:
                print(f"✅ 控制器: 成功更新進度階段 {stage_id}")
            else:
                print(f"❌ 控制器: 更新進度階段失敗")

            return result

        except Exception as e:
            print(f"❌ CaseController.update_progress_stage 失敗: {e}")
            return False

    def complete_progress_stage(self, stage_id: str) -> bool:
        """
        完成進度階段

        Args:
            stage_id: 階段ID

        Returns:
            bool: 是否成功
        """
        try:
            result = self.progress_repository.batch_complete_stages([stage_id])
            success = result['success_count'] > 0

            if success:
                print(f"✅ 控制器: 成功完成進度階段 {stage_id}")
            else:
                print(f"❌ 控制器: 完成進度階段失敗 - {result['errors']}")

            return success

        except Exception as e:
            print(f"❌ CaseController.complete_progress_stage 失敗: {e}")
            return False

    def assign_progress_stages(self, stage_ids: List[str], assignee: str) -> bool:
        """
        指派進度階段

        Args:
            stage_ids: 階段ID列表
            assignee: 負責人

        Returns:
            bool: 是否成功
        """
        try:
            result = self.progress_repository.batch_assign_stages(stage_ids, assignee)
            success = result['success_count'] > 0

            if success:
                print(f"✅ 控制器: 成功指派 {result['success_count']} 個進度階段給 {assignee}")
            else:
                print(f"❌ 控制器: 指派進度階段失敗 - {result['errors']}")

            return success

        except Exception as e:
            print(f"❌ CaseController.assign_progress_stages 失敗: {e}")
            return False

    # ==================== 檔案管理操作 ====================

    def upload_file(self, source_path: str, case_id: str, category: str = "一般文件",
                   description: str = "") -> Tuple[bool, str]:
        """
        上傳檔案到案件

        Args:
            source_path: 來源檔案路徑
            case_id: 案件ID
            category: 檔案分類
            description: 檔案描述

        Returns:
            Tuple[bool, str]: (成功與否, 目標路徑或錯誤訊息)
        """
        try:
            # 取得案件資料夾
            case_data = self.case_repository.get_case_by_id(case_id)
            if not case_data:
                return False, f"案件不存在: {case_id}"

            folder_service = self._get_folder_service()
            case_folder = folder_service.get_case_folder_path(case_data)

            if not case_folder:
                return False, f"找不到案件資料夾: {case_id}"

            # 根據分類決定目標子資料夾
            category_folders = {
                "證據資料": "證據資料",
                "庭期紀錄": "庭期紀錄",
                "相關文件": "相關文件",
                "一般文件": "相關文件"
            }

            target_folder = os.path.join(case_folder, category_folders.get(category, "相關文件"))

            # 儲存檔案
            result = self.file_repository.save_file(source_path, target_folder, case_id, category, description)

            if result[0]:
                print(f"✅ 控制器: 成功上傳檔案到案件 {case_id}")
            else:
                print(f"❌ 控制器: 檔案上傳失敗 - {result[1]}")

            return result

        except Exception as e:
            error_msg = f"檔案上傳失敗: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg

    def get_case_files(self, case_id: str) -> List[Any]:
        """取得案件的所有檔案"""
        return self.file_repository.get_files_by_case(case_id)


    def delete_file(self, file_path: str) -> bool:
        """
        刪除檔案

        Args:
            file_path: 檔案路徑

        Returns:
            bool: 是否刪除成功
        """
        try:
            result = self.file_repository.delete_file(file_path, backup=True)

            if result[0]:
                print(f"✅ 控制器: 成功刪除檔案 {os.path.basename(file_path)}")
            else:
                print(f"❌ 控制器: 刪除檔案失敗 - {result[1]}")

            return result[0]

        except Exception as e:
            print(f"❌ CaseController.delete_file 失敗: {e}")
            return False

    # ==================== 匯入匯出操作 ====================

    def import_from_excel(self, file_path: str, merge_strategy: str = 'skip_duplicates',
                         create_folders: bool = True, apply_template: str = None) -> Tuple[bool, Dict[str, Any]]:
        """
        從Excel匯入案件資料

        Args:
            file_path: Excel檔案路徑
            merge_strategy: 合併策略
            create_folders: 是否為匯入的案件建立資料夾
            apply_template: 套用的進度範本

        Returns:
            (成功與否, 詳細結果)
        """
        try:
            import_export_service = self._get_import_export_service()
            result = import_export_service.import_cases_from_excel(
                file_path, merge_strategy, create_folders, apply_template
            )

            if result[0]:
                print(f"✅ 控制器: Excel匯入成功")
            else:
                print(f"❌ 控制器: Excel匯入失敗 - {result[1]}")

            return result

        except Exception as e:
            error_msg = f"Excel匯入失敗: {str(e)}"
            print(f"❌ {error_msg}")
            return False, {'error': error_msg}

    def export_to_excel(self, file_path: str, cases: List[CaseData] = None,
                       include_progress: bool = True, include_metadata: bool = True) -> Tuple[bool, str]:
        """
        匯出案件資料到Excel

        Args:
            file_path: 匯出檔案路徑
            cases: 要匯出的案件列表（None表示全部）
            include_progress: 是否包含進度資訊
            include_metadata: 是否包含元資料

        Returns:
            (成功與否, 訊息)
        """
        try:
            if cases is None:
                cases = self.case_repository.get_all_cases()

            # 增強案件資料（如果需要包含進度）
            if include_progress:
                enhanced_cases = []
                for case in cases:
                    enhanced_case = case
                    progress_info = self.progress_repository.get_case_progress_summary(case.case_id)
                    # 將進度資訊添加到案件資料中（如果案件物件支援）
                    if hasattr(enhanced_case, '__dict__'):
                        enhanced_case.__dict__['progress_summary'] = f"{progress_info['progress_percentage']}% ({progress_info['completed_stages']}/{progress_info['total_stages']})"
                    enhanced_cases.append(enhanced_case)
                cases = enhanced_cases

            import_export_service = self._get_import_export_service()
            result = import_export_service.export_cases_to_excel(cases, file_path, include_metadata)

            if result[0]:
                print(f"✅ 控制器: Excel匯出成功")
            else:
                print(f"❌ 控制器: Excel匯出失敗 - {result[1]}")

            return result

        except Exception as e:
            error_msg = f"Excel匯出失敗: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg

    def export_case_report(self, case_id: str, report_path: str) -> bool:
        """
        匯出案件詳細報告

        Args:
            case_id: 案件ID
            report_path: 報告檔案路徑

        Returns:
            bool: 匯出是否成功
        """
        try:
            # 取得完整案件資訊
            case_info = self.case_service.get_case_with_progress(case_id)
            if not case_info:
                print(f"❌ 找不到案件: {case_id}")
                return False

            # 取得檔案資訊
            case_files = self.file_repository.get_files_by_case(case_id)

            # 建立報告資料
            report_data = {
                'case_data': case_info['case_data'].to_dict() if hasattr(case_info['case_data'], 'to_dict') else case_info['case_data'].__dict__,
                'progress_summary': case_info['progress_summary'],
                'progress_stages': [stage.to_dict() for stage in case_info['progress_stages']],
                'files': [file_meta.to_dict() for file_meta in case_files],
                'report_generated_at': datetime.now().isoformat()
            }

            # 寫入報告檔案
            import json
            os.makedirs(os.path.dirname(report_path), exist_ok=True)
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2, default=str)

            print(f"✅ 控制器: 案件報告匯出成功 - {report_path}")
            return True

        except Exception as e:
            print(f"❌ CaseController.export_case_report 失敗: {e}")
            return False

    # ==================== 統計和報告 ====================

    def get_dashboard_data(self) -> Dict[str, Any]:
        """取得儀表板資料"""
        try:
            # 基本統計
            case_stats = self.case_service.get_case_statistics()

            # 工作負荷
            workload_report = self.case_service.get_workload_report()

            # 最近活動
            recent_cases = self.case_repository.get_all_cases()[-10:]  # 最近10個案件

            # 即將到期的進度
            upcoming_stages = self.progress_repository.get_upcoming_stages(7)

            # 逾期進度
            overdue_stages = self.progress_repository.get_overdue_stages()

            dashboard_data = {
                'case_statistics': case_stats,
                'workload_overview': workload_report,
                'recent_cases': [case.to_dict() if hasattr(case, 'to_dict') else case.__dict__ for case in recent_cases],
                'upcoming_deadlines': [stage.to_dict() for stage in upcoming_stages[:5]],  # 顯示前5個
                'overdue_items': [stage.to_dict() for stage in overdue_stages[:5]],  # 顯示前5個
                'alerts': {
                    'urgent_cases': len(case_stats.get('urgent_cases_count', 0)),
                    'overdue_stages': len(overdue_stages),
                    'upcoming_deadlines': len(upcoming_stages)
                },
                'last_updated': datetime.now().isoformat()
            }

            return dashboard_data

        except Exception as e:
            print(f"❌ CaseController.get_dashboard_data 失敗: {e}")
            return {}

    def get_progress_report(self, assignee: str = None, date_range: Tuple[datetime, datetime] = None) -> Dict[str, Any]:
        """
        取得進度報告

        Args:
            assignee: 特定負責人（可選）
            date_range: 日期範圍（可選）

        Returns:
            進度報告資料
        """
        try:
            # 取得進度統計
            progress_stats = self.progress_repository.get_progress_statistics()

            # 取得工作負荷統計
            workload_stats = self.progress_repository.get_workload_by_assignee()

            # 篩選特定負責人
            if assignee:
                workload_stats = {k: v for k, v in workload_stats.items() if k == assignee}

            # 取得所有進度階段
            all_stages = self.progress_repository.get_all_progress_stages()

            # 日期篩選
            if date_range:
                start_date, end_date = date_range
                filtered_stages = []
                for stage in all_stages:
                    if stage.created_at and start_date <= stage.created_at <= end_date:
                        filtered_stages.append(stage)
                all_stages = filtered_stages

            # 建立報告
            report = {
                'overall_statistics': progress_stats,
                'workload_by_assignee': workload_stats,
                'stage_details': [stage.to_dict() for stage in all_stages],
                'summary': {
                    'total_stages_in_period': len(all_stages),
                    'completion_rate': progress_stats.get('completion_rate', 0),
                    'overdue_count': progress_stats.get('overdue_count', 0)
                },
                'filters': {
                    'assignee': assignee,
                    'date_range': [d.isoformat() if d else None for d in (date_range or (None, None))]
                },
                'generated_at': datetime.now().isoformat()
            }

            return report

        except Exception as e:
            print(f"❌ CaseController.get_progress_report 失敗: {e}")
            return {}

    # ==================== 批次操作 ====================

    def batch_update_cases(self, updates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """批次更新案件"""
        return self.case_repository.batch_update_cases(updates)

    def batch_assign_cases(self, case_ids: List[str], assignee: str) -> Dict[str, Any]:
        """批次指派案件"""
        return self.case_service.batch_assign_progress(case_ids, assignee)

    def batch_complete_stages(self, stage_ids: List[str]) -> Dict[str, Any]:
        """批次完成進度階段"""
        return self.progress_repository.batch_complete_stages(stage_ids)

    def batch_create_folders(self, case_ids: List[str]) -> Dict[str, Any]:
        """
        批次建立案件資料夾

        Args:
            case_ids: 案件ID列表

        Returns:
            批次建立結果
        """
        try:
            result = {
                'success_count': 0,
                'failed_count': 0,
                'errors': []
            }

            folder_service = self._get_folder_service()

            for case_id in case_ids:
                case_data = self.case_repository.get_case_by_id(case_id)
                if case_data:
                    folder_result = folder_service.create_case_folder_structure(case_data)
                    if folder_result[0]:
                        result['success_count'] += 1
                    else:
                        result['failed_count'] += 1
                        result['errors'].append(f"案件 {case_id}: {folder_result[1]}")
                else:
                    result['failed_count'] += 1
                    result['errors'].append(f"找不到案件: {case_id}")

            return result

        except Exception as e:
            return {
                'success_count': 0,
                'failed_count': len(case_ids),
                'errors': [f"批次建立資料夾失敗: {str(e)}"]
            }

    # ==================== 資料維護操作 ====================

    def validate_data_integrity(self) -> Dict[str, Any]:
        """驗證資料完整性"""
        return self.case_service.validate_data_integrity()

    def cleanup_data(self) -> Dict[str, Any]:
        """清理資料"""
        try:
            # 清理案件和進度的孤立資料
            case_cleanup = self.case_service.cleanup_orphaned_data()

            # 清理檔案元資料
            file_cleanup_count = self.file_repository.cleanup_orphaned_metadata()

            return {
                'case_progress_cleanup': case_cleanup,
                'file_metadata_cleaned': file_cleanup_count,
                'total_cleaned_items': (case_cleanup.get('cleaned_progress_stages', 0) +
                                      case_cleanup.get('cleaned_case_metadata', 0) +
                                      file_cleanup_count)
            }

        except Exception as e:
            return {'error': str(e)}

    def backup_all_data(self, backup_folder: str) -> Dict[str, bool]:
        """
        備份所有資料

        Args:
            backup_folder: 備份資料夾路徑

        Returns:
            各部分備份結果
        """
        try:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            results = {}

            # 備份案件資料
            case_backup_path = os.path.join(backup_folder, f"cases_backup_{timestamp}.json")
            results['cases'] = self.case_repository.backup_data(case_backup_path)

            # 備份進度資料
            progress_backup_path = os.path.join(backup_folder, f"progress_backup_{timestamp}.json")
            results['progress'] = self.progress_repository.backup_progress_data(progress_backup_path)

            # 備份檔案清單
            files_backup_path = os.path.join(backup_folder, f"files_backup_{timestamp}.json")
            results['files'] = self.file_repository.export_file_list(files_backup_path)

            print(f"✅ 控制器: 資料備份完成 - {backup_folder}")
            return results

        except Exception as e:
            print(f"❌ CaseController.backup_all_data 失敗: {e}")
            return {'error': str(e)}

    def reload_all_data(self) -> bool:
        """重新載入所有資料"""
        try:
            case_reload = self.case_repository.reload_data()
            progress_reload = self.progress_repository.reload_data()

            success = case_reload and progress_reload

            if success:
                print("✅ 控制器: 成功重新載入所有資料")
            else:
                print("❌ 控制器: 重新載入資料時發生錯誤")

            return success

        except Exception as e:
            print(f"❌ CaseController.reload_all_data 失敗: {e}")
            return False

    # ==================== 輔助功能 ====================

    def check_case_id_duplicate(self, case_id: str, case_type: str, exclude_case_id: str = None) -> bool:
        """
        檢查案件編號是否重複 - 修正：按案件類型分別檢查

        Args:
            case_id: 要檢查的案件編號
            case_type: 案件類型（民事/刑事）
            exclude_case_id: 排除的案件編號（更新時用）

        Returns:
            bool: 是否重複
        """
        for case in self.cases:
            # 修正：同一案件類型內才檢查重複
            if (case.case_id == case_id and
                case.case_type == case_type and
                case.case_id != exclude_case_id):
                return True
        return False

    def generate_case_id(self, case_type: str = None) -> str:
        """
        產生新的案件編號 - 修正：按案件類型分別生成
        格式：民國年分(三碼)+流水號(三碼)

        Args:
            case_type: 案件類型，用於檢查同類型內的重複

        Returns:
            str: 新的案件編號
        """
        try:
            import datetime

            # 計算民國年分
            current_year = datetime.datetime.now().year
            minguo_year = current_year - 1911

            # 如果沒有指定案件類型，使用預設邏輯
            if not case_type:
                case_type = "民事"  # 預設為民事

            # 取得同類型案件的現有編號
            same_type_cases = [case for case in self.cases if case.case_type == case_type]
            existing_ids = {case.case_id for case in same_type_cases}

            # 找出當年度最大編號（只在同類型案件中查找）
            current_year_prefix = f"{minguo_year:03d}"
            max_number = 0

            for case_id in existing_ids:
                if case_id.startswith(current_year_prefix) and len(case_id) == 6:
                    try:
                        number = int(case_id[3:])
                        max_number = max(max_number, number)
                    except ValueError:
                        continue

            # 產生新編號
            new_number = max_number + 1
            new_case_id = f"{current_year_prefix}{new_number:03d}"

            return new_case_id

        except Exception as e:
            print(f"產生案件編號失敗: {e}")
            # 備用方案
            import datetime
            current_year = datetime.datetime.now().year
            minguo_year = current_year - 1911
            return f"{minguo_year:03d}001"


    def validate_case_data(self, case_data: CaseData) -> Tuple[bool, str]:
        """
        驗證案件資料（委託給服務層）

        Args:
            case_data: 案件資料

        Returns:
            Tuple[bool, str]: (驗證是否通過, 訊息)
        """
        try:
            validation_service = self.case_service._get_validation_service()
            return validation_service.validate_case_data(case_data)
        except Exception as e:
            return False, f"驗證失敗: {str(e)}"

    # ==================== 系統狀態檢查 ====================

    def get_system_status(self) -> Dict[str, Any]:
        """取得系統狀態"""
        try:
            status = {
                'data_folder': self.data_folder,
                'data_folder_exists': os.path.exists(self.data_folder),
                'repositories': {
                    'case_repository': {
                        'data_file': self.case_repository.data_file,
                        'data_file_exists': os.path.exists(self.case_repository.data_file),
                        'case_count': self.case_repository.get_case_count()
                    },
                    'progress_repository': {
                        'data_file': self.progress_repository.progress_file,
                        'data_file_exists': os.path.exists(self.progress_repository.progress_file),
                        'stage_count': len(self.progress_repository.get_all_progress_stages())
                    },
                    'file_repository': {
                        'metadata_file': self.file_repository.metadata_file,
                        'metadata_file_exists': os.path.exists(self.file_repository.metadata_file),
                        'file_count': len(self.file_repository.get_all_files())
                    }
                },
                'data_integrity': self.validate_data_integrity(),
                'last_checked': datetime.now().isoformat()
            }

            return status

        except Exception as e:
            return {
                'error': str(e),
                'last_checked': datetime.now().isoformat()
            }