#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
資料夾管理模組
提供統一的資料夾操作功能
"""

import os
import shutil
from typing import Optional, List, Dict, Tuple, Any
from pathlib import Path

class FolderManager:
    """資料夾管理器 - 統一的資料夾操作"""

    def __init__(self, base_folder: str):
        """初始化資料夾管理器"""
        self.base_folder = Path(base_folder)
        self.base_folder.mkdir(parents=True, exist_ok=True)

        # 預設的案件資料夾結構
        self.default_subfolders = [
            "案件資訊",
            "法院文件",
            "當事人資料",
            "相關證據",
            "往來信件",
            "其他文件"
        ]

    def create_case_folder_structure(self, case_data) -> bool:
        """建立案件資料夾結構"""
        try:
            # 從案件資料建立資料夾名稱
            folder_name = self._generate_folder_name(case_data)
            case_folder = self.base_folder / folder_name

            # 建立主資料夾
            case_folder.mkdir(parents=True, exist_ok=True)

            # 建立子資料夾結構
            for subfolder in self.default_subfolders:
                (case_folder / subfolder).mkdir(exist_ok=True)

            # 建立案件資訊Excel檔案
            self._create_case_info_excel(case_folder, case_data)

            print(f"✅ 建立案件資料夾: {case_folder}")
            return True

        except Exception as e:
            print(f"建立案件資料夾失敗: {e}")
            return False

    def get_case_folder_path(self, case_data) -> Optional[str]:
        """取得案件資料夾路徑"""
        try:
            folder_name = self._generate_folder_name(case_data)
            case_folder = self.base_folder / folder_name

            if case_folder.exists():
                return str(case_folder)
            return None

        except Exception as e:
            print(f"取得案件資料夾路徑失敗: {e}")
            return None

    def _generate_folder_name(self, case_data) -> str:
        """產生資料夾名稱"""
        try:
            # 根據案件資料生成唯一的資料夾名稱
            if hasattr(case_data, 'client') and hasattr(case_data, 'case_type'):
                # 清理檔案名稱中的特殊字符
                client_name = str(case_data.client).replace('/', '_').replace('\\', '_')
                case_type = str(case_data.case_type).replace('/', '_').replace('\\', '_')
                return f"{client_name}_{case_type}"
            elif hasattr(case_data, 'client'):
                client_name = str(case_data.client).replace('/', '_').replace('\\', '_')
                return client_name
            elif hasattr(case_data, 'case_number'):
                case_number = str(case_data.case_number).replace('/', '_').replace('\\', '_')
                return f"案件_{case_number}"
            else:
                return f"案件_{id(case_data)}"
        except Exception as e:
            print(f"產生資料夾名稱失敗: {e}")
            return f"案件_{id(case_data)}"

    def _create_case_info_excel(self, case_folder: Path, case_data) -> bool:
        """建立案件資訊Excel檔案"""
        try:
            import pandas as pd

            # 準備案件資訊資料
            case_info = {}

            # 從案件資料物件提取資訊
            if hasattr(case_data, '__dict__'):
                case_info = case_data.__dict__.copy()
            else:
                # 如果是字典
                case_info = dict(case_data) if isinstance(case_data, dict) else {}

            # 補充基本欄位
            basic_fields = {
                '委託人': case_info.get('client', ''),
                '案件類型': case_info.get('case_type', ''),
                '案件編號': case_info.get('case_number', ''),
                '承辦律師': case_info.get('lawyer', ''),
                '案件狀態': case_info.get('status', '進行中'),
                '委託日期': case_info.get('commission_date', ''),
                '備註': case_info.get('notes', '')
            }

            # 建立DataFrame
            df = pd.DataFrame([basic_fields])

            # 儲存到案件資訊資料夾
            info_folder = case_folder / "案件資訊"
            info_folder.mkdir(exist_ok=True)

            excel_path = info_folder / "案件基本資料.xlsx"
            df.to_excel(excel_path, index=False, engine='openpyxl')

            print(f"✅ 建立案件資訊檔案: {excel_path}")
            return True

        except Exception as e:
            print(f"建立案件資訊Excel檔案失敗: {e}")
            return False

    def list_case_folders(self) -> List[str]:
        """列出所有案件資料夾"""
        try:
            folders = []
            for item in self.base_folder.iterdir():
                if item.is_dir():
                    folders.append(item.name)
            return sorted(folders)

        except Exception as e:
            print(f"列出案件資料夾失敗: {e}")
            return []

    def get_case_folder_info(self, case_data) -> Dict[str, Any]:
        """取得案件資料夾詳細資訊"""
        try:
            folder_path = self.get_case_folder_path(case_data)

            if not folder_path or not os.path.exists(folder_path):
                return {
                    'exists': False,
                    'path': None,
                    'has_files': False,
                    'file_count': 0,
                    'size_mb': 0,
                    'subfolders': []
                }

            # 計算檔案數量和大小
            total_files = 0
            total_size = 0
            subfolders = []

            for root, dirs, files in os.walk(folder_path):
                total_files += len(files)

                # 記錄子資料夾
                if root == folder_path:
                    subfolders = dirs.copy()

                for file in files:
                    try:
                        file_path = os.path.join(root, file)
                        total_size += os.path.getsize(file_path)
                    except:
                        pass

            return {
                'exists': True,
                'path': folder_path,
                'has_files': total_files > 0,
                'file_count': total_files,
                'size_mb': round(total_size / (1024 * 1024), 2),
                'subfolders': subfolders
            }

        except Exception as e:
            print(f"取得案件資料夾資訊失敗: {e}")
            return {
                'exists': False,
                'path': None,
                'has_files': False,
                'file_count': 0,
                'size_mb': 0,
                'subfolders': [],
                'error': str(e)
            }

    def delete_case_folder(self, case_data) -> bool:
        """刪除案件資料夾"""
        try:
            case_folder = self.get_case_folder_path(case_data)
            if case_folder and os.path.exists(case_folder):
                shutil.rmtree(case_folder)
                print(f"✅ 刪除案件資料夾: {case_folder}")
                return True
            return False

        except Exception as e:
            print(f"刪除案件資料夾失敗: {e}")
            return False

    def update_case_info_excel(self, case_data) -> bool:
        """更新案件資訊Excel檔案"""
        try:
            case_folder_path = self.get_case_folder_path(case_data)
            if not case_folder_path:
                print(f"找不到案件資料夾")
                return False

            case_folder = Path(case_folder_path)
            return self._create_case_info_excel(case_folder, case_data)

        except Exception as e:
            print(f"更新案件資訊Excel檔案失敗: {e}")
            return False

    def validate_folder_structure(self, case_data) -> Dict[str, Any]:
        """驗證案件資料夾結構"""
        try:
            folder_path = self.get_case_folder_path(case_data)

            if not folder_path:
                return {
                    'valid': False,
                    'message': '案件資料夾不存在',
                    'missing_folders': self.default_subfolders,
                    'existing_folders': []
                }

            existing_folders = []
            missing_folders = []

            for subfolder in self.default_subfolders:
                subfolder_path = os.path.join(folder_path, subfolder)
                if os.path.exists(subfolder_path):
                    existing_folders.append(subfolder)
                else:
                    missing_folders.append(subfolder)

            valid = len(missing_folders) == 0

            return {
                'valid': valid,
                'message': '資料夾結構完整' if valid else '部分子資料夾遺失',
                'missing_folders': missing_folders,
                'existing_folders': existing_folders
            }

        except Exception as e:
            return {
                'valid': False,
                'message': f'驗證失敗: {e}',
                'missing_folders': [],
                'existing_folders': []
            }

    def repair_folder_structure(self, case_data) -> bool:
        """修復案件資料夾結構"""
        try:
            folder_path = self.get_case_folder_path(case_data)

            if not folder_path:
                print("案件資料夾不存在，無法修復")
                return False

            # 建立遺失的子資料夾
            for subfolder in self.default_subfolders:
                subfolder_path = os.path.join(folder_path, subfolder)
                if not os.path.exists(subfolder_path):
                    os.makedirs(subfolder_path, exist_ok=True)
                    print(f"✅ 建立遺失的子資料夾: {subfolder}")

            print(f"✅ 修復完成: {folder_path}")
            return True

        except Exception as e:
            print(f"修復資料夾結構失敗: {e}")
            return False