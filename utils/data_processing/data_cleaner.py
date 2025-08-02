#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
資料清理器 - 重構版本
負責各種資料的清理、標準化和驗證
從原有的程式碼中提取並整合資料清理功能
"""

import re
import unicodedata
from typing import Optional, List, Dict, Any, Union
from datetime import datetime


class DataCleaner:
    """資料清理核心類別"""

    def __init__(self):
        """初始化資料清理器"""
        # 常見的標點符號對應
        self.punctuation_map = {
            '，': ',',
            '。': '.',
            '；': ';',
            '：': ':',
            '？': '?',
            '！': '!',
            '（': '(',
            '）': ')',
            '【': '[',
            '】': ']',
            '「': '"',
            '」': '"',
            '『': "'",
            '』': "'"
        }

    # ==================== 文字資料清理 ====================

    def clean_text_data(self, text: Union[str, Any]) -> Optional[str]:
        """
        清理文字資料

        Args:
            text: 原始文字資料

        Returns:
            清理後的文字或None
        """
        if not text:
            return None

        try:
            # 轉換為字串
            clean_text = str(text).strip()

            # 移除多餘的空白字元
            clean_text = re.sub(r'\s+', ' ', clean_text)

            # 移除控制字元
            clean_text = ''.join(char for char in clean_text
                               if unicodedata.category(char) != 'Cc')

            # 標準化標點符號
            clean_text = self._normalize_punctuation(clean_text)

            # 移除前後空格
            clean_text = clean_text.strip()

            return clean_text if clean_text else None

        except Exception as e:
            print(f"⚠️ 文字清理失敗: {e}")
            return str(text).strip() if text else None

    def _normalize_punctuation(self, text: str) -> str:
        """標準化標點符號"""
        for chinese_punct, english_punct in self.punctuation_map.items():
            text = text.replace(chinese_punct, english_punct)
        return text

    def clean_name_data(self, name: Union[str, Any]) -> Optional[str]:
        """
        清理姓名資料

        Args:
            name: 原始姓名

        Returns:
            清理後的姓名
        """
        if not name:
            return None

        try:
            clean_name = self.clean_text_data(name)
            if not clean_name:
                return None

            # 移除多餘的空格
            clean_name = re.sub(r'\s+', ' ', clean_name)

            # 移除常見的無效字元
            invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*', '\t', '\n', '\r']
            for char in invalid_chars:
                clean_name = clean_name.replace(char, '')

            # 限制長度
            if len(clean_name) > 100:
                clean_name = clean_name[:100]

            return clean_name.strip() if clean_name.strip() else None

        except Exception as e:
            print(f"⚠️ 姓名清理失敗: {e}")
            return str(name).strip() if name else None

    def clean_case_number(self, case_number: Union[str, Any]) -> Optional[str]:
        """
        清理案號資料

        Args:
            case_number: 原始案號

        Returns:
            清理後的案號
        """
        if not case_number:
            return None

        try:
            clean_number = self.clean_text_data(case_number)
            if not clean_number:
                return None

            # 移除多餘的括號和空格
            clean_number = re.sub(r'\s*[\(\)]\s*', '', clean_number)
            clean_number = re.sub(r'\s+', ' ', clean_number)

            # 標準化案號格式
            # 例如：111年度訴字第123號 -> 111年度訴字第123號
            clean_number = re.sub(r'(\d+)\s*年\s*度', r'\1年度', clean_number)
            clean_number = re.sub(r'第\s*(\d+)\s*號', r'第\1號', clean_number)

            return clean_number.strip() if clean_number.strip() else None

        except Exception as e:
            print(f"⚠️ 案號清理失敗: {e}")
            return str(case_number).strip() if case_number else None

    # ==================== 日期資料清理 ====================

    def clean_date_data(self, date_input: Union[str, datetime, Any]) -> Optional[str]:
        """
        清理日期資料

        Args:
            date_input: 原始日期資料

        Returns:
            標準格式的日期字串（YYYY-MM-DD）
        """
        if not date_input:
            return None

        try:
            # 如果已經是datetime物件
            if isinstance(date_input, datetime):
                return date_input.strftime('%Y-%m-%d')

            # 轉換為字串並清理
            date_str = str(date_input).strip()
            if not date_str:
                return None

            # 嘗試解析各種日期格式
            parsed_date = self._parse_date_string(date_str)
            if parsed_date:
                return parsed_date.strftime('%Y-%m-%d')

            return None

        except Exception as e:
            print(f"⚠️ 日期清理失敗: {e}")
            return None

    def _parse_date_string(self, date_str: str) -> Optional[datetime]:
        """解析日期字串"""
        # 支援的日期格式
        date_formats = [
            '%Y-%m-%d',
            '%Y/%m/%d',
            '%Y.%m.%d',
            '%Y-%m-%d %H:%M:%S',
            '%Y/%m/%d %H:%M:%S',
            '%m/%d/%Y',
            '%d/%m/%Y',
            '%Y年%m月%d日',
            '%m月%d日',
            '%m-%d'
        ]

        for fmt in date_formats:
            try:
                parsed = datetime.strptime(date_str, fmt)

                # 處理只有月日的情況，補上當前年份
                if '%Y' not in fmt:
                    current_year = datetime.now().year
                    parsed = parsed.replace(year=current_year)

                return parsed
            except ValueError:
                continue

        return None

    # ==================== 數值資料清理 ====================

    def clean_numeric_data(self, value: Union[str, int, float, Any]) -> Optional[Union[int, float]]:
        """
        清理數值資料

        Args:
            value: 原始數值

        Returns:
            清理後的數值
        """
        if value is None:
            return None

        try:
            # 如果已經是數值類型
            if isinstance(value, (int, float)):
                return value

            # 轉換為字串並清理
            clean_str = str(value).strip()
            if not clean_str:
                return None

            # 移除常見的非數字字元
            clean_str = re.sub(r'[,，\s]', '', clean_str)
            clean_str = re.sub(r'[^\d.-]', '', clean_str)

            # 嘗試轉換為數值
            if '.' in clean_str:
                return float(clean_str)
            else:
                return int(clean_str)

        except Exception:
            return None

    # ==================== 電話號碼清理 ====================

    def clean_phone_number(self, phone: Union[str, Any]) -> Optional[str]:
        """
        清理電話號碼

        Args:
            phone: 原始電話號碼

        Returns:
            清理後的電話號碼
        """
        if not phone:
            return None

        try:
            clean_phone = str(phone).strip()

            # 移除常見的分隔符號
            clean_phone = re.sub(r'[-\s\(\)]', '', clean_phone)

            # 只保留數字和+號
            clean_phone = re.sub(r'[^\d+]', '', clean_phone)

            # 檢查是否為有效的電話號碼格式
            if re.match(r'^(\+886|0)?[2-9]\d{7,8}$', clean_phone):
                return clean_phone
            elif re.match(r'^09\d{8}$', clean_phone):  # 手機號碼
                return clean_phone

            return clean_phone if clean_phone else None

        except Exception as e:
            print(f"⚠️ 電話號碼清理失敗: {e}")
            return str(phone).strip() if phone else None

    # ==================== 地址資料清理 ====================

    def clean_address_data(self, address: Union[str, Any]) -> Optional[str]:
        """
        清理地址資料

        Args:
            address: 原始地址

        Returns:
            清理後的地址
        """
        if not address:
            return None

        try:
            clean_address = self.clean_text_data(address)
            if not clean_address:
                return None

            # 標準化地址格式
            # 移除多餘的空格
            clean_address = re.sub(r'\s+', '', clean_address)

            # 標準化縣市名稱
            clean_address = clean_address.replace('台北市', '臺北市')
            clean_address = clean_address.replace('台中市', '臺中市')
            clean_address = clean_address.replace('台南市', '臺南市')
            clean_address = clean_address.replace('台東縣', '臺東縣')

            return clean_address if clean_address else None

        except Exception as e:
            print(f"⚠️ 地址清理失敗: {e}")
            return str(address).strip() if address else None

    # ==================== 批量清理功能 ====================

    def clean_case_data_dict(self, case_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        清理案件資料字典

        Args:
            case_dict: 原始案件資料字典

        Returns:
            清理後的案件資料字典
        """
        if not isinstance(case_dict, dict):
            return {}

        cleaned_data = {}

        try:
            # 定義清理規則
            cleaning_rules = {
                'client': self.clean_name_data,
                'case_id': self.clean_text_data,
                'case_type': self.clean_text_data,
                'case_reason': self.clean_text_data,
                'case_number': self.clean_case_number,
                'court': self.clean_text_data,
                'opposing_party': self.clean_name_data,
                'division': self.clean_text_data,
                'lawyer': self.clean_name_data,
                'legal_affairs': self.clean_name_data,
                'notes': self.clean_text_data,
                'phone': self.clean_phone_number,
                'address': self.clean_address_data
            }

            # 執行清理
            for key, value in case_dict.items():
                if key in cleaning_rules:
                    cleaned_data[key] = cleaning_rules[key](value)
                else:
                    # 一般文字清理
                    cleaned_data[key] = self.clean_text_data(value)

            return cleaned_data

        except Exception as e:
            print(f"⚠️ 案件資料清理失敗: {e}")
            return case_dict

    def clean_excel_data_list(self, data_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        清理Excel資料列表

        Args:
            data_list: 原始資料列表

        Returns:
            清理後的資料列表
        """
        if not isinstance(data_list, list):
            return []

        cleaned_list = []

        try:
            for item in data_list:
                if isinstance(item, dict):
                    cleaned_item = self.clean_case_data_dict(item)
                    if cleaned_item:  # 只保留有效的清理結果
                        cleaned_list.append(cleaned_item)

            return cleaned_list

        except Exception as e:
            print(f"⚠️ Excel資料列表清理失敗: {e}")
            return data_list

    # ==================== 驗證功能 ====================

    def validate_cleaned_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        驗證清理後的資料

        Args:
            data: 清理後的資料

        Returns:
            驗證結果
        """
        result = {
            'is_valid': True,
            'errors': [],
            'warnings': []
        }

        try:
            # 檢查必要欄位
            required_fields = ['client']
            for field in required_fields:
                if not data.get(field):
                    result['errors'].append(f"缺少必要欄位: {field}")

            # 檢查資料格式
            if data.get('case_id') and len(str(data['case_id'])) > 50:
                result['warnings'].append("案件編號過長")

            if data.get('client') and len(str(data['client'])) > 100:
                result['warnings'].append("當事人姓名過長")

            if result['errors']:
                result['is_valid'] = False

        except Exception as e:
            result['is_valid'] = False
            result['errors'].append(f"驗證過程發生錯誤: {str(e)}")

        return result

    # ==================== 統計功能 ====================

    def get_cleaning_stats(self, original_data: List[Dict], cleaned_data: List[Dict]) -> Dict[str, Any]:
        """
        取得清理統計資訊

        Args:
            original_data: 原始資料
            cleaned_data: 清理後資料

        Returns:
            清理統計結果
        """
        try:
            stats = {
                'original_count': len(original_data),
                'cleaned_count': len(cleaned_data),
                'removed_count': len(original_data) - len(cleaned_data),
                'fields_cleaned': {},
                'cleaning_rate': 0.0
            }

            if stats['original_count'] > 0:
                stats['cleaning_rate'] = (stats['cleaned_count'] / stats['original_count']) * 100

            # 統計各欄位的清理情況
            if cleaned_data:
                sample_fields = cleaned_data[0].keys()
                for field in sample_fields:
                    original_values = [item.get(field) for item in original_data if item.get(field)]
                    cleaned_values = [item.get(field) for item in cleaned_data if item.get(field)]

                    stats['fields_cleaned'][field] = {
                        'original': len(original_values),
                        'cleaned': len(cleaned_values),
                        'change_rate': ((len(cleaned_values) / len(original_values)) * 100) if original_values else 0
                    }

            return stats

        except Exception as e:
            print(f"⚠️ 統計計算失敗: {e}")
            return {'error': str(e)}

    # ==================== 工具方法 ====================

    def is_empty_or_none(self, value: Any) -> bool:
        """檢查值是否為空或None"""
        if value is None:
            return True

        if isinstance(value, str):
            return not value.strip()

        if isinstance(value, (list, dict)):
            return len(value) == 0

        return False

    def normalize_whitespace(self, text: str) -> str:
        """標準化空白字元"""
        if not text:
            return ""

        # 將所有空白字元標準化為單一空格
        return re.sub(r'\s+', ' ', text).strip()

    def remove_duplicates(self, data_list: List[Dict[str, Any]], key_field: str = 'client') -> List[Dict[str, Any]]:
        """
        移除重複的資料項目

        Args:
            data_list: 資料列表
            key_field: 用於判斷重複的關鍵欄位

        Returns:
            去重後的資料列表
        """
        try:
            seen_keys = set()
            unique_data = []

            for item in data_list:
                key_value = item.get(key_field)
                if key_value and key_value not in seen_keys:
                    seen_keys.add(key_value)
                    unique_data.append(item)

            print(f"✅ 去重完成：原始 {len(data_list)} 筆，去重後 {len(unique_data)} 筆")
            return unique_data

        except Exception as e:
            print(f"⚠️ 去重失敗: {e}")
            return data_list