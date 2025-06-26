from typing import Dict, List, Optional, Tuple

import pandas as pd
from models.case_model import CaseData


class ExcelHandler:
   """Excel 檔案處理類別"""

   @staticmethod
   def export_cases_to_excel(cases: List[CaseData], file_path: str) -> bool:
       """將案件資料匯出為 Excel 檔案"""
       try:
           data = []
           for case in cases:
               data.append({
                   '案由': getattr(case, 'case_reason', '') or '',
                   '案號': getattr(case, 'case_number', '') or '',
                   '負責法院': getattr(case, 'court', '') or '',
                   '負責股別': getattr(case, 'division', '') or '',
                   '對造': getattr(case, 'opposing_party', '') or '',
               })

           df = pd.DataFrame(data)

           with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
               df.to_excel(writer, sheet_name='案件資料', index=False)

               worksheet = writer.sheets['案件資料']
               for column in worksheet.columns:
                   max_length = 0
                   column_letter = column[0].column_letter

                   for cell in column:
                       try:
                           if len(str(cell.value)) > max_length:
                               max_length = len(str(cell.value))
                       except:
                           pass

                   adjusted_width = min(max_length + 2, 50)
                   worksheet.column_dimensions[column_letter].width = adjusted_width

           return True

       except Exception as e:
           print(f"匯出 Excel 失敗: {e}")
           return False

   @staticmethod
   def import_cases_from_excel(file_path: str) -> Optional[List[CaseData]]:
       """從 Excel 檔案匯入案件資料（原有功能保持不變）"""
       try:
           df = pd.read_excel(file_path)
           cases = []

           for _, row in df.iterrows():
               try:
                   case = CaseData(
                       case_id=str(row.get('案件編號', '')),
                       case_type=str(row.get('案件類型', '')),
                       client=str(row.get('當事人', '')),
                       lawyer=str(row.get('委任律師', '')) if pd.notna(row.get('委任律師')) else None,
                       legal_affairs=str(row.get('法務', '')) if pd.notna(row.get('法務')) else None,
                       progress=str(row.get('進度追蹤', '待處理')),
                       case_reason=str(row.get('案由', '')) if pd.notna(row.get('案由')) else None,
                       case_number=str(row.get('案號', '')) if pd.notna(row.get('案號')) else None,
                       opposing_party=str(row.get('對造', '')) if pd.notna(row.get('對造')) else None,
                       court=str(row.get('負責法院', '')) if pd.notna(row.get('負責法院')) else None,
                       division=str(row.get('負責股別', '')) if pd.notna(row.get('負責股別')) else None
                   )
                   cases.append(case)
               except Exception as e:
                   print(f"處理第 {len(cases) + 1} 筆資料時發生錯誤: {e}")
                   continue

           return cases

       except Exception as e:
           print(f"匯入 Excel 失敗: {e}")
           return None

   @staticmethod
   def analyze_excel_sheets(file_path: str) -> Tuple[bool, str, Dict[str, List[str]]]:
       """
       分析Excel檔案中的工作表，自動識別民事和刑事分頁

       Args:
           file_path: Excel檔案路徑

       Returns:
           Tuple[bool, str, Dict[str, List[str]]]: (成功狀態, 訊息, 分類結果)
           分類結果格式: {'民事': [工作表名稱列表], '刑事': [工作表名稱列表], 'unknown': [未識別的工作表]}
       """
       try:
           excel_file = pd.ExcelFile(file_path)
           sheet_names = excel_file.sheet_names

           if not sheet_names:
               return False, "Excel檔案中沒有找到任何工作表", {}

           # 分類工作表
           categorized_sheets = {
               '民事': [],
               '刑事': [],
               'unknown': []
           }

           for sheet_name in sheet_names:
               sheet_lower = sheet_name.lower()
               if '民事' in sheet_name:
                   categorized_sheets['民事'].append(sheet_name)
               elif '刑事' in sheet_name:
                   categorized_sheets['刑事'].append(sheet_name)
               elif 'civil' in sheet_lower or '民' in sheet_name:
                   categorized_sheets['民事'].append(sheet_name)
               elif 'criminal' in sheet_lower or '刑' in sheet_name:
                   categorized_sheets['刑事'].append(sheet_name)
               else:
                   categorized_sheets['unknown'].append(sheet_name)

           # 建立分析結果訊息
           total_civil = len(categorized_sheets['民事'])
           total_criminal = len(categorized_sheets['刑事'])
           total_unknown = len(categorized_sheets['unknown'])

           if total_civil == 0 and total_criminal == 0:
               message = f"未找到民事或刑事相關的工作表\n所有工作表: {', '.join(sheet_names)}"
               return False, message, categorized_sheets

           message_parts = []
           if total_civil > 0:
               message_parts.append(f"民事工作表 {total_civil} 個: {', '.join(categorized_sheets['民事'])}")
           if total_criminal > 0:
               message_parts.append(f"刑事工作表 {total_criminal} 個: {', '.join(categorized_sheets['刑事'])}")
           if total_unknown > 0:
               message_parts.append(f"未識別工作表 {total_unknown} 個: {', '.join(categorized_sheets['unknown'])}")

           message = "\n".join(message_parts)
           return True, message, categorized_sheets

       except Exception as e:
           return False, f"分析Excel檔案失敗：{str(e)}", {}

   @staticmethod
   def import_cases_from_multiple_sheets(file_path: str, selected_sheets: Dict[str, List[str]]) -> Tuple[bool, str, Dict[str, List[CaseData]]]:
       """
       從多個工作表匯入案件資料

       Args:
           file_path: Excel檔案路徑
           selected_sheets: 選擇的工作表 {'民事': [sheet_names], '刑事': [sheet_names]}

       Returns:
           Tuple[bool, str, Dict[str, List[CaseData]]]: (成功狀態, 訊息, 分類案件資料)
       """
       try:
           all_cases = {'民事': [], '刑事': []}
           import_summary = []

           for case_type, sheet_names in selected_sheets.items():
               if case_type not in ['民事', '刑事'] or not sheet_names:
                   continue

               type_cases = []
               for sheet_name in sheet_names:
                   success, message, cases = ExcelHandler._import_from_single_sheet(file_path, sheet_name, case_type)
                   if success and cases:
                       type_cases.extend(cases)
                       import_summary.append(f"「{sheet_name}」: {len(cases)} 筆")
                   elif not success:
                       import_summary.append(f"「{sheet_name}」: 失敗 - {message}")

               all_cases[case_type] = type_cases

           # 統計總數
           total_civil = len(all_cases['民事'])
           total_criminal = len(all_cases['刑事'])
           total_all = total_civil + total_criminal

           if total_all == 0:
               return False, "沒有成功匯入任何案件資料", all_cases

           # 建立結果訊息
           summary_msg = f"匯入完成！共 {total_all} 筆案件\n"
           if total_civil > 0:
               summary_msg += f"民事案件: {total_civil} 筆\n"
           if total_criminal > 0:
               summary_msg += f"刑事案件: {total_criminal} 筆\n"

           summary_msg += "\n詳細結果:\n" + "\n".join(import_summary)

           return True, summary_msg, all_cases

       except Exception as e:
           return False, f"匯入過程發生錯誤：{str(e)}", {'民事': [], '刑事': []}

   @staticmethod
   def _import_from_single_sheet(file_path: str, sheet_name: str, case_type: str) -> Tuple[bool, str, List[CaseData]]:
       """
       從單一工作表匯入案件資料

       Args:
           file_path: Excel檔案路徑
           sheet_name: 工作表名稱
           case_type: 案件類型

       Returns:
           Tuple[bool, str, List[CaseData]]: (成功狀態, 訊息, 案件列表)
       """
       try:
           # 讀取指定工作表
           df = pd.read_excel(file_path, sheet_name=sheet_name)

           if df.empty:
               return False, f"工作表「{sheet_name}」是空的", []

           # 建立欄位對應字典
           column_mapping = ExcelHandler._create_column_mapping(df.columns.tolist())

           if not column_mapping.get('client'):
               return False, "找不到當事人相關欄位", []

           # 解析資料並建立案件列表
           cases = []
           success_count = 0

           for index, row in df.iterrows():
               try:
                   # 檢查當事人欄位是否有值
                   client_value = str(row.get(column_mapping['client'], '')).strip()
                   if not client_value or client_value.lower() in ['nan', 'none', '']:
                       continue

                   # 建立CaseData物件
                   case = CaseData(
                       case_id='',  # 將在controller中自動產生
                       case_type=case_type,
                       client=client_value,
                       lawyer=None,
                       legal_affairs=None,
                       progress='待處理',
                       case_reason=ExcelHandler._safe_get_value(row, column_mapping.get('case_reason')),
                       case_number=ExcelHandler._safe_get_value(row, column_mapping.get('case_number')),
                       opposing_party=ExcelHandler._safe_get_value(row, column_mapping.get('opposing_party')),
                       court=None,
                       division=ExcelHandler._safe_get_value(row, column_mapping.get('division')),
                       progress_date=None
                   )

                   cases.append(case)
                   success_count += 1

               except Exception as e:
                   continue

           return True, f"成功解析 {success_count} 筆案件", cases

       except Exception as e:
           return False, f"讀取工作表失敗：{str(e)}", []

   @staticmethod
   def _create_column_mapping(columns: List[str]) -> Dict[str, str]:
       """
       建立欄位對應字典

       Args:
           columns: Excel欄位名稱列表

       Returns:
           Dict[str, str]: 欄位對應字典
       """
       mapping = {}

       # 當事人欄位對應
       client_keywords = ['當事人', '客戶', '客戶名稱', '名字']
       for col in columns:
           col_clean = str(col).strip()
           if col_clean in client_keywords:
               mapping['client'] = col
               break

       # 案由欄位對應
       for col in columns:
           col_clean = str(col).strip()
           if '案由' in col_clean:
               mapping['case_reason'] = col
               break

       # 案號欄位對應
       for col in columns:
           col_clean = str(col).strip()
           if '案號' in col_clean or '機關' in col_clean:
               mapping['case_number'] = col
               break

       # 對造欄位對應
       for col in columns:
           col_clean = str(col).strip()
           if '對造' in col_clean:
               mapping['opposing_party'] = col
               break

       # 股別欄位對應
       for col in columns:
           col_clean = str(col).strip()
           if '股別' in col_clean:
               mapping['division'] = col
               break

       return mapping

   @staticmethod
   def _safe_get_value(row, column_name: str) -> Optional[str]:
       """
       安全地取得欄位值

       Args:
           row: pandas行資料
           column_name: 欄位名稱

       Returns:
           Optional[str]: 欄位值或None
       """
       if not column_name:
           return None

       try:
           value = row.get(column_name, '')
           if pd.isna(value) or str(value).strip().lower() in ['nan', 'none', '']:
               return None
           return str(value).strip()
       except:
           return None

   @staticmethod
   def import_cases_from_sheet_with_mapping(file_path: str, case_type: str) -> Tuple[bool, str, List[CaseData]]:
       """
       從Excel工作表匯入案件資料，支援欄位自動對應（向後相容性方法）

       Args:
           file_path: Excel檔案路徑
           case_type: 案件類型（'民事' 或 '刑事'）

       Returns:
           Tuple[bool, str, List[CaseData]]: (成功狀態, 訊息, 案件列表)
       """
       try:
           # 讀取Excel檔案，取得所有工作表
           excel_file = pd.ExcelFile(file_path)

           # 檢查是否有對應的工作表
           target_sheet = None
           for sheet_name in excel_file.sheet_names:
               if case_type in sheet_name:
                   target_sheet = sheet_name
                   break

           if not target_sheet:
               return False, f"找不到包含「{case_type}」的工作表", []

           # 使用新的單一工作表匯入方法
           return ExcelHandler._import_from_single_sheet(file_path, target_sheet, case_type)

       except Exception as e:
           return False, f"讀取Excel檔案失敗：{str(e)}", []