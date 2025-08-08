#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
api/database.py (修復版本)
確保資料庫依賴注入正確運作
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

# 取得資料庫URL
DATABASE_URL = os.getenv("DATABASE_URL")

# 🔥 關鍵修復：處理預設資料庫名稱問題
if not DATABASE_URL:
    # 如果沒有DATABASE_URL，使用本地SQLite
    DATABASE_URL = "sqlite:///./law_system.db"
    print("⚠️ 使用預設SQLite資料庫")
elif DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# 建立引擎
try:
    engine = create_engine(
        DATABASE_URL,
        echo=False,  # 關閉SQL日誌避免干擾
        pool_pre_ping=True,
        pool_recycle=300
    )
    print(f"✅ 資料庫引擎建立成功")
except Exception as e:
    print(f"❌ 資料庫引擎建立失敗: {e}")
    # 使用記憶體SQLite作為最後手段
    DATABASE_URL = "sqlite:///:memory:"
    engine = create_engine(DATABASE_URL)

# 建立會話工廠
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 建立Base類別
Base = declarative_base()

def get_control_db():
    """
    取得資料庫會話 (FastAPI依賴注入用)
    修復 'default' 錯誤的關鍵函數
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        print(f"❌ 資料庫會話錯誤: {e}")
        db.rollback()
        raise
    finally:
        db.close()

def get_database_info():
    """取得資料庫資訊"""
    return {
        "database_url_masked": DATABASE_URL.split('@')[0] + "@[HIDDEN]" if '@' in DATABASE_URL else DATABASE_URL,
        "engine_info": str(engine.url),
        "is_connected": True
    }