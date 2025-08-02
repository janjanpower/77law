#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
簡化驗證服務 - 備用版本
只進行基本驗證，確保系統穩定運行
"""

from typing import Tuple


class SimpleValidationService:
    """簡化驗證服務 - 只做基本檢查"""

    def __init__(self):
        print("✅ SimpleValidationService 初始化完成")

    def validate_case_data(self, case_data, strict_mode: bool = False) -> Tuple[bool, str]:
        """
        簡化的案件資料驗證

        Args:
            case_data: 要驗證的案件資料
            strict_mode: 嚴格模式（暫時忽略）

        Returns:
            (驗證是否通過, 錯誤訊息或成功訊息)
        """
        try:
            # 基本檢查
            if case_data is None:
                return False, "案件資料不能為None"

            if isinstance(case_data, str):
                return False, "案件資料不能是字串"

            # 檢查基本屬性
            if not hasattr(case_data, 'client'):
                return False, "案件資料缺少當事人欄位"

            if not hasattr(case_data, 'case_type'):
                return False, "案件資料缺少案件類型欄位"

            # 檢查必填欄位值
            client = getattr(case_data, 'client', '')
            if not client or str(client).strip() == "":
                return False, "當事人姓名不能為空"

            case_type = getattr(case_data, 'case_type', '')
            if not case_type or str(case_type).strip() == "":
                return False, "案件類型不能為空"

            return True, "基本驗證通過"

        except Exception as e:
            return False, f"驗證過程發生錯誤: {str(e)}"

    def validate_case_type(self, case_type: str) -> Tuple[bool, str]:
        """驗證案件類型"""
        if not case_type or str(case_type).strip() == "":
            return False, "案件類型不能為空"
        return True, "案件類型有效"

    def validate_client_name_for_folder(self, client_name: str) -> Tuple[bool, str]:
        """驗證當事人姓名是否適合作為資料夾名稱"""
        if not client_name or str(client_name).strip() == "":
            return False, "當事人姓名不能為空"

        # 簡單的禁用字元檢查
        forbidden_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
        for char in forbidden_chars:
            if char in client_name:
                return False, f"當事人姓名包含禁用字元: {char}"

        return True, "當事人姓名有效"


# 創建全域實例
_simple_validation_service = None

def get_simple_validation_service():
    """取得簡化驗證服務實例"""
    global _simple_validation_service
    if _simple_validation_service is None:
        _simple_validation_service = SimpleValidationService()
    return _simple_validation_service