#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
驗證業務邏輯服務 - 修正案件ID驗證規則
專責處理各種資料驗證的業務邏輯，增強屬性檢查
"""

from typing import List, Optional, Dict, Any, Tuple
import re
from datetime import datetime
import os


class ValidationService:
    """驗證業務邏輯服務 - 修正版本"""

    def __init__(self):
        """初始化驗證服務"""
        # 修正後的驗證規則配置
        self.validation_rules = {
            'client_name': {
                'max_length': 50,
                'min_length': 1,
                'forbidden_chars': ['<', '>', ':', '"', '/', '\\', '|', '?', '*'],
                'required': True
            },
            'case_id': {
                'length': 6,  # 修正：固定6位數字
                'pattern': r'^\d{6}$',  # 修正：6位純數字格式
                'required': False  # 可以自動生成
            },
            'case_type': {
                'allowed_values': ['民事', '刑事', '行政訴訟', '商事糾紛', '家事案件', '其他'],  # 修正：簡化類型
                'required': True
            },
            'status': {
                'allowed_values': ['待處理', '進行中', '已完成', '已結案', '暫停'],
                'required': False  # 有預設值
            }
        }

        print("✅ ValidationService 初始化完成 (已修正案件ID驗證規則)")

    # ==================== 安全屬性檢查 ====================

    def _safe_getattr(self, obj, attr_name, default=None):
        """安全地取得物件屬性"""
        try:
            return getattr(obj, attr_name, default)
        except Exception:
            return default

    def _has_attr(self, obj, attr_name):
        """安全地檢查物件是否有指定屬性"""
        try:
            return hasattr(obj, attr_name)
        except Exception:
            return False

    # ==================== 案件資料驗證 ====================

    def validate_case_data(self, case_data, strict_mode: bool = False) -> Tuple[bool, str]:
        """
        驗證案件資料的完整性和正確性（修復版本）

        Args:
            case_data: 要驗證的案件資料
            strict_mode: 嚴格模式（更嚴格的驗證規則）

        Returns:
            (驗證是否通過, 錯誤訊息或成功訊息)
        """
        try:
            validation_errors = []

            # 0. 基本物件檢查
            if case_data is None:
                return False, "案件資料不能為None"

            # 檢查是否為字串（常見錯誤）
            if isinstance(case_data, str):
                return False, "案件資料不能是字串"

            # 1. 基本必填欄位驗證
            basic_validation = self._validate_basic_fields(case_data)
            if basic_validation:
                validation_errors.extend(basic_validation)

            # 2. 當事人姓名驗證
            client = self._safe_getattr(case_data, 'client', '')
            client_validation = self._validate_client_name(client)
            if client_validation:
                validation_errors.extend(client_validation)

            # 3. 案件ID驗證（如果有提供）
            case_id = self._safe_getattr(case_data, 'case_id', '')
            if case_id:
                case_id_validation = self._validate_case_id(case_id)
                if case_id_validation:
                    validation_errors.extend(case_id_validation)

            # 4. 案件類型驗證
            case_type = self._safe_getattr(case_data, 'case_type', '')
            case_type_validation = self._validate_case_type(case_type)
            if not case_type_validation[0]:
                validation_errors.append(case_type_validation[1])

            # 5. 狀態驗證
            status = self._safe_getattr(case_data, 'status', '')
            status_validation = self._validate_status(status)
            if not status_validation[0]:
                validation_errors.append(status_validation[1])

            # 6. 日期驗證（安全檢查）
            creation_date = self._safe_getattr(case_data, 'creation_date')
            if creation_date:
                date_validation = self._validate_date(creation_date, "建立日期")
                if date_validation:
                    validation_errors.extend(date_validation)

            # 7. 重要日期驗證（安全檢查）
            important_dates = self._safe_getattr(case_data, 'important_dates', [])
            if important_dates:
                important_dates_validation = self._validate_important_dates(important_dates)
                if important_dates_validation:
                    validation_errors.extend(important_dates_validation)

            # 8. 嚴格模式額外驗證
            if strict_mode:
                strict_validation = self._strict_mode_validation(case_data)
                if strict_validation:
                    validation_errors.extend(strict_validation)

            if validation_errors:
                error_message = "; ".join(validation_errors)
                return False, f"資料驗證失敗: {error_message}"
            else:
                return True, "資料驗證通過"

        except Exception as e:
            return False, f"驗證過程發生錯誤: {str(e)}"

    # ==================== 私有驗證方法 ====================

    def _validate_basic_fields(self, case_data) -> List[str]:
        """驗證基本必填欄位"""
        errors = []

        # 檢查必填欄位
        client = self._safe_getattr(case_data, 'client', '')
        if not client or str(client).strip() == "":
            errors.append("當事人姓名為必填欄位")

        case_type = self._safe_getattr(case_data, 'case_type', '')
        if not case_type or str(case_type).strip() == "":
            errors.append("案件類型為必填欄位")

        return errors

    def _validate_client_name(self, client_name: str) -> List[str]:
        """驗證當事人姓名"""
        errors = []

        if not client_name:
            return errors  # 基本驗證已處理

        # 長度檢查
        if len(client_name) > self.validation_rules['client_name']['max_length']:
            errors.append(f"當事人姓名過長（最多{self.validation_rules['client_name']['max_length']}字元）")

        if len(client_name.strip()) < self.validation_rules['client_name']['min_length']:
            errors.append("當事人姓名過短")

        # 禁用字元檢查
        forbidden_chars = self.validation_rules['client_name']['forbidden_chars']
        for char in forbidden_chars:
            if char in client_name:
                errors.append(f"當事人姓名包含禁用字元: {char}")

        return errors

    def _validate_case_id(self, case_id: str) -> List[str]:
        """驗證案件ID - 修正為6位數字格式"""
        errors = []

        if not case_id:
            return errors

        # 修正：長度檢查 - 必須是6位數字
        if len(case_id) != self.validation_rules['case_id']['length']:
            errors.append(f"案件ID長度錯誤（必須是{self.validation_rules['case_id']['length']}位數字）")
            return errors

        # 修正：格式檢查 - 必須是純數字
        pattern = self.validation_rules['case_id']['pattern']
        if not re.match(pattern, case_id):
            errors.append("案件ID格式不正確（必須是6位純數字，格式：民國年3碼+流水號3碼，例如：114001）")
            return errors

        # 修正：加入民國年範圍檢查
        try:
            year_part = int(case_id[:3])  # 前3碼：民國年
            number_part = int(case_id[3:])  # 後3碼：流水號

            # 民國年範圍檢查
            if year_part < 100 or year_part > 200:
                errors.append("案件ID年份範圍錯誤（民國年應在100-200年之間）")

            # 流水號範圍檢查
            if number_part < 1 or number_part > 999:
                errors.append("案件ID流水號範圍錯誤（流水號應在001-999之間）")

        except ValueError:
            errors.append("案件ID格式錯誤（無法解析年份和流水號）")

        return errors

    def _validate_case_type(self, case_type: str) -> Tuple[bool, str]:
        """驗證案件類型"""
        if not case_type:
            return False, "案件類型不能為空"

        allowed_values = self.validation_rules['case_type']['allowed_values']
        if allowed_values and case_type not in allowed_values:
            return False, f"案件類型無效，允許的類型: {', '.join(allowed_values)}"

        return True, "案件類型有效"

    def _validate_status(self, status: str) -> Tuple[bool, str]:
        """驗證案件狀態"""
        if not status:
            return True, "狀態為空，將使用預設值"  # 有預設值，所以允許為空

        allowed_values = self.validation_rules['status']['allowed_values']
        if status not in allowed_values:
            return False, f"案件狀態無效，允許的狀態: {', '.join(allowed_values)}"

        return True, "案件狀態有效"

    def _validate_date(self, date_value, field_name: str) -> List[str]:
        """驗證日期格式"""
        errors = []

        try:
            if isinstance(date_value, str):
                # 嘗試解析字串日期
                datetime.strptime(date_value, '%Y-%m-%d')
            elif not isinstance(date_value, datetime):
                errors.append(f"{field_name}格式不正確")
        except ValueError:
            errors.append(f"{field_name}格式不正確（應為YYYY-MM-DD格式）")
        except Exception as e:
            errors.append(f"{field_name}驗證失敗: {str(e)}")

        return errors

    def _validate_important_dates(self, important_dates) -> List[str]:
        """驗證重要日期列表"""
        errors = []

        try:
            if not isinstance(important_dates, list):
                errors.append("重要日期應為列表格式")
                return errors

            for i, date_item in enumerate(important_dates):
                if not isinstance(date_item, dict):
                    errors.append(f"重要日期{i+1}格式不正確（應為字典格式）")
                    continue

                if 'date' not in date_item:
                    errors.append(f"重要日期{i+1}缺少日期欄位")

                if 'description' not in date_item or not date_item['description']:
                    errors.append(f"重要日期{i+1}缺少描述")
        except Exception as e:
            errors.append(f"重要日期格式錯誤: {str(e)}")

        return errors

    def _strict_mode_validation(self, case_data) -> List[str]:
        """嚴格模式驗證"""
        errors = []

        # 嚴格模式要求更多欄位
        case_id = self._safe_getattr(case_data, 'case_id', '')
        if not case_id or str(case_id).strip() == "":
            errors.append("嚴格模式要求提供案件ID")

        status = self._safe_getattr(case_data, 'status', '')
        if not status or str(status).strip() == "":
            errors.append("嚴格模式要求提供案件狀態")

        creation_date = self._safe_getattr(case_data, 'creation_date')
        if not creation_date:
            errors.append("嚴格模式要求提供建立日期")

        # 檢查備註長度
        notes = self._safe_getattr(case_data, 'notes', '')
        if notes and len(str(notes)) > 1000:
            errors.append("備註內容過長（嚴格模式限制1000字元）")

        return errors

    # ==================== 其他驗證方法 ====================

    def validate_case_type(self, case_type: str) -> Tuple[bool, str]:
        """
        驗證案件類型

        Args:
            case_type: 案件類型

        Returns:
            (是否有效, 訊息)
        """
        return self._validate_case_type(case_type)

    def validate_client_name_for_folder(self, client_name: str) -> Tuple[bool, str]:
        """
        驗證當事人姓名是否適合作為資料夾名稱

        Args:
            client_name: 當事人姓名

        Returns:
            (是否有效, 訊息)
        """
        if not client_name or str(client_name).strip() == "":
            return False, "當事人姓名不能為空"

        # 檢查長度
        if len(client_name) > 50:
            return False, "當事人姓名過長（最多50字元）"

        # 檢查禁用字元
        forbidden_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
        for char in forbidden_chars:
            if char in client_name:
                return False, f"當事人姓名包含資料夾禁用字元: {char}"

        return True, "當事人姓名適合作為資料夾名稱"

    def validate_multiple_cases(self, cases_data, cross_validation: bool = False) -> Dict[str, Any]:
        """
        批次驗證多個案件資料

        Args:
            cases_data: 案件資料列表
            cross_validation: 是否進行交叉驗證（檢查重複等）

        Returns:
            驗證結果摘要
        """
        validation_summary = {
            'total_cases': len(cases_data),
            'valid_cases': 0,
            'invalid_cases': 0,
            'warnings': [],
            'errors': [],
            'case_results': []
        }

        for i, case_data in enumerate(cases_data):
            try:
                is_valid, message = self.validate_case_data(case_data)

                case_result = {
                    'index': i,
                    'valid': is_valid,
                    'message': message,
                    'case_id': self._safe_getattr(case_data, 'case_id', f'未知_{i}'),
                    'client': self._safe_getattr(case_data, 'client', f'未知當事人_{i}')
                }

                if is_valid:
                    validation_summary['valid_cases'] += 1
                else:
                    validation_summary['invalid_cases'] += 1
                    validation_summary['errors'].append(f"案件{i+1}: {message}")

                validation_summary['case_results'].append(case_result)

            except Exception as e:
                validation_summary['invalid_cases'] += 1
                validation_summary['errors'].append(f"案件{i+1}驗證時發生錯誤: {str(e)}")

        # 交叉驗證
        if cross_validation and validation_summary['valid_cases'] > 1:
            cross_validation_errors = self._cross_validate_cases(cases_data)
            validation_summary['errors'].extend(cross_validation_errors)

        return validation_summary

    def _cross_validate_cases(self, cases_data) -> List[str]:
        """交叉驗證案件資料"""
        errors = []

        # 檢查重複的案件ID
        case_ids = []
        for i, case_data in enumerate(cases_data):
            case_id = self._safe_getattr(case_data, 'case_id', '')
            if case_id:
                if case_id in case_ids:
                    errors.append(f"重複的案件ID: {case_id}")
                else:
                    case_ids.append(case_id)

        return errors

    # ==================== 新增：案件ID生成輔助方法 ====================

    def validate_case_id_format(self, case_id: str) -> bool:
        """
        驗證案件編號格式（與CaseController兼容）

        Args:
            case_id: 案件ID

        Returns:
            bool: 格式是否正確
        """
        if not case_id or len(case_id) != 6:
            return False

        try:
            # 檢查前三碼是否為數字（民國年分）
            year_part = int(case_id[:3])
            # 檢查後三碼是否為數字（流水號）
            number_part = int(case_id[3:])

            # 基本範圍檢查
            if year_part < 100 or year_part > 200:  # 民國100-200年合理範圍
                return False
            if number_part < 1 or number_part > 999:
                return False

            return True
        except ValueError:
            return False