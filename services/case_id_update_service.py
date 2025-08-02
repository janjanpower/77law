#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
案件編號更新服務 - 完整實現
檔案路徑: services/case_id_update_service.py
"""

import os
import shutil
import json
from typing import Tuple, List, Dict, Any
from datetime import datetime
from pathlib import Path


class CaseIdUpdateService:
    """案件編號更新服務 - 負責處理複雜的案件編號更新邏輯"""

    def __init__(self, data_folder: str, config: Dict[str, Any] = None):
        """
        初始化服務

        Args:
            data_folder: 資料資料夾路徑
            config: 配置設定
        """
        self.data_folder = data_folder
        self.config = config or {}

        # 可處理的文字檔案擴展名
        self.text_extensions = {
            '.txt', '.doc', '.docx', '.rtf', '.md', '.html', '.xml',
            '.json', '.csv', '.log', '.ini', '.cfg', '.conf'
        }

        # 編碼嘗試順序
        self.encodings = ['utf-8', 'big5', 'gbk', 'cp950', 'latin1', 'ascii']

    def update_case_id_comprehensive(self, old_case_id: str, new_case_id: str,
                                   case_type: str, case_data: Any) -> Tuple[bool, str, Dict[str, Any]]:
        """
        全面更新案件編號（包含資料、資料夾、內容）

        Args:
            old_case_id: 原案件編號
            new_case_id: 新案件編號
            case_type: 案件類型
            case_data: 案件資料物件

        Returns:
            Tuple[bool, str, Dict]: (成功與否, 訊息, 詳細結果)
        """
        update_results = {
            'folder_renamed': False,
            'content_updated': False,
            'files_processed': 0,
            'files_updated': 0,
            'files_failed': 0,
            'errors': [],
            'warnings': []
        }

        try:
            print(f"🔄 開始全面更新案件編號: {old_case_id} → {new_case_id}")

            # 1. 更新資料夾名稱
            folder_result = self._update_folder_name(old_case_id, new_case_id, case_type)
            update_results['folder_renamed'] = folder_result['success']
            if not folder_result['success']:
                update_results['warnings'].append(f"資料夾更新失敗: {folder_result['message']}")

            # 2. 更新資料夾內容中的案件編號
            content_result = self._update_folder_contents(new_case_id, old_case_id, case_type)
            update_results.update(content_result)

            # 3. 更新進度檔案中的案件編號
            progress_result = self._update_progress_files(old_case_id, new_case_id)
            if not progress_result['success']:
                update_results['warnings'].append(f"進度檔案更新失敗: {progress_result['message']}")

            # 4. 更新設定檔案中的案件編號
            config_result = self._update_config_files(old_case_id, new_case_id)
            if not config_result['success']:
                update_results['warnings'].append(f"設定檔更新失敗: {config_result['message']}")

            # 判斷整體成功與否
            overall_success = (
                update_results['folder_renamed'] or
                update_results['files_updated'] > 0
            )

            if overall_success:
                message = self._generate_success_message(old_case_id, new_case_id, update_results)
                return True, message, update_results
            else:
                message = f"案件編號更新失敗: 沒有任何項目被成功更新"
                return False, message, update_results

        except Exception as e:
            error_msg = f"案件編號更新過程發生錯誤: {str(e)}"
            update_results['errors'].append(error_msg)
            return False, error_msg, update_results

    def _update_folder_name(self, old_case_id: str, new_case_id: str, case_type: str) -> Dict[str, Any]:
        """
        更新案件資料夾名稱

        Args:
            old_case_id: 原案件編號
            new_case_id: 新案件編號
            case_type: 案件類型

        Returns:
            Dict: 更新結果
        """
        try:
            # 取得案件類型對應的資料夾名稱
            case_type_folders = self.config.get('case_type_folders', {
                '民事': '民事',
                '刑事': '刑事',
                '行政': '行政'
            })

            case_type_folder = case_type_folders.get(case_type, case_type)
            old_folder_path = os.path.join(self.data_folder, case_type_folder, old_case_id)
            new_folder_path = os.path.join(self.data_folder, case_type_folder, new_case_id)

            # 檢查原資料夾是否存在
            if not os.path.exists(old_folder_path):
                return {
                    'success': True,  # 資料夾不存在也算成功
                    'message': f"原案件資料夾不存在: {old_folder_path}",
                    'old_path': old_folder_path,
                    'new_path': new_folder_path
                }

            # 檢查目標資料夾是否已存在
            if os.path.exists(new_folder_path):
                return {
                    'success': False,
                    'message': f"目標資料夾已存在: {new_folder_path}",
                    'old_path': old_folder_path,
                    'new_path': new_folder_path
                }

            # 重新命名資料夾
            shutil.move(old_folder_path, new_folder_path)

            return {
                'success': True,
                'message': f"資料夾重新命名成功: {old_case_id} → {new_case_id}",
                'old_path': old_folder_path,
                'new_path': new_folder_path
            }

        except Exception as e:
            return {
                'success': False,
                'message': f"資料夾重新命名失敗: {str(e)}",
                'old_path': old_folder_path if 'old_folder_path' in locals() else '',
                'new_path': new_folder_path if 'new_folder_path' in locals() else ''
            }

    def _update_folder_contents(self, new_case_id: str, old_case_id: str, case_type: str) -> Dict[str, Any]:
        """
        更新資料夾內容中的案件編號

        Args:
            new_case_id: 新案件編號
            old_case_id: 原案件編號
            case_type: 案件類型

        Returns:
            Dict: 更新結果
        """
        result = {
            'content_updated': False,
            'files_processed': 0,
            'files_updated': 0,
            'files_failed': 0,
            'updated_files': [],
            'failed_files': []
        }

        try:
            # 取得案件資料夾路徑
            case_type_folders = self.config.get('case_type_folders', {
                '民事': '民事',
                '刑事': '刑事',
                '行政': '行政'
            })

            case_type_folder = case_type_folders.get(case_type, case_type)
            folder_path = os.path.join(self.data_folder, case_type_folder, new_case_id)

            if not os.path.exists(folder_path):
                return result

            # 遍歷所有檔案
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    result['files_processed'] += 1

                    # 處理檔案
                    if self._update_single_file(file_path, old_case_id, new_case_id):
                        result['files_updated'] += 1
                        result['updated_files'].append(os.path.relpath(file_path, folder_path))
                    else:
                        # 只有文字檔案更新失敗才計入失敗
                        if self._is_text_file(file_path):
                            result['files_failed'] += 1
                            result['failed_files'].append(os.path.relpath(file_path, folder_path))

            result['content_updated'] = result['files_updated'] > 0
            return result

        except Exception as e:
            print(f"❌ 更新資料夾內容失敗: {e}")
            return result

    def _update_single_file(self, file_path: str, old_case_id: str, new_case_id: str) -> bool:
        """
        更新單個檔案中的案件編號

        Args:
            file_path: 檔案路徑
            old_case_id: 原案件編號
            new_case_id: 新案件編號

        Returns:
            bool: 是否成功更新
        """
        # 只處理文字檔案
        if not self._is_text_file(file_path):
            return True  # 非文字檔案視為成功

        try:
            # 嘗試用不同編碼讀取檔案
            content = None
            used_encoding = None

            for encoding in self.encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        content = f.read()
                    used_encoding = encoding
                    break
                except UnicodeDecodeError:
                    continue
                except Exception as e:
                    print(f"⚠️ 讀取檔案失敗 {file_path}: {e}")
                    return False

            if content is None:
                print(f"⚠️ 無法以任何編碼讀取檔案: {file_path}")
                return False

            # 檢查是否包含舊案件編號
            if old_case_id not in content:
                return True  # 沒有需要更新的內容也算成功

            # 替換案件編號
            original_content = content
            updated_content = content.replace(old_case_id, new_case_id)

            # 如果內容沒有變化，表示沒有找到需要替換的內容
            if updated_content == original_content:
                return True

            # 寫回檔案
            with open(file_path, 'w', encoding=used_encoding) as f:
                f.write(updated_content)

            print(f"✅ 檔案內容已更新: {os.path.basename(file_path)}")
            return True

        except Exception as e:
            print(f"❌ 更新檔案內容失敗 {file_path}: {e}")
            return False

    def _is_text_file(self, file_path: str) -> bool:
        """
        判斷是否為文字檔案

        Args:
            file_path: 檔案路徑

        Returns:
            bool: 是否為文字檔案
        """
        _, ext = os.path.splitext(file_path.lower())
        return ext in self.text_extensions

    def _update_progress_files(self, old_case_id: str, new_case_id: str) -> Dict[str, Any]:
        """
        更新進度檔案中的案件編號

        Args:
            old_case_id: 原案件編號
            new_case_id: 新案件編號

        Returns:
            Dict: 更新結果
        """
        try:
            # 更新進度JSON檔案
            progress_file = os.path.join(self.data_folder, 'progress.json')

            if os.path.exists(progress_file):
                with open(progress_file, 'r', encoding='utf-8') as f:
                    progress_data = json.load(f)

                # 如果存在舊案件編號的進度資料，移動到新編號
                if old_case_id in progress_data:
                    progress_data[new_case_id] = progress_data.pop(old_case_id)

                    with open(progress_file, 'w', encoding='utf-8') as f:
                        json.dump(progress_data, f, ensure_ascii=False, indent=2)

                    return {'success': True, 'message': '進度檔案更新成功'}

            return {'success': True, 'message': '無需更新進度檔案'}

        except Exception as e:
            return {'success': False, 'message': f'進度檔案更新失敗: {str(e)}'}

    def _update_config_files(self, old_case_id: str, new_case_id: str) -> Dict[str, Any]:
        """
        更新設定檔案中的案件編號

        Args:
            old_case_id: 原案件編號
            new_case_id: 新案件編號

        Returns:
            Dict: 更新結果
        """
        try:
            updated_configs = []

            # 查找可能的設定檔案
            config_files = [
                os.path.join(self.data_folder, 'settings.json'),
                os.path.join(self.data_folder, 'config.json'),
                os.path.join(self.data_folder, 'case_settings.json')
            ]

            for config_file in config_files:
                if os.path.exists(config_file):
                    try:
                        with open(config_file, 'r', encoding='utf-8') as f:
                            content = f.read()

                        if old_case_id in content:
                            updated_content = content.replace(old_case_id, new_case_id)

                            with open(config_file, 'w', encoding='utf-8') as f:
                                f.write(updated_content)

                            updated_configs.append(os.path.basename(config_file))

                    except Exception as e:
                        print(f"⚠️ 更新設定檔失敗 {config_file}: {e}")

            if updated_configs:
                return {
                    'success': True,
                    'message': f'設定檔更新成功: {", ".join(updated_configs)}'
                }
            else:
                return {'success': True, 'message': '無需更新設定檔'}

        except Exception as e:
            return {'success': False, 'message': f'設定檔更新失敗: {str(e)}'}

    def _generate_success_message(self, old_case_id: str, new_case_id: str,
                                results: Dict[str, Any]) -> str:
        """
        產生成功訊息

        Args:
            old_case_id: 原案件編號
            new_case_id: 新案件編號
            results: 更新結果

        Returns:
            str: 成功訊息
        """
        message_parts = [f"案件編號更新成功: {old_case_id} → {new_case_id}"]

        if results['folder_renamed']:
            message_parts.append("✅ 資料夾已重新命名")

        if results['files_updated'] > 0:
            message_parts.append(f"✅ 已更新 {results['files_updated']} 個檔案的內容")

        if results['files_failed'] > 0:
            message_parts.append(f"⚠️ {results['files_failed']} 個檔案更新失敗")

        if results['warnings']:
            message_parts.append(f"⚠️ 警告: {len(results['warnings'])} 個項目")

        return "\n".join(message_parts)

    def validate_case_id_format(self, case_id: str) -> Tuple[bool, str]:
        """
        驗證案件編號格式

        Args:
            case_id: 案件編號

        Returns:
            Tuple[bool, str]: (是否有效, 錯誤訊息)
        """
        if not case_id or not case_id.strip():
            return False, "案件編號不能為空"

        case_id = case_id.strip().upper()

        # 基本格式檢查：長度應為6位數字
        if len(case_id) != 6:
            return False, "案件編號應為6位數字"

        if not case_id.isdigit():
            return False, "案件編號只能包含數字"

        # 檢查民國年份範圍（假設系統使用年份在100-999之間）
        try:
            year_part = int(case_id[:3])
            seq_part = int(case_id[3:])

            if year_part < 100 or year_part > 999:
                return False, "案件編號年份部分無效"

            if seq_part < 1 or seq_part > 999:
                return False, "案件編號序號部分無效"

        except ValueError:
            return False, "案件編號格式錯誤"

        return True, "案件編號格式正確"

    def backup_before_update(self, case_id: str, case_type: str) -> Tuple[bool, str]:
        """
        在更新前備份案件資料

        Args:
            case_id: 案件編號
            case_type: 案件類型

        Returns:
            Tuple[bool, str]: (是否成功, 備份路徑或錯誤訊息)
        """
        try:
            # 建立備份資料夾
            backup_folder = os.path.join(self.data_folder, '_backups',
                                       f"{case_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            os.makedirs(backup_folder, exist_ok=True)

            # 取得案件資料夾路徑
            case_type_folders = self.config.get('case_type_folders', {
                '民事': '民事',
                '刑事': '刑事',
                '行政': '行政'
            })

            case_type_folder = case_type_folders.get(case_type, case_type)
            source_folder = os.path.join(self.data_folder, case_type_folder, case_id)

            if os.path.exists(source_folder):
                # 複製案件資料夾
                shutil.copytree(source_folder, os.path.join(backup_folder, case_id))

            # 備份相關設定檔案
            config_files = ['cases.json', 'progress.json', 'settings.json']
            for config_file in config_files:
                source_file = os.path.join(self.data_folder, config_file)
                if os.path.exists(source_file):
                    shutil.copy2(source_file, backup_folder)

            return True, backup_folder

        except Exception as e:
            return False, f"備份失敗: {str(e)}"

    def restore_from_backup(self, backup_path: str, case_id: str, case_type: str) -> Tuple[bool, str]:
        """
        從備份恢復案件資料

        Args:
            backup_path: 備份路徑
            case_id: 案件編號
            case_type: 案件類型

        Returns:
            Tuple[bool, str]: (是否成功, 結果訊息)
        """
        try:
            if not os.path.exists(backup_path):
                return False, f"備份路徑不存在: {backup_path}"

            # 恢復案件資料夾
            case_type_folders = self.config.get('case_type_folders', {
                '民事': '民事',
                '刑事': '刑事',
                '行政': '行政'
            })

            case_type_folder = case_type_folders.get(case_type, case_type)
            target_folder = os.path.join(self.data_folder, case_type_folder, case_id)
            backup_case_folder = os.path.join(backup_path, case_id)

            if os.path.exists(backup_case_folder):
                # 如果目標資料夾存在，先刪除
                if os.path.exists(target_folder):
                    shutil.rmtree(target_folder)

                # 恢復案件資料夾
                shutil.copytree(backup_case_folder, target_folder)

            # 恢復設定檔案
            config_files = ['cases.json', 'progress.json', 'settings.json']
            for config_file in config_files:
                backup_file = os.path.join(backup_path, config_file)
                target_file = os.path.join(self.data_folder, config_file)

                if os.path.exists(backup_file):
                    shutil.copy2(backup_file, target_file)

            return True, f"成功從備份恢復案件: {case_id}"

        except Exception as e:
            return False, f"恢復備份失敗: {str(e)}"

    def get_update_summary(self, update_results: Dict[str, Any]) -> str:
        """
        取得更新摘要報告

        Args:
            update_results: 更新結果

        Returns:
            str: 摘要報告
        """
        summary_lines = []

        summary_lines.append("=== 案件編號更新摘要 ===")
        summary_lines.append(f"處理時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        summary_lines.append("")

        # 資料夾更新狀態
        if update_results['folder_renamed']:
            summary_lines.append("✅ 資料夾重新命名: 成功")
        else:
            summary_lines.append("❌ 資料夾重新命名: 失敗")

        # 檔案更新統計
        summary_lines.append(f"📁 檔案處理統計:")
        summary_lines.append(f"   總處理檔案: {update_results['files_processed']}")
        summary_lines.append(f"   成功更新: {update_results['files_updated']}")
        summary_lines.append(f"   更新失敗: {update_results['files_failed']}")

        # 成功更新的檔案列表
        if update_results['updated_files']:
            summary_lines.append("")
            summary_lines.append("✅ 成功更新的檔案:")
            for file_name in update_results['updated_files'][:10]:  # 最多顯示10個
                summary_lines.append(f"   - {file_name}")
            if len(update_results['updated_files']) > 10:
                summary_lines.append(f"   ... 還有 {len(update_results['updated_files']) - 10} 個檔案")

        # 失敗的檔案列表
        if update_results['failed_files']:
            summary_lines.append("")
            summary_lines.append("❌ 更新失敗的檔案:")
            for file_name in update_results['failed_files'][:5]:  # 最多顯示5個
                summary_lines.append(f"   - {file_name}")
            if len(update_results['failed_files']) > 5:
                summary_lines.append(f"   ... 還有 {len(update_results['failed_files']) - 5} 個檔案")

        # 警告訊息
        if update_results['warnings']:
            summary_lines.append("")
            summary_lines.append("⚠️ 警告訊息:")
            for warning in update_results['warnings']:
                summary_lines.append(f"   - {warning}")

        # 錯誤訊息
        if update_results['errors']:
            summary_lines.append("")
            summary_lines.append("❌ 錯誤訊息:")
            for error in update_results['errors']:
                summary_lines.append(f"   - {error}")

        summary_lines.append("")
        summary_lines.append("=== 摘要結束 ===")

        return "\n".join(summary_lines)

    def clean_old_backups(self, keep_days: int = 30) -> Tuple[bool, str]:
        """
        清理舊的備份檔案

        Args:
            keep_days: 保留天數

        Returns:
            Tuple[bool, str]: (是否成功, 結果訊息)
        """
        try:
            backup_folder = os.path.join(self.data_folder, '_backups')

            if not os.path.exists(backup_folder):
                return True, "沒有備份資料夾需要清理"

            cutoff_date = datetime.now() - timedelta(days=keep_days)
            deleted_count = 0

            for item in os.listdir(backup_folder):
                item_path = os.path.join(backup_folder, item)

                if os.path.isdir(item_path):
                    # 從資料夾名稱解析建立時間
                    try:
                        # 假設格式為 case_id_YYYYMMDD_HHMMSS
                        date_part = item.split('_')[-2] + item.split('_')[-1]
                        backup_date = datetime.strptime(date_part, '%Y%m%d%H%M%S')

                        if backup_date < cutoff_date:
                            shutil.rmtree(item_path)
                            deleted_count += 1
                            print(f"已刪除舊備份: {item}")

                    except (ValueError, IndexError):
                        # 如果無法解析日期，檢查檔案修改時間
                        mod_time = datetime.fromtimestamp(os.path.getmtime(item_path))
                        if mod_time < cutoff_date:
                            shutil.rmtree(item_path)
                            deleted_count += 1
                            print(f"已刪除舊備份: {item}")

            return True, f"清理完成，刪除了 {deleted_count} 個舊備份"

        except Exception as e:
            return False, f"清理備份失敗: {str(e)}"

