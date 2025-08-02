#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
資料夾服務 - 修正版本
提供案件資料夾管理的業務邏輯，簡化實現避免依賴不存在的模組
"""

from typing import List, Optional, Dict, Any, Tuple
from models.case_model import CaseData
from datetime import datetime
import os
import shutil


class FolderService:
    """資料夾業務邏輯服務 - 簡化版本"""

    def __init__(self, base_data_folder: str):
        """
        初始化資料夾服務

        Args:
            base_data_folder: 基礎資料資料夾路徑
        """
        self.base_data_folder = base_data_folder

        # 確保基礎資料夾存在
        os.makedirs(base_data_folder, exist_ok=True)

        # 初始化資料夾類型配置
        self.case_type_folders = {
            '民事': '民事案件',
            '刑事': '刑事案件',
            '行政': '行政案件',
            '勞工': '勞工案件',
            '家事': '家事案件',
            '商事': '商事案件'
        }

        # 標準資料夾結構
        self.standard_subfolders = ['案件資訊', '進度追蹤', '狀紙']

        print("✅ FolderService 初始化完成")

    # ==================== 資料夾路徑管理 ====================

    def get_case_folder_path(self, case_data: CaseData) -> Optional[str]:
        """
        取得案件資料夾路徑

        Args:
            case_data: 案件資料

        Returns:
            案件資料夾路徑，如果失敗則返回None
        """
        try:
            # 1. 取得案件類型資料夾
            type_folder = self._get_case_type_folder_path(case_data.case_type)
            if not type_folder:
                return None

            # 2. 生成案件資料夾名稱
            safe_client_name = self._sanitize_folder_name(case_data.client)
            safe_case_id = self._sanitize_folder_name(case_data.case_id)

            # 使用格式：案件編號_當事人姓名
            case_folder_name = f"{safe_case_id}_{safe_client_name}"
            case_folder_path = os.path.join(type_folder, case_folder_name)

            return case_folder_path

        except Exception as e:
            print(f"❌ 取得案件資料夾路徑失敗: {e}")
            return None

    def _get_case_type_folder_path(self, case_type: str) -> Optional[str]:
        """取得案件類型對應的資料夾路徑"""
        try:
            folder_name = self.case_type_folders.get(case_type, case_type)
            folder_path = os.path.join(self.base_data_folder, folder_name)

            # 確保資料夾存在
            os.makedirs(folder_path, exist_ok=True)

            return folder_path
        except Exception as e:
            print(f"❌ 取得案件類型資料夾路徑失敗: {e}")
            return None

    def _sanitize_folder_name(self, name: str) -> str:
        """清理資料夾名稱，移除不安全字符"""
        if not name:
            return "未命名"

        # 移除或替換不安全字符
        unsafe_chars = '<>:"/\\|?*'
        safe_name = name
        for char in unsafe_chars:
            safe_name = safe_name.replace(char, '_')

        # 限制長度並移除前後空白
        safe_name = safe_name.strip()[:50]

        return safe_name if safe_name else "未命名"

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

            # 6. 建立案件資訊Excel檔案
            self._create_case_info_excel(case_data, case_folder_path)

            print(f"✅ 成功建立案件資料夾結構: {case_folder_path}")
            return True, f"成功建立資料夾: {case_folder_path}"

        except Exception as e:
            error_msg = f"建立案件資料夾失敗: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg

    def _create_case_info_excel(self, case_data: CaseData, case_folder_path: str):
        """建立案件資訊Excel檔案"""
        try:
            # 簡化實現：建立文字檔案而非Excel
            info_folder = os.path.join(case_folder_path, '案件資訊')
            info_file = os.path.join(info_folder, '案件基本資料.txt')

            case_info = f"""案件基本資料
================

案件編號：{case_data.case_id}
案件類型：{case_data.case_type}
當事人：{case_data.client}
委任律師：{case_data.lawyer or '未指定'}
法務人員：{case_data.legal_affairs or '未指定'}
案由：{case_data.case_reason or '未填寫'}
案號：{case_data.case_number or '未填寫'}
對造：{case_data.opposing_party or '未填寫'}
負責法院：{case_data.court or '未填寫'}
負責股別：{case_data.division or '未填寫'}
目前進度：{case_data.progress}
建立日期：{case_data.created_date.strftime('%Y-%m-%d %H:%M:%S') if case_data.created_date else '未知'}
更新日期：{case_data.updated_date.strftime('%Y-%m-%d %H:%M:%S') if case_data.updated_date else '未知'}
"""

            with open(info_file, 'w', encoding='utf-8') as f:
                f.write(case_info)

            print(f"✅ 建立案件資訊檔案: {info_file}")

        except Exception as e:
            print(f"⚠️ 建立案件資訊檔案失敗: {e}")

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
                    'size_mb': 0,
                    'file_count': 0,
                    'subfolders': [],
                    'last_modified': None
                }

            exists = os.path.exists(folder_path)

            if not exists:
                return {
                    'exists': False,
                    'path': folder_path,
                    'size_mb': 0,
                    'file_count': 0,
                    'subfolders': [],
                    'last_modified': None
                }

            # 計算資料夾大小和檔案數量
            total_size = 0
            file_count = 0
            subfolders = []

            for root, dirs, files in os.walk(folder_path):
                subfolders.extend(dirs)
                file_count += len(files)
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        total_size += os.path.getsize(file_path)
                    except OSError:
                        pass

            # 取得最後修改時間
            try:
                last_modified = datetime.fromtimestamp(os.path.getmtime(folder_path))
            except OSError:
                last_modified = None

            return {
                'exists': True,
                'path': folder_path,
                'size_mb': total_size / (1024 * 1024),
                'file_count': file_count,
                'subfolders': list(set(subfolders)),
                'last_modified': last_modified
            }

        except Exception as e:
            print(f"❌ 取得資料夾資訊失敗: {e}")
            return {
                'exists': False,
                'path': None,
                'size_mb': 0,
                'file_count': 0,
                'subfolders': [],
                'last_modified': None,
                'error': str(e)
            }

    # ==================== 資料夾操作 ====================

    def delete_case_folder(self, case_data: CaseData) -> Tuple[bool, str]:
        """
        刪除案件資料夾

        Args:
            case_data: 案件資料

        Returns:
            (成功與否, 結果訊息)
        """
        try:
            folder_path = self.get_case_folder_path(case_data)

            if not folder_path or not os.path.exists(folder_path):
                return True, "資料夾不存在，無需刪除"

            # 備份資料夾
            backup_result = self._backup_folder(folder_path, case_data)
            if not backup_result[0]:
                print(f"⚠️ 備份失敗: {backup_result[1]}")

            # 刪除資料夾
            shutil.rmtree(folder_path)

            print(f"✅ 成功刪除案件資料夾: {folder_path}")
            return True, f"成功刪除資料夾: {folder_path}"

        except Exception as e:
            error_msg = f"刪除資料夾失敗: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg

    def _backup_folder(self, folder_path: str, case_data: CaseData) -> Tuple[bool, str]:
        """備份資料夾"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_folder = os.path.join(self.base_data_folder, "_backups")
            os.makedirs(backup_folder, exist_ok=True)

            backup_name = f"{case_data.case_id}_{case_data.client}_{timestamp}"
            backup_name = self._sanitize_folder_name(backup_name)
            backup_path = os.path.join(backup_folder, backup_name)

            shutil.copytree(folder_path, backup_path)

            print(f"✅ 備份完成: {backup_path}")
            return True, f"備份到: {backup_path}"

        except Exception as e:
            return False, f"備份失敗: {str(e)}"

    # ==================== 進度資料夾管理 ====================

    def create_progress_folder(self, case_data: CaseData, stage_name: str) -> Tuple[bool, str]:
        """
        建立進度階段資料夾

        Args:
            case_data: 案件資料
            stage_name: 階段名稱

        Returns:
            (成功與否, 結果訊息)
        """
        try:
            if not stage_name or stage_name.strip() == "":
                return False, "階段名稱不能為空"

            case_folder = self.get_case_folder_path(case_data)
            if not case_folder or not os.path.exists(case_folder):
                return False, f"案件資料夾不存在: {case_data.client}"

            progress_folder = os.path.join(case_folder, '進度追蹤')
            safe_stage_name = self._sanitize_folder_name(stage_name)
            stage_folder = os.path.join(progress_folder, safe_stage_name)

            os.makedirs(stage_folder, exist_ok=True)

            print(f"✅ 建立進度資料夾: {stage_folder}")
            return True, f"成功建立進度資料夾: {stage_name}"

        except Exception as e:
            error_msg = f"建立進度資料夾失敗: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg

    # ==================== 輔助方法 ====================

    def validate_folder_structure(self, case_data: CaseData) -> Dict[str, Any]:
        """驗證案件資料夾結構"""
        try:
            folder_path = self.get_case_folder_path(case_data)

            if not folder_path or not os.path.exists(folder_path):
                return {
                    'is_valid': False,
                    'missing_folders': self.standard_subfolders,
                    'path': folder_path
                }

            missing_folders = []
            for folder in self.standard_subfolders:
                subfolder_path = os.path.join(folder_path, folder)
                if not os.path.exists(subfolder_path):
                    missing_folders.append(folder)

            return {
                'is_valid': len(missing_folders) == 0,
                'missing_folders': missing_folders,
                'path': folder_path
            }

        except Exception as e:
            return {
                'is_valid': False,
                'missing_folders': self.standard_subfolders,
                'path': None,
                'error': str(e)
            }

    def list_case_folders(self) -> List[Dict[str, Any]]:
        """列出所有案件資料夾"""
        try:
            folders = []

            for case_type_folder in self.case_type_folders.values():
                type_folder_path = os.path.join(self.base_data_folder, case_type_folder)

                if os.path.exists(type_folder_path):
                    for item in os.listdir(type_folder_path):
                        item_path = os.path.join(type_folder_path, item)
                        if os.path.isdir(item_path):
                            try:
                                # 解析資料夾名稱（假設格式：案件編號_當事人姓名）
                                if '_' in item:
                                    case_id, client = item.split('_', 1)
                                else:
                                    case_id, client = item, "未知"

                                folders.append({
                                    'case_id': case_id,
                                    'client': client,
                                    'path': item_path,
                                    'case_type': case_type_folder,
                                    'last_modified': datetime.fromtimestamp(os.path.getmtime(item_path))
                                })
                            except Exception as e:
                                print(f"⚠️ 解析資料夾失敗: {item} - {e}")

            return folders

        except Exception as e:
            print(f"❌ 列出案件資料夾失敗: {e}")
            return []