#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
API Schemas 模組
統一管理所有API資料模型
"""

# LINE相關模型
from .line_schemas import (
    # 基礎模型
    ConversationStep,
    MessageType,

    # 請求模型
    LineWebhookRequest,
    ConversationContext,

    # 回應模型
    LineWebhookResponse,
    QuickReplyOption,
    QuickReplyResponse,

    # 案件選擇模型
    CaseSelectionRequest,
    CaseSelectionResponse,

    # 系統狀態模型
    SystemStatusResponse,
    ErrorResponse,

    # 工具函數
    create_text_response,
    create_quick_reply_response,
    create_error_response
)

# 案件相關模型
from .case_schemas import (
    # 基礎案件模型
    CaseDetailResponse,
    CaseListResponse,

    # 增強案件模型
    DetailedCaseResponse,
    DetailedCaseListResponse,

    # 進度相關模型
    ProgressStageDetail,
    CaseProgressHistoryResponse,
    CaseProgressUpdateRequest,
    CaseProgressUpdateResponse,

    # 搜尋相關模型
    CaseSearchRequest,
    CaseSearchResult,

    # 統計相關模型
    CaseStatistics,

    # 選擇記錄模型
    FinalCaseSelectionRequest,
    FinalCaseSelectionResponse,

    # 工具函數
    convert_case_data_to_response,
    create_case_list_response
)

# 匯出所有模型
__all__ = [
    # LINE相關
    "ConversationStep",
    "MessageType",
    "LineWebhookRequest",
    "ConversationContext",
    "LineWebhookResponse",
    "QuickReplyOption",
    "QuickReplyResponse",
    "CaseSelectionRequest",
    "CaseSelectionResponse",
    "SystemStatusResponse",
    "ErrorResponse",
    "create_text_response",
    "create_quick_reply_response",
    "create_error_response",

    # 案件相關
    "CaseDetailResponse",
    "CaseListResponse",
    "DetailedCaseResponse",
    "DetailedCaseListResponse",
    "ProgressStageDetail",
    "CaseProgressHistoryResponse",
    "CaseProgressUpdateRequest",
    "CaseProgressUpdateResponse",
    "CaseSearchRequest",
    "CaseSearchResult",
    "CaseStatistics",
    "FinalCaseSelectionRequest",
    "FinalCaseSelectionResponse",
    "convert_case_data_to_response",
    "create_case_list_response"
]

# 版本資訊
__version__ = "2.0.0"
__author__ = "專業Python工程團隊"
__description__ = "LINE BOT案件管理API資料模型"