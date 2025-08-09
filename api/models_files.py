# -*- coding: utf-8 -*-
# api/models_files.py
from sqlalchemy import Column, Integer, String, DateTime, JSON, Index, func

try:
    from api.database import Base
except ImportError:
    from sqlalchemy.ext.declarative import declarative_base
    Base = declarative_base()

class FileBlob(Base):
    __tablename__ = "file_blobs"
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(String(50), nullable=False, index=True)
    case_id   = Column(String(100), nullable=False, index=True)
    filename     = Column(String(255), nullable=False)
    content_type = Column(String(100), nullable=True)
    size_bytes   = Column(Integer, nullable=False)
    s3_key       = Column(String(512), nullable=False)
    uploaded_by  = Column(String(100), nullable=True)
    uploaded_at  = Column(DateTime, server_default=func.now(), nullable=False)

    # ⚠️ ORM 屬性叫 meta；資料庫欄位仍是 "metadata"
    meta = Column("metadata", JSON, nullable=True)

Index("ix_file_blobs_client_case", FileBlob.client_id, FileBlob.case_id)
