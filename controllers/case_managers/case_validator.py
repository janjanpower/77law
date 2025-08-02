#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
案件資料驗證管理器 - 修正版本
主要修改：移除 CASE_ID_PREFIXES 相關邏輯，改用民國年+流水號格式驗證
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from models.case_model import CaseData
from config.settings import AppConfig


class CaseValidator:
    """案件資料驗證管理器 - 修正版本"""

    def __init__(self, cases: List[CaseData]):
        """
        初始化驗證器

        Args:
            cases: 案件資料列表（引用）
        """
        self.cases = cases

    def check_case_id_duplicate(self, case_id: str, case_type: str, exclude_case_id: str = None) -> bool:
        """
        檢查案件編號重複 - 新增方法（如果不存在）

        Args:
            case_id: 要檢查的案件編號
            case_type: 案件類型
            exclude_case_id: 要排除的案件編號（用於更新時）

        Returns:
            bool: 是否重複
        """
        try:
            # 委託給驗證器處理
            if hasattr(self, 'validator') and self.validator:
                return self.validator.check_case_id_duplicate(case_id, case_type, exclude_case_id)

            # 備用方法：直接檢查
            all_cases = self.get_cases()
            for case in all_cases:
                if (case.case_id == case_id and
                    case.case_type == case_type and
                    case.case_id != exclude_case_id):
                    return True

            return False

        except Exception as e:
            print(f"❌ 檢查案件編號重複失敗: {e}")
            return False  # 發生錯誤時假設不重複，避免阻擋操作

    def validate_case_data(self, case_data: CaseData) -> Tuple[bool, List[str]]:
        """
        驗證案件資料的完整性

        Args:
            case_data: 要驗證的案件資料

        Returns:
            Tuple[bool, List[str]]: (是否通過驗證, 錯誤訊息列表)
        """
        errors = []

        # 必填欄位檢查
        if not case_data.case_id or not case_data.case_id.strip():
            errors.append("案件編號不能為空")

        if not case_data.case_type or not case_data.case_type.strip():
            errors.append("案件類型不能為空")

        if not case_data.client or not case_data.client.strip():
            errors.append("當事人不能為空")

        # 案件類型有效性檢查
        valid_case_types = list(AppConfig.CASE_TYPE_FOLDERS.keys())
        if case_data.case_type not in valid_case_types:
            errors.append(f"無效的案件類型: {case_data.case_type}")

        # 案件編號格式檢查（民國年+流水號格式）
        if case_data.case_id:
            if not self._validate_case_id_format(case_data.case_id):
                errors.append(f"案件編號格式不正確: {case_data.case_id}（應為民國年+流水號，例如：113001）")

        # 進度階段檢查
        if case_data.progress_stages:
            stage_errors = self._validate_progress_stages(case_data.progress_stages)
            errors.extend(stage_errors)

        # 日期格式檢查
        if case_data.progress_date:
            if not self._validate_date_format(case_data.progress_date):
                errors.append(f"進度日期格式不正確: {case_data.progress_date}")

        return len(errors) == 0, errors

    def _validate_case_id_format(self, case_id: str) -> bool:
        """
        驗證案件編號格式 - 修正版本：民國年+流水號格式

        格式：民國年份(3位) + 流水號(3位)
        例如：113001 (民國113年第1號案件)

        Args:
            case_id: 案件編號

        Returns:
            bool: 格式是否正確
        """
        try:
            # 檢查長度是否為6位
            if len(case_id) != 6:
                return False

            # 檢查是否全為數字
            if not case_id.isdigit():
                return False

            # 檢查民國年份是否合理（假設範圍：80-150年）
            roc_year = int(case_id[:3])
            if roc_year < 80 or roc_year > 150:
                return False

            # 檢查流水號是否為001-999
            serial_num = int(case_id[3:])
            if serial_num < 1 or serial_num > 999:
                return False

            return True

        except Exception as e:
            print(f"驗證案件編號格式失敗: {e}")
            return False

    def _validate_progress_stages(self, progress_stages: Dict[str, str]) -> List[str]:
        """
        驗證進度階段

        Args:
            progress_stages: 進度階段字典

        Returns:
            List[str]: 錯誤訊息列表
        """
        errors = []

        try:
            for stage_name, stage_date in progress_stages.items():
                # 檢查階段名稱
                if not stage_name or not stage_name.strip():
                    errors.append("進度階段名稱不能為空")
                    continue

                # 檢查日期格式
                if stage_date and not self._validate_date_format(stage_date):
                    errors.append(f"階段「{stage_name}」的日期格式不正確: {stage_date}")

        except Exception as e:
            errors.append(f"驗證進度階段失敗: {str(e)}")

        return errors

    def _validate_date_format(self, date_str: str) -> bool:
        """
        驗證日期格式

        Args:
            date_str: 日期字串

        Returns:
            bool: 格式是否正確
        """
        if not date_str or not date_str.strip():
            return True  # 空日期視為有效

        # 支援的日期格式
        date_patterns = [
            r'^\d{4}-\d{2}-\d{2}$',  # YYYY-MM-DD
            r'^\d{4}/\d{2}/\d{2}$',  # YYYY/MM/DD
            r'^\d{4}\.\d{2}\.\d{2}$',  # YYYY.MM.DD
            r'^\d{2}-\d{2}-\d{2}$',  # YY-MM-DD
            r'^\d{2}/\d{2}/\d{2}$',  # YY/MM/DD
        ]

        for pattern in date_patterns:
            if re.match(pattern, date_str.strip()):
                return True

        return False


    def validate_case_id_update(self, old_case_id: str, case_type: str, new_case_id: str) -> Tuple[bool, str]:
        """
        驗證案件編號更新 - CaseValidator的職責

        Args:
            old_case_id: 原案件編號
            case_type: 案件類型
            new_case_id: 新案件編號

        Returns:
            Tuple[bool, str]: (是否有效, 錯誤訊息)
        """
        try:
            print(f"🔍 CaseValidator 驗證案件編號更新: {old_case_id} → {new_case_id}")

            # 1. 驗證新案件編號格式
            if not self._validate_case_id_format(new_case_id):
                return False, f"新案件編號格式無效: {new_case_id}"

            # 2. 檢查新案件編號是否重複
            if self.check_case_id_duplicate(new_case_id, case_type, exclude_case_id=old_case_id):
                return False, f"案件編號 {new_case_id} 已存在"

            # 3. 驗證原案件是否存在
            if not self._case_exists(old_case_id, case_type):
                return False, f"原案件編號不存在: {old_case_id}"

            # 4. 檢查案件編號是否確實有變更
            if old_case_id == new_case_id:
                return False, "新舊案件編號相同，無需更新"

            # 5. 其他業務規則驗證
            business_validation = self._validate_case_id_update_business_rules(old_case_id, new_case_id, case_type)
            if not business_validation[0]:
                return business_validation

            print(f"✅ 案件編號更新驗證通過")
            return True, "驗證通過"

        except Exception as e:
            print(f"❌ CaseValidator 驗證失敗: {e}")
            return False, f"驗證過程發生錯誤: {str(e)}"

    def _validate_case_id_update_business_rules(self, old_case_id: str, new_case_id: str, case_type: str) -> Tuple[bool, str]:
        """驗證案件編號更新的業務規則"""
        try:
            # 可以在這裡添加更多業務規則
            # 例如：某些案件編號不允許更改、需要特定權限等

            return True, ""

        except Exception as e:
            return False, f"業務規則驗證失敗: {str(e)}"

    def _case_exists(self, case_id: str, case_type: str) -> bool:
        """檢查案件是否存在"""
        try:
            for case in self.cases:
                if case.case_id == case_id and case.case_type == case_type:
                    return True
            return False
        except Exception as e:
            print(f"❌ 檢查案件存在性失敗: {e}")
            return False