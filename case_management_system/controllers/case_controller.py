from typing import List, Optional
from models.case_model import CaseData
from utils.excel_handler import ExcelHandler
from utils.folder_manager import FolderManager  # 新增導入
from config.settings import AppConfig
import json
import os
from datetime import datetime

class CaseController:
    """案件資料控制器"""

    def __init__(self, data_file: str = None):
        """初始化案件控制器"""
        if data_file is None:
            self.data_file = AppConfig.DATA_CONFIG['case_data_file']
        else:
            self.data_file = data_file

        self.data_folder = os.path.dirname(self.data_file) if os.path.dirname(self.data_file) else '.'
        self.cases: List[CaseData] = []

        # 初始化資料夾管理器
        self.folder_manager = FolderManager(self.data_folder)

        # 確保資料夾存在
        self._ensure_data_folder()

        # 載入案件資料
        self.load_cases()

    def _migrate_case_data(self, case_dict: dict) -> dict:
        """🔥 修正：遷移舊版案件資料到新版格式（支援 experienced_stages）"""
        # 確保所有新欄位都有預設值
        default_fields = {
            'case_reason': None,
            'case_number': None,
            'opposing_party': None,
            'court': None,
            'division': None,
            'progress_date': None,
            'progress_history': {},
            'experienced_stages': []  # 🔥 使用新的欄位名稱
        }

        # 合併預設值和現有資料
        for field, default_value in default_fields.items():
            if field not in case_dict:
                case_dict[field] = default_value

        # 🔥 處理向後相容性：將 completed_stages 轉換為 experienced_stages
        if 'completed_stages' in case_dict and not case_dict.get('experienced_stages'):
            case_dict['experienced_stages'] = case_dict['completed_stages']

        # 🔥 修正：初始化經歷階段
        if not case_dict.get('experienced_stages') and case_dict.get('progress'):
            case_dict['experienced_stages'] = [case_dict['progress']]

        # 🔥 修正：如果有進度但沒有進度歷史，建立基本歷史記錄
        if (case_dict.get('progress') and
            case_dict.get('progress_date') and
            not case_dict.get('progress_history')):
            case_dict['progress_history'] = {
                case_dict['progress']: case_dict['progress_date']
            }

        return case_dict

    def get_case_status_report(self, case_id: str) -> str:
        """取得案件狀態報告（不包含百分比）"""
        try:
            from utils.progress_manager import ProgressManager

            case = self.get_case_by_id(case_id)
            if not case:
                return "案件不存在"

            report = f"案件編號：{case.case_id}\n"
            report += f"當事人：{case.client}\n"
            report += f"案件類型：{case.case_type}\n"
            report += ProgressManager.format_progress_display(case, include_dates=True, include_percentage=False)

            # 經歷階段資訊
            experienced_stages = ProgressManager.get_experienced_stages(case)
            if experienced_stages:
                report += f"\n經歷階段：{' → '.join(experienced_stages)}"

            return report

        except Exception as e:
            print(f"產生狀態報告失敗: {e}")
            return "狀態報告產生失敗"

    def _create_progress_summary(self, case_data):
        """建立進度摘要（不包含百分比）"""
        from utils.progress_manager import ProgressManager

        summary_text = ProgressManager.format_progress_display(
            case_data,
            include_dates=True,
            include_percentage=False  # 🔥 明確設定不包含百分比
        )

        return summary_text


    def display_case_info_tooltip(self, case_data):
        """顯示案件資訊提示（不包含百分比）"""
        from utils.progress_manager import ProgressManager

        tooltip_text = f"案件：{case_data.client}\n"
        tooltip_text += ProgressManager.format_progress_display(
            case_data,
            include_dates=True,
            include_percentage=False  # 🔥 確保不顯示百分比
        )

        return tooltip_text

    def get_case_progress_summary(self, case_id: str) -> dict:
        """
        🔥 新增：取得案件進度摘要

        Args:
            case_id: 案件編號

        Returns:
            dict: 進度摘要
        """
        try:
            from utils.progress_manager import ProgressManager

            case = self.get_case_by_id(case_id)
            if not case:
                return {}

            return ProgressManager.export_progress_summary(case)

        except Exception as e:
            print(f"取得進度摘要失敗: {e}")
            return {}

    def validate_all_case_progress(self) -> List[str]:
        """
        🔥 新增：驗證所有案件的進度一致性

        Returns:
            List[str]: 有問題的案件編號列表
        """
        problematic_cases = []

        for case in self.cases:
            if hasattr(case, 'validate_progress_consistency'):
                if not case.validate_progress_consistency():
                    problematic_cases.append(case.case_id)
                    print(f"案件 {case.case_id} 進度資料不一致")

                    # 自動修復
                    if hasattr(case, 'repair_progress_data'):
                        case.repair_progress_data()
                        print(f"已自動修復案件 {case.case_id} 的進度資料")

        if problematic_cases:
            # 儲存修復後的資料
            self.save_cases()
            print(f"已修復 {len(problematic_cases)} 個案件的進度資料")

        return problematic_cases

    def update_case_progress(self, case_id: str, new_progress: str, progress_date: str = None) -> bool:
        """
        🔥 修正：真正的漸進式更新案件進度

        Args:
            case_id: 案件編號
            new_progress: 新的進度狀態
            progress_date: 進度日期（格式：YYYY-MM-DD），如果為None則使用當前日期

        Returns:
            bool: 是否更新成功
        """
        try:
            case = self.get_case_by_id(case_id)
            if not case:
                raise ValueError(f"找不到案件編號: {case_id}")

            # 記錄更新前的階段
            old_stages = getattr(case, 'experienced_stages', []).copy()
            old_progress = case.progress

            # 🔥 使用案件物件的 update_progress 方法（會自動處理漸進式邏輯）
            case.update_progress(new_progress, progress_date)

            # 取得更新後的階段
            new_stages = getattr(case, 'experienced_stages', [])

            # 儲存資料
            success = self.save_cases()
            if success:
                # 🔥 更新進度資料夾結構（只建立新增的階段資料夾）
                folder_success = self.folder_manager.update_progress_folders(case)

                # 更新案件資訊Excel檔案
                excel_success = self.folder_manager.update_case_info_excel(case)

                if not excel_success:
                    print(f"警告：案件 {case_id} Excel檔案更新失敗")
                if not folder_success:
                    print(f"警告：案件 {case_id} 進度資料夾更新失敗")

                print(f"已更新案件 {case_id} 進度：{old_progress} → {new_progress}")
                print(f"階段變化：{old_stages} → {new_stages}")

                # 🔥 新增：顯示新增的資料夾資訊
                new_stages_added = [stage for stage in new_stages if stage not in old_stages]
                if new_stages_added:
                    print(f"新增進度資料夾：{new_stages_added}")

            return success

        except Exception as e:
            print(f"更新案件進度失敗: {e}")
            return False

    def get_case_progress_history(self, case_id: str) -> dict:
        """
        🔥 新增：取得案件進度歷史

        Args:
            case_id: 案件編號

        Returns:
            dict: 進度歷史記錄 {進度: 日期}
        """
        case = self.get_case_by_id(case_id)
        if case and hasattr(case, 'progress_history'):
            return case.progress_history.copy()
        return {}

    def get_cases_by_progress(self, progress: str) -> List[CaseData]:
        """
        🔥 新增：根據進度狀態取得案件列表

        Args:
            progress: 進度狀態

        Returns:
            List[CaseData]: 符合條件的案件列表
        """
        return [case for case in self.cases if case.progress == progress]

    def get_cases_by_date_range(self, start_date: str, end_date: str) -> List[CaseData]:
        """
        🔥 新增：根據進度日期範圍取得案件列表

        Args:
            start_date: 開始日期 (YYYY-MM-DD)
            end_date: 結束日期 (YYYY-MM-DD)

        Returns:
            List[CaseData]: 符合條件的案件列表
        """
        try:
            result = []
            for case in self.cases:
                if case.progress_date:
                    if start_date <= case.progress_date <= end_date:
                        result.append(case)
            return result
        except Exception as e:
            print(f"根據日期範圍篩選案件失敗: {e}")
            return []


    def _ensure_data_folder(self):
        """確保資料夾存在"""
        try:
            if not os.path.exists(self.data_folder):
                os.makedirs(self.data_folder)
                print(f"建立資料夾：{self.data_folder}")

            # 只建立刑事和民事資料夾
            for folder_name in AppConfig.CASE_TYPE_FOLDERS.values():
                folder_path = os.path.join(self.data_folder, folder_name)
                if not os.path.exists(folder_path):
                    os.makedirs(folder_path)
                    print(f"建立案件類型資料夾：{folder_path}")

        except Exception as e:
            print(f"建立資料夾失敗: {e}")

    def get_data_folder(self) -> str:
        """取得資料資料夾路徑"""
        return self.data_folder

    def get_case_type_folder(self, case_type: str) -> str:
        """取得特定案件類型的資料夾路徑"""
        folder_name = AppConfig.CASE_TYPE_FOLDERS.get(case_type, case_type)
        return os.path.join(self.data_folder, folder_name)

    def load_cases(self) -> bool:
        """載入案件資料"""
        try:
            print(f"嘗試載入案件資料檔案: {self.data_file}")

            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    print(f"從檔案載入 {len(data)} 筆原始資料")

                    # 遷移資料格式
                    migrated_data = [self._migrate_case_data(case_data) for case_data in data]
                    self.cases = [CaseData.from_dict(case_data) for case_data in migrated_data]

                print(f"成功載入 {len(self.cases)} 筆案件資料")

                # 驗證載入的資料
                for i, case in enumerate(self.cases):
                    print(f"案件 {i+1}: {case.case_id} - {case.client} ({case.case_type})")

            else:
                print(f"資料檔案不存在，建立新的空資料庫：{self.data_file}")
                self.cases = []
                # 建立空的資料檔案
                self.save_cases()

            return True

        except Exception as e:
            print(f"載入案件資料失敗: {e}")
            import traceback
            traceback.print_exc()
            self.cases = []
            return False

    def save_cases(self) -> bool:
        """儲存案件資料"""
        try:
            print(f"開始儲存 {len(self.cases)} 筆案件資料到: {self.data_file}")

            data = [case.to_dict() for case in self.cases]

            # 確保資料夾存在
            os.makedirs(os.path.dirname(self.data_file), exist_ok=True)

            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            print(f"成功儲存 {len(self.cases)} 筆案件資料")

            # 驗證儲存的資料
            with open(self.data_file, 'r', encoding='utf-8') as f:
                saved_data = json.load(f)
                print(f"驗證：檔案中有 {len(saved_data)} 筆資料")

            return True

        except Exception as e:
            print(f"儲存案件資料失敗: {e}")
            import traceback
            traceback.print_exc()
            return False

    def add_case(self, case: CaseData) -> bool:
        """🔥 修正：新增案件（確保只建立當前進度的資料夾）"""
        try:
            # 檢查案件編號是否重複
            if any(c.case_id == case.case_id for c in self.cases):
                raise ValueError(f"案件編號 {case.case_id} 已存在")

            # 🔥 確保新案件的進度資料正確初始化
            if not hasattr(case, 'experienced_stages') or not case.experienced_stages:
                case.experienced_stages = [case.progress] if case.progress else []

            if case.progress and case.progress_date:
                if not hasattr(case, 'progress_history') or not case.progress_history:
                    case.progress_history = {case.progress: case.progress_date}

            # 新增案件到列表
            self.cases.append(case)

            # 儲存案件資料
            success = self.save_cases()
            if not success:
                # 如果儲存失敗，從列表中移除
                self.cases.remove(case)
                return False

            # 🔥 建立案件資料夾結構（只建立當前進度）
            folder_success = self.folder_manager.create_case_folder_structure(case)
            if not folder_success:
                print(f"警告：案件 {case.case_id} 資料夾結構建立失敗")
                # 注意：這裡不回傳False，因為案件資料已經成功儲存

            print(f"已新增案件：{case.case_id}")
            print(f"初始進度：{case.progress}")
            print(f"初始階段：{case.experienced_stages}")
            return True

        except Exception as e:
            print(f"新增案件失敗: {e}")
            return False

    def update_case(self, case_id: str, updated_case: CaseData) -> bool:
        """🔥 修正：更新案件（處理進度變更和資料夾同步）"""
        try:
            for i, case in enumerate(self.cases):
                if case.case_id == case_id:
                    # 記錄更新前的階段
                    old_stages = getattr(case, 'experienced_stages', []).copy()
                    old_progress = case.progress

                    # 更新案件資料
                    updated_case.updated_date = datetime.now()
                    self.cases[i] = updated_case

                    # 取得更新後的階段
                    new_stages = getattr(updated_case, 'experienced_stages', [])
                    new_progress = updated_case.progress

                    # 儲存案件資料
                    success = self.save_cases()
                    if success:
                        # 🔥 如果有新的進度階段，更新資料夾結構
                        if old_progress != new_progress or old_stages != new_stages:
                            folder_success = self.folder_manager.update_progress_folders(updated_case)
                            if not folder_success:
                                print(f"警告：案件 {case_id} 進度資料夾更新失敗")

                        # 更新案件資訊Excel檔案
                        excel_success = self.folder_manager.update_case_info_excel(updated_case)
                        if not excel_success:
                            print(f"警告：案件 {case_id} Excel檔案更新失敗")

                        print(f"已更新案件：{case_id}")
                        if old_progress != new_progress:
                            print(f"進度變更：{old_progress} → {new_progress}")
                            print(f"階段變化：{old_stages} → {new_stages}")

                    return success

            raise ValueError(f"找不到案件編號: {case_id}")

        except Exception as e:
            print(f"更新案件失敗: {e}")
            return False

    def get_case_folder_path(self, case_id: str) -> Optional[str]:
        """取得指定案件的資料夾路徑"""
        case = self.get_case_by_id(case_id)
        if case:
            return self.folder_manager.get_case_folder_path(case)
        return None

    def delete_case(self, case_id: str) -> bool:
        """刪除案件"""
        try:
            original_count = len(self.cases)
            self.cases = [case for case in self.cases if case.case_id != case_id]

            if len(self.cases) < original_count:
                success = self.save_cases()
                if success:
                    print(f"已刪除案件：{case_id}")
                return success
            else:
                raise ValueError(f"找不到案件編號: {case_id}")
        except Exception as e:
            print(f"刪除案件失敗: {e}")
            return False

    def get_cases(self) -> List[CaseData]:
        """取得所有案件"""
        return self.cases.copy()

    def get_case_by_id(self, case_id: str) -> Optional[CaseData]:
        """根據編號取得案件"""
        for case in self.cases:
            if case.case_id == case_id:
                return case
        return None

    def search_cases(self, keyword: str) -> List[CaseData]:
        """搜尋案件"""
        results = []
        keyword = keyword.lower()

        for case in self.cases:
            if (keyword in case.case_id.lower() or
                keyword in case.case_type.lower() or
                keyword in case.client.lower() or
                (case.lawyer and keyword in case.lawyer.lower()) or
                (case.legal_affairs and keyword in case.legal_affairs.lower()) or
                keyword in case.progress.lower()):
                results.append(case)

        return results

    def export_to_excel(self, file_path: str = None) -> bool:
        """匯出案件資料到 Excel"""
        try:
            if file_path is None:
                # 使用預設的匯出路徑（直接放在資料夾根目錄）
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"案件資料匯出_{timestamp}.xlsx"
                file_path = os.path.join(self.data_folder, filename)

            success = ExcelHandler.export_cases_to_excel(self.cases, file_path)
            if success:
                print(f"已匯出案件資料到：{file_path}")
            return success
        except Exception as e:
            print(f"匯出Excel失敗: {e}")
            return False

    def import_from_excel(self, file_path: str) -> bool:
        """從 Excel 匯入案件資料"""
        try:
            imported_cases = ExcelHandler.import_cases_from_excel(file_path)
            if imported_cases:
                # 合併資料（避免重複）
                existing_ids = {case.case_id for case in self.cases}
                new_cases = []
                updated_count = 0

                for case in imported_cases:
                    if case.case_id not in existing_ids:
                        new_cases.append(case)
                    else:
                        # 更新現有案件
                        for i, existing_case in enumerate(self.cases):
                            if existing_case.case_id == case.case_id:
                                case.updated_date = datetime.now()
                                self.cases[i] = case
                                updated_count += 1
                                break

                self.cases.extend(new_cases)
                success = self.save_cases()

                if success:
                    print(f"匯入成功：新增 {len(new_cases)} 筆案件，更新 {updated_count} 筆案件")

                return success
            return False
        except Exception as e:
            print(f"匯入Excel失敗: {e}")
            return False

    def generate_case_id(self) -> str:
        """產生新的案件編號"""
        try:
            existing_ids = {case.case_id for case in self.cases}
            year = datetime.now().year

            for i in range(1, 10000):
                case_id = f"C{year}{i:04d}"
                if case_id not in existing_ids:
                    return case_id

            raise RuntimeError("無法產生唯一的案件編號")
        except Exception as e:
            print(f"產生案件編號失敗: {e}")
            return f"C{datetime.now().year}0001"

    def get_statistics(self) -> dict:
        """取得案件統計資訊（使用 ProgressManager）"""
        try:
            from utils.progress_manager import ProgressManager

            # 使用 ProgressManager 取得統計
            stats = ProgressManager.get_progress_statistics(self.cases)

            # 添加其他統計資訊
            stats.update({
                'lawyer_stats': {},
                'legal_affairs_stats': {}
            })

            for case in self.cases:
                # 律師統計
                lawyer = case.lawyer or '未指派'
                stats['lawyer_stats'][lawyer] = stats['lawyer_stats'].get(lawyer, 0) + 1

                # 法務統計
                legal_affairs = case.legal_affairs or '未指派'
                stats['legal_affairs_stats'][legal_affairs] = stats['legal_affairs_stats'].get(legal_affairs, 0) + 1

            return stats
        except Exception as e:
            print(f"取得統計資訊失敗: {e}")
            return {}

    def get_overdue_cases(self, days_threshold: int = 30) -> List[CaseData]:
        """
        🔥 新增：取得逾期案件（使用 ProgressManager）
        """
        from utils.progress_manager import ProgressManager
        return ProgressManager.get_overdue_cases(self.cases, days_threshold)