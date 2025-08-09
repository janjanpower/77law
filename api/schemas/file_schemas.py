#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
案件資料夾檔案管理系統 - 完整實作
包含控制層、邏輯層、API端點和檔案傳輸功能
"""

import hashlib
import os
from datetime import datetime, timedelta
import secrets
from typing import Optional, Dict, Any, List, Tuple
import zipfile

from fastapi import HTTPException, Path, Query
import shutil

from pathlib import Path
import json

# ==================== 1. 資料模型擴展 ====================

from pydantic import BaseModel, Field

class FolderContentItem(BaseModel):
    """資料夾內容項目"""
    name: str = Field(..., description="檔案/資料夾名稱")
    type: str = Field(..., description="類型: file/folder")
    size: int = Field(default=0, description="檔案大小(位元組)")
    size_mb: float = Field(default=0.0, description="檔案大小(MB)")
    modified_date: str = Field(..., description="修改日期")
    file_extension: Optional[str] = Field(default=None, description="檔案副檔名")
    file_category: str = Field(..., description="檔案分類: document/image/audio/video/other")
    relative_path: str = Field(..., description="相對路徑")
    can_preview: bool = Field(default=False, description="是否可預覽")
    download_url: Optional[str] = Field(default=None, description="下載連結")

class CaseFolderStructure(BaseModel):
    """案件資料夾結構"""
    case_id: str = Field(..., description="案件編號")
    client: str = Field(..., description="當事人")
    folder_path: str = Field(..., description="資料夾路徑")
    total_files: int = Field(default=0, description="總檔案數")
    total_size_mb: float = Field(default=0.0, description="總大小(MB)")
    subfolders: List[Dict[str, Any]] = Field(default_factory=list, description="子資料夾列表")
    recent_files: List[FolderContentItem] = Field(default_factory=list, description="最近檔案")
    file_categories: Dict[str, int] = Field(default_factory=dict, description="檔案分類統計")

class FileTransferRequest(BaseModel):
    """檔案傳輸請求"""
    case_id: str = Field(..., description="案件編號")
    file_paths: List[str] = Field(..., description="檔案路徑列表")
    transfer_method: str = Field(..., description="傳輸方式: single/zip/preview")
    client_info: Optional[Dict[str, str]] = Field(default=None, description="客戶資訊")
    expiry_hours: int = Field(default=24, description="連結有效期(小時)")

class FileTransferResponse(BaseModel):
    """檔案傳輸回應"""
    success: bool = Field(..., description="傳輸是否成功")
    transfer_id: str = Field(..., description="傳輸ID")
    download_links: List[Dict[str, str]] = Field(..., description="下載連結列表")
    zip_download_url: Optional[str] = Field(default=None, description="ZIP下載連結")
    preview_urls: List[Dict[str, str]] = Field(default_factory=list, description="預覽連結")
    expires_at: str = Field(..., description="過期時間")
    file_count: int = Field(..., description="檔案數量")
    total_size_mb: float = Field(..., description="總大小")

# ==================== 2. 檔案分類邏輯層 ====================

class FileClassifier:
    """檔案分類器"""

    CATEGORIES = {
        'document': ['.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt', '.xlsx', '.xls', '.ppt', '.pptx'],
        'image': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.tiff', '.webp'],
        'audio': ['.mp3', '.wav', '.aac', '.flac', '.ogg', '.m4a', '.wma'],
        'video': ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v']
    }

    PREVIEW_SUPPORTED = {
        'image': ['.jpg', '.jpeg', '.png', '.gif', '.webp'],
        'document': ['.pdf', '.txt'],
        'audio': ['.mp3', '.wav'],
        'video': ['.mp4', '.webm']
    }

    @classmethod
    def get_file_category(cls, file_extension: str) -> str:
        """取得檔案分類"""
        ext_lower = file_extension.lower()
        for category, extensions in cls.CATEGORIES.items():
            if ext_lower in extensions:
                return category
        return 'other'

    @classmethod
    def can_preview(cls, file_extension: str, file_size_mb: float) -> bool:
        """判斷檔案是否可預覽"""
        if file_size_mb > 50:  # 大於50MB不提供預覽
            return False

        ext_lower = file_extension.lower()
        for category, extensions in cls.PREVIEW_SUPPORTED.items():
            if ext_lower in extensions:
                return True
        return False

    @classmethod
    def get_optimal_transfer_method(cls, files: List[Dict]) -> str:
        """根據檔案特性推薦最佳傳輸方式"""
        total_size = sum(f.get('size_mb', 0) for f in files)
        file_count = len(files)

        # 單個小圖片 → 直接傳送
        if file_count == 1 and files[0].get('file_category') == 'image' and total_size < 10:
            return 'single'

        # 多檔案或大檔案 → 打包
        if file_count > 3 or total_size > 20:
            return 'zip'

        # 可預覽檔案 → 預覽連結
        if all(f.get('can_preview', False) for f in files):
            return 'preview'

        return 'single'

# ==================== 3. 安全檔案傳輸邏輯層 ====================

class SecureFileTransfer:
    """安全檔案傳輸管理器"""

    def __init__(self, base_url: str, temp_folder: str):
        self.base_url = base_url
        self.temp_folder = temp_folder
        self.transfer_records = {}  # 在實際應用中應使用資料庫

        # 確保臨時資料夾存在
        os.makedirs(temp_folder, exist_ok=True)

    def create_secure_download_link(self, file_path: str, expiry_hours: int = 24) -> Dict[str, str]:
        """建立安全下載連結"""
        try:
            # 生成唯一的傳輸ID
            transfer_id = secrets.token_urlsafe(32)

            # 計算檔案雜湊值
            file_hash = self._calculate_file_hash(file_path)

            # 建立過期時間
            expires_at = datetime.now() + timedelta(hours=expiry_hours)

            # 儲存傳輸記錄
            self.transfer_records[transfer_id] = {
                'file_path': file_path,
                'file_hash': file_hash,
                'expires_at': expires_at.isoformat(),
                'download_count': 0,
                'created_at': datetime.now().isoformat()
            }

            # 生成下載URL
            download_url = f"{self.base_url}/download/{transfer_id}"

            return {
                'transfer_id': transfer_id,
                'download_url': download_url,
                'expires_at': expires_at.isoformat(),
                'file_name': os.path.basename(file_path)
            }

        except Exception as e:
            print(f"建立安全下載連結失敗: {e}")
            return {}

    def create_zip_package(self, files: List[str], case_id: str) -> str:
        """建立ZIP打包檔案"""
        try:
            # 生成ZIP檔案名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            zip_filename = f"case_{case_id}_{timestamp}.zip"
            zip_path = os.path.join(self.temp_folder, zip_filename)

            # 建立ZIP檔案
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in files:
                    if os.path.exists(file_path):
                        # 使用相對路徑作為ZIP內部路徑
                        arcname = os.path.basename(file_path)
                        zipf.write(file_path, arcname)

            return zip_path

        except Exception as e:
            print(f"建立ZIP檔案失敗: {e}")
            return ""

    def _calculate_file_hash(self, file_path: str) -> str:
        """計算檔案SHA256雜湊值"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def verify_transfer(self, transfer_id: str) -> Tuple[bool, str]:
        """驗證傳輸請求"""
        if transfer_id not in self.transfer_records:
            return False, "無效的傳輸ID"

        record = self.transfer_records[transfer_id]
        expires_at = datetime.fromisoformat(record['expires_at'])

        if datetime.now() > expires_at:
            return False, "下載連結已過期"

        if not os.path.exists(record['file_path']):
            return False, "檔案不存在"

        return True, "驗證通過"

# ==================== 4. 案件資料夾檔案邏輯層 ====================

class CaseFolderFileLogic:
    """案件資料夾檔案管理邏輯層"""

    def __init__(self, case_controller, base_url: str = "http://localhost:8000"):
        self.case_controller = case_controller
        self.file_transfer = SecureFileTransfer(
            base_url=base_url,
            temp_folder="temp_downloads"
        )
        self.classifier = FileClassifier()

    def get_case_folder_structure(self, case_id: str) -> Optional[CaseFolderStructure]:
        """取得案件資料夾結構"""
        try:
            # 取得案件資料
            case_data = self.case_controller.get_case_by_id(case_id)
            if not case_data:
                return None

            # 取得資料夾路徑
            folder_path = self.case_controller.folder_manager.get_case_folder_path(case_data)
            if not folder_path or not os.path.exists(folder_path):
                return None

            # 分析資料夾內容
            total_files, total_size, subfolders, recent_files, file_categories = self._analyze_folder_content(folder_path)

            return CaseFolderStructure(
                case_id=case_id,
                client=case_data.client,
                folder_path=folder_path,
                total_files=total_files,
                total_size_mb=round(total_size / (1024 * 1024), 2),
                subfolders=subfolders,
                recent_files=recent_files,
                file_categories=file_categories
            )

        except Exception as e:
            print(f"取得案件資料夾結構失敗: {e}")
            return None

    def get_folder_files(self, case_id: str, subfolder: str = "") -> List[FolderContentItem]:
        """取得指定資料夾內的檔案列表"""
        try:
            case_data = self.case_controller.get_case_by_id(case_id)
            if not case_data:
                return []

            base_folder = self.case_controller.folder_manager.get_case_folder_path(case_data)
            if not base_folder:
                return []

            target_folder = os.path.join(base_folder, subfolder) if subfolder else base_folder

            if not os.path.exists(target_folder):
                return []

            files = []
            for item in os.listdir(target_folder):
                item_path = os.path.join(target_folder, item)

                if os.path.isfile(item_path):
                    file_info = self._create_file_content_item(item_path, subfolder)
                    if file_info:
                        files.append(file_info)

            # 按修改時間排序（最新的在前）
            files.sort(key=lambda x: x.modified_date, reverse=True)
            return files

        except Exception as e:
            print(f"取得資料夾檔案失敗: {e}")
            return []

    def prepare_file_transfer(self, request: FileTransferRequest) -> FileTransferResponse:
        """準備檔案傳輸"""
        try:
            case_data = self.case_controller.get_case_by_id(request.case_id)
            if not case_data:
                raise ValueError(f"找不到案件: {request.case_id}")

            base_folder = self.case_controller.folder_manager.get_case_folder_path(case_data)
            if not base_folder:
                raise ValueError("找不到案件資料夾")

            # 驗證並取得完整檔案路徑
            full_file_paths = []
            file_infos = []
            total_size = 0

            for relative_path in request.file_paths:
                full_path = os.path.join(base_folder, relative_path)
                if os.path.exists(full_path) and os.path.isfile(full_path):
                    full_file_paths.append(full_path)

                    file_size = os.path.getsize(full_path)
                    file_size_mb = file_size / (1024 * 1024)
                    total_size += file_size_mb

                    file_info = {
                        'path': full_path,
                        'name': os.path.basename(full_path),
                        'size_mb': file_size_mb,
                        'extension': os.path.splitext(full_path)[1],
                        'category': self.classifier.get_file_category(os.path.splitext(full_path)[1])
                    }
                    file_infos.append(file_info)

            if not full_file_paths:
                raise ValueError("沒有找到有效的檔案")

            # 檢查檔案大小限制
            if total_size > 100:
                raise ValueError(f"檔案總大小超過限制 ({total_size:.1f}MB > 100MB)")

            # 決定傳輸方式
            if request.transfer_method == 'auto':
                transfer_method = self.classifier.get_optimal_transfer_method(file_infos)
            else:
                transfer_method = request.transfer_method

            # 生成傳輸ID
            transfer_id = secrets.token_urlsafe(16)

            # 建立下載連結
            download_links = []
            preview_urls = []
            zip_download_url = None

            if transfer_method == 'zip' or len(full_file_paths) > 1:
                # 建立ZIP檔案
                zip_path = self.file_transfer.create_zip_package(full_file_paths, request.case_id)
                if zip_path:
                    zip_link = self.file_transfer.create_secure_download_link(
                        zip_path, request.expiry_hours
                    )
                    zip_download_url = zip_link.get('download_url')

            else:
                # 單檔案下載連結
                for file_path in full_file_paths:
                    link_info = self.file_transfer.create_secure_download_link(
                        file_path, request.expiry_hours
                    )
                    if link_info:
                        download_links.append({
                            'file_name': link_info['file_name'],
                            'download_url': link_info['download_url'],
                            'transfer_id': link_info['transfer_id']
                        })

                        # 建立預覽連結（如果支援）
                        file_ext = os.path.splitext(file_path)[1]
                        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)

                        if self.classifier.can_preview(file_ext, file_size_mb):
                            preview_urls.append({
                                'file_name': link_info['file_name'],
                                'preview_url': f"{link_info['download_url']}?preview=true"
                            })

            # 記錄傳輸歷史
            self._log_transfer_history(request.case_id, transfer_id, file_infos, request.client_info)

            expires_at = datetime.now() + timedelta(hours=request.expiry_hours)

            return FileTransferResponse(
                success=True,
                transfer_id=transfer_id,
                download_links=download_links,
                zip_download_url=zip_download_url,
                preview_urls=preview_urls,
                expires_at=expires_at.isoformat(),
                file_count=len(full_file_paths),
                total_size_mb=round(total_size, 2)
            )

        except Exception as e:
            print(f"準備檔案傳輸失敗: {e}")
            return FileTransferResponse(
                success=False,
                transfer_id="",
                download_links=[],
                expires_at="",
                file_count=0,
                total_size_mb=0.0
            )

    def _analyze_folder_content(self, folder_path: str) -> Tuple[int, int, List[Dict], List[FolderContentItem], Dict[str, int]]:
        """分析資料夾內容"""
        total_files = 0
        total_size = 0
        subfolders = []
        recent_files = []
        file_categories = {'document': 0, 'image': 0, 'audio': 0, 'video': 0, 'other': 0}

        try:
            # 遍歷資料夾
            for root, dirs, files in os.walk(folder_path):
                # 子資料夾資訊
                if root == folder_path:
                    for dir_name in dirs:
                        dir_path = os.path.join(root, dir_name)
                        dir_size = sum(
                            os.path.getsize(os.path.join(dirpath, filename))
                            for dirpath, dirnames, filenames in os.walk(dir_path)
                            for filename in filenames
                        )
                        dir_file_count = sum(len(filenames) for _, _, filenames in os.walk(dir_path))

                        subfolders.append({
                            'name': dir_name,
                            'path': os.path.relpath(dir_path, folder_path),
                            'file_count': dir_file_count,
                            'size_mb': round(dir_size / (1024 * 1024), 2)
                        })

                # 檔案資訊
                for file_name in files:
                    file_path = os.path.join(root, file_name)
                    file_size = os.path.getsize(file_path)
                    total_files += 1
                    total_size += file_size

                    # 檔案分類統計
                    file_ext = os.path.splitext(file_name)[1]
                    category = self.classifier.get_file_category(file_ext)
                    file_categories[category] += 1

                    # 收集最近檔案
                    if len(recent_files) < 10:
                        relative_path = os.path.relpath(file_path, folder_path)
                        file_item = self._create_file_content_item(file_path, os.path.dirname(relative_path))
                        if file_item:
                            recent_files.append(file_item)

            # 按修改時間排序最近檔案
            recent_files.sort(key=lambda x: x.modified_date, reverse=True)
            recent_files = recent_files[:5]  # 只保留最近5個檔案

        except Exception as e:
            print(f"分析資料夾內容失敗: {e}")

        return total_files, total_size, subfolders, recent_files, file_categories

    def _create_file_content_item(self, file_path: str, subfolder: str = "") -> Optional[FolderContentItem]:
        """建立檔案內容項目"""
        try:
            if not os.path.exists(file_path):
                return None

            file_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            file_size_mb = file_size / (1024 * 1024)
            modified_time = datetime.fromtimestamp(os.path.getmtime(file_path))
            file_ext = os.path.splitext(file_name)[1]

            category = self.classifier.get_file_category(file_ext)
            can_preview = self.classifier.can_preview(file_ext, file_size_mb)

            relative_path = os.path.join(subfolder, file_name) if subfolder else file_name

            return FolderContentItem(
                name=file_name,
                type="file",
                size=file_size,
                size_mb=round(file_size_mb, 2),
                modified_date=modified_time.isoformat(),
                file_extension=file_ext,
                file_category=category,
                relative_path=relative_path,
                can_preview=can_preview
            )

        except Exception as e:
            print(f"建立檔案內容項目失敗: {e}")
            return None

    def _log_transfer_history(self, case_id: str, transfer_id: str, files: List[Dict], client_info: Dict):
        """記錄傳輸歷史"""
        try:
            # 在實際應用中，這裡應該寫入資料庫
            log_entry = {
                'transfer_id': transfer_id,
                'case_id': case_id,
                'timestamp': datetime.now().isoformat(),
                'file_count': len(files),
                'total_size_mb': sum(f.get('size_mb', 0) for f in files),
                'files': [f.get('name') for f in files],
                'client_info': client_info
            }
            print(f"檔案傳輸記錄: {log_entry}")

        except Exception as e:
            print(f"記錄傳輸歷史失敗: {e}")

# ==================== 5. 控制層擴展 ====================

class CaseControllerExtension:
    """案件控制器擴展 - 檔案管理功能"""

    def __init__(self, case_controller):
        self.case_controller = case_controller
        self.folder_file_logic = CaseFolderFileLogic(case_controller)

    def get_case_detail_without_current_status(self, case_id: str) -> Dict[str, Any]:
        """取得案件詳細資訊（移除當前狀態顯示）"""
        try:
            case_data = self.case_controller.get_case_by_id(case_id)
            if not case_data:
                return {'success': False, 'message': '找不到案件'}

            # 使用修改後的格式化器（移除當前狀態）
            detail_text = self._format_case_detail_without_status(case_data)

            return {
                'success': True,
                'case_detail': detail_text,
                'case_data': case_data
            }

        except Exception as e:
            print(f"取得案件詳細資訊失敗: {e}")
            return {'success': False, 'message': f'系統錯誤: {str(e)}'}

    def get_case_folder_content(self, case_id: str, subfolder: str = "") -> Dict[str, Any]:
        """取得案件資料夾內容"""
        try:
            # 取得資料夾結構
            folder_structure = self.folder_file_logic.get_case_folder_structure(case_id)
            if not folder_structure:
                return {'success': False, 'message': '找不到案件資料夾'}

            # 取得檔案列表
            files = self.folder_file_logic.get_folder_files(case_id, subfolder)

            return {
                'success': True,
                'folder_structure': folder_structure,
                'files': files,
                'current_path': subfolder or "根目錄"
            }

        except Exception as e:
            print(f"取得案件資料夾內容失敗: {e}")
            return {'success': False, 'message': f'系統錯誤: {str(e)}'}

    def prepare_files_for_client(self, case_id: str, file_paths: List[str],
                                client_info: Optional[Dict] = None) -> Dict[str, Any]:
        """為客戶準備檔案傳輸"""
        try:
            request = FileTransferRequest(
                case_id=case_id,
                file_paths=file_paths,
                transfer_method='auto',
                client_info=client_info,
                expiry_hours=24
            )

            response = self.folder_file_logic.prepare_file_transfer(request)

            if response.success:
                return {
                    'success': True,
                    'transfer_response': response,
                    'message': f'已準備 {response.file_count} 個檔案進行傳輸'
                }
            else:
                return {
                    'success': False,
                    'message': '檔案傳輸準備失敗'
                }

        except Exception as e:
            print(f"準備檔案傳輸失敗: {e}")
            return {'success': False, 'message': f'系統錯誤: {str(e)}'}

    def _format_case_detail_without_status(self, case_data) -> str:
        """格式化案件詳細資訊（移除當前狀態）"""
        try:
            response = "📋 案件詳細資訊\n"
            response += "=" * 30 + "\n"

            # 基本資訊
            response += f"📌 案件編號：{case_data.case_id}\n"
            response += f"👤 當事人：{case_data.client}\n"
            response += f"⚖️ 案件類型：{case_data.case_type}\n"

            if case_data.case_reason:
                response += f"📝 案由：{case_data.case_reason}\n"

            if case_data.case_number:
                response += f"🏛️ 案號：{case_data.case_number}\n"

            if case_data.lawyer:
                response += f"👨‍💼 委任律師：{case_data.lawyer}\n"

            if case_data.legal_affairs:
                response += f"👩‍💼 法務：{case_data.legal_affairs}\n"

            if hasattr(case_data, 'opposing_party') and case_data.opposing_party:
                response += f"🔄 對造：{case_data.opposing_party}\n"

            if hasattr(case_data, 'court') and case_data.court:
                response += f"🏛️ 負責法院：{case_data.court}\n"

            if hasattr(case_data, 'division') and case_data.division:
                response += f"📍 負責股別：{case_data.division}\n"

            # 📁 新增：資料夾資訊層級
            response += "\n📁 案件資料夾：\n"
            folder_info = self._get_folder_summary(case_data)
            response += folder_info

            # 時間戳記
            response += f"\n🕐 建立時間：{case_data.created_date.strftime('%Y-%m-%d %H:%M')}\n"
            response += f"🔄 更新時間：{case_data.updated_date.strftime('%Y-%m-%d %H:%M')}\n"

            response += "\n" + "=" * 30

            return response

        except Exception as e:
            print(f"格式化案件詳細資料失敗: {e}")
            return f"❌ 無法顯示案件 {getattr(case_data, 'case_id', '未知')} 的詳細資料"

    def _get_folder_summary(self, case_data) -> str:
        """取得資料夾摘要資訊"""
        try:
            folder_structure = self.folder_file_logic.get_case_folder_structure(case_data.case_id)

            if not folder_structure:
                return "⚠️ 尚未建立案件資料夾\n"

            summary = f"📂 資料夾位置：{os.path.basename(folder_structure.folder_path)}\n"
            summary += f"📊 檔案統計：共 {folder_structure.total_files} 個檔案 ({folder_structure.total_size_mb}MB)\n"

            # 檔案分類統計
            if folder_structure.file_categories:
                category_icons = {
                    'document': '📄', 'image': '🖼️',
                    'audio': '🎵', 'video': '🎬', 'other': '📎'
                }

                categories = []
                for category, count in folder_structure.file_categories.items():
                    if count > 0:
                        icon = category_icons.get(category, '📎')
                        categories.append(f"{icon}{count}")

                if categories:
                    summary += f"📋 分類：{' | '.join(categories)}\n"

            # 子資料夾
            if folder_structure.subfolders:
                summary += f"📁 子資料夾：{len(folder_structure.subfolders)} 個\n"
                for subfolder in folder_structure.subfolders[:3]:  # 只顯示前3個
                    summary += f"   └ {subfolder['name']} ({subfolder['file_count']}個檔案)\n"

                if len(folder_structure.subfolders) > 3:
                    summary += f"   └ ...還有 {len(folder_structure.subfolders) - 3} 個資料夾\n"

            # 最近檔案
            if folder_structure.recent_files:
                summary += f"📅 最近檔案：\n"
                for file_item in folder_structure.recent_files[:2]:  # 只顯示最近2個
                    file_icon = self._get_file_icon(file_item.file_category)
                    summary += f"   {file_icon} {file_item.name}\n"

            return summary

        except Exception as e:
            print(f"取得資料夾摘要失敗: {e}")
            return "❌ 無法取得資料夾資訊\n"

    def _get_file_icon(self, category: str) -> str:
        """取得檔案圖示"""
        icons = {
            'document': '📄',
            'image': '🖼️',
            'audio': '🎵',
            'video': '🎬',
            'other': '📎'
        }
        return icons.get(category, '📎')

# ==================== 6. API端點擴展 ====================

"""
以下為需要添加到 api.py 的新端點：

# 添加到現有的 api.py 檔案中

@app.get("/api/cases/{case_id}/detail-without-status")
def get_case_detail_without_status(case_id: str = Path(..., description="案件編號")):
    \"\"\"取得案件詳細資訊（移除當前狀態顯示）\"\"\"
    try:
        if not MODULES_OK:
            raise HTTPException(status_code=503, detail="系統模組不可用")

        controller = get_controller()
        extension = CaseControllerExtension(controller)

        result = extension.get_case_detail_without_current_status(case_id)

        if not result['success']:
            raise HTTPException(status_code=404, detail=result['message'])

        return {
            "success": True,
            "case_id": case_id,
            "detail": result['case_detail'],
            "timestamp": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 取得案件詳細資訊 API 錯誤: {e}")
        raise HTTPException(status_code=500, detail="系統錯誤")

@app.get("/api/cases/{case_id}/folder")
def get_case_folder_content(
    case_id: str = Path(..., description="案件編號"),
    subfolder: str = Query("", description="子資料夾路徑")
):
    \"\"\"取得案件資料夾內容\"\"\"
    try:
        if not MODULES_OK:
            raise HTTPException(status_code=503, detail="系統模組不可用")

        controller = get_controller()
        extension = CaseControllerExtension(controller)

        result = extension.get_case_folder_content(case_id, subfolder)

        if not result['success']:
            raise HTTPException(status_code=404, detail=result['message'])

        return {
            "success": True,
            "case_id": case_id,
            "current_path": result['current_path'],
            "folder_structure": result['folder_structure'],
            "files": result['files'],
            "timestamp": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 取得案件資料夾內容 API 錯誤: {e}")
        raise HTTPException(status_code=500, detail="系統錯誤")

@app.post("/api/cases/{case_id}/prepare-files")
def prepare_files_for_transfer(
    case_id: str = Path(..., description="案件編號"),
    request: Dict[str, Any] = None
):
    \"\"\"準備檔案傳輸給客戶\"\"\"
    try:
        if not MODULES_OK:
            raise HTTPException(status_code=503, detail="系統模組不可用")

        if not request or 'file_paths' not in request:
            raise HTTPException(status_code=400, detail="請提供檔案路徑列表")

        controller = get_controller()
        extension = CaseControllerExtension(controller)

        file_paths = request['file_paths']
        client_info = request.get('client_info', {})

        result = extension.prepare_files_for_client(case_id, file_paths, client_info)

        if not result['success']:
            raise HTTPException(status_code=400, detail=result['message'])

        return {
            "success": True,
            "case_id": case_id,
            "transfer_info": result['transfer_response'],
            "message": result['message'],
            "timestamp": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 準備檔案傳輸 API 錯誤: {e}")
        raise HTTPException(status_code=500, detail="系統錯誤")

@app.get("/download/{transfer_id}")
def download_file(transfer_id: str = Path(..., description="傳輸ID")):
    \"\"\"安全檔案下載端點\"\"\"
    try:
        controller = get_controller()
        extension = CaseControllerExtension(controller)
        file_transfer = extension.folder_file_logic.file_transfer

        # 驗證傳輸請求
        valid, message = file_transfer.verify_transfer(transfer_id)
        if not valid:
            raise HTTPException(status_code=403, detail=message)

        # 取得檔案資訊
        record = file_transfer.transfer_records[transfer_id]
        file_path = record['file_path']

        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="檔案不存在")

        # 更新下載次數
        record['download_count'] += 1

        from fastapi.responses import FileResponse
        return FileResponse(
            path=file_path,
            filename=os.path.basename(file_path),
            media_type='application/octet-stream'
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 檔案下載 API 錯誤: {e}")
        raise HTTPException(status_code=500, detail="檔案下載失敗")

# 全域變數擴展（添加到現有的全域變數區域）
case_controller_extension = None  # 新增：案件控制器擴展

def get_case_controller_extension():
    \"\"\"取得案件控制器擴展實例\"\"\"
    global case_controller_extension
    if case_controller_extension is None and MODULES_OK:
        try:
            controller = get_controller()
            case_controller_extension = CaseControllerExtension(controller)
            print("✅ 案件控制器擴展初始化成功")
        except Exception as e:
            print(f"❌ 案件控制器擴展初始化失敗: {e}")
            raise
    return case_controller_extension
"""

# ==================== 7. LINE Bot 集成示例 ====================

class LineBotFileManager:
    """LINE Bot 檔案管理集成"""

    def __init__(self, case_controller_extension):
        self.extension = case_controller_extension

    def handle_hierarchical_file_request(self, case_id: str, user_message: str,
                                       user_state: dict = None) -> str:
        """處理階層式檔案請求"""
        try:
            message_lower = user_message.lower()

            # 初始化用戶狀態
            if not user_state:
                user_state = {'browse_step': 0, 'current_folder': '', 'selected_files': []}

            # 解析用戶請求
            if message_lower in ["資料夾", "檔案", "瀏覽檔案"]:
                return self._show_folder_menu(case_id, user_state)
            elif message_lower.startswith("資料夾") and len(message_lower) > 3:
                # 處理資料夾選擇 (例如: "資料夾 1")
                folder_num = message_lower.replace("資料夾", "").strip()
                return self._enter_folder(case_id, folder_num, user_state)
            elif message_lower.startswith("檔案") and len(message_lower) > 2:
                # 處理檔案選擇 (例如: "檔案 1")
                file_num = message_lower.replace("檔案", "").strip()
                return self._show_file_detail(case_id, file_num, user_state)
            elif message_lower.startswith("下載"):
                return self._handle_download_request(case_id, user_message, user_state)
            elif message_lower in ["返回", "上一步"]:
                return self._handle_back_navigation(case_id, user_state)
            else:
                return self._show_file_help()

        except Exception as e:
            print(f"處理階層式檔案請求失敗: {e}")
            return "❌ 處理檔案請求時發生錯誤"

    def _show_folder_menu(self, case_id: str, user_state: dict) -> str:
        """顯示資料夾選單"""
        try:
            # 取得案件資料
            case_data = self.extension.case_controller.get_case_by_id(case_id)
            if not case_data:
                return "❌ 找不到指定案件"

            # 取得資料夾路徑
            folder_manager = self.extension.case_controller.folder_manager
            if not folder_manager:
                return "❌ 資料夾管理器不可用"

            case_folder_path = folder_manager.get_case_folder_path(case_data)
            if not case_folder_path or not os.path.exists(case_folder_path):
                return f"❌ 找不到案件「{case_data.client}」的資料夾\n💡 請先建立案件資料夾"

            # 列舉子資料夾
            subfolders = []
            for item in os.listdir(case_folder_path):
                item_path = os.path.join(case_folder_path, item)
                if os.path.isdir(item_path):
                    # 計算檔案數量
                    file_count = sum(len(files) for _, _, files in os.walk(item_path))
                    subfolders.append({
                        'name': item,
                        'path': item_path,
                        'file_count': file_count
                    })

            if not subfolders:
                return f"📂 案件「{case_data.client}」的資料夾為空\n💡 請先上傳檔案到案件資料夾"

            # 格式化資料夾選單
            response = f"📁 {case_data.client} 的案件資料夾\n"
            response += "=" * 30 + "\n\n"
            response += "📂 請選擇要瀏覽的資料夾：\n\n"

            user_state['folders'] = {}
            for i, folder in enumerate(subfolders, 1):
                folder_name = folder['name']
                file_count = folder['file_count']
                user_state['folders'][str(i)] = folder
                response += f"{i}. 📁 {folder_name} ({file_count} 個檔案)\n"

            response += f"\n💡 輸入數字選擇資料夾 (1-{len(subfolders)})"
            response += "\n💡 例如：輸入「1」進入第一個資料夾"

            user_state['browse_step'] = 1  # 設定為資料夾選擇步驟
            return response

        except Exception as e:
            print(f"顯示資料夾選單失敗: {e}")
            return "❌ 無法顯示資料夾選單"

    def _enter_folder(self, case_id: str, folder_selection: str, user_state: dict) -> str:
        """進入選擇的資料夾"""
        try:
            # 檢查是否為數字選擇
            try:
                folder_index = int(folder_selection)
                folder_key = str(folder_index)
            except ValueError:
                available_count = len(user_state.get('folders', {}))
                return f"❌ 請輸入有效的資料夾編號 (1-{available_count})"

            if 'folders' not in user_state or folder_key not in user_state['folders']:
                return "❌ 請先選擇資料夾選單，輸入「資料夾」重新開始"

            # 取得選擇的資料夾
            selected_folder = user_state['folders'][folder_key]
            folder_name = selected_folder['name']
            folder_path = selected_folder['path']

            # 讀取資料夾內的檔案
            files = []
            try:
                for item in os.listdir(folder_path):
                    item_path = os.path.join(folder_path, item)
                    if os.path.isfile(item_path):
                        file_size = os.path.getsize(item_path)
                        file_size_mb = file_size / (1024 * 1024)
                        modified_time = datetime.fromtimestamp(os.path.getmtime(item_path))

                        files.append({
                            'name': item,
                            'path': item_path,
                            'size': file_size,
                            'size_mb': round(file_size_mb, 2),
                            'extension': os.path.splitext(item)[1].lower(),
                            'modified': modified_time
                        })

                # 按修改時間排序（最新的在前）
                files.sort(key=lambda x: x['modified'], reverse=True)

            except Exception as e:
                print(f"讀取資料夾檔案失敗: {e}")
                return f"❌ 無法讀取資料夾「{folder_name}」的內容"

            if not files:
                response = f"📂 資料夾「{folder_name}」為空\n\n"
                response += "💡 輸入「返回」選擇其他資料夾"
                return response

            # 格式化檔案列表
            response = f"📁 資料夾：{folder_name}\n"
            response += "=" * 30 + "\n\n"
            response += f"📄 檔案列表 ({len(files)} 個檔案)：\n\n"

            user_state['files'] = {}
            user_state['current_folder'] = folder_name
            user_state['current_folder_path'] = folder_path

            for i, file_info in enumerate(files, 1):
                file_name = file_info['name']
                file_size_mb = file_info['size_mb']
                file_ext = file_info['extension']

                # 取得檔案圖示
                icon = get_file_icon(file_ext)

                user_state['files'][str(i)] = file_info

                size_text = f"({file_size_mb:.1f}MB)" if file_size_mb >= 0.1 else "(<0.1MB)"
                response += f"{i}. {icon} {file_name} {size_text}\n"

            response += f"\n💡 輸入數字查看檔案詳細資訊 (1-{len(files)})"
            response += "\n💡 輸入「下載 1,3,5」選擇多個檔案下載"
            response += "\n💡 輸入「全部下載」下載所有檔案"
            response += "\n💡 輸入「返回」回到資料夾選擇"

            user_state['browse_step'] = 2  # 設定為檔案選擇步驟
            return response

        except Exception as e:
            print(f"進入資料夾失敗: {e}")
            return "❌ 進入資料夾失敗"

    def _show_file_detail(self, case_id: str, file_selection: str, user_state: dict) -> str:
        """顯示檔案詳細資訊"""
        try:
            # 檢查是否為數字選擇
            try:
                file_index = int(file_selection)
                file_key = str(file_index)
            except ValueError:
                available_count = len(user_state.get('files', {}))
                return f"❌ 請輸入有效的檔案編號 (1-{available_count})"

            if 'files' not in user_state or file_key not in user_state['files']:
                return "❌ 請先進入資料夾，輸入「資料夾」重新開始"

            # 取得選擇的檔案
            file_info = user_state['files'][file_key]
            file_name = file_info['name']
            file_path = file_info['path']
            file_size_mb = file_info['size_mb']
            modified_time = file_info['modified']

            # 格式化檔案詳細資訊
            response = f"📄 檔案詳細資訊\n"
            response += "=" * 30 + "\n\n"
            response += f"📝 檔案名稱：{file_name}\n"
            response += f"📦 檔案大小：{file_size_mb:.2f}MB\n"
            response += f"🕒 修改時間：{modified_time.strftime('%Y-%m-%d %H:%M')}\n"
            response += f"📂 所在資料夾：{user_state.get('current_folder', '未知')}\n\n"

            response += f"💡 輸入「下載 {file_index}」下載此檔案\n"
            response += "💡 輸入「返回」回到檔案列表"

            return response

        except Exception as e:
            print(f"顯示檔案詳細資訊失敗: {e}")
            return "❌ 無法顯示檔案詳細資訊"

    def _handle_download_request(self, case_id: str, user_message: str, user_state: dict) -> str:
        """處理下載請求"""
        try:
            if 'files' not in user_state or not user_state['files']:
                return "❌ 請先進入資料夾並選擇檔案"

            message_lower = user_message.lower()

            # 處理全部下載
            if message_lower in ["全部下載", "下載全部", "all"]:
                selected_indices = list(range(1, len(user_state['files']) + 1))
            else:
                # 解析下載指令 (例如: "下載 1,3,5")
                import re
                numbers_match = re.search(r'下載\s*(.+)', user_message)
                if not numbers_match:
                    return "❌ 下載指令格式錯誤，請使用「下載 1,3,5」格式"

                numbers_str = numbers_match.group(1).strip()

                try:
                    selected_indices = []
                    for num_str in numbers_str.split(','):
                        num = int(num_str.strip())
                        if str(num) in user_state['files']:
                            selected_indices.append(num)
                        else:
                            return f"❌ 檔案編號 {num} 不存在 (有效範圍: 1-{len(user_state['files'])})"

                    if not selected_indices:
                        return "❌ 沒有選擇有效的檔案"

                except ValueError:
                    return "❌ 檔案編號格式錯誤，請使用「下載 1,3,5」格式"

            # 準備檔案下載
            selected_files = []
            case_folder_path = None

            try:
                # 取得案件資料夾根路徑
                case_data = self.extension.case_controller.get_case_by_id(case_id)
                folder_manager = self.extension.case_controller.folder_manager
                case_folder_path = folder_manager.get_case_folder_path(case_data)
            except Exception as e:
                print(f"取得案件資料夾路徑失敗: {e}")

            for index in selected_indices:
                file_info = user_state['files'][str(index)]
                file_path = file_info['path']

                # 計算相對路徑
                if case_folder_path:
                    try:
                        relative_path = os.path.relpath(file_path, case_folder_path)
                    except Exception:
                        relative_path = file_info['name']
                else:
                    relative_path = file_info['name']

                selected_files.append(relative_path)

            # 使用現有的檔案傳輸邏輯
            transfer_result = self.extension.prepare_files_for_client(
                case_id,
                selected_files,
                {
                    "source": "line_bot_hierarchical_browser",
                    "folder": user_state.get('current_folder', ''),
                    "timestamp": datetime.now().isoformat()
                }
            )

            if not transfer_result['success']:
                return f"❌ 檔案下載準備失敗：{transfer_result.get('message', '未知錯誤')}"

            transfer_response = transfer_result['transfer_response']

            response = f"✅ 已準備 {len(selected_indices)} 個檔案進行下載\n\n"
            response += f"📦 總大小：{transfer_response.total_size_mb:.1f}MB\n"
            response += f"⏰ 連結有效期：24小時\n\n"

            # 提供下載連結
            if transfer_response.zip_download_url:
                response += f"📥 打包下載：\n{transfer_response.zip_download_url}\n\n"

            if transfer_response.download_links:
                response += "📄 個別下載：\n"
                for i, link in enumerate(transfer_response.download_links[:3], 1):
                    response += f"{i}. {link['file_name']}\n"

                if len(transfer_response.download_links) > 3:
                    response += f"... 還有 {len(transfer_response.download_links) - 3} 個檔案\n"

            response += "\n🔒 連結安全加密，僅限您使用"
            response += "\n💡 輸入「返回」繼續瀏覽檔案"

            return response

        except Exception as e:
            print(f"處理下載請求失敗: {e}")
            return "❌ 檔案下載處理失敗"

    def _handle_back_navigation(self, case_id: str, user_state: dict) -> str:
        """處理返回導航"""
        try:
            browse_step = user_state.get('browse_step', 0)

            if browse_step == 2:
                # 從檔案列表返回資料夾選擇
                user_state['browse_step'] = 0
                user_state['current_folder'] = ''
                user_state['files'] = {}
                return self._show_folder_menu(case_id, user_state)
            else:
                # 退出資料夾瀏覽模式
                user_state.clear()
                return "🔄 已退出資料夾瀏覽模式\n💡 輸入「資料夾」重新瀏覽檔案"

        except Exception as e:
            print(f"處理返回導航失敗: {e}")
            return "❌ 返回導航處理失敗"

    def _show_file_help(self) -> str:
        """顯示檔案功能說明 - 階層瀏覽版本"""
        return """📁 階層式檔案瀏覽功能

🔍 查看檔案：
• 輸入「資料夾」或「檔案」查看案件檔案

📤 傳送檔案：
• 輸入「傳送檔案」選擇要傳送的檔案
• 支援文檔、圖片、音檔、影片（≤100MB）

💡 使用方式：
1. 查看案件詳細資訊
2. 瀏覽案件資料夾
3. 選擇要傳送的檔案
4. 取得安全下載連結

🔒 安全保障：
• 檔案連結加密保護
• 24小時自動過期
• 僅限您個人使用"""

# ==================== 8. 使用範例 ====================

def example_usage():
    """使用範例"""
    print("=" * 50)
    print("📁 案件資料夾檔案管理系統 - 使用範例")
    print("=" * 50)

    # 假設已有 case_controller 實例
    # controller = CaseController()
    # extension = CaseControllerExtension(controller)

    print("""
    # 1. 取得案件詳細資訊（無當前狀態）
    result = extension.get_case_detail_without_current_status("113001")
    print(result['case_detail'])

    # 2. 瀏覽案件資料夾
    folder_result = extension.get_case_folder_content("113001")
    print(f"檔案數量: {len(folder_result['files'])}")

    # 3. 準備檔案傳輸
    files_to_send = ["document.pdf", "evidence.jpg"]
    transfer_result = extension.prepare_files_for_client(
        "113001",
        files_to_send,
        {"client_name": "張三", "phone": "0912345678"}
    )

    print(f"下載連結: {transfer_result['transfer_response'].download_links}")

    # 4. LINE Bot 整合
    line_manager = LineBotFileManager(extension)
    response = line_manager.handle_file_request("113001", "查看資料夾")
    print(f"LINE回覆: {response}")
    """)

if __name__ == "__main__":
    example_usage()