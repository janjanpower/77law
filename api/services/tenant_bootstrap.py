# -*- coding: utf-8 -*-
"""
api/services/tenant_bootstrap.py
建立每個租戶專屬的 Postgres schema，並回傳帶 search_path 的連線字串。
使用 ORM 在該 schema 建立與主系統一致的 case_records 表。
"""

import os
import re
import urllib.parse
import psycopg2
from psycopg2 import sql
from sqlalchemy import create_engine

from api.database import Base
from api.models_cases import CaseRecord

DATABASE_URL = os.getenv("DATABASE_URL")

_slug_re = re.compile(r"[^a-z0-9_]+")


def _schema_name_from_client_id(client_id: str) -> str:
    """將 client_id 轉成合法的 schema 名稱"""
    s = client_id.strip().lower().replace("-", "_")
    s = _slug_re.sub("_", s)
    s = s.strip("_")
    if not s:
        s = "x"
    return f"tenant_{s}"


def _compose_schema_url(base_url: str, schema: str) -> str:
    """在連線字串後面加 options=-c search_path=schema"""
    sep = "&" if "?" in base_url else "?"
    return f"{base_url}{sep}options={urllib.parse.quote('-c search_path=' + schema)}"


def ensure_tenant_schema(client_id: str) -> str:
    """
    建立（若不存在）租戶專屬 schema 與最低限度表結構。
    回傳：附帶 search_path 的連線字串，可直接給 ORM/連線使用。
    """
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL not set")

    schema = _schema_name_from_client_id(client_id)

    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    cur = conn.cursor()

    # 1) 建 schema（若不存在）
    cur.execute(sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(sql.Identifier(schema)))

    cur.close()
    conn.close()

    # 2) 回傳可直接使用的連線字串（鎖定在該 schema）
    schema_url = _compose_schema_url(DATABASE_URL, schema)

    # 3) 使用主系統的 ORM 定義在該 schema 建立 case_records 表
    eng = create_engine(schema_url, pool_pre_ping=True)
    Base.metadata.create_all(bind=eng, tables=[CaseRecord.__table__])

    return schema_url
