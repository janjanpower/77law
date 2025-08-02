#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
資料夾服務 - 修正版本
1. 修正Excel檔案生成邏輯
2. 整合case_data_manager.py中的Excel生成規則
"""

import os
from typing import Dict, Any, List, Tuple, Optional
from models.case_model import CaseData
from config.settings import AppConfig


class FolderService:
    """資料夾管理服務 - 修正版本"""

    def __init__(self, base_data_folder: str):
        """
        初始化資料夾服務

        Args:
            base_data_folder: 基礎資料資料夾路徑
        """
        self.base_data_folder = base_data_folder
        self.standard_subfolders = [
            '案件資訊',     # 存放案件基本資料Excel
            '進度追蹤',     # 存放進度相關檔案
            '狀紙'         # 存放法律文件

        ]

        # 確保基礎資料夾存在
        os.makedirs(base_data_folder, exist_ok=True)
        print(f"✅ FolderService 初始化完成，基礎路徑: {base_data_folder}")

    def get_case_folder_path(self, case_data: CaseData) -> Optional[str]:
        """
        取得案件資料夾路徑

        Args:
            case_data: 案件資料

        Returns:
            Optional[str]: 資料夾路徑或None
        """
        try:
            # 取得案件類型資料夾
            case_type_folder_name = AppConfig.CASE_TYPE_FOLDERS.get(case_data.case_type)
            if not case_type_folder_name:
                print(f"❌ 未知的案件類型: {case_data.case_type}")
                return None

            # 清理當事人姓名
            safe_client_name = self._sanitize_name_for_folder(case_data.client)

            # 建構完整路徑
            case_folder_path = os.path.join(
                self.base_data_folder,
                case_type_folder_name,
                safe_client_name
            )

            return case_folder_path

        except Exception as e:
            print(f"❌ 取得案件資料夾路徑失敗: {e}")
            return None

    def _sanitize_name_for_folder(self, name: str) -> str:
        """
        清理名稱用於資料夾命名

        Args:
            name: 原始名稱

        Returns:
            str: 清理後的名稱
        """
        try:
            # 移除資料夾名不允許的字元
            unsafe_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
            safe_name = name
            for char in unsafe_chars:
                safe_name = safe_name.replace(char, '_')

            # 限制長度並移除前後空白
            safe_name = safe_name.strip()[:50]

            return safe_name if safe_name else "未命名"

        except Exception as e:
            print(f"❌ 清理資料夾名稱失敗: {e}")
            return "未知客戶"

    def _sanitize_name_for_filename(self, name: str) -> str:
        """
        清理名稱用於檔案命名

        Args:
            name: 原始名稱

        Returns:
            str: 清理後的名稱
        """
        try:
            # 移除檔案名不允許的字元
            invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
            clean_name = name

            for char in invalid_chars:
                clean_name = clean_name.replace(char, '_')

            # 移除多餘的空格和點
            clean_name = clean_name.strip(' .')

            # 限制長度
            if len(clean_name) > 20:
                clean_name = clean_name[:20]

            # 確保不為空
            if not clean_name:
                clean_name = "客戶"

            return clean_name

        except Exception as e:
            print(f"❌ 清理檔案名稱失敗: {e}")
            return "客戶"

    # ==================== 資料夾建立 ====================

    def create_case_folder_structure(self, case_data: CaseData, force_recreate: bool = False) -> Tuple[bool, str]:
        """
        建立案件資料夾結構

        Args:
            case_data: 案件資料
            force_recreate: 是否強制重新建立

        Returns:
            (成功與否, 結果訊息)
        """
        try:
            print(f"🏗️ 開始建立案件資料夾結構: {case_data.client}")

            # 1. 基本驗證
            if not case_data.client or not case_data.case_type:
                return False, "案件資料不完整，無法建立資料夾"

            # 2. 取得資料夾路徑
            case_folder_path = self.get_case_folder_path(case_data)
            if not case_folder_path:
                return False, "無法確定資料夾路徑"

            # 3. 檢查是否已存在
            if os.path.exists(case_folder_path) and not force_recreate:
                return True, f"資料夾已存在: {case_folder_path}"

            # 4. 建立主要資料夾
            os.makedirs(case_folder_path, exist_ok=True)

            # 5. 建立子資料夾結構
            for subfolder in self.standard_subfolders:
                subfolder_path = os.path.join(case_folder_path, subfolder)
                os.makedirs(subfolder_path, exist_ok=True)

            # 6. 建立案件資訊Excel檔案（修正版本）
            excel_success = self._create_case_info_excel(case_data, case_folder_path)
            if not excel_success:
                print(f"⚠️ Excel檔案建立失敗，但資料夾結構已建立完成")

            print(f"✅ 成功建立案件資料夾結構: {case_folder_path}")
            return True, f"成功建立資料夾: {case_folder_path}"

        except Exception as e:
            error_msg = f"建立案件資料夾失敗: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg

    def _create_case_info_excel(self, case_data: CaseData, case_folder_path: str) -> bool:
        """
        建立案件資訊Excel檔案 - 修正版本
        整合case_data_manager.py中的Excel生成邏輯

        Args:
            case_data: 案件資料
            case_folder_path: 案件資料夾路徑

        Returns:
            bool: 建立是否成功
        """
        try:
            print(f"📊 開始建立案件資訊Excel檔案")

            # 檢查pandas是否可用
            try:
                import pandas as pd
            except ImportError:
                print(f"⚠️ 缺少pandas套件，無法建立Excel檔案，將建立文字檔案作為替代")
                return self._create_case_info_text_fallback(case_data, case_folder_path)

            # 建立Excel檔案路徑
            info_folder = os.path.join(case_folder_path, '案件資訊')
            clean_client = self._sanitize_name_for_filename(case_data.client)
            excel_filename = f"{case_data.case_id}_{clean_client}_案件資訊.xlsx"
            excel_file_path = os.path.join(info_folder, excel_filename)

            # 基本資訊
            basic_info = [
                ['案件編號', case_data.case_id],
                ['案件類型', case_data.case_type],
                ['當事人', case_data.client],
                ['委任律師', getattr(case_data, 'lawyer', '') or ''],
                ['法務', getattr(case_data, 'legal_affairs', '') or ''],
                ['目前進度', case_data.progress],
                ['進度日期', case_data.progress_date or ''],
                ['建立日期', case_data.created_date.strftime('%Y-%m-%d %H:%M:%S') if case_data.created_date else ''],
                ['更新日期', case_data.updated_date.strftime('%Y-%m-%d %H:%M:%S') if case_data.updated_date else '']
            ]

            # 詳細資訊
            detail_info = [
                ['案由', getattr(case_data, 'case_reason', '') or ''],
                ['案號', getattr(case_data, 'case_number', '') or ''],
                ['對造', getattr(case_data, 'opposing_party', '') or ''],
                ['負責法院', getattr(case_data, 'court', '') or ''],
                ['負責股別', getattr(case_data, 'division', '') or '']
            ]

            # 寫入Excel檔案
            with pd.ExcelWriter(excel_file_path, engine='openpyxl') as writer:
                # 基本資訊工作表
                df_basic = pd.DataFrame(basic_info, columns=['項目', '內容'])
                df_basic.to_excel(writer, sheet_name='基本資訊', index=False)

                # 詳細資訊工作表
                df_detail = pd.DataFrame(detail_info, columns=['項目', '內容'])
                df_detail.to_excel(writer, sheet_name='詳細資訊', index=False)

                # 進度追蹤工作表（如果有進度階段）
                if hasattr(case_data, 'progress_stages') and case_data.progress_stages:
                    progress_data = []
                    for stage_name, stage_info in case_data.progress_stages.items():
                        if isinstance(stage_info, dict):
                            date = stage_info.get('date', '')
                            note = stage_info.get('note', '')
                            time = stage_info.get('time', '')
                        else:
                            date = str(stage_info)
                            note = ''
                            time = ''

                        progress_data.append([stage_name, date, note, time])

                    if progress_data:
                        df_progress = pd.DataFrame(progress_data, columns=['階段', '日期', '備註', '時間'])
                        df_progress.to_excel(writer, sheet_name='進度追蹤', index=False)

            print(f"✅ Excel檔案建立完成: {excel_filename}")
            return True

        except Exception as e:
            print(f"❌ 建立Excel檔案失敗: {e}")
            # 建立文字檔案作為備用
            return self._create_case_info_text_fallback(case_data, case_folder_path)

    def _create_case_info_text_fallback(self, case_data: CaseData, case_folder_path: str) -> bool:
        """
        建立案件資訊文字檔案（備用方案）

        Args:
            case_data: 案件資料
            case_folder_path: 案件資料夾路徑

        Returns:
            bool: 建立是否成功
        """
        try:
            info_folder = os.path.join(case_folder_path, '案件資訊')
            info_file = os.path.join(info_folder, '案件基本資料.txt')

            case_info = f"""案件基本資料
================

案件編號：{case_data.case_id}
案件類型：{case_data.case_type}
當事人：{case_data.client}
委任律師：{getattr(case_data, 'lawyer', '') or '未指定'}
法務人員：{getattr(case_data, 'legal_affairs', '') or '未指定'}
案由：{getattr(case_data, 'case_reason', '') or '未填寫'}
案號：{getattr(case_data, 'case_number', '') or '未填寫'}
對造：{getattr(case_data, 'opposing_party', '') or '未填寫'}
負責法院：{getattr(case_data, 'court', '') or '未填寫'}
負責股別：{getattr(case_data, 'division', '') or '未填寫'}
目前進度：{case_data.progress}
建立日期：{case_data.created_date.strftime('%Y-%m-%d %H:%M:%S') if case_data.created_date else '未知'}
更新日期：{case_data.updated_date.strftime('%Y-%m-%d %H:%M:%S') if case_data.updated_date else '未知'}
"""

            with open(info_file, 'w', encoding='utf-8') as f:
                f.write(case_info)

            print(f"✅ 建立案件資訊文字檔案: {info_file}")
            return True

        except Exception as e:
            print(f"❌ 建立案件資訊文字檔案失敗: {e}")
            return False

    # ==================== 資料夾查詢 ====================

    def get_case_folder_info(self, case_data: CaseData) -> Dict[str, Any]:
        """
        取得案件資料夾資訊

        Args:
            case_data: 案件資料

        Returns:
            資料夾資訊字典
        """
        try:
            folder_path = self.get_case_folder_path(case_data)

            if not folder_path:
                return {
                    'exists': False,
                    'path': None,
                    'subfolders': {},
                    'error': '無法確定資料夾路徑'
                }

            folder_info = {
                'exists': os.path.exists(folder_path),
                'path': folder_path,
                'subfolders': {},
                'error': None
            }

            if folder_info['exists']:
                # 檢查子資料夾狀態
                for subfolder in self.standard_subfolders:
                    subfolder_path = os.path.join(folder_path, subfolder)
                    folder_info['subfolders'][subfolder] = {
                        'exists': os.path.exists(subfolder_path),
                        'path': subfolder_path
                    }

            return folder_info

        except Exception as e:
            return {
                'exists': False,
                'path': None,
                'subfolders': {},
                'error': f'取得資料夾資訊失敗: {str(e)}'
            }

    def list_case_folders(self, case_type: str = None) -> List[Dict[str, Any]]:
        """
        列出所有案件資料夾

        Args:
            case_type: 案件類型過濾（可選）

        Returns:
            資料夾資訊列表
        """
        folders = []

        try:
            # 如果指定案件類型，只查看該類型
            if case_type:
                case_type_folders = [AppConfig.CASE_TYPE_FOLDERS.get(case_type)]
                case_type_folders = [f for f in case_type_folders if f]
            else:
                case_type_folders = list(AppConfig.CASE_TYPE_FOLDERS.values())

            for type_folder in case_type_folders:
                type_path = os.path.join(self.base_data_folder, type_folder)

                if not os.path.exists(type_path):
                    continue

                # 遍歷當事人資料夾
                for client_folder in os.listdir(type_path):
                    client_path = os.path.join(type_path, client_folder)

                    if not os.path.isdir(client_path):
                        continue

                    folder_info = {
                        'case_type': case_type or '未知',
                        'client_name': client_folder,
                        'folder_path': client_path,
                        'subfolders': []
                    }

                    # 檢查子資料夾
                    for subfolder in self.standard_subfolders:
                        subfolder_path = os.path.join(client_path, subfolder)
                        if os.path.exists(subfolder_path):
                            folder_info['subfolders'].append(subfolder)

                    folders.append(folder_info)

        except Exception as e:
            print(f"❌ 列出案件資料夾失敗: {e}")

        return folders

    def create_progress_folder(self, case_data: CaseData, stage_name: str) -> bool:
        """
        建立進度階段資料夾

        Args:
            case_data: 案件資料
            stage_name: 階段名稱

        Returns:
            bool: 建立是否成功
        """
        try:
            print(f"📁 準備建立進度階段資料夾: {stage_name}")

            # 取得案件資料夾路徑
            case_folder_path = self.get_case_folder_path(case_data)
            if not case_folder_path:
                print(f"❌ 無法取得案件資料夾路徑")
                return False

            # 建立進度追蹤子資料夾路徑
            progress_folder = os.path.join(case_folder_path, '進度追蹤', stage_name)

            # 建立資料夾
            os.makedirs(progress_folder, exist_ok=True)
            print(f"✅ 成功建立進度階段資料夾: {progress_folder}")

            return True

        except Exception as e:
            print(f"❌ 建立進度階段資料夾失敗: {e}")
            return False

    def delete_case_folder(self, case_data: CaseData, force: bool = False) -> Tuple[bool, str]:
        """
        刪除案件資料夾

        Args:
            case_data: 案件資料
            force: 是否強制刪除

        Returns:
            (成功與否, 結果訊息)
        """
        try:
            folder_path = self.get_case_folder_path(case_data)
            if not folder_path:
                return False, "無法確定資料夾路徑"

            if not os.path.exists(folder_path):
                return True, "資料夾不存在"

            if not force:
                # 檢查資料夾是否為空
                if os.listdir(folder_path):
                    return False, "資料夾不為空，請使用強制刪除"

            # 刪除資料夾
            import shutil
            shutil.rmtree(folder_path)

            print(f"✅ 成功刪除案件資料夾: {folder_path}")
            return True, f"成功刪除資料夾: {folder_path}"

        except Exception as e:
            error_msg = f"刪除案件資料夾失敗: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg