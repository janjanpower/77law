from typing import Optional, Dict
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class CaseRecord:
    case_id: str                    # 案件編號
    case_type: str                  # 案件類型（刑事/民事）
    client: str                     # 當事人
    lawyer: Optional[str] = None    # 委任律師
    legal_affairs: Optional[str] = None  # 法務
    progress: str = "待處理"         # 當前進度

    # 詳細資訊
    case_reason: Optional[str] = None    # 案由
    case_number: Optional[str] = None    # 案號
    opposing_party: Optional[str] = None # 對造
    court: Optional[str] = None          # 負責法院
    division: Optional[str] = None       # 負責股別

    # 簡化進度追蹤
    progress_date: Optional[str] = None                    # 當前進度日期
    progress_stages: Dict[str, str] = field(default_factory=dict) # {階段: 日期}
    progress_notes: Dict[str, str] = field(default_factory=dict)  # {階段: 備註}
    progress_times: Dict[str, str] = field(default_factory=dict)  # {階段: 時間}

    created_date: Optional[datetime] = None
    updated_date: Optional[datetime] = None
