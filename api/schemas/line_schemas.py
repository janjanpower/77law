#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LINE BOT 相關資料模型
處理LINE Webhook請求和回應的資料結構
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

# ==================== 基礎模型 ====================

class ConversationStep(str, Enum):
    """對話步驟枚舉"""
    INITIAL = "initial"
    SEARCHING = "searching"
    SELECTING = "selecting"
    CONFIRMING = "confirming"
    COMPLETED = "completed"

class MessageType(str, Enum):
    """訊息類型枚舉"""
    TEXT = "text"
    QUICK_REPLY = "quick_reply"
    FLEX = "flex"
    IMAGE = "image"

# ==================== 請求模型 ====================

class LineWebhookRequest(BaseModel):
    """LINE Webhook 請求模型"""
    message: str = Field(..., description="用戶訊息內容")
    user_id: str = Field(..., description="LINE用戶ID")
    timestamp: Optional[str] = Field(default=None, description="訊息時間戳")
    message_type: MessageType = Field(default=MessageType.TEXT, description="訊息類型")

class ConversationContext(BaseModel):
    """對話上下文模型"""
    user_id: str = Field(..., description="用戶ID")
    step: ConversationStep = Field(default=ConversationStep.INITIAL, description="當前對話步驟")
    search_results: List[str] = Field(default_factory=list, description="搜尋結果")
    selected_case_id: Optional[str] = Field(default=None, description="選中的案件ID")
    last_message: Optional[str] = Field(default=None, description="最後一條訊息")
    created_at: datetime = Field(default_factory=datetime.now, description="建立時間")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新時間")

# ==================== 回應模型 ====================

class LineWebhookResponse(BaseModel):
    """LINE Webhook 回應模型"""
    type: MessageType = Field(default=MessageType.TEXT, description="回應訊息類型")
    text: str = Field(..., description="回應文字內容")
    user_id: str = Field(..., description="目標用戶ID")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat(), description="回應時間")
    success: bool = Field(default=True, description="處理是否成功")
    error_message: Optional[str] = Field(default=None, description="錯誤訊息")

class QuickReplyOption(BaseModel):
    """快速回覆選項模型"""
    text: str = Field(..., description="顯示文字")
    action_data: str = Field(..., description="動作資料")

class QuickReplyResponse(LineWebhookResponse):
    """快速回覆回應模型"""
    type: MessageType = Field(default=MessageType.QUICK_REPLY, description="回應類型")
    quick_reply_options: List[QuickReplyOption] = Field(..., description="快速回覆選項")

# ==================== 案件選擇相關模型 ====================

class CaseSelectionRequest(BaseModel):
    """案件選擇請求模型"""
    user_id: str = Field(..., description="用戶ID")
    selected_case_id: str = Field(..., description="選擇的案件編號")
    reason: Optional[str] = Field(default=None, description="選擇原因")

class CaseSelectionResponse(BaseModel):
    """案件選擇回應模型"""
    success: bool = Field(..., description="選擇是否成功")
    message: str = Field(..., description="回應訊息")
    case_id: str = Field(..., description="案件編號")
    selection_time: str = Field(default_factory=lambda: datetime.now().isoformat(), description="選擇時間")
    user_id: str = Field(..., description="用戶ID")

# ==================== 統計和摘要模型 ====================

class SystemStatusResponse(BaseModel):
    """系統狀態回應模型"""
    status: str = Field(default="healthy", description="系統狀態")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat(), description="檢查時間")
    version: str = Field(default="2.0.0", description="系統版本")
    active_conversations: int = Field(default=0, description="活躍對話數")
    total_cases: int = Field(default=0, description="總案件數")
    features: List[str] = Field(default_factory=list, description="可用功能列表")
    modules_status: Dict[str, bool] = Field(default_factory=dict, description="模組狀態")

# ==================== 錯誤處理模型 ====================

class ErrorResponse(BaseModel):
    """錯誤回應模型"""
    error: bool = Field(default=True, description="是否為錯誤")
    error_code: str = Field(..., description="錯誤代碼")
    error_message: str = Field(..., description="錯誤訊息")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat(), description="錯誤時間")
    user_id: Optional[str] = Field(default=None, description="用戶ID")

# ==================== 工具函數 ====================

def create_text_response(text: str, user_id: str, success: bool = True, error_message: str = None) -> LineWebhookResponse:
    """建立文字回應"""
    return LineWebhookResponse(
        text=text,
        user_id=user_id,
        success=success,
        error_message=error_message
    )

def create_quick_reply_response(text: str, user_id: str, options: List[QuickReplyOption]) -> QuickReplyResponse:
    """建立快速回覆回應"""
    return QuickReplyResponse(
        text=text,
        user_id=user_id,
        quick_reply_options=options
    )

def create_error_response(error_code: str, error_message: str, user_id: str = None) -> ErrorResponse:
    """建立錯誤回應"""
    return ErrorResponse(
        error_code=error_code,
        error_message=error_message,
        user_id=user_id
    )