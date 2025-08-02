#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
案件控制器 - 簡化版本
使用新的 Services 層架構，專注於請求處理和回應
"""

from typing import List, Optional, Tuple, Dict, Any
from models.case_model import CaseData
from services.services_controller import ServicesController
from config.settings import AppConfig
import os


class CaseController:
    """案件控制器 - 簡化版本（委託給 Services 層）"""

    def __init__(self, data_folder: str = None):
        """
        初始化案件控制器

        Args:
            data_folder: 資料資料夾路徑
        """
        self.data_folder = data_folder or AppConfig.DATA_CONFIG.get('data_folder', './data')

        # 確保資料夾存在
        os.makedirs(self.data_folder, exist_ok=True)

        # 初始化服務控制器（所有業務邏輯都委託給它）
        self.services = ServicesController(self.data_folder)

        print("✅ CaseController 初始化完成 (使用 Services 架構)")

    # ==================== 案件CRUD操作 ====================

    def add_case(self, case_data: CaseData, create_folder: bool = True,
                 apply_template: str = None) -> bool:
        """
        新增案件

        Args:
            case_data: 案件資料
            create_folder: 是否建立資料夾
            apply_template: 套用的進度範本名稱

        Returns:
            bool: 是否新增成功
        """
        try:
            result = self.services.create_case(case_data, create_folder, apply_template)
            if result[0]:
                print(f"✅ 控制器: 成功新增案件 {case_data.client}")
            else:
                print(f"❌ 控制器: 新增案件失敗 - {result[1]}")
            return result[0]
        except Exception as e:
            print(f"❌ CaseController.add_case 失敗: {e}")
            return False

    def update_case(self, case_data: CaseData, update_folder: bool = False) -> bool:
        """
        更新案件

        Args:
            case_data: 更新後的案件資料
            update_folder: 是否同步更新資料夾

        Returns:
            bool: 是否更新成功
        """
        try:
            result = self.services.update_case(case_data, update_folder, sync_progress=True)
            if result[0]:
                print(f"✅ 控制器: 成功更新案件 {case_data.case_id}")
            else:
                print(f"❌ 控制器: 更新案件失敗 - {result[1]}")
            return result[0]
        except Exception as e:
            print(f"❌ CaseController.update_case 失敗: {e}")
            return False

    def delete_case(self, case_id: str, delete_folder: bool = True, force: bool = False) -> bool:
        """
        刪除案件

        Args:
            case_id: 案件ID
            delete_folder: 是否刪除資料夾
            force: 是否強制刪除

        Returns:
            bool: 是否刪除成功
        """
        try:
            result = self.services.delete_case(case_id, delete_folder, delete_progress=True, force=force)
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
        return self.services.case_service.get_case_by_id(case_id)

    def get_cases(self) -> List[CaseData]:
        """取得所有案件"""
        return self.services.case_service.repository.get_all_cases()

    def get_cases_by_client(self, client_name: str) -> List[CaseData]:
        """根據當事人姓名取得案件"""
        return self.services.case_service.get_cases_by_client(client_name)

    def get_cases_by_type(self, case_type: str) -> List[CaseData]:
        """根據案件類型取得案件"""
        return self.services.case_service.get_cases_by_type(case_type)

    def search_cases(self, keyword: str, **filters) -> List[CaseData]:
        """
        搜尋案件

        Args:
            keyword: 搜尋關鍵字
            **filters: 其他篩選條件

        Returns:
            符合條件的案件列表
        """
        if filters:
            # 使用進階搜尋
            advanced_results = self.services.search_cases_advanced(
                keyword=keyword,
                case_type=filters.get('case_type', ''),
                status=filters.get('status', ''),
                progress_status=filters.get('progress_status', ''),
                has_overdue=filters.get('has_overdue')
            )
            return [CaseData.from_dict(result['case_data']) for result in advanced_results]
        else:
            # 簡單搜尋
            return self.services.case_service.search_cases(keyword)

    def get_case_complete_info(self, case_id: str) -> Optional[Dict[str, Any]]:
        """取得案件完整資訊（包含進度、資料夾狀態等）"""
        return self.services.get_case_complete_info(case_id)

    # ==================== 匯入匯出操作 ====================

    def import_from_excel(self, file_path: str, merge_strategy: str = 'skip_duplicates',
                         create_folders: bool = True) -> Tuple[bool, Dict[str, Any]]:
        """
        從Excel匯入案件資料

        Args:
            file_path: Excel檔案路徑
            merge_strategy: 合併策略
            create_folders: 是否為匯入的案件建立資料夾

        Returns:
            (成功與否, 詳細結果)
        """
        try:
            result = self.services.import_cases_from_excel(
                file_path, merge_strategy, create_folders, apply_templates=False
            )

            if result[0]:
                report = result[1]
                print(f"✅ 控制器: Excel匯入成功")
                print(f"   匯入數量: {report.get('imported_count', 0)}")
                if report.get('failed_count', 0) > 0:
                    print(f"   失敗數量: {report.get('failed_count', 0)}")
            else:
                print(f"❌ 控制器: Excel匯入失敗 - {result[1]}")

            return result

        except Exception as e:
            error_msg = f"匯入Excel失敗: {str(e)}"
            print(f"❌ CaseController.import_from_excel: {error_msg}")
            return False, {'error': error_msg}

    def export_to_excel(self, file_path: str = None, cases: List[CaseData] = None,
                       include_progress: bool = True) -> bool:
        """
        匯出案件資料到Excel

        Args:
            file_path: 匯出檔案路徑，None則自動生成
            cases: 要匯出的案件列表，None表示所有案件
            include_progress: 是否包含進度資訊

        Returns:
            bool: 匯出是否成功
        """
        try:
            result = self.services.export_cases_to_excel(
                cases, file_path, include_progress, include_metadata=True
            )

            if result[0]:
                print(f"✅ 控制器: Excel匯出成功 - {result[1]}")
            else:
                print(f"❌ 控制器: Excel匯出失敗 - {result[1]}")

            return result[0]

        except Exception as e:
            print(f"❌ CaseController.export_to_excel 失敗: {e}")
            return False

    # ==================== 資料夾操作 ====================

    def create_case_folder(self, case_id: str) -> bool:
        """為指定案件建立資料夾"""
        try:
            case_data = self.get_case_by_id(case_id)
            if not case_data:
                print(f"❌ 找不到案件: {case_id}")
                return False

            result = self.services.folder_service.create_case_folder_structure(case_data)
            return result[0]

        except Exception as e:
            print(f"❌ CaseController.create_case_folder 失敗: {e}")
            return False

    def delete_case_folder(self, case_id: str) -> bool:
        """刪除指定案件的資料夾"""
        try:
            case_data = self.get_case_by_id(case_id)
            if not case_data:
                print(f"❌ 找不到案件: {case_id}")
                return False

            result = self.services.folder_service.delete_case_folder(case_data)
            return result[0]

        except Exception as e:
            print(f"❌ CaseController.delete_case_folder 失敗: {e}")
            return False

    def get_case_folder_path(self, case_id: str) -> Optional[str]:
        """取得案件資料夾路徑"""
        try:
            case_data = self.get_case_by_id(case_id)
            if not case_data:
                return None

            return self.services.folder_service.get_case_folder_path(case_data)

        except Exception as e:
            print(f"❌ CaseController.get_case_folder_path 失敗: {e}")
            return None

    # ==================== 進度管理操作 ====================

    def get_case_progress(self, case_id: str) -> Dict[str, Any]:
        """取得案件進度資訊"""
        return self.services.progress_service.get_case_progress(case_id)

    def add_progress_stage(self, case_id: str, stage_name: str, description: str = "",
                          due_date: str = None, priority: str = "一般") -> bool:
        """
        為案件新增進度階段

        Args:
            case_id: 案件ID
            stage_name: 階段名稱
            description: 階段描述
            due_date: 到期日期 (YYYY-MM-DD)
            priority: 優先級

        Returns:
            bool: 是否新增成功
        """
        try:
            stage_data = {
                'name': stage_name,
                'description': description,
                'priority': priority,
                'status': '未開始'
            }

            if due_date:
                stage_data['due_date'] = due_date

            result = self.services.progress_service.create_progress_stage(case_id, stage_data)
            return result[0]

        except Exception as e:
            print(f"❌ CaseController.add_progress_stage 失敗: {e}")
            return False

    def update_progress_stage(self, case_id: str, stage_id: str, **updates) -> bool:
        """
        更新進度階段

        Args:
            case_id: 案件ID
            stage_id: 階段ID
            **updates: 要更新的欄位

        Returns:
            bool: 是否更新成功
        """
        try:
            result = self.services.progress_service.update_progress_stage(case_id, stage_id, updates)
            return result[0]

        except Exception as e:
            print(f"❌ CaseController.update_progress_stage 失敗: {e}")
            return False

    def apply_progress_template(self, case_id: str, template_name: str) -> bool:
        """
        為案件套用進度範本

        Args:
            case_id: 案件ID
            template_name: 範本名稱

        Returns:
            bool: 是否套用成功
        """
        try:
            result = self.services.progress_service.apply_progress_template(case_id, template_name)
            return result[0]

        except Exception as e:
            print(f"❌ CaseController.apply_progress_template 失敗: {e}")
            return False

    def get_available_progress_templates(self) -> List[str]:
        """取得可用的進度範本列表"""
        return self.services.progress_service.get_available_templates()

    # ==================== 統計和報告 ====================

    def get_case_statistics(self) -> Dict[str, Any]:
        """取得案件統計資訊"""
        return self.services.case_service.get_case_statistics()

    def get_system_dashboard(self) -> Dict[str, Any]:
        """取得系統儀表板資料"""
        return self.services.get_system_dashboard()

    def get_urgent_cases(self, days_threshold: int = 7) -> List[CaseData]:
        """取得緊急案件"""
        return self.services.case_service.get_urgent_cases(days_threshold)

    def get_overdue_stages(self, case_id: str = None) -> List[Dict[str, Any]]:
        """取得延期的進度階段"""
        return self.services.progress_service.get_overdue_stages(case_id)

    def generate_case_report(self, case_id: str) -> str:
        """生成案件報告"""
        try:
            # 取得完整案件資訊
            complete_info = self.get_case_complete_info(case_id)
            if not complete_info:
                return f"❌ 找不到案件: {case_id}"

            # 生成進度報告
            progress_report = self.services.progress_service.generate_progress_report(case_id)

            # 整合報告
            case_data = complete_info['case_data']
            folder_info = complete_info['folder_info']

            report_lines = []
            report_lines.append("=" * 60)
            report_lines.append(f"案件完整報告 - {case_data['client']}")
            report_lines.append("=" * 60)

            # 基本資訊
            report_lines.append("\n📋 基本資訊:")
            report_lines.append(f"案件ID: {case_data['case_id']}")
            report_lines.append(f"當事人: {case_data['client']}")
            report_lines.append(f"案件類型: {case_data['case_type']}")
            report_lines.append(f"案件狀態: {case_data['status']}")
            if case_data.get('creation_date'):
                report_lines.append(f"建立時間: {case_data['creation_date']}")
            if case_data.get('notes'):
                report_lines.append(f"備註: {case_data['notes']}")

            # 資料夾資訊
            report_lines.append(f"\n📁 資料夾資訊:")
            report_lines.append(f"資料夾存在: {'是' if folder_info['exists'] else '否'}")
            if folder_info['exists']:
                report_lines.append(f"檔案數量: {folder_info['file_count']}")
                report_lines.append(f"資料夾大小: {folder_info['size_mb']:.1f} MB")

            # 進度報告
            report_lines.append(f"\n{progress_report}")

            report_lines.append(f"\n報告生成時間: {self.services.progress_service.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

            return "\n".join(report_lines)

        except Exception as e:
            return f"❌ 生成報告失敗: {str(e)}"

    # ==================== 批量操作 ====================

    def batch_create_folders(self, case_ids: List[str]) -> Dict[str, Any]:
        """批量建立案件資料夾"""
        return self.services.batch_create_folders(case_ids)

    def batch_apply_templates(self, case_template_mapping: Dict[str, str]) -> Dict[str, Any]:
        """批量套用進度範本"""
        return self.services.batch_apply_progress_templates(case_template_mapping)

    def batch_update_status(self, case_ids: List[str], new_status: str) -> Dict[str, Any]:
        """
        批量更新案件狀態

        Args:
            case_ids: 案件ID列表
            new_status: 新狀態

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
                case_data = self.get_case_by_id(case_id)
                if not case_data:
                    results['failed'] += 1
                    results['details'].append({
                        'case_id': case_id,
                        'status': 'failed',
                        'reason': '案件不存在'
                    })
                    continue

                # 更新狀態
                case_data.status = new_status
                if self.update_case(case_data):
                    results['success'] += 1
                    results['details'].append({
                        'case_id': case_id,
                        'status': 'success',
                        'new_status': new_status
                    })
                else:
                    results['failed'] += 1
                    results['details'].append({
                        'case_id': case_id,
                        'status': 'failed',
                        'reason': '更新失敗'
                    })

            except Exception as e:
                results['failed'] += 1
                results['details'].append({
                    'case_id': case_id,
                    'status': 'failed',
                    'reason': str(e)
                })

        return results

    # ==================== 通知管理 ====================

    def get_notifications(self, limit: int = 50) -> List[Dict[str, Any]]:
        """取得通知列表"""
        return self.services.notification_service.get_notifications(limit)

    def get_unread_notifications(self) -> List[Dict[str, Any]]:
        """取得未讀通知"""
        return self.services.notification_service.get_unread_notifications()

    def mark_notification_as_read(self, notification_id: str):
        """標記通知為已讀"""
        self.services.notification_service.mark_notification_as_read(notification_id)

    def mark_all_notifications_as_read(self):
        """標記所有通知為已讀"""
        self.services.notification_service.mark_all_as_read()

    def check_deadline_reminders(self, notification_days: List[int] = [1, 3, 7]) -> List[Dict[str, Any]]:
        """檢查期限提醒並發送通知"""
        return self.services.progress_service.check_progress_deadlines(notification_days)

    # ==================== 系統維護 ====================

    def perform_system_maintenance(self) -> Dict[str, Any]:
        """執行系統維護"""
        return self.services.perform_system_maintenance()

    def validate_all_cases(self) -> Dict[str, Any]:
        """驗證所有案件資料"""
        try:
            all_cases = self.get_cases()
            return self.services.validation_service.validate_multiple_cases(all_cases, cross_validation=True)
        except Exception as e:
            return {'error': str(e)}

    def create_data_backup(self, backup_name: str = None, include_folders: bool = False) -> Tuple[bool, str]:
        """建立資料備份"""
        return self.services.import_export_service.create_data_backup(backup_name, include_folders)

    def get_system_health(self) -> Dict[str, Any]:
        """取得系統健康狀態"""
        dashboard = self.get_system_dashboard()
        return dashboard.get('system_health', {})

    # ==================== 便利方法 ====================

    def load_cases(self) -> bool:
        """載入案件資料（向後相容）"""
        try:
            # Services 層會自動載入，這裡只是為了向後相容
            cases = self.get_cases()
            print(f"✅ 載入了 {len(cases)} 筆案件資料")
            return True
        except Exception as e:
            print(f"❌ 載入案件資料失敗: {e}")
            return False

    def save_cases(self) -> bool:
        """儲存案件資料（向後相容）"""
        try:
            # Services 層會自動儲存，這裡只是為了向後相容
            return True
        except Exception as e:
            print(f"❌ 儲存案件資料失敗: {e}")
            return False

    def refresh_data(self):
        """重新整理資料"""
        try:
            # 重新初始化服務控制器
            self.services = ServicesController(self.data_folder)
            print("✅ 資料重新整理完成")
        except Exception as e:
            print(f"❌ 重新整理資料失敗: {e}")

    # ==================== 除錯和狀態查詢 ====================

    def get_controller_status(self) -> Dict[str, Any]:
        """取得控制器狀態資訊"""
        try:
            dashboard = self.get_system_dashboard()

            status = {
                'controller_version': 'Services架構版本',
                'data_folder': self.data_folder,
                'total_cases': len(self.get_cases()),
                'services_available': {
                    'case_service': hasattr(self.services, 'case_service'),
                    'folder_service': hasattr(self.services, 'folder_service'),
                    'import_export_service': hasattr(self.services, 'import_export_service'),
                    'notification_service': hasattr(self.services, 'notification_service'),
                    'validation_service': hasattr(self.services, 'validation_service'),
                    'progress_service': hasattr(self.services, 'progress_service')
                },
                'system_health': dashboard.get('system_health', {}),
                'last_check': self.services.progress_service.datetime.now().isoformat()
            }

            return status

        except Exception as e:
            return {
                'error': str(e),
                'controller_version': 'Services架構版本（狀態檢查失敗）'
            }

    def debug_case(self, case_id: str) -> Dict[str, Any]:
        """除錯特定案件"""
        try:
            debug_info = {
                'case_id': case_id,
                'case_exists': False,
                'folder_exists': False,
                'progress_stages': 0,
                'notifications': 0,
                'issues': []
            }

            # 檢查案件是否存在
            case_data = self.get_case_by_id(case_id)
            if case_data:
                debug_info['case_exists'] = True
                debug_info['case_data'] = case_data.to_dict()

                # 檢查資料夾
                folder_info = self.services.folder_service.get_case_folder_info(case_data)
                debug_info['folder_exists'] = folder_info['exists']
                debug_info['folder_info'] = folder_info

                # 檢查進度
                progress_info = self.get_case_progress(case_id)
                debug_info['progress_stages'] = progress_info['total_stages']
                debug_info['progress_info'] = progress_info

                # 檢查問題
                if not folder_info['exists']:
                    debug_info['issues'].append('資料夾不存在')

                if progress_info['overdue_stages'] > 0:
                    debug_info['issues'].append(f'有 {progress_info["overdue_stages"]} 個延期階段')

            else:
                debug_info['issues'].append('案件不存在')

            return debug_info

        except Exception as e:
            return {
                'case_id': case_id,
                'error': str(e)
            }


# ==================== 向後相容的工廠函數 ====================

def create_case_controller(data_folder: str = None) -> CaseController:
    """
    建立案件控制器的工廠函數

    Args:
        data_folder: 資料資料夾路徑

    Returns:
        CaseController 實例
    """
    return CaseController(data_folder)


# ==================== 便利裝飾器 ====================

def handle_controller_errors(func):
    """控制器方法的錯誤處理裝飾器"""
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except Exception as e:
            print(f"❌ {func.__name__} 執行失敗: {e}")
            # 根據方法返回類型決定預設返回值
            if func.__name__.startswith('get_') and 'List' in str(func.__annotations__.get('return', '')):
                return []
            elif func.__name__.startswith('get_') and 'Dict' in str(func.__annotations__.get('return', '')):
                return {}
            elif func.__name__.startswith('get_'):
                return None
            else:
                return False
    return wrapper


# ==================== 使用範例 ====================

if __name__ == "__main__":
    # 示範如何使用新的控制器
    print("🎯 案件控制器測試")

    try:
        # 初始化控制器
        controller = CaseController("./test_data")

        # 查看系統狀態
        print("\n📊 系統狀態:")
        status = controller.get_controller_status()
        print(f"總案件數: {status['total_cases']}")
        print(f"系統健康: {status['system_health'].get('overall_status', 'unknown')}")

        # 示範建立案件
        from models.case_model import CaseData
        from datetime import datetime

        test_case = CaseData(
            case_id="TEST001",
            client="測試當事人",
            case_type="民事",
            status="待處理",
            notes="測試案件",
            creation_date=datetime.now()
        )

        print(f"\n🏗️ 建立測試案件...")
        if controller.add_case(test_case, create_folder=True):
            print("✅ 案件建立成功")

            # 套用進度範本
            templates = controller.get_available_progress_templates()
            if templates:
                print(f"套用進度範本: {templates[0]}")
                controller.apply_progress_template("TEST001", templates[0])

            # 查看完整資訊
            complete_info = controller.get_case_complete_info("TEST001")
            if complete_info:
                print("✅ 案件完整資訊取得成功")

        print(f"\n📋 系統儀表板:")
        dashboard = controller.get_system_dashboard()
        case_stats = dashboard.get('case_statistics', {})
        print(f"總案件: {case_stats.get('total_cases', 0)}")

    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()