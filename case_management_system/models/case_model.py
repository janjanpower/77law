from dataclasses import dataclass, field
from typing import Optional, Dict, Any
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

    # 新增詳細資訊欄位
    case_reason: Optional[str] = None    # 案由
    case_number: Optional[str] = None    # 案號
    opposing_party: Optional[str] = None # 對造
    court: Optional[str] = None          # 負責法院
    division: Optional[str] = None       # 負責股別

    # 🔥 新增：進度日期追蹤
    progress_date: Optional[str] = None  # 當前進度的日期
    progress_history: Dict[str, str] = field(default_factory=dict)  # 進度歷史記錄 {進度: 日期}

    created_date: datetime = None
    updated_date: datetime = None

    def __post_init__(self):
        if self.created_date is None:
            self.created_date = datetime.now()
        if self.updated_date is None:
            self.updated_date = datetime.now()

    def update_progress(self, new_progress: str, progress_date: str = None):
        """
        更新進度並記錄日期

        Args:
            new_progress: 新的進度狀態
            progress_date: 進度日期（格式：YYYY-MM-DD），如果為None則使用當前日期
        """
        if progress_date is None:
            progress_date = datetime.now().strftime('%Y-%m-%d')

        # 記錄舊進度到歷史中
        if self.progress and self.progress_date:
            self.progress_history[self.progress] = self.progress_date

        # 更新當前進度
        self.progress = new_progress
        self.progress_date = progress_date

        # 也記錄到歷史中
        self.progress_history[new_progress] = progress_date

        # 更新修改時間
        self.updated_date = datetime.now()

    def get_progress_date(self, progress_stage: str) -> Optional[str]:
        """
        取得指定進度階段的日期

        Args:
            progress_stage: 進度階段名稱

        Returns:
            str: 該階段的日期，如果不存在則返回None
        """
        return self.progress_history.get(progress_stage)

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
            'progress_history': self.progress_history,
            'created_date': self.created_date.isoformat(),
            'updated_date': self.updated_date.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CaseData':
        """從字典建立案件資料"""
        # 處理進度歷史資料的向後相容性
        progress_history = data.get('progress_history', {})
        if not progress_history and data.get('progress') and data.get('progress_date'):
            # 如果沒有歷史記錄但有當前進度和日期，建立基本記錄
            progress_history = {data['progress']: data.get('progress_date')}

        return cls(
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
            progress_history=progress_history,
            created_date=datetime.fromisoformat(data['created_date']),
            updated_date=datetime.fromisoformat(data['updated_date'])
        )