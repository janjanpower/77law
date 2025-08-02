#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
案件進度管理器
專責案件進度的管理功能
"""

import os
from datetime import datetime
from typing import List, Optional, Dict, Any
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

    def update_current_progress(self, case_id: str, new_progress: str, progress_date: str = None) -> bool:
        """
        更新案件當前進度

        Args:
            case_id: 案件編號
            new_progress: 新的進度
            progress_date: 進度日期

        Returns:
            bool: 是否成功
        """
        try:
            case = self._get_case_by_id(case_id)
            if not case:
                raise ValueError(f"找不到案件編號: {case_id}")

            # 更新當前進度
            case.update_progress(new_progress, progress_date)

            # 更新Excel檔案
            self.folder_manager.update_case_info_excel(case)

            # 發布進度更新事件
            try:
                event_manager.publish(EventType.CASE_UPDATED, {
                    'case_id': case_id,
                    'case': case,
                    'case_type': case.case_type,
                    'client': case.client,
                    'action': 'progress_updated',
                    'new_progress': new_progress,
                    'progress_date': progress_date
                })
            except Exception as e:
                print(f"發布事件失敗: {e}")

            case_display_name = AppConfig.format_case_display_name(case)
            print(f"已更新案件 {case_display_name} 的當前進度為: {new_progress}")
            return True

        except Exception as e:
            print(f"更新案件當前進度失敗: {e}")
            return False

    def get_stage_folder_path(self, case_id: str, stage_name: str) -> Optional[str]:
        """
        取得案件特定階段的資料夾路徑

        Args:
            case_id: 案件編號
            stage_name: 階段名稱

        Returns:
            Optional[str]: 資料夾路徑或None
        """
        case = self._get_case_by_id(case_id)
        if case:
            case_folder = self.folder_manager.get_case_folder_path(case)
            if case_folder:
                return os.path.join(case_folder, '進度追蹤', stage_name)
        return None

    def get_progress_statistics(self) -> Dict[str, Any]:
        """
        取得進度統計資訊

        Returns:
            Dict[str, Any]: 統計資訊
        """
        stats = {
            'total_cases': len(self.cases),
            'progress_distribution': {},
            'case_type_progress': {},
            'stage_frequency': {},
            'cases_with_stages': 0,
            'average_stages_per_case': 0.0
        }

        total_stages = 0

        for case in self.cases:
            # 進度分布統計
            progress = getattr(case, 'progress', '未知')
            stats['progress_distribution'][progress] = stats['progress_distribution'].get(progress, 0) + 1

            # 案件類型進度統計
            case_type = getattr(case, 'case_type', '未知')
            if case_type not in stats['case_type_progress']:
                stats['case_type_progress'][case_type] = {}
            stats['case_type_progress'][case_type][progress] = stats['case_type_progress'][case_type].get(progress, 0) + 1

            # 階段頻率統計
            if hasattr(case, 'progress_stages') and case.progress_stages:
                stats['cases_with_stages'] += 1
                stages_count = len(case.progress_stages)
                total_stages += stages_count

                for stage_name in case.progress_stages.keys():
                    stats['stage_frequency'][stage_name] = stats['stage_frequency'].get(stage_name, 0) + 1
