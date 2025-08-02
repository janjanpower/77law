#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
案件資料模型 - 修復版本
確保正確的序列化和反序列化支援
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
import json


@dataclass
class CaseData:
    """案件資料類別 - 完整版本"""
    case_id: str
    case_type: str  # 案件類型（刑事/民事/行政等）
    client: str     # 當事人

    # 可選基本欄位
    lawyer: Optional[str] = None    # 委任律師
    legal_affairs: Optional[str] = None  # 法務
    progress: str = "待處理"  # 當前進度狀態
    status: str = "待處理"    # 案件狀態（待處理、進行中、已完成、暫停等）

    # 詳細資訊欄位
    case_reason: Optional[str] = None    # 案由
    case_number: Optional[str] = None    # 案號
    opposing_party: Optional[str] = None # 對造
    court: Optional[str] = None          # 負責法院
    division: Optional[str] = None       # 負責股別
    notes: Optional[str] = None          # 備註

    # 進度追蹤相關
    progress_date: Optional[str] = None  # 當前進度的日期
    progress_stages: Dict[str, str] = field(default_factory=dict)  # 進度階段記錄 {階段: 日期}
    progress_notes: Dict[str, str] = field(default_factory=dict)   # 進度階段備註 {階段: 備註}
    progress_times: Dict[str, str] = field(default_factory=dict)   # 進度階段時間 {階段: 時間}

    # 時間戳記
    creation_date: Optional[datetime] = None
    last_modified: Optional[datetime] = None

    # 向後相容的欄位別名
    created_date: Optional[datetime] = field(default=None, init=False)
    updated_date: Optional[datetime] = field(default=None, init=False)

    # 新增：重要日期支援（用於驗證服務相容性）
    important_dates: List[Dict[str, Any]] = field(default_factory=list)

    def __post_init__(self):
        """初始化後處理"""
        # 設定預設時間
        if self.creation_date is None:
            self.creation_date = datetime.now()
        if self.last_modified is None:
            self.last_modified = datetime.now()

        # 向後相容：同步時間欄位
        if self.created_date is None:
            self.created_date = self.creation_date
        if self.updated_date is None:
            self.updated_date = self.last_modified

        # 確保字典欄位存在
        if not isinstance(self.progress_stages, dict):
            self.progress_stages = {}
        if not isinstance(self.progress_notes, dict):
            self.progress_notes = {}
        if not isinstance(self.progress_times, dict):
            self.progress_times = {}

    def update_progress(self, new_progress: str, progress_date: str = None,
                       note: str = None, time: str = None):
        """
        更新進度

        Args:
            new_progress: 新進度名稱
            progress_date: 進度日期
            note: 備註
            time: 時間
        """
        if progress_date is None:
            progress_date = datetime.now().strftime('%Y-%m-%d')

        self.progress = new_progress
        self.progress_date = progress_date
        self.progress_stages[new_progress] = progress_date
        self.last_modified = datetime.now()

        # 更新備註
        if note:
            self.progress_notes[new_progress] = note
        elif new_progress in self.progress_notes and note is None:
            # 如果明確傳入 None，則移除現有備註
            pass  # 保留現有備註

        # 更新時間
        if time:
            self.progress_times[new_progress] = time

    def to_dict(self) -> Dict[str, Any]:
        """
        轉換為字典格式

        Returns:
            Dict[str, Any]: 字典格式的案件資料
        """
        try:
            data = {
                'case_id': self.case_id,
                'case_type': self.case_type,
                'client': self.client,
                'lawyer': self.lawyer,
                'legal_affairs': self.legal_affairs,
                'progress': self.progress,
                'status': self.status,
                'case_reason': self.case_reason,
                'case_number': self.case_number,
                'opposing_party': self.opposing_party,
                'court': self.court,
                'division': self.division,
                'notes': self.notes,
                'progress_date': self.progress_date,
                'progress_stages': self.progress_stages,
                'progress_notes': self.progress_notes,
                'progress_times': self.progress_times,
                'creation_date': self.creation_date.isoformat() if self.creation_date else None,
                'last_modified': self.last_modified.isoformat() if self.last_modified else None,
                # 向後相容
                'created_date': self.created_date.isoformat() if self.created_date else None,
                'updated_date': self.updated_date.isoformat() if self.updated_date else None
            }
            return data
        except Exception as e:
            print(f"❌ CaseData.to_dict() 失敗: {e}")
            # 返回基本資料以避免完全失敗
            return {
                'case_id': getattr(self, 'case_id', ''),
                'case_type': getattr(self, 'case_type', ''),
                'client': getattr(self, 'client', ''),
                'error': f"序列化失敗: {str(e)}"
            }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CaseData':
        """
        從字典建立案件資料

        Args:
            data: 字典格式的案件資料

        Returns:
            CaseData: 案件資料物件
        """
        try:
            # 處理必要欄位
            case_id = data.get('case_id', '')
            case_type = data.get('case_type', '')
            client = data.get('client', '')

            if not case_id or not case_type or not client:
                raise ValueError(f"缺少必要欄位: case_id={case_id}, case_type={case_type}, client={client}")

            # 處理進度追蹤字典
            progress_stages = data.get('progress_stages', {})
            progress_notes = data.get('progress_notes', {})
            progress_times = data.get('progress_times', {})

            # 確保是字典格式
            if not isinstance(progress_stages, dict):
                progress_stages = {}
            if not isinstance(progress_notes, dict):
                progress_notes = {}
            if not isinstance(progress_times, dict):
                progress_times = {}

            # 處理時間欄位
            creation_date = None
            last_modified = None

            # 優先使用新的欄位名稱
            if 'creation_date' in data and data['creation_date']:
                try:
                    creation_date = datetime.fromisoformat(data['creation_date'])
                except:
                    pass
            elif 'created_date' in data and data['created_date']:
                try:
                    creation_date = datetime.fromisoformat(data['created_date'])
                except:
                    pass

            if 'last_modified' in data and data['last_modified']:
                try:
                    last_modified = datetime.fromisoformat(data['last_modified'])
                except:
                    pass
            elif 'updated_date' in data and data['updated_date']:
                try:
                    last_modified = datetime.fromisoformat(data['updated_date'])
                except:
                    pass

            # 建立案件物件
            case = cls(
                case_id=case_id,
                case_type=case_type,
                client=client,
                lawyer=data.get('lawyer'),
                legal_affairs=data.get('legal_affairs'),
                progress=data.get('progress', '待處理'),
                status=data.get('status', '待處理'),
                case_reason=data.get('case_reason'),
                case_number=data.get('case_number'),
                opposing_party=data.get('opposing_party'),
                court=data.get('court'),
                division=data.get('division'),
                notes=data.get('notes'),
                progress_date=data.get('progress_date'),
                progress_stages=progress_stages,
                progress_notes=progress_notes,
                progress_times=progress_times,
                creation_date=creation_date,
                last_modified=last_modified
            )

            return case

        except Exception as e:
            print(f"❌ CaseData.from_dict() 失敗: {e}")
            print(f"   輸入資料: {data}")
            # 嘗試建立最基本的案件物件
            try:
                return cls(
                    case_id=data.get('case_id', f'ERROR_{datetime.now().strftime("%Y%m%d%H%M%S")}'),
                    case_type=data.get('case_type', '未知'),
                    client=data.get('client', '未知')
                )
            except Exception as fallback_error:
                print(f"❌ 連基本案件物件都無法建立: {fallback_error}")
                raise ValueError(f"無法從字典建立 CaseData: {str(e)}")

    def validate(self) -> Tuple[bool, List[str]]:
        """
        驗證案件資料

        Returns:
            Tuple[bool, List[str]]: (是否有效, 錯誤訊息列表)
        """
        errors = []

        # 檢查必要欄位
        if not self.case_id or not self.case_id.strip():
            errors.append("案件ID不能為空")

        if not self.case_type or not self.case_type.strip():
            errors.append("案件類型不能為空")

        if not self.client or not self.client.strip():
            errors.append("當事人不能為空")

        # 檢查案件ID格式（可選）
        if self.case_id and len(self.case_id) < 3:
            errors.append("案件ID長度至少3個字元")

        # 檢查進度字典格式
        if not isinstance(self.progress_stages, dict):
            errors.append("進度階段必須是字典格式")

        if not isinstance(self.progress_notes, dict):
            errors.append("進度備註必須是字典格式")

        if not isinstance(self.progress_times, dict):
            errors.append("進度時間必須是字典格式")

        return len(errors) == 0, errors

    def __str__(self) -> str:
        """字串表示"""
        return f"案件[{self.case_id}] {self.client} - {self.case_type} ({self.progress})"

    def __repr__(self) -> str:
        """開發者表示"""
        return f"CaseData(case_id='{self.case_id}', client='{self.client}', case_type='{self.case_type}')"

    def copy(self) -> 'CaseData':
        """建立副本"""
        return CaseData.from_dict(self.to_dict())

    def get_progress_summary(self) -> Dict[str, Any]:
        """
        取得進度摘要

        Returns:
            Dict[str, Any]: 進度摘要資訊
        """
        return {
            'current_progress': self.progress,
            'progress_date': self.progress_date,
            'total_stages': len(self.progress_stages),
            'has_notes': len(self.progress_notes) > 0,
            'has_times': len(self.progress_times) > 0,
            'last_modified': self.last_modified.isoformat() if self.last_modified else None
        }

    # 向後相容的方法
    def update_timestamp(self):
        """更新時間戳記"""
        self.last_modified = datetime.now()
        self.updated_date = self.last_modified

    @property
    def is_valid(self) -> bool:
        """檢查案件資料是否有效"""
        valid, _ = self.validate()
        return valid


# 便利函數
def create_case_from_basic_info(case_id: str, client: str, case_type: str, **kwargs) -> CaseData:
    """
    從基本資訊建立案件

    Args:
        case_id: 案件ID
        client: 當事人
        case_type: 案件類型
        **kwargs: 其他選項

    Returns:
        CaseData: 案件資料物件
    """
    return CaseData(
        case_id=case_id,
        client=client,
        case_type=case_type,
        **kwargs
    )


def batch_create_cases_from_list(cases_data: List[Dict[str, Any]]) -> List[CaseData]:
    """
    批次從字典列表建立案件

    Args:
        cases_data: 字典格式的案件資料列表

    Returns:
        List[CaseData]: 案件物件列表
    """
    cases = []
    for data in cases_data:
        try:
            case = CaseData.from_dict(data)
            cases.append(case)
        except Exception as e:
            print(f"❌ 建立案件失敗: {e}, 資料: {data}")

    return cases