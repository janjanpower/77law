#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
進度資料存取層 (Progress Repository)
專責處理案件進度相關的資料存取邏輯
"""

import os
import json
import threading
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime


class ProgressStage:
    """進度階段資料類別"""

    def __init__(self, stage_id: str, stage_name: str, case_id: str):
        self.stage_id = stage_id
        self.stage_name = stage_name
        self.case_id = case_id
        self.status = "待處理"  # 待處理、進行中、已完成、延期
        self.start_date = None
        self.due_date = None
        self.completion_date = None
        self.description = ""
        self.notes = ""
        self.priority = "一般"  # 低、一般、高、緊急
        self.assigned_to = ""
        self.progress_percentage = 0
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            'stage_id': self.stage_id,
            'stage_name': self.stage_name,
            'case_id': self.case_id,
            'status': self.status,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'completion_date': self.completion_date.isoformat() if self.completion_date else None,
            'description': self.description,
            'notes': self.notes,
            'priority': self.priority,
            'assigned_to': self.assigned_to,
            'progress_percentage': self.progress_percentage,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProgressStage':
        """從字典建立物件"""
        stage = cls(data.get('stage_id', ''), data.get('stage_name', ''), data.get('case_id', ''))
        stage.status = data.get('status', '待處理')
        stage.start_date = datetime.fromisoformat(data['start_date']) if data.get('start_date') else None
        stage.due_date = datetime.fromisoformat(data['due_date']) if data.get('due_date') else None
        stage.completion_date = datetime.fromisoformat(data['completion_date']) if data.get('completion_date') else None
        stage.description = data.get('description', '')
        stage.notes = data.get('notes', '')
        stage.priority = data.get('priority', '一般')
        stage.assigned_to = data.get('assigned_to', '')
        stage.progress_percentage = data.get('progress_percentage', 0)
        stage.created_at = datetime.fromisoformat(data['created_at']) if data.get('created_at') else datetime.now()
        stage.updated_at = datetime.fromisoformat(data['updated_at']) if data.get('updated_at') else datetime.now()
        return stage


class ProgressRepository:
    """進度資料存取器"""

    def __init__(self, data_folder: str, progress_file: str = None):
        """
        初始化進度資料存取器

        Args:
            data_folder: 資料資料夾路徑
            progress_file: 進度資料檔案路徑
        """
        self.data_folder = data_folder
        self.progress_file = progress_file or os.path.join(data_folder, "progress_data.json")
        self.progress_stages = []
        self._lock = threading.Lock()
        self._load_progress_data()

    # ==================== 資料載入與儲存 ====================

    def _load_progress_data(self) -> bool:
        """
        載入進度資料

        Returns:
            bool: 載入是否成功
        """
        try:
            if os.path.exists(self.progress_file):
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.progress_stages = [ProgressStage.from_dict(item) for item in data]

                print(f"✅ 成功載入 {len(self.progress_stages)} 筆進度資料")
                return True
            else:
                print("📂 進度資料檔案不存在，將建立新檔案")
                self.progress_stages = []
                return True

        except Exception as e:
            print(f"❌ 載入進度資料失敗: {e}")
            self.progress_stages = []
            return False

    def _save_progress_data(self) -> bool:
        """
        儲存進度資料

        Returns:
            bool: 儲存是否成功
        """
        try:
            os.makedirs(os.path.dirname(self.progress_file), exist_ok=True)

            data = [stage.to_dict() for stage in self.progress_stages]

            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)

            print(f"✅ 成功儲存 {len(self.progress_stages)} 筆進度資料")
            return True

        except Exception as e:
            print(f"❌ 儲存進度資料失敗: {e}")
            return False

    def reload_data(self) -> bool:
        """
        重新載入資料

        Returns:
            bool: 重新載入是否成功
        """
        with self._lock:
            return self._load_progress_data()

    # ==================== CRUD 操作 ====================

    def create_progress_stage(self, stage: ProgressStage) -> bool:
        """
        新增進度階段

        Args:
            stage: 進度階段資料

        Returns:
            bool: 新增是否成功
        """
        try:
            with self._lock:
                # 檢查是否已存在相同ID的階段
                if self.get_progress_stage(stage.stage_id):
                    print(f"❌ 進度階段ID已存在: {stage.stage_id}")
                    return False

                # 設定建立時間
                stage.created_at = datetime.now()
                stage.updated_at = datetime.now()

                # 新增到記憶體
                self.progress_stages.append(stage)

                # 儲存到檔案
                return self._save_progress_data()

        except Exception as e:
            print(f"❌ 新增進度階段失敗: {e}")
            return False

    def update_progress_stage(self, stage: ProgressStage) -> bool:
        """
        更新進度階段

        Args:
            stage: 更新後的進度階段資料

        Returns:
            bool: 更新是否成功
        """
        try:
            with self._lock:
                # 找到要更新的階段索引
                stage_index = None
                for i, existing_stage in enumerate(self.progress_stages):
                    if existing_stage.stage_id == stage.stage_id:
                        stage_index = i
                        break

                if stage_index is None:
                    print(f"❌ 找不到要更新的進度階段: {stage.stage_id}")
                    return False

                # 設定更新時間
                stage.updated_at = datetime.now()

                # 更新階段資料
                self.progress_stages[stage_index] = stage

                # 儲存到檔案
                return self._save_progress_data()

        except Exception as e:
            print(f"❌ 更新進度階段失敗: {e}")
            return False

    def delete_progress_stage(self, stage_id: str) -> bool:
        """
        刪除進度階段

        Args:
            stage_id: 進度階段ID

        Returns:
            bool: 刪除是否成功
        """
        try:
            with self._lock:
                # 找到要刪除的階段
                stage_to_delete = None
                for i, stage in enumerate(self.progress_stages):
                    if stage.stage_id == stage_id:
                        stage_to_delete = i
                        break

                if stage_to_delete is None:
                    print(f"❌ 找不到要刪除的進度階段: {stage_id}")
                    return False

                # 從記憶體中移除
                deleted_stage = self.progress_stages.pop(stage_to_delete)
                print(f"🗑️ 準備刪除進度階段: {deleted_stage.stage_name} ({stage_id})")

                # 儲存到檔案
                return self._save_progress_data()

        except Exception as e:
            print(f"❌ 刪除進度階段失敗: {e}")
            return False

    def delete_case_progress(self, case_id: str) -> bool:
        """
        刪除案件的所有進度階段

        Args:
            case_id: 案件ID

        Returns:
            bool: 刪除是否成功
        """
        try:
            with self._lock:
                # 找到該案件的所有階段
                stages_to_delete = [stage for stage in self.progress_stages if stage.case_id == case_id]

                if not stages_to_delete:
                    print(f"📝 案件 {case_id} 沒有進度階段需要刪除")
                    return True

                # 從記憶體中移除
                self.progress_stages = [stage for stage in self.progress_stages if stage.case_id != case_id]

                print(f"🗑️ 刪除案件 {case_id} 的 {len(stages_to_delete)} 個進度階段")

                # 儲存到檔案
                return self._save_progress_data()

        except Exception as e:
            print(f"❌ 刪除案件進度失敗: {e}")
            return False

    # ==================== 查詢操作 ====================

    def get_progress_stage(self, stage_id: str) -> Optional[ProgressStage]:
        """
        取得特定進度階段

        Args:
            stage_id: 進度階段ID

        Returns:
            Optional[ProgressStage]: 進度階段資料或None
        """
        with self._lock:
            for stage in self.progress_stages:
                if stage.stage_id == stage_id:
                    return stage
            return None

    def get_case_progress_stages(self, case_id: str) -> List[ProgressStage]:
        """
        取得案件的所有進度階段

        Args:
            case_id: 案件ID

        Returns:
            List[ProgressStage]: 進度階段列表
        """
        with self._lock:
            stages = [stage for stage in self.progress_stages if stage.case_id == case_id]
            # 按建立時間排序
            stages.sort(key=lambda x: x.created_at)
            return stages

    def get_stages_by_status(self, status: str) -> List[ProgressStage]:
        """
        取得特定狀態的所有進度階段

        Args:
            status: 階段狀態

        Returns:
            List[ProgressStage]: 進度階段列表
        """
        with self._lock:
            return [stage for stage in self.progress_stages if stage.status == status]

    def get_stages_by_priority(self, priority: str) -> List[ProgressStage]:
        """
        取得特定優先級的所有進度階段

        Args:
            priority: 優先級

        Returns:
            List[ProgressStage]: 進度階段列表
        """
        with self._lock:
            return [stage for stage in self.progress_stages if stage.priority == priority]

    def get_overdue_stages(self) -> List[ProgressStage]:
        """
        取得所有逾期的進度階段

        Returns:
            List[ProgressStage]: 逾期的進度階段列表
        """
        current_time = datetime.now()
        with self._lock:
            overdue_stages = []
            for stage in self.progress_stages:
                if (stage.due_date and
                    stage.due_date < current_time and
                    stage.status not in ['已完成']):
                    overdue_stages.append(stage)
            return overdue_stages

    def get_upcoming_stages(self, days_ahead: int = 7) -> List[ProgressStage]:
        """
        取得即將到期的進度階段

        Args:
            days_ahead: 向前查看的天數

        Returns:
            List[ProgressStage]: 即將到期的進度階段列表
        """
        from datetime import timedelta

        current_time = datetime.now()
        future_time = current_time + timedelta(days=days_ahead)

        with self._lock:
            upcoming_stages = []
            for stage in self.progress_stages:
                if (stage.due_date and
                    current_time <= stage.due_date <= future_time and
                    stage.status not in ['已完成']):
                    upcoming_stages.append(stage)
            return upcoming_stages

    def search_progress_stages(self, keyword: str) -> List[ProgressStage]:
        """
        搜尋進度階段

        Args:
            keyword: 搜尋關鍵字

        Returns:
            List[ProgressStage]: 符合條件的進度階段列表
        """
        if not keyword:
            return self.get_all_progress_stages()

        keyword_lower = keyword.lower()
        with self._lock:
            results = []
            for stage in self.progress_stages:
                if (keyword_lower in stage.stage_name.lower() or
                    keyword_lower in stage.description.lower() or
                    keyword_lower in stage.notes.lower() or
                    keyword_lower in stage.assigned_to.lower()):
                    results.append(stage)
            return results

    def get_all_progress_stages(self) -> List[ProgressStage]:
        """
        取得所有進度階段

        Returns:
            List[ProgressStage]: 所有進度階段
        """
        with self._lock:
            return self.progress_stages.copy()

    # ==================== 統計查詢 ====================

    def get_case_progress_summary(self, case_id: str) -> Dict[str, Any]:
        """
        取得案件進度摘要

        Args:
            case_id: 案件ID

        Returns:
            Dict[str, Any]: 進度摘要
        """
        stages = self.get_case_progress_stages(case_id)

        if not stages:
            return {
                'total_stages': 0,
                'completed_stages': 0,
                'in_progress_stages': 0,
                'pending_stages': 0,
                'overdue_stages': 0,
                'progress_percentage': 0.0,
                'next_due_date': None,
                'status_distribution': {}
            }

        # 統計各狀態數量
        status_counts = {}
        overdue_count = 0
        current_time = datetime.now()
        next_due_date = None

        for stage in stages:
            status = stage.status
            status_counts[status] = status_counts.get(status, 0) + 1

            # 檢查逾期
            if (stage.due_date and
                stage.due_date < current_time and
                stage.status not in ['已完成']):
                overdue_count += 1

            # 找下一個到期日
            if (stage.due_date and
                stage.status not in ['已完成'] and
                (next_due_date is None or stage.due_date < next_due_date)):
                next_due_date = stage.due_date

        completed_stages = status_counts.get('已完成', 0)
        total_stages = len(stages)
        progress_percentage = (completed_stages / total_stages * 100) if total_stages > 0 else 0

        return {
            'total_stages': total_stages,
            'completed_stages': completed_stages,
            'in_progress_stages': status_counts.get('進行中', 0),
            'pending_stages': status_counts.get('待處理', 0),
            'overdue_stages': overdue_count,
            'progress_percentage': round(progress_percentage, 2),
            'next_due_date': next_due_date.isoformat() if next_due_date else None,
            'status_distribution': status_counts
        }

    def get_progress_statistics(self) -> Dict[str, Any]:
        """
        取得整體進度統計

        Returns:
            Dict[str, Any]: 進度統計
        """
        with self._lock:
            if not self.progress_stages:
                return {
                    'total_stages': 0,
                    'status_distribution': {},
                    'priority_distribution': {},
                    'overdue_count': 0,
                    'completion_rate': 0.0
                }

            status_counts = {}
            priority_counts = {}
            overdue_count = 0
            current_time = datetime.now()

            for stage in self.progress_stages:
                # 狀態統計
                status = stage.status
                status_counts[status] = status_counts.get(status, 0) + 1

                # 優先級統計
                priority = stage.priority
                priority_counts[priority] = priority_counts.get(priority, 0) + 1

                # 逾期統計
                if (stage.due_date and
                    stage.due_date < current_time and
                    stage.status not in ['已完成']):
                    overdue_count += 1

            completed_count = status_counts.get('已完成', 0)
            total_stages = len(self.progress_stages)
            completion_rate = (completed_count / total_stages * 100) if total_stages > 0 else 0

            return {
                'total_stages': total_stages,
                'status_distribution': status_counts,
                'priority_distribution': priority_counts,
                'overdue_count': overdue_count,
                'completion_rate': round(completion_rate, 2)
            }

    def get_workload_by_assignee(self) -> Dict[str, Dict[str, Any]]:
        """
        取得各負責人的工作負荷統計

        Returns:
            Dict[str, Dict[str, Any]]: 負責人工作負荷統計
        """
        with self._lock:
            workload = {}

            for stage in self.progress_stages:
                assignee = stage.assigned_to or "未指派"

                if assignee not in workload:
                    workload[assignee] = {
                        'total_stages': 0,
                        'pending_stages': 0,
                        'in_progress_stages': 0,
                        'completed_stages': 0,
                        'overdue_stages': 0
                    }

                workload[assignee]['total_stages'] += 1

                if stage.status == '待處理':
                    workload[assignee]['pending_stages'] += 1
                elif stage.status == '進行中':
                    workload[assignee]['in_progress_stages'] += 1
                elif stage.status == '已完成':
                    workload[assignee]['completed_stages'] += 1

                # 檢查逾期
                current_time = datetime.now()
                if (stage.due_date and
                    stage.due_date < current_time and
                    stage.status not in ['已完成']):
                    workload[assignee]['overdue_stages'] += 1

            return workload

    # ==================== 批次操作 ====================

    def batch_update_stages(self, updates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        批次更新進度階段

        Args:
            updates: 更新資料列表，格式: [{'stage_id': '', 'updates': {}}]

        Returns:
            Dict[str, Any]: 批次更新結果
        """
        result = {
            'success_count': 0,
            'failed_count': 0,
            'errors': []
        }

        try:
            with self._lock:
                for update_data in updates:
                    stage_id = update_data.get('stage_id')
                    updates_dict = update_data.get('updates', {})

                    # 找到進度階段
                    stage_found = False
                    for stage in self.progress_stages:
                        if stage.stage_id == stage_id:
                            # 更新欄位
                            for field, value in updates_dict.items():
                                if hasattr(stage, field):
                                    # 處理日期欄位
                                    if field in ['start_date', 'due_date', 'completion_date'] and isinstance(value, str):
                                        try:
                                            setattr(stage, field, datetime.fromisoformat(value))
                                        except:
                                            setattr(stage, field, value)
                                    else:
                                        setattr(stage, field, value)

                            # 設定更新時間
                            stage.updated_at = datetime.now()
                            stage_found = True
                            result['success_count'] += 1
                            break

                    if not stage_found:
                        result['failed_count'] += 1
                        result['errors'].append(f"找不到進度階段: {stage_id}")

                # 儲存變更
                if result['success_count'] > 0:
                    self._save_progress_data()

        except Exception as e:
            result['errors'].append(f"批次更新失敗: {str(e)}")

        return result

    def batch_complete_stages(self, stage_ids: List[str]) -> Dict[str, Any]:
        """
        批次完成進度階段

        Args:
            stage_ids: 階段ID列表

        Returns:
            Dict[str, Any]: 批次完成結果
        """
        updates = []
        for stage_id in stage_ids:
            updates.append({
                'stage_id': stage_id,
                'updates': {
                    'status': '已完成',
                    'completion_date': datetime.now(),
                    'progress_percentage': 100
                }
            })

        return self.batch_update_stages(updates)

    def batch_assign_stages(self, stage_ids: List[str], assignee: str) -> Dict[str, Any]:
        """
        批次指派進度階段

        Args:
            stage_ids: 階段ID列表
            assignee: 負責人

        Returns:
            Dict[str, Any]: 批次指派結果
        """
        updates = []
        for stage_id in stage_ids:
            updates.append({
                'stage_id': stage_id,
                'updates': {
                    'assigned_to': assignee
                }
            })

        return self.batch_update_stages(updates)

    # ==================== 範本操作 ====================

    def create_stages_from_template(self, case_id: str, template_stages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        從範本建立進度階段

        Args:
            case_id: 案件ID
            template_stages: 範本階段列表

        Returns:
            Dict[str, Any]: 建立結果
        """
        result = {
            'success_count': 0,
            'failed_count': 0,
            'created_stages': [],
            'errors': []
        }

        try:
            import uuid

            for i, template_stage in enumerate(template_stages):
                try:
                    # 生成唯一ID
                    stage_id = f"{case_id}_stage_{i+1}_{str(uuid.uuid4())[:8]}"

                    # 建立進度階段
                    stage = ProgressStage(
                        stage_id=stage_id,
                        stage_name=template_stage.get('stage_name', f"階段 {i+1}"),
                        case_id=case_id
                    )

                    # 設定範本資料
                    stage.description = template_stage.get('description', '')
                    stage.priority = template_stage.get('priority', '一般')
                    stage.assigned_to = template_stage.get('assigned_to', '')

                    # 處理日期
                    if template_stage.get('due_days'):
                        from datetime import timedelta
                        stage.due_date = datetime.now() + timedelta(days=template_stage['due_days'])

                    # 新增階段
                    if self.create_progress_stage(stage):
                        result['success_count'] += 1
                        result['created_stages'].append(stage_id)
                    else:
                        result['failed_count'] += 1
                        result['errors'].append(f"建立階段失敗: {template_stage.get('stage_name')}")

                except Exception as e:
                    result['failed_count'] += 1
                    result['errors'].append(f"處理範本階段失敗: {str(e)}")

        except Exception as e:
            result['errors'].append(f"從範本建立階段失敗: {str(e)}")

        return result

    def export_progress_template(self, case_id: str, template_path: str) -> bool:
        """
        匯出進度範本

        Args:
            case_id: 案件ID
            template_path: 範本檔案路徑

        Returns:
            bool: 匯出是否成功
        """
        try:
            stages = self.get_case_progress_stages(case_id)

            template_data = {
                'template_name': f"案件_{case_id}_進度範本",
                'created_at': datetime.now().isoformat(),
                'total_stages': len(stages),
                'stages': []
            }

            for stage in stages:
                template_stage = {
                    'stage_name': stage.stage_name,
                    'description': stage.description,
                    'priority': stage.priority,
                    'assigned_to': stage.assigned_to,
                    'due_days': None  # 可以根據需要計算相對天數
                }
                template_data['stages'].append(template_stage)

            os.makedirs(os.path.dirname(template_path), exist_ok=True)
            with open(template_path, 'w', encoding='utf-8') as f:
                json.dump(template_data, f, ensure_ascii=False, indent=2, default=str)

            print(f"✅ 進度範本匯出成功: {template_path}")
            return True

        except Exception as e:
            print(f"❌ 匯出進度範本失敗: {e}")
            return False

    # ==================== 資料驗證 ====================

    def validate_progress_integrity(self) -> Dict[str, Any]:
        """
        驗證進度資料完整性

        Returns:
            Dict[str, Any]: 驗證結果
        """
        validation_result = {
            'is_valid': True,
            'total_stages': len(self.progress_stages),
            'issues': [],
            'duplicate_ids': [],
            'invalid_dates': [],
            'missing_fields': []
        }

        with self._lock:
            # 檢查重複的階段ID
            stage_ids = []
            for stage in self.progress_stages:
                if stage.stage_id in stage_ids:
                    validation_result['duplicate_ids'].append(stage.stage_id)
                    validation_result['is_valid'] = False
                else:
                    stage_ids.append(stage.stage_id)

            # 檢查必要欄位和資料邏輯
            for i, stage in enumerate(self.progress_stages):
                stage_issues = []

                # 檢查必要欄位
                if not stage.stage_id:
                    stage_issues.append("缺少階段ID")
                if not stage.stage_name:
                    stage_issues.append("缺少階段名稱")
                if not stage.case_id:
                    stage_issues.append("缺少案件ID")

                # 檢查日期邏輯
                if stage.start_date and stage.due_date and stage.start_date > stage.due_date:
                    stage_issues.append("開始日期晚於到期日期")
                    validation_result['invalid_dates'].append({
                        'stage_id': stage.stage_id,
                        'issue': '開始日期晚於到期日期'
                    })

                if stage.completion_date and stage.start_date and stage.completion_date < stage.start_date:
                    stage_issues.append("完成日期早於開始日期")
                    validation_result['invalid_dates'].append({
                        'stage_id': stage.stage_id,
                        'issue': '完成日期早於開始日期'
                    })

                # 檢查狀態與完成日期的一致性
                if stage.status == '已完成' and not stage.completion_date:
                    stage_issues.append("已完成但缺少完成日期")

                if stage.status != '已完成' and stage.completion_date:
                    stage_issues.append("未完成但有完成日期")

                if stage_issues:
                    validation_result['missing_fields'].append({
                        'stage_index': i,
                        'stage_id': stage.stage_id,
                        'issues': stage_issues
                    })
                    validation_result['is_valid'] = False

        return validation_result

    def cleanup_invalid_progress(self) -> int:
        """
        清理無效的進度資料

        Returns:
            int: 清理的進度數量
        """
        cleaned_count = 0

        with self._lock:
            valid_stages = []
            for stage in self.progress_stages:
                # 檢查基本必要欄位
                if stage.stage_id and stage.stage_name and stage.case_id:
                    valid_stages.append(stage)
                else:
                    print(f"🧹 清理無效進度: {stage.stage_id or 'Unknown'}")
                    cleaned_count += 1

            self.progress_stages = valid_stages
            if cleaned_count > 0:
                self._save_progress_data()

        print(f"✅ 進度清理完成，移除了 {cleaned_count} 筆無效進度")
        return cleaned_count

    # ==================== 備份與恢復 ====================

    def backup_progress_data(self, backup_path: str) -> bool:
        """
        備份進度資料

        Args:
            backup_path: 備份檔案路徑

        Returns:
            bool: 備份是否成功
        """
        try:
            os.makedirs(os.path.dirname(backup_path), exist_ok=True)

            backup_data = {
                'backup_time': datetime.now().isoformat(),
                'total_stages': len(self.progress_stages),
                'progress_stages': [stage.to_dict() for stage in self.progress_stages]
            }

            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, ensure_ascii=False, indent=2, default=str)

            print(f"✅ 進度資料備份成功: {backup_path}")
            return True

        except Exception as e:
            print(f"❌ 進度備份失敗: {e}")
            return False