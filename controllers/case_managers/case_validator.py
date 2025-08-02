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
        檢查案件編號是否重複

        Args:
            case_id: 要檢查的案件編號
            case_type: 案件類型
            exclude_case_id: 排除的案件編號（用於更新時）

        Returns:
            bool: True表示重複，False表示不重複
        """
        for case in self.cases:
            if (case.case_id == case_id and
                case.case_type == case_type and
                case.case_id != exclude_case_id):
                return True
        return False

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

    def validate_client_name(self, client_name: str) -> Tuple[bool, str]:
        """
        驗證當事人姓名

        Args:
            client_name: 當事人姓名

        Returns:
            Tuple[bool, str]: (是否有效, 錯誤訊息)
        """
        if not client_name or not client_name.strip():
            return False, "當事人姓名不能為空"

        # 檢查長度
        if len(client_name.strip()) > 50:
            return False, "當事人姓名過長（最多50字元）"

        # 檢查特殊字元
        invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
        for char in invalid_chars:
            if char in client_name:
                return False, f"當事人姓名不能包含特殊字元：{char}"

        return True, ""

    def validate_case_type(self, case_type: str) -> bool:
        """
        驗證案件類型

        Args:
            case_type: 案件類型

        Returns:
            bool: 是否有效
        """
        return case_type in AppConfig.CASE_TYPE_FOLDERS

    def validate_progress(self, progress: str, case_type: str) -> bool:
        """
        驗證進度狀態

        Args:
            progress: 進度狀態
            case_type: 案件類型

        Returns:
            bool: 是否有效
        """
        valid_progress = AppConfig.get_progress_options(case_type)
        if not valid_progress:
            valid_progress = AppConfig.PROGRESS_OPTIONS.get('default', [])

        return progress in valid_progress

    def get_validation_summary(self, cases: List[CaseData] = None) -> Dict[str, Any]:
        """
        取得驗證摘要

        Args:
            cases: 要驗證的案件列表，None表示使用所有案件

        Returns:
            Dict[str, Any]: 驗證摘要
        """
        if cases is None:
            cases = self.cases

        summary = {
            'total_cases': len(cases),
            'valid_cases': 0,
            'invalid_cases': 0,
            'common_errors': {},
            'duplicate_ids': []
        }

        # 檢查重複編號
        case_ids = {}
        for case in cases:
            key = f"{case.case_id}_{case.case_type}"
            if key in case_ids:
                summary['duplicate_ids'].append(case.case_id)
            else:
                case_ids[key] = case

        # 驗證每個案件
        for case in cases:
            is_valid, errors = self.validate_case_data(case)

            if is_valid:
                summary['valid_cases'] += 1
            else:
                summary['invalid_cases'] += 1

                # 統計常見錯誤
                for error in errors:
                    if error not in summary['common_errors']:
                        summary['common_errors'][error] = 0
                    summary['common_errors'][error] += 1

        return summary

    def fix_case_id_format(self, case: CaseData) -> Tuple[bool, str]:
        """
        修正案件編號格式

        Args:
            case: 案件資料

        Returns:
            Tuple[bool, str]: (是否修正成功, 新的案件編號或錯誤訊息)
        """
        try:
            from datetime import datetime

            # 如果已經是正確格式，直接返回
            if self._validate_case_id_format(case.case_id):
                return True, case.case_id

            # 嘗試修正格式
            current_year = datetime.now().year
            roc_year = current_year - 1911

            # 取得同類型案件的最大流水號
            same_type_cases = [
                c for c in self.cases
                if c.case_type == case.case_type and
                c.case_id != case.case_id and
                self._validate_case_id_format(c.case_id)
            ]

            max_num = 0
            for existing_case in same_type_cases:
                if existing_case.case_id.startswith(str(roc_year)):
                    try:
                        num_part = existing_case.case_id[3:]
                        if num_part.isdigit():
                            num = int(num_part)
                            max_num = max(max_num, num)
                    except (ValueError, IndexError):
                        continue

            # 生成新編號
            new_num = max_num + 1
            new_case_id = f"{roc_year:03d}{new_num:03d}"

            return True, new_case_id

        except Exception as e:
            return False, f"修正案件編號失敗: {str(e)}"