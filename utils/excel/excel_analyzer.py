#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Excel分析器 - 專責Excel智慧分析功能
提供工作表分類、欄位對應、資料品質分析等功能
"""

import re
from typing import Dict, List, Optional, Any, Tuple

# 安全的依賴導入
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

from models.case_model import CaseData
from utils.data_cleaner import DataCleaner
from .excel_reader import ExcelReader
from .exceptions import ExcelDependencyError


class ExcelAnalyzer:
    """Excel分析器類別"""

    def __init__(self):
        """初始化Excel分析器"""
        self._check_dependencies()
        self.reader = ExcelReader()

        # 欄位對應規則
        self.field_mapping_rules = {
            'client': ['當事人', '客戶', '委託人', '姓名', '名稱'],
            'case_reason': ['案由', '事由', '案件事由'],
            'case_number': ['案號', '機關', '案件號碼', '機關案號', '法院案號', '案件號', '號碼'],
            'court': ['法院', '負責法院', '管轄法院', '審理法院', '法庭'],
            'opposing_party': ['對造', '對方當事人', '相對人'],
            'division': ['股別', '負責股別', '承辦股'],
            'lawyer': ['律師', '代理人', '委任律師'],
            'legal_affairs': ['法務', '法務人員'],
            'progress': ['進度', '狀態', '案件狀態'],
            'case_id': ['案件編號', '編號', 'ID', '序號']
        }

        # 案件類型識別關鍵字
        self.case_type_keywords = {
            '民事': ['民事', 'civil', '民', '契約', '侵權', '債務', '財產'],
            '刑事': ['刑事', 'criminal', '刑', '犯罪', '違法', '起訴'],
            '行政': ['行政', 'administrative', '行政訴訟', '行政處分'],
            '家事': ['家事', 'family', '離婚', '監護', '收養']
        }

    def _check_dependencies(self) -> None:
        """檢查必要依賴"""
        if not PANDAS_AVAILABLE:
            raise ExcelDependencyError("pandas 不可用，無法進行Excel分析")

    def analyze_excel_comprehensive(self, file_path: str) -> Tuple[bool, str, Dict[str, Any]]:
        """
        綜合分析Excel檔案

        Args:
            file_path: Excel檔案路徑

        Returns:
            (成功狀態, 分析報告, 詳細結果)
        """
        try:
            print(f"🔍 開始綜合分析: {file_path}")

            # 讀取檔案基本資訊
            file_info = self.reader.read_excel_file_info(file_path)
            print(f"    檔案大小: {file_info['file_size_mb']} MB")
            print(f"    工作表數量: {file_info['sheet_count']}")

            # 分析所有工作表
            sheets_analysis = {}
            categorized_sheets = {'民事': [], '刑事': [], '行政': [], '家事': [], 'unknown': []}

            for sheet_name in file_info['sheet_names']:
                print(f"  🔍 分析工作表: {sheet_name}")

                sheet_analysis = self.analyze_single_sheet(file_path, sheet_name)
                sheets_analysis[sheet_name] = sheet_analysis

                # 分類工作表
                if sheet_analysis['success']:
                    case_type = self._classify_sheet_by_content(sheet_name, sheet_analysis)
                    categorized_sheets[case_type].append(sheet_name)
                    print(f"      分類結果: {case_type}")
                else:
                    categorized_sheets['unknown'].append(sheet_name)
                    print(f"      分析失敗: {sheet_analysis.get('error', '未知錯誤')}")

            # 生成分析報告
            report = self._generate_analysis_report(file_info, sheets_analysis, categorized_sheets)

            # 構建詳細結果
            detailed_result = {
                'file_info': file_info,
                'sheets_analysis': sheets_analysis,
                'categorized_sheets': categorized_sheets,
                'analysis_summary': {
                    'total_sheets': len(file_info['sheet_names']),
                    'processable_sheets': sum(1 for analysis in sheets_analysis.values() if analysis['success']),
                    'case_types_found': {k: len(v) for k, v in categorized_sheets.items() if v}
                }
            }

            success = any(analysis['success'] for analysis in sheets_analysis.values())
            print("✅ 綜合分析完成")

            return success, report, detailed_result

        except Exception as e:
            error_msg = f"綜合分析失敗: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg, {}

    def analyze_single_sheet(self, file_path: str, sheet_name: str) -> Dict[str, Any]:
        """
        分析單一工作表

        Args:
            file_path: Excel檔案路徑
            sheet_name: 工作表名稱

        Returns:
            工作表分析結果
        """
        try:
            # 讀取工作表資料
            df = self.reader.read_sheet_data(file_path, sheet_name)

            if df is None or df.empty:
                return {
                    'success': False,
                    'error': '工作表為空或無法讀取',
                    'has_data': False
                }

            # 檢測標題列
            header_row = self.reader.detect_header_row(file_path, sheet_name)

            # 分析欄位對應
            column_mapping = self._create_column_mapping(df.columns.tolist())

            # 分析資料品質
            quality_analysis = self._analyze_data_quality(df)

            # 檢查案號合併需求
            merge_analysis = self._analyze_case_number_merge_needs(df.columns.tolist())

            # 預估資料筆數
            valid_data_count = self._estimate_valid_data_count(df, column_mapping)

            return {
                'success': True,
                'sheet_name': sheet_name,
                'header_row': header_row,
                'total_rows': len(df),
                'total_columns': len(df.columns),
                'column_mapping': column_mapping,
                'quality_analysis': quality_analysis,
                'merge_analysis': merge_analysis,
                'valid_data_count': valid_data_count,
                'has_required_fields': bool(column_mapping.get('client')),
                'columns': df.columns.tolist()
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'has_data': False
            }

    def extract_cases_from_analysis(
        self,
        file_path: str,
        analysis_result: Dict[str, Any]
    ) -> Tuple[bool, str, Dict[str, List[CaseData]]]:
        """
        根據分析結果提取案件資料

        Args:
            file_path: Excel檔案路徑
            analysis_result: 分析結果

        Returns:
            (成功狀態, 結果訊息, 分類案件資料)
        """
        try:
            all_cases = {'民事': [], '刑事': [], '行政': [], '家事': []}
            import_summary = []

            sheets_analysis = analysis_result.get('sheets_analysis', {})
            categorized_sheets = analysis_result.get('categorized_sheets', {})

            for case_type, sheet_names in categorized_sheets.items():
                if case_type == 'unknown' or not sheet_names:
                    continue

                for sheet_name in sheet_names:
                    sheet_analysis = sheets_analysis.get(sheet_name)
                    if not sheet_analysis or not sheet_analysis['success']:
                        continue

                    try:
                        print(f"  提取 {case_type} 案件: {sheet_name}")
                        cases = self._extract_cases_from_sheet(
                            file_path, sheet_name, case_type, sheet_analysis
                        )

                        if cases:
                            all_cases[case_type].extend(cases)
                            import_summary.append(f"「{sheet_name}」: {len(cases)} 筆{case_type}案件")
                            print(f"    ✅ 提取 {len(cases)} 筆")
                        else:
                            import_summary.append(f"「{sheet_name}」: 沒有有效資料")

                    except Exception as e:
                        import_summary.append(f"「{sheet_name}」: 提取失敗 - {str(e)}")
                        print(f"    ❌ 提取失敗: {e}")

            # 統計結果
            total_cases = sum(len(cases) for cases in all_cases.values())

            if total_cases == 0:
                return False, "沒有成功提取任何案件資料", all_cases

            # 生成結果訊息
            summary_lines = [f"✅ 提取完成！共 {total_cases} 筆案件"]

            for case_type, cases in all_cases.items():
                if cases:
                    summary_lines.append(f"📋 {case_type}案件: {len(cases)} 筆")

            summary_lines.append("\n📊 詳細結果:")
            summary_lines.extend(import_summary)

            return True, "\n".join(summary_lines), all_cases

        except Exception as e:
            error_msg = f"提取案件資料失敗: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg, {'民事': [], '刑事': [], '行政': [], '家事': []}

    def _create_column_mapping(self, columns: List[str]) -> Dict[str, str]:
        """建立欄位對應關係"""
        mapping = {}
        used_columns = set()

        print(f"        可用欄位: {', '.join(str(col) for col in columns)}")

        # 按優先順序對應欄位
        for field, keywords in self.field_mapping_rules.items():
            matched_column = self._find_best_column_match(field, columns, used_columns)
            if matched_column:
                mapping[field] = matched_column
                used_columns.add(matched_column)
                print(f"        ✅ {field}: 「{matched_column}」")

        return mapping

    def _find_best_column_match(self, field: str, columns: List[str], used_columns: set) -> Optional[str]:
        """尋找最佳欄位匹配"""
        keywords = self.field_mapping_rules.get(field, [])
        best_match = None
        best_score = 0

        for col in columns:
            if col in used_columns:
                continue

            col_clean = str(col).strip()
            score = 0

            # 精確匹配得分最高
            for keyword in keywords:
                if keyword == col_clean:
                    score += 100
                elif keyword in col_clean:
                    score += 50
                elif col_clean in keyword:
                    score += 30
                elif self._fuzzy_match(keyword, col_clean):
                    score += 20

            if score > best_score:
                best_score = score
                best_match = col

        return best_match if best_score > 0 else None

    def _fuzzy_match(self, keyword: str, column: str) -> bool:
        """模糊匹配"""
        # 移除標點符號和空白
        keyword_clean = re.sub(r'[^\w]', '', keyword)
        column_clean = re.sub(r'[^\w]', '', column)

        # 檢查是否有共同字元
        common_chars = set(keyword_clean) & set(column_clean)
        return len(common_chars) >= min(2, len(keyword_clean) // 2)

    def _classify_sheet_by_content(self, sheet_name: str, sheet_analysis: Dict[str, Any]) -> str:
        """根據內容分類工作表"""
        # 先根據工作表名稱分類
        sheet_name_lower = sheet_name.lower()

        for case_type, keywords in self.case_type_keywords.items():
            if any(keyword in sheet_name_lower for keyword in keywords):
                return case_type

        # 如果名稱無法判斷，根據欄位內容分析
        columns = sheet_analysis.get('columns', [])
        column_text = ' '.join(str(col).lower() for col in columns)

        for case_type, keywords in self.case_type_keywords.items():
            if any(keyword in column_text for keyword in keywords):
                return case_type

        return 'unknown'

    def _analyze_data_quality(self, df: pd.DataFrame) -> Dict[str, Any]:
        """分析資料品質"""
        quality_info = {
            'total_rows': len(df),
            'non_empty_rows': 0,
            'columns_info': {},
            'quality_score': 0
        }

        # 分析每個欄位
        for col in df.columns:
            non_null_count = df[col].notna().sum()
            null_count = df[col].isna().sum()

            quality_info['columns_info'][col] = {
                'non_null_count': non_null_count,
                'null_count': null_count,
                'fill_rate': non_null_count / len(df) if len(df) > 0 else 0,
                'unique_count': df[col].nunique(),
                'data_type': str(df[col].dtype)
            }

        # 計算非空行數
        quality_info['non_empty_rows'] = len(df.dropna(how='all'))

        # 計算品質分數（0-100）
        if len(df) > 0:
            avg_fill_rate = sum(info['fill_rate'] for info in quality_info['columns_info'].values()) / len(quality_info['columns_info'])
            quality_info['quality_score'] = round(avg_fill_rate * 100, 2)

        return quality_info

    def _analyze_case_number_merge_needs(self, columns: List[str]) -> Dict[str, Any]:
        """分析案號欄位合併需求"""
        case_number_related = []

        for col in columns:
            col_clean = str(col).strip().lower()
            if any(keyword in col_clean for keyword in ['案號', '機關', '號碼', '字號']):
                case_number_related.append(col)

        needs_merge = len(case_number_related) > 1

        return {
            'needs_merge': needs_merge,
            'case_number_fields': case_number_related,
            'merge_separator': '-' if needs_merge else '',
            'merge_description': f"發現 {len(case_number_related)} 個案號相關欄位，建議合併" if needs_merge else "單一案號欄位"
        }

    def _estimate_valid_data_count(self, df: pd.DataFrame, column_mapping: Dict[str, str]) -> int:
        """預估有效資料筆數"""
        if not column_mapping.get('client'):
            return 0

        client_column = column_mapping['client']
        if client_column not in df.columns:
            return 0

        # 計算當事人欄位中有效資料的行數
        valid_count = df[client_column].notna().sum()
        return int(valid_count)

    def _extract_cases_from_sheet(
        self,
        file_path: str,
        sheet_name: str,
        case_type: str,
        sheet_analysis: Dict[str, Any]
    ) -> List[CaseData]:
        """從工作表提取案件資料"""
        try:
            # 讀取工作表資料
            df = self.reader.read_sheet_data(file_path, sheet_name)
            if df is None or df.empty:
                return []

            column_mapping = sheet_analysis['column_mapping']
            merge_info = sheet_analysis['merge_analysis']

            if not column_mapping.get('client'):
                print(f"      找不到當事人欄位")
                return []

            cases = []
            processed_rows = 0

            for index, row in df.iterrows():
                try:
                    # 提取基本資料
                    case_data = {
                        'case_type': case_type,
                        'client': self._safe_extract_value(row, column_mapping.get('client')),
                        'case_id': self._safe_extract_value(row, column_mapping.get('case_id')),
                        'case_reason': self._safe_extract_value(row, column_mapping.get('case_reason')),
                        'lawyer': self._safe_extract_value(row, column_mapping.get('lawyer')),
                        'legal_affairs': self._safe_extract_value(row, column_mapping.get('legal_affairs')),
                        'opposing_party': self._safe_extract_value(row, column_mapping.get('opposing_party')),
                        'court': self._safe_extract_value(row, column_mapping.get('court')),
                        'division': self._safe_extract_value(row, column_mapping.get('division'))
                    }

                    # 處理案號合併
                    if merge_info['needs_merge']:
                        case_number_parts = []
                        for field in merge_info['case_number_fields']:
                            part = self._safe_extract_value(row, field)
                            if part:
                                case_number_parts.append(part)
                        case_data['case_number'] = merge_info['merge_separator'].join(case_number_parts) if case_number_parts else None
                    else:
                        case_data['case_number'] = self._safe_extract_value(row, column_mapping.get('case_number'))

                    # 檢查必要欄位
                    if not case_data['client']:
                        processed_rows += 1
                        continue

                    # 建立案件物件
                    case = CaseData(
                        case_type=case_data['case_type'],
                        client=case_data['client'],
                        case_id=case_data['case_id'],
                        case_reason=case_data['case_reason'],
                        case_number=case_data['case_number'],
                        court=case_data['court'],
                        division=case_data['division'],
                        lawyer=case_data['lawyer'],
                        legal_affairs=case_data['legal_affairs'],
                        opposing_party=case_data['opposing_party'],
                        progress='待處理'
                    )

                    cases.append(case)
                    processed_rows += 1

                except Exception as e:
                    print(f"      處理第 {index + 1} 行時發生錯誤: {e}")
                    continue

            return cases

        except Exception as e:
            print(f"❌ 從工作表 {sheet_name} 提取資料失敗: {e}")
            return []

    def _safe_extract_value(self, row, column_name: str) -> Optional[str]:
        """安全提取欄位值並清理"""
        if not column_name:
            return None

        try:
            value = row.get(column_name, None)
            if pd.isna(value):
                return None

            # 使用統一的資料清理工具
            cleaned_value = DataCleaner.clean_text_data(value)
            return cleaned_value

        except Exception:
            return None

    def _generate_analysis_report(
        self,
        file_info: Dict[str, Any],
        sheets_analysis: Dict[str, Any],
        categorized_sheets: Dict[str, List[str]]
    ) -> str:
        """生成分析報告"""
        report_lines = []

        # 檔案基本資訊
        report_lines.append(f"📄 檔案: {file_info['file_path']}")
        report_lines.append(f"📊 工作表總數: {file_info['sheet_count']}")

        # 可處理工作表統計
        processable_count = sum(1 for analysis in sheets_analysis.values() if analysis['success'])
        report_lines.append(f"✅ 可處理工作表: {processable_count}")

        # 案件類型分布
        for case_type, sheets in categorized_sheets.items():
            if sheets and case_type != 'unknown':
                report_lines.append(f"📋 {case_type}工作表 {len(sheets)} 個: {', '.join(sheets)}")

        # 資料品質摘要
        total_valid_cases = 0
        for sheet_name, analysis in sheets_analysis.items():
            if analysis['success']:
                total_valid_cases += analysis.get('valid_data_count', 0)

        report_lines.append(f"📈 預估可匯入案件: {total_valid_cases} 筆")

        return "\n".join(report_lines)