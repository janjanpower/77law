#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
智慧分析器 - 可選模組
提供進階的資料分析和智慧判斷功能
"""

import re
from collections import Counter
from typing import Dict, List, Any


class SmartAnalyzer:
    """智慧資料分析器"""

    def __init__(self):
        """初始化智慧分析器"""
        # 案件類型關鍵字對應
        self.case_type_keywords = {
            '民事': ['民事', '契約', '侵權', '損害賠償', '債務', '買賣', '租賃'],
            '刑事': ['刑事', '詐欺', '竊盜', '傷害', '妨害', '公然侮辱', '誹謗'],
            '行政': ['行政', '稅務', '罰鍰', '撤銷', '行政處分'],
            '家事': ['家事', '離婚', '監護權', '扶養', '繼承', '遺產'],
            '商事': ['商事', '公司', '股東', '商標', '專利', '營業秘密']
        }

        # 法院類型關鍵字
        self.court_keywords = {
            '地方法院': ['地院', '地方法院'],
            '高等法院': ['高院', '高等法院'],
            '最高法院': ['最高法院'],
            '行政法院': ['行政法院', '高等行政法院'],
            '智慧財產法院': ['智財法院', '智慧財產法院']
        }

    # ==================== 案件類型智慧判斷 ====================

    def analyze_case_type(self, case_reason: str, case_number: str = '', notes: str = '') -> Dict[str, Any]:
        """
        智慧分析案件類型

        Args:
            case_reason: 案由
            case_number: 案號
            notes: 備註

        Returns:
            分析結果
        """
        result = {
            'suggested_type': None,
            'confidence': 0.0,
            'alternatives': [],
            'keywords_found': []
        }

        try:
            # 合併所有文字進行分析
            combined_text = f"{case_reason} {case_number} {notes}".lower()

            # 計算各案件類型的匹配分數
            type_scores = {}

            for case_type, keywords in self.case_type_keywords.items():
                score = 0
                found_keywords = []

                for keyword in keywords:
                    if keyword in combined_text:
                        score += 1
                        found_keywords.append(keyword)

                if score > 0:
                    type_scores[case_type] = {
                        'score': score,
                        'keywords': found_keywords
                    }

            # 找出最佳匹配
            if type_scores:
                best_type = max(type_scores, key=lambda x: type_scores[x]['score'])
                best_score = type_scores[best_type]['score']

                result['suggested_type'] = best_type
                result['confidence'] = min(best_score / 3.0, 1.0)  # 標準化到0-1
                result['keywords_found'] = type_scores[best_type]['keywords']

                # 找出其他候選項
                alternatives = []
                for case_type, info in type_scores.items():
                    if case_type != best_type and info['score'] > 0:
                        alternatives.append({
                            'type': case_type,
                            'score': info['score'],
                            'confidence': min(info['score'] / 3.0, 1.0)
                        })

                result['alternatives'] = sorted(alternatives, key=lambda x: x['score'], reverse=True)

        except Exception as e:
            result['error'] = f"分析失敗: {str(e)}"

        return result

    # ==================== 法院智慧識別 ====================

    def analyze_court_info(self, case_number: str, court: str = '') -> Dict[str, Any]:
        """
        智慧分析法院資訊

        Args:
            case_number: 案號
            court: 法院名稱

        Returns:
            分析結果
        """
        result = {
            'suggested_court': None,
            'court_type': None,
            'location': None,
            'extracted_info': {}
        }

        try:
            combined_text = f"{case_number} {court}".lower()

            # 從案號中提取法院資訊
            court_patterns = [
                r'(\w+)地方法院',
                r'(\w+)地院',
                r'(\w+)高等法院',
                r'(\w+)高院',
                r'最高法院',
                r'(\w+)行政法院',
                r'智慧?財產法院'
            ]

            for pattern in court_patterns:
                match = re.search(pattern, combined_text)
                if match:
                    if '地方法院' in pattern or '地院' in pattern:
                        result['court_type'] = '地方法院'
                        if match.groups():
                            result['location'] = match.group(1)
                    elif '高等法院' in pattern or '高院' in pattern:
                        result['court_type'] = '高等法院'
                        if match.groups():
                            result['location'] = match.group(1)
                    elif '最高法院' in pattern:
                        result['court_type'] = '最高法院'
                    elif '行政法院' in pattern:
                        result['court_type'] = '行政法院'
                        if match.groups():
                            result['location'] = match.group(1)
                    elif '智慧財產法院' in pattern:
                        result['court_type'] = '智慧財產法院'
                    break

            # 建議完整法院名稱
            if result['court_type'] and result['location']:
                result['suggested_court'] = f"{result['location']}{result['court_type']}"
            elif result['court_type']:
                result['suggested_court'] = result['court_type']

        except Exception as e:
            result['error'] = f"分析失敗: {str(e)}"

        return result

    # ==================== 案號格式分析 ====================

    def analyze_case_number_format(self, case_number: str) -> Dict[str, Any]:
        """
        分析案號格式並提取資訊

        Args:
            case_number: 案號

        Returns:
            分析結果
        """
        result = {
            'is_valid_format': False,
            'year': None,
            'case_type': None,
            'number': None,
            'extracted_parts': {},
            'format_suggestions': []
        }

        try:
            if not case_number:
                return result

            clean_number = case_number.strip()

            # 台灣法院案號格式：111年度訴字第123號
            patterns = [
                r'(\d{2,3})年度(\w+)字第(\d+)號',  # 標準格式
                r'(\d{2,3})年(\w+)字第(\d+)號',    # 簡化格式
                r'(\d{2,3})年度(\w+)(\d+)號',      # 無"字第"
                r'(\d{2,3})-(\w+)-(\d+)',          # 連字號格式
            ]

            for pattern in patterns:
                match = re.search(pattern, clean_number)
                if match:
                    result['is_valid_format'] = True
                    result['year'] = match.group(1)
                    result['case_type'] = match.group(2)
                    result['number'] = match.group(3)

                    result['extracted_parts'] = {
                        'year': result['year'],
                        'case_type': result['case_type'],
                        'number': result['number']
                    }
                    break

            # 如果無法解析，提供格式建議
            if not result['is_valid_format']:
                result['format_suggestions'] = [
                    "標準格式：111年度訴字第123號",
                    "簡化格式：111年訴字第123號",
                    "檢查是否有遺漏的字元或格式錯誤"
                ]

        except Exception as e:
            result['error'] = f"分析失敗: {str(e)}"

        return result

    # ==================== 資料品質分析 ====================

    def analyze_data_quality(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析案件資料品質

        Args:
            case_data: 案件資料字典

        Returns:
            品質分析結果
        """
        result = {
            'overall_score': 0.0,
            'completeness': {},
            'quality_issues': [],
            'suggestions': []
        }

        try:
            # 定義必要欄位和重要欄位
            required_fields = ['client', 'case_type']
            important_fields = ['case_id', 'case_reason', 'case_number']
            optional_fields = ['court', 'lawyer', 'legal_affairs']

            # 計算完整性分數
            total_fields = len(required_fields) + len(important_fields) + len(optional_fields)
            filled_fields = 0

            # 檢查必要欄位
            for field in required_fields:
                if case_data.get(field):
                    filled_fields += 2  # 必要欄位加權
                    result['completeness'][field] = 'excellent'
                else:
                    result['quality_issues'].append(f"缺少必要欄位: {field}")
                    result['completeness'][field] = 'missing'

            # 檢查重要欄位
            for field in important_fields:
                if case_data.get(field):
                    filled_fields += 1.5  # 重要欄位加權
                    result['completeness'][field] = 'good'
                else:
                    result['suggestions'].append(f"建議填寫: {field}")
                    result['completeness'][field] = 'missing'

            # 檢查可選欄位
            for field in optional_fields:
                if case_data.get(field):
                    filled_fields += 1
                    result['completeness'][field] = 'good'
                else:
                    result['completeness'][field] = 'optional'

            # 計算總分（滿分為必要欄位*2 + 重要欄位*1.5 + 可選欄位*1）
            max_score = len(required_fields) * 2 + len(important_fields) * 1.5 + len(optional_fields) * 1
            result['overall_score'] = min(filled_fields / max_score, 1.0) * 100

            # 品質等級判定
            if result['overall_score'] >= 90:
                result['quality_level'] = 'excellent'
            elif result['overall_score'] >= 70:
                result['quality_level'] = 'good'
            elif result['overall_score'] >= 50:
                result['quality_level'] = 'fair'
            else:
                result['quality_level'] = 'poor'

            # 特定欄位品質檢查
            self._check_specific_field_quality(case_data, result)

        except Exception as e:
            result['error'] = f"分析失敗: {str(e)}"

        return result

    def _check_specific_field_quality(self, case_data: Dict[str, Any], result: Dict[str, Any]):
        """檢查特定欄位的品質"""
        try:
            # 檢查案件編號格式
            if case_data.get('case_id'):
                case_id = case_data['case_id']
                if len(case_id) < 3:
                    result['quality_issues'].append("案件編號過短")
                elif len(case_id) > 50:
                    result['quality_issues'].append("案件編號過長")

            # 檢查當事人姓名
            if case_data.get('client'):
                client = case_data['client']
                if len(client) < 2:
                    result['quality_issues'].append("當事人姓名過短")
                elif len(client) > 100:
                    result['quality_issues'].append("當事人姓名過長")

            # 檢查案號格式
            if case_data.get('case_number'):
                case_number = case_data['case_number']
                format_analysis = self.analyze_case_number_format(case_number)
                if not format_analysis['is_valid_format']:
                    result['quality_issues'].append("案號格式不標準")

        except Exception as e:
            result['quality_issues'].append(f"欄位品質檢查失敗: {str(e)}")

    # ==================== 重複資料偵測 ====================

    def detect_duplicates(self, case_list: List[Dict[str, Any]], threshold: float = 0.8) -> Dict[str, Any]:
        """
        偵測重複的案件資料

        Args:
            case_list: 案件資料列表
            threshold: 相似度閾值

        Returns:
            重複偵測結果
        """
        result = {
            'duplicates_found': [],
            'potential_duplicates': [],
            'duplicate_count': 0,
            'unique_count': 0
        }

        try:
            duplicates = []
            checked_indices = set()

            for i, case1 in enumerate(case_list):
                if i in checked_indices:
                    continue

                duplicate_group = [i]

                for j, case2 in enumerate(case_list[i+1:], i+1):
                    if j in checked_indices:
                        continue

                    similarity = self._calculate_case_similarity(case1, case2)

                    if similarity >= threshold:
                        duplicate_group.append(j)
                        checked_indices.add(j)

                if len(duplicate_group) > 1:
                    duplicates.append({
                        'indices': duplicate_group,
                        'cases': [case_list[idx] for idx in duplicate_group],
                        'similarity_scores': [
                            self._calculate_case_similarity(case_list[duplicate_group[0]], case_list[idx])
                            for idx in duplicate_group[1:]
                        ]
                    })
                    checked_indices.update(duplicate_group)

            result['duplicates_found'] = duplicates
            result['duplicate_count'] = sum(len(group['indices']) for group in duplicates)
            result['unique_count'] = len(case_list) - result['duplicate_count']

            # 偵測潛在重複（相似度較低但可能相關）
            potential_threshold = max(threshold - 0.2, 0.5)
            for i, case1 in enumerate(case_list):
                for j, case2 in enumerate(case_list[i+1:], i+1):
                    similarity = self._calculate_case_similarity(case1, case2)

                    if potential_threshold <= similarity < threshold:
                        result['potential_duplicates'].append({
                            'indices': [i, j],
                            'cases': [case1, case2],
                            'similarity': similarity
                        })

        except Exception as e:
            result['error'] = f"重複偵測失敗: {str(e)}"

        return result

    def _calculate_case_similarity(self, case1: Dict[str, Any], case2: Dict[str, Any]) -> float:
        """計算兩個案件的相似度"""
        try:
            # 權重設定
            weights = {
                'client': 0.4,
                'case_number': 0.3,
                'case_reason': 0.2,
                'court': 0.1
            }

            total_score = 0.0
            total_weight = 0.0

            for field, weight in weights.items():
                value1 = case1.get(field, '').lower().strip()
                value2 = case2.get(field, '').lower().strip()

                if value1 and value2:
                    # 計算字串相似度
                    similarity = self._string_similarity(value1, value2)
                    total_score += similarity * weight
                    total_weight += weight
                elif value1 == value2:  # 都是空值
                    total_score += 0.5 * weight
                    total_weight += weight

            return total_score / total_weight if total_weight > 0 else 0.0

        except Exception:
            return 0.0

    def _string_similarity(self, str1: str, str2: str) -> float:
        """計算字串相似度（簡單的比較方法）"""
        try:
            if str1 == str2:
                return 1.0

            # 使用編輯距離的簡化版本
            len1, len2 = len(str1), len(str2)
            if len1 == 0 or len2 == 0:
                return 0.0

            # 計算最長公共子序列
            common_chars = 0
            for char in str1:
                if char in str2:
                    common_chars += 1

            return (2.0 * common_chars) / (len1 + len2)

        except Exception:
            return 0.0

    # ==================== 資料統計分析 ====================

    def generate_data_statistics(self, case_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        生成資料統計報告

        Args:
            case_list: 案件資料列表

        Returns:
            統計報告
        """
        result = {
            'total_cases': 0,
            'case_type_distribution': {},
            'court_distribution': {},
            'lawyer_distribution': {},
            'completeness_stats': {},
            'quality_summary': {}
        }

        try:
            result['total_cases'] = len(case_list)

            # 統計案件類型分佈
            case_types = [case.get('case_type', '未知') for case in case_list]
            result['case_type_distribution'] = dict(Counter(case_types))

            # 統計法院分佈
            courts = [case.get('court', '未知') for case in case_list if case.get('court')]
            result['court_distribution'] = dict(Counter(courts))

            # 統計律師分佈
            lawyers = [case.get('lawyer', '未知') for case in case_list if case.get('lawyer')]
            result['lawyer_distribution'] = dict(Counter(lawyers))

            # 完整性統計
            fields = ['client', 'case_type', 'case_reason', 'case_number', 'court', 'lawyer']
            completeness = {}

            for field in fields:
                filled_count = sum(1 for case in case_list if case.get(field))
                completeness[field] = {
                    'filled': filled_count,
                    'percentage': (filled_count / len(case_list) * 100) if case_list else 0
                }

            result['completeness_stats'] = completeness

            # 品質摘要
            quality_scores = []
            for case in case_list:
                quality = self.analyze_data_quality(case)
                quality_scores.append(quality.get('overall_score', 0))

            if quality_scores:
                result['quality_summary'] = {
                    'average_score': sum(quality_scores) / len(quality_scores),
                    'min_score': min(quality_scores),
                    'max_score': max(quality_scores),
                    'excellent_count': sum(1 for score in quality_scores if score >= 90),
                    'good_count': sum(1 for score in quality_scores if 70 <= score < 90),
                    'fair_count': sum(1 for score in quality_scores if 50 <= score < 70),
                    'poor_count': sum(1 for score in quality_scores if score < 50)
                }

        except Exception as e:
            result['error'] = f"統計分析失敗: {str(e)}"

        return result

    # ==================== 智慧建議功能 ====================

    def generate_smart_suggestions(self, case_data: Dict[str, Any]) -> List[str]:
        """
        根據案件資料生成智慧建議

        Args:
            case_data: 案件資料

        Returns:
            建議列表
        """
        suggestions = []

        try:
            # 案件類型建議
            if case_data.get('case_reason'):
                type_analysis = self.analyze_case_type(case_data['case_reason'])
                if type_analysis.get('suggested_type') and not case_data.get('case_type'):
                    suggestions.append(f"建議案件類型：{type_analysis['suggested_type']}")

            # 法院建議
            if case_data.get('case_number') and not case_data.get('court'):
                court_analysis = self.analyze_court_info(case_data['case_number'])
                if court_analysis.get('suggested_court'):
                    suggestions.append(f"建議法院：{court_analysis['suggested_court']}")

            # 案號格式建議
            if case_data.get('case_number'):
                format_analysis = self.analyze_case_number_format(case_data['case_number'])
                if not format_analysis['is_valid_format']:
                    suggestions.extend(format_analysis.get('format_suggestions', []))

            # 資料完整性建議
            quality_analysis = self.analyze_data_quality(case_data)
            suggestions.extend(quality_analysis.get('suggestions', []))

        except Exception as e:
            suggestions.append(f"建議生成失敗: {str(e)}")

        return suggestions

    # ==================== 工具方法 ====================

    def get_analyzer_info(self) -> Dict[str, Any]:
        """取得分析器資訊"""
        return {
            'version': '1.0.0',
            'capabilities': [
                '案件類型智慧判斷',
                '法院資訊識別',
                '案號格式分析',
                '資料品質評估',
                '重複資料偵測',
                '統計分析',
                '智慧建議生成'
            ],
            'supported_case_types': list(self.case_type_keywords.keys()),
            'supported_court_types': list(self.court_keywords.keys())
        }