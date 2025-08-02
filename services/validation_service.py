#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
驗證服務 - 簡化版本
提供案件資料驗證功能
"""

from typing import Tuple, List
from models.case_model import CaseData
from datetime import datetime


class ValidationService:
    """案件資料驗證服務 - 簡化版本"""

    def __init__(self):
        """初始化驗證服務"""
        print("✅ ValidationService 初始化完成")

    def validate_case_data(self, case_data: CaseData) -> Tuple[bool, str]:
        """
        驗證案件資料

        Args:
            case_data: 案件資料

        Returns:
            (是否通過驗證, 錯誤訊息)
        """
        try:
            errors = []

            # 1. 基本必填欄位驗證
            if not case_data.client or case_data.client.strip() == "":
                errors.append("當事人姓名為必填欄位")

            if not case_data.case_type or case_data.case_type.strip() == "":
                errors.append("案件類型為必填欄位")

            # 2. 案件編號格式驗證（如果有提供）
            if case_data.case_id:
                if not self._validate_case_id_format(case_data.case_id):
                    errors.append("案件編號格式錯誤")

            # 3. 日期驗證
            try:
                if hasattr(case_data, 'creation_date') and case_data.creation_date:
                    if case_data.creation_date > datetime.now():
                        errors.append("建立日期不能是未來時間")
            except Exception:
                pass  # 忽略日期驗證錯誤

            # 4. 字串長度驗證
            if len(case_data.client) > 100:
                errors.append("當事人姓名過長")

            if case_data.case_type and len(case_data.case_type) > 50:
                errors.append("案件類型過長")

            # 返回驗證結果
            if errors:
                return False, "; ".join(errors)
            else:
                return True, "驗證通過"

        except Exception as e:
            # 如果驗證過程出錯，記錄錯誤但不阻止操作
            print(f"⚠️ 驗證過程發生錯誤: {e}")
            return True, "驗證過程有警告，但允許繼續"

    def _validate_case_id_format(self, case_id: str) -> bool:
        """驗證案件編號格式"""
        try:
            if not case_id or len(case_id) != 6:
                return False

            # 檢查是否都是數字
            if not case_id.isdigit():
                return False

            # 檢查年分範圍（民國100-200年）
            year_part = int(case_id[:3])
            if year_part < 100 or year_part > 200:
                return False

            # 檢查編號範圍（001-999）
            number_part = int(case_id[3:])
            if number_part < 1 or number_part > 999:
                return False

            return True

        except Exception:
            return False

    def validate_case_for_deletion(self, case_data: CaseData, force: bool = False) -> Tuple[bool, str]:
        """
        驗證案件是否可以刪除

        Args:
            case_data: 案件資料
            force: 是否強制刪除

        Returns:
            (是否可以刪除, 原因)
        """
        try:
            # 強制模式下總是允許刪除
            if force:
                return True, "強制刪除模式"

            # 檢查案件狀態 - 使用progress作為狀態
            status = getattr(case_data, 'progress', '待處理')

            # 一般情況下，只有特定狀態不能刪除
            if status in ['已結案', '已完成']:
                return False, f"案件狀態為「{status}」，建議不要刪除"

            return True, "可以刪除"

        except Exception as e:
            print(f"⚠️ 刪除驗證錯誤: {e}")
            return True, "驗證有錯誤，但允許刪除"

    def validate_required_fields(self, **fields) -> Tuple[bool, List[str]]:
        """
        驗證必填欄位

        Args:
            **fields: 欄位名稱和值的字典

        Returns:
            (是否通過, 錯誤訊息列表)
        """
        errors = []

        for field_name, field_value in fields.items():
            if not field_value or (isinstance(field_value, str) and field_value.strip() == ""):
                errors.append(f"{field_name}為必填欄位")

        return len(errors) == 0, errors