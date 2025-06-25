from dataclasses import dataclass
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

    created_date: datetime = None
    updated_date: datetime = None

    def __post_init__(self):
        if self.created_date is None:
            self.created_date = datetime.now()
        if self.updated_date is None:
            self.updated_date = datetime.now()

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
            'created_date': self.created_date.isoformat(),
            'updated_date': self.updated_date.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CaseData':
        """從字典建立案件資料"""
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
            created_date=datetime.fromisoformat(data['created_date']),
            updated_date=datetime.fromisoformat(data['updated_date'])
        )