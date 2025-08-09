# utils/data_cleaner.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
資料清理工具 - 處理匯入資料的清理需求
統一處理換行符號移除和其他資料清理功能
"""
import re
from typing import Any, Optional


class DataCleaner:
    """統一的資料清理工具"""

    @staticmethod
    def clean_text_data(value: Any) -> Optional[str]:
        """
        清理文字資料，包含移除換行符號

        Args:
            value: 原始資料值

        Returns:
            清理後的字串，如果原始值為空則返回None
        """
        if value is None:
            return None

        # 轉換為字串
        text = str(value).strip()

        # 檢查是否為空值
        if not text or text.lower() in ['nan', 'none', '', 'null']:
            return None

        # 移除各種換行符號
        # \r\n (Windows), \n (Unix/Linux), \r (舊Mac系統)
        text = text.replace('\r\n', ' ')  # Windows換行
        text = text.replace('\n', ' ')    # Unix/Linux換行
        text = text.replace('\r', ' ')    # 舊Mac換行

        # 移除過多的空格（將多個連續空格合並為一個）
        text = re.sub(r'\s+', ' ', text)

        # 最終清理
        text = text.strip()

        return text if text else None

    @staticmethod
    def clean_case_data_fields(case_data_dict: dict) -> dict:
        """
        清理案件資料字典中的所有文字欄位

        Args:
            case_data_dict: 包含案件資料的字典

        Returns:
            清理後的案件資料字典
        """
        # 需要清理的文字欄位
        text_fields = [
            'case_id', 'client', 'case_reason', 'case_number',
            'lawyer', 'legal_affairs', 'opposing_party',
            'court', 'division', 'progress'
        ]

        cleaned_data = case_data_dict.copy()

        for field in text_fields:
            if field in cleaned_data:
                cleaned_data[field] = DataCleaner.clean_text_data(cleaned_data[field])

        return cleaned_data