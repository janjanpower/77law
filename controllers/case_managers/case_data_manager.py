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
        """刪除案件"""
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
                print(f"找不到要刪除的案件: {case_id}")
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

    def generate_case_id(self, case_type: str) -> str:
        """
        生成案件編號 - 修正版本：民國年+流水號格式

        格式：民國年份 + 3位流水號
        例如：113001 (民國113年第1號案件)

        Args:
            case_type: 案件類型

        Returns:
            str: 生成的案件編號
        """
        try:
            # 取得當前民國年份
            current_year = datetime.now().year
            roc_year = current_year - 1911  # 轉換為民國年

            # 取得同年同類型的現有案件
            same_year_type_cases = [
                case for case in self.cases
                if case.case_type == case_type and
                case.case_id and
                case.case_id.startswith(str(roc_year))
            ]

            # 找出最大的流水號
            max_num = 0
            for case in same_year_type_cases:
                if case.case_id and len(case.case_id) >= 6:  # 民國年(3位) + 流水號(3位)
                    try:
                        # 提取流水號部分
                        num_part = case.case_id[3:]  # 跳過民國年份的3位數
                        if num_part.isdigit():
                            num = int(num_part)
                            max_num = max(max_num, num)
                    except (ValueError, IndexError):
                        continue

            # 生成新編號
            new_num = max_num + 1
            new_case_id = f"{roc_year:03d}{new_num:03d}"

            print(f"為 {case_type} 類型生成新案件編號: {new_case_id} (民國{roc_year}年第{new_num}號)")
            return new_case_id

        except Exception as e:
            print(f"生成案件編號失敗: {e}")
            # 使用時間戳作為備用方案
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            return f"ERR{timestamp}"

    def update_case_id(self, old_case_id: str, case_type: str, new_case_id: str) -> Tuple[bool, str]:
        """更新案件編號"""
        try:
            # 找到要更新的案件
            case_to_update = None
            for case in self.cases:
                if case.case_id == old_case_id and case.case_type == case_type:
                    case_to_update = case
                    break

            if case_to_update:
                # 更新案件編號
                case_to_update.case_id = new_case_id
                case_to_update.updated_date = datetime.now()

                success = self.save_cases()
                if success:
                    # 發布案件更新事件
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
                    print(f"已更新案件編號：{old_case_id} → {new_case_id} ({case_display_name})")
                    return True, "案件編號更新成功"
                else:
                    return False, "儲存案件資料失敗"

            return False, f"找不到案件編號: {old_case_id} (類型: {case_type})"

        except Exception as e:
            print(f"更新案件編號失敗: {e}")
            import traceback
            traceback.print_exc()
            return False, f"更新失敗: {str(e)}"

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