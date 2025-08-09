# -*- coding: utf-8 -*-
"""
api/models_cases.py
案件資料庫模型 - 完整的 CaseRecord 定義
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, Boolean, Index, func
from sqlalchemy.ext.declarative import declarative_base

# 使用現有的 Base 或建立新的
try:
    from api.database import Base
except ImportError:
    try:
        from database import Base
    except ImportError:
        Base = declarative_base()


class CaseRecord(Base):
    """案件記錄資料表 - 完整版"""
    __tablename__ = "case_records"

    # 主鍵
    id = Column(Integer, primary_key=True, index=True, comment="主鍵")

    # 必要識別欄位
    client_id = Column(String(50), nullable=False, index=True, comment="事務所ID")
    case_id = Column(String(100), nullable=False, index=True, comment="案件編號")

    # 基本案件資訊 - 完全匹配 case_model.py
    case_type = Column(String(50), nullable=False, comment="案件類型")  # 刑事/民事
    client = Column(String(100), nullable=False, comment="當事人")
    lawyer = Column(String(100), nullable=True, comment="委任律師")
    legal_affairs = Column(String(100), nullable=True, comment="法務人員")

    # 案件狀態 - 完全匹配 case_model.py
    progress = Column(String(50), nullable=False, default="待處理", comment="進度追蹤")
    case_reason = Column(Text, nullable=True, comment="案由")
    case_number = Column(String(100), nullable=True, comment="案號")
    opposing_party = Column(String(100), nullable=True, comment="對造")
    court = Column(String(100), nullable=True, comment="負責法院")
    division = Column(String(50), nullable=True, comment="負責股別")
    progress_date = Column(String(20), nullable=True, comment="當前進度的日期")

    # JSON 欄位 - 完全匹配 case_model.py 的字典結構
    progress_stages = Column(JSON, nullable=True, comment="進度階段記錄 {階段: 日期}")
    progress_notes = Column(JSON, nullable=True, comment="進度階段備註 {階段: 備註}")
    progress_times = Column(JSON, nullable=True, comment="進度階段時間 {階段: 時間}")

    # 時間戳記 - 匹配 case_model.py
    created_date = Column(DateTime, nullable=True, comment="原始建立日期")
    updated_date = Column(DateTime, nullable=True, comment="原始更新日期")
    # 資料庫管理欄位
    uploaded_by = Column(String(100), nullable=True, comment="上傳者")
    created_at = Column(DateTime, server_default=func.now(), nullable=False, comment="資料庫建立時間")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False, comment="資料庫更新時間")

    # 狀態欄位
    is_active = Column(Boolean, default=True, nullable=False, comment="是否啟用")
    is_deleted = Column(Boolean, default=False, nullable=False, comment="是否已刪除")

    # 建立索引以提升查詢效能
    __table_args__ = (
        Index('idx_client_case', 'client_id', 'case_id'),
        Index('idx_client_type', 'client_id', 'case_type'),
        Index('idx_client_lawyer', 'client_id', 'lawyer'),
        Index('idx_upload_time', 'created_at'),
        Index('idx_progress', 'progress'),
        Index('idx_case_number', 'case_number'),
    )

    def __repr__(self):
        return f"<CaseRecord(id={self.id}, client_id='{self.client_id}', case_id='{self.case_id}', client='{self.client}')>"

    def to_dict(self):
        """轉換為字典格式 - 匹配 case_model.py 的 to_dict 結構"""
        return {
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
            'created_date': self.created_date.isoformat() if self.created_date else None,
            'updated_date': self.updated_date.isoformat() if self.updated_date else None,
            # 額外的資料庫欄位
            'id': self.id,
            'client_id': self.client_id,
            'uploaded_by': self.uploaded_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_active': self.is_active
        }