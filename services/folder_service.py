#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
修復版資料夾服務 - 確保資料夾建立成功
檔案路徑: services/folder_service.py (覆蓋原版)
"""

import os
import shutil
from typing import Dict, Any, List, Tuple, Optional
from models.case_model import CaseData
from config.settings import AppConfig


class FolderService:
    """修復版資料夾管理服務 - 確保資料夾建立功能正常"""

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
            '狀紙',         # 存放法律文件
        ]

        # 確保基礎資料夾存在
        try:
            os.makedirs(base_data_folder, exist_ok=True)
            print(f"✅ FolderService 初始化完成，基礎路徑: {base_data_folder}")
        except Exception as e:
            print(f"❌ FolderService 初始化失敗: {e}")

    def create_case_folder_structure(self, case_data: CaseData, force_recreate: bool = False) -> Tuple[bool, str]:
        """
        建立案件資料夾結構（修復版 - 確保成功）

        Args:
            case_data: 案件資料
            force_recreate: 是否強制重新建立

        Returns:
            (成功與否, 結果訊息)
        """
        try:
            print(f"🏗️ 開始建立案件資料夾結構: {case_data.client} ({case_data.case_type})")

            # 1. 驗證輸入資料
            if not case_data or not case_data.client or not case_data.case_type:
                error_msg = "案件資料不完整，無法建立資料夾"
                print(f"❌ {error_msg}")
                return False, error_msg

            # 2. 取得案件資料夾路徑
            case_folder_path = self.get_case_folder_path(case_data)
            if not case_folder_path:
                error_msg = "無法確定案件資料夾路徑"
                print(f"❌ {error_msg}")
                return False, error_msg

            print(f"📂 目標資料夾路徑: {case_folder_path}")

            # 3. 檢查是否已存在
            if os.path.exists(case_folder_path) and not force_recreate:
                success_msg = f"資料夾已存在: {case_folder_path}"
                print(f"✅ {success_msg}")
                return True, success_msg

            # 4. 建立主要案件資料夾
            try:
                os.makedirs(case_folder_path, exist_ok=True)
                print(f"✅ 成功建立主資料夾: {os.path.basename(case_folder_path)}")
            except Exception as e:
                error_msg = f"建立主資料夾失敗: {str(e)}"
                print(f"❌ {error_msg}")
                return False, error_msg

            # 5. 建立標準子資料夾
            created_folders = []
            failed_folders = []

            for subfolder in self.standard_subfolders:
                try:
                    subfolder_path = os.path.join(case_folder_path, subfolder)
                    os.makedirs(subfolder_path, exist_ok=True)
                    created_folders.append(subfolder)
                    print(f"  ✅ 建立子資料夾: {subfolder}")
                except Exception as e:
                    failed_folders.append(f"{subfolder}: {str(e)}")
                    print(f"  ❌ 建立子資料夾失敗 {subfolder}: {e}")

            # 6. 建立案件資訊 Excel 檔案（如果可能）
            try:
                self._create_case_info_excel(case_folder_path, case_data)
            except Exception as e:
                print(f"⚠️ 建立案件資訊 Excel 失敗: {e}")

            # 7. 建立進度階段資料夾（如果案件有進度資料）
            if hasattr(case_data, 'progress_stages') and case_data.progress_stages:
                self._create_progress_stage_folders(case_folder_path, case_data)

            # 8. 產生結果訊息
            if failed_folders:
                warning_msg = f"資料夾建立完成，但部分子資料夾失敗: {', '.join(failed_folders)}"
                print(f"⚠️ {warning_msg}")
                return True, warning_msg
            else:
                success_msg = f"資料夾結構建立成功: {case_folder_path}"
                print(f"✅ {success_msg}")
                return True, success_msg

        except Exception as e:
            error_msg = f"建立案件資料夾結構失敗: {str(e)}"
            print(f"❌ {error_msg}")
            import traceback
            traceback.print_exc()

            # 嘗試備用建立方法
            return self._create_basic_folder_fallback(case_data)

    def get_case_folder_path(self, case_data: CaseData) -> Optional[str]:
        """
        取得案件資料夾路徑

        Args:
            case_data: 案件資料

        Returns:
            Optional[str]: 資料夾路徑或None
        """
        try:
            # 取得案件類型資料夾名稱
            case_type_folder_name = AppConfig.CASE_TYPE_FOLDERS.get(case_data.case_type)
            if not case_type_folder_name:
                print(f"❌ 未知的案件類型: {case_data.case_type}")
                # 使用原始案件類型作為資料夾名稱
                case_type_folder_name = case_data.case_type

            # 清理當事人姓名作為資料夾名稱
            safe_client_name = self._sanitize_folder_name(case_data.client)

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

    def _sanitize_folder_name(self, name: str) -> str:
        """
        清理名稱用於資料夾命名

        Args:
            name: 原始名稱

        Returns:
            str: 清理後的名稱
        """
        try:
            if not name or not name.strip():
                return "未命名"

            # 移除或替換不允許的字元
            unsafe_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
            safe_name = name
            for char in unsafe_chars:
                safe_name = safe_name.replace(char, '_')

            # 移除前後空白並限制長度
            safe_name = safe_name.strip()
            if len(safe_name) > 50:
                safe_name = safe_name[:50]

            # 確保不為空
            if not safe_name:
                safe_name = "未命名"

            return safe_name

        except Exception as e:
            print(f"❌ 清理資料夾名稱失敗: {e}")
            return "未知客戶"

    def _create_basic_folder_fallback(self, case_data: CaseData) -> Tuple[bool, str]:
        """
        備用的基本資料夾建立方法

        Args:
            case_data: 案件資料

        Returns:
            Tuple[bool, str]: (是否成功, 結果訊息)
        """
        try:
            print("🔧 使用備用方法建立基本資料夾結構...")

            # 確保案件類型資料夾存在
            case_type_folder_name = AppConfig.CASE_TYPE_FOLDERS.get(
                case_data.case_type, case_data.case_type
            )
            case_type_path = os.path.join(self.base_data_folder, case_type_folder_name)
            os.makedirs(case_type_path, exist_ok=True)

            # 建立當事人資料夾
            safe_client_name = self._sanitize_folder_name(case_data.client)
            client_folder = os.path.join(case_type_path, safe_client_name)
            os.makedirs(client_folder, exist_ok=True)

            # 建立最基本的子資料夾
            basic_folders = ['案件資訊', '進度追蹤', '狀紙']
            for folder_name in basic_folders:
                folder_path = os.path.join(client_folder, folder_name)
                os.makedirs(folder_path, exist_ok=True)
                print(f"  ✅ 建立基本資料夾: {folder_name}")

            success_msg = f"備用方法成功建立基本資料夾: {client_folder}"
            print(f"✅ {success_msg}")
            return True, success_msg

        except Exception as e:
            error_msg = f"備用建立方法也失敗: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg

    def _create_case_info_excel(self, case_folder_path: str, case_data: CaseData):
        """
        建立案件資訊 Excel 檔案

        Args:
            case_folder_path: 案件資料夾路徑
            case_data: 案件資料
        """
        try:
            import pandas as pd
            from datetime import datetime

            # 準備案件資訊資料
            case_info = {
                '案件編號': [case_data.case_id],
                '當事人': [case_data.client],
                '案件類型': [case_data.case_type],
                '建立日期': [datetime.now().strftime('%Y-%m-%d')],
                '狀態': [getattr(case_data, 'status', '待處理')],
                '備註': [getattr(case_data, 'notes', '')]
            }

            # 建立 DataFrame
            df = pd.DataFrame(case_info)

            # 儲存為 Excel 檔案
            excel_file_path = os.path.join(case_folder_path, '案件資訊', '案件基本資料.xlsx')
            df.to_excel(excel_file_path, index=False, engine='openpyxl')

            print(f"✅ 建立案件資訊 Excel: {excel_file_path}")

        except ImportError:
            print("⚠️ pandas 或 openpyxl 不可用，跳過 Excel 檔案建立")
        except Exception as e:
            print(f"⚠️ 建立案件資訊 Excel 失敗: {e}")

    def _create_progress_stage_folders(self, case_folder_path: str, case_data: CaseData):
        """
        建立進度階段資料夾

        Args:
            case_folder_path: 案件資料夾路徑
            case_data: 案件資料
        """
        try:
            progress_base_path = os.path.join(case_folder_path, '進度追蹤')

            for stage_name in case_data.progress_stages.keys():
                safe_stage_name = self._sanitize_folder_name(stage_name)
                stage_path = os.path.join(progress_base_path, safe_stage_name)
                os.makedirs(stage_path, exist_ok=True)
                print(f"  ✅ 建立進度階段資料夾: {stage_name}")

        except Exception as e:
            print(f"⚠️ 建立進度階段資料夾失敗: {e}")

    def validate_folder_structure(self, case_data: CaseData) -> Dict[str, Any]:
        """
        驗證案件資料夾結構

        Args:
            case_data: 案件資料

        Returns:
            Dict: 驗證結果
        """
        validation_result = {
            'is_valid': False,
            'exists': False,
            'missing_folders': [],
            'extra_folders': [],
            'path': None,
            'issues': []
        }

        try:
            case_folder_path = self.get_case_folder_path(case_data)
            validation_result['path'] = case_folder_path

            if not case_folder_path:
                validation_result['issues'].append("無法確定資料夾路徑")
                return validation_result

            if not os.path.exists(case_folder_path):
                validation_result['issues'].append("案件資料夾不存在")
                return validation_result

            validation_result['exists'] = True

            # 檢查標準子資料夾
            for subfolder in self.standard_subfolders:
                subfolder_path = os.path.join(case_folder_path, subfolder)
                if not os.path.exists(subfolder_path):
                    validation_result['missing_folders'].append(subfolder)

            # 檢查是否有額外的資料夾
            if os.path.exists(case_folder_path):
                existing_folders = [
                    item for item in os.listdir(case_folder_path)
                    if os.path.isdir(os.path.join(case_folder_path, item))
                ]

                for folder in existing_folders:
                    if folder not in self.standard_subfolders:
                        validation_result['extra_folders'].append(folder)

            # 判斷整體有效性
            validation_result['is_valid'] = (
                validation_result['exists'] and
                len(validation_result['missing_folders']) == 0
            )

            if not validation_result['is_valid']:
                if validation_result['missing_folders']:
                    validation_result['issues'].append(
                        f"缺少資料夾: {', '.join(validation_result['missing_folders'])}"
                    )

        except Exception as e:
            validation_result['issues'].append(f"驗證過程異常: {str(e)}")

        return validation_result

    def repair_folder_structure(self, case_data: CaseData) -> Tuple[bool, str]:
        """
        修復案件資料夾結構

        Args:
            case_data: 案件資料

        Returns:
            Tuple[bool, str]: (是否成功, 結果訊息)
        """
        try:
            print(f"🔧 開始修復案件資料夾結構: {case_data.client}")

            # 驗證當前狀態
            validation = self.validate_folder_structure(case_data)

            if validation['is_valid']:
                return True, "資料夾結構完整，無需修復"

            if not validation['exists']:
                # 資料夾不存在，重新建立
                return self.create_case_folder_structure(case_data, force_recreate=True)

            # 資料夾存在但不完整，修復缺少的部分
            case_folder_path = validation['path']
            repaired_folders = []

            for missing_folder in validation['missing_folders']:
                try:
                    missing_path = os.path.join(case_folder_path, missing_folder)
                    os.makedirs(missing_path, exist_ok=True)
                    repaired_folders.append(missing_folder)
                    print(f"  ✅ 修復資料夾: {missing_folder}")
                except Exception as e:
                    print(f"  ❌ 修復資料夾失敗 {missing_folder}: {e}")

            if repaired_folders:
                success_msg = f"修復完成，已修復: {', '.join(repaired_folders)}"
                print(f"✅ {success_msg}")
                return True, success_msg
            else:
                error_msg = "修復失敗，無法建立缺少的資料夾"
                print(f"❌ {error_msg}")
                return False, error_msg

        except Exception as e:
            error_msg = f"修復過程異常: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg

    def get_folder_info(self, case_data: CaseData) -> Dict[str, Any]:
        """
        取得案件資料夾詳細資訊

        Args:
            case_data: 案件資料

        Returns:
            Dict: 資料夾資訊
        """
        info = {
            'path': None,
            'exists': False,
            'size_mb': 0.0,
            'file_count': 0,
            'folder_count': 0,
            'subfolders': [],
            'validation': None
        }

        try:
            case_folder_path = self.get_case_folder_path(case_data)
            info['path'] = case_folder_path

            if not case_folder_path or not os.path.exists(case_folder_path):
                return info

            info['exists'] = True

            # 計算大小和檔案數量
            total_size = 0
            file_count = 0
            folder_count = 0

            for root, dirs, files in os.walk(case_folder_path):
                folder_count += len(dirs)
                file_count += len(files)

                for file in files:
                    try:
                        file_path = os.path.join(root, file)
                        total_size += os.path.getsize(file_path)
                    except:
                        pass

            info['size_mb'] = round(total_size / (1024 * 1024), 2)
            info['file_count'] = file_count
            info['folder_count'] = folder_count

            # 列出直接子資料夾
            if os.path.exists(case_folder_path):
                info['subfolders'] = [
                    item for item in os.listdir(case_folder_path)
                    if os.path.isdir(os.path.join(case_folder_path, item))
                ]

            # 驗證結構
            info['validation'] = self.validate_folder_structure(case_data)

        except Exception as e:
            info['error'] = str(e)

        return info

    def delete_case_folder(self, case_data: CaseData, confirm: bool = False) -> Tuple[bool, str]:
        """
        刪除案件資料夾

        Args:
            case_data: 案件資料
            confirm: 是否確認刪除

        Returns:
            Tuple[bool, str]: (是否成功, 結果訊息)
        """
        try:
            if not confirm:
                return False, "請確認刪除操作"

            case_folder_path = self.get_case_folder_path(case_data)
            if not case_folder_path:
                return False, "無法確定資料夾路徑"

            if not os.path.exists(case_folder_path):
                return True, "資料夾不存在，視為刪除成功"

            # 刪除資料夾
            shutil.rmtree(case_folder_path)

            success_msg = f"成功刪除案件資料夾: {case_folder_path}"
            print(f"✅ {success_msg}")
            return True, success_msg

        except Exception as e:
            error_msg = f"刪除案件資料夾失敗: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg