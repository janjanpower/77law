#!/usr/bin/env python3
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
           "進度追蹤",
           "狀紙"
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
        """
        取得案件的資料夾路徑 - 邏輯層方法

        Args:
            case_data: CaseData物件或字典

        Returns:
            Optional[str]: 資料夾路徑或None
        """
        try:
            # 🔥 關鍵修復：型別檢查和轉換
            if isinstance(case_data, str):
                print(f"❌ 錯誤：收到字串參數 '{case_data}'，預期為 CaseData 物件")
                return None

            # 🔥 處理字典型別的案件資料
            if isinstance(case_data, dict):
                case_type = case_data.get('case_type')
                client = case_data.get('client')
            elif hasattr(case_data, 'case_type') and hasattr(case_data, 'client'):
                # 🔥 處理 CaseData 物件
                case_type = case_data.case_type
                client = case_data.client
            else:
                print(f"❌ 無法識別的案件資料格式: {type(case_data)}")
                return None

            # 🔥 驗證必要欄位
            if not case_type or not client:
                print(f"❌ 案件資料缺少必要欄位 - case_type: {case_type}, client: {client}")
                return None

            # 取得案件類型資料夾
            case_type_folder = self._get_case_type_folder(case_type)
            if not case_type_folder:
                print(f"❌ 無法取得案件類型資料夾: {case_type}")
                return None

            # 清理當事人姓名並建構路徑
            safe_client_name = self._sanitize_folder_name(client)
            client_folder = os.path.join(case_type_folder, safe_client_name)

            return client_folder if os.path.exists(client_folder) else None

        except Exception as e:
            print(f"❌ 取得案件資料夾路徑失敗: {e}")
            import traceback
            traceback.print_exc()
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

# ==================== 輔助驗證方法 ====================

# 3. 新增驗證輔助方法 (加入到 utils/folder_manager.py)
def validate_case_data(self, case_data) -> bool:
    """
    驗證案件資料的完整性

    Args:
        case_data: 案件資料

    Returns:
        bool: 是否有效
    """
    try:
        # 檢查是否為空
        if not case_data:
            print("❌ 案件資料為空")
            return False

        # 檢查是否為字串（錯誤的參數型別）
        if isinstance(case_data, str):
            print(f"❌ 錯誤：收到字串參數，應該是案件資料物件")
            return False

        # 檢查必要屬性
        required_attrs = ['case_type', 'client']

        if isinstance(case_data, dict):
            for attr in required_attrs:
                if attr not in case_data or not case_data[attr]:
                    print(f"❌ 案件資料缺少必要欄位: {attr}")
                    return False
        else:
            for attr in required_attrs:
                if not hasattr(case_data, attr) or not getattr(case_data, attr):
                    print(f"❌ 案件資料缺少必要屬性: {attr}")
                    return False

        return True

    except Exception as e:
        print(f"❌ 驗證案件資料時發生錯誤: {e}")
        return False


