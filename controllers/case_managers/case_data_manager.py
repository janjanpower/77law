#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
案件資料管理器 - 修正版本
主要修改：案件編號生成邏輯改為民國年+流水號格式
"""

import json
import os
from datetime import datetime
from typing import List, Optional, Tuple
from models.case_model import CaseData
from config.settings import AppConfig
from utils.event_manager import event_manager, EventType


class CaseDataManager:
    """案件資料管理器 - 修正版本"""

    def __init__(self, data_file: str, data_folder: str):
        """
        初始化資料管理器

        Args:
            data_file: 資料檔案路徑
            data_folder: 資料資料夾路徑
        """
        self.data_file = data_file
        self.data_folder = data_folder
        self.cases = []

    def load_cases(self) -> bool:
        """載入案件資料"""
        try:
            if not os.path.exists(self.data_file):
                print(f"資料檔案不存在，將建立新檔案: {self.data_file}")
                self.cases = []
                return True

            with open(self.data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.cases = []
            for case_dict in data:
                try:
                    case = CaseData.from_dict(case_dict)
                    self.cases.append(case)
                except Exception as e:
                    print(f"解析案件資料失敗: {case_dict.get('case_id', '未知')}, 錯誤: {e}")
                    continue

            print(f"成功載入 {len(self.cases)} 筆案件資料")
            return True

        except Exception as e:
            print(f"載入案件資料失敗: {e}")
            self.cases = []
            return False

    def save_cases(self) -> bool:
        """儲存案件資料"""
        try:
            # 確保資料夾存在
            os.makedirs(os.path.dirname(self.data_file), exist_ok=True)

            # 將案件資料轉換為字典格式
            data = [case.to_dict() for case in self.cases]

            # 儲存到檔案
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            print(f"成功儲存 {len(self.cases)} 筆案件資料到 {self.data_file}")
            return True

        except Exception as e:
            print(f"儲存案件資料失敗: {e}")
            return False

    def add_case(self, case_data: CaseData) -> bool:
        """新增案件"""
        try:
            # 如果沒有案件編號，自動生成
            if not case_data.case_id:
                case_data.case_id = self.generate_case_id(case_data.case_type)

            # 檢查編號重複
            if self._is_case_id_duplicate(case_data.case_id, case_data.case_type):
                print(f"案件編號重複: {case_data.case_id}")
                return False

            # 設定建立時間
            case_data.created_date = datetime.now()
            case_data.updated_date = datetime.now()

            # 新增到列表
            self.cases.append(case_data)

            # 儲存資料
            success = self.save_cases()
            if success:
                # 發布案件新增事件
                try:
                    event_manager.publish(EventType.CASE_ADDED, {
                        'case': case_data,
                        'case_id': case_data.case_id,
                        'case_type': case_data.case_type,
                        'client': case_data.client
                    })
                except Exception as e:
                    print(f"發布事件失敗: {e}")

                case_display_name = AppConfig.format_case_display_name(case_data)
                print(f"成功新增案件：{case_data.case_id} - {case_display_name}")

            return success

        except Exception as e:
            print(f"新增案件失敗: {e}")
            import traceback
            traceback.print_exc()
            return False

    def update_case(self, case_data: CaseData) -> bool:
        """更新案件"""
        try:
            # 找到要更新的案件
            case_index = None
            for i, case in enumerate(self.cases):
                if case.case_id == case_data.case_id and case.case_type == case_data.case_type:
                    case_index = i
                    break

            if case_index is None:
                print(f"找不到要更新的案件: {case_data.case_id}")
                return False

            # 更新時間
            case_data.updated_date = datetime.now()

            # 更新案件
            self.cases[case_index] = case_data

            # 儲存資料
            success = self.save_cases()
            if success:
                # 發布案件更新事件
                try:
                    event_manager.publish(EventType.CASE_UPDATED, {
                        'case': case_data,
                        'case_id': case_data.case_id,
                        'case_type': case_data.case_type,
                        'client': case_data.client,
                        'action': 'case_updated'
                    })
                except Exception as e:
                    print(f"發布事件失敗: {e}")

                case_display_name = AppConfig.format_case_display_name(case_data)
                print(f"成功更新案件：{case_data.case_id} - {case_display_name}")

            return success

        except Exception as e:
            print(f"更新案件失敗: {e}")
            import traceback
            traceback.print_exc()
            return False

    def delete_case(self, case_id: str, case_type: str) -> bool:
        """
        刪除案件 - 確保參數一致

        Args:
            case_id: 案件編號
            case_type: 案件類型

        Returns:
            bool: 是否刪除成功
        """
        try:
            # 找到要刪除的案件
            case_index = None
            deleted_case = None
            for i, case in enumerate(self.cases):
                if case.case_id == case_id and case.case_type == case_type:
                    case_index = i
                    deleted_case = case
                    break

            if case_index is None:
                print(f"找不到要刪除的案件: {case_id} (類型: {case_type})")
                return False

            # 從列表中移除
            self.cases.pop(case_index)

            # 儲存資料
            success = self.save_cases()
            if success:
                # 發布案件刪除事件
                try:
                    event_manager.publish(EventType.CASE_DELETED, {
                        'case_id': case_id,
                        'case_type': case_type,
                        'client': deleted_case.client if deleted_case else None
                    })
                except Exception as e:
                    print(f"發布事件失敗: {e}")

                case_display_name = AppConfig.format_case_display_name(deleted_case)
                print(f"成功刪除案件：{case_id} - {case_display_name}")
            else:
                # 如果儲存失敗，還原案件
                self.cases.insert(case_index, deleted_case)

            return success

        except Exception as e:
            print(f"刪除案件失敗: {e}")
            import traceback
            traceback.print_exc()
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



    def _find_case_excel_file(self, case_info_folder: str, case_id: str, client_name: str) -> Optional[str]:
        """
        尋找案件的Excel檔案 - CaseDataManager的輔助方法

        Args:
            case_info_folder: 案件資訊資料夾路徑
            case_id: 案件編號
            client_name: 當事人姓名

        Returns:
            Optional[str]: Excel檔案路徑或None
        """
        try:
            if not os.path.exists(case_info_folder):
                return None

            # 策略1：尋找包含案件編號的Excel檔案
            for filename in os.listdir(case_info_folder):
                if (filename.endswith('.xlsx') and
                    case_id in filename and
                    '案件資訊' in filename):
                    return os.path.join(case_info_folder, filename)

            # 策略2：尋找包含當事人姓名的Excel檔案
            clean_client = self._sanitize_name_for_filename(client_name)
            for filename in os.listdir(case_info_folder):
                if (filename.endswith('.xlsx') and
                    clean_client in filename and
                    '案件資訊' in filename):
                    return os.path.join(case_info_folder, filename)

            # 策略3：尋找任何案件資訊Excel檔案
            for filename in os.listdir(case_info_folder):
                if filename.endswith('.xlsx') and '案件資訊' in filename:
                    return os.path.join(case_info_folder, filename)

            return None

        except Exception as e:
            print(f"❌ 尋找Excel檔案失敗: {e}")
            return None

    def _generate_excel_filename(self, case_id: str, client_name: str) -> str:
        """
        產生Excel檔案名稱 - CaseDataManager的輔助方法

        Args:
            case_id: 案件編號
            client_name: 當事人姓名

        Returns:
            str: Excel檔案名稱
        """
        try:
            clean_client = self._sanitize_name_for_filename(client_name)
            return f"{case_id}_{clean_client}_案件資訊.xlsx"
        except Exception as e:
            print(f"❌ 產生Excel檔案名稱失敗: {e}")
            return f"{case_id}_案件資訊.xlsx"

    def _sanitize_name_for_filename(self, name: str) -> str:
        """
        清理名稱用於檔案命名 - CaseDataManager的輔助方法

        Args:
            name: 原始名稱

        Returns:
            str: 清理後的名稱
        """
        try:
            # 移除檔案名不允許的字元
            invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
            clean_name = name

            for char in invalid_chars:
                clean_name = clean_name.replace(char, '_')

            # 移除多餘的空格和點
            clean_name = clean_name.strip(' .')

            # 限制長度
            if len(clean_name) > 20:
                clean_name = clean_name[:20]

            # 確保不為空
            if not clean_name:
                clean_name = "客戶"

            return clean_name

        except Exception as e:
            print(f"❌ 清理名稱失敗: {e}")
            return "客戶"

    def _sanitize_name_for_folder(self, name: str) -> str:
        """
        清理名稱用於資料夾命名 - CaseDataManager的輔助方法

        Args:
            name: 原始名稱

        Returns:
            str: 清理後的名稱
        """
        try:
            # 移除資料夾名不允許的字元
            invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
            clean_name = name

            for char in invalid_chars:
                clean_name = clean_name.replace(char, '_')

            clean_name = clean_name.strip(' .')

            # 限制長度
            if len(clean_name) > 50:
                clean_name = clean_name[:50]

            if not clean_name:
                clean_name = "未知客戶"

            return clean_name

        except Exception as e:
            print(f"❌ 清理資料夾名稱失敗: {e}")
            return "未知客戶"

    def _create_simple_excel_file(self, case_data: CaseData, excel_file_path: str) -> bool:
        """
        建立簡單的Excel檔案 - CaseDataManager的輔助方法

        Args:
            case_data: 案件資料
            excel_file_path: Excel檔案路徑

        Returns:
            bool: 建立是否成功
        """
        try:
            import pandas as pd

            # 基本資訊
            basic_info = [
                ['案件編號', case_data.case_id],
                ['案件類型', case_data.case_type],
                ['當事人', case_data.client],
                ['委任律師', getattr(case_data, 'lawyer', '') or ''],
                ['法務', getattr(case_data, 'legal_affairs', '') or ''],
                ['目前進度', case_data.progress],
                ['進度日期', case_data.progress_date or ''],
                ['建立日期', case_data.created_date.strftime('%Y-%m-%d %H:%M:%S') if case_data.created_date else ''],
                ['更新日期', case_data.updated_date.strftime('%Y-%m-%d %H:%M:%S') if case_data.updated_date else '']
            ]

            # 詳細資訊
            detail_info = [
                ['案由', getattr(case_data, 'case_reason', '') or ''],
                ['案號', getattr(case_data, 'case_number', '') or ''],
                ['對造', getattr(case_data, 'opposing_party', '') or ''],
                ['負責法院', getattr(case_data, 'court', '') or ''],
                ['負責股別', getattr(case_data, 'division', '') or '']
            ]

            # 寫入Excel檔案
            with pd.ExcelWriter(excel_file_path, engine='openpyxl') as writer:
                # 基本資訊工作表
                df_basic = pd.DataFrame(basic_info, columns=['項目', '內容'])
                df_basic.to_excel(writer, sheet_name='基本資訊', index=False)

                # 詳細資訊工作表
                df_detail = pd.DataFrame(detail_info, columns=['項目', '內容'])
                df_detail.to_excel(writer, sheet_name='詳細資訊', index=False)

                # 進度追蹤工作表（如果有進度階段）
                if hasattr(case_data, 'progress_stages') and case_data.progress_stages:
                    progress_data = []
                    for stage_name, stage_info in case_data.progress_stages.items():
                        if isinstance(stage_info, dict):
                            date = stage_info.get('date', '')
                            note = stage_info.get('note', '')
                            time = stage_info.get('time', '')
                        else:
                            date = str(stage_info)
                            note = ''
                            time = ''

                        progress_data.append([stage_name, date, note, time])

                    if progress_data:
                        df_progress = pd.DataFrame(progress_data, columns=['階段', '日期', '備註', '時間'])
                        df_progress.to_excel(writer, sheet_name='進度追蹤', index=False)

            print(f"✅ Excel檔案內容更新完成: {os.path.basename(excel_file_path)}")
            return True

        except Exception as e:
            print(f"❌ 建立Excel檔案失敗: {e}")
            return False

    def _create_new_excel_file_for_case(self, case_data: CaseData, case_info_folder: str) -> bool:
        """
        為案件建立新的Excel檔案 - CaseDataManager的輔助方法

        Args:
            case_data: 案件資料
            case_info_folder: 案件資訊資料夾路徑

        Returns:
            bool: 建立是否成功
        """
        try:
            new_excel_filename = self._generate_excel_filename(case_data.case_id, case_data.client)
            new_excel_path = os.path.join(case_info_folder, new_excel_filename)

            success = self._create_simple_excel_file(case_data, new_excel_path)
            if success:
                print(f"✅ 為案件建立新Excel檔案: {new_excel_filename}")

            return success

        except Exception as e:
            print(f"❌ 建立新Excel檔案失敗: {e}")
            return False


    def _get_case_folder_path(self, case_data: CaseData) -> Optional[str]:
        """
        取得案件資料夾路徑 - CaseDataManager的輔助方法

        Args:
            case_data: 案件資料

        Returns:
            Optional[str]: 資料夾路徑或None
        """
        try:
            import os
            from config.settings import AppConfig

            # 取得案件類型資料夾名稱
            case_type_folder_name = AppConfig.CASE_TYPE_FOLDERS.get(case_data.case_type)
            if not case_type_folder_name:
                return None

            # 清理當事人姓名
            safe_client_name = self._sanitize_name_for_folder(case_data.client)

            # 建構完整路徑
            case_folder_path = os.path.join(self.data_folder, case_type_folder_name, safe_client_name)

            return case_folder_path if os.path.exists(case_folder_path) else None

        except Exception as e:
            print(f"❌ 取得案件資料夾路徑失敗: {e}")
            return None

    def _is_case_id_duplicate(self, case_id: str, case_type: str, exclude_case_id: str = None) -> bool:
        """檢查案件編號是否重複"""
        for case in self.cases:
            if (case.case_id == case_id and
                case.case_type == case_type and
                case.case_id != exclude_case_id):
                return True
        return False

    def get_case_statistics(self) -> dict:
        """取得案件統計資訊"""
        stats = {
            'total_cases': len(self.cases),
            'by_type': {},
            'by_progress': {},
            'recent_cases': 0
        }

        # 統計各類型案件數量
        for case in self.cases:
            case_type = case.case_type
            if case_type not in stats['by_type']:
                stats['by_type'][case_type] = 0
            stats['by_type'][case_type] += 1

            # 統計各進度案件數量
            progress = case.progress
            if progress not in stats['by_progress']:
                stats['by_progress'][progress] = 0
            stats['by_progress'][progress] += 1

        # 統計近期案件（7天內）
        week_ago = datetime.now() - timedelta(days=7)
        for case in self.cases:
            if case.created_date and case.created_date >= week_ago:
                stats['recent_cases'] += 1

        return stats
    def update_case_id_with_files(self, old_case_id: str, case_type: str, new_case_id: str) -> Tuple[bool, str]:
        """
        更新案件編號並處理檔案 - 別名方法
        委託給 update_case_id 處理
        """
        return self.update_case_id(old_case_id, case_type, new_case_id)

    def update_case_id(self, old_case_id: str, case_type: str, new_case_id: str) -> Tuple[bool, str]:
        """
        更新案件編號 - 完整版本
        包含Excel檔案重新命名和內容更新

        Args:
            old_case_id: 原案件編號
            case_type: 案件類型
            new_case_id: 新案件編號

        Returns:
            Tuple[bool, str]: (是否成功, 訊息)
        """
        try:
            print(f"🔄 CaseDataManager 更新案件編號: {old_case_id} → {new_case_id}")

            # 1. 找到要更新的案件
            case_to_update = None
            for case in self.cases:
                if case.case_id == old_case_id and case.case_type == case_type:
                    case_to_update = case
                    break

            if not case_to_update:
                return False, f"找不到案件編號: {old_case_id} (類型: {case_type})"

            # 2. 檢查新編號是否重複
            if self._is_case_id_duplicate(new_case_id, case_type, exclude_case_id=old_case_id):
                return False, f"案件編號 {new_case_id} 已存在"

            # 3. 處理Excel檔案重新命名（在更新案件編號之前）
            excel_rename_success = self._rename_case_excel_file(case_to_update, old_case_id, new_case_id)

            # 4. 更新案件編號
            case_to_update.case_id = new_case_id
            case_to_update.updated_date = datetime.now()

            # 5. 儲存案件資料
            success = self.save_cases()
            if success:
                # 6. 更新Excel檔案內容中的案件編號
                try:
                    self._update_excel_content_after_case_id_change(case_to_update)
                    print(f"✅ Excel內容中的案件編號已更新")
                except Exception as e:
                    print(f"⚠️ Excel內容更新失敗: {e}")

                # 7. 發布案件更新事件
                try:
                    event_manager.publish(EventType.CASE_UPDATED, {
                        'case': case_to_update,
                        'case_id': new_case_id,
                        'old_case_id': old_case_id,
                        'case_type': case_type,
                        'action': 'case_id_updated'
                    })
                except Exception as e:
                    print(f"發布事件失敗: {e}")

                case_display_name = AppConfig.format_case_display_name(case_to_update)

                if excel_rename_success:
                    print(f"✅ 已更新案件編號：{old_case_id} → {new_case_id} ({case_display_name})")
                    print(f"✅ Excel檔案已重新命名並更新內容")
                    return True, "案件編號更新成功，Excel檔案已同步更新"
                else:
                    print(f"✅ 已更新案件編號：{old_case_id} → {new_case_id} ({case_display_name})")
                    print(f"⚠️ Excel檔案重新命名失敗")
                    return True, "案件編號更新成功（Excel檔案更新部分失敗）"
            else:
                # 如果儲存失敗，恢復原始編號
                case_to_update.case_id = old_case_id
                return False, "儲存案件資料失敗"

        except Exception as e:
            print(f"❌ 更新案件編號失敗: {e}")
            import traceback
            traceback.print_exc()
            return False, f"更新失敗: {str(e)}"

    def _rename_case_excel_file(self, case_data: CaseData, old_case_id: str, new_case_id: str) -> bool:
        """
        重新命名案件Excel檔案

        Args:
            case_data: 案件資料
            old_case_id: 原案件編號
            new_case_id: 新案件編號

        Returns:
            bool: 重新命名是否成功
        """
        try:
            print(f"📁 處理Excel檔案重新命名: {old_case_id} → {new_case_id}")

            # 取得案件資料夾路徑
            case_folder_path = self._get_case_folder_path(case_data)
            if not case_folder_path:
                print(f"❌ 找不到案件資料夾")
                return False

            case_info_folder = os.path.join(case_folder_path, '案件資訊')
            if not os.path.exists(case_info_folder):
                print(f"❌ 找不到案件資訊資料夾: {case_info_folder}")
                return False

            # 尋找舊的Excel檔案
            old_excel_file = self._find_case_excel_file(case_info_folder, old_case_id, case_data.client)
            if not old_excel_file:
                print(f"ℹ️ 找不到舊的Excel檔案")
                return False

            # 產生新的Excel檔案名稱
            new_excel_filename = self._generate_excel_filename(new_case_id, case_data.client)
            new_excel_file = os.path.join(case_info_folder, new_excel_filename)

            print(f"📄 Excel檔案重新命名:")
            print(f"   原檔案: {os.path.basename(old_excel_file)}")
            print(f"   新檔案: {new_excel_filename}")

            # 如果新舊檔案名相同，不需要重新命名
            if old_excel_file == new_excel_file:
                print(f"ℹ️ 檔案名稱未變更")
                return True

            # 處理檔案名衝突
            if os.path.exists(new_excel_file):
                backup_file = f"{new_excel_file}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                os.rename(new_excel_file, backup_file)
                print(f"   已備份現有檔案: {os.path.basename(backup_file)}")

            # 重新命名檔案
            import shutil
            shutil.move(old_excel_file, new_excel_file)
            print(f"   ✅ 檔案重新命名成功")

            return True

        except Exception as e:
            print(f"❌ 重新命名Excel檔案失敗: {e}")
            return False

    def _update_excel_content_after_case_id_change(self, case_data: CaseData):
        """
        更新Excel檔案內容中的案件編號

        Args:
            case_data: 更新後的案件資料
        """
        try:
            print(f"📊 更新Excel檔案內容中的案件編號: {case_data.case_id}")

            # 取得案件資料夾
            case_folder_path = self._get_case_folder_path(case_data)
            if not case_folder_path:
                print(f"❌ 找不到案件資料夾")
                return

            case_info_folder = os.path.join(case_folder_path, '案件資訊')
            if not os.path.exists(case_info_folder):
                print(f"❌ 找不到案件資訊資料夾")
                return

            # 找到Excel檔案
            excel_file = None
            for filename in os.listdir(case_info_folder):
                if filename.endswith('.xlsx') and case_data.case_id in filename and '案件資訊' in filename:
                    excel_file = os.path.join(case_info_folder, filename)
                    break

            if not excel_file:
                print(f"❌ 找不到Excel檔案")
                return

            # 重新生成Excel內容（確保案件編號正確）
            self._recreate_excel_with_updated_case_id(case_data, excel_file)

        except Exception as e:
            print(f"❌ 更新Excel內容失敗: {e}")

    def _recreate_excel_with_updated_case_id(self, case_data: CaseData, excel_path: str):
        """
        重新建立Excel檔案確保案件編號正確

        Args:
            case_data: 案件資料
            excel_path: Excel檔案路徑
        """
        try:
            # 檢查pandas是否可用
            try:
                import pandas as pd
            except ImportError:
                print(f"⚠️ 缺少pandas套件，無法更新Excel內容")
                return

            print(f"📝 重新生成Excel內容: {os.path.basename(excel_path)}")

            # 基本資訊（確保案件編號是最新的）
            basic_info = [
                ['案件編號', case_data.case_id],  # ✅ 使用最新的案件編號
                ['案件類型', case_data.case_type],
                ['當事人', case_data.client],
                ['委任律師', getattr(case_data, 'lawyer', '') or ''],
                ['法務', getattr(case_data, 'legal_affairs', '') or ''],
                ['目前進度', case_data.progress],
                ['進度日期', case_data.progress_date or ''],
                ['建立日期', case_data.created_date.strftime('%Y-%m-%d %H:%M:%S') if case_data.created_date else ''],
                ['更新日期', case_data.updated_date.strftime('%Y-%m-%d %H:%M:%S') if case_data.updated_date else '']
            ]

            # 詳細資訊
            detail_info = [
                ['案由', getattr(case_data, 'case_reason', '') or ''],
                ['案號', getattr(case_data, 'case_number', '') or ''],
                ['對造', getattr(case_data, 'opposing_party', '') or ''],
                ['負責法院', getattr(case_data, 'court', '') or ''],
                ['負責股別', getattr(case_data, 'division', '') or '']
            ]

            # 重新寫入Excel
            with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
                # 基本資訊工作表
                df_basic = pd.DataFrame(basic_info, columns=['項目', '內容'])
                df_basic.to_excel(writer, sheet_name='基本資訊', index=False)

                # 詳細資訊工作表
                df_detail = pd.DataFrame(detail_info, columns=['項目', '內容'])
                df_detail.to_excel(writer, sheet_name='詳細資訊', index=False)

                # 進度追蹤工作表
                if hasattr(case_data, 'progress_stages') and case_data.progress_stages:
                    progress_data = []
                    for stage_name, stage_info in case_data.progress_stages.items():
                        if isinstance(stage_info, dict):
                            date = stage_info.get('date', '')
                            note = stage_info.get('note', '')
                            time = stage_info.get('time', '')
                        else:
                            date = str(stage_info)
                            note = ''
                            time = ''
                        progress_data.append([stage_name, date, note, time])

                    if progress_data:
                        df_progress = pd.DataFrame(progress_data, columns=['階段', '日期', '備註', '時間'])
                        df_progress.to_excel(writer, sheet_name='進度追蹤', index=False)

            print(f"✅ Excel內容重新生成完成，案件編號已更新為: {case_data.case_id}")

        except Exception as e:
            print(f"❌ 重新生成Excel失敗: {e}")

    def _get_case_folder_path(self, case_data: CaseData) -> Optional[str]:
        """
        取得案件資料夾路徑

        Args:
            case_data: 案件資料

        Returns:
            Optional[str]: 資料夾路徑或None
        """
        try:
            import os
            from config.settings import AppConfig

            # 取得案件類型資料夾名稱
            case_type_folder_name = AppConfig.CASE_TYPE_FOLDERS.get(case_data.case_type)
            if not case_type_folder_name:
                return None

            # 清理當事人姓名
            safe_client_name = self._sanitize_name_for_folder(case_data.client)

            # 建構完整路徑
            case_folder_path = os.path.join(self.data_folder, case_type_folder_name, safe_client_name)

            return case_folder_path if os.path.exists(case_folder_path) else None

        except Exception as e:
            print(f"❌ 取得案件資料夾路徑失敗: {e}")
            return None

    def _find_case_excel_file(self, case_info_folder: str, case_id: str, client_name: str) -> Optional[str]:
        """
        尋找案件的Excel檔案

        Args:
            case_info_folder: 案件資訊資料夾路徑
            case_id: 案件編號
            client_name: 當事人姓名

        Returns:
            Optional[str]: Excel檔案路徑或None
        """
        try:
            if not os.path.exists(case_info_folder):
                return None

            # 策略1：尋找包含案件編號的Excel檔案
            for filename in os.listdir(case_info_folder):
                if (filename.endswith('.xlsx') and
                    case_id in filename and
                    '案件資訊' in filename):
                    return os.path.join(case_info_folder, filename)

            # 策略2：尋找包含當事人姓名的Excel檔案
            clean_client = self._sanitize_name_for_filename(client_name)
            for filename in os.listdir(case_info_folder):
                if (filename.endswith('.xlsx') and
                    clean_client in filename and
                    '案件資訊' in filename):
                    return os.path.join(case_info_folder, filename)

            # 策略3：尋找任何案件資訊Excel檔案
            for filename in os.listdir(case_info_folder):
                if filename.endswith('.xlsx') and '案件資訊' in filename:
                    return os.path.join(case_info_folder, filename)

            return None

        except Exception as e:
            print(f"❌ 尋找Excel檔案失敗: {e}")
            return None

    def _generate_excel_filename(self, case_id: str, client_name: str) -> str:
        """
        產生Excel檔案名稱

        Args:
            case_id: 案件編號
            client_name: 當事人姓名

        Returns:
            str: Excel檔案名稱
        """
        try:
            clean_client = self._sanitize_name_for_filename(client_name)
            return f"{case_id}_{clean_client}_案件資訊.xlsx"
        except Exception as e:
            print(f"❌ 產生Excel檔案名稱失敗: {e}")
            return f"{case_id}_案件資訊.xlsx"

    def _sanitize_name_for_filename(self, name: str) -> str:
        """
        清理名稱用於檔案命名

        Args:
            name: 原始名稱

        Returns:
            str: 清理後的名稱
        """
        try:
            # 移除檔案名不允許的字元
            invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
            clean_name = name

            for char in invalid_chars:
                clean_name = clean_name.replace(char, '_')

            # 移除多餘的空格和點
            clean_name = clean_name.strip(' .')

            # 限制長度
            if len(clean_name) > 20:
                clean_name = clean_name[:20]

            # 確保不為空
            if not clean_name:
                clean_name = "客戶"

            return clean_name

        except Exception as e:
            print(f"❌ 清理名稱失敗: {e}")
            return "客戶"

    def _sanitize_name_for_folder(self, name: str) -> str:
        """
        清理名稱用於資料夾命名

        Args:
            name: 原始名稱

        Returns:
            str: 清理後的名稱
        """
        try:
            # 移除資料夾名不允許的字元
            invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
            clean_name = name

            for char in invalid_chars:
                clean_name = clean_name.replace(char, '_')

            clean_name = clean_name.strip(' .')

            # 限制長度
            if len(clean_name) > 50:
                clean_name = clean_name[:50]

            if not clean_name:
                clean_name = "未知客戶"

            return clean_name

        except Exception as e:
            print(f"❌ 清理資料夾名稱失敗: {e}")
            return "未知客戶"

    def _is_case_id_duplicate(self, case_id: str, case_type: str, exclude_case_id: str = None) -> bool:
        """
        檢查案件編號是否重複

        Args:
            case_id: 要檢查的案件編號
            case_type: 案件類型
            exclude_case_id: 要排除的案件編號（用於更新時）

        Returns:
            bool: 是否重複
        """
        try:
            for case in self.cases:
                if (case.case_id == case_id and
                    case.case_type == case_type and
                    case.case_id != exclude_case_id):
                    return True
            return False
        except Exception as e:
            print(f"❌ 檢查案件編號重複失敗: {e}")
            return False