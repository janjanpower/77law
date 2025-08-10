# api/services/tenant_bootstrap.py
# 建立每個租戶專屬的 Postgres schema，並回傳帶 search_path 的連線字串
import os
import re
import urllib.parse
import psycopg2
from psycopg2 import sql
from api.database import Base
from api.models_cases import CaseRecord
from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv("DATABASE_URL")

_slug_re = re.compile(r"[^a-z0-9_]+")

def _schema_name_from_client_id(client_id: str) -> str:
    # schema 名只能用小寫英數與底線；前綴 tenant_
    s = client_id.strip().lower().replace("-", "_")
    s = _slug_re.sub("_", s)
    s = s.strip("_")
    if not s:
        s = "x"
    return f"tenant_{s}"

def _compose_schema_url(base_url: str, schema: str) -> str:
    # 在連線字串後面加 options=-c search_path=schema
    sep = "&" if "?" in base_url else "?"
    return f"{base_url}{sep}options={urllib.parse.quote('-c search_path=' + schema)}"

def ensure_tenant_schema(client_id: str) -> str:
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL not set")

    schema = _schema_name_from_client_id(client_id)

    # 1) 建 schema（若不存在）
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute(sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(sql.Identifier(schema)))
    cur.close()
    conn.close()

    # 2) 組租戶 schema 連線字串 + 建表
    schema_url = _compose_schema_url(DATABASE_URL, schema)
    eng = create_engine(schema_url, pool_pre_ping=True)
    Base.metadata.create_all(bind=eng, tables=[CaseRecord.__table__])

    # 3) ✅ 直接回寫 login_users（保證有 URL）
    main_eng = create_engine(DATABASE_URL, pool_pre_ping=True)
    with main_eng.begin() as cx:
        cx.execute(
            text("""
                UPDATE login_users
                   SET tenant_db_url = :url,
                       tenant_db_ready = TRUE
                 WHERE client_id = :cid
            """),
            {"url": schema_url, "cid": client_id}
        )

    return schema_url
