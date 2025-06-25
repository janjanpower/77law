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

    # 新增詳細資訊欄位
    case_reason: Optional[str] = None    # 案由
    case_number: Optional[str] = None    # 案號
    opposing_party: Optional[str] = None # 對造
    court: Optional[str] = None          # 負責法院
    division: Optional[str] = None       # 負責股別

    # 🔥 修正：真正漸進式進度追蹤
    progress_date: Optional[str] = None  # 當前進度的日期
    progress_history: Dict[str, str] = field(default_factory=dict)  # 進度歷史記錄 {進度: 日期}
    experienced_stages: List[str] = field(default_factory=list)  # 🔥 改名：實際經歷過的進度階段（按時間順序）

    created_date: datetime = None
    updated_date: datetime = None

    def __post_init__(self):
        if self.created_date is None:
            self.created_date = datetime.now()
        if self.updated_date is None:
            self.updated_date = datetime.now()

        # 🔥 修正：新增案件時只包含當前進度
        if not self.experienced_stages and self.progress:
            self.experienced_stages = [self.progress]

        # 🔥 修正：確保進度歷史包含當前進度
        if self.progress and self.progress_date and self.progress not in self.progress_history:
            self.progress_history[self.progress] = self.progress_date

    def update_progress(self, new_progress: str, progress_date: str = None):
        """
        🔥 修正：真正漸進式更新進度（只添加實際經歷的階段）

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
        old_progress = self.progress
        self.progress = new_progress
        self.progress_date = progress_date

        # 記錄到歷史中
        self.progress_history[new_progress] = progress_date

        # 🔥 修正：只有當新進度不在經歷過的階段中時，才添加
        if new_progress not in self.experienced_stages:
            self.experienced_stages.append(new_progress)

        # 更新修改時間
        self.updated_date = datetime.now()

    def get_display_stages(self) -> List[str]:
        """
        🔥 修正：只返回實際經歷過的進度階段

        Returns:
            List[str]: 實際經歷過的進度階段列表（按時間順序）
        """
        return self.experienced_stages.copy()

    def get_progress_date(self, progress_stage: str) -> Optional[str]:
        """
        取得指定進度階段的日期

        Args:
            progress_stage: 進度階段名稱

        Returns:
            str: 該階段的日期，如果不存在則返回None
        """
        return self.progress_history.get(progress_stage)

    def is_stage_experienced(self, stage: str) -> bool:
        """
        🔥 修正：檢查指定階段是否已經歷過

        Args:
            stage: 進度階段名稱

        Returns:
            bool: 是否已經歷過
        """
        return stage in self.experienced_stages

    def get_current_stage_index(self) -> int:
        """
        🔥 修正：取得當前進度在經歷階段中的索引

        Returns:
            int: 當前進度的索引，如果不存在則返回 -1
        """
        try:
            return self.experienced_stages.index(self.progress)
        except ValueError:
            return -1

    def get_next_available_stages(self) -> List[str]:
        """
        🔥 修正：取得可以前進的下一個階段列表（基於標準流程）

        Returns:
            List[str]: 可以前進的階段列表
        """
        from config.settings import AppConfig
        all_stages = AppConfig.get_progress_options(self.case_type)

        try:
            current_index = all_stages.index(self.progress)
            if current_index < len(all_stages) - 1:
                return all_stages[current_index + 1:]
            return []
        except ValueError:
            # 如果當前階段不在標準列表中，返回所有階段
            return all_stages

    def add_custom_stage(self, stage_name: str, stage_date: str = None):
        """
        🔥 新增：添加自訂進度階段

        Args:
            stage_name: 階段名稱
            stage_date: 階段日期
        """
        if stage_date is None:
            stage_date = datetime.now().strftime('%Y-%m-%d')

        if stage_name not in self.experienced_stages:
            self.experienced_stages.append(stage_name)

        self.progress_history[stage_name] = stage_date
        self.updated_date = datetime.now()

    def remove_stage(self, stage_name: str) -> bool:
        """
        🔥 新增：移除階段（只能移除非當前階段）

        Args:
            stage_name: 要移除的階段名稱

        Returns:
            bool: 是否成功移除
        """
        if stage_name == self.progress:
            return False  # 不能移除當前階段

        if stage_name in self.experienced_stages:
            self.experienced_stages.remove(stage_name)

        if stage_name in self.progress_history:
            del self.progress_history[stage_name]

        self.updated_date = datetime.now()
        return True

    def validate_progress_consistency(self) -> bool:
        """
        🔥 修正：驗證進度資料的一致性

        Returns:
            bool: 資料是否一致
        """
        # 檢查當前進度是否在經歷階段中
        if self.progress not in self.experienced_stages:
            return False

        # 檢查進度歷史是否包含當前進度
        if self.progress not in self.progress_history:
            return False

        # 檢查經歷階段是否都有對應的歷史記錄
        for stage in self.experienced_stages:
            if stage not in self.progress_history:
                return False

        return True

    def repair_progress_data(self):
        """
        🔥 修正：修復進度資料的不一致問題
        """
        # 確保當前進度在歷史中
        if self.progress and self.progress_date and self.progress not in self.progress_history:
            self.progress_history[self.progress] = self.progress_date

        # 確保當前進度在經歷階段中
        if self.progress and self.progress not in self.experienced_stages:
            self.experienced_stages.append(self.progress)

        # 移除歷史中沒有對應經歷階段的記錄
        stages_to_remove = []
        for stage in self.progress_history:
            if stage not in self.experienced_stages:
                stages_to_remove.append(stage)

        for stage in stages_to_remove:
            del self.progress_history[stage]

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
            'experienced_stages': self.experienced_stages,  # 🔥 修正欄位名稱
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

        # 🔥 處理經歷階段的向後相容性（支援舊的 completed_stages 欄位）
        experienced_stages = data.get('experienced_stages', data.get('completed_stages', []))
        if not experienced_stages and data.get('progress'):
            # 如果沒有經歷階段記錄，至少包含當前進度
            experienced_stages = [data['progress']]

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
            progress_history=progress_history,
            experienced_stages=experienced_stages,  # 🔥 修正欄位名稱
            created_date=datetime.fromisoformat(data['created_date']),
            updated_date=datetime.fromisoformat(data['updated_date'])
        )

        # 🔥 修正：建立後驗證和修復資料一致性
        if not case.validate_progress_consistency():
            case.repair_progress_data()

        return case