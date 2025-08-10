#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from typing import Generator, Optional
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# ---- Primary DB URL ----
DATABASE_URL = os.getenv("DATABASE_URL", "")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL not set")

# ---- Engine / Session / Base ----
engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=300, future=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
Base = declarative_base()

# ---- Resolve tenant DSN from primary DB ----
def get_tenant_db_url(client_id: str) -> Optional[str]:
    with engine.connect() as conn:
        row = conn.execute(
            text("""SELECT tenant_db_url FROM login_users WHERE client_id=:cid LIMIT 1"""),
            {"cid": client_id},
        ).fetchone()
        return row[0] if row else None

# ---- Context manager for manual usage (with ...): supports tenant ----
@contextmanager
def get_db_cm(client_id: Optional[str] = None) -> Generator:
    if client_id:
        tenant_url = get_tenant_db_url(client_id)
        if not tenant_url:
            raise RuntimeError(f"No tenant_db_url configured for client_id={client_id}")
        tenant_engine = create_engine(tenant_url, pool_pre_ping=True, pool_recycle=300, future=True)
        Session = sessionmaker(bind=tenant_engine, autocommit=False, autoflush=False, future=True)
        db = Session()
    else:
        db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---- FastAPI dependency (yield style): primary DB only ----
def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_database_info():
    try:
        masked = str(engine.url)
        if "@" in masked:
            userinfo, rest = masked.split("@", 1)
            user = userinfo.split(":")[0]
            masked = f"{user}:***@{rest}"
        return {"engine": str(engine.url), "url_masked": masked}
    except Exception:
        return {"engine": "unknown", "url_masked": "unknown"}