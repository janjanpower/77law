#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
驗證服務 - 服務層
統一所有驗證相關的業務邏輯
整合現有的各種驗證功能
"""

import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from models.case_model import CaseData
from config.settings import AppConfig


class ValidationService:
    """驗證服務 - 統一驗證業務邏輯"""

    def __init__(self):
        """初始化驗證服務"""
        # 不安全字符列表
        self.unsafe_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']

        # 必填欄位列表
        self.required_fields = ['client', 'case_type']

        # 案件類型驗證
        self.valid_case_types = AppConfig.CASE_TYPES

    # ====== 案件資料驗證 ======

    def validate_case_data(self, case_data: CaseData) -> Tuple[bool, List[str]]:
        """
        驗證案件資料完整性

        Args:
            case_data: 案件資料

        Returns:
            (is_valid, error_messages)
        """
        errors = []

        try:
            # 基本存在性檢查
            if not case_data:
                errors.append("案件資料不能為空")
                return False, errors

            # 必填欄位驗證
            missing_fields = self._validate_required_fields(case_data)
            errors.extend(missing_fields)

            # 欄位格式驗證
            format_errors = self._validate_field_formats(case_data)
            errors.extend(format_errors)

            # 業務邏輯驗證
            business_errors = self._validate_business_rules(case_data)
            errors.extend(business_errors)

            is_valid = len(errors) == 0
            return is_valid, errors

        except Exception as e:
            errors.append(f"驗證過程發生錯誤: {str(e)}")
            return False, errors

    def _validate_required_fields(self, case_data: CaseData) -> List[str]:
        """驗證必填欄位"""
        errors = []

        # 當事人不能為空
        if not case_data.client or not case_data.client.strip():
            errors.append("當事人不能為空")

        # 案件類型必須有效
        if not case_data.case_type or case_data.case_type not in self.valid_case_types:
            errors.append(f"案件類型必須是以下之一: {', '.join(self.valid_case_types)}")

        return errors

    def _validate_field_formats(self, case_data: CaseData) -> List[str]:
        """驗證欄位格式"""
        errors = []

        # 當事人名稱長度檢查
        if case_data.client and len(case_data.client) > 50:
            errors.append("當事人名稱不能超過50個字符")

        # 案由長度檢查
        if case_data.case_reason and len(case_data.case_reason) > 100:
            errors.append("案由不能超過100個字符")

        # 案號格式檢查
        if case_data.case_number:
            if not self._validate_case_number_format(case_data.case_number):
                errors.append("案號格式不正確")

        # 檢查不安全字符
        unsafe_fields = self._check_unsafe_characters(case_data)
        if unsafe_fields:
            errors.append(f"以下欄位包含不安全字符: {', '.join(unsafe_fields)}")

        return errors

    def _validate_business_rules(self, case_data: CaseData) -> List[str]:
        """驗證業務規則"""
        errors = []

        # 進度狀態驗證
        if case_data.progress:
            valid_progress = AppConfig.get_progress_options(case_data.case_type)
            if valid_progress and case_data.progress not in valid_progress:
                errors.append(f"進度狀態 '{case_data.progress}' 對於 {case_data.case_type} 案件不有效")

        # 日期邏輯驗證
        if case_data.progress_date and case_data.created_date:
            if case_data.progress_date < case_data.created_date:
                errors.append("進度日期不能早於建立日期")

        return errors

    def _validate_case_number_format(self, case_number: str) -> bool:
        """驗證案號格式"""
        if not case_number:
            return True  # 可以為空

        # 基本格式檢查：不能包含特殊字符
        for char in self.unsafe_chars:
            if char in case_number:
                return False

        # 長度檢查
        if len(case_number) > 30:
            return False

        return True

    def _check_unsafe_characters(self, case_data: CaseData) -> List[str]:
        """檢查不安全字符"""
        unsafe_fields = []

        fields_to_check = {
            'client': case_data.client,
            'case_reason': case_data.case_reason,
            'case_number': case_data.case_number,
            'court': case_data.court,
            'lawyer': case_data.lawyer,
            'legal_affairs': case_data.legal_affairs,
            'opposing_party': case_data.opposing_party,
            'division': case_data.division
        }

        for field_name, field_value in fields_to_check.items():
            if field_value and any(char in field_value for char in self.unsafe_chars):
                unsafe_fields.append(field_name)

        return unsafe_fields

    # ====== 檔案名稱驗證 ======

    def validate_folder_name(self, name: str) -> Tuple[bool, str]:
        """
        驗證資料夾名稱

        Args:
            name: 資料夾名稱

        Returns:
            (is_valid, error_message_or_safe_name)
        """
        try:
            if not name or not name.strip():
                return False, "資料夾名稱不能為空"

            # 清理名稱
            safe_name = self.sanitize_folder_name(name)

            if not safe_name or safe_name == "未知":
                return False, "資料夾名稱包含過多不安全字符"

            return True, safe_name

        except Exception as e:
            return False, f"驗證資料夾名稱時發生錯誤: {str(e)}"

    def sanitize_folder_name(self, name: str) -> str:
        """
        清理資料夾名稱

        Args:
            name: 原始名稱

        Returns:
            清理後的安全名稱
        """
        if not name:
            return "未知"

        # 移除或替換不安全字符
        safe_name = name.strip()

        for char in self.unsafe_chars:
            safe_name = safe_name.replace(char, '_')

        # 移除多餘空白和點號
        safe_name = ' '.join(safe_name.split())
        safe_name = safe_name.strip('.')

        # 限制長度
        if len(safe_name) > 50:
            safe_name = safe_name[:50]

        # 確保不為空
        return safe_name if safe_name else "未知"

    def validate_file_name(self, filename: str) -> Tuple[bool, str]:
        """
        驗證檔案名稱

        Args:
            filename: 檔案名稱

        Returns:
            (is_valid, error_message_or_safe_name)
        """
        try:
            if not filename or not filename.strip():
                return False, "檔案名稱不能為空"

            # 分離檔名和副檔名
            name_part, ext_part = os.path.splitext(filename)

            # 驗證檔名部分
            if not name_part:
                return False, "檔案名稱不能只有副檔名"

            # 清理檔名
            safe_name = self.sanitize_folder_name(name_part)

            if not safe_name or safe_name == "未知":
                return False, "檔案名稱包含過多不安全字符"

            # 重組檔案名稱
            safe_filename = safe_name + ext_part

            return True, safe_filename

        except Exception as e:
            return False, f"驗證檔案名稱時發生錯誤: {str(e)}"

    # ====== 檔案路徑驗證 ======

    def validate_file_path(self, file_path: str) -> Tuple[bool, str]:
        """
        驗證檔案路徑

        Args:
            file_path: 檔案路徑

        Returns:
            (is_valid, error_message)
        """
        try:
            if not file_path or not file_path.strip():
                return False, "檔案路徑不能為空"

            # 檢查路徑是否存在
            if not os.path.exists(file_path):
                return False, f"檔案路徑不存在: {file_path}"

            # 檢查是否為檔案
            if not os.path.isfile(file_path):
                return False, f"路徑不是檔案: {file_path}"

            # 檢查檔案大小（限制100MB）
            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
            if file_size_mb > 100:
                return False, f"檔案過大: {file_size_mb:.2f}MB，限制100MB"

            return True, "檔案路徑驗證通過"

        except Exception as e:
            return False, f"驗證檔案路徑時發生錯誤: {str(e)}"

    def validate_folder_path(self, folder_path: str) -> Tuple[bool, str]:
        """
        驗證資料夾路徑

        Args:
            folder_path: 資料夾路徑

        Returns:
            (is_valid, error_message)
        """
        try:
            if not folder_path or not folder_path.strip():
                return False, "資料夾路徑不能為空"

            # 檢查路徑是否存在
            if not os.path.exists(folder_path):
                return False, f"資料夾路徑不存在: {folder_path}"

            # 檢查是否為資料夾
            if not os.path.isdir(folder_path):
                return False, f"路徑不是資料夾: {folder_path}"

            # 檢查讀寫權限
            if not os.access(folder_path, os.R_OK | os.W_OK):
                return False, f"資料夾沒有讀寫權限: {folder_path}"

            return True, "資料夾路徑驗證通過"

        except Exception as e:
            return False, f"驗證資料夾路徑時發生錯誤: {str(e)}"

    # ====== Excel檔案驗證 ======

    def validate_excel_file(self, file_path: str) -> Tuple[bool, str]:
        """
        驗證Excel檔案

        Args:
            file_path: Excel檔案路徑

        Returns:
            (is_valid, error_message)
        """
        try:
            # 基本檔案驗證
            is_valid, message = self.validate_file_path(file_path)
            if not is_valid:
                return False, message

            # 檢查檔案副檔名
            if not file_path.lower().endswith(('.xlsx', '.xls')):
                return False, "不是有效的Excel檔案格式（.xlsx 或 .xls）"

            # 檢查檔案大小（Excel限制50MB）
            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
            if file_size_mb > 50:
                return False, f"Excel檔案過大: {file_size_mb:.2f}MB，限制50MB"

            return True, "Excel檔案驗證通過"

        except Exception as e:
            return False, f"驗證Excel檔案時發生錯誤: {str(e)}"

    # ====== 資料格式驗證 ======

    def validate_date_format(self, date_str: str) -> Tuple[bool, str]:
        """
        驗證日期格式

        Args:
            date_str: 日期字串

        Returns:
            (is_valid, error_message_or_formatted_date)
        """
        try:
            if not date_str or not date_str.strip():
                return True, ""  # 空值允許

            # 嘗試多種日期格式
            date_formats = [
                '%Y-%m-%d',
                '%Y/%m/%d',
                '%Y.%m.%d',
                '%m/%d/%Y',
                '%m-%d-%Y',
                '%d/%m/%Y',
                '%d-%m-%Y'
            ]

            for fmt in date_formats:
                try:
                    parsed_date = datetime.strptime(date_str.strip(), fmt)
                    # 返回統一格式
                    return True, parsed_date.strftime('%Y-%m-%d')
                except ValueError:
                    continue

            return False, f"日期格式不正確: {date_str}，支援格式: YYYY-MM-DD, YYYY/MM/DD 等"

        except Exception as e:
            return False, f"驗證日期格式時發生錯誤: {str(e)}"


    # ====== 批次驗證 ======

    def batch_validate_cases(self, cases: List[CaseData]) -> Dict[str, Any]:
        """
        批次驗證案件資料

        Args:
            cases: 案件資料列表

        Returns:
            批次驗證結果
        """
        result = {
            'total': len(cases),
            'valid': 0,
            'invalid': 0,
            'errors': {},
            'warnings': []
        }

        for i, case_data in enumerate(cases):
            try:
                is_valid, errors = self.validate_case_data(case_data)

                if is_valid:
                    result['valid'] += 1
                else:
                    result['invalid'] += 1
                    result['errors'][f"第{i+1}筆"] = errors

            except Exception as e:
                result['invalid'] += 1
                result['errors'][f"第{i+1}筆"] = [f"驗證過程發生錯誤: {str(e)}"]

        # 產生警告
        if result['invalid'] > 0:
            result['warnings'].append(f"發現 {result['invalid']} 筆無效資料")

        return result

    # ====== 資料夾結構驗證 ======

    def validate_case_folder_structure(self, folder_path: str) -> Dict[str, Any]:
        """
        驗證案件資料夾結構

        Args:
            folder_path: 案件資料夾路徑

        Returns:
            驗證結果
        """
        result = {
            'is_valid': True,
            'missing_folders': [],
            'extra_folders': [],
            'errors': [],
            'warnings': []
        }

        try:
            if not os.path.exists(folder_path):
                result['is_valid'] = False
                result['errors'].append(f"資料夾不存在: {folder_path}")
                return result

            # 必要的子資料夾
            required_subfolders = ['狀紙', '進度追蹤', '案件資訊']

            # 檢查必要子資料夾
            for subfolder in required_subfolders:
                subfolder_path = os.path.join(folder_path, subfolder)
                if not os.path.exists(subfolder_path):
                    result['missing_folders'].append(subfolder)
                    result['warnings'].append(f"缺少必要子資料夾: {subfolder}")

            # 檢查額外資料夾
            existing_folders = [f for f in os.listdir(folder_path)
                             if os.path.isdir(os.path.join(folder_path, f))]

            for folder in existing_folders:
                if folder not in required_subfolders:
                    result['extra_folders'].append(folder)

            # 設定驗證結果
            if result['missing_folders']:
                result['is_valid'] = False

        except Exception as e:
            result['is_valid'] = False
            result['errors'].append(f"驗證資料夾結構時發生錯誤: {str(e)}")

        return result

    # ====== 重複資料檢查 ======

    def check_duplicate_cases(self, cases: List[CaseData]) -> Dict[str, Any]:
        """
        檢查重複案件

        Args:
            cases: 案件資料列表

        Returns:
            重複檢查結果
        """
        result = {
            'has_duplicates': False,
            'duplicate_groups': [],
            'total_duplicates': 0
        }

        try:
            # 按當事人和案件類型分組
            groups = {}
            for i, case in enumerate(cases):
                key = (case.client.strip().lower(), case.case_type)
                if key not in groups:
                    groups[key] = []
                groups[key].append((i, case))

            # 找出重複組
            for key, group in groups.items():
                if len(group) > 1:
                    result['has_duplicates'] = True
                    result['duplicate_groups'].append({
                        'client': group[0][1].client,
                        'case_type': group[0][1].case_type,
                        'indices': [i for i, _ in group],
                        'count': len(group)
                    })
                    result['total_duplicates'] += len(group) - 1

        except Exception as e:
            print(f"❌ 檢查重複案件時發生錯誤: {e}")

        return result

    # ====== 工具方法 ======

    def get_validation_summary(self, validation_results: Dict[str, Any]) -> str:
        """
        取得驗證結果摘要

        Args:
            validation_results: 驗證結果

        Returns:
            驗證摘要文字
        """
        try:
            if validation_results.get('total', 0) == 0:
                return "沒有資料需要驗證"

            total = validation_results['total']
            valid = validation_results.get('valid', 0)
            invalid = validation_results.get('invalid', 0)

            summary = f"驗證完成：總計 {total} 筆，有效 {valid} 筆，無效 {invalid} 筆"

            if invalid > 0:
                summary += f"，錯誤率 {(invalid/total)*100:.1f}%"

            return summary

        except Exception as e:
            return f"產生驗證摘要時發生錯誤: {str(e)}"

    @staticmethod
    def is_safe_filename(filename: str) -> bool:
        """
        檢查檔案名稱是否安全

        Args:
            filename: 檔案名稱

        Returns:
            是否安全
        """
        unsafe_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
        return not any(char in filename for char in unsafe_chars)

    @staticmethod
    def get_supported_file_types() -> Dict[str, List[str]]:
        """
        取得支援的檔案類型

        Returns:
            支援的檔案類型字典
        """
        return {
            'excel': ['.xlsx', '.xls'],
            'image': ['.jpg', '.jpeg', '.png', '.gif', '.bmp'],
            'document': ['.pdf', '.doc', '.docx', '.txt'],
            'archive': ['.zip', '.rar', '.7z']
        }