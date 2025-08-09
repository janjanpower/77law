# api/database.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# 若在本地有 .env 可保留；Heroku 上沒有也沒關係
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# 1) 讀取 DATABASE_URL，並修正 Heroku 舊格式
DATABASE_URL = os.getenv("DATABASE_URL", "")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL not set")

# 2) 建立 Engine / Session / Base
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
Base = declarative_base()

# 3) FastAPI 依賴：取得 DB session
def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# （可選）提供資料庫資訊供 /health 或 debug 使用
def get_database_info():
    try:
        masked = DATABASE_URL
        if "@" in masked:
            userinfo, rest = masked.split("@", 1)
            masked = userinfo.split(":")[0] + ":***@" + rest
        return {"engine": str(engine.url), "url_masked": masked}
    except Exception:
        return {"engine": "unknown", "url_masked": "unknown"}
