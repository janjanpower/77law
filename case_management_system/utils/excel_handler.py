import pandas as pd
from typing import List, Optional
from models.case_model import CaseData
from datetime import datetime
import os

class ExcelHandler:
    """Excel 檔案處理類別"""

    @staticmethod
    def export_cases_to_excel(cases: List[CaseData], file_path: str) -> bool:
        """
        將案件資料匯出為 Excel 檔案

        Args:
            cases: 案件資料列表
            file_path: 檔案路徑

        Returns:
            bool: 是否成功匯出
        """
        try:
            # 準備資料
            data = []
            for case in cases:
                data.append({
                    '案件編號': case.case_id,
                    '案件類型': case.case_type,
                    '當事人': case.client,
                    '委任律師': case.lawyer or '',
                    '法務': case.legal_affairs or '',
                    '進度追蹤': case.progress,
                    '建立日期': case.created_date.strftime('%Y-%m-%d %H:%M:%S'),
                    '更新日期': case.updated_date.strftime('%Y-%m-%d %H:%M:%S')
                })

            # 建立 DataFrame
            df = pd.DataFrame(data)

            # 匯出到 Excel
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='案件資料', index=False)

                # 調整欄位寬度
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
        """
        從 Excel 檔案匯入案件資料

        Args:
            file_path: 檔案路徑

        Returns:
            Optional[List[CaseData]]: 案件資料列表，失敗時返回 None
        """
        try:
            # 讀取 Excel 檔案
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
                        progress=str(row.get('進度追蹤', '待處理'))
                    )
                    cases.append(case)
                except Exception as e:
                    print(f"處理第 {len(cases) + 1} 筆資料時發生錯誤: {e}")
                    continue

            return cases

        except Exception as e:
            print(f"匯入 Excel 失敗: {e}")
            return None
