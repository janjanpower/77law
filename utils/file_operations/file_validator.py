#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
檔案驗證器 - 重構版本
整合 folder_validator 和其他驗證功能
負責檔案路徑驗證、安全檢查和名稱清理
"""

import os
from typing import Dict, Any, Tuple, Optional
from config.settings import AppConfig


class FileValidator:
    """檔案和路徑驗證器 - 統一所有驗證功能"""

    # 無效字元定義
    INVALID_CHARS = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']

    # 保留名稱（Windows系統）
    RESERVED_NAMES = [
        'CON', 'PRN', 'AUX', 'NUL',
        'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
        'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
    ]

    def __init__(self):
        """初始化驗證器"""
        pass

    # ==================== 資料夾名稱清理功能 ====================

    def sanitize_folder_name(self, name: str) -> str:
        """
        清理資料夾名稱中的無效字元

        Args:
            name: 原始名稱

        Returns:
            清理後的安全名稱
        """
        if not name or not isinstance(name, str):
            return "未知案件"

        clean_name = str(name).strip()

        # 移除無效字元
        for char in self.INVALID_CHARS:
            clean_name = clean_name.replace(char, '_')

        # 移除前後空格和點
        clean_name = clean_name.strip(' .')

        # 檢查保留名稱
        if clean_name.upper() in self.RESERVED_NAMES:
            clean_name = f"案件_{clean_name}"

        # 長度限制
        if len(clean_name) > 100:
            clean_name = clean_name[:100]

        # 空名稱處理
        if not clean_name:
            clean_name = "未知案件"

        return clean_name

    def sanitize_file_name(self, name: str) -> str:
        """
        清理檔案名稱中的無效字元

        Args:
            name: 原始檔案名稱

        Returns:
            清理後的安全檔案名稱
        """
        if not name or not isinstance(name, str):
            return "未知檔案"

        # 分離檔案名稱和副檔名
        name_part, ext_part = os.path.splitext(name)

        # 清理檔案名稱部分
        clean_name = str(name_part).strip()

        # 移除無效字元
        for char in self.INVALID_CHARS:
            clean_name = clean_name.replace(char, '_')

        # 移除前後空格和點
        clean_name = clean_name.strip(' .')

        # 檢查保留名稱
        if clean_name.upper() in self.RESERVED_NAMES:
            clean_name = f"檔案_{clean_name}"

        # 長度限制（考慮副檔名）
        max_name_length = 100 - len(ext_part)
        if len(clean_name) > max_name_length:
            clean_name = clean_name[:max_name_length]

        # 空名稱處理
        if not clean_name:
            clean_name = "未知檔案"

        return clean_name + ext_part

    def get_safe_client_name(self, client_name: str) -> str:
        """取得安全的當事人名稱（向後相容方法）"""
        return self.sanitize_folder_name(client_name)

    # ==================== 路徑驗證功能 ====================

    def validate_path(self, path: str) -> Tuple[bool, str]:
        """
        驗證路徑的有效性

        Args:
            path: 檔案或資料夾路徑

        Returns:
            (is_valid, error_message)
        """
        if not path:
            return False, "路徑不能為空"

        try:
            # 檢查路徑長度（Windows限制）
            if len(path) > 260:
                return False, "路徑長度超過系統限制（260字元）"

            # 檢查父目錄是否存在
            parent_dir = os.path.dirname(path)
            if parent_dir and not os.path.exists(parent_dir):
                return False, f"父目錄不存在: {parent_dir}"

            # 檢查寫入權限
            if os.path.exists(path):
                if not os.access(path, os.W_OK):
                    return False, "沒有寫入權限"
            else:
                # 檢查父目錄的寫入權限
                if parent_dir and not os.access(parent_dir, os.W_OK):
                    return False, "父目錄沒有寫入權限"

            return True, ""

        except Exception as e:
            return False, f"路徑驗證失敗: {str(e)}"

    def validate_folder_path(self, folder_path: str) -> Tuple[bool, str]:
        """
        驗證資料夾路徑

        Args:
            folder_path: 資料夾路徑

        Returns:
            (is_valid, error_message)
        """
        try:
            if not folder_path or not folder_path.strip():
                return False, "資料夾路徑不能為空"

            # 檢查路徑是否存在
            if not os.path.exists(folder_path):
                return False, f"資料夾路徑不存在: {folder_path}"

            # 檢查是否為資料夾
            if not os.path.isdir(folder_path):
                return False, f"路徑不是資料夾: {folder_path}"

            # 檢查讀寫權限
            if not os.access(folder_path, os.R_OK | os.W_OK):
                return False, f"資料夾沒有讀寫權限: {folder_path}"

            return True, "資料夾路徑驗證通過"

        except Exception as e:
            return False, f"驗證資料夾路徑時發生錯誤: {str(e)}"

    def validate_file_path(self, file_path: str) -> Tuple[bool, str]:
        """
        驗證檔案路徑

        Args:
            file_path: 檔案路徑

        Returns:
            (is_valid, error_message)
        """
        try:
            if not file_path or not file_path.strip():
                return False, "檔案路徑不能為空"

            # 檢查路徑是否存在
            if not os.path.exists(file_path):
                return False, f"檔案路徑不存在: {file_path}"

            # 檢查是否為檔案
            if not os.path.isfile(file_path):
                return False, f"路徑不是檔案: {file_path}"

            # 檢查讀取權限
            if not os.access(file_path, os.R_OK):
                return False, f"檔案沒有讀取權限: {file_path}"

            return True, "檔案路徑驗證通過"

        except Exception as e:
            return False, f"驗證檔案路徑時發生錯誤: {str(e)}"

    # ==================== 案件類型驗證功能 ====================

    def validate_case_type(self, case_type: str) -> bool:
        """
        驗證案件類型是否有效

        Args:
            case_type: 案件類型

        Returns:
            是否為有效的案件類型
        """
        try:
            return case_type in AppConfig.CASE_TYPE_FOLDERS
        except Exception:
            return False

    # ==================== 資料夾衝突檢查功能 ====================

    def check_folder_conflicts(self, base_path: str, folder_name: str) -> Tuple[bool, str]:
        """
        檢查資料夾名稱衝突

        Args:
            base_path: 基礎路徑
            folder_name: 資料夾名稱

        Returns:
            (has_conflict, suggested_name)
        """
        full_path = os.path.join(base_path, folder_name)

        if not os.path.exists(full_path):
            return False, folder_name

        # 產生不衝突的名稱
        counter = 1
        while True:
            suggested_name = f"{folder_name}_{counter}"
            suggested_path = os.path.join(base_path, suggested_name)

            if not os.path.exists(suggested_path):
                return True, suggested_name

            counter += 1
            if counter > 100:  # 防止無限循環
                break

        return True, f"{folder_name}_{counter}"

    # ==================== 資料夾結構驗證功能 ====================

    def validate_folder_structure(self, folder_path: str) -> Dict[str, Any]:
        """
        驗證資料夾結構完整性

        Args:
            folder_path: 資料夾路徑

        Returns:
            驗證結果字典
        """
        result = {
            'is_valid': True,
            'missing_folders': [],
            'errors': [],
            'warnings': []
        }

        try:
            if not os.path.exists(folder_path):
                result['is_valid'] = False
                result['errors'].append(f"主資料夾不存在: {folder_path}")

                            # 檢查必要的子資料夾
            required_subfolders = ['狀紙', '進度追蹤', '案件資訊']

            for subfolder in required_subfolders:
                subfolder_path = os.path.join(folder_path, subfolder)
                if not os.path.exists(subfolder_path):
                    result['missing_folders'].append(subfolder)
                    result['warnings'].append(f"缺少子資料夾: {subfolder}")

            # 檢查案件資訊Excel
            case_info_folder = os.path.join(folder_path, '案件資訊')
            if os.path.exists(case_info_folder):
                excel_files = [f for f in os.listdir(case_info_folder)
                              if f.endswith(('.xlsx', '.xls'))]
                if not excel_files:
                    result['warnings'].append("案件資訊資料夾中沒有Excel檔案")

            if result['missing_folders'] or result['errors']:
                result['is_valid'] = False

        except Exception as e:
            result['is_valid'] = False
            result['errors'].append(f"驗證過程發生錯誤: {str(e)}")

        return result

            # ==================== 狀態檢查功能 ====================

    def check_system_compatibility(self) -> Dict[str, Any]:
        """
        檢查系統相容性

        Returns:
            系統相容性報告
        """
        import platform

        result = {
            'platform': platform.system(),
            'python_version': platform.python_version(),
            'supports_long_paths': True,
            'file_system': 'unknown',
            'warnings': []
        }

        try:
            # Windows特定檢查
            if result['platform'] == 'Windows':
                # 檢查長路徑支援
                try:
                    test_long_path = 'C:\\' + 'a' * 250 + '\\test.txt'
                    os.makedirs(os.path.dirname(test_long_path), exist_ok=True)
                    with open(test_long_path, 'w') as f:
                        f.write('test')
                    os.remove(test_long_path)
                    os.rmdir(os.path.dirname(test_long_path))
                except:
                    result['supports_long_paths'] = False
                    result['warnings'].append('系統不支援長路徑，請啟用Windows長路徑支援')

        except Exception as e:
            result['warnings'].append(f'系統相容性檢查失敗: {str(e)}')

        return result

    def get_validation_summary(self) -> str:
        """
        取得驗證器功能摘要

        Returns:
            功能摘要字串
        """
        return """
📋 檔案驗證器功能摘要:

🔍 路徑驗證功能:
  • 檔案路徑驗證
  • 資料夾路徑驗證
  • 路徑安全檢查
  • 權限檢查

🛡️ 名稱清理功能:
  • 資料夾名稱清理
  • 檔案名稱清理
  • 無效字元移除
  • 保留名稱檢查

📊 Excel檔案驗證:
  • 檔案格式檢查
  • 檔案大小限制
  • 內容完整性驗證

🎯 案件資料驗證:
  • 案件類型驗證
  • 案件編號格式檢查
  • 資料完整性驗證

📁 資料夾結構驗證:
  • 必要子資料夾檢查
  • 結構完整性驗證
  • 缺失項目報告

⚙️ 系統相容性:
  • 作業系統檢查
  • 長路徑支援檢查
  • 檔案系統相容性
        """.strip()

    # ==================== 批量驗證功能 ====================

    def validate_multiple_paths(self, paths: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        批量驗證多個路徑

        Args:
            paths: 路徑列表

        Returns:
            各路徑的驗證結果
        """
        results = {}

        for path in paths:
            try:
                if os.path.isfile(path):
                    is_valid, message = self.validate_file_path(path)
                elif os.path.isdir(path):
                    is_valid, message = self.validate_folder_path(path)
                else:
                    is_valid, message = self.validate_path(path)

                results[path] = {
                    'is_valid': is_valid,
                    'message': message,
                    'type': 'file' if os.path.isfile(path) else 'folder' if os.path.isdir(path) else 'unknown'
                }

            except Exception as e:
                results[path] = {
                    'is_valid': False,
                    'message': f'驗證失敗: {str(e)}',
                    'type': 'error'
                }

        return results

    def validate_case_folder_batch(self, case_folders: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        批量驗證案件資料夾結構

        Args:
            case_folders: 案件資料夾路徑列表

        Returns:
            各資料夾的驗證結果
        """
        results = {}

        for folder_path in case_folders:
            try:
                results[folder_path] = self.validate_folder_structure(folder_path)
            except Exception as e:
                results[folder_path] = {
                    'is_valid': False,
                    'errors': [f'驗證失敗: {str(e)}'],
                    'missing_folders': [],
                    'warnings': []
                }

        return results

    # ==================== 修復建議功能 ====================

    def get_repair_suggestions(self, validation_result: Dict[str, Any]) -> List[str]:
        """
        根據驗證結果提供修復建議

        Args:
            validation_result: 驗證結果

        Returns:
            修復建議列表
        """
        suggestions = []

        try:
            if not validation_result.get('is_valid', True):
                # 根據錯誤類型提供建議
                errors = validation_result.get('errors', [])
                missing_folders = validation_result.get('missing_folders', [])

                for error in errors:
                    if '不存在' in error:
                        suggestions.append('建立缺失的資料夾或檔案')
                    elif '權限' in error:
                        suggestions.append('檢查並修正檔案/資料夾權限')
                    elif '格式' in error:
                        suggestions.append('確認檔案格式是否正確')

                if missing_folders:
                    suggestions.append(f'建立缺失的子資料夾: {", ".join(missing_folders)}')

                # 通用建議
                if not suggestions:
                    suggestions.append('檢查路徑是否正確且可存取')

        except Exception as e:
            suggestions.append(f'無法生成修復建議: {str(e)}')

        return suggestions

    def auto_fix_folder_structure(self, folder_path: str, dry_run: bool = True) -> Dict[str, Any]:
        """
        自動修復資料夾結構

        Args:
            folder_path: 資料夾路徑
            dry_run: 是否僅模擬執行

        Returns:
            修復結果
        """
        result = {
            'success': False,
            'actions_taken': [],
            'errors': []
        }

        try:
            # 先驗證目前狀態
            validation = self.validate_folder_structure(folder_path)

            if validation['is_valid']:
                result['success'] = True
                result['actions_taken'].append('資料夾結構已完整，無需修復')
                return result

            # 建立缺失的資料夾
            missing_folders = validation.get('missing_folders', [])
            for missing_folder in missing_folders:
                missing_path = os.path.join(folder_path, missing_folder)

                if dry_run:
                    result['actions_taken'].append(f'將建立資料夾: {missing_path}')
                else:
                    try:
                        os.makedirs(missing_path, exist_ok=True)
                        result['actions_taken'].append(f'已建立資料夾: {missing_path}')
                    except Exception as e:
                        result['errors'].append(f'建立資料夾失敗 {missing_path}: {str(e)}')

            # 檢查修復結果
            if not dry_run:
                final_validation = self.validate_folder_structure(folder_path)
                result['success'] = final_validation['is_valid']
            else:
                result['success'] = len(result['errors']) == 0

        except Exception as e:
            result['errors'].append(f'自動修復失敗: {str(e)}')

        return result

    # ==================== 高級驗證功能 ====================

    def deep_validate_case_folder(self, folder_path: str) -> Dict[str, Any]:
        """
        深度驗證案件資料夾

        Args:
            folder_path: 案件資料夾路徑

        Returns:
            詳細驗證結果
        """
        result = {
            'basic_structure': {},
            'file_analysis': {},
            'permissions': {},
            'storage_info': {},
            'recommendations': []
        }

        try:
            # 基本結構驗證
            result['basic_structure'] = self.validate_folder_structure(folder_path)

            # 檔案分析
            result['file_analysis'] = self._analyze_folder_files(folder_path)

            # 權限檢查
            result['permissions'] = self._check_folder_permissions(folder_path)

            # 儲存空間資訊
            result['storage_info'] = self._get_storage_info(folder_path)

            # 生成建議
            result['recommendations'] = self._generate_folder_recommendations(result)

        except Exception as e:
            result['error'] = f'深度驗證失敗: {str(e)}'

        return result

    def _analyze_folder_files(self, folder_path: str) -> Dict[str, Any]:
        """分析資料夾中的檔案"""
        analysis = {
            'total_files': 0,
            'file_types': {},
            'large_files': [],
            'empty_folders': []
        }

        try:
            for root, dirs, files in os.walk(folder_path):
                analysis['total_files'] += len(files)

                # 檢查空資料夾
                if not files and not dirs:
                    analysis['empty_folders'].append(root)

                # 分析檔案類型和大小
                for file in files:
                    file_path = os.path.join(root, file)
                    file_ext = os.path.splitext(file)[1].lower()

                    # 統計檔案類型
                    if file_ext in analysis['file_types']:
                        analysis['file_types'][file_ext] += 1
                    else:
                        analysis['file_types'][file_ext] = 1

                    # 檢查大檔案（超過10MB）
                    try:
                        file_size = os.path.getsize(file_path)
                        if file_size > 10 * 1024 * 1024:  # 10MB
                            analysis['large_files'].append({
                                'path': file_path,
                                'size_mb': round(file_size / (1024 * 1024), 2)
                            })
                    except:
                        pass

        except Exception as e:
            analysis['error'] = str(e)

        return analysis

    def _check_folder_permissions(self, folder_path: str) -> Dict[str, Any]:
        """檢查資料夾權限"""
        permissions = {
            'readable': False,
            'writable': False,
            'executable': False,
            'issues': []
        }

        try:
            permissions['readable'] = os.access(folder_path, os.R_OK)
            permissions['writable'] = os.access(folder_path, os.W_OK)
            permissions['executable'] = os.access(folder_path, os.X_OK)

            if not permissions['readable']:
                permissions['issues'].append('缺少讀取權限')
            if not permissions['writable']:
                permissions['issues'].append('缺少寫入權限')
            if not permissions['executable']:
                permissions['issues'].append('缺少執行權限')

        except Exception as e:
            permissions['error'] = str(e)

        return permissions

    def _get_storage_info(self, folder_path: str) -> Dict[str, Any]:
        """取得儲存空間資訊"""
        storage = {
            'folder_size_mb': 0.0,
            'available_space_mb': 0.0,
            'space_usage_percent': 0.0
        }

        try:
            # 計算資料夾大小
            total_size = 0
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    try:
                        file_path = os.path.join(root, file)
                        total_size += os.path.getsize(file_path)
                    except:
                        pass

            storage['folder_size_mb'] = round(total_size / (1024 * 1024), 2)

            # 取得可用空間
            import shutil
            total, used, free = shutil.disk_usage(folder_path)
            storage['available_space_mb'] = round(free / (1024 * 1024), 2)
            storage['space_usage_percent'] = round((used / total) * 100, 2)

        except Exception as e:
            storage['error'] = str(e)

        return storage

    def _generate_folder_recommendations(self, validation_result: Dict[str, Any]) -> List[str]:
        """根據驗證結果生成建議"""
        recommendations = []

        try:
            # 基於檔案分析的建議
            file_analysis = validation_result.get('file_analysis', {})

            if file_analysis.get('empty_folders'):
                recommendations.append('發現空資料夾，考慮是否需要清理')

            if file_analysis.get('large_files'):
                recommendations.append('發現大型檔案，建議定期備份')

            # 基於權限的建議
            permissions = validation_result.get('permissions', {})
            if permissions.get('issues'):
                recommendations.append('發現權限問題，建議檢查資料夾權限設定')

            # 基於儲存空間的建議
            storage = validation_result.get('storage_info', {})
            if storage.get('space_usage_percent', 0) > 90:
                recommendations.append('磁碟空間不足，建議清理或擴充儲存空間')

        except Exception as e:
            recommendations.append(f'無法生成建議: {str(e)}')

        return recommendations


    # ==================== Excel檔案驗證功能 ====================

    def validate_excel_file(self, file_path: str) -> Tuple[bool, str]:
        """
        驗證Excel檔案

        Args:
            file_path: Excel檔案路徑

        Returns:
            (is_valid, error_message)
        """
        try:
            # 基本檔案驗證
            is_valid, message = self.validate_file_path(file_path)
            if not is_valid:
                return False, message

            # 檢查檔案副檔名
            if not file_path.lower().endswith(('.xlsx', '.xls')):
                return False, "不是有效的Excel檔案格式（.xlsx 或 .xls）"

            # 檢查檔案大小（Excel限制50MB）
            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
            if file_size_mb > 50:
                return False, f"Excel檔案過大: {file_size_mb:.2f}MB，限制50MB"

            return True, "Excel檔案驗證通過"

        except Exception as e:
            return False, f"驗證Excel檔案時發生錯誤: {str(e)}"

    # ==================== 資料格式驗證功能 ====================

    def validate_date_format(self, date_str: str) -> Tuple[bool, str]:
        """
        驗證日期格式

        Args:
            date_str: 日期字串

        Returns:
            (is_valid, error_message)
        """
        if not date_str or not date_str.strip():
            return False, "日期不能為空"

        try:
            from datetime import datetime

            # 支援的日期格式
            date_formats = [
                '%Y-%m-%d',
                '%Y/%m/%d',
                '%Y.%m.%d',
                '%Y-%m-%d %H:%M:%S',
                '%Y/%m/%d %H:%M:%S',
                '%m/%d/%Y',
                '%d/%m/%Y'
            ]

            for fmt in date_formats:
                try:
                    datetime.strptime(date_str.strip(), fmt)
                    return True, "日期格式驗證通過"
                except ValueError:
                    continue

            return False, f"不支援的日期格式: {date_str}"

        except Exception as e:
            return False, f"驗證日期格式時發生錯誤: {str(e)}"

    def validate_case_id_format(self, case_id: str) -> Tuple[bool, str]:
        """
        驗證案件編號格式

        Args:
            case_id: 案件編號

        Returns:
            (is_valid, error_message)
        """
        if not case_id or not case_id.strip():
            return False, "案件編號不能為空"

        try:
            clean_id = case_id.strip()

            # 檢查長度
            if len(clean_id) < 3:
                return False, "案件編號長度不足（至少3個字元）"

            if len(clean_id) > 50:
                return False, "案件編號過長（最多50個字元）"

            # 檢查是否包含無效字元
            invalid_chars_found = [char for char in self.INVALID_CHARS if char in clean_id]
            if invalid_chars_found:
                return False, f"案件編號包含無效字元: {', '.join(invalid_chars_found)}"

            return True, "案件編號格式驗證通過"

        except Exception as e:
            return False, f"驗證案件編號格式時發生錯誤: {str(e)}"

    # ==================== 綜合驗證功能 ====================

    def validate_case_data(self, case_data) -> Dict[str, Any]:
        """
        驗證案件資料完整性

        Args:
            case_data: CaseData物件

        Returns:
            驗證結果字典
        """
        result = {
            'is_valid': True,
            'errors': [],
            'warnings': []
        }

        try:
            # 必填欄位檢查
            if not case_data.client or not case_data.client.strip():
                result['errors'].append("當事人姓名為必填欄位")

            if not case_data.case_type or not case_data.case_type.strip():
                result['errors'].append("案件類型為必填欄位")

            # 案件編號驗證
            if case_data.case_id:
                is_valid, message = self.validate_case_id_format(case_data.case_id)
                if not is_valid:
                    result['warnings'].append(f"案件編號格式問題: {message}")

            # 案件類型驗證
            if case_data.case_type and not self.validate_case_type(case_data.case_type):
                result['errors'].append(f"無效的案件類型: {case_data.case_type}")

            # 當事人姓名清理建議
            if case_data.client:
                safe_name = self.sanitize_folder_name(case_data.client)
                if safe_name != case_data.client:
                    result['warnings'].append(f"當事人姓名包含特殊字元，建議使用: {safe_name}")

            if result['errors']:
                result['is_valid'] = False

        except Exception as e:
            result['is_valid'] = False
            result['errors'].append(f"驗證過程發生錯誤: {str(e)}")

        return result

    def validate_upload_file(self, file_path: str) -> Tuple[bool, str]:
        """
        驗證上傳檔案

        Args:
            file_path: 檔案路徑

        Returns:
            (is_valid, error_message)
        """
        try:
            # 基本檔案驗證
            is_valid, message = self.validate_file_path(file_path)
            if not is_valid:
                return False, message

            # 檢查檔案大小（限制100MB）
            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
            if file_size_mb > 100:
                return False, f"檔案過大: {file_size_mb:.2f}MB，限制100MB"

            # 檢查檔案類型（基本安全檢查）
            file_ext = os.path.splitext(file_path)[1].lower()
            dangerous_extensions = ['.exe', '.bat', '.cmd', '.scr', '.pif', '.com']

            if file_ext in dangerous_extensions:
                return False, f"不允許上傳的檔案類型: {file_ext}"

            return True, "檔案驗證通過"

        except Exception as e:
            return False, f"驗證檔案時發生錯誤: {str(e)}"

    # ==================== 工具方法 ====================

    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """
        取得檔案資訊

        Args:
            file_path: 檔案路徑

        Returns:
            檔案資訊字典
        """
        try:
            if not os.path.exists(file_path):
                return {'exists': False}

            stat_info = os.stat(file_path)

            return {
                'exists': True,
                'size_bytes': stat_info.st_size,
                'size_mb': round(stat_info.st_size / (1024 * 1024), 2),
                'is_file': os.path.isfile(file_path),
                'is_directory': os.path.isdir(file_path),
                'extension': os.path.splitext(file_path)[1].lower(),
                'basename': os.path.basename(file_path),
                'dirname': os.path.dirname(file_path)
            }

        except Exception as e:
            return {
                'exists': False,
                'error': str(e)
            }

    def create_safe_path(self, base_path: str, *path_parts) -> str:
        """
        建立安全的路徑

        Args:
            base_path: 基礎路徑
            *path_parts: 路徑組成部分

        Returns:
            安全的完整路徑
        """
        try:
            # 清理所有路徑部分
            safe_parts = []
            for part in path_parts:
                if part:
                    safe_part = self.sanitize_folder_name(str(part))
                    safe_parts.append(safe_part)

            # 組合路徑
            safe_path = os.path.join(base_path, *safe_parts)
            return safe_path

        except Exception as e:
            print(f"❌ 建立安全路徑失敗: {e}")
            return base_path

    # ==================== 狀態檢查功能 ====================

    def check_system_compatibility(self) -> Dict[str, Any]:
        """
        檢查系統相容性

        Returns:
            系統相容性報告
        """
        import platform

        result = {
            'platform': platform.system(),
            'python_version': platform.python_version(),
            'supports_long_paths': True,
            'file_system': 'unknown',
            'warnings': []
        }

        try:
            # Windows特定檢查
            if result['platform'] == 'Windows':
                # 檢查長路徑支援
                try:
                    test_long_path = 'C:\\' + 'a' * 250 + '\\test.txt'
                    os.makedirs(os.path.dirname(test_long_path), exist_ok=True)
                    with open(test_long_path, 'w') as f:
                        f.write('test')
                    os.remove(test_long_path)
                    os.rmdir(os.path.dirname(test_long_path))
                except:
                    result['supports_long_paths'] = False
                    result['warnings'].append('系統不支援長路徑，請啟用Windows長路徑支援')

        except Exception as e:
            result['warnings'].append(f'系統相容性檢查失敗: {str(e)}')

        return result