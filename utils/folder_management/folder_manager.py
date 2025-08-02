FOLDER_MANAGER_CONTENT = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
資料夾管理器
提供統一的資料夾操作功能
"""

import os
import shutil
from typing import Optional, List, Dict, Any
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
            folder_name = self._generate_folder_name(case_data)
            case_folder = self.base_folder / folder_name

            case_folder.mkdir(parents=True, exist_ok=True)

            for subfolder in self.default_subfolders:
                (case_folder / subfolder).mkdir(exist_ok=True)

            self._create_case_info_excel(case_folder, case_data)
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
            if hasattr(case_data, 'client') and hasattr(case_data, 'case_type'):
                client_name = str(case_data.client).replace('/', '_').replace('\\\\', '_')
                case_type = str(case_data.case_type).replace('/', '_').replace('\\\\', '_')
                return f"{client_name}_{case_type}"
            elif hasattr(case_data, 'client'):
                client_name = str(case_data.client).replace('/', '_').replace('\\\\', '_')
                return client_name
            elif hasattr(case_data, 'case_number'):
                case_number = str(case_data.case_number).replace('/', '_').replace('\\\\', '_')
                return f"案件_{case_number}"
            else:
                return f"案件_{id(case_data)}"
        except Exception:
            return f"案件_{id(case_data)}"

    def _create_case_info_excel(self, case_folder: Path, case_data) -> bool:
        """建立案件資訊Excel檔案"""
        try:
            import pandas as pd

            case_info = {}
            if hasattr(case_data, '__dict__'):
                case_info = case_data.__dict__.copy()
            else:
                case_info = dict(case_data) if isinstance(case_data, dict) else {}

            basic_fields = {
                '委託人': case_info.get('client', ''),
                '案件類型': case_info.get('case_type', ''),
                '案件編號': case_info.get('case_number', ''),
                '承辦律師': case_info.get('lawyer', ''),
                '案件狀態': case_info.get('status', '進行中'),
                '委託日期': case_info.get('commission_date', ''),
                '備註': case_info.get('notes', '')
            }

            df = pd.DataFrame([basic_fields])

            info_folder = case_folder / "案件資訊"
            info_folder.mkdir(exist_ok=True)

            excel_path = info_folder / "案件基本資料.xlsx"
            df.to_excel(excel_path, index=False, engine='openpyxl')

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
        except Exception:
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
                    'size_mb': 0
                }

            total_files = 0
            total_size = 0

            for root, dirs, files in os.walk(folder_path):
                total_files += len(files)
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
                'size_mb': round(total_size / (1024 * 1024), 2)
            }

        except Exception:
            return {
                'exists': False,
                'path': None,
                'has_files': False,
                'file_count': 0,
                'size_mb': 0
            }
'''