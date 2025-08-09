#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
案件相關資料模型
處理案件查詢、更新、進度管理的資料結構
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime

# ==================== 基礎案件模型 ====================

class CaseDetailResponse(BaseModel):
    """案件詳細資料回應模型"""
    case_id: str = Field(..., description="案件編號")
    case_type: str = Field(..., description="案件類型")
    client: str = Field(..., description="當事人姓名")
    lawyer: Optional[str] = Field(default=None, description="委任律師")
    legal_affairs: Optional[str] = Field(default=None, description="法務人員")
    progress: str = Field(..., description="當前進度")
    case_reason: Optional[str] = Field(default=None, description="案由")
    case_number: Optional[str] = Field(default=None, description="案號")
    opposing_party: Optional[str] = Field(default=None, description="對造")
    court: Optional[str] = Field(default=None, description="負責法院")
    division: Optional[str] = Field(default=None, description="負責股別")
    progress_date: Optional[str] = Field(default=None, description="進度日期")
    progress_stages: Dict[str, str] = Field(default_factory=dict, description="進度階段記錄")
    progress_notes: Dict[str, str] = Field(default_factory=dict, description="進度備註")
    progress_times: Dict[str, str] = Field(default_factory=dict, description="進度時間")
    created_date: str = Field(..., description="建立日期")
    updated_date: str = Field(..., description="更新日期")
    folder_info: Optional[Dict[str, Any]] = Field(default=None, description="案件資料夾資訊")

class CaseListResponse(BaseModel):
    """案件列表回應模型"""
    total_count: int = Field(..., description="總案件數")
    cases: List[CaseDetailResponse] = Field(..., description="案件列表")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat(), description="查詢時間")

# ==================== 增強的案件模型 ====================

class DetailedCaseResponse(BaseModel):
    """增強的案件詳細資料回應模型 - 包含案號、對造、股別等"""
    case_id: str = Field(..., description="案件編號")
    case_type: str = Field(..., description="案件類型")
    client: str = Field(..., description="當事人姓名")
    lawyer: Optional[str] = Field(default=None, description="委任律師")
    legal_affairs: Optional[str] = Field(default=None, description="法務人員")
    progress: str = Field(..., description="當前進度")

    # 詳細資訊欄位
    case_reason: Optional[str] = Field(default=None, description="案由")
    case_number: Optional[str] = Field(default=None, description="案號")
    opposing_party: Optional[str] = Field(default=None, description="對造")
    court: Optional[str] = Field(default=None, description="負責法院")
    division: Optional[str] = Field(default=None, description="負責股別")

    # 進度相關的詳細資訊
    progress_date: Optional[str] = Field(default=None, description="當前進度日期")
    progress_stages: Dict[str, str] = Field(default_factory=dict, description="進度階段與日期記錄")
    progress_notes: Dict[str, str] = Field(default_factory=dict, description="各階段備註")
    progress_times: Dict[str, str] = Field(default_factory=dict, description="各階段時間")

    created_date: str = Field(..., description="建立日期")
    updated_date: str = Field(..., description="更新日期")
    folder_info: Optional[Dict[str, Any]] = Field(default=None, description="案件資料夾資訊")

class DetailedCaseListResponse(BaseModel):
    """詳細案件列表回應模型"""
    total_count: int = Field(..., description="總案件數")
    cases: List[DetailedCaseResponse] = Field(..., description="案件列表")
    search_criteria: Optional[Dict[str, Any]] = Field(default=None, description="搜尋條件")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat(), description="查詢時間")

# ==================== 進度相關模型 ====================

class ProgressStageDetail(BaseModel):
    """進度階段詳細資訊模型"""
    stage_name: str = Field(..., description="階段名稱")
    date: Optional[str] = Field(default=None, description="階段日期")
    time: Optional[str] = Field(default=None, description="階段時間")
    note: Optional[str] = Field(default=None, description="階段備註")
    order: int = Field(default=0, description="階段順序")

class CaseProgressHistoryResponse(BaseModel):
    """案件進度歷史回應模型"""
    case_id: str = Field(..., description="案件編號")
    client: str = Field(..., description="當事人姓名")
    case_type: str = Field(..., description="案件類型")
    current_progress: str = Field(..., description="當前進度")
    total_stages: int = Field(..., description="總階段數")
    progress_stages: List[ProgressStageDetail] = Field(..., description="進度階段詳細列表")
    last_updated: str = Field(..., description="最後更新時間")

class CaseProgressUpdateRequest(BaseModel):
    """案件進度更新請求模型"""
    case_id: str = Field(..., description="案件編號")
    new_progress: str = Field(..., description="新進度")
    progress_date: Optional[str] = Field(default=None, description="進度日期")
    note: Optional[str] = Field(default=None, description="備註")
    time: Optional[str] = Field(default=None, description="時間")

class CaseProgressUpdateResponse(BaseModel):
    """案件進度更新回應模型"""
    success: bool = Field(..., description="更新是否成功")
    message: str = Field(..., description="回應訊息")
    case_id: str = Field(..., description="案件編號")
    new_progress: str = Field(..., description="新進度")
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat(), description="更新時間")

# ==================== 搜尋相關模型 ====================

class CaseSearchRequest(BaseModel):
    """案件搜尋請求模型"""
    keyword: Optional[str] = Field(default=None, description="關鍵字搜尋")
    case_type: Optional[str] = Field(default=None, description="案件類型")
    lawyer: Optional[str] = Field(default=None, description="律師")
    court: Optional[str] = Field(default=None, description="法院")
    division: Optional[str] = Field(default=None, description="股別")
    opposing_party: Optional[str] = Field(default=None, description="對造")
    progress: Optional[str] = Field(default=None, description="進度")

class CaseSearchResult(BaseModel):
    """案件搜尋結果模型"""
    total_found: int = Field(..., description="找到的案件總數")
    search_criteria: CaseSearchRequest = Field(..., description="搜尋條件")
    cases: List[CaseDetailResponse] = Field(..., description="符合條件的案件")
    search_time: str = Field(default_factory=lambda: datetime.now().isoformat(), description="搜尋時間")

# ==================== 統計相關模型 ====================

class CaseStatistics(BaseModel):
    """案件統計模型"""
    total_cases: int = Field(..., description="總案件數")
    case_types: Dict[str, int] = Field(..., description="各類型案件數量")
    progress_distribution: Dict[str, int] = Field(..., description="進度分布")
    lawyers: Dict[str, int] = Field(..., description="各律師案件數量")
    courts: Dict[str, int] = Field(..., description="各法院案件數量")
    recent_cases: int = Field(..., description="近期案件數量")
    urgent_cases: int = Field(..., description="緊急案件數量")
    generated_at: str = Field(default_factory=lambda: datetime.now().isoformat(), description="統計生成時間")

# ==================== 選擇記錄模型 ====================

class FinalCaseSelectionRequest(BaseModel):
    """最終案件選擇請求模型"""
    user_id: str = Field(..., description="用戶ID")
    selected_case_id: str = Field(..., description="選擇的案件編號")
    reason: Optional[str] = Field(default=None, description="選擇原因")

class FinalCaseSelectionResponse(BaseModel):
    """最終案件選擇回應模型"""
    selected_case: CaseDetailResponse = Field(..., description="選擇的案件詳細資料")
    selection_time: str = Field(default_factory=lambda: datetime.now().isoformat(), description="選擇時間")
    user_id: str = Field(..., description="用戶ID")
    success: bool = Field(default=True, description="選擇是否成功")
    message: str = Field(default="案件選擇成功", description="回應訊息")

# ==================== 工具函數 ====================

def convert_case_data_to_response(case_data) -> CaseDetailResponse:
    """將CaseData物件轉換為回應模型"""
    return CaseDetailResponse(
        case_id=case_data.case_id,
        case_type=case_data.case_type,
        client=case_data.client,
        lawyer=case_data.lawyer,
        legal_affairs=case_data.legal_affairs,
        progress=case_data.progress,
        case_reason=case_data.case_reason,
        case_number=case_data.case_number,
        opposing_party=case_data.opposing_party,
        court=case_data.court,
        division=case_data.division,
        progress_date=case_data.progress_date,
        progress_stages=case_data.progress_stages,
        progress_notes=getattr(case_data, 'progress_notes', {}),
        progress_times=getattr(case_data, 'progress_times', {}),
        created_date=case_data.created_date.isoformat() if case_data.created_date else "",
        updated_date=case_data.updated_date.isoformat() if case_data.updated_date else ""
    )

def create_case_list_response(cases: List, total_count: int = None) -> CaseListResponse:
    """建立案件列表回應"""
    if total_count is None:
        total_count = len(cases)

    case_responses = [convert_case_data_to_response(case) for case in cases]

    return CaseListResponse(
        total_count=total_count,
        cases=case_responses
    )