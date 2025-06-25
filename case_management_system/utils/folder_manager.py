import os
import pandas as pd
from typing import Optional
from models.case_model import CaseData
from config.settings import AppConfig

class FolderManager:
    """案件資料夾管理工具"""

    def __init__(self, base_data_folder: str):
        """
        初始化資料夾管理器

        Args:
            base_data_folder: 基礎資料夾路徑
        """
        self.base_data_folder = base_data_folder

    def create_case_folder_structure(self, case_data: CaseData) -> bool:
        """
        為新增的案件建立完整的資料夾結構

        Args:
            case_data: 案件資料

        Returns:
            bool: 是否成功建立
        """
        try:
            # 1. 取得案件類型對應的資料夾
            case_type_folder = self._get_case_type_folder(case_data.case_type)
            if not case_type_folder:
                print(f"未知的案件類型: {case_data.case_type}")
                return False

            # 2. 建立當事人資料夾
            client_folder = self._create_client_folder(case_type_folder, case_data.client)
            if not client_folder:
                return False

            # 3. 建立子資料夾結構
            sub_folders = self._create_sub_folders(client_folder)
            if not sub_folders:
                return False

            # 4. 建立案件資訊Excel檔案
            case_info_folder = sub_folders['案件資訊']
            excel_success = self._create_case_info_excel(case_info_folder, case_data)

            if excel_success:
                print(f"成功為案件 {case_data.case_id} 建立完整資料夾結構")
                print(f"路徑: {client_folder}")
                return True
            else:
                print(f"資料夾建立成功，但Excel檔案建立失敗")
                return False

        except Exception as e:
            print(f"建立案件資料夾結構失敗: {e}")
            return False

    def _get_case_type_folder(self, case_type: str) -> Optional[str]:
        """取得案件類型對應的資料夾路徑"""
        try:
            folder_name = AppConfig.CASE_TYPE_FOLDERS.get(case_type)
            if not folder_name:
                return None

            case_type_path = os.path.join(self.base_data_folder, folder_name)

            # 確保案件類型資料夾存在
            if not os.path.exists(case_type_path):
                os.makedirs(case_type_path)
                print(f"建立案件類型資料夾: {case_type_path}")

            return case_type_path

        except Exception as e:
            print(f"取得案件類型資料夾失敗: {e}")
            return None

    def _create_client_folder(self, case_type_folder: str, client_name: str) -> Optional[str]:
        """建立當事人資料夾"""
        try:
            # 清理檔案名稱，移除不允許的字元
            safe_client_name = self._sanitize_folder_name(client_name)
            client_folder_path = os.path.join(case_type_folder, safe_client_name)

            # 如果資料夾已存在，就直接使用
            if not os.path.exists(client_folder_path):
                os.makedirs(client_folder_path)
                print(f"建立當事人資料夾: {client_folder_path}")
            else:
                print(f"當事人資料夾已存在: {client_folder_path}")

            return client_folder_path

        except Exception as e:
            print(f"建立當事人資料夾失敗: {e}")
            return None

    def _create_sub_folders(self, client_folder: str) -> Optional[dict]:
        """建立子資料夾結構"""
        try:
            sub_folder_names = ['狀紙', '進度追蹤', '案件資訊']
            created_folders = {}

            for folder_name in sub_folder_names:
                folder_path = os.path.join(client_folder, folder_name)

                if not os.path.exists(folder_path):
                    os.makedirs(folder_path)
                    print(f"建立子資料夾: {folder_path}")
                else:
                    print(f"子資料夾已存在: {folder_path}")

                created_folders[folder_name] = folder_path

            return created_folders

        except Exception as e:
            print(f"建立子資料夾失敗: {e}")
            return None

    def _create_case_info_excel(self, case_info_folder: str, case_data: CaseData) -> bool:
        """建立案件資訊Excel檔案"""
        try:
            # Excel檔案名稱
            excel_filename = f"{case_data.case_id}_{case_data.client}_案件資訊.xlsx"
            excel_path = os.path.join(case_info_folder, excel_filename)

            # 準備詳細資訊資料 (A1-A5)
            detail_info = [
                ['案由', getattr(case_data, 'case_reason', '') or ''],
                ['案號', getattr(case_data, 'case_number', '') or ''],
                ['對造', getattr(case_data, 'opposing_party', '') or ''],
                ['負責法院', getattr(case_data, 'court', '') or ''],
                ['負責股別', getattr(case_data, 'division', '') or '']
            ]

            # 建立DataFrame
            df = pd.DataFrame(detail_info, columns=['項目', '內容'])

            # 使用ExcelWriter建立多個工作表
            with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
                # 詳細資訊工作表
                df.to_excel(writer, sheet_name='詳細資訊', index=False, startrow=0, startcol=0)

                # 基本資訊工作表
                basic_info = [
                    ['案件編號', case_data.case_id],
                    ['案件類型', case_data.case_type],
                    ['當事人', case_data.client],
                    ['委任律師', case_data.lawyer or ''],
                    ['法務', case_data.legal_affairs or ''],
                    ['進度追蹤', case_data.progress],
                    ['建立日期', case_data.created_date.strftime('%Y-%m-%d %H:%M:%S')],
                    ['更新日期', case_data.updated_date.strftime('%Y-%m-%d %H:%M:%S')]
                ]

                df_basic = pd.DataFrame(basic_info, columns=['項目', '內容'])
                df_basic.to_excel(writer, sheet_name='基本資訊', index=False, startrow=0, startcol=0)

                # 調整欄位寬度
                for sheet_name in ['詳細資訊', '基本資訊']:
                    worksheet = writer.sheets[sheet_name]

                    # 設定欄位寬度
                    worksheet.column_dimensions['A'].width = 15  # 項目欄位
                    worksheet.column_dimensions['B'].width = 30  # 內容欄位

                    # 設定標題行樣式
                    for cell in worksheet[1]:
                        cell.font = cell.font.copy(bold=True)

            print(f"成功建立案件資訊Excel檔案: {excel_path}")
            return True

        except Exception as e:
            print(f"建立案件資訊Excel檔案失敗: {e}")
            return False

    def _sanitize_folder_name(self, name: str) -> str:
        """清理資料夾名稱，移除不允許的字元"""
        # Windows不允許的字元
        invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']

        clean_name = name
        for char in invalid_chars:
            clean_name = clean_name.replace(char, '_')

        # 移除前後空白和點
        clean_name = clean_name.strip(' .')

        # 如果名稱為空或太長，使用預設名稱
        if not clean_name or len(clean_name) > 100:
            clean_name = f"案件_{case_data.case_id if hasattr(case_data, 'case_id') else 'unknown'}"

        return clean_name

    def get_case_folder_path(self, case_data: CaseData) -> Optional[str]:
        """取得案件的資料夾路徑"""
        try:
            case_type_folder = self._get_case_type_folder(case_data.case_type)
            if not case_type_folder:
                return None

            safe_client_name = self._sanitize_folder_name(case_data.client)
            client_folder = os.path.join(case_type_folder, safe_client_name)

            return client_folder if os.path.exists(client_folder) else None

        except Exception as e:
            print(f"取得案件資料夾路徑失敗: {e}")
            return None

    def update_case_info_excel(self, case_data: CaseData) -> bool:
        """更新案件資訊Excel檔案"""
        try:
            case_folder = self.get_case_folder_path(case_data)
            if not case_folder:
                print(f"找不到案件資料夾: {case_data.client}")
                return False

            case_info_folder = os.path.join(case_folder, '案件資訊')
            if not os.path.exists(case_info_folder):
                print(f"找不到案件資訊資料夾: {case_info_folder}")
                return False

            # 重新建立Excel檔案
            return self._create_case_info_excel(case_info_folder, case_data)

        except Exception as e:
            print(f"更新案件資訊Excel檔案失敗: {e}")
            return False