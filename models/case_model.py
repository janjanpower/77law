#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime

@dataclass
class CaseData:
    """案件資料類別"""
    case_id: str
    case_type: str  # 案件類型（刑事/民事）
    client: str     # 當事人
    lawyer: Optional[str] = None    # 委任律師
    legal_affairs: Optional[str] = None  # 法務
    progress: str = "待處理"  # 進度追蹤

    # 詳細資訊欄位
    case_reason: Optional[str] = None    # 案由
    case_number: Optional[str] = None    # 案號
    opposing_party: Optional[str] = None # 對造
    court: Optional[str] = None          # 負責法院
    division: Optional[str] = None       # 負責股別

    # 簡化的進度追蹤
    progress_date: Optional[str] = None  # 當前進度的日期
    progress_stages: Dict[str, str] = field(default_factory=dict)  # 進度階段記錄 {階段: 日期}
    progress_notes: Dict[str, str] = field(default_factory=dict)   # 🔥 新增：進度階段備註 {階段: 備註}
    progress_times: Dict[str, str] = field(default_factory=dict)   # 🔥 新增：進度階段時間 {階段: 時間}

    created_date: datetime = None
    updated_date: datetime = None

    def __post_init__(self):
        if self.created_date is None:
            self.created_date = datetime.now()
        if self.updated_date is None:
            self.updated_date = datetime.now()

        # 確保progress_notes和progress_times字典存在
        if not hasattr(self, 'progress_notes') or self.progress_notes is None:
            self.progress_notes = {}
        if not hasattr(self, 'progress_times') or self.progress_times is None:
            self.progress_times = {}

    def update_progress(self, new_progress: str, progress_date: str = None, note: str = None, time: str = None):
        """更新進度"""
        if progress_date is None:
            progress_date = datetime.now().strftime('%Y-%m-%d')

        self.progress = new_progress
        self.progress_date = progress_date
        self.progress_stages[new_progress] = progress_date

        # 🔥 新增：更新備註
        if note:
            self.progress_notes[new_progress] = note
        elif new_progress in self.progress_notes and not note:
            # 如果傳入空備註，移除現有備註
            del self.progress_notes[new_progress]

        # 🔥 新增：更新時間
        if time:
            self.progress_times[new_progress] = time
        elif new_progress in self.progress_times and not time:
            # 如果傳入空時間，移除現有時間
            del self.progress_times[new_progress]

        self.updated_date = datetime.now()

    def add_progress_stage(self, stage_name: str, stage_date: str = None, note: str = None, time: str = None):
        """新增進度階段"""
        if stage_date is None:
            stage_date = datetime.now().strftime('%Y-%m-%d')

        self.progress_stages[stage_name] = stage_date

        # 🔥 新增：儲存備註
        if note:
            self.progress_notes[stage_name] = note

        # 🔥 新增：儲存時間
        if time:
            self.progress_times[stage_name] = time

        self.updated_date = datetime.now()

    def update_stage_note(self, stage_name: str, note: str):
        """更新階段備註"""
        if stage_name in self.progress_stages:
            if note:
                self.progress_notes[stage_name] = note
            elif stage_name in self.progress_notes:
                del self.progress_notes[stage_name]
            self.updated_date = datetime.now()

    def update_stage_time(self, stage_name: str, time: str):
        """更新階段時間"""
        if stage_name in self.progress_stages:
            if time:
                self.progress_times[stage_name] = time
            elif stage_name in self.progress_times:
                del self.progress_times[stage_name]
            self.updated_date = datetime.now()

    def get_stage_time(self, stage_name: str) -> str:
        """取得階段時間"""
        return self.progress_times.get(stage_name, "")

    def get_stage_note(self, stage_name: str) -> str:
        """取得階段備註"""
        return self.progress_notes.get(stage_name, "")

    def has_stage_note(self, stage_name: str) -> bool:
        """檢查階段是否有備註"""
        return stage_name in self.progress_notes and bool(self.progress_notes[stage_name].strip())

    def remove_progress_stage(self, stage_name: str) -> bool:
        """
        移除進度階段（改善版本）

        Args:
            stage_name: 階段名稱

        Returns:
            bool: 移除是否成功
        """
        try:
            removed_anything = False

            # 移除進度階段記錄
            if stage_name in self.progress_stages:
                del self.progress_stages[stage_name]
                removed_anything = True
                print(f"✅ 已移除階段記錄: {stage_name}")

            # 移除相關備註
            if stage_name in self.progress_notes:
                del self.progress_notes[stage_name]
                print(f"✅ 已移除階段備註: {stage_name}")

            # 移除相關時間
            if stage_name in self.progress_times:
                del self.progress_times[stage_name]
                print(f"✅ 已移除階段時間: {stage_name}")

            # 如果移除的是當前進度，需要重新設定當前進度
            if stage_name == self.progress:
                # 選擇最新的階段作為當前進度，如果沒有則設為空
                if self.progress_stages:
                    # 按日期排序，選擇最新的
                    sorted_stages = sorted(
                        self.progress_stages.items(),
                        key=lambda x: x[1],
                        reverse=True
                    )
                    self.progress = sorted_stages[0][0]
                    print(f"✅ 當前進度已更新為: {self.progress}")
                else:
                    self.progress = ""
                    print(f"✅ 當前進度已清空（無其他階段）")

            if removed_anything:
                self.updated_date = datetime.now()
                return True
            else:
                print(f"⚠️ 階段 {stage_name} 不存在於記錄中")
                return False

        except Exception as e:
            print(f"❌ 移除進度階段失敗: {e}")
            return False

    def update_stage_date(self, stage_name: str, new_date: str):
        """更新階段日期"""
        if stage_name in self.progress_stages:
            self.progress_stages[stage_name] = new_date
            if stage_name == self.progress:
                self.progress_date = new_date
            self.updated_date = datetime.now()

    def get_ordered_stages(self) -> List[tuple]:
        """取得按日期排序的階段列表"""
        return sorted(self.progress_stages.items(), key=lambda x: x[1] if x[1] else '9999-12-31')

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式"""
        return {
            'case_id': self.case_id,
            'case_type': self.case_type,
            'client': self.client,
            'lawyer': self.lawyer,
            'legal_affairs': self.legal_affairs,
            'progress': self.progress,
            'case_reason': self.case_reason,
            'case_number': self.case_number,
            'opposing_party': self.opposing_party,
            'court': self.court,
            'division': self.division,
            'progress_date': self.progress_date,
            'progress_stages': self.progress_stages,
            'progress_notes': self.progress_notes,  # 🔥 新增：匯出備註
            'progress_times': self.progress_times,  # 🔥 新增：匯出時間
            'created_date': self.created_date.isoformat(),
            'updated_date': self.updated_date.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CaseData':
        """從字典建立案件資料"""
        # 處理舊資料的相容性
        progress_stages = data.get('progress_stages', {})
        progress_notes = data.get('progress_notes', {})  # 🔥 新增：載入備註
        progress_times = data.get('progress_times', {})  # 🔥 新增：載入時間

        # 從舊的 progress_history 或 experienced_stages 轉換
        if not progress_stages:
            if 'progress_history' in data:
                progress_stages = data['progress_history']
            elif 'experienced_stages' in data and data.get('progress'):
                # 從經歷階段重建
                progress_stages = {}
                if data.get('progress') and data.get('progress_date'):
                    progress_stages[data['progress']] = data['progress_date']

        case = cls(
            case_id=data['case_id'],
            case_type=data['case_type'],
            client=data['client'],
            lawyer=data.get('lawyer'),
            legal_affairs=data.get('legal_affairs'),
            progress=data.get('progress', '待處理'),
            case_reason=data.get('case_reason'),
            case_number=data.get('case_number'),
            opposing_party=data.get('opposing_party'),
            court=data.get('court'),
            division=data.get('division'),
            progress_date=data.get('progress_date'),
            progress_stages=progress_stages,
            progress_notes=progress_notes,  # 🔥 新增：設定備註
            progress_times=progress_times,  # 🔥 新增：設定時間
            created_date=datetime.fromisoformat(data['created_date']),
            updated_date=datetime.fromisoformat(data['updated_date'])
        )

        return case