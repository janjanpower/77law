# -*- coding: utf-8 -*-
"""
api/models_cases.py
案件資料庫模型 - 完整的 CaseRecord 定義（修正版，只保留你原本的欄位 + 必要補欄位）
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, Boolean, Index, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
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
    __tablename__ = "case_records"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 核心唯一鍵
    case_type = Column(String, nullable=False)
    case_id   = Column(String, nullable=False)

    # ✅ 新增：租戶/事務所識別
    client_id = Column(String, index=True)   # 可為空；之後上傳時會自動寫入

    # 其餘欄位（依你的實際欄位保持不變）
    client         = Column(String)   # 當事人姓名
    lawyer         = Column(String)
    legal_affairs  = Column(String)
    progress       = Column(String)
    case_reason    = Column(String)
    case_number    = Column(String)
    opposing_party = Column(String)
    court          = Column(String)
    division       = Column(String)
    progress_date  = Column(String)
    created_date   = Column(String)
    updated_date   = Column(String)

    progress_stages = Column(JSONB)
    progress_notes  = Column(JSONB)
    progress_times  = Column(JSONB)

    __table_args__ = (
        UniqueConstraint('case_type', 'case_id', name='ux_case_records_type_case'),
        Index('ix_case_records_case_type', 'case_type'),
        Index('ix_case_records_case_id', 'case_id'),
        Index('ix_case_records_client_id', 'client_id'),
    )


    def __repr__(self):
        return f"<CaseRecord(id={self.id}, client_id='{self.client_id}', case_id='{self.case_id}', client='{self.client}')>"

    def to_dict(self):
        """轉換為字典格式"""
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
            'id': self.id,
            'client_id': self.client_id,
            'uploaded_by': self.uploaded_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_active': self.is_active
        }
