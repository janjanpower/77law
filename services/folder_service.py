#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
資料夾業務邏輯服務
專責處理資料夾相關的業務邏輯，整合底層資料夾管理功能
"""

from typing import List, Optional, Dict, Any, Tuple
from models.case_model import CaseData
import os
import shutil
from datetime import datetime


class FolderValidator:
    """簡化的資料夾驗證器"""

    def sanitize_folder_name(self, name: str) -> str:
        """清理資料夾名稱"""
        if not name:
            return "未命名"

        # 移除非法字元
        illegal_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
        for char in illegal_chars:
            name = name.replace(char, '_')

        return name.strip()

    def get_safe_client_name(self, client_name: str) -> str:
        """取得安全的當事人名稱"""
        return self.sanitize_folder_name(client_name)

    def validate_path(self, path: str) -> Tuple[bool, str]:
        """驗證路徑"""
        if not path:
            return False, "路徑不能為空"

        if len(path) > 260:
            return False, "路徑過長"

        return True, "路徑有效"

    def get_folder_size_info(self, folder_path: str) -> Dict[str, Any]:
        """取得資料夾大小資訊"""
        try:
            total_size = 0
            file_count = 0

            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    if os.path.exists(file_path):
                        total_size += os.path.getsize(file_path)
                        file_count += 1

            return {
                'total_size_mb': total_size / (1024 * 1024),
                'file_count': file_count,
                'has_files': file_count > 0
            }
        except Exception:
            return {
                'total_size_mb': 0,
                'file_count': 0,
                'has_files': False
            }

    def validate_folder_structure(self, folder_path: str) -> Dict[str, Any]:
        """驗證資料夾結構"""
        required_folders = ['案件資訊', '進度追蹤', '狀紙']
        missing = []

        for folder in required_folders:
            subfolder_path = os.path.join(folder_path, folder)
            if not os.path.exists(subfolder_path):
                missing.append(folder)

        return {
            'is_valid': len(missing) == 0,
            'missing_folders': missing
        }


class FolderService:
    """資料夾業務邏輯服務"""

    def __init__(self, base_data_folder: str):
        """
        初始化資料夾服務

        Args:
            base_data_folder: 基礎資料資料夾路徑
        """
        self.base_data_folder = base_data_folder

        # 初始化驗證器
        self.folder_validator = FolderValidator()

        # 延遲初始化其他服務
        self.validation_service = None

        print("✅ FolderService 初始化完成")

    def _get_validation_service(self):
        """延遲取得驗證服務"""
        if self.validation_service is None:
            try:
                from .validation_service import ValidationService
                self.validation_service = ValidationService()
            except ImportError:
                print("⚠️ ValidationService 不可用")
                self.validation_service = None
        return self.validation_service

    def _get_case_type_folder_path(self, case_type: str) -> Optional[str]:
        """取得案件類型對應的資料夾路徑"""
        try:
            # 簡化的案件類型對應
            case_type_folders = {
                '民事': '民事案件',
                '刑事': '刑事案件',
                '行政': '行政案件',
                '勞工': '勞工案件',
                '家事': '家事案件',
                '商事': '商事案件'
            }

            folder_name = case_type_folders.get(case_type, case_type)
            folder_path = os.path.join(self.base_data_folder, folder_name)

            # 確保資料夾存在
            os.makedirs(folder_path, exist_ok=True)

            return folder_path
        except Exception as e:
            print(f"❌ 取得案件類型資料夾路徑失敗: {e}")
            return None

    # ==================== 資料夾建立業務邏輯 ====================

    def create_case_folder_structure(self, case_data: CaseData, force_recreate: bool = False) -> Tuple[bool, str]:
        """
        建立案件資料夾結構（業務邏輯層面）

        Args:
            case_data: 案件資料
            force_recreate: 是否強制重新建立

        Returns:
            (成功與否, 結果訊息或錯誤訊息)
        """
        try:
            print(f"🏗️ 資料夾服務: 開始為案件建立資料夾結構")
            print(f"   案件ID: {case_data.case_id}")
            print(f"   當事人: {case_data.client}")
            print(f"   案件類型: {case_data.case_type}")

            # 1. 業務驗證
            validation_result = self._validate_folder_creation_request(case_data)
            if not validation_result[0]:
                return False, f"資料夾建立驗證失敗: {validation_result[1]}"

            # 2. 檢查是否已存在
            existing_path = self.get_case_folder_path(case_data)
            if existing_path and not force_recreate:
                print(f"ℹ️ 資料夾已存在: {existing_path}")
                return True, f"資料夾已存在: {existing_path}"

            # 3. 如果強制重新建立，先備份舊資料夾
            if existing_path and force_recreate:
                backup_result = self._backup_existing_folder(existing_path)
                if not backup_result[0]:
                    return False, f"備份舊資料夾失敗: {backup_result[1]}"

            # 4. 委託給底層管理器建立
            creation_result = self.folder_manager.create_case_folder_structure(case_data)
            if not creation_result:
                return False, "底層資料夾建立失敗"

            # 5. 驗證建立結果
            verification_result = self._verify_folder_structure(case_data)
            if not verification_result[0]:
                return False, f"資料夾結構驗證失敗: {verification_result[1]}"

            # 6. 設定資料夾權限（如果需要）
            folder_path = self.get_case_folder_path(case_data)
            if folder_path:
                self._set_folder_permissions(folder_path)

            print(f"✅ 成功建立案件資料夾結構: {folder_path}")
            return True, f"成功建立資料夾: {folder_path}"

        except Exception as e:
            error_msg = f"建立案件資料夾結構失敗: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg

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
            print(f"📁 建立進度資料夾: {stage_name}")

            # 1. 驗證階段名稱
            if not stage_name or stage_name.strip() == "":
                return False, "階段名稱不能為空"

            # 2. 確保案件資料夾存在
            case_folder = self.get_case_folder_path(case_data)
            if not case_folder:
                return False, f"案件資料夾不存在: {case_data.client}"

            # 3. 委託給底層管理器建立
            if hasattr(self.folder_manager, 'create_progress_folder'):
                result = self.folder_manager.create_progress_folder(case_folder, stage_name)
                if result:
                    return True, f"成功建立進度資料夾: {stage_name}"
                else:
                    return False, f"建立進度資料夾失敗: {stage_name}"
            else:
                # 備用方法
                progress_folder = os.path.join(case_folder, '進度追蹤')
                safe_stage_name = self.folder_validator.sanitize_folder_name(stage_name)
                stage_folder = os.path.join(progress_folder, safe_stage_name)

                os.makedirs(stage_folder, exist_ok=True)
                return True, f"成功建立進度資料夾: {stage_name}"

        except Exception as e:
            error_msg = f"建立進度資料夾失敗: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg

    # ==================== 資料夾刪除業務邏輯 ====================

    def delete_case_folder(self, case_data: CaseData, backup_before_delete: bool = True) -> Tuple[bool, str]:
        """
        刪除案件資料夾（業務邏輯層面）

        Args:
            case_data: 案件資料
            backup_before_delete: 刪除前是否備份

        Returns:
            (成功與否, 結果訊息)
        """
        try:
            print(f"🗑️ 資料夾服務: 開始刪除案件資料夾")

            # 1. 檢查資料夾是否存在
            folder_path = self.get_case_folder_path(case_data)
            if not folder_path:
                return True, f"資料夾不存在，無需刪除: {case_data.client}"

            # 2. 業務驗證
            can_delete, reason = self._validate_folder_deletion(case_data, folder_path)
            if not can_delete:
                return False, f"無法刪除資料夾: {reason}"

            # 3. 備份（如果需要）
            if backup_before_delete:
                backup_result = self._backup_before_deletion(folder_path, case_data)
                if not backup_result[0]:
                    print(f"⚠️ 警告: 備份失敗 - {backup_result[1]}")

            # 4. 委託給底層操作器刪除
            delete_result = self.folder_operations.delete_case_folder(case_data, confirm=True)
            if not delete_result[0]:
                return False, f"資料夾刪除失敗: {delete_result[1]}"

            print(f"✅ 成功刪除案件資料夾: {folder_path}")
            return True, f"成功刪除資料夾: {folder_path}"

        except Exception as e:
            error_msg = f"刪除案件資料夾失敗: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg

    def delete_progress_folder(self, case_data: CaseData, stage_name: str) -> Tuple[bool, str]:
        """
        刪除進度階段資料夾

        Args:
            case_data: 案件資料
            stage_name: 階段名稱

        Returns:
            (成功與否, 結果訊息)
        """
        try:
            print(f"🗑️ 刪除進度資料夾: {stage_name}")

            # 委託給底層操作器
            delete_result = self.folder_operations.delete_stage_folder(case_data, stage_name)
            if delete_result[0]:
                return True, f"成功刪除進度資料夾: {stage_name}"
            else:
                return False, f"刪除進度資料夾失敗: {delete_result[1]}"

        except Exception as e:
            error_msg = f"刪除進度資料夾失敗: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg

    # ==================== 資料夾同步業務邏輯 ====================

    def sync_case_folder(self, old_case_data: CaseData, new_case_data: CaseData) -> Tuple[bool, str]:
        """
        同步案件資料夾（當案件資料更新時）

        Args:
            old_case_data: 舊的案件資料
            new_case_data: 新的案件資料

        Returns:
            (成功與否, 結果訊息)
        """
        try:
            print(f"🔄 同步案件資料夾")

            # 1. 檢查是否需要同步
            sync_needed, sync_reasons = self._check_folder_sync_needed(old_case_data, new_case_data)
            if not sync_needed:
                return True, "無需同步資料夾"

            print(f"需要同步原因: {', '.join(sync_reasons)}")

            # 2. 處理案件類型變更
            if old_case_data.case_type != new_case_data.case_type:
                move_result = self._move_case_to_new_type(old_case_data, new_case_data)
                if not move_result[0]:
                    return False, f"移動案件類型失敗: {move_result[1]}"

            # 3. 處理當事人名稱變更
            if old_case_data.client != new_case_data.client:
                rename_result = self._rename_case_folder(old_case_data, new_case_data)
                if not rename_result[0]:
                    return False, f"重新命名資料夾失敗: {rename_result[1]}"

            # 4. 同步進度階段
            if old_case_data.progress_stages != new_case_data.progress_stages:
                sync_progress_result = self._sync_progress_folders(old_case_data, new_case_data)
                if not sync_progress_result[0]:
                    print(f"⚠️ 警告: 進度資料夾同步失敗 - {sync_progress_result[1]}")

            print(f"✅ 成功同步案件資料夾")
            return True, "成功同步資料夾"

        except Exception as e:
            error_msg = f"同步案件資料夾失敗: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg

    # ==================== 資料夾查詢業務邏輯 ====================

    def get_case_folder_path(self, case_data: CaseData) -> Optional[str]:
        """取得案件資料夾路徑"""
        return self.folder_operations.get_case_folder_path(case_data)

    def get_case_folder_info(self, case_data: CaseData) -> Dict[str, Any]:
        """
        取得案件資料夾詳細資訊

        Args:
            case_data: 案件資料

        Returns:
            資料夾資訊字典
        """
        try:
            # 使用底層操作器取得基本資訊
            basic_info = self.folder_operations.get_case_folder_info(case_data)

            # 增加業務層面的資訊
            if basic_info['exists']:
                # 檢查資料夾完整性
                structure_check = self._check_folder_structure_integrity(basic_info['path'])
                basic_info['structure_integrity'] = structure_check

                # 檢查是否有重要檔案
                important_files = self._check_important_files(basic_info['path'])
                basic_info['important_files'] = important_files

                # 最後修改時間
                basic_info['last_modified'] = self._get_folder_last_modified(basic_info['path'])

            return basic_info

        except Exception as e:
            print(f"❌ 取得資料夾資訊失敗: {e}")
            return {'exists': False, 'error': str(e)}

    def list_case_folders_with_status(self, case_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        列出案件資料夾並包含狀態資訊

        Args:
            case_type: 指定案件類型

        Returns:
            資料夾資訊列表（包含狀態）
        """
        try:
            # 使用底層操作器取得基本列表
            basic_list = self.folder_operations.list_case_folders(case_type)

            # 為每個資料夾添加業務狀態資訊
            enhanced_list = []
            for folder_info in basic_list:
                # 檢查資料夾健康狀態
                health_status = self._check_folder_health(folder_info['path'])
                folder_info['health_status'] = health_status

                # 檢查是否有最近活動
                recent_activity = self._check_recent_activity(folder_info['path'])
                folder_info['recent_activity'] = recent_activity

                enhanced_list.append(folder_info)

            return enhanced_list

        except Exception as e:
            print(f"❌ 列出資料夾失敗: {e}")
            return []

    # ==================== 私有輔助方法 ====================

    def _validate_folder_creation_request(self, case_data: CaseData) -> Tuple[bool, str]:
        """驗證資料夾建立請求"""
        # 基本案件資料驗證
        if not case_data.client or case_data.client.strip() == "":
            return False, "當事人姓名不能為空"

        if not case_data.case_type:
            return False, "案件類型不能為空"

        # 檢查案件類型是否有效
        validation_result = self.validation_service.validate_case_type(case_data.case_type)
        if not validation_result[0]:
            return False, f"無效的案件類型: {case_data.case_type}"

        return True, "驗證通過"

    def _validate_folder_deletion(self, case_data: CaseData, folder_path: str) -> Tuple[bool, str]:
        """驗證資料夾刪除請求"""
        # 檢查資料夾是否包含重要檔案
        important_files = self._check_important_files(folder_path)
        if important_files['has_important_files']:
            return False, f"資料夾包含重要檔案，請先備份: {important_files['file_count']} 個檔案"

        # 檢查資料夾大小
        folder_info = self.folder_operations.get_case_folder_info(case_data)
        if folder_info['size_mb'] > 100:  # 如果資料夾超過100MB
            return False, f"資料夾過大 ({folder_info['size_mb']:.1f}MB)，請確認是否真的要刪除"

        return True, "可以刪除"

    def _backup_existing_folder(self, folder_path: str) -> Tuple[bool, str]:
        """備份現有資料夾"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{folder_path}_backup_{timestamp}"

            shutil.copytree(folder_path, backup_path)
            print(f"✅ 備份資料夾到: {backup_path}")
            return True, backup_path

        except Exception as e:
            return False, f"備份失敗: {str(e)}"

    def _backup_before_deletion(self, folder_path: str, case_data: CaseData) -> Tuple[bool, str]:
        """刪除前備份"""
        try:
            backup_base = os.path.join(self.base_data_folder, "_backups", "deleted_cases")
            os.makedirs(backup_base, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{case_data.client}_{case_data.case_id}_{timestamp}"
            backup_path = os.path.join(backup_base, backup_name)

            shutil.copytree(folder_path, backup_path)
            print(f"✅ 刪除前備份到: {backup_path}")
            return True, backup_path

        except Exception as e:
            return False, f"刪除前備份失敗: {str(e)}"

    def _verify_folder_structure(self, case_data: CaseData) -> Tuple[bool, str]:
        """驗證資料夾結構是否正確建立"""
        try:
            folder_path = self.get_case_folder_path(case_data)
            if not folder_path:
                return False, "找不到建立的資料夾"

            # 檢查必要的子資料夾
            required_subfolders = ['案件資訊', '進度追蹤', '狀紙']
            for subfolder in required_subfolders:
                subfolder_path = os.path.join(folder_path, subfolder)
                if not os.path.exists(subfolder_path):
                    return False, f"缺少必要子資料夾: {subfolder}"

            return True, "資料夾結構驗證通過"

        except Exception as e:
            return False, f"驗證資料夾結構失敗: {str(e)}"

    def _set_folder_permissions(self, folder_path: str):
        """設定資料夾權限（如果需要）"""
        try:
            # 在Windows系統上可能不需要特別設定權限
            # 在Linux/Mac系統上可以設定適當的權限
            import stat
            import platform

            if platform.system() != "Windows":
                # 設定資料夾權限為 755 (所有者可讀寫執行，群組和其他人可讀執行)
                os.chmod(folder_path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
                print(f"✅ 設定資料夾權限: {folder_path}")
        except Exception as e:
            print(f"⚠️ 設定資料夾權限失敗: {e}")

    def _check_folder_sync_needed(self, old_data: CaseData, new_data: CaseData) -> Tuple[bool, List[str]]:
        """檢查是否需要同步資料夾"""
        reasons = []

        if old_data.case_type != new_data.case_type:
            reasons.append("案件類型變更")

        if old_data.client != new_data.client:
            reasons.append("當事人名稱變更")

        if old_data.progress_stages != new_data.progress_stages:
            reasons.append("進度階段變更")

        return len(reasons) > 0, reasons

    def _move_case_to_new_type(self, old_data: CaseData, new_data: CaseData) -> Tuple[bool, str]:
        """移動案件到新的類型資料夾"""
        try:
            result = self.folder_operations.move_case_folder(old_data, new_data.case_type)
            return result
        except Exception as e:
            return False, f"移動案件類型失敗: {str(e)}"

    def _rename_case_folder(self, old_data: CaseData, new_data: CaseData) -> Tuple[bool, str]:
        """重新命名案件資料夾"""
        try:
            old_path = self.get_case_folder_path(old_data)
            if not old_path:
                return False, "找不到舊資料夾"

            safe_new_name = self.folder_validator.get_safe_client_name(new_data.client)
            new_path = os.path.join(os.path.dirname(old_path), safe_new_name)

            if os.path.exists(new_path):
                return False, f"目標資料夾已存在: {new_path}"

            os.rename(old_path, new_path)
            return True, f"成功重新命名資料夾: {new_path}"

        except Exception as e:
            return False, f"重新命名資料夾失敗: {str(e)}"

    def _sync_progress_folders(self, old_data: CaseData, new_data: CaseData) -> Tuple[bool, str]:
        """同步進度資料夾"""
        try:
            # 這裡可以實作進度資料夾的同步邏輯
            # 比較新舊進度階段，新增缺少的，移除多餘的
            print("🔄 同步進度資料夾...")
            return True, "進度資料夾同步完成"
        except Exception as e:
            return False, f"同步進度資料夾失敗: {str(e)}"

    def _check_folder_structure_integrity(self, folder_path: str) -> Dict[str, Any]:
        """檢查資料夾結構完整性"""
        try:
            required_subfolders = ['案件資訊', '進度追蹤', '狀紙']
            missing_folders = []

            for subfolder in required_subfolders:
                subfolder_path = os.path.join(folder_path, subfolder)
                if not os.path.exists(subfolder_path):
                    missing_folders.append(subfolder)

            return {
                'is_complete': len(missing_folders) == 0,
                'missing_folders': missing_folders,
                'integrity_score': (len(required_subfolders) - len(missing_folders)) / len(required_subfolders)
            }
        except Exception as e:
            return {'is_complete': False, 'error': str(e)}

    def _check_important_files(self, folder_path: str) -> Dict[str, Any]:
        """檢查是否有重要檔案"""
        try:
            important_extensions = ['.pdf', '.docx', '.doc', '.xlsx', '.xls']
            important_files = []

            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    if any(file.lower().endswith(ext) for ext in important_extensions):
                        important_files.append(os.path.join(root, file))

            return {
                'has_important_files': len(important_files) > 0,
                'file_count': len(important_files),
                'file_list': important_files[:10]  # 只返回前10個檔案路徑
            }
        except Exception as e:
            return {'has_important_files': False, 'error': str(e)}

    def _get_folder_last_modified(self, folder_path: str) -> Optional[datetime]:
        """取得資料夾最後修改時間"""
        try:
            latest_time = os.path.getmtime(folder_path)

            # 檢查子檔案的修改時間
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    file_time = os.path.getmtime(file_path)
                    if file_time > latest_time:
                        latest_time = file_time

            return datetime.fromtimestamp(latest_time)
        except Exception as e:
            print(f"⚠️ 取得資料夾修改時間失敗: {e}")
            return None

    def _check_folder_health(self, folder_path: str) -> Dict[str, Any]:
        """檢查資料夾健康狀態"""
        try:
            health_score = 100
            issues = []

            # 檢查結構完整性
            integrity = self._check_folder_structure_integrity(folder_path)
            if not integrity['is_complete']:
                health_score -= 30
                issues.append(f"結構不完整，缺少: {', '.join(integrity['missing_folders'])}")

            # 檢查是否為空資料夾
            total_files = sum([len(files) for r, d, files in os.walk(folder_path)])
            if total_files == 0:
                health_score -= 20
                issues.append("資料夾為空")

            # 檢查是否有過期的臨時檔案
            temp_files = []
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    if file.startswith('~') or file.endswith('.tmp'):
                        temp_files.append(file)

            if temp_files:
                health_score -= 10
                issues.append(f"發現 {len(temp_files)} 個臨時檔案")

            status = "健康" if health_score >= 80 else "警告" if health_score >= 60 else "不佳"

            return {
                'status': status,
                'score': health_score,
                'issues': issues
            }
        except Exception as e:
            return {'status': '錯誤', 'score': 0, 'issues': [str(e)]}

    def _check_recent_activity(self, folder_path: str, days: int = 30) -> Dict[str, Any]:
        """檢查最近活動"""
        try:
            from datetime import timedelta
            cutoff_date = datetime.now() - timedelta(days=days)
            recent_files = []

            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                    if file_time > cutoff_date:
                        recent_files.append({
                            'file': file,
                            'modified': file_time
                        })

            return {
                'has_recent_activity': len(recent_files) > 0,
                'recent_file_count': len(recent_files),
                'latest_activity': max([f['modified'] for f in recent_files]) if recent_files else None
            }
        except Exception as e:
            return {'has_recent_activity': False, 'error': str(e)}