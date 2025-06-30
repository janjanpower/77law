from typing import Dict, List, Optional, Tuple
from models.case_model import CaseData
from utils.excel_handler import ExcelHandler
from utils.folder_manager import FolderManager
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
        self.folder_manager = FolderManager(self.data_folder)
        self.excel_handler = ExcelHandler()

        # Google Drive 同步支援（替換原來的雲端同步）
        try:
            from utils.google_drive_sync import GoogleDriveSync
            self.google_drive_sync = GoogleDriveSync()
            self.google_drive_sync.load_config()

            # 如果啟用了同步，啟動自動同步
            if self.google_drive_sync.is_enabled:
                self.google_drive_sync.start_auto_sync(self.data_file)
        except ImportError:
            self.google_drive_sync = None

        self.cases = []
        self.load_cases()

    def _migrate_case_data(self, case_dict: dict) -> dict:
        """遷移舊版案件資料到新版格式 - 🔥 修改：新增備註欄位"""
        # 確保所有新欄位都有預設值
        default_fields = {
            'case_reason': None,
            'case_number': None,
            'opposing_party': None,
            'court': None,
            'division': None,
            'progress_date': None,
            'progress_stages': {},
            'progress_notes': {},  # 🔥 新增：備註欄位預設值
            'progress_times': {}   # 🔥 新增：時間欄位預設值
        }

        # 合併預設值和現有資料
        for field, default_value in default_fields.items():
            if field not in case_dict:
                case_dict[field] = default_value

        # 處理舊資料轉換
        if not case_dict.get('progress_stages'):
            progress_stages = {}

            # 從 progress_history 轉換
            if case_dict.get('progress_history'):
                progress_stages = case_dict['progress_history']
            # 從當前進度建立基本記錄
            elif case_dict.get('progress') and case_dict.get('progress_date'):
                progress_stages = {case_dict['progress']: case_dict['progress_date']}

            case_dict['progress_stages'] = progress_stages

        # 🔥 新增：確保備註和時間欄位存在
        if not case_dict.get('progress_notes'):
            case_dict['progress_notes'] = {}
        if not case_dict.get('progress_times'):
            case_dict['progress_times'] = {}

        return case_dict

    def _ensure_data_folder(self):
        """確保資料夾存在"""
        try:
            if not os.path.exists(self.data_folder):
                os.makedirs(self.data_folder)
                print(f"建立資料夾：{self.data_folder}")

            # 建立案件類型資料夾
            for folder_name in AppConfig.CASE_TYPE_FOLDERS.values():
                folder_path = os.path.join(self.data_folder, folder_name)
                if not os.path.exists(folder_path):
                    os.makedirs(folder_path)
                    print(f"建立案件類型資料夾：{folder_path}")

        except Exception as e:
            print(f"建立資料夾失敗: {e}")

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
            else:
                print(f"資料檔案不存在，建立新的空資料庫：{self.data_file}")
                self.cases = []
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

            # Google Drive 自動同步（替換原來的雲端同步）
            if self.google_drive_sync and self.google_drive_sync.is_enabled:
                try:
                    self.google_drive_sync.auto_sync(self.data_file)
                except Exception as e:
                    print(f"Google Drive 同步失敗: {e}")

            return True

        except Exception as e:
            print(f"儲存案件資料失敗: {e}")
            import traceback
            traceback.print_exc()
            return False

    def add_case(self, case: CaseData) -> bool:
        """新增案件 - 使用統一顯示格式"""
        try:
            # 檢查案件編號是否重複
            if any(c.case_id == case.case_id for c in self.cases):
                raise ValueError(f"案件編號 {case.case_id} 已存在")

            # 新增案件到列表
            self.cases.append(case)

            # 儲存案件資料
            success = self.save_cases()
            if not success:
                self.cases.remove(case)
                return False

            # 建立案件資料夾結構
            folder_success = self.folder_manager.create_case_folder_structure(case)
            if not folder_success:
                case_display_name = AppConfig.format_case_display_name(case)
                print(f"警告：案件 {case_display_name} 資料夾結構建立失敗")

            case_display_name = AppConfig.format_case_display_name(case)
            print(f"已新增案件：{case_display_name}")
            return True

        except Exception as e:
            print(f"新增案件失敗: {e}")
            return False

    def update_case(self, case_id: str, updated_case: CaseData) -> bool:
        """更新案件 - 使用統一顯示格式"""
        try:
            for i, case in enumerate(self.cases):
                if case.case_id == case_id:
                    updated_case.updated_date = datetime.now()
                    self.cases[i] = updated_case

                    success = self.save_cases()
                    if success:
                        # 更新案件資訊Excel檔案
                        excel_success = self.folder_manager.update_case_info_excel(updated_case)
                        if not excel_success:
                            case_display_name = AppConfig.format_case_display_name(updated_case)
                            print(f"警告：案件 {case_display_name} Excel檔案更新失敗")

                        case_display_name = AppConfig.format_case_display_name(updated_case)
                        print(f"已更新案件：{case_display_name}")

                    return success

            raise ValueError(f"找不到案件編號: {case_id}")

        except Exception as e:
            print(f"更新案件失敗: {e}")
            return False

    def add_case_progress_stage(self, case_id: str, stage_name: str, stage_date: str = None, note: str = None, time: str = None) -> bool:
        """新增案件進度階段 - 🔥 修改：支援備註和時間"""
        try:
            case = self.get_case_by_id(case_id)
            if not case:
                raise ValueError(f"找不到案件編號: {case_id}")

            case.add_progress_stage(stage_name, stage_date, note, time)  # 🔥 修改：傳入時間

            success = self.save_cases()
            if success:
                # 建立對應的資料夾
                self.folder_manager.create_progress_folder(case, stage_name)
                self.folder_manager.update_case_info_excel(case)
                case_display_name = AppConfig.format_case_display_name(case)
                print(f"已新增案件 {case_display_name} 的階段 {stage_name}")

            return success

        except Exception as e:
            print(f"新增案件進度階段失敗: {e}")
            return False

    def update_case_progress_stage(self, case_id: str, stage_name: str, stage_date: str, note: str = None, time: str = None) -> bool:
        """更新案件進度階段 - 🔥 修改：支援備註和時間"""
        try:
            case = self.get_case_by_id(case_id)
            if not case:
                raise ValueError(f"找不到案件編號: {case_id}")

            case.update_stage_date(stage_name, stage_date)

            # 🔥 新增：更新備註
            if note is not None:  # 允許空字串來清除備註
                case.update_stage_note(stage_name, note)

            # 🔥 新增：更新時間
            if time is not None:  # 允許空字串來清除時間
                case.update_stage_time(stage_name, time)

            success = self.save_cases()
            if success:
                # 更新資料夾和Excel
                self.folder_manager.update_case_info_excel(case)
                case_display_name = AppConfig.format_case_display_name(case)
                print(f"已更新案件 {case_display_name} 的階段 {stage_name} 日期為 {stage_date}")
                if note:
                    print(f"同時更新備註：{note[:20]}...")
                if time:
                    print(f"同時更新時間：{time}")

            return success

        except Exception as e:
            print(f"更新案件進度階段失敗: {e}")
            return False

    def remove_case_progress_stage(self, case_id: str, stage_name: str) -> bool:
        """移除案件進度階段 - 使用統一顯示格式"""
        try:
            case = self.get_case_by_id(case_id)
            if not case:
                raise ValueError(f"找不到案件編號: {case_id}")

            # 先刪除對應的資料夾
            print(f"準備刪除階段 {stage_name} 的資料夾...")
            folder_success = self.folder_manager.delete_progress_folder(case, stage_name)

            if folder_success:
                print(f"階段資料夾刪除成功: {stage_name}")
            else:
                print(f"階段資料夾刪除失敗或不存在: {stage_name}")

            # 再移除進度階段記錄
            success = case.remove_progress_stage(stage_name)
            if success:
                # 儲存更新後的案件資料
                save_success = self.save_cases()
                if save_success:
                    # 更新Excel檔案
                    self.folder_manager.update_case_info_excel(case)
                    case_display_name = AppConfig.format_case_display_name(case)
                    print(f"已移除案件 {case_display_name} 的階段 {stage_name}")

                    if not folder_success:
                        print(f"警告：階段記錄已移除，但資料夾刪除失敗")

                    return True
                else:
                    print(f"階段記錄移除成功，但儲存案件資料失敗")
                    return False
            else:
                print(f"移除階段記錄失敗")
                return False

        except Exception as e:
            print(f"移除案件進度階段失敗: {e}")
            import traceback
            traceback.print_exc()
            return False

    def delete_case(self, case_id: str, delete_folder: bool = True) -> bool:
        """刪除案件 - 使用統一顯示格式"""
        try:
            # 找到要刪除的案件
            case_to_delete = None
            for case in self.cases:
                if case.case_id == case_id:
                    case_to_delete = case
                    break

            if not case_to_delete:
                raise ValueError(f"找不到案件編號: {case_id}")

            case_display_name = AppConfig.format_case_display_name(case_to_delete)

            # 如果需要刪除資料夾
            folder_success = True
            if delete_folder:
                print(f"準備刪除案件 {case_display_name} 的資料夾...")
                folder_success = self.folder_manager.delete_case_folder(case_to_delete)

                if folder_success:
                    print(f"案件資料夾刪除成功: {case_display_name}")
                else:
                    print(f"案件資料夾刪除失敗或不存在: {case_display_name}")

            # 從列表中移除案件
            original_count = len(self.cases)
            self.cases = [case for case in self.cases if case.case_id != case_id]

            if len(self.cases) < original_count:
                success = self.save_cases()
                if success:
                    print(f"已刪除案件：{case_display_name}")

                    if delete_folder and not folder_success:
                        print(f"警告：案件記錄已刪除，但資料夾刪除失敗")

                    return True
                else:
                    # 如果儲存失敗，恢復案件
                    self.cases.append(case_to_delete)
                    print(f"儲存失敗，已恢復案件記錄")
                    return False
            else:
                raise ValueError(f"找不到案件編號: {case_id}")

        except Exception as e:
            print(f"刪除案件失敗: {e}")
            import traceback
            traceback.print_exc()
            return False

    def get_case_folder_info(self, case_id: str) -> dict:
        """取得案件資料夾資訊（用於刪除前檢查）"""
        try:
            case = self.get_case_by_id(case_id)
            if not case:
                return {'exists': False}

            return self.folder_manager.get_case_folder_info(case)
        except Exception as e:
            print(f"取得案件資料夾資訊失敗: {e}")
            return {'exists': False}

    def get_cases(self) -> List[CaseData]:
        """取得所有案件"""
        return self.cases.copy()

    def get_case_by_id(self, case_id: str) -> Optional[CaseData]:
        """根據編號取得案件"""
        for case in self.cases:
            if case.case_id == case_id:
                return case
        return None

    def get_case_folder_path(self, case_id: str) -> Optional[str]:
        """取得指定案件的資料夾路徑"""
        case = self.get_case_by_id(case_id)
        if case:
            return self.folder_manager.get_case_folder_path(case)
        return None

    def get_case_stage_folder_path(self, case_id: str, stage_name: str) -> Optional[str]:
        """取得案件特定階段的資料夾路徑"""
        case = self.get_case_by_id(case_id)
        if case:
            case_folder = self.folder_manager.get_case_folder_path(case)
            if case_folder:
                return os.path.join(case_folder, '進度追蹤', stage_name)
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
                existing_ids = {case.case_id for case in self.cases}
                new_cases = []
                updated_count = 0

                for case in imported_cases:
                    if case.case_id not in existing_ids:
                        new_cases.append(case)
                    else:
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
        """產生新的案件編號 - 民國年分(三碼)+XXX(三碼)格式"""
        try:
            import datetime

            # 計算民國年分
            current_year = datetime.datetime.now().year
            minguo_year = current_year - 1911

            # 取得現有所有案件編號
            existing_ids = {case.case_id for case in self.cases}

            # 找出當年度最大編號
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

    def validate_case_id_format(self, case_id: str) -> bool:
        """驗證案件編號格式"""
        if not case_id or len(case_id) != 6:
            return False

        try:
            # 檢查前三碼是否為數字（民國年分）
            year_part = int(case_id[:3])
            # 檢查後三碼是否為數字（流水號）
            number_part = int(case_id[3:])

            # 基本範圍檢查
            if year_part < 100 or year_part > 200:  # 民國100-200年合理範圍
                return False
            if number_part < 1 or number_part > 999:
                return False

            return True
        except ValueError:
            return False

    def check_case_id_duplicate(self, case_id: str, exclude_case_id: str = None) -> bool:
        """檢查案件編號是否重複"""
        for case in self.cases:
            if case.case_id == case_id and case.case_id != exclude_case_id:
                return True
        return False

    def update_case_id(self, old_case_id: str, new_case_id: str) -> tuple:
        """更新案件編號 - 修正返回值處理"""
        try:
            # 驗證新編號格式
            if not self.validate_case_id_format(new_case_id):
                return False, "案件編號格式錯誤，應為6位數字(民國年分3碼+流水號3碼)"

            # 檢查是否重複
            if self.check_case_id_duplicate(new_case_id, old_case_id):
                return False, f"案件編號 {new_case_id} 已存在"

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


    def get_statistics(self) -> dict:
        """取得案件統計資訊"""
        try:
            stats = {
                'total_cases': len(self.cases),
                'progress_distribution': {},
                'case_type_distribution': {},
                'lawyer_stats': {},
                'legal_affairs_stats': {}
            }

            for case in self.cases:
                # 進度分布
                progress = case.progress
                stats['progress_distribution'][progress] = stats['progress_distribution'].get(progress, 0) + 1

                # 案件類型分布
                case_type = case.case_type
                stats['case_type_distribution'][case_type] = stats['case_type_distribution'].get(case_type, 0) + 1

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

    def import_cases_from_excel_auto(self, file_path: str) -> Tuple[bool, str]:
        """
        自動識別Excel工作表並匯入案件資料

        Args:
            file_path: Excel檔案路徑

        Returns:
            Tuple[bool, str]: (成功狀態, 結果訊息)
        """
        try:
            # 先分析Excel檔案
            analyze_success, analyze_message, categorized_sheets = ExcelHandler.analyze_excel_sheets(file_path)

            if not analyze_success:
                return False, analyze_message

            # 準備要匯入的工作表
            sheets_to_import = {}
            if categorized_sheets['民事']:
                sheets_to_import['民事'] = categorized_sheets['民事']
            if categorized_sheets['刑事']:
                sheets_to_import['刑事'] = categorized_sheets['刑事']

            if not sheets_to_import:
                return False, "沒有找到民事或刑事相關的工作表"

            # 執行匯入
            import_success, import_message, all_cases = ExcelHandler.import_cases_from_multiple_sheets(
                file_path, sheets_to_import
            )

            if not import_success:
                return False, import_message

            # 批量新增案件
            total_added = 0
            total_duplicates = 0
            error_cases = []

            for case_type, cases in all_cases.items():
                for case in cases:
                    try:
                        # 產生案件編號
                        case.case_id = self.generate_case_id()

                        # 修改：檢查是否重複（根據當事人、案件類型和案號）
                        case_number = getattr(case, 'case_number', '') or ''
                        existing_case = self._find_existing_case_by_client_and_number(
                            case.client, case.case_type, case_number
                        )

                        if existing_case:
                            total_duplicates += 1
                            continue

                        # 新增案件
                        if self.add_case(case):
                            total_added += 1
                        else:
                            error_cases.append(case.client)

                    except Exception as e:
                        error_cases.append(f"{case.client}: {str(e)}")
                        continue

            # 建立最終結果訊息
            final_message = f"📋 Excel匯入結果\n\n"
            final_message += f"🔍 檔案分析結果：\n{analyze_message}\n\n"
            final_message += f"✅ 成功新增：{total_added} 筆案件\n"

            if total_duplicates > 0:
                final_message += f"⚠️ 重複跳過：{total_duplicates} 筆案件\n"

            if error_cases:
                final_message += f"❌ 新增失敗：{len(error_cases)} 筆案件\n"
                final_message += f"失敗案件：{', '.join(error_cases[:3])}"
                if len(error_cases) > 3:
                    final_message += f"...等 {len(error_cases)} 筆"

            return total_added > 0, final_message

        except Exception as e:
            return False, f"匯入過程發生錯誤：{str(e)}"

    def import_cases_from_sheet(self, file_path: str, case_type: str) -> Tuple[bool, str]:
        """
        從Excel工作表匯入案件資料

        Args:
            file_path: Excel檔案路徑
            case_type: 案件類型

        Returns:
            Tuple[bool, str]: (成功狀態, 結果訊息)
        """
        try:
            # 使用ExcelHandler解析Excel檔案
            success, message, cases = ExcelHandler.import_cases_from_sheet_with_mapping(file_path, case_type)

            if not success:
                return False, message

            if not cases:
                return False, "沒有找到有效的案件資料"

            # 批量新增案件
            added_count = 0
            duplicate_count = 0
            error_cases = []

            for case in cases:
                try:
                    # 產生案件編號
                    case.case_id = self.generate_case_id()

                    # 修改：檢查是否重複（以當事人、案件類型和案號為檢查依據）
                    case_number = getattr(case, 'case_number', '') or ''
                    existing_case = self._find_existing_case_by_client_and_number(
                        case.client, case.case_type, case_number
                    )

                    if existing_case:
                        duplicate_count += 1
                        continue

                    # 新增案件
                    if self.add_case(case):
                        added_count += 1
                    else:
                        error_cases.append(case.client)

                except Exception as e:
                    error_cases.append(f"{case.client}: {str(e)}")
                    continue

            # 建立結果訊息
            result_message = f"匯入完成！\n\n成功新增：{added_count} 筆案件"

            if duplicate_count > 0:
                result_message += f"\n重複跳過：{duplicate_count} 筆案件"

            if error_cases:
                result_message += f"\n新增失敗：{len(error_cases)} 筆案件"
                result_message += "\n失敗原因：" + "、".join(error_cases[:3])
                if len(error_cases) > 3:
                    result_message += f"...等 {len(error_cases)} 項"

            return added_count > 0, result_message

        except Exception as e:
            return False, f"匯入過程發生錯誤：{str(e)}"

    def _find_existing_case_by_client_and_number(self, client_name: str, case_type: str, case_number: str = None) -> Optional[CaseData]:
        """
        根據當事人姓名、案件類型和案號查找現有案件

        Args:
            client_name: 當事人姓名
            case_type: 案件類型
            case_number: 案號（可選）

        Returns:
            Optional[CaseData]: 找到的案件或None
        """
        for case in self.cases:
            # 檢查當事人和案件類型是否相同
            if (case.client.strip().lower() == client_name.strip().lower() and
                case.case_type == case_type):

                # 如果提供了案號，則必須案號也相同才算重複
                if case_number:
                    existing_case_number = getattr(case, 'case_number', '') or ''
                    if existing_case_number.strip() == case_number.strip():
                        return case
                else:
                    # 如果沒有提供案號，檢查現有案件是否也沒有案號
                    existing_case_number = getattr(case, 'case_number', '') or ''
                    if not existing_case_number.strip():
                        return case

        return None

    def setup_google_drive_sync(self) -> Tuple[bool, str]:
        """設定 Google Drive 同步"""
        if not self.google_drive_sync:
            return False, "Google Drive 同步模組未載入"
        return self.google_drive_sync.setup_google_drive_sync()

    def get_google_drive_status(self) -> Dict:
        """取得 Google Drive 同步狀態"""
        if not self.google_drive_sync:
            return {'enabled': False}
        return self.google_drive_sync.get_sync_status()