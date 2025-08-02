#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
檔案資料存取層 (File Repository)
專責處理檔案相關的資料存取邏輯
"""

import os
import json
import shutil
import threading
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from pathlib import Path


class FileMetadata:
    """檔案元資料類別"""

    def __init__(self, file_path: str, case_id: str = None, category: str = None):
        self.file_path = file_path
        self.case_id = case_id
        self.category = category
        self.upload_time = datetime.now()
        self.file_size = 0
        self.file_type = ""
        self.description = ""

        if os.path.exists(file_path):
            self.file_size = os.path.getsize(file_path)
            self.file_type = os.path.splitext(file_path)[1].lower()

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            'file_path': self.file_path,
            'case_id': self.case_id,
            'category': self.category,
            'upload_time': self.upload_time.isoformat() if self.upload_time else None,
            'file_size': self.file_size,
            'file_type': self.file_type,
            'description': self.description
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FileMetadata':
        """從字典建立物件"""
        metadata = cls(data.get('file_path', ''), data.get('case_id'), data.get('category'))
        metadata.upload_time = datetime.fromisoformat(data['upload_time']) if data.get('upload_time') else datetime.now()
        metadata.file_size = data.get('file_size', 0)
        metadata.file_type = data.get('file_type', '')
        metadata.description = data.get('description', '')
        return metadata


class FileRepository:
    """檔案資料存取器"""

    def __init__(self, base_data_folder: str, metadata_file: str = None):
        """
        初始化檔案資料存取器

        Args:
            base_data_folder: 基礎資料資料夾路徑
            metadata_file: 檔案元資料檔案路徑
        """
        self.base_data_folder = base_data_folder
        self.metadata_file = metadata_file or os.path.join(base_data_folder, "file_metadata.json")
        self.file_metadata = []
        self._lock = threading.Lock()
        self._load_metadata()

    # ==================== 元資料管理 ====================

    def _load_metadata(self) -> bool:
        """
        載入檔案元資料

        Returns:
            bool: 載入是否成功
        """
        try:
            if os.path.exists(self.metadata_file):
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.file_metadata = [FileMetadata.from_dict(item) for item in data]

                print(f"✅ 成功載入 {len(self.file_metadata)} 筆檔案元資料")
                return True
            else:
                print("📂 檔案元資料檔案不存在，將建立新檔案")
                self.file_metadata = []
                return True

        except Exception as e:
            print(f"❌ 載入檔案元資料失敗: {e}")
            self.file_metadata = []
            return False

    def _save_metadata(self) -> bool:
        """
        儲存檔案元資料

        Returns:
            bool: 儲存是否成功
        """
        try:
            os.makedirs(os.path.dirname(self.metadata_file), exist_ok=True)

            data = [metadata.to_dict() for metadata in self.file_metadata]

            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)

            print(f"✅ 成功儲存 {len(self.file_metadata)} 筆檔案元資料")
            return True

        except Exception as e:
            print(f"❌ 儲存檔案元資料失敗: {e}")
            return False

    # ==================== 檔案操作 ====================

    def save_file(self, source_path: str, target_folder: str, case_id: str,
                  category: str = "一般文件", description: str = "") -> Tuple[bool, str]:
        """
        儲存檔案到指定位置

        Args:
            source_path: 來源檔案路徑
            target_folder: 目標資料夾路徑
            case_id: 案件ID
            category: 檔案分類
            description: 檔案描述

        Returns:
            Tuple[bool, str]: (成功與否, 目標檔案路徑或錯誤訊息)
        """
        try:
            if not os.path.exists(source_path):
                return False, f"來源檔案不存在: {source_path}"

            # 確保目標資料夾存在
            os.makedirs(target_folder, exist_ok=True)

            # 生成目標檔案路徑
            filename = os.path.basename(source_path)
            target_path = os.path.join(target_folder, filename)

            # 處理檔案名稱衝突
            counter = 1
            original_target_path = target_path
            while os.path.exists(target_path):
                name, ext = os.path.splitext(original_target_path)
                target_path = f"{name}_{counter}{ext}"
                counter += 1

            # 複製檔案
            shutil.copy2(source_path, target_path)

            # 建立檔案元資料
            metadata = FileMetadata(target_path, case_id, category)
            metadata.description = description

            with self._lock:
                self.file_metadata.append(metadata)
                self._save_metadata()

            print(f"✅ 檔案儲存成功: {target_path}")
            return True, target_path

        except Exception as e:
            error_msg = f"儲存檔案失敗: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg

    def move_file(self, current_path: str, target_folder: str) -> Tuple[bool, str]:
        """
        移動檔案到新位置

        Args:
            current_path: 當前檔案路徑
            target_folder: 目標資料夾路徑

        Returns:
            Tuple[bool, str]: (成功與否, 新檔案路徑或錯誤訊息)
        """
        try:
            if not os.path.exists(current_path):
                return False, f"檔案不存在: {current_path}"

            # 確保目標資料夾存在
            os.makedirs(target_folder, exist_ok=True)

            # 生成新檔案路徑
            filename = os.path.basename(current_path)
            new_path = os.path.join(target_folder, filename)

            # 處理檔案名稱衝突
            counter = 1
            original_new_path = new_path
            while os.path.exists(new_path):
                name, ext = os.path.splitext(original_new_path)
                new_path = f"{name}_{counter}{ext}"
                counter += 1

            # 移動檔案
            shutil.move(current_path, new_path)

            # 更新元資料
            with self._lock:
                for metadata in self.file_metadata:
                    if metadata.file_path == current_path:
                        metadata.file_path = new_path
                        break
                self._save_metadata()

            print(f"✅ 檔案移動成功: {current_path} -> {new_path}")
            return True, new_path

        except Exception as e:
            error_msg = f"移動檔案失敗: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg

    def delete_file(self, file_path: str, backup: bool = True) -> Tuple[bool, str]:
        """
        刪除檔案

        Args:
            file_path: 檔案路徑
            backup: 是否備份到回收區

        Returns:
            Tuple[bool, str]: (成功與否, 訊息)
        """
        try:
            if not os.path.exists(file_path):
                return False, f"檔案不存在: {file_path}"

            # 備份檔案
            if backup:
                backup_result = self._backup_file(file_path)
                if not backup_result[0]:
                    print(f"⚠️ 備份失敗，但繼續刪除: {backup_result[1]}")

            # 刪除檔案
            os.remove(file_path)

            # 從元資料中移除
            with self._lock:
                self.file_metadata = [m for m in self.file_metadata if m.file_path != file_path]
                self._save_metadata()

            print(f"🗑️ 檔案刪除成功: {file_path}")
            return True, f"檔案已刪除: {os.path.basename(file_path)}"

        except Exception as e:
            error_msg = f"刪除檔案失敗: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg

    def _backup_file(self, file_path: str) -> Tuple[bool, str]:
        """
        備份檔案到回收區

        Args:
            file_path: 檔案路徑

        Returns:
            Tuple[bool, str]: (成功與否, 備份路徑或錯誤訊息)
        """
        try:
            backup_folder = os.path.join(self.base_data_folder, "_backup", "deleted_files")
            os.makedirs(backup_folder, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.basename(file_path)
            name, ext = os.path.splitext(filename)
            backup_filename = f"{name}_{timestamp}{ext}"
            backup_path = os.path.join(backup_folder, backup_filename)

            shutil.copy2(file_path, backup_path)
            print(f"📋 檔案備份成功: {backup_path}")
            return True, backup_path

        except Exception as e:
            error_msg = f"備份檔案失敗: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg

    # ==================== 查詢操作 ====================

    def get_files_by_case(self, case_id: str) -> List[FileMetadata]:
        """
        取得特定案件的所有檔案

        Args:
            case_id: 案件ID

        Returns:
            List[FileMetadata]: 檔案元資料列表
        """
        with self._lock:
            return [metadata for metadata in self.file_metadata
                   if metadata.case_id == case_id]

    def get_files_by_category(self, category: str) -> List[FileMetadata]:
        """
        取得特定分類的所有檔案

        Args:
            category: 檔案分類

        Returns:
            List[FileMetadata]: 檔案元資料列表
        """
        with self._lock:
            return [metadata for metadata in self.file_metadata
                   if metadata.category == category]

    def get_files_by_type(self, file_type: str) -> List[FileMetadata]:
        """
        取得特定類型的所有檔案

        Args:
            file_type: 檔案類型 (如 .pdf, .docx)

        Returns:
            List[FileMetadata]: 檔案元資料列表
        """
        with self._lock:
            return [metadata for metadata in self.file_metadata
                   if metadata.file_type.lower() == file_type.lower()]

    def search_files(self, keyword: str) -> List[FileMetadata]:
        """
        搜尋檔案

        Args:
            keyword: 搜尋關鍵字

        Returns:
            List[FileMetadata]: 符合條件的檔案元資料列表
        """
        if not keyword:
            return self.get_all_files()

        keyword_lower = keyword.lower()
        with self._lock:
            results = []
            for metadata in self.file_metadata:
                # 搜尋檔案名稱、描述、分類
                if (keyword_lower in os.path.basename(metadata.file_path).lower() or
                    keyword_lower in metadata.description.lower() or
                    keyword_lower in metadata.category.lower()):
                    results.append(metadata)
            return results

    def get_all_files(self) -> List[FileMetadata]:
        """
        取得所有檔案元資料

        Returns:
            List[FileMetadata]: 所有檔案元資料
        """
        with self._lock:
            return self.file_metadata.copy()

    def get_file_metadata(self, file_path: str) -> Optional[FileMetadata]:
        """
        取得特定檔案的元資料

        Args:
            file_path: 檔案路徑

        Returns:
            Optional[FileMetadata]: 檔案元資料或None
        """
        with self._lock:
            for metadata in self.file_metadata:
                if metadata.file_path == file_path:
                    return metadata
            return None

    # ==================== 統計查詢 ====================

    def get_file_count_by_case(self) -> Dict[str, int]:
        """
        取得各案件的檔案數量統計

        Returns:
            Dict[str, int]: 各案件的檔案數量
        """
        with self._lock:
            case_counts = {}
            for metadata in self.file_metadata:
                if metadata.case_id:
                    case_counts[metadata.case_id] = case_counts.get(metadata.case_id, 0) + 1
            return case_counts

    def get_file_count_by_category(self) -> Dict[str, int]:
        """
        取得各分類的檔案數量統計

        Returns:
            Dict[str, int]: 各分類的檔案數量
        """
        with self._lock:
            category_counts = {}
            for metadata in self.file_metadata:
                if metadata.category:
                    category_counts[metadata.category] = category_counts.get(metadata.category, 0) + 1
            return category_counts

    def get_total_file_size(self) -> int:
        """
        取得所有檔案的總大小

        Returns:
            int: 總檔案大小（位元組）
        """
        with self._lock:
            return sum(metadata.file_size for metadata in self.file_metadata)

    def get_file_size_by_case(self, case_id: str) -> int:
        """
        取得特定案件的檔案總大小

        Args:
            case_id: 案件ID

        Returns:
            int: 檔案總大小（位元組）
        """
        case_files = self.get_files_by_case(case_id)
        return sum(metadata.file_size for metadata in case_files)

    # ==================== 檔案驗證 ====================

    def validate_file_integrity(self) -> Dict[str, Any]:
        """
        驗證檔案完整性

        Returns:
            Dict[str, Any]: 驗證結果
        """
        validation_result = {
            'is_valid': True,
            'total_files': len(self.file_metadata),
            'missing_files': [],
            'orphaned_metadata': [],
            'size_mismatches': []
        }

        with self._lock:
            for metadata in self.file_metadata:
                file_path = metadata.file_path

                # 檢查檔案是否存在
                if not os.path.exists(file_path):
                    validation_result['missing_files'].append(file_path)
                    validation_result['is_valid'] = False
                else:
                    # 檢查檔案大小是否一致
                    actual_size = os.path.getsize(file_path)
                    if actual_size != metadata.file_size:
                        validation_result['size_mismatches'].append({
                            'file_path': file_path,
                            'expected_size': metadata.file_size,
                            'actual_size': actual_size
                        })
                        validation_result['is_valid'] = False

        return validation_result

    def cleanup_orphaned_metadata(self) -> int:
        """
        清理孤立的元資料（對應檔案不存在）

        Returns:
            int: 清理的元資料數量
        """
        cleaned_count = 0

        with self._lock:
            valid_metadata = []
            for metadata in self.file_metadata:
                if os.path.exists(metadata.file_path):
                    valid_metadata.append(metadata)
                else:
                    print(f"🧹 清理孤立元資料: {metadata.file_path}")
                    cleaned_count += 1

            self.file_metadata = valid_metadata
            if cleaned_count > 0:
                self._save_metadata()

        print(f"✅ 清理完成，移除了 {cleaned_count} 筆孤立元資料")
        return cleaned_count

    # ==================== 批次操作 ====================

    def batch_update_metadata(self, updates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        批次更新檔案元資料

        Args:
            updates: 更新資料列表，格式: [{'file_path': '', 'updates': {}}]

        Returns:
            Dict[str, Any]: 批次更新結果
        """
        result = {
            'success_count': 0,
            'failed_count': 0,
            'errors': []
        }

        try:
            with self._lock:
                for update_data in updates:
                    file_path = update_data.get('file_path')
                    updates_dict = update_data.get('updates', {})

                    # 找到檔案元資料
                    metadata_found = False
                    for metadata in self.file_metadata:
                        if metadata.file_path == file_path:
                            # 更新欄位
                            for field, value in updates_dict.items():
                                if hasattr(metadata, field):
                                    setattr(metadata, field, value)

                            metadata_found = True
                            result['success_count'] += 1
                            break

                    if not metadata_found:
                        result['failed_count'] += 1
                        result['errors'].append(f"找不到檔案元資料: {file_path}")

                # 儲存變更
                if result['success_count'] > 0:
                    self._save_metadata()

        except Exception as e:
            result['errors'].append(f"批次更新失敗: {str(e)}")

        return result

    def batch_move_files(self, case_id: str, target_folder: str) -> Dict[str, Any]:
        """
        批次移動案件的所有檔案

        Args:
            case_id: 案件ID
            target_folder: 目標資料夾

        Returns:
            Dict[str, Any]: 批次移動結果
        """
        result = {
            'success_count': 0,
            'failed_count': 0,
            'errors': []
        }

        case_files = self.get_files_by_case(case_id)

        for metadata in case_files:
            move_result = self.move_file(metadata.file_path, target_folder)
            if move_result[0]:
                result['success_count'] += 1
            else:
                result['failed_count'] += 1
                result['errors'].append(f"{metadata.file_path}: {move_result[1]}")

        return result

    # ==================== 匯出功能 ====================

    def export_file_list(self, export_path: str, case_id: str = None) -> bool:
        """
        匯出檔案清單

        Args:
            export_path: 匯出檔案路徑
            case_id: 案件ID（可選，不指定則匯出所有）

        Returns:
            bool: 匯出是否成功
        """
        try:
            if case_id:
                files_to_export = self.get_files_by_case(case_id)
            else:
                files_to_export = self.get_all_files()

            export_data = {
                'export_time': datetime.now().isoformat(),
                'total_files': len(files_to_export),
                'case_id': case_id,
                'files': [metadata.to_dict() for metadata in files_to_export]
            }

            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2, default=str)

            print(f"✅ 檔案清單匯出成功: {export_path}")
            return True

        except Exception as e:
            print(f"❌ 匯出檔案清單失敗: {e}")
            return False


# 確保 FileRepository 類別被正確導出
__all__ = ['FileRepository', 'FileMetadata']