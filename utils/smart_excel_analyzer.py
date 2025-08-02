#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智慧Excel分析器 - 🔥 完整版本
自動識別工作表、標題列和欄位對應，支援智慧合併和靈活匹配
完整實現所有分析和資料提取功能
"""
import os
from typing import Dict, List, Optional, Tuple, Any
from utils.data_cleaner import DataCleaner

# Excel處理相關依賴
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

try:
    import openpyxl
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False

try:
    import xlrd
    XLRD_AVAILABLE = True
except ImportError:
    XLRD_AVAILABLE = False

# 嘗試導入CaseData模型
try:
    from models.case_model import CaseData
    CASE_MODEL_AVAILABLE = True
except ImportError:
    CASE_MODEL_AVAILABLE = False
    print("⚠️ CaseData 模型不可用，將使用字典格式")


class SmartExcelAnalyzer:
    """智慧Excel分析器 - 🔥 完整版本"""

    def __init__(self):
        """初始化分析器"""
        # 🔥 欄位關鍵字對應表 - 根據需求設計
        self.field_keywords = {
            'case_id': ['編號', '案件編號', 'ID', 'id', '序號', '流水號', '案件ID', '案件id'],
            'case_reason': ['案由', '事由', '案件事由', '訴訟事由', '案件原因', '事件類型', '事件', '原因'],
            'case_number': ['案號', '機關', '案件號碼', '機關案號', '法院案號', '案件號', '號碼'],  # 🔥 新增 case_number
            'court': ['法院', '負責法院', '管轄法院', '審理法院', '法庭'],  # 🔥 修改 court 欄位關鍵字
            'client': ['當事人', '客戶', '客戶名稱', '姓名', '委託人', '申請人', '當事者', '名稱'],
            'lawyer': ['委任律師', '律師', '代理律師', '辯護律師', '訴訟代理人', '代表律師', '律師姓名'],
            'legal_affairs': ['法務', '法務人員', '助理', '法務助理', '承辦人', '負責人', '經辦人'],
            'opposing_party': ['對造', '相對人', '被告', '對方當事人', '另一方', '對方'],
            'division': ['股別', '分機']
        }

        # 🔥 案件類型關鍵字
        self.case_type_keywords = {
            '民事': ['民事', '民商', '民', 'civil', 'Civil', 'CIVIL'],
            '刑事': ['刑事', '刑', 'criminal', 'Criminal', 'CRIMINAL']
        }

        # 🔥 標題列識別的最小得分閾值
        self.header_min_score = 2

        # 🔥 合併欄位的分隔符
        self.merge_separator = '-'

    def analyze_excel_comprehensive(self, file_path: str) -> Tuple[bool, str, Dict[str, Any]]:
        """
        🔥 全面分析Excel檔案

        Args:
            file_path: Excel檔案路徑

        Returns:
            Tuple[bool, str, Dict]: (成功狀態, 詳細分析結果, 結構化資料)
        """
        try:
            print(f"🔍 開始分析Excel檔案: {file_path}")

            if not PANDAS_AVAILABLE:
                return False, "pandas 不可用，無法分析 Excel", {}

            # 檢查檔案是否存在
            if not os.path.exists(file_path):
                return False, f"檔案不存在: {file_path}", {}

            # 第1步：取得所有工作表
            print("📋 步驟1: 讀取工作表...")
            sheets_info = self._get_all_sheets(file_path)
            if not sheets_info['success']:
                return False, sheets_info['message'], {}

            print(f"✅ 找到 {sheets_info['total_sheets']} 個工作表")

            # 第2步：分析每個工作表的案件類型
            print("🏷️ 步驟2: 分類工作表...")
            categorized_sheets = self._categorize_sheets_by_case_type(sheets_info['sheets'])

            civil_count = len(categorized_sheets['民事'])
            criminal_count = len(categorized_sheets['刑事'])
            unknown_count = len(categorized_sheets['unknown'])

            print(f"✅ 分類完成: 民事{civil_count}個, 刑事{criminal_count}個, 未識別{unknown_count}個")

            # 第3步：分析每個相關工作表的欄位結構
            print("🔍 步驟3: 分析欄位結構...")
            sheets_analysis = {}
            total_analyzed = 0

            for case_type, sheet_names in categorized_sheets.items():
                if case_type in ['民事', '刑事'] and sheet_names:
                    for sheet_name in sheet_names:
                        print(f"  分析工作表: {sheet_name}")
                        analysis = self._analyze_sheet_structure(file_path, sheet_name, case_type)
                        if analysis['success']:
                            sheets_analysis[sheet_name] = analysis
                            total_analyzed += 1
                            print(f"  ✅ {sheet_name}: 找到{analysis['required_fields_found']}個欄位, {analysis['data_rows']}行資料")
                        else:
                            print(f"  ❌ {sheet_name}: {analysis['message']}")

            print(f"✅ 結構分析完成: {total_analyzed}個工作表可處理")

            # 第4步：生成分析報告
            print("📊 步驟4: 生成分析報告...")
            analysis_report = self._generate_analysis_report(categorized_sheets, sheets_analysis)

            result = {
                'categorized_sheets': categorized_sheets,
                'sheets_analysis': sheets_analysis,
                'total_processable_sheets': len(sheets_analysis),
                'analysis_report': analysis_report,
                'file_path': file_path,
                'engine': sheets_info.get('engine', 'auto')
            }

            print("✅ 分析完成!")
            return True, analysis_report, result

        except Exception as e:
            error_msg = f"分析過程發生錯誤：{str(e)}"
            print(f"❌ {error_msg}")
            import traceback
            traceback.print_exc()
            return False, error_msg, {}

    def _get_all_sheets(self, file_path: str) -> Dict[str, Any]:
        """取得Excel檔案中的所有工作表"""
        try:
            engine = self._get_best_engine(file_path)
            if not engine:
                return {'success': False, 'message': '無可用的Excel讀取引擎'}

            print(f"  使用引擎: {engine}")

            if engine == 'openpyxl':
                excel_file = pd.ExcelFile(file_path, engine='openpyxl')
            elif engine == 'xlrd':
                excel_file = pd.ExcelFile(file_path, engine='xlrd')
            else:
                excel_file = pd.ExcelFile(file_path)

            sheets = excel_file.sheet_names
            if not sheets:
                return {'success': False, 'message': 'Excel檔案中沒有工作表'}

            return {
                'success': True,
                'sheets': sheets,
                'total_sheets': len(sheets),
                'engine': engine
            }

        except Exception as e:
            return {'success': False, 'message': f'讀取Excel檔案失敗：{str(e)}'}

    def _categorize_sheets_by_case_type(self, sheet_names: List[str]) -> Dict[str, List[str]]:
        """🔥 根據案件類型分類工作表"""
        categorized = {
            '民事': [],
            '刑事': [],
            'unknown': []
        }

        for sheet_name in sheet_names:
            classified = False
            sheet_name_clean = str(sheet_name).strip()

            # 檢查民事關鍵字
            for keyword in self.case_type_keywords['民事']:
                if keyword in sheet_name_clean:
                    categorized['民事'].append(sheet_name)
                    classified = True
                    print(f"  📝 {sheet_name} → 民事 (匹配: {keyword})")
                    break

            # 如果還沒分類，檢查刑事關鍵字
            if not classified:
                for keyword in self.case_type_keywords['刑事']:
                    if keyword in sheet_name_clean:
                        categorized['刑事'].append(sheet_name)
                        classified = True
                        print(f"  ⚖️ {sheet_name} → 刑事 (匹配: {keyword})")
                        break

            # 如果都沒匹配，歸類為未知
            if not classified:
                categorized['unknown'].append(sheet_name)
                print(f"  ❓ {sheet_name} → 未識別")

        return categorized

    def _analyze_sheet_structure(self, file_path: str, sheet_name: str, case_type: str) -> Dict[str, Any]:
        """🔥 分析單一工作表的結構"""
        try:
            engine = self._get_best_engine(file_path)

            # 先讀取工作表的前幾行來尋找標題列
            print(f"    讀取工作表: {sheet_name}")
            if engine == 'openpyxl':
                df_preview = pd.read_excel(file_path, sheet_name=sheet_name,
                                         engine='openpyxl', nrows=15, header=None)
            elif engine == 'xlrd':
                df_preview = pd.read_excel(file_path, sheet_name=sheet_name,
                                         engine='xlrd', nrows=15, header=None)
            else:
                df_preview = pd.read_excel(file_path, sheet_name=sheet_name,
                                         nrows=15, header=None)

            if df_preview.empty:
                return {'success': False, 'message': f'工作表 {sheet_name} 是空的'}

            # 🔥 智慧尋找標題列
            print(f"    尋找標題列...")
            header_row = self._find_header_row(df_preview)
            if header_row is None:
                return {'success': False, 'message': f'工作表 {sheet_name} 找不到標題列'}

            print(f"    標題列位置: 第 {header_row + 1} 行")

            # 使用找到的標題列重新讀取完整資料
            if engine == 'openpyxl':
                df = pd.read_excel(file_path, sheet_name=sheet_name,
                                 header=header_row, engine='openpyxl')
            elif engine == 'xlrd':
                df = pd.read_excel(file_path, sheet_name=sheet_name,
                                 header=header_row, engine='xlrd')
            else:
                df = pd.read_excel(file_path, sheet_name=sheet_name, header=header_row)

            # 🔥 智慧欄位對應
            print(f"    分析欄位對應...")
            column_mapping = self._smart_column_mapping(df.columns.tolist())

            # 統計找到的欄位
            found_fields = sum(1 for v in column_mapping.values() if v is not None)
            print(f"    找到欄位: {found_fields}/{len(self.field_keywords)}")

            # 🔥 檢查合併欄位需求 (案號相關)
            merge_info = self._check_merge_requirements(df.columns.tolist())
            if merge_info['needs_merge']:
                print(f"    需要合併欄位: {', '.join(merge_info['case_number_fields'])}")

            # 統計資料行數
            data_rows = len(df.dropna(how='all'))  # 排除完全空白的行
            print(f"    資料行數: {data_rows}")

            return {
                'success': True,
                'case_type': case_type,
                'header_row': header_row,
                'column_mapping': column_mapping,
                'merge_info': merge_info,
                'total_columns': len(df.columns),
                'data_rows': data_rows,
                'columns': df.columns.tolist(),
                'required_fields_found': found_fields,
                'has_client_field': column_mapping.get('client') is not None,
                'sample_data': df.head(3).to_dict('records') if data_rows > 0 else []  # 保存樣本資料
            }

        except Exception as e:
            return {'success': False, 'message': f'分析工作表 {sheet_name} 失敗：{str(e)}'}

    def _find_header_row(self, df: pd.DataFrame) -> Optional[int]:
        """🔥 智慧尋找標題列位置"""
        max_rows_to_check = min(10, len(df))

        best_row = 0
        best_score = 0

        print(f"      檢查前 {max_rows_to_check} 行...")

        for row_idx in range(max_rows_to_check):
            score = 0
            matched_keywords = []

            if row_idx >= len(df):
                break

            row_data = df.iloc[row_idx]

            # 計算該行包含多少個可能的欄位關鍵字
            for cell_value in row_data:
                if pd.notna(cell_value):
                    cell_text = str(cell_value).strip()

                    # 檢查是否包含任何欄位關鍵字
                    for field_name, field_keywords in self.field_keywords.items():
                        for keyword in field_keywords:
                            if keyword in cell_text:
                                score += 1
                                matched_keywords.append(f"{keyword}({field_name})")
                                break  # 找到一個就跳出

            print(f"      第 {row_idx + 1} 行: 得分 {score}, 匹配: {', '.join(matched_keywords[:3])}")

            # 如果這一行的得分更高，更新最佳標題列
            if score > best_score:
                best_score = score
                best_row = row_idx

        # 如果得分太低，可能沒有找到合適的標題列
        if best_score < self.header_min_score:
            print(f"      ❌ 最高得分 {best_score} 低於閾值 {self.header_min_score}")
            return None

        print(f"      ✅ 選擇第 {best_row + 1} 行 (得分: {best_score})")
        return best_row

    def _smart_column_mapping(self, columns: List[str]) -> Dict[str, Optional[str]]:
        """🔥 智慧欄位對應"""
        mapping = {field: None for field in self.field_keywords.keys()}

        print(f"      可用欄位: {', '.join(str(col) for col in columns)}")

        for field, keywords in self.field_keywords.items():
            best_match = None
            best_score = 0

            for col in columns:
                if pd.notna(col):
                    col_text = str(col).strip()

                    # 計算匹配得分
                    score = 0
                    matched_keyword = None

                    for keyword in keywords:
                        if keyword in col_text:
                            # 完全匹配得分更高
                            if keyword == col_text:
                                score += 10
                                matched_keyword = keyword
                            else:
                                score += 1
                                if not matched_keyword:  # 記錄第一個匹配的關鍵字
                                    matched_keyword = keyword

                    if score > best_score:
                        best_score = score
                        best_match = col

            if best_match:
                mapping[field] = best_match
                print(f"      ✅ {self._get_field_display_name(field)}: 「{best_match}」")
            else:
                print(f"      ❌ {self._get_field_display_name(field)}: 未找到")

        return mapping

    def _check_merge_requirements(self, columns: List[str]) -> Dict[str, Any]:
        """🔥 檢查需要合併的欄位（主要針對案號相關）"""
        merge_info = {
            'case_number_fields': [],
            'needs_merge': False,
            'merge_separator': self.merge_separator
        }

        # 🔥 修正：使用正確的案號關鍵字
        case_number_keywords = self.field_keywords['case_number']  # 原本是 case_number

        for col in columns:
            if pd.notna(col):
                col_text = str(col).strip()
                for keyword in case_number_keywords:
                    if keyword in col_text:
                        merge_info['case_number_fields'].append(col)
                        break

        # 如果找到多個案號相關欄位，標記需要合併
        if len(merge_info['case_number_fields']) > 1:
            merge_info['needs_merge'] = True

        return merge_info

    def _generate_analysis_report(self, categorized_sheets: Dict[str, List[str]],
                                 sheets_analysis: Dict[str, Dict]) -> str:
        """🔥 生成詳細的分析報告"""
        lines = []

        # 工作表分類統計
        lines.append('📋 工作表分類結果：')
        for case_type, sheets in categorized_sheets.items():
            if sheets:
                if case_type == '民事':
                    lines.append(f'  📝 民事工作表 ({len(sheets)} 個)：')
                elif case_type == '刑事':
                    lines.append(f'  ⚖️ 刑事工作表 ({len(sheets)} 個)：')

        # 詳細欄位分析
        if sheets_analysis:
            lines.append('')

            for sheet_name, analysis in sheets_analysis.items():
                lines.append(f'📄 工作表：{sheet_name}')
                lines.append(f'   案件類型：{analysis["case_type"]}')
                lines.append(f'   資料行數：{analysis["data_rows"]} 行')

        else:
            lines.append('⚠️ 沒有找到可處理的工作表')


        return '\n'.join(lines)

    def _get_field_display_name(self, field: str) -> str:
        """取得欄位的顯示名稱"""
        display_names = {
            'case_id': '案件編號',
            'case_reason': '案由',
            'case_number': '案號',  # 🔥 新增
            'court': '法院',        # 🔥 修改顯示名稱
            'client': '當事人',
            'lawyer': '委任律師',
            'legal_affairs': '法務',
            'opposing_party': '對造',
            'division': '股別'
        }
        return display_names.get(field, field)

    def extract_data_from_analysis(self, file_path: str, analysis_result: Dict[str, Any]) -> Tuple[bool, str, Dict[str, List]]:
        """🔥 根據分析結果提取實際資料"""
        try:
            print(f"🚀 開始提取資料: {file_path}")

            all_cases = {'民事': [], '刑事': []}
            import_summary = []

            sheets_analysis = analysis_result.get('sheets_analysis', {})

            if not sheets_analysis:
                return False, "沒有可用的工作表分析結果", all_cases

            # 🔥 修正：儲存分析結果供後續使用
            self._current_analysis_result = analysis_result

            for sheet_name, analysis in sheets_analysis.items():
                if not analysis.get('success', False):
                    continue

                if not analysis.get('has_client_field', False):
                    import_summary.append(f'「{sheet_name}」: 跳過 - 缺少當事人欄位')
                    continue

                case_type = analysis['case_type']
                column_mapping = analysis['column_mapping']
                merge_info = analysis['merge_info']

                print(f"  處理工作表: {sheet_name} ({case_type})")
                print(f"    欄位對應: {[(k, v) for k, v in column_mapping.items() if v]}")

                # 從工作表提取資料
                cases = self._extract_cases_from_sheet(
                    file_path, sheet_name, case_type, column_mapping, merge_info
                )

                if cases:
                    all_cases[case_type].extend(cases)
                    import_summary.append(f'「{sheet_name}」: {len(cases)} 筆{case_type}案件')
                    print(f"    ✅ 提取了 {len(cases)} 筆資料")
                else:
                    import_summary.append(f'「{sheet_name}」: 沒有有效資料')
                    print(f"    ❌ 沒有提取到有效資料")

            # 清理臨時變數
            if hasattr(self, '_current_analysis_result'):
                delattr(self, '_current_analysis_result')

            # 統計結果
            total_civil = len(all_cases['民事'])
            total_criminal = len(all_cases['刑事'])
            total_all = total_civil + total_criminal

            if total_all == 0:
                return False, "沒有成功提取任何案件資料", all_cases

            # 生成結果訊息
            summary_msg = f"✅ 智慧匯入完成！共 {total_all} 筆案件\n"
            if total_civil > 0:
                summary_msg += f"📋 民事案件: {total_civil} 筆\n"
            if total_criminal > 0:
                summary_msg += f"⚖️ 刑事案件: {total_criminal} 筆\n"

            summary_msg += "\n📊 詳細結果:\n" + "\n".join(import_summary)

            print(f"✅ 資料提取完成: 共 {total_all} 筆")
            return True, summary_msg, all_cases

        except Exception as e:
            error_msg = f"資料提取過程發生錯誤：{str(e)}"
            print(f"❌ {error_msg}")
            import traceback
            traceback.print_exc()
            return False, error_msg, {'民事': [], '刑事': []}

    def _extract_cases_from_sheet(self, file_path: str, sheet_name: str, case_type: str,
                                 column_mapping: Dict[str, Optional[str]],
                                 merge_info: Dict[str, Any]) -> List:
        """從單一工作表提取案件資料"""
        try:
            engine = self._get_best_engine(file_path)

            # 🔥 修正：需要從分析結果中取得正確的標題列位置
            header_row = 0  # 預設值

            # 如果有儲存的分析結果，使用正確的標題列
            if hasattr(self, '_current_analysis_result'):
                for sheet_analysis in self._current_analysis_result.get('sheets_analysis', {}).values():
                    if sheet_analysis.get('case_type') == case_type:
                        header_row = sheet_analysis.get('header_row', 0)
                        break

            print(f"    使用標題列位置: 第 {header_row + 1} 行")

            # 🔥 關鍵修正：使用正確的標題列位置讀取資料
            if engine == 'openpyxl':
                df = pd.read_excel(file_path, sheet_name=sheet_name,
                                 header=header_row, engine='openpyxl')
            elif engine == 'xlrd':
                df = pd.read_excel(file_path, sheet_name=sheet_name,
                                 header=header_row, engine='xlrd')
            else:
                df = pd.read_excel(file_path, sheet_name=sheet_name, header=header_row)

            if df.empty:
                print(f"    工作表 {sheet_name} 讀取後為空")
                return []

            print(f"    實際讀取到 {len(df)} 行資料")
            print(f"    欄位名稱: {list(df.columns)}")

            cases = []
            processed_rows = 0

            for index, row in df.iterrows():
                try:
                    # 🔥 智慧提取各欄位資料 - 確保包含 court 和 case_number
                    case_data = {
                        'case_type': case_type,
                        'client': self._safe_extract_value(row, column_mapping.get('client')),
                        'case_id': self._safe_extract_value(row, column_mapping.get('case_id')),
                        'case_reason': self._safe_extract_value(row, column_mapping.get('case_reason')),
                        'lawyer': self._safe_extract_value(row, column_mapping.get('lawyer')),
                        'legal_affairs': self._safe_extract_value(row, column_mapping.get('legal_affairs')),
                        'opposing_party': self._safe_extract_value(row, column_mapping.get('opposing_party')),
                        'court': self._safe_extract_value(row, column_mapping.get('court')),  # 🔥 確保提取 court
                        'division': self._safe_extract_value(row, column_mapping.get('division'))
                    }

                    # 🔥 處理案號合併
                    if merge_info['needs_merge']:
                        case_number_parts = []
                        for field in merge_info['case_number_fields']:
                            part = self._safe_extract_value(row, field)
                            if part:
                                case_number_parts.append(part)
                        case_data['case_number'] = merge_info['merge_separator'].join(case_number_parts) if case_number_parts else None
                    else:
                        case_data['case_number'] = self._safe_extract_value(row, column_mapping.get('case_number'))


                    # 🔥 調試：顯示提取的資料
                    if processed_rows < 3:  # 只顯示前3筆用於調試
                        print(f"    第 {processed_rows + 1} 筆資料: 當事人='{case_data['client']}', 案由='{case_data['case_reason']}'")

                    # 檢查必要欄位
                    if not case_data['client']:  # 當事人是必要欄位
                        if processed_rows < 3:
                            print(f"      ❌ 跳過：沒有當事人資料")
                        processed_rows += 1
                        continue

                     # 建立案件物件時確保包含所有欄位
                    if CASE_MODEL_AVAILABLE:
                        case = CaseData(
                            case_type=case_data['case_type'],
                            client=case_data['client'],
                            case_id=case_data['case_id'],
                            case_reason=case_data['case_reason'],
                            case_number=case_data['case_number'],  # 🔥 確保傳入 case_number
                            court=case_data['court'],              # 🔥 確保傳入 court
                            division=case_data['division'],
                            lawyer=case_data['lawyer'],
                            legal_affairs=case_data['legal_affairs'],
                            opposing_party=case_data['opposing_party'],
                            progress='待處理'
                        )
                    else:
                        case = case_data
                        case['progress'] = '待處理'

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
        """
        安全提取欄位值 - 🔥 修改版本，增加資料清理
        """
        if not column_name:
            return None

        try:
            value = row.get(column_name, None)
            if pd.isna(value):
                return None

            # 🔥 新增：使用統一的資料清理工具
            cleaned_value = DataCleaner.clean_text_data(value)
            return cleaned_value

        except Exception as e:
            return None

    def _get_best_engine(self, file_path: str) -> Optional[str]:
        """根據檔案格式選擇最佳引擎"""
        file_ext = os.path.splitext(file_path)[1].lower()

        if file_ext == '.xlsx':
            if OPENPYXL_AVAILABLE:
                return 'openpyxl'
            elif XLRD_AVAILABLE:
                return 'xlrd'
        elif file_ext == '.xls':
            if XLRD_AVAILABLE:
                return 'xlrd'
            elif OPENPYXL_AVAILABLE:
                return 'openpyxl'

        return None

    def validate_analysis_result(self, analysis_result: Dict[str, Any]) -> Tuple[bool, str]:
        """驗證分析結果的有效性"""
        try:
            if not analysis_result:
                return False, "分析結果為空"

            sheets_analysis = analysis_result.get('sheets_analysis', {})
            if not sheets_analysis:
                return False, "沒有找到可處理的工作表"

            processable_count = 0
            for sheet_name, analysis in sheets_analysis.items():
                if analysis.get('success') and analysis.get('has_client_field'):
                    processable_count += 1

            if processable_count == 0:
                return False, "沒有找到包含必要欄位（當事人）的工作表"

            return True, f"驗證通過，找到 {processable_count} 個可處理的工作表"

        except Exception as e:
            return False, f"驗證過程發生錯誤：{str(e)}"

    def get_supported_fields(self) -> Dict[str, List[str]]:
        """取得支援的欄位及其關鍵字"""
        return self.field_keywords.copy()

    def get_supported_case_types(self) -> Dict[str, List[str]]:
        """取得支援的案件類型及其關鍵字"""
        return self.case_type_keywords.copy()

    def add_field_keyword(self, field: str, keyword: str) -> bool:
        """新增欄位關鍵字"""
        try:
            if field not in self.field_keywords:
                self.field_keywords[field] = []

            if keyword not in self.field_keywords[field]:
                self.field_keywords[field].append(keyword)
                return True
            return False
        except Exception as e:
            print(f"新增欄位關鍵字失敗: {e}")
            return False

    def add_case_type_keyword(self, case_type: str, keyword: str) -> bool:
        """新增案件類型關鍵字"""
        try:
            if case_type not in self.case_type_keywords:
                self.case_type_keywords[case_type] = []

            if keyword not in self.case_type_keywords[case_type]:
                self.case_type_keywords[case_type].append(keyword)
                return True
            return False
        except Exception as e:
            print(f"新增案件類型關鍵字失敗: {e}")
            return False

    def export_configuration(self) -> Dict[str, Any]:
        """匯出當前配置"""
        return {
            'field_keywords': self.field_keywords,
            'case_type_keywords': self.case_type_keywords,
            'header_min_score': self.header_min_score,
            'merge_separator': self.merge_separator
        }

    def import_configuration(self, config: Dict[str, Any]) -> bool:
        """匯入配置"""
        try:
            if 'field_keywords' in config:
                self.field_keywords = config['field_keywords']

            if 'case_type_keywords' in config:
                self.case_type_keywords = config['case_type_keywords']

            if 'header_min_score' in config:
                self.header_min_score = config['header_min_score']

            if 'merge_separator' in config:
                self.merge_separator = config['merge_separator']

            return True
        except Exception as e:
            print(f"匯入配置失敗: {e}")
            return False
