#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from typing import Generator, Optional
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from contextlib import contextmanager

# =========================================================
# 環境變數載入
# =========================================================
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# =========================================================
# 1) 讀取主系統資料庫連線
# =========================================================
DATABASE_URL = os.getenv("DATABASE_URL", "")

# 轉換 Heroku 舊格式
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL not set")

# =========================================================
# 2) 主系統 Engine / Session / Base
# =========================================================
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    future=True,
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
Base = declarative_base()

# =========================================================
# 3) 從主系統查詢租戶的專用連線字串
# =========================================================
def get_tenant_db_url(client_id: str) -> Optional[str]:
    """
    從主系統資料庫查詢指定租戶的 tenant_db_url
    - client_id: 事務所 / 租戶的唯一識別
    - 回傳: Postgres DSN 字串（可包含 search_path）
    """
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT tenant_db_url FROM login_users WHERE client_id = :cid"),
            {"cid": client_id}
        ).fetchone()
        return result[0] if result else None

# =========================================================
# 4) 動態建立資料庫 Session
# =========================================================
@contextmanager
def get_db(client_id: Optional[str] = None) -> Generator:
    """
    取得 SQLAlchemy Session
    - 無 client_id: 回傳主系統資料庫 Session
    - 有 client_id: 回傳該租戶專用資料庫 Session
    """
    if client_id:
        tenant_url = get_tenant_db_url(client_id)
        if not tenant_url:
            raise RuntimeError(f"找不到 client_id={client_id} 的租戶資料庫設定")
        tenant_engine = create_engine(tenant_url, pool_pre_ping=True, pool_recycle=300, future=True)
        Session = sessionmaker(bind=tenant_engine, autocommit=False, autoflush=False, future=True)
        db = Session()
    else:
        db = SessionLocal()

    try:
        yield db
    finally:
        db.close()

# =========================================================
# 5) Debug / 健康檢查
# =========================================================
def get_database_info():
    try:
        masked = DATABASE_URL
        if "@" in masked:
            userinfo, rest = masked.split("@", 1)
            masked = userinfo.split(":")[0] + ":***@" + rest
        return {"engine": str(engine.url), "url_masked": masked}
    except Exception:
        return {"engine": "unknown", "url_masked": "unknown"}
