#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
進度管理業務邏輯服務
專責處理案件進度追蹤相關的業務邏輯
"""

from typing import List, Optional, Dict, Any, Tuple
from models.case_model import CaseData
from .folder_service import FolderService
from .notification_service import NotificationService
from datetime import datetime, timedelta
from enum import Enum
import json
import os


class ProgressStatus(Enum):
    """進度狀態"""
    NOT_STARTED = "未開始"
    IN_PROGRESS = "進行中"
    COMPLETED = "已完成"
    DELAYED = "延期"
    CANCELLED = "取消"


class ProgressPriority(Enum):
    """進度優先級"""
    LOW = "低"
    NORMAL = "一般"
    HIGH = "高"
    URGENT = "緊急"


class ProgressStage:
    """進度階段資料結構"""

    def __init__(self, stage_id: str, name: str, description: str = "",
                 status: ProgressStatus = ProgressStatus.NOT_STARTED,
                 priority: ProgressPriority = ProgressPriority.NORMAL,
                 start_date: datetime = None, due_date: datetime = None,
                 completion_date: datetime = None, assignee: str = "",
                 dependencies: List[str] = None, notes: str = ""):
        self.stage_id = stage_id
        self.name = name
        self.description = description
        self.status = status
        self.priority = priority
        self.start_date = start_date
        self.due_date = due_date
        self.completion_date = completion_date
        self.assignee = assignee
        self.dependencies = dependencies or []
        self.notes = notes
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式"""
        return {
            'stage_id': self.stage_id,
            'name': self.name,
            'description': self.description,
            'status': self.status.value,
            'priority': self.priority.value,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'completion_date': self.completion_date.isoformat() if self.completion_date else None,
            'assignee': self.assignee,
            'dependencies': self.dependencies,
            'notes': self.notes,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProgressStage':
        """從字典建立進度階段"""
        stage = cls(
            stage_id=data['stage_id'],
            name=data['name'],
            description=data.get('description', ''),
            status=ProgressStatus(data.get('status', ProgressStatus.NOT_STARTED.value)),
            priority=ProgressPriority(data.get('priority', ProgressPriority.NORMAL.value)),
            assignee=data.get('assignee', ''),
            dependencies=data.get('dependencies', []),
            notes=data.get('notes', '')
        )

        # 解析日期
        if data.get('start_date'):
            stage.start_date = datetime.fromisoformat(data['start_date'])
        if data.get('due_date'):
            stage.due_date = datetime.fromisoformat(data['due_date'])
        if data.get('completion_date'):
            stage.completion_date = datetime.fromisoformat(data['completion_date'])
        if data.get('created_at'):
            stage.created_at = datetime.fromisoformat(data['created_at'])
        if data.get('updated_at'):
            stage.updated_at = datetime.fromisoformat(data['updated_at'])

        return stage


class ProgressService:
    """進度管理業務邏輯服務"""

    def __init__(self, data_folder: str):
        """
        初始化進度服務

        Args:
            data_folder: 資料資料夾路徑
        """
        self.data_folder = data_folder
        self.progress_data_file = os.path.join(data_folder, "progress_data.json")

        # 初始化相依服務
        self.folder_service = FolderService(data_folder)
        self.notification_service = NotificationService()

        # 載入進度資料
        self.progress_data = self._load_progress_data()
        print("✅ ProgressService 初始化完成")

    # ==================== 進度階段管理 ====================

    def create_progress_stage(self, case_id: str, stage_data: Dict[str, Any],
                            create_folder: bool = True) -> Tuple[bool, str]:
        """
        建立新的進度階段

        Args:
            case_id: 案件ID
            stage_data: 階段資料
            create_folder: 是否建立對應的資料夾

        Returns:
            (成功與否, 結果訊息)
        """
        try:
            print(f"📝 建立進度階段: {stage_data.get('name', '未命名')}")

            # 驗證輸入資料
            validation_result = self._validate_stage_data(stage_data)
            if not validation_result[0]:
                return False, f"階段資料驗證失敗: {validation_result[1]}"

            # 建立進度階段物件
            stage = ProgressStage(
                stage_id=stage_data.get('stage_id') or self._generate_stage_id(case_id),
                name=stage_data['name'],
                description=stage_data.get('description', ''),
                status=ProgressStatus(stage_data.get('status', ProgressStatus.NOT_STARTED.value)),
                priority=ProgressPriority(stage_data.get('priority', ProgressPriority.NORMAL.value)),
                assignee=stage_data.get('assignee', ''),
                dependencies=stage_data.get('dependencies', []),
                notes=stage_data.get('notes', '')
            )

            # 設定日期
            if stage_data.get('start_date'):
                stage.start_date = self._parse_date(stage_data['start_date'])
            if stage_data.get('due_date'):
                stage.due_date = self._parse_date(stage_data['due_date'])

            # 檢查依賴關係
            dependency_check = self._validate_dependencies(case_id, stage.dependencies)
            if not dependency_check[0]:
                return False, f"依賴關係驗證失敗: {dependency_check[1]}"

            # 添加到進度資料
            if case_id not in self.progress_data:
                self.progress_data[case_id] = []

            self.progress_data[case_id].append(stage.to_dict())

            # 儲存進度資料
            self._save_progress_data()

            # 建立資料夾（如果需要）
            if create_folder:
                folder_result = self._create_stage_folder(case_id, stage.name)
                if not folder_result[0]:
                    print(f"⚠️ 警告: 階段資料夾建立失敗 - {folder_result[1]}")

            # 發送通知
            self.notification_service.create_custom_notification(
                title="進度階段建立",
                message=f"已建立新的進度階段: {stage.name}",
                data={'case_id': case_id, 'stage_id': stage.stage_id}
            )

            print(f"✅ 成功建立進度階段: {stage.name}")
            return True, f"成功建立階段: {stage.name}"

        except Exception as e:
            error_msg = f"建立進度階段失敗: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg

    def update_progress_stage(self, case_id: str, stage_id: str,
                            updates: Dict[str, Any]) -> Tuple[bool, str]:
        """
        更新進度階段

        Args:
            case_id: 案件ID
            stage_id: 階段ID
            updates: 更新資料

        Returns:
            (成功與否, 結果訊息)
        """
        try:
            print(f"🔄 更新進度階段: {stage_id}")

            # 尋找階段
            stage_data = self._find_stage(case_id, stage_id)
            if not stage_data:
                return False, f"找不到進度階段: {stage_id}"

            # 記錄變更
            changes = []
            old_status = stage_data.get('status')

            # 更新資料
            for key, value in updates.items():
                if key in stage_data and stage_data[key] != value:
                    changes.append(f"{key}: {stage_data[key]} → {value}")
                    stage_data[key] = value

            # 更新時間戳
            stage_data['updated_at'] = datetime.now().isoformat()

            # 處理狀態變更
            new_status = stage_data.get('status')
            if old_status != new_status:
                status_change_result = self._handle_status_change(case_id, stage_id, old_status, new_status)
                if not status_change_result[0]:
                    return False, f"狀態變更處理失敗: {status_change_result[1]}"

            # 儲存進度資料
            self._save_progress_data()

            # 發送通知
            if changes:
                self.notification_service.create_custom_notification(
                    title="進度階段更新",
                    message=f"階段 {stage_data['name']} 已更新: {'; '.join(changes[:3])}{'...' if len(changes) > 3 else ''}",
                    data={'case_id': case_id, 'stage_id': stage_id, 'changes': changes}
                )

            print(f"✅ 成功更新進度階段: {stage_data['name']}")
            return True, f"成功更新階段: {stage_data['name']}"

        except Exception as e:
            error_msg = f"更新進度階段失敗: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg

    def _load_progress_data(self) -> Dict[str, List[Dict[str, Any]]]:
        """載入進度資料"""
        try:
            if os.path.exists(self.progress_data_file):
                with open(self.progress_data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                print(f"✅ 載入進度資料: {len(data)} 個案件")
                return data
            else:
                return {}
        except Exception as e:
            print(f"⚠️ 載入進度資料失敗: {e}")
            return {}

    def _save_progress_data(self):
        """儲存進度資料"""
        try:
            with open(self.progress_data_file, 'w', encoding='utf-8') as f:
                json.dump(self.progress_data, f, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            print(f"⚠️ 儲存進度資料失敗: {e}")