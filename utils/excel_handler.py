#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Excel處理模組 - 橋接版本
為了向後相容，將調用轉發到新模組
同時提供備用方案確保系統穩定運行
"""

import os


# 🔄 嘗試載入新模組
try:
    from .excel import ExcelHandler as NewExcelHandler
    from .excel import ExcelReader, ExcelWriter, ExcelAnalyzer, ExcelValidator

    # 使用新模組
    ExcelHandler = NewExcelHandler

    print("✅ 使用新版Excel處理模組")
    NEW_MODULE_AVAILABLE = True

except ImportError as e:
    print(f"⚠️ 新模組載入失敗，使用備用方案: {e}")
    NEW_MODULE_AVAILABLE = False

    # 🔄 備用方案：基本的ExcelHandler類別
    try:
        import pandas as pd
        PANDAS_AVAILABLE = True
    except ImportError:
        PANDAS_AVAILABLE = False
        print("❌ pandas 不可用，Excel功能將受限")

    try:
        import openpyxl
        OPENPYXL_AVAILABLE = True
    except ImportError:
        OPENPYXL_AVAILABLE = False
        print("❌ openpyxl 不可用，無法處理.xlsx檔案")

    from typing import List, Dict, Optional, Tuple, Any

    class ExcelHandler:
        """基本的Excel處理類別 - 備用方案"""

        @staticmethod
        def check_dependencies() -> Dict[str, bool]:
            """檢查依賴狀態"""
            return {
                'pandas': PANDAS_AVAILABLE,
                'openpyxl': OPENPYXL_AVAILABLE,
                'new_module': NEW_MODULE_AVAILABLE
            }

        @staticmethod
        def analyze_excel_sheets(file_path: str) -> Tuple[bool, str, Dict[str, List[str]]]:
            """分析Excel工作表 - 備用版本"""
            if not PANDAS_AVAILABLE:
                return False, "pandas 不可用，無法分析Excel", {}

            try:
                if not os.path.exists(file_path):
                    return False, "檔案不存在", {}

                # 基本分析
                try:
                    if OPENPYXL_AVAILABLE:
                        excel_file = pd.ExcelFile(file_path, engine='openpyxl')
                    else:
                        excel_file = pd.ExcelFile(file_path)
                except Exception as e:
                    return False, f"無法開啟Excel檔案: {str(e)}", {}

                sheet_names = excel_file.sheet_names

                if not sheet_names:
                    return False, "Excel檔案中沒有工作表", {}

                # 簡單分類邏輯
                categorized = {
                    '民事': [],
                    '刑事': [],
                    'unknown': []
                }

                for name in sheet_names:
                    name_lower = name.lower()
                    if '民事' in name or '民' in name or 'civil' in name_lower:
                        categorized['民事'].append(name)
                    elif '刑事' in name or '刑' in name or 'criminal' in name_lower:
                        categorized['刑事'].append(name)
                    else:
                        categorized['unknown'].append(name)

                message = f"📋 找到 {len(sheet_names)} 個工作表\n"
                for category, sheets in categorized.items():
                    if sheets:
                        message += f"  {category}: {len(sheets)} 個\n"

                return True, message.strip(), categorized

            except Exception as e:
                return False, f"分析Excel檔案失敗: {str(e)}", {}

        @staticmethod
        def import_cases_from_multiple_sheets(file_path: str,
                                            sheets_to_import: Dict[str, List[str]]) -> Tuple[bool, str, Dict[str, List]]:
            """從多個工作表匯入案件 - 備用版本"""
            if not PANDAS_AVAILABLE:
                return False, "pandas 不可用，無法匯入Excel", {}

            try:
                all_cases = {}
                import_messages = []

                for case_type, sheet_names in sheets_to_import.items():
                    type_cases = []

                    for sheet_name in sheet_names:
                        try:
                            # 讀取工作表
                            if OPENPYXL_AVAILABLE:
                                df = pd.read_excel(file_path, sheet_name=sheet_name, engine='openpyxl')
                            else:
                                df = pd.read_excel(file_path, sheet_name=sheet_name)

                            if df is not None and not df.empty:
                                # 基本資料處理
                                cases = ExcelHandler._convert_df_to_cases(df, case_type)
                                type_cases.extend(cases)
                                import_messages.append(f"從 {sheet_name} 匯入 {len(cases)} 筆案件")
                            else:
                                import_messages.append(f"工作表 {sheet_name} 無資料")

                        except Exception as e:
                            import_messages.append(f"讀取工作表 {sheet_name} 失敗: {str(e)}")
                            continue

                    if type_cases:
                        all_cases[case_type] = type_cases

                success = len(all_cases) > 0
                total_imported = sum(len(cases) for cases in all_cases.values())

                if success:
                    message = f"✅ 成功匯入 {total_imported} 筆案件\n" + "\n".join(import_messages)
                else:
                    message = "❌ 沒有匯入任何案件\n" + "\n".join(import_messages)

                return success, message, all_cases

            except Exception as e:
                return False, f"匯入案件失敗: {str(e)}", {}

        @staticmethod
        def import_cases_by_category(file_path: str) -> Tuple[bool, str, Dict[str, List]]:
            """按類別匯入案件 - 備用版本"""
            try:
                # 先分析工作表
                analyze_success, analyze_message, categorized_sheets = ExcelHandler.analyze_excel_sheets(file_path)

                if not analyze_success:
                    return False, analyze_message, {}

                # 準備匯入的工作表
                sheets_to_import = {}
                for category, sheets in categorized_sheets.items():
                    if category != 'unknown' and sheets:
                        sheets_to_import[category] = sheets

                if not sheets_to_import:
                    return False, "沒有找到民事或刑事相關的工作表", {}

                # 執行匯入
                return ExcelHandler.import_cases_from_multiple_sheets(file_path, sheets_to_import)

            except Exception as e:
                return False, f"按類別匯入失敗: {str(e)}", {}

        @staticmethod
        def export_cases_to_excel(cases: List, file_path: str) -> bool:
            """匯出案件到Excel - 備用版本"""
            if not PANDAS_AVAILABLE:
                print("❌ pandas 不可用，無法匯出Excel")
                return False

            try:
                if not cases:
                    print("⚠️ 沒有案件資料需要匯出")
                    return False

                # 準備資料
                data = []
                for case in cases:
                    case_data = {
                        '案件編號': getattr(case, 'case_id', '') or '',
                        '案件類型': getattr(case, 'case_type', '') or '',
                        '當事人': getattr(case, 'client', '') or '',
                        '案由': getattr(case, 'case_reason', '') or '',
                        '案號': getattr(case, 'case_number', '') or '',
                        '負責法院': getattr(case, 'court', '') or '',
                        '負責股別': getattr(case, 'division', '') or '',
                        '對造': getattr(case, 'opposing_party', '') or '',
                        '委任律師': getattr(case, 'lawyer', '') or '',
                        '法務': getattr(case, 'legal_affairs', '') or '',
                        '進度追蹤': getattr(case, 'progress', '') or '待處理'
                    }
                    data.append(case_data)

                # 建立DataFrame並匯出
                df = pd.DataFrame(data)

                # 確保目錄存在
                os.makedirs(os.path.dirname(file_path), exist_ok=True)

                # 匯出Excel
                if OPENPYXL_AVAILABLE:
                    df.to_excel(file_path, index=False, engine='openpyxl')
                else:
                    df.to_excel(file_path, index=False)

                print(f"✅ 成功匯出 {len(cases)} 筆案件到 {file_path}")
                return True

            except Exception as e:
                print(f"❌ 匯出Excel失敗: {e}")
                return False

        @staticmethod
        def import_cases_from_excel(file_path: str) -> Optional[List]:
            """從Excel匯入案件 - 備用版本"""
            try:
                success, message, categorized_cases = ExcelHandler.import_cases_by_category(file_path)

                if not success:
                    print(f"匯入失敗: {message}")
                    return None

                # 合併所有類別的案件
                all_cases = []
                for cases in categorized_cases.values():
                    all_cases.extend(cases)

                return all_cases if all_cases else None

            except Exception as e:
                print(f"匯入Excel檔案失敗: {e}")
                return None

        @staticmethod
        def _convert_df_to_cases(df: pd.DataFrame, case_type: str) -> List:
            """將DataFrame轉換為案件物件 - 簡化版本"""
            try:
                # 嘗試導入案件模型
                try:
                    from models.case_model import CaseData
                except ImportError:
                    print("⚠️ 無法導入CaseData模型，建立簡單替代")

                    # 簡單的案件資料類別
                    class CaseData:
                        def __init__(self, **kwargs):
                            for key, value in kwargs.items():
                                setattr(self, key, value)

                cases = []

                # 簡單的欄位對應邏輯
                field_mapping = {}

                for col in df.columns:
                    col_str = str(col).strip()
                    if any(keyword in col_str for keyword in ['當事人', '客戶', '委託人', '姓名']):
                        field_mapping['client'] = col
                    elif any(keyword in col_str for keyword in ['案由', '事由']):
                        field_mapping['case_reason'] = col
                    elif any(keyword in col_str for keyword in ['案號', '機關案號', '法院案號']):
                        field_mapping['case_number'] = col
                    elif any(keyword in col_str for keyword in ['法院', '負責法院']):
                        field_mapping['court'] = col
                    elif any(keyword in col_str for keyword in ['股別', '負責股別']):
                        field_mapping['division'] = col
                    elif any(keyword in col_str for keyword in ['對造']):
                        field_mapping['opposing_party'] = col
                    elif any(keyword in col_str for keyword in ['律師', '委任律師']):
                        field_mapping['lawyer'] = col
                    elif any(keyword in col_str for keyword in ['法務']):
                        field_mapping['legal_affairs'] = col
                    elif any(keyword in col_str for keyword in ['進度', '狀態']):
                        field_mapping['progress'] = col

                # 檢查是否有當事人欄位
                if 'client' not in field_mapping:
                    print(f"⚠️ 工作表中沒有找到當事人欄位，可用欄位: {list(df.columns)}")
                    return cases

                # 轉換每一列資料
                for index, row in df.iterrows():
                    try:
                        # 取得當事人資料
                        client = ExcelHandler._safe_get_value(row, field_mapping['client'])

                        if not client:
                            continue

                        # 建立案件資料
                        case_data = {
                            'case_type': case_type,
                            'client': client,
                            'progress': '待處理'
                        }

                        # 添加其他欄位
                        for field, col in field_mapping.items():
                            if field != 'client':
                                value = ExcelHandler._safe_get_value(row, col)
                                if value:
                                    case_data[field] = value

                        # 建立案件物件
                        case = CaseData(**case_data)
                        cases.append(case)

                    except Exception as e:
                        print(f"處理第 {index + 1} 列資料時發生錯誤: {e}")
                        continue

                print(f"✅ 成功轉換 {len(cases)} 筆案件資料")
                return cases

            except Exception as e:
                print(f"❌ 轉換案件資料失敗: {e}")
                return []

        @staticmethod
        def _safe_get_value(row, column_name) -> Optional[str]:
            """安全地取得欄位值"""
            try:
                if column_name not in row.index:
                    return None

                value = row[column_name]
                if pd.isna(value):
                    return None

                cleaned = str(value).strip()
                return cleaned if cleaned and cleaned != 'nan' else None

            except Exception:
                return None

        @staticmethod
        def get_dependency_status() -> str:
            """取得依賴狀態說明"""
            deps = ExcelHandler.check_dependencies()

            status_lines = ["📊 Excel 處理依賴狀態 (備用模式):"]

            for dep, available in deps.items():
                status = "✅" if available else "❌"
                status_lines.append(f"  {status} {dep}")

            if not deps['pandas']:
                status_lines.append("\n⚠️ 缺少 pandas，Excel 功能將無法使用")
                status_lines.append("請執行: pip install pandas openpyxl")

            if not deps['new_module']:
                status_lines.append(f"\n⚠️ 新模組不可用，正在使用備用模式")
                status_lines.append("建議檢查新模組檔案是否正確安裝")

            return "\n".join(status_lines)

# 向後相容的匯出
__all__ = ['ExcelHandler']

# 在載入時顯示狀態
if __name__ != "__main__":
    deps = ExcelHandler.check_dependencies()
    if not deps['new_module']:
        print("🔄 Excel處理模組已載入（備用模式）")
    if not deps['pandas']:
        print("❌ 警告：pandas 不可用，Excel功能將受到限制")