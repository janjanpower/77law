# -*- coding: utf-8 -*-
# api/services/tenant_bootstrap.py
# 建立每個租戶專屬的 Postgres schema；確保建立 case_records；並把 schema 連線字串寫回 login_users.tenant_db_url

import os
import re
import urllib.parse
import psycopg2
from psycopg2 import sql
from sqlalchemy import create_engine, text

from api.database import Base
from api.models_cases import CaseRecord

DATABASE_URL = os.getenv("DATABASE_URL", "")

# 正規化 DSN（Heroku 舊格式）
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)

_slug_re = re.compile(r"[^a-z0-9_]+")

def _schema_name_from_client_id(client_id: str) -> str:
    s = client_id.strip().lower().replace("-", "_")
    s = _slug_re.sub("_", s).strip("_") or "x"
    return f"tenant_{s}"

def _compose_schema_url(base_url: str, schema: str) -> str:
    sep = "&" if "?" in base_url else "?"
    return f"{base_url}{sep}options={urllib.parse.quote('-c search_path=' + schema)}"

def _ensure_case_records_sql_fallback(engine):
    """If ORM create_all did not create the table, fallback to SQL DDL."""
    ddl = text(
        """
        CREATE TABLE IF NOT EXISTS case_records (
            id BIGSERIAL PRIMARY KEY,
            client_id TEXT NOT NULL,
            case_id   TEXT NOT NULL,
            case_type TEXT,
            client    TEXT,
            lawyer    TEXT,
            legal_affairs TEXT,
            progress  TEXT,
            case_reason TEXT,
            case_number TEXT,
            opposing_party TEXT,
            court     TEXT,
            division  TEXT,
            progress_date TEXT,
            progress_stages JSONB DEFAULT '{}'::jsonb,
            progress_notes  JSONB DEFAULT '{}'::jsonb,
            progress_times  JSONB DEFAULT '{}'::jsonb,
            created_date TIMESTAMPTZ NULL,
            updated_date TIMESTAMPTZ NULL,
            CONSTRAINT uq_case_records_client_case UNIQUE (client_id, case_id)
        );
        CREATE INDEX IF NOT EXISTS idx_case_records_client ON case_records (client_id);
        CREATE INDEX IF NOT EXISTS idx_case_records_case   ON case_records (case_id);
        """
    )
    with engine.begin() as cx:
        cx.execute(ddl)

def ensure_tenant_schema(client_id: str) -> str:
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL not set")

    schema = _schema_name_from_client_id(client_id)

    # 1) create schema
    raw_pg_url = str(DATABASE_URL).replace("+psycopg2", "")
    conn = psycopg2.connect(raw_pg_url)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute(sql.SQL("CREATE SCHEMA IF NOT EXISTS {}" ).format(sql.Identifier(schema)))
    cur.close()
    conn.close()

    # 2) create tables in that schema (ORM + SQL fallback)
    schema_url = _compose_schema_url(DATABASE_URL, schema)
    tenant_engine = create_engine(schema_url, pool_pre_ping=True)

    # ORM attempt
    Base.metadata.create_all(bind=tenant_engine, tables=[CaseRecord.__table__])

    # Verify; if missing, fallback DDL
    with tenant_engine.connect() as cx:
        ok = cx.execute(text("SELECT to_regclass('case_records')")).scalar()
    if not ok:
        _ensure_case_records_sql_fallback(tenant_engine)
        with tenant_engine.connect() as cx:
            ok2 = cx.execute(text("SELECT to_regclass('case_records')")).scalar()
        if not ok2:
            raise RuntimeError("Failed to create case_records (ORM + SQL fallback failed)")

    # 3) write back tenant_db_url
    main_engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    with main_engine.begin() as cx:
        res = cx.execute(
            text(
                """
                UPDATE login_users
                   SET tenant_db_url = :url,
                       tenant_db_ready = TRUE
                 WHERE client_id = :cid
                """
            ),
            {"url": schema_url, "cid": client_id},
        )
        try:
            rc = res.rowcount
        except Exception:
            rc = None
        if not rc:
            print(f"[ensure_tenant_schema] WARN: UPDATE login_users affected 0 rows for client_id={client_id}")

    return schema_url
