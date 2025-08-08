# -*- coding: utf-8 -*-
"""
api/models_cases.py
案件資料庫模型 - 用於儲存上傳的案件資料
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, Boolean, Index, func
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import json

# 使用現有的 Base 或創建新的
try:
    from api.database import Base
except ImportError:
    from sqlalchemy.ext.declarative import declarative_base
    Base = declarative_base()


class CaseRecord(Base):
    """案件記錄表"""
    __tablename__ = "case_records"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(String(50), nullable=False, index=True)
    case_id = Column(String(100), nullable=False)
    case_type = Column(String(50), default="未分類")
    client = Column(String(100), nullable=False)
    lawyer = Column(String(100), default="")
    legal_affairs = Column(String(100), default="")
    progress = Column(String(100), default="待處理")

    # 詳細資訊
    case_reason = Column(String(200), default="")
    case_number = Column(String(100), default="")
    opposing_party = Column(String(200), default="")
    court = Column(String(100), default="")
    division = Column(String(100), default="")
    progress_date = Column(String(50), default="")

    # JSON 欄位
    progress_stages = Column(JSON, default=dict)
    progress_notes = Column(JSON, default=dict)
    progress_times = Column(JSON, default=dict)

    # 時間戳
    created_date = Column(DateTime, default=func.now())
    updated_date = Column(DateTime, default=func.now(), onupdate=func.now())
    uploaded_at = Column(DateTime, default=func.now())

    # 狀態
    is_deleted = Column(Boolean, default=False)
    uploaded_by = Column(String(50), default="system")

    # 時間戳記
    created_date = Column(DateTime, nullable=True, comment="原始建立日期")
    updated_date = Column(DateTime, nullable=True, comment="原始更新日期")
    upload_time = Column(DateTime, default=datetime.utcnow, nullable=False, comment="上傳時間")
    last_modified = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="最後修改時間")

    # 狀態欄位
    is_active = Column(Boolean, default=True, nullable=False, comment="是否啟用")
    is_deleted = Column(Boolean, default=False, nullable=False, comment="是否已刪除")

    # 建立索引
    __table_args__ = (
        Index('idx_client_case', 'client_id', 'case_id'),
        Index('idx_client_type', 'client_id', 'case_type'),
        Index('idx_client_lawyer', 'client_id', 'lawyer'),
        Index('idx_upload_time', 'upload_time'),
        Index('idx_progress', 'progress'),
    )

    def to_dict(self):
        """轉換為字典格式"""
        return {
            'id': self.id,
            'case_id': self.case_id,
            'case_type': self.case_type,
            'client': self.client,
            'lawyer': self.lawyer,
            'legal_affairs': self.legal_affairs,
            'progress': self.progress,
            'case_reason': self.case_reason,
            'case_number': self.case_number,
            'opposing_party': self.opposing_party,
            'court': self.court,
            'division': self.division,
            'progress_date': self.progress_date,
            'progress_stages': self.progress_stages or {},
            'progress_notes': self.progress_notes or {},
            'progress_times': self.progress_times or {},
            'client_id': self.client_id,
            'client_name': self.client_name,
            'uploaded_by': self.uploaded_by,
            'created_date': self.created_date.isoformat() if self.created_date else None,
            'updated_date': self.updated_date.isoformat() if self.updated_date else None,
            'upload_time': self.upload_time.isoformat() if self.upload_time else None,
            'last_modified': self.last_modified.isoformat() if self.last_modified else None,
            'is_active': self.is_active
        }

    @classmethod
    def from_case_data(cls, case_data: dict, client_info: dict):
        """從案件資料建立記錄"""
        return cls(
            client_id=client_info.get('client_id', 'unknown'),
            case_id=case_data.get('case_id', ''),
            case_type=case_data.get('case_type', '未分類'),
            client=case_data.get('client', ''),
            lawyer=case_data.get('lawyer', ''),
            legal_affairs=case_data.get('legal_affairs', ''),
            progress=case_data.get('progress', '待處理'),
            case_reason=case_data.get('case_reason', ''),
            case_number=case_data.get('case_number', ''),
            opposing_party=case_data.get('opposing_party', ''),
            court=case_data.get('court', ''),
            division=case_data.get('division', ''),
            progress_date=case_data.get('progress_date', ''),
            progress_stages=case_data.get('progress_stages', {}) or {},
            progress_notes=case_data.get('progress_notes', {}) or {},
            progress_times=case_data.get('progress_times', {}) or {},
            uploaded_by=client_info.get('client_id', 'system')
        )


class UploadLog(Base):
    """上傳日誌表"""
    __tablename__ = "upload_logs"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(String(50), nullable=False, index=True)
    upload_time = Column(DateTime, default=func.now())
    total_cases = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    success_rate = Column(String(10), nullable=True)
    upload_status = Column(String(20), default="completed")
    error_details = Column(JSON, nullable=True)

    # 建立索引
    __table_args__ = (
        Index('idx_client_upload_time', 'client_id', 'upload_time'),
    )

    def to_dict(self):
        """轉換為字典格式"""
        return {
            'id': self.id,
            'client_id': self.client_id,
            'client_name': self.client_name,
            'upload_time': self.upload_time.isoformat() if self.upload_time else None,
            'total_cases': self.total_cases,
            'success_count': self.success_count,
            'failed_count': self.failed_count,
            'success_rate': self.success_rate,
            'upload_status': self.upload_status,
            'error_details': self.error_details or {}
        }