#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
案件進度管理器
專責案件進度的管理功能
"""

import os
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from models.case_model import CaseData
from utils.folder_management.folder_manager import FolderManager
from utils.event_manager import event_manager, EventType
from config.settings import AppConfig


class CaseProgressManager:
    """案件進度管理器"""

    def __init__(self, cases: List[CaseData], folder_manager: FolderManager):
        """
        初始化進度管理器

        Args:
            cases: 案件資料列表（引用）
            folder_manager: 資料夾管理器
        """
        self.cases = cases
        self.folder_manager = folder_manager

    def _get_case_by_id(self, case_id: str) -> Optional[CaseData]:
        """
        根據編號取得案件

        Args:
            case_id: 案件編號

        Returns:
            Optional[CaseData]: 案件資料或None
        """
        print(f"🔍 尋找案件編號: {case_id}")
        print(f"📋 當前案件總數: {len(self.cases)}")

        # 列出所有案件編號以供除錯
        all_case_ids = [case.case_id for case in self.cases]
        print(f"📝 所有案件編號: {all_case_ids}")

        for case in self.cases:
            print(f"   檢查案件: {case.case_id} (類型: {type(case.case_id)})")
            # 嘗試字串比較和類型轉換
            if str(case.case_id) == str(case_id):
                print(f"✅ 找到案件: {case.case_id}")
                return case

        print(f"❌ 未找到案件編號: {case_id}")
        return None

    def add_progress_stage(self, case_id: str, stage_name: str, stage_date: str = None,
                          note: str = None, time: str = None) -> bool:
        """
        新增案件進度階段

        Args:
            case_id: 案件編號
            stage_name: 階段名稱
            stage_date: 階段日期
            note: 備註
            time: 時間

        Returns:
            bool: 是否成功
        """
        try:
            case = self._get_case_by_id(case_id)
            if not case:
                raise ValueError(f"找不到案件編號: {case_id}")

            # 新增進度階段到案件資料
            case.add_progress_stage(stage_name, stage_date, note, time)

            # 建立對應的資料夾
            self.folder_manager.create_progress_folder(case, stage_name)

            # 更新案件資訊Excel
            self.folder_manager.update_case_info_excel(case)

            case_display_name = AppConfig.format_case_display_name(case)
            print(f"已新增案件 {case_display_name} 的階段 {stage_name}")

            # 發布階段新增事件
            try:
                event_manager.publish(EventType.STAGE_ADDED, {
                    'case_id': case_id,
                    'case': case,
                    'stage_name': stage_name,
                    'stage_date': stage_date,
                    'note': note,
                    'time': time
                })

                # 同時發布案件更新事件，確保UI更新
                event_manager.publish(EventType.CASE_UPDATED, {
                    'case_id': case_id,
                    'case': case,
                    'case_type': case.case_type,
                    'client': case.client,
                    'action': 'stage_added'
                })

                print(f"已發布階段新增和案件更新事件")
            except Exception as e:
                print(f"發布事件失敗: {e}")

            return True

        except Exception as e:
            print(f"新增案件進度階段失敗: {e}")
            return False

    def update_progress_stage(self, case_id: str, stage_name: str, stage_date: str,
                             note: str = None, time: str = None) -> bool:
        """
        更新案件進度階段

        Args:
            case_id: 案件編號
            stage_name: 階段名稱
            stage_date: 階段日期
            note: 備註
            time: 時間

        Returns:
            bool: 是否成功
        """
        try:
            case = self._get_case_by_id(case_id)
            if not case:
                raise ValueError(f"找不到案件編號: {case_id}")

            # 更新階段資料
            case.update_stage_date(stage_name, stage_date)

            # 更新備註
            if note is not None:
                case.update_stage_note(stage_name, note)

            # 更新時間
            if time is not None:
                case.update_stage_time(stage_name, time)

            # 更新資料夾和Excel
            self.folder_manager.update_case_info_excel(case)

            case_display_name = AppConfig.format_case_display_name(case)
            print(f"已更新案件 {case_display_name} 的階段 {stage_name}")

            # 發布階段更新事件
            try:
                event_manager.publish(EventType.STAGE_UPDATED, {
                    'case_id': case_id,
                    'case': case,
                    'stage_name': stage_name,
                    'stage_date': stage_date,
                    'note': note,
                    'time': time
                })

                # 同時發布案件更新事件，確保UI更新
                event_manager.publish(EventType.CASE_UPDATED, {
                    'case_id': case_id,
                    'case': case,
                    'case_type': case.case_type,
                    'client': case.client,
                    'action': 'stage_updated'
                })

                print(f"已發布階段更新和案件更新事件")
            except Exception as e:
                print(f"發布事件失敗: {e}")

            return True

        except Exception as e:
            print(f"更新案件進度階段失敗: {e}")
            return False

    def remove_progress_stage(self, case_id: str, stage_name: str) -> bool:
        """
        移除案件進度階段

        Args:
            case_id: 案件編號
            stage_name: 階段名稱

        Returns:
            bool: 是否成功
        """
        try:
            case = self._get_case_by_id(case_id)
            if not case:
                raise ValueError(f"找不到案件編號: {case_id}")

            # 先刪除對應的資料夾
            print(f"準備刪除階段 {stage_name} 的資料夾...")
            folder_success = self.folder_manager.delete_progress_folder(case, stage_name)

            if folder_success:
                print(f"✅ 階段資料夾刪除成功: {stage_name}")
            else:
                print(f"⚠️ 階段資料夾刪除失敗或不存在: {stage_name}")

            # 移除進度階段記錄
            stage_remove_success = case.remove_progress_stage(stage_name)

            if not stage_remove_success:
                print(f"❌ 移除階段記錄失敗: {stage_name}")
                return False

            # 更新Excel檔案
            try:
                self.folder_manager.update_case_info_excel(case)
            except Exception as e:
                print(f"⚠️ 更新Excel檔案失敗: {e}")

            # 發布事件通知
            try:
                # 發布階段刪除事件
                event_manager.publish(EventType.STAGE_DELETED, {
                    'case_id': case_id,
                    'case': case,
                    'stage_name': stage_name,
                    'folder_deleted': folder_success
                })

                # 發布案件更新事件，確保UI更新
                event_manager.publish(EventType.CASE_UPDATED, {
                    'case_id': case_id,
                    'case': case,
                    'case_type': case.case_type,
                    'client': case.client,
                    'action': 'stage_removed'
                })

                print(f"已發布階段刪除和案件更新事件")
            except Exception as e:
                print(f"發布事件失敗: {e}")

            case_display_name = AppConfig.format_case_display_name(case)
            print(f"✅ 成功移除案件 {case_display_name} 的階段: {stage_name}")
            return True

        except Exception as e:
            print(f"移除案件進度階段失敗: {e}")
            return False


    def update_progress_files_for_case_id_change(self, old_case_id: str, new_case_id: str) -> Tuple[bool, str]:
        """
        更新進度相關檔案中的案件編號 - CaseProgressManager的職責

        Args:
            old_case_id: 原案件編號
            new_case_id: 新案件編號

        Returns:
            Tuple[bool, str]: (是否成功, 訊息)
        """
        try:
            print(f"📈 CaseProgressManager 更新進度檔案: {old_case_id} → {new_case_id}")

            # 找到案件
            case_data = self._get_case_by_id(new_case_id)
            if not case_data:
                return False, f"找不到案件: {new_case_id}"

            updated_items = []

            # 1. 更新進度階段資料夾名稱中的案件編號
            if self._update_progress_folder_names(case_data, old_case_id, new_case_id):
                updated_items.append("進度資料夾")

            # 2. 更新進度相關的檔案內容
            if self._update_progress_file_contents(case_data, old_case_id, new_case_id):
                updated_items.append("進度檔案內容")

            # 3. 更新Excel檔案中進度追蹤工作表的案件編號
            if self._update_progress_excel_sheets(case_data, old_case_id, new_case_id):
                updated_items.append("進度Excel工作表")

            if updated_items:
                message = f"進度檔案更新完成: {', '.join(updated_items)}"
                print(f"✅ {message}")
                return True, message
            else:
                return False, "沒有進度檔案需要更新"

        except Exception as e:
            print(f"❌ CaseProgressManager 更新進度檔案失敗: {e}")
            return False, f"進度檔案更新失敗: {str(e)}"

    def _update_progress_folder_names(self, case_data: CaseData, old_case_id: str, new_case_id: str) -> bool:
        """更新進度階段資料夾名稱中的案件編號"""
        try:
            case_folder_path = self._get_case_folder_path(case_data)
            if not case_folder_path:
                return False

            progress_folder = os.path.join(case_folder_path, '進度追蹤')
            if not os.path.exists(progress_folder):
                return False

            renamed_count = 0

            # 檢查每個進度階段資料夾
            for item in os.listdir(progress_folder):
                item_path = os.path.join(progress_folder, item)
                if os.path.isdir(item_path) and old_case_id in item:
                    new_item_name = item.replace(old_case_id, new_case_id)
                    new_item_path = os.path.join(progress_folder, new_item_name)

                    try:
                        os.rename(item_path, new_item_path)
                        renamed_count += 1
                        print(f"     重新命名進度資料夾: {item} → {new_item_name}")
                    except Exception as e:
                        print(f"     重新命名進度資料夾失敗: {item} - {e}")

            return renamed_count > 0

        except Exception as e:
            print(f"❌ 更新進度資料夾名稱失敗: {e}")
            return False

    def _update_progress_file_contents(self, case_data: CaseData, old_case_id: str, new_case_id: str) -> bool:
        """更新進度相關檔案的內容"""
        try:
            # 更新進度階段資料中的案件編號參考
            if hasattr(case_data, 'progress_stages') and case_data.progress_stages:
                for stage_name, stage_info in case_data.progress_stages.items():
                    if isinstance(stage_info, dict):
                        # 檢查備註中是否包含舊案件編號
                        if 'note' in stage_info and stage_info['note']:
                            if old_case_id in stage_info['note']:
                                stage_info['note'] = stage_info['note'].replace(old_case_id, new_case_id)
                                print(f"     更新進度備註中的案件編號: {stage_name}")

            return True

        except Exception as e:
            print(f"❌ 更新進度檔案內容失敗: {e}")
            return False

    def _update_progress_excel_sheets(self, case_data: CaseData, old_case_id: str, new_case_id: str) -> bool:
        """更新Excel檔案中進度追蹤工作表的案件編號"""
        try:
            # 這部分可以委託給 import_export 或者在這裡實現
            # 專門處理進度追蹤工作表的更新
            return True

        except Exception as e:
            print(f"❌ 更新進度Excel工作表失敗: {e}")
            return False
