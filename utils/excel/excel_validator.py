#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Excel驗證器 - 專責Excel資料驗證功能
提供欄位完整性檢查、資料格式驗證、品質評分等功能
"""

import re
from typing import Dict, List, Optional, Any, NamedTuple
from dataclasses import dataclass

# 安全的依賴導入
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

from utils.data_cleaner import DataCleaner
from .exceptions import ExcelDependencyError, ExcelDataValidationError


@dataclass
class ValidationResult:
    """驗證結果資料類別"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    suggestions: List[str]
    validated_data: Optional[Dict[str, Any]] = None


class ExcelValidator:
    """Excel驗證器類別"""

    def __init__(self):
        """初始化Excel驗證器"""
        self._check_dependencies()

        # 必要欄位定義
        self.required_fields = ['client']  # 當事人是唯一必要欄位

        # 驗證規則
        self.validation_rules = {
            'client': {
                'required': True,
                'min_length': 1,
                'max_length': 100,
                'pattern': None
            },
            'case_number': {
                'required': False,
                'min_length': 1,
                'max_length': 50,
                'pattern':None
            },
            'case_reason': {
                'required': False,
                'min_length': 1,
                'max_length': 200,
                'pattern': None
            },
            'court': {
                'required': False,
                'min_length': 1,
                'max_length': 100,
                'pattern': None
            },
            'lawyer': {
                'required': False,
                'min_length': 1,
                'max_length': 100,
                'pattern': None
            },
            'legal_affairs': {
                'required': False,
                'min_length': 1,
                'max_length': 100,
                'pattern': None
            }
        }

    def _check_dependencies(self) -> None:
        """檢查必要依賴"""
        if not PANDAS_AVAILABLE:
            raise ExcelDependencyError("pandas 不可用，無法進行Excel驗證")

    def validate_dataframe(
        self,
        df: pd.DataFrame,
        field_mapping: Dict[str, str],
        strict_mode: bool = False
    ) -> ValidationResult:
        """
        驗證整個DataFrame

        Args:
            df: 要驗證的DataFrame
            field_mapping: 欄位對應關係
            strict_mode: 是否使用嚴格模式

        Returns:
            驗證結果
        """
        try:
            errors = []
            warnings = []
            suggestions = []

            # 檢查DataFrame基本狀態
            if df is None or df.empty:
                errors.append("DataFrame為空或不存在")
                return ValidationResult(False, errors, warnings, suggestions)

            # 檢查必要欄位
            missing_fields = self._check_required_fields(field_mapping)
            if missing_fields:
                errors.extend([f"缺少必要欄位: {field}" for field in missing_fields])

            # 檢查欄位對應有效性
            mapping_issues = self._validate_field_mapping(df, field_mapping)
            if mapping_issues:
                warnings.extend(mapping_issues)

            # 逐行驗證資料
            valid_rows = 0
            total_rows = len(df)
            row_errors = []

            for index, row in df.iterrows():
                row_result = self._validate_row(row, field_mapping)

                if row_result.is_valid:
                    valid_rows += 1
                else:
                    if strict_mode:
                        row_errors.extend([f"第{index+1}行: {error}" for error in row_result.errors])
                    else:
                        # 非嚴格模式只記錄警告
                        warnings.extend([f"第{index+1}行: {error}" for error in row_result.errors])

            # 資料品質檢查
            quality_result = self._assess_data_quality(df, field_mapping)
            if quality_result['warnings']:
                warnings.extend(quality_result['warnings'])
            if quality_result['suggestions']:
                suggestions.extend(quality_result['suggestions'])

            # 嚴格模式下的錯誤處理
            if strict_mode and row_errors:
                errors.extend(row_errors)

            # 最終驗證結果
            data_quality_score = (valid_rows / total_rows * 100) if total_rows > 0 else 0

            is_valid = (
                len(errors) == 0 and
                valid_rows > 0 and
                data_quality_score >= 50  # 至少50%的資料有效
            )

            suggestions.append(f"資料品質分數: {data_quality_score:.1f}% ({valid_rows}/{total_rows} 行有效)")

            return ValidationResult(
                is_valid=is_valid,
                errors=errors,
                warnings=warnings,
                suggestions=suggestions,
                validated_data={'valid_rows': valid_rows, 'total_rows': total_rows, 'quality_score': data_quality_score}
            )

        except Exception as e:
            return ValidationResult(
                is_valid=False,
                errors=[f"驗證過程發生錯誤: {str(e)}"],
                warnings=[],
                suggestions=[]
            )

    def validate_field_mapping(self, columns: List[str], field_mapping: Dict[str, str]) -> ValidationResult:
        """
        驗證欄位對應的有效性

        Args:
            columns: 可用欄位列表
            field_mapping: 欄位對應關係

        Returns:
            驗證結果
        """
        errors = []
        warnings = []
        suggestions = []

        # 檢查必要欄位
        missing_required = self._check_required_fields(field_mapping)
        if missing_required:
            errors.extend([f"缺少必要欄位對應: {field}" for field in missing_required])

        # 檢查對應欄位是否存在
        for field, column in field_mapping.items():
            if column not in columns:
                errors.append(f"對應欄位不存在: {field} -> {column}")

        # 檢查重複對應
        used_columns = []
        for field, column in field_mapping.items():
            if column in used_columns:
                warnings.append(f"欄位重複對應: {column}")
            else:
                used_columns.append(column)

        # 建議未對應的欄位
        unmapped_columns = [col for col in columns if col not in field_mapping.values()]
        if unmapped_columns:
            suggestions.append(f"未對應的欄位: {', '.join(unmapped_columns[:5])}")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions
        )

    def validate_case_data(self, case_data: Dict[str, Any]) -> ValidationResult:
        """
        驗證單筆案件資料

        Args:
            case_data: 案件資料字典

        Returns:
            驗證結果
        """
        errors = []
        warnings = []
        suggestions = []
        validated_data = {}

        # 驗證每個欄位
        for field, value in case_data.items():
            field_result = self._validate_field_value(field, value)

            if field_result.errors:
                errors.extend([f"{field}: {error}" for error in field_result.errors])

            if field_result.warnings:
                warnings.extend([f"{field}: {warning}" for warning in field_result.warnings])

            if field_result.suggestions:
                suggestions.extend([f"{field}: {suggestion}" for suggestion in field_result.suggestions])

            # 儲存清理後的值
            validated_data[field] = self._clean_field_value(field, value)

        # 檢查必要欄位
        if not case_data.get('client'):
            errors.append("缺少當事人資料")

        # 邏輯一致性檢查
        logic_issues = self._check_case_logic_consistency(case_data)
        if logic_issues:
            warnings.extend(logic_issues)

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions,
            validated_data=validated_data if len(errors) == 0 else None
        )

    def get_data_quality_score(self, df: pd.DataFrame, field_mapping: Dict[str, str]) -> Dict[str, Any]:
        """
        計算資料品質分數

        Args:
            df: DataFrame
            field_mapping: 欄位對應關係

        Returns:
            品質分數和詳細資訊
        """
        if df is None or df.empty:
            return {
                'overall_score': 0,
                'completeness_score': 0,
                'validity_score': 0,
                'consistency_score': 0,
                'details': {}
            }

        # 完整性分數 (Completeness)
        completeness_scores = {}
        for field, column in field_mapping.items():
            if column in df.columns:
                non_null_rate = df[column].notna().sum() / len(df)
                completeness_scores[field] = non_null_rate * 100

        completeness_score = sum(completeness_scores.values()) / len(completeness_scores) if completeness_scores else 0

        # 有效性分數 (Validity)
        validity_scores = {}
        for field, column in field_mapping.items():
            if column in df.columns:
                valid_count = 0
                total_count = df[column].notna().sum()

                for value in df[column].dropna():
                    field_result = self._validate_field_value(field, value)
                    if field_result.is_valid:
                        valid_count += 1

                validity_scores[field] = (valid_count / total_count * 100) if total_count > 0 else 0

        validity_score = sum(validity_scores.values()) / len(validity_scores) if validity_scores else 0

        # 一致性分數 (Consistency)
        consistency_score = self._calculate_consistency_score(df, field_mapping)

        # 綜合分數
        overall_score = (completeness_score * 0.4 + validity_score * 0.4 + consistency_score * 0.2)

        return {
            'overall_score': round(overall_score, 2),
            'completeness_score': round(completeness_score, 2),
            'validity_score': round(validity_score, 2),
            'consistency_score': round(consistency_score, 2),
            'details': {
                'completeness_by_field': {k: round(v, 2) for k, v in completeness_scores.items()},
                'validity_by_field': {k: round(v, 2) for k, v in validity_scores.items()},
                'total_rows': len(df),
                'non_empty_rows': len(df.dropna(how='all'))
            }
        }

    def _check_required_fields(self, field_mapping: Dict[str, str]) -> List[str]:
        """檢查必要欄位"""
        missing_fields = []
        for required_field in self.required_fields:
            if required_field not in field_mapping:
                missing_fields.append(required_field)
        return missing_fields

    def _validate_field_mapping(self, df: pd.DataFrame, field_mapping: Dict[str, str]) -> List[str]:
        """驗證欄位對應"""
        issues = []

        for field, column in field_mapping.items():
            if column not in df.columns:
                issues.append(f"對應欄位 '{column}' 不存在於工作表中")

        return issues

    def _validate_row(self, row: pd.Series, field_mapping: Dict[str, str]) -> ValidationResult:
        """驗證單一資料列"""
        errors = []
        warnings = []
        suggestions = []
        validated_data = {}

        # 驗證每個已對應的欄位
        for field, column in field_mapping.items():
            if column not in row.index:
                continue

            value = row[column]
            field_result = self._validate_field_value(field, value)

            if field_result.errors:
                errors.extend(field_result.errors)

            if field_result.warnings:
                warnings.extend(field_result.warnings)

            if field_result.suggestions:
                suggestions.extend(field_result.suggestions)

            # 儲存清理後的值
            validated_data[field] = self._clean_field_value(field, value)

        # 檢查是否有足夠資料（至少要有當事人）
        if 'client' not in validated_data or not validated_data['client']:
            errors.append('缺少當事人資料')

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions,
            validated_data=validated_data if len(errors) == 0 else None
        )

    def _validate_field_value(self, field: str, value: Any) -> ValidationResult:
        """驗證單一欄位值"""
        errors = []
        warnings = []
        suggestions = []

        rule = self.validation_rules.get(field, {})

        # 檢查必要欄位
        if rule.get('required', False) and (pd.isna(value) or not str(value).strip()):
            errors.append(f'{field} 是必要欄位')
            return ValidationResult(False, errors, warnings, suggestions)

        # 如果值為空且非必要，跳過其他檢查
        if pd.isna(value) or not str(value).strip():
            return ValidationResult(True, errors, warnings, suggestions)

        # 清理值用於驗證
        cleaned_value = DataCleaner.clean_text_data(value)
        if not cleaned_value:
            warnings.append(f'{field} 資料清理後為空')
            return ValidationResult(True, errors, warnings, suggestions)

        # 長度檢查
        if 'min_length' in rule and len(cleaned_value) < rule['min_length']:
            errors.append(f'{field} 長度不足（最少 {rule["min_length"]} 字元）')

        if 'max_length' in rule and len(cleaned_value) > rule['max_length']:
            warnings.append(f'{field} 長度過長（最多 {rule["max_length"]} 字元），將被截斷')

        # 格式檢查
        if 'pattern' in rule and rule['pattern']:
            if not re.match(rule['pattern'], cleaned_value):
                warnings.append(f'{field} 格式可能不正確')

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions
        )

    def _clean_field_value(self, field: str, value: Any) -> Optional[str]:
        """清理欄位值"""
        if pd.isna(value):
            return None

        cleaned = DataCleaner.clean_text_data(value)

        # 根據欄位類型進行特殊處理
        if cleaned and field in self.validation_rules:
            rule = self.validation_rules[field]

            # 長度截斷
            if 'max_length' in rule and len(cleaned) > rule['max_length']:
                cleaned = cleaned[:rule['max_length']]

        return cleaned

    def _assess_data_quality(self, df: pd.DataFrame, field_mapping: Dict[str, str]) -> Dict[str, List[str]]:
        """評估資料品質"""
        warnings = []
        suggestions = []

        # 檢查空值比例
        for field, column in field_mapping.items():
            if column in df.columns:
                null_rate = df[column].isna().sum() / len(df)
                if null_rate > 0.5:
                    warnings.append(f'{field} 欄位空值比例過高: {null_rate:.1%}')
                elif null_rate > 0.2:
                    suggestions.append(f'{field} 欄位有 {null_rate:.1%} 空值，考慮補充資料')

        # 檢查重複資料
        if 'client' in field_mapping and field_mapping['client'] in df.columns:
            duplicate_count = df[field_mapping['client']].duplicated().sum()
            if duplicate_count > 0:
                warnings.append(f'發現 {duplicate_count} 筆重複的當事人資料')

        return {'warnings': warnings, 'suggestions': suggestions}

    def _check_case_logic_consistency(self, case_data: Dict[str, Any]) -> List[str]:
        """檢查案件資料邏輯一致性"""
        issues = []

        # 檢查案件類型與相關欄位的一致性
        case_type = case_data.get('case_type', '').lower()
        case_reason = case_data.get('case_reason', '').lower()

        if case_type == '民事' and case_reason:
            if any(keyword in case_reason for keyword in ['刑事', '犯罪', '起訴']):
                issues.append('案件類型與案由可能不一致（民事案件包含刑事相關內容）')

        if case_type == '刑事' and case_reason:
            if any(keyword in case_reason for keyword in ['契約', '債務', '侵權']):
                issues.append('案件類型與案由可能不一致（刑事案件包含民事相關內容）')

        return issues

    def _calculate_consistency_score(self, df: pd.DataFrame, field_mapping: Dict[str, str]) -> float:
        """計算一致性分數"""
        consistency_score = 100.0

        # 檢查格式一致性
        for field, column in field_mapping.items():
            if column not in df.columns:
                continue

            non_null_values = df[column].dropna()
            if len(non_null_values) == 0:
                continue

            # 檢查是否有明顯的格式不一致
            formats = set()
            for value in non_null_values.head(20):  # 只檢查前20個值以提高效率
                cleaned = DataCleaner.clean_text_data(value)
                if cleaned:
                    # 簡單的格式檢查
                    has_numbers = any(c.isdigit() for c in cleaned)
                    has_letters = any(c.isalpha() for c in cleaned)
                    has_chinese = any('\u4e00' <= c <= '\u9fff' for c in cleaned)

                    format_signature = (has_numbers, has_letters, has_chinese)
                    formats.add(format_signature)

            if len(formats) > 3:  # 如果格式變化太多，扣分
                consistency_score -= 10

        return max(0, consistency_score)