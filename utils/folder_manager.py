
import os
import shutil
import pandas as pd
from typing import Optional, List
from models.case_model import CaseData
from config.settings import AppConfig

class FolderManager:
    """案件資料夾管理工具"""

    def __init__(self, base_data_folder: str):
        """初始化資料夾管理器"""
        self.base_data_folder = base_data_folder

    def create_case_folder_structure(self, case_data: CaseData) -> bool:
        """為案件建立完整的資料夾結構"""
        try:
            # 取得案件類型對應的資料夾
            case_type_folder = self._get_case_type_folder(case_data.case_type)
            if not case_type_folder:
                print(f"未知的案件類型: {case_data.case_type}")
                return False

            # 建立當事人資料夾
            client_folder = self._create_client_folder(case_type_folder, case_data.client)
            if not client_folder:
                return False

            # 建立子資料夾結構
            sub_folders = self._create_sub_folders(client_folder)
            if not sub_folders:
                return False

            # 建立現有的進度階段資料夾
            progress_folder_success = self._create_progress_folders(
                sub_folders['進度追蹤'], case_data.progress_stages
            )

            # 建立案件資訊Excel檔案
            case_info_folder = sub_folders['案件資訊']
            excel_success = self._create_case_info_excel(case_info_folder, case_data)

            if excel_success and progress_folder_success:
                print(f"成功為案件 {case_data.case_id} 建立完整資料夾結構")
                print(f"路徑: {client_folder}")
                return True
            else:
                print(f"資料夾建立成功，但部分功能建立失敗")
                return False

        except Exception as e:
            print(f"建立案件資料夾結構失敗: {e}")
            return False

    def _create_progress_folders(self, progress_base_folder: str, progress_stages: dict) -> bool:
        """建立進度階段資料夾"""
        try:
            for stage_name in progress_stages.keys():
                stage_folder_path = os.path.join(progress_base_folder, stage_name)
                if not os.path.exists(stage_folder_path):
                    os.makedirs(stage_folder_path)
                    print(f"建立進度資料夾: {stage_folder_path}")

            return True

        except Exception as e:
            print(f"建立進度資料夾失敗: {e}")
            return False

    def create_progress_folder(self, case_data: CaseData, stage_name: str) -> bool:
        """為案件建立特定進度階段資料夾"""
        try:
            case_folder = self.get_case_folder_path(case_data)
            if not case_folder:
                return False

            progress_base_folder = os.path.join(case_folder, '進度追蹤')
            stage_folder_path = os.path.join(progress_base_folder, stage_name)

            if not os.path.exists(stage_folder_path):
                os.makedirs(stage_folder_path)
                print(f"建立進度資料夾: {stage_folder_path}")

            return True

        except Exception as e:
            print(f"建立進度資料夾失敗: {e}")
            return False

    def delete_progress_folder(self, case_data: CaseData, stage_name: str) -> bool:
        """刪除案件的特定進度階段資料夾"""
        try:
            case_folder = self.get_case_folder_path(case_data)
            if not case_folder:
                print(f"找不到案件資料夾: {case_data.client}")
                return False

            stage_folder_path = os.path.join(case_folder, '進度追蹤', stage_name)

            if os.path.exists(stage_folder_path):
                # 檢查資料夾是否為空
                if os.listdir(stage_folder_path):
                    print(f"警告：階段資料夾 {stage_name} 內含檔案，將一併刪除")

                # 刪除整個資料夾及其內容
                shutil.rmtree(stage_folder_path)
                print(f"已刪除階段資料夾: {stage_folder_path}")
                return True
            else:
                print(f"階段資料夾不存在: {stage_folder_path}")
                return False

        except Exception as e:
            print(f"刪除階段資料夾失敗: {e}")
            return False

    def _get_case_type_folder(self, case_type: str) -> Optional[str]:
        """取得案件類型對應的資料夾路徑"""
        try:
            folder_name = AppConfig.CASE_TYPE_FOLDERS.get(case_type)
            if not folder_name:
                return None

            case_type_path = os.path.join(self.base_data_folder, folder_name)

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
            safe_client_name = self._sanitize_folder_name(client_name)
            client_folder_path = os.path.join(case_type_folder, safe_client_name)

            if not os.path.exists(client_folder_path):
                os.makedirs(client_folder_path)
                print(f"建立當事人資料夾: {client_folder_path}")

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

                created_folders[folder_name] = folder_path

            return created_folders

        except Exception as e:
            print(f"建立子資料夾失敗: {e}")
            return None

    def _create_case_info_excel(self, case_info_folder: str, case_data: CaseData) -> bool:
        """建立案件資訊Excel檔案"""
        try:
            excel_filename = f"{case_data.case_id}_{case_data.client}_案件資訊.xlsx"
            excel_path = os.path.join(case_info_folder, excel_filename)

            # 準備詳細資訊資料
            detail_info = [
                ['案由', getattr(case_data, 'case_reason', '') or ''],
                ['案號', getattr(case_data, 'case_number', '') or ''],
                ['對造', getattr(case_data, 'opposing_party', '') or ''],
                ['負責法院', getattr(case_data, 'court', '') or ''],
                ['負責股別', getattr(case_data, 'division', '') or '']
            ]

            df = pd.DataFrame(detail_info, columns=['項目', '內容'])

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
                    ['進度日期', case_data.progress_date or ''],
                    ['建立日期', case_data.created_date.strftime('%Y-%m-%d %H:%M:%S')],
                    ['更新日期', case_data.updated_date.strftime('%Y-%m-%d %H:%M:%S')]
                ]

                df_basic = pd.DataFrame(basic_info, columns=['項目', '內容'])
                df_basic.to_excel(writer, sheet_name='基本資訊', index=False, startrow=0, startcol=0)

                # 進度階段工作表
                if case_data.progress_stages:
                    progress_info = []
                    for stage, date in sorted(case_data.progress_stages.items(), key=lambda x: x[1]):
                        progress_info.append([stage, date])

                    if progress_info:
                        df_progress = pd.DataFrame(progress_info, columns=['進度階段', '日期'])
                        df_progress.to_excel(writer, sheet_name='進度階段', index=False, startrow=0, startcol=0)

                # 調整欄位寬度
                for sheet_name in writer.sheets:
                    worksheet = writer.sheets[sheet_name]
                    worksheet.column_dimensions['A'].width = 15
                    worksheet.column_dimensions['B'].width = 30

                    for cell in worksheet[1]:
                        cell.font = cell.font.copy(bold=True)

            print(f"成功建立案件資訊Excel檔案: {excel_path}")
            return True

        except Exception as e:
            print(f"建立案件資訊Excel檔案失敗: {e}")
            return False

    def _sanitize_folder_name(self, name: str) -> str:
        """清理資料夾名稱，移除不允許的字元"""
        invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']

        clean_name = name
        for char in invalid_chars:
            clean_name = clean_name.replace(char, '_')

        clean_name = clean_name.strip(' .')

        if not clean_name or len(clean_name) > 100:
            clean_name = f"案件_unknown"

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

    def get_stage_folder_path(self, case_data: CaseData, stage_name: str) -> Optional[str]:
        """取得特定階段的資料夾路徑"""
        try:
            case_folder = self.get_case_folder_path(case_data)
            if not case_folder:
                return None

            stage_folder_path = os.path.join(case_folder, '進度追蹤', stage_name)
            return stage_folder_path if os.path.exists(stage_folder_path) else None

        except Exception as e:
            print(f"取得階段資料夾路徑失敗: {e}")
            return None

    def delete_case_folder(self, case_data: CaseData) -> bool:
        """刪除案件的整個當事人資料夾"""
        try:
            case_folder = self.get_case_folder_path(case_data)
            if not case_folder:
                print(f"找不到案件資料夾: {case_data.client}")
                return False

            if os.path.exists(case_folder):
                # 檢查資料夾是否為空
                if os.listdir(case_folder):
                    print(f"警告：案件資料夾 {case_data.client} 內含檔案，將一併刪除")

                # 刪除整個資料夾及其內容
                shutil.rmtree(case_folder)
                print(f"已刪除案件資料夾: {case_folder}")
                return True
            else:
                print(f"案件資料夾不存在: {case_folder}")
                return False

        except Exception as e:
            print(f"刪除案件資料夾失敗: {e}")
            return False

    def get_case_folder_info(self, case_data: CaseData) -> dict:
        """取得案件資料夾資訊（用於刪除前檢查）"""
        try:
            case_folder = self.get_case_folder_path(case_data)
            if not case_folder or not os.path.exists(case_folder):
                return {
                    'exists': False,
                    'path': case_folder,
                    'has_files': False,
                    'file_count': 0,
                    'size_mb': 0
                }

            # 計算資料夾內檔案數量和大小
            total_files = 0
            total_size = 0

            for root, dirs, files in os.walk(case_folder):
                total_files += len(files)
                for file in files:
                    try:
                        file_path = os.path.join(root, file)
                        total_size += os.path.getsize(file_path)
                    except:
                        pass

            return {
                'exists': True,
                'path': case_folder,
                'has_files': total_files > 0,
                'file_count': total_files,
                'size_mb': round(total_size / (1024 * 1024), 2)
            }

        except Exception as e:
            print(f"取得案件資料夾資訊失敗: {e}")
            return {
                'exists': False,
                'path': None,
                'has_files': False,
                'file_count': 0,
                'size_mb': 0
            }

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

            return self._create_case_info_excel(case_info_folder, case_data)

        except Exception as e:
            print(f"更新案件資訊Excel檔案失敗: {e}")
            return False